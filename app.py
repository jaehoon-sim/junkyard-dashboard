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
# 🛠️ [설정] 페이지 설정 (변경됨)
# ---------------------------------------------------------
st.set_page_config(page_title="K-Used Car Global Hub", layout="wide")

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
# 🌍 [설정] 주소 변환 데이터
# ---------------------------------------------------------
PROVINCE_MAP = {
    '경기': 'Gyeonggi-do', '서울': 'Seoul', '인천': 'Incheon', '강원': 'Gangwon-do',
    '충북': 'Chungbuk', '충남': 'Chungnam', '대전': 'Daejeon', '세종': 'Sejong',
    '전북': 'Jeonbuk', '전남': 'Jeonnam', '광주': 'Gwangju',
    '경북': 'Gyeongbuk', '경남': 'Gyeongnam', '대구': 'Daegu', '부산': 'Busan', '울산': 'Ulsan',
    '제주': 'Jeju', '경상남도': 'Gyeongnam', '경상북도': 'Gyeongbuk', 
    '전라남도': 'Jeonnam', '전라북도': 'Jeonbuk', '충청남도': 'Chungnam', '충청북도': 'Chungbuk',
    '경기도': 'Gyeonggi-do', '강원도': 'Gangwon-do', '제주도': 'Jeju'
}

CITY_MAP = {
    '수원': 'Suwon', '성남': 'Seongnam', '의정부': 'Uijeongbu', '안양': 'Anyang',
    '부천': 'Bucheon', '광명': 'Gwangmyeong', '평택': 'Pyeongtaek', '동두천': 'Dongducheon',
    '안산': 'Ansan', '고양': 'Goyang', '과천': 'Gwacheon', '구리': 'Guri',
    '남양주': 'Namyangju', '오산': 'Osan', '시흥': 'Siheung', '군포': 'Gunpo',
    '의왕': 'Uiwang', '하남': 'Hanam', '용인': 'Yongin', '파주': 'Paju',
    '이천': 'Icheon', '안성': 'Anseong', '김포': 'Gimpo', '화성': 'Hwaseong',
    '광주': 'Gwangju', '양주': 'Yangju', '포천': 'Pocheon', '여주': 'Yeoju',
    '연천': 'Yeoncheon', '가평': 'Gapyeong', '양평': 'Yangpyeong',
    '천안': 'Cheonan', '공주': 'Gongju', '보령': 'Boryeong', '아산': 'Asan',
    '서산': 'Seosan', '논산': 'Nonsan', '계룡': 'Gyeryong', '당진': 'Dangjin',
    '금산': 'Geumsan', '부여': 'Buyeo', '서천': 'Seocheon', '청양': 'Cheongyang',
    '홍성': 'Hongseong', '예산': 'Yesan', '태안': 'Taean',
    '청주': 'Cheongju', '충주': 'Chungju', '제천': 'Jecheon', '보은': 'Boeun',
    '옥천': 'Okcheon', '영동': 'Yeongdong', '증평': 'Jeungpyeong', '진천': 'Jincheon',
    '괴산': 'Goesan', '음성': 'Eumseong', '단양': 'Danyang',
    '포항': 'Pohang', '경주': 'Gyeongju', '김천': 'Gimcheon', '안동': 'Andong',
    '구미': 'Gumi', '영주': 'Yeongju', '영천': 'Yeongcheon', '상주': 'Sangju',
    '문경': 'Mungyeong', '경산': 'Gyeongsan', '군위': 'Gunwi', '의성': 'Uiseong',
    '청송': 'Cheongsong', '영양': 'Yeongyang', '영덕': 'Yeongdeok', '청도': 'Cheongdo',
    '고령': 'Goryeong', '성주': 'Seongju', '칠곡': 'Chilgok', '예천': 'Yecheon',
    '봉화': 'Bonghwa', '울진': 'Uljin', '울릉': 'Ulleung',
    '창원': 'Changwon', '진주': 'Jinju', '통영': 'Tongyeong', '사천': 'Sacheon',
    '김해': 'Gimhae', '밀양': 'Miryang', '거제': 'Geoje', '양산': 'Yangsan',
    '의령': 'Uiryeong', '함안': 'Haman', '창녕': 'Changnyeong', '고성': 'Goseong',
    '남해': 'Namhae', '하동': 'Hadong', '산청': 'Sancheong', '함양': 'Hamyang',
    '거창': 'Geochang', '합천': 'Hapcheon',
    '전주': 'Jeonju', '군산': 'Gunsan', '익산': 'Iksan', '정읍': 'Jeongeup',
    '남원': 'Namwon', '김제': 'Gimje', '완주': 'Wanju', '진안': 'Jinan',
    '무주': 'Muju', '장수': 'Jangsu', '임실': 'Imsil', '순창': 'Sunchang',
    '고창': 'Gochang', '부안': 'Buan',
    '목포': 'Mokpo', '여수': 'Yeosu', '순천': 'Suncheon', '나주': 'Naju',
    '광양': 'Gwangyang', '담양': 'Damyang', '곡성': 'Gokseong', '구례': 'Gurye',
    '고흥': 'Goheung', '보성': 'Boseong', '화순': 'Hwasun', '장흥': 'Jangheung',
    '강진': 'Gangjin', '해남': 'Haenam', '영암': 'Yeongam', '무안': 'Muan',
    '함평': 'Hampyeong', '영광': 'Yeonggwang', '장성': 'Jangseong', '완도': 'Wando',
    '진도': 'Jindo', '신안': 'Sinan', '제주': 'Jeju', '서귀포': 'Seogwipo'
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
        contact_info TEXT,
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
# 🕵️ [직거래 방지] 데이터 마스킹 & 영문 변환
# ---------------------------------------------------------
def generate_alias(real_name):
    if not isinstance(real_name, str): return "Unknown"
    hash_object = hashlib.md5(str(real_name).encode())
    hash_int = int(hash_object.hexdigest(), 16) % 900 + 100 
    return f"Partner #{hash_int}"

def translate_address(addr):
    """한글 주소 -> 영문 주소 변환 (시/군 단위)"""
    if not isinstance(addr, str) or addr == "검색실패" or "조회" in addr:
        return "Unknown Address"
        
    parts = addr.split()
    if len(parts) < 2: return "South Korea"
    
    k_do = parts[0][:2]
    k_city = parts[1]
    
    en_do = PROVINCE_MAP.get(k_do, k_do)
    for k, v in PROVINCE_MAP.items():
        if k in parts[0]: 
            en_do = v
            break
            
    city_core = k_city.replace('시','').replace('군','').replace('구','')
    en_city = CITY_MAP.get(city_core, city_core)
    
    if en_do in ['Seoul', 'Incheon', 'Busan', 'Daegu', 'Daejeon', 'Gwangju', 'Ulsan']:
        return f"{en_do}, Korea"
    else:
        suffix = "-si" if "시" in k_city else ("-gun" if "군" in k_city else "")
        if en_city != city_core: 
             return f"{en_do}, {en_city}{suffix}"
        else:
             return f"{en_do}, Korea"

def mask_dataframe(df, role):
    if df.empty: return df
    df_safe = df.copy()
    
    if role == 'admin':
        if 'junkyard' in df_safe.columns:
            df_safe['partner_alias'] = df_safe['junkyard'].apply(generate_alias)
        return df_safe

    # 바이어/게스트용 마스킹
    if 'junkyard' in df_safe.columns:
        df_safe['real_junkyard'] = df_safe['junkyard'] # 내부 로직용 백업
        if role == 'buyer':
            df_safe['junkyard'] = df_safe['junkyard'].apply(generate_alias)
        else:
            df_safe['junkyard'] = "🔒 Login Required"

    if 'address' in df_safe.columns:
        if role == 'buyer':
            df_safe['address'] = df_safe['address'].apply(translate_address)
            if 'region' in df_safe.columns:
                df_safe['region'] = df_safe['address'].apply(lambda x: x.split(',')[0] if ',' in str(x) else x)
        else:
            df_safe['address'] = "🔒 Login Required"
            df_safe['region'] = "🔒"

    if 'vin' in df_safe.columns:
        df_safe['vin'] = df_safe['vin'].astype(str).apply(lambda x: x[:8] + "****" if len(x) > 8 else "****")
    
    drop_cols = ['car_no', 'lat', 'lon', 'real_junkyard']
    df_safe = df_safe.drop(columns=[c for c in drop_cols if c in df_safe.columns], errors='ignore')

    if role == 'guest' and 'lat' in df_safe.columns:
        df_safe['lat'] = 0.0
        df_safe['lon'] = 0.0
        
    return df_safe

# ---------------------------------------------------------
# 기능 함수들
# ---------------------------------------------------------
def log_search(keywords, s_type):
    if not keywords: return
    try:
        conn = init_db()
        c = conn.cursor()
        city, country = 'Seoul', 'KR'
        if isinstance(keywords, list):
            for k in keywords:
                c.execute("INSERT INTO search_logs_v2 (keyword, search_type, country, city) VALUES (?, ?, ?, ?)", (str(k), s_type, country, city))
        else:
            c.execute("INSERT INTO search_logs_v2 (keyword, search_type, country, city) VALUES (?, ?, ?, ?)", (str(keywords), s_type, country, city))
        conn.commit()
        conn.close()
    except: pass

def get_search_trends():
    try:
        conn = init_db()
        eng = pd.read_sql("SELECT keyword, COUNT(*) as count FROM search_logs_v2 WHERE search_type='engine' GROUP BY keyword ORDER BY count DESC LIMIT 10", conn)
        mod = pd.read_sql("SELECT keyword, COUNT(*) as count FROM search_logs_v2 WHERE search_type='model' GROUP BY keyword ORDER BY count DESC LIMIT 10", conn)
        conn.close()
        
        if eng.empty and mod.empty: return pd.DataFrame(), pd.DataFrame()
        
        def process_counts(sub_df):
            if sub_df.empty: return pd.DataFrame()
            sub_df['clean_keyword'] = sub_df['keyword'].astype(str).apply(
                lambda x: x.replace('[', '').replace(']', '').replace("'", "").replace('"', '')
            )
            sub_df['split_keyword'] = sub_df['clean_keyword'].apply(lambda x: [i.strip() for i in x.split(',') if i.strip()])
            exploded = sub_df.explode('split_keyword')
            counts = exploded['split_keyword'].value_counts().reset_index()
            counts.columns = ['keyword', 'count']
            return counts.head(10)

        eng_counts = process_counts(eng)
        mod_counts = process_counts(mod)
        return eng_counts, mod_counts
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
            c.execute("INSERT OR IGNORE INTO junkyard_info (name, address, region) VALUES (?, ?, ?)", (yard, '검색실패', '기타'))
            
        conn.commit()
        conn.close()
        return cnt, 0
    except: return 0, 0

def save_address_file(uploaded_file):
    try:
        if uploaded_file.name.endswith('.csv'): df = pd.read_csv(uploaded_file, dtype=str)
        else: 
            try: df = pd.read_excel(uploaded_file, engine='openpyxl', dtype=str)
            except: df = pd.read_excel(uploaded_file, engine='xlrd', dtype=str)
        
        name_col = next((c for c in df.columns if '폐차장' in c or '업체' in c or '회원' in c), None)
        addr_col = next((c for c in df.columns if '주소' in c or '소재' in c), None)
        if not name_col or not addr_col: return 0

        conn = init_db()
        c = conn.cursor()
        update_cnt = 0
        
        for _, row in df.iterrows():
            yard_name = str(row[name_col]).strip()
            address = str(row[addr_col]).strip()
            region = address.split()[0][:2] if len(address.split()) >= 1 else '기타'
            c.execute("INSERT OR REPLACE INTO junkyard_info (name, address, region) VALUES (?, ?, ?)", (yard_name, address, region))
            update_cnt += 1
            
        conn.commit()
        conn.close()
        return update_cnt
    except: return 0

@st.cache_data(ttl=60)
def search_data_from_db(maker, models, engines, sy, ey, yards):
    try:
        conn = init_db()
        
        # Base Filters
        base_cond = "1=1"
        params = []
        
        if maker and maker != "All":
            base_cond += " AND v.manufacturer = ?"
            params.append(maker)
            
        base_cond += " AND v.model_year >= ? AND v.model_year <= ?"
        params.extend([sy, ey])
        
        if models:
            placeholders = ','.join(['?'] * len(models))
            base_cond += f" AND v.model_name IN ({placeholders})"
            params.extend(models)
            
        if engines:
            placeholders = ','.join(['?'] * len(engines))
            base_cond += f" AND v.engine_code IN ({placeholders})"
            params.extend(engines)
            
        if yards:
            placeholders = ','.join(['?'] * len(yards))
            base_cond += f" AND v.junkyard IN ({placeholders})"
            params.extend(yards)
            
        # 1. Total Count
        count_q = f"SELECT COUNT(*) FROM vehicle_data v WHERE {base_cond}"
        cursor = conn.cursor()
        total_count = cursor.execute(count_q, params).fetchone()[0]
        
        # 2. Data Limit
        data_q = f"""
            SELECT v.*, j.region, j.address 
            FROM vehicle_data v 
            LEFT JOIN junkyard_info j ON v.junkyard = j.name
            WHERE {base_cond}
            ORDER BY v.reg_date DESC LIMIT 5000
        """
        df = pd.read_sql(data_q, conn, params=params)
        conn.close()
        
        if not df.empty:
            df['model_year'] = pd.to_numeric(df['model_year'], errors='coerce').fillna(0)
            df['reg_date'] = pd.to_datetime(df['reg_date'], errors='coerce')
            
        return df, total_count
    except Exception as e: return pd.DataFrame(), 0

# 메타데이터 및 초기 로드
@st.cache_data(ttl=300)
def load_metadata_and_init_data():
    conn = init_db()
    df_m = pd.read_sql("SELECT DISTINCT manufacturer, model_name FROM model_list", conn)
    df_e = pd.read_sql("SELECT DISTINCT engine_code FROM vehicle_data", conn)
    df_y = pd.read_sql("SELECT name FROM junkyard_info", conn)
    
    total_cnt = conn.execute("SELECT COUNT(*) FROM vehicle_data").fetchone()[0]
    df_init = pd.read_sql("SELECT v.*, j.region, j.address FROM vehicle_data v LEFT JOIN junkyard_info j ON v.junkyard = j.name ORDER BY v.reg_date DESC LIMIT 5000", conn)
    
    conn.close()
    
    if not df_init.empty:
        df_init['model_year'] = pd.to_numeric(df_init['model_year'], errors='coerce').fillna(0)
        df_init['reg_date'] = pd.to_datetime(df_init['reg_date'], errors='coerce')
        
    return df_m, df_e['engine_code'].tolist(), df_y['name'].tolist(), df_init, total_cnt

def update_order_status(order_id, new_status):
    conn = init_db()
    conn.execute("UPDATE orders SET status = ? WHERE id = ?", (new_status, order_id))
    conn.commit()
    conn.close()

def reset_dashboard():
    # 리셋 시 초기 데이터 복구
    _, _, _, df_init, total = load_metadata_and_init_data()
    st.session_state['view_data'] = df_init
    st.session_state['total_count'] = total
    st.session_state['is_filtered'] = False
    st.session_state['mode_demand'] = False
    
    if 'msel' in st.session_state: st.session_state['msel'] = "All"
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

# 초기 로딩
if 'view_data' not in st.session_state or 'metadata_loaded' not in st.session_state:
    m_df, m_eng, m_yards, init_df, init_total = load_metadata_and_init_data()
    st.session_state['view_data'] = init_df
    st.session_state['total_count'] = init_total
    st.session_state['models_df'] = m_df
    st.session_state['engines_list'] = m_eng
    st.session_state['yards_list'] = m_yards
    st.session_state['metadata_loaded'] = True
    st.session_state['is_filtered'] = False
    st.session_state['mode_demand'] = False

df_raw = st.session_state['view_data']
total_records = st.session_state['total_count']
df_models = st.session_state['models_df']
list_engines = st.session_state['engines_list']
list_yards = st.session_state['yards_list']

# 1. 사이드바
with st.sidebar:
    st.title("K-Used Car Global Hub")
    
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
            del st.session_state['metadata_loaded'] # 재로딩 유도
            safe_rerun()

    st.divider()

    if st.session_state.user_role == 'admin':
        with st.expander("📂 Admin Tools"):
            up_files = st.file_uploader("Data Upload", type=['xlsx', 'xls', 'csv'], accept_multiple_files=True)
            if up_files and st.button("Save Data"):
                tot = 0
                bar = st.progress(0)
                for i, f in enumerate(up_files):
                    n, _ = save_vehicle_file(f)
                    tot += n
                    bar.progress((i+1)/len(up_files))
                st.success(f"{tot} records uploaded.")
                load_metadata_and_init_data.clear()
                safe_rerun()
            
            addr_file = st.file_uploader("Address DB", type=['xlsx', 'xls', 'csv'], key="a_up")
            if addr_file and st.button("Save Address"):
                cnt = save_address_file(addr_file)
                st.success(f"{cnt} addresses updated.")
                load_metadata_and_init_data.clear()
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
                load_metadata_and_init_data.clear()
                safe_rerun()
            
            st.divider()
            st.subheader("👑 Admin Menu")
            if st.button("🔮 Global Demand Analysis", use_container_width=True):
                st.session_state['mode_demand'] = True
                safe_rerun()

    st.subheader("🔍 Search Filter")
    search_tabs = st.tabs(["🚙 Vehicle", "🔧 Engine", "🏭 Yard"])
    
    with search_tabs[0]: 
        makers = sorted(df_models['manufacturer'].unique().tolist())
        makers.insert(0, "All")
        sel_maker = st.selectbox("Manufacturer", makers, key="msel")
        
        c1, c2 = st.columns(2)
        with c1: sel_sy = st.number_input("From", 1990, 2030, 2000, key="sy")
        with c2: sel_ey = st.number_input("To", 1990, 2030, 2025, key="ey")
        
        if sel_maker != "All":
            f_models = sorted(df_models[df_models['manufacturer'] == sel_maker]['model_name'].unique().tolist())
        else:
            f_models = sorted(df_models['model_name'].unique().tolist())
        sel_models = st.multiselect("Model", f_models, key="mms")
        
        if st.button("🔍 Search Vehicle", type="primary"):
            log_search(sel_models, 'model')
            res, tot = search_data_from_db(sel_maker, sel_models, [], sel_sy, sel_ey, [])
            st.session_state['view_data'] = res
            st.session_state['total_count'] = tot
            st.session_state['is_filtered'] = True
            st.session_state['mode_demand'] = False
            safe_rerun()

    with search_tabs[1]: 
        sel_engines = st.multiselect("Engine Code", sorted(list_engines), key="es")
        if st.button("🔍 Search Engine", type="primary"):
            log_search(sel_engines, 'engine')
            res, tot = search_data_from_db(None, [], sel_engines, 1990, 2030, [])
            st.session_state['view_data'] = res
            st.session_state['total_count'] = tot
            st.session_state['is_filtered'] = True
            st.session_state['mode_demand'] = False
            safe_rerun()

    with search_tabs[2]: 
        yard_opts = list_yards
        if st.session_state.user_role == 'buyer':
            yard_opts = sorted(list(set([generate_alias(name) for name in list_yards])))
        else:
            yard_opts = sorted(list_yards)
            
        sel_yards = st.multiselect("Partner Name", yard_opts, key="ys")
        
        if st.button("🔍 Search Partner", type="primary"):
            real_yard_names = []
            if st.session_state.user_role == 'buyer':
                for y in list_yards:
                    if generate_alias(y) in sel_yards:
                        real_yard_names.append(y)
            else:
                real_yard_names = sel_yards
                
            res, tot = search_data_from_db(None, [], [], 1990, 2030, real_yard_names)
            st.session_state['view_data'] = res
            st.session_state['total_count'] = tot
            st.session_state['is_filtered'] = True
            st.session_state['mode_demand'] = False
            safe_rerun()

    if st.button("🔄 Reset Filters", use_container_width=True, on_click=reset_dashboard):
        pass

# 2. 메인 화면
if st.session_state.mode_demand and st.session_state.user_role == 'admin':
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
    st.title("K-Used Car/Engine Inventory")
    
    df_view = st.session_state['view_data']
    total_cnt = st.session_state['total_count']
    
    df_display = mask_dataframe(df_view, st.session_state.user_role)
    
    if st.session_state.user_role == 'admin':
        main_tabs = st.tabs(["📊 Inventory", "📩 Orders"])
    else:
        main_tabs = st.tabs(["📊 Search Results", "🛒 My Orders"])

    with main_tabs[0]:
        if df_display.empty:
            if st.session_state['is_filtered']:
                st.warning("No results found.")
            else:
                st.info("Please select filters from the sidebar to search.")
        else:
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Vehicles", f"{total_cnt:,} EA")
            c2.metric("Matched Engines", f"{df_display['engine_code'].nunique()} Types")
            sup_label = "Real Junkyards" if st.session_state.user_role == 'admin' else "Partners"
            c3.metric(sup_label, f"{df_display['junkyard'].nunique()} EA")
            
            if total_cnt > 5000:
                st.warning(f"⚠️ Showing top 5,000 results out of {total_cnt:,}. Please refine your filters.")
            
            st.divider()
            st.subheader("📦 Stock by Partner")
            
            grp_cols = ['junkyard', 'address']
            if st.session_state.user_role == 'admin' and 'region' in df_display.columns:
                grp_cols.append('region')
            
            if 'address' in df_display.columns:
                df_display['address'] = df_display['address'].fillna("Unknown")

            stock_summary = df_display.groupby(grp_cols).size().reset_index(name='qty').sort_values('qty', ascending=False)
            selection = st.dataframe(stock_summary, use_container_width=True, hide_index=True, selection_mode="single-row", on_select="rerun")
            
            # 견적 요청 폼
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
                                        temp_df = df_view.copy()
                                        temp_df['alias'] = temp_df['junkyard'].apply(generate_alias)
                                        match = temp_df[temp_df['alias'] == target_partner]
                                        if not match.empty:
                                            real_name = match['junkyard'].iloc[0]
                                    except: real_name = "Unknown"

                                summary = f"Qty: {req_qty} (Total Stock: {stock_cnt}), Item: {item}, Price: {offer}, Msg: {msg}"
                                cur.execute("INSERT INTO orders (buyer_id, contact_info, target_partner_alias, real_junkyard_name, items_summary, status) VALUES (?, ?, ?, ?, ?, ?)",
                                            (buyer_name, contact, target_partner, real_name, summary, 'PENDING'))
                                conn.commit()
                                conn.close()
                                st.success("✅ Inquiry has been sent to our sales team.")

            st.divider()
            st.subheader("📋 Item List")
            st.dataframe(df_display, use_container_width=True)

    if st.session_state.user_role == 'admin':
        with main_tabs[1]:
            st.subheader("📩 Incoming Quote Requests")
            conn = init_db()
            orders = pd.read_sql("SELECT * FROM orders ORDER BY created_at DESC", conn)
            conn.close()
            
            if not orders.empty:
                for idx, row in orders.iterrows():
                    with st.expander(f"[{row['status']}] {row['created_at']} | From: {row['buyer_id']}"):
                        st.write(f"**Contact:** {row['contact_info']}")
                        st.write(f"**Target:** {row['real_junkyard_name']} ({row['target_partner_alias']})")
                        st.info(f"**Request:** {row['items_summary']}")
                        
                        c1, c2 = st.columns([3, 1])
                        with c1:
                            new_status = st.selectbox("Change Status", 
                                                      ["PENDING", "QUOTED", "PAID", "PROCESSING", "SHIPPING", "DONE", "CANCELLED"],
                                                      index=["PENDING", "QUOTED", "PAID", "PROCESSING", "SHIPPING", "DONE", "CANCELLED"].index(row['status']),
                                                      key=f"st_{row['id']}")
                        with c2:
                            st.write("")
                            st.write("")
                            if st.button("Update", key=f"btn_{row['id']}"):
                                update_order_status(row['id'], new_status)
                                st.success("Updated!")
                                time.sleep(0.5)
                                safe_rerun()
            else:
                st.info("No pending orders.")

    if st.session_state.user_role == 'buyer':
        with main_tabs[1]: # My Orders
            st.subheader("🛒 My Quote Requests")
            conn = init_db()
            my_orders = pd.read_sql("SELECT * FROM orders WHERE buyer_id = ? ORDER BY created_at DESC", conn, params=(st.session_state.username,))
            conn.close()

            if not my_orders.empty:
                for idx, row in my_orders.iterrows():
                    status_color = "green" if row['status'] == 'DONE' else "orange" if row['status'] == 'PENDING' else "blue"
                    with st.expander(f"[{row['created_at']}] {row['target_partner_alias']} ({row['status']})"):
                        st.caption(f"Status: :{status_color}[{row['status']}]")
                        st.write(f"**Request Details:** {row['items_summary']}")
                        if row['status'] == 'QUOTED':
                            st.success("💬 Offer Received! Check your email/phone.")
            else:
                st.info("You haven't requested any quotes yet.")

except Exception as e:
    st.error("⛔ 앱 실행 중 문제가 발생했습니다.")
    with st.expander("상세 오류 보기"):
        st.code(traceback.format_exc())
