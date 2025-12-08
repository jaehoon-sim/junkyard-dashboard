import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import datetime
import requests
import re
import os
import traceback
import time
import gc
import hashlib
import numpy as np

# ---------------------------------------------------------
# 🛠️ [설정] 페이지 설정
# ---------------------------------------------------------
st.set_page_config(page_title="K-Parts Global Hub", layout="wide")

def safe_rerun():
    try:
        st.rerun()
    except AttributeError:
        st.experimental_rerun()

# ---------------------------------------------------------
# 🔐 [보안] 계정 설정
# ---------------------------------------------------------
try:
    ADMIN_CREDENTIALS = st.secrets["ADMIN_CREDENTIALS"]
    NAVER_CLIENT_ID = st.secrets["NAVER_CLIENT_ID"]
    NAVER_CLIENT_SECRET = st.secrets["NAVER_CLIENT_SECRET"]
except:
    ADMIN_CREDENTIALS = {"admin": "1234"}
    NAVER_CLIENT_ID = "aic55XK2RCthRyeMMlJM"
    NAVER_CLIENT_SECRET = "ZqOAIOzYGf"

# 바이어 계정
BUYER_CREDENTIALS = {
    "buyer": "1111",
    "global": "2222",
    "testbuyer": "1234"
}

DB_NAME = 'junkyard.db'

# ---------------------------------------------------------
# 🌍 [설정] 지역명 한글 -> 영문 매핑 테이블
# ---------------------------------------------------------
REGION_EN_MAP = {
    '경기': 'Gyeonggi', '서울': 'Seoul', '인천': 'Incheon', '강원': 'Gangwon',
    '충북': 'Chungbuk', '충남': 'Chungnam', '대전': 'Daejeon', '세종': 'Sejong',
    '전북': 'Jeonbuk', '전남': 'Jeonnam', '광주': 'Gwangju',
    '경북': 'Gyeongbuk', '경남': 'Gyeongnam', '대구': 'Daegu', '부산': 'Busan', '울산': 'Ulsan',
    '제주': 'Jeju', '기타': 'Other'
}

# 📍 전국 시/군/구 단위 상세 좌표 데이터베이스 (Fallback용)
CITY_COORDS = {
    '경기 수원': [37.2636, 127.0286], '경기 성남': [37.4386, 127.1378], '경기 용인': [37.2410, 127.1775],
    '경기 안양': [37.3943, 126.9568], '경기 안산': [37.3219, 126.8309], '경기 과천': [37.4292, 126.9877],
    '경기 광명': [37.4784, 126.8647], '경기 광주': [37.4293, 127.2551], '경기 군포': [37.3614, 126.9352],
    '경기 부천': [37.5034, 126.7660], '경기 시흥': [37.3801, 126.8029], '경기 김포': [37.6152, 126.7157],
    '경기 안성': [37.0080, 127.2797], '경기 오산': [37.1498, 127.0771], '경기 의왕': [37.3447, 126.9683],
    '경기 이천': [37.2892, 127.4452], '경기 평택': [36.9924, 127.1127], '경기 하남': [37.5393, 127.2148],
    '경기 화성': [37.1995, 126.8315], '경기 여주': [37.2983, 127.6373], '경기 양평': [37.4918, 127.4876],
    '경기 고양': [37.6584, 126.8320], '경기 구리': [37.5943, 127.1296], '경기 남양주': [37.6360, 127.2165],
    '경기 동두천': [37.9019, 127.0607], '경기 양주': [37.7853, 127.0459], '경기 의정부': [37.7381, 127.0337],
    '경기 파주': [37.7600, 126.7798], '경기 포천': [37.8949, 127.2003], '경기 연천': [38.0964, 127.0749],
    '경기 가평': [37.8315, 127.5097],
    '충북 청주': [36.6424, 127.4890], '충북 충주': [36.9915, 127.9260], '충북 제천': [37.1326, 128.1910],
    '충북 음성': [36.9403, 127.6903], '충북 진천': [36.8553, 127.4355], '충북 괴산': [36.8153, 127.7867],
    '충남 천안': [36.8151, 127.1139], '충남 공주': [36.4465, 127.1190], '충남 보령': [36.3333, 126.6129],
    '충남 아산': [36.7898, 127.0018], '충남 서산': [36.7848, 126.4503], '충남 논산': [36.2021, 127.0850],
    '충남 당진': [36.8906, 126.6290], '충남 금산': [36.1087, 127.4883], '충남 예산': [36.6816, 126.8437],
    '충남 홍성': [36.6015, 126.6607], '충남 부여': [36.2755, 126.9097], '세종': [36.4800, 127.2890],
    '경북 포항': [36.0190, 129.3435], '경북 경주': [35.8562, 129.2247], '경북 김천': [36.1398, 128.1136],
    '경북 안동': [36.5684, 128.7294], '경북 구미': [36.1195, 128.3443], '경북 영주': [36.8055, 128.6241],
    '경북 영천': [35.9733, 128.9385], '경북 상주': [36.4109, 128.1591], '경북 경산': [35.8251, 128.7414],
    '경북 칠곡': [35.9610, 128.4014], '경북 성주': [35.9190, 128.2829],
    '경남 창원': [35.2279, 128.6818], '경남 진주': [35.1805, 128.1076], '경남 통영': [34.8544, 128.4332],
    '경남 사천': [35.0038, 128.0642], '경남 김해': [35.2285, 128.8894], '경남 밀양': [35.5038, 128.7466],
    '경남 거제': [34.8806, 128.6211], '경남 양산': [35.3350, 129.0373], '경남 함안': [35.2725, 128.4065],
    '경남 창녕': [35.5413, 128.4923], '경남 고성': [34.9755, 128.3232], '경남 거창': [35.6865, 127.9093],
    '전북 전주': [35.8242, 127.1480], '전북 군산': [35.9676, 126.7366], '전북 익산': [35.9483, 126.9578],
    '전북 정읍': [35.5699, 126.8559], '전북 남원': [35.4164, 127.3904], '전북 김제': [35.8036, 126.8809],
    '전북 완주': [35.9048, 127.1620],
    '전남 목포': [34.8118, 126.3922], '전남 여수': [34.7604, 127.6622], '전남 순천': [34.9506, 127.4872],
    '전남 나주': [35.0158, 126.7108], '전남 광양': [34.9407, 127.6959], '전남 화순': [35.0645, 126.9863],
    '전남 담양': [35.3211, 126.9881], '전남 해남': [34.5708, 126.5990],
    '서울': [37.5665, 126.9780], '인천': [37.4563, 126.7052], '대전': [36.3504, 127.3845],
    '대구': [35.8714, 128.6014], '광주': [35.1595, 126.8526], '부산': [35.1796, 129.0756],
    '울산': [35.5384, 129.3114], '제주': [33.4996, 126.5312]
}

# ---------------------------------------------------------
# 1. 데이터베이스 초기화
# ---------------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS vehicle_data (vin TEXT PRIMARY KEY, reg_date TEXT, car_no TEXT, manufacturer TEXT, model_name TEXT, model_year REAL, junkyard TEXT, engine_code TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS junkyard_info (name TEXT PRIMARY KEY, address TEXT, region TEXT, lat REAL, lon REAL, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS model_list (manufacturer TEXT, model_name TEXT, PRIMARY KEY (manufacturer, model_name))''')
    c.execute('''CREATE TABLE IF NOT EXISTS search_logs_v2 (id INTEGER PRIMARY KEY AUTOINCREMENT, keyword TEXT, search_type TEXT, country TEXT, city TEXT, lat REAL, lon REAL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        buyer_id TEXT,
        target_partner_alias TEXT,
        real_junkyard_name TEXT,
        items_summary TEXT,
        status TEXT DEFAULT 'PENDING',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute("CREATE INDEX IF NOT EXISTS idx_mfr ON vehicle_data(manufacturer)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_model ON vehicle_data(model_name)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_engine ON vehicle_data(engine_code)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_yard ON vehicle_data(junkyard)")
    conn.commit()
    return conn

# ---------------------------------------------------------
# 🕵️ [직거래 방지] 데이터 마스킹 & 포맷팅
# ---------------------------------------------------------
def generate_alias(real_name):
    if not isinstance(real_name, str): return "Unknown"
    hash_object = hashlib.md5(str(real_name).encode())
    hash_int = int(hash_object.hexdigest(), 16) % 900 + 100 
    return f"Partner #{hash_int}"

def translate_region(region_kr):
    """한글 지역명을 영문으로 변환 (Mapping + Fallback)"""
    s = str(region_kr)
    # 매핑 테이블에서 먼저 찾기
    for kr, en in REGION_EN_MAP.items():
        if kr in s: return en
    return "Korea" # Fallback

def mask_dataframe(df, role):
    if df.empty: return df
    df_safe = df.copy()
    
    # 🟢 [수정] Region 영문 변환 (모든 권한 공통)
    if 'region' in df_safe.columns:
        df_safe['region'] = df_safe['region'].apply(translate_region)

    # 1. 관리자: 원본 유지하되 편의상 Alias만 추가
    if role == 'admin':
        if 'junkyard' in df_safe.columns:
            df_safe['partner_alias'] = df_safe['junkyard'].apply(generate_alias)
        return df_safe

    # 2. 바이어/게스트: 마스킹 적용
    
    # 업체명 (내부 백업 후 Alias로 교체)
    if 'junkyard' in df_safe.columns:
        df_safe['real_junkyard'] = df_safe['junkyard'] # 로직용 백업
        if role == 'buyer':
            df_safe['junkyard'] = df_safe['junkyard'].apply(generate_alias)
        else:
            df_safe['junkyard'] = "🔒 Login Required"

    # 주소 (상세주소 제거 후 광역 영문 주소로 변경)
    def simplify_address(addr):
        # 주소 문자열에서 지역명 찾아서 영문 변환
        return f"{translate_region(addr)}, South Korea"
    
    if 'address' in df_safe.columns:
        if role == 'buyer':
            df_safe['address'] = df_safe['address'].apply(simplify_address)
        else:
            df_safe['address'] = "🔒 Login Required"

    # 민감정보 제거
    if 'vin' in df_safe.columns:
        df_safe['vin'] = df_safe['vin'].astype(str).apply(lambda x: x[:8] + "****" if len(x) > 8 else "****")
    
    # 🟢 [수정] Lat, Lon, Car_no, real_junkyard 컬럼 완전 제거 (화면 표시 방지)
    drop_cols = ['car_no', 'lat', 'lon', 'real_junkyard']
    df_safe = df_safe.drop(columns=[c for c in drop_cols if c in df_safe.columns], errors='ignore')

    return df_safe

# ---------------------------------------------------------
# 기능 함수들
# ---------------------------------------------------------
def log_search(keywords, s_type):
    if not keywords: return
    try:
        conn = init_db()
        c = conn.cursor()
        lat, lon, city, country = 37.5, 127.0, 'Seoul', 'KR' 
        if isinstance(keywords, list):
            for k in keywords:
                c.execute("INSERT INTO search_logs_v2 (keyword, search_type, country, city, lat, lon) VALUES (?, ?, ?, ?, ?, ?)", (str(k), s_type, country, city, lat, lon))
        else:
            c.execute("INSERT INTO search_logs_v2 (keyword, search_type, country, city, lat, lon) VALUES (?, ?, ?, ?, ?, ?)", (str(keywords), s_type, country, city, lat, lon))
        conn.commit()
        conn.close()
    except: pass

def get_search_trends():
    try:
        conn = init_db()
        eng = pd.read_sql("SELECT keyword, COUNT(*) as count FROM search_logs_v2 WHERE search_type='engine' GROUP BY keyword ORDER BY count DESC LIMIT 10", conn)
        mod = pd.read_sql("SELECT keyword, COUNT(*) as count FROM search_logs_v2 WHERE search_type='model' GROUP BY keyword ORDER BY count DESC LIMIT 10", conn)
        conn.close()
        return eng, mod
    except: return pd.DataFrame(), pd.DataFrame()

def save_vehicle_file(uploaded_file):
    try:
        if uploaded_file.name.endswith('.csv'): df = pd.read_csv(uploaded_file, dtype=str)
        else: 
            try: df = pd.read_excel(uploaded_file, engine='openpyxl', dtype=str)
            except: df = pd.read_excel(uploaded_file, engine='xlrd', dtype=str)

        if '차대번호' not in df.columns:
            if uploaded_file.name.endswith('.csv'): uploaded_file.seek(0); df = pd.read_csv(uploaded_file, header=2, dtype=str)
            else: 
                try: df = pd.read_excel(uploaded_file, header=2, engine='openpyxl', dtype=str)
                except: df = pd.read_excel(uploaded_file, header=2, engine='xlrd', dtype=str)
        
        df.columns = [str(c).strip() for c in df.columns]
        required = ['등록일자', '차량번호', '차대번호', '제조사', '차량명', '회원사', '원동기형식']
        if not all(col in df.columns for col in required): return 0, 0

        conn = init_db()
        c = conn.cursor()
        
        df_db = pd.DataFrame()
        df_db['vin'] = df['차대번호'].fillna('').astype(str).str.strip()
        df_db['reg_date'] = df['등록일자'].fillna('').astype(str)
        df_db['car_no'] = df['차량번호'].fillna('').astype(str)
        df_db['manufacturer'] = df['제조사'].fillna('').astype(str)
        df_db['model_name'] = df['차량명'].fillna('').astype(str)
        df_db['junkyard'] = df['회원사'].fillna('').astype(str)
        df_db['engine_code'] = df['원동기형식'].fillna('').astype(str)
        
        def parse_year(x):
            try: return float(re.findall(r"[\d\.]+", str(x))[0])
            except: return 0.0
        df_db['model_year'] = df['연식'].apply(parse_year)

        df_db.to_sql('temp_vehicles', conn, if_exists='replace', index=False)
        c.execute("""INSERT OR IGNORE INTO vehicle_data (vin, reg_date, car_no, manufacturer, model_name, model_year, junkyard, engine_code)
                     SELECT vin, reg_date, car_no, manufacturer, model_name, model_year, junkyard, engine_code FROM temp_vehicles""")
        cnt = len(df_db)
        c.execute("DROP TABLE temp_vehicles")
        
        model_list_df = df_db[['manufacturer', 'model_name']].drop_duplicates()
        for _, row in model_list_df.iterrows():
            c.execute("INSERT OR IGNORE INTO model_list (manufacturer, model_name) VALUES (?, ?)", (row['manufacturer'], row['model_name']))

        unique_yards = df_db['junkyard'].unique().tolist()
        for yard in unique_yards:
            c.execute("INSERT OR IGNORE INTO junkyard_info (name, address, region, lat, lon) VALUES (?, ?, ?, ?, ?)", (yard, '검색실패', '기타', 0.0, 0.0))
            
        conn.commit()
        conn.close()
        return cnt, 0
    except: return 0, 0

@st.cache_data(ttl=300)
def load_all_data():
    try:
        conn = init_db()
        # [수정] lat, lon 컬럼 삭제됨
        query = "SELECT v.*, j.region, j.address FROM vehicle_data v LEFT JOIN junkyard_info j ON v.junkyard = j.name"
        df = pd.read_sql(query, conn)
        conn.close()
        if not df.empty:
            df['model_year'] = pd.to_numeric(df['model_year'], errors='coerce').fillna(0)
            df['reg_date'] = pd.to_datetime(df['reg_date'], errors='coerce')
        return df
    except: return pd.DataFrame()

def load_model_list():
    try:
        conn = init_db()
        df = pd.read_sql("SELECT manufacturer, model_name FROM model_list ORDER BY manufacturer, model_name", conn)
        conn.close()
        return df
    except: return pd.DataFrame()

def load_engine_list():
    try:
        conn = init_db()
        df = pd.read_sql("SELECT DISTINCT engine_code FROM vehicle_data ORDER BY engine_code", conn)
        conn.close()
        return df['engine_code'].tolist()
    except: return []

def load_yard_list_for_filter(role):
    try:
        conn = init_db()
        df = pd.read_sql("SELECT name FROM junkyard_info ORDER BY name", conn)
        conn.close()
        real_names = df['name'].tolist()
        if role == 'admin':
            return real_names
        elif role == 'buyer':
            return sorted(list(set([generate_alias(name) for name in real_names])))
        return []
    except: return []

def reset_dashboard():
    st.session_state['view_data'] = load_all_data()
    st.session_state['is_filtered'] = False
    st.session_state['mode_demand'] = False
    
    if 'maker_sel' in st.session_state: st.session_state['maker_sel'] = "All"
    if 'sy' in st.session_state: st.session_state['sy'] = 2000
    if 'ey' in st.session_state: st.session_state['ey'] = datetime.datetime.now().year
    if 'mms' in st.session_state: st.session_state['mms'] = []
    if 'es' in st.session_state: st.session_state['es'] = []
    if 'ys' in st.session_state: st.session_state['ys'] = []

# ---------------------------------------------------------
# 🚀 메인 어플리케이션
# ---------------------------------------------------------
if 'user_role' not in st.session_state: st.session_state.user_role = 'guest'
if 'username' not in st.session_state: st.session_state.username = 'Guest'
if 'view_data' not in st.session_state: st.session_state['view_data'] = pd.DataFrame()
if 'is_filtered' not in st.session_state: st.session_state['is_filtered'] = False
if 'mode_demand' not in st.session_state: st.session_state.mode_demand = False

df_raw = load_all_data()
df_models = load_model_list()
list_engines = load_engine_list()

# 1. 사이드바
with st.sidebar:
    st.title("K-Parts Global Hub")
    
    # 로그인
    if st.session_state.user_role == 'guest':
        with st.expander("🔐 Login", expanded=True):
            uid = st.text_input("ID")
            upw = st.text_input("Password", type="password")
            if st.button("Sign In"):
                if uid in ADMIN_CREDENTIALS and ADMIN_CREDENTIALS[uid] == upw:
                    st.session_state.user_role = 'admin'
                    st.session_state.username = uid
                    safe_rerun()
                elif uid in BUYER_CREDENTIALS and BUYER_CREDENTIALS[uid] == upw:
                    st.session_state.user_role = 'buyer'
                    st.session_state.username = uid
                    safe_rerun()
                else:
                    st.error("Invalid Credentials")
    else:
        role_text = "Manager" if st.session_state.user_role == 'admin' else "Global Buyer"
        st.success(f"Welcome, {st.session_state.username} ({role_text})!")
        if st.button("Logout"):
            st.session_state.user_role = 'guest'
            st.session_state.username = 'Guest'
            safe_rerun()

    st.divider()

    if st.session_state.user_role == 'admin':
        with st.expander("📂 Admin Tools"):
            up_files = st.file_uploader("Data Upload", type=['xlsx', 'xls', 'csv'], accept_multiple_files=True)
            if up_files and st.button("Save"):
                tot = 0
                bar = st.progress(0)
                for i, f in enumerate(up_files):
                    n, _ = save_vehicle_file(f)
                    tot += n
                    bar.progress((i+1)/len(up_files))
                st.success(f"{tot} records uploaded.")
                load_all_data.clear()
                safe_rerun()
            
            if st.button("🗑️ Reset DB"):
                conn = init_db()
                conn.execute("DROP TABLE vehicle_data")
                conn.execute("DROP TABLE junkyard_info")
                conn.execute("DROP TABLE model_list")
                conn.execute("DROP TABLE search_logs_v2")
                conn.execute("DROP TABLE orders")
                conn.commit()
                conn.close()
                st.success("Reset Done")
                safe_rerun()

    st.subheader("🔍 Search Filter")
    search_tabs = st.tabs(["🚙 Vehicle", "🔧 Engine", "🏭 Yard", "🔮 Forecast"])
    
    with search_tabs[0]: 
        if not df_models.empty:
            makers = sorted(df_models['manufacturer'].unique().tolist())
            makers.insert(0, "All")
            sel_maker = st.selectbox("Manufacturer", makers, key="msel")
            
            c1, c2 = st.columns(2)
            with c1: sel_sy = st.number_input("From", 1990, 2030, 2000)
            with c2: sel_ey = st.number_input("To", 1990, 2030, 2025)
            
            if sel_maker != "All":
                f_models = sorted(df_models[df_models['manufacturer'] == sel_maker]['model_name'].tolist())
            else:
                f_models = sorted(df_models['model_name'].unique().tolist())
            sel_models = st.multiselect("Model", f_models, key="mms")
            
            if st.button("🔍 Search Vehicle", type="primary"):
                log_search(sel_models, 'model')
                res = load_all_data()
                if sel_maker != "All": res = res[res['manufacturer'] == sel_maker]
                if sel_models: res = res[res['model_name'].isin(sel_models)]
                res = res[(res['model_year'] >= sel_sy) & (res['model_year'] <= sel_ey)]
                
                st.session_state['view_data'] = res.reset_index(drop=True)
                st.session_state['is_filtered'] = True
                st.session_state['mode_demand'] = False
                safe_rerun()

    with search_tabs[1]: 
        if list_engines:
            sel_engines = st.multiselect("Engine Code", list_engines)
            if st.button("🔍 Search Engine", type="primary"):
                log_search(sel_engines, 'engine')
                res = load_all_data()
                if sel_engines: res = res[res['engine_code'].isin(sel_engines)]
                st.session_state['view_data'] = res.reset_index(drop=True)
                st.session_state['is_filtered'] = True
                st.session_state['mode_demand'] = False
                safe_rerun()

    with search_tabs[2]: 
        filter_yards = load_yard_list_for_filter(st.session_state.user_role)
        if not filter_yards:
            st.warning("Login required.")
        else:
            sel_yards = st.multiselect("Partner Name", filter_yards, key="ys")
            if st.button("🔍 Search Partner", type="primary"):
                res = load_all_data()
                if sel_yards:
                    res['alias_temp'] = res['junkyard'].apply(generate_alias)
                    if st.session_state.user_role == 'admin':
                        res = res[res['junkyard'].isin(sel_yards)]
                    else:
                        res = res[res['alias_temp'].isin(sel_yards)]
                    if 'alias_temp' in res.columns: res = res.drop(columns=['alias_temp'])

                st.session_state['view_data'] = res.reset_index(drop=True)
                st.session_state['is_filtered'] = True
                st.session_state['mode_demand'] = False
                safe_rerun()

    with search_tabs[3]: 
        st.info("Check global search trends.")
        if st.button("🔮 Show Trends"):
            st.session_state['mode_demand'] = True
            safe_rerun()

    if st.button("🔄 Reset Filters", use_container_width=True, on_click=reset_dashboard):
        pass

# 2. 메인 화면
if st.session_state.mode_demand:
    st.title("📈 Global Demand Trends (Real-time)")
    eng_trend, mod_trend = get_search_trends()
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🔥 Top Searched Engines")
        if not eng_trend.empty:
            fig = px.bar(eng_trend, x='count', y='keyword', orientation='h', text='count')
            st.plotly_chart(fig, use_container_width=True)
        else: st.info("No data yet.")
    with c2:
        st.subheader("🚙 Top Searched Models")
        if not mod_trend.empty:
            fig = px.bar(mod_trend, x='count', y='keyword', orientation='h', text='count')
            st.plotly_chart(fig, use_container_width=True)
        else: st.info("No data yet.")
else:
    st.title("🇰🇷 Korea Used Auto Parts Inventory")
    
    df_view = st.session_state['view_data']
    
    # 🛡️ 마스킹 적용
    df_display = mask_dataframe(df_view, st.session_state.user_role)
    
    if st.session_state.user_role == 'admin':
        main_tabs = st.tabs(["📊 Inventory", "📩 Orders"])
    else:
        main_tabs = st.tabs(["📊 Search Results"])

    with main_tabs[0]:
        if df_display.empty:
            st.info("Please select filters from the sidebar to search.")
        else:
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Vehicles", f"{len(df_display):,} EA")
            c2.metric("Matched Engines", f"{df_display['engine_code'].nunique()} Types")
            sup_label = "Real Junkyards" if st.session_state.user_role == 'admin' else "Partners"
            c3.metric(sup_label, f"{df_display['junkyard'].nunique()} EA")
            
            st.divider()
            st.subheader("📦 Stock by Partner")
            
            grp_cols = ['junkyard', 'address']
            if st.session_state.user_role == 'admin' and 'region' in df_display.columns:
                grp_cols.append('region')
            
            stock_summary = df_display.groupby(grp_cols).size().reset_index(name='qty').sort_values('qty', ascending=False)
            selection = st.dataframe(stock_summary, use_container_width=True, hide_index=True, selection_mode="single-row", on_select="rerun")
            
            # [수정됨] 견적 요청 폼
            if len(selection.selection.rows) > 0:
                sel_idx = selection.selection.rows[0]
                sel_row = stock_summary.iloc[sel_idx]
                target_partner = sel_row['junkyard']
                stock_cnt = sel_row['qty']
                
                if st.session_state.user_role == 'guest':
                    st.warning("🔒 Login required to request a quote.")
                else:
                    st.success(f"Selected: **{target_partner}** ({stock_cnt} EA)")
                    
                    with st.form("order_form"):
                        st.markdown(f"### 📨 Request Quote to {target_partner}")
                        c_a, c_b = st.columns(2)
                        with c_a:
                            buyer_name = st.text_input("Name / Company", value=st.session_state.username)
                            contact = st.text_input("Contact (Email/Phone) *")
                            req_qty = st.number_input("Quantity *", min_value=1, value=1)
                        with c_b:
                            # 🟢 [핵심] 검색 필터 기반 자동 품목 생성
                            s_maker = st.session_state.get('msel', 'All')
                            s_models = st.session_state.get('mms', [])
                            s_engines = st.session_state.get('es', [])
                            s_sy = st.session_state.get('sy', 2000)
                            s_ey = st.session_state.get('ey', 2025)

                            item_desc = []
                            if s_engines: item_desc.append(f"Engine: {','.join(s_engines[:3])}")
                            elif s_models: item_desc.append(f"Model: {','.join(s_models[:3])}")
                            elif s_maker != "All": item_desc.append(f"{s_maker} Cars")
                            else: item_desc.append("Auto Parts")
                            
                            if not s_engines: item_desc.append(f"({s_sy}~{s_ey})")
                            
                            def_item = " ".join(item_desc)
                            
                            # 🟢 [수정] 수량 중복 제거 (순수 품목명만)
                            item = st.text_input("Item *", value=def_item)
                            offer = st.text_input("Target Unit Price (USD) *", placeholder="e.g. $500/ea")
                        
                        msg = st.text_area("Message to Admin", height=80, placeholder="Details...")
                        
                        if st.form_submit_button("🚀 Send Inquiry"):
                            if not contact or not item or not offer:
                                st.error("⚠️ Please fill in all required fields: Contact, Item, and Price.")
                            else:
                                conn = init_db()
                                cur = conn.cursor()
                                real_name = target_partner
                                if st.session_state.user_role == 'buyer':
                                    try:
                                        match = df_view[df_view['junkyard'].apply(generate_alias) == target_partner]
                                        if not match.empty:
                                            real_name = match['junkyard'].iloc[0]
                                    except: real_name = "Unknown"

                                summary = f"Qty: {req_qty} (Total Stock: {stock_cnt}), Item: {item}, Price: {offer}, Msg: {msg}"
                                cur.execute("INSERT INTO orders (buyer_id, target_partner_alias, real_junkyard_name, items_summary, status) VALUES (?, ?, ?, ?, ?)",
                                            (buyer_name, target_partner, real_name, summary, 'PENDING'))
                                conn.commit()
                                conn.close()
                                st.success("✅ Inquiry has been sent to our sales team.")

            st.divider()
            st.subheader("📋 Item List")
            st.dataframe(df_display, use_container_width=True)

    if st.session_state.user_role == 'admin':
        with main_tabs[1]:
            st.subheader("📩 Quote Requests")
            conn = init_db()
            orders = pd.read_sql("SELECT * FROM orders ORDER BY created_at DESC", conn)
            conn.close()
            if not orders.empty: st.dataframe(orders)
            else: st.info("No orders.")
