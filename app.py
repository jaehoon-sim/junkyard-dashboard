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

# ---------------------------------------------------------
# 🛠️ [설정] 페이지 및 유틸
# ---------------------------------------------------------
st.set_page_config(page_title="폐차 관제 시스템 Pro", layout="wide")

def safe_rerun():
    try:
        st.rerun()
    except AttributeError:
        st.experimental_rerun()

# ---------------------------------------------------------
# 🔐 [보안] 관리자 계정 & API 키
# ---------------------------------------------------------
try:
    ADMIN_CREDENTIALS = st.secrets["ADMIN_CREDENTIALS"]
    NAVER_CLIENT_ID = st.secrets["NAVER_CLIENT_ID"]
    NAVER_CLIENT_SECRET = st.secrets["NAVER_CLIENT_SECRET"]
except:
    ADMIN_CREDENTIALS = {"admin": "1234"}
    NAVER_CLIENT_ID = "aic55XK2RCthRyeMMlJM"
    NAVER_CLIENT_SECRET = "ZqOAIOzYGf"

DB_NAME = 'junkyard.db'

# 📍 전국 시/군/구 단위 상세 좌표 데이터베이스
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

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS vehicle_data (vin TEXT PRIMARY KEY, reg_date TEXT, car_no TEXT, manufacturer TEXT, model_name TEXT, model_year REAL, junkyard TEXT, engine_code TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS junkyard_info (name TEXT PRIMARY KEY, address TEXT, region TEXT, lat REAL, lon REAL, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS model_list (manufacturer TEXT, model_name TEXT, PRIMARY KEY (manufacturer, model_name))''')
    
    # 인덱스 최적화
    c.execute("CREATE INDEX IF NOT EXISTS idx_mfr ON vehicle_data(manufacturer)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_model ON vehicle_data(model_name)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_engine ON vehicle_data(engine_code)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_yard ON vehicle_data(junkyard)")
    conn.commit()
    return conn

# ---------------------------------------------------------
# [성능최적화] 데이터프레임 경량화 함수
# ---------------------------------------------------------
def optimize_dataframe(df):
    for col in df.select_dtypes(include=['object']).columns:
        num_unique_values = len(df[col].unique())
        num_total_values = len(df[col])
        if num_total_values > 0 and num_unique_values / num_total_values < 0.5:
            df[col] = df[col].astype('category')
    return df

def clean_junkyard_name(name):
    cleaned = re.sub(r'\(주\)|주식회사|\(유\)|합자회사|유한회사', '', str(name))
    cleaned = re.sub(r'지점', '', cleaned) 
    return cleaned.strip()

def search_place_naver(query):
    cleaned_name = clean_junkyard_name(query)
    search_queries = [query]
    if '폐차' not in cleaned_name and len(cleaned_name) < 5: search_queries.append(f"{cleaned_name} 폐차장")
    if len(cleaned_name) > 1: search_queries.append(cleaned_name)

    url = "https://openapi.naver.com/v1/search/local.json"
    headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}

    for q in search_queries:
        try:
            params = {"query": q, "display": 1, "sort": "random"}
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200:
                items = response.json().get('items')
                if items:
                    address = items[0]['address']
                    addr_parts = address.split()
                    short_region = ""
                    if len(addr_parts) >= 2:
                        si_do = addr_parts[0][:2]
                        si_gun = addr_parts[1]
                        if si_do in ['서울', '인천', '대전', '대구', '광주', '부산', '울산', '세종', '제주']: short_region = si_do
                        else:
                            gun_name = si_gun.replace('시','').replace('군','').replace('구','')
                            if len(gun_name) < 1: gun_name = si_gun
                            temp_key = f"{si_do} {gun_name}"
                            for k in CITY_COORDS.keys():
                                if temp_key in k or k in f"{si_do} {si_gun}": short_region = k; break
                            if not short_region: short_region = f"{si_do} {si_gun}"
                    else: short_region = addr_parts[0][:2]

                    lat, lon = 0.0, 0.0
                    if short_region in CITY_COORDS: lat, lon = CITY_COORDS[short_region]
                    else:
                        for k, v in CITY_COORDS.items():
                            if k in address: short_region = k; lat, lon = v; break
                    return {'address': address, 'region': short_region, 'lat': lat, 'lon': lon}
        except: continue
    return None

def update_single_junkyard(conn, yard_name):
    info = search_place_naver(yard_name)
    c = conn.cursor()
    if info:
        c.execute("INSERT OR REPLACE INTO junkyard_info (name, address, region, lat, lon) VALUES (?, ?, ?, ?, ?)", (yard_name, info['address'], info['region'], info['lat'], info['lon']))
        conn.commit()
        return True, info['address']
    else:
        c.execute("INSERT OR REPLACE INTO junkyard_info (name, address, region, lat, lon) VALUES (?, ?, ?, ?, ?)", (yard_name, '검색실패', '기타', 0.0, 0.0))
        conn.commit()
        return False, "검색실패"

# ⚡ [통합] 대량 파일 저장 함수 (이름 통일됨)
def save_vehicle_file(uploaded_file):
    try:
        if uploaded_file.name.endswith('.csv'): 
            df = pd.read_csv(uploaded_file, dtype=str)
        else: 
            try: df = pd.read_excel(uploaded_file, engine='openpyxl', dtype=str)
            except: df = pd.read_excel(uploaded_file, engine='xlrd', dtype=str)

        if '차대번호' not in df.columns:
            if uploaded_file.name.endswith('.csv'): 
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, header=2, dtype=str)
            else: 
                try: df = pd.read_excel(uploaded_file, header=2, engine='openpyxl', dtype=str)
                except: df = pd.read_excel(uploaded_file, header=2, engine='xlrd', dtype=str)
        
        df.columns = [str(c).strip() for c in df.columns]
        required = ['등록일자', '차량번호', '차대번호', '제조사', '차량명', '회원사', '원동기형식']
        missing = [c for c in required if c not in df.columns]
        if missing:
            st.error(f"필수 컬럼 누락: {missing}")
            return 0, 0

        conn = init_db()
        c = conn.cursor()
        
        # 데이터프레임 생성
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

        # Bulk Insert
        df_db.to_sql('temp_vehicles', conn, if_exists='replace', index=False)
        c.execute("""
            INSERT OR IGNORE INTO vehicle_data (vin, reg_date, car_no, manufacturer, model_name, model_year, junkyard, engine_code)
            SELECT vin, reg_date, car_no, manufacturer, model_name, model_year, junkyard, engine_code FROM temp_vehicles
        """)
        
        new_cnt = len(df_db)
        c.execute("DROP TABLE temp_vehicles")
        
        # 모델 리스트 업데이트
        model_list_df = df_db[['manufacturer', 'model_name']].drop_duplicates()
        model_list_df.to_sql('temp_models', conn, if_exists='replace', index=False)
        c.execute("INSERT OR IGNORE INTO model_list (manufacturer, model_name) SELECT manufacturer, model_name FROM temp_models")
        c.execute("DROP TABLE temp_models")
        
        # 신규 폐차장 등록 (주소 없음 상태)
        unique_yards = df_db['junkyard'].unique().tolist()
        for yard in unique_yards:
             c.execute("INSERT OR IGNORE INTO junkyard_info (name, address, region, lat, lon) VALUES (?, ?, ?, ?, ?)", 
                      (yard, '검색실패', '기타', 0.0, 0.0))

        conn.commit()
        conn.close()
        
        del df, df_db
        gc.collect()
        
        return new_cnt, 0
    except Exception as e:
        st.error(f"파일 처리 오류: {e}")
        return 0, 0

def save_address_file(uploaded_file):
    try:
        if uploaded_file.name.endswith('.csv'): df = pd.read_csv(uploaded_file)
        else: 
            try: df = pd.read_excel(uploaded_file, engine='openpyxl')
            except: df = pd.read_excel(uploaded_file, engine='xlrd')
        
        name_col = next((c for c in df.columns if '폐차장' in c or '업체' in c or '회원' in c), None)
        addr_col = next((c for c in df.columns if '주소' in c or '소재' in c), None)
        
        if not name_col or not addr_col: return 0

        conn = init_db()
        c = conn.cursor()
        update_cnt = 0
        
        for _, row in df.iterrows():
            yard_name = str(row[name_col]).strip()
            address = str(row[addr_col]).strip()
            
            region = '기타'
            addr_parts = address.split()
            if len(addr_parts) >= 2:
                si_do = addr_parts[0][:2]
                si_gun = addr_parts[1]
                if si_do in ['서울', '인천', '대전', '대구', '광주', '부산', '울산', '제주', '세종']: region = si_do
                else:
                    gun_name = si_gun.replace('시','').replace('군','').replace('구','')
                    if len(gun_name) < 1: gun_name = si_gun
                    temp_key = f"{si_do} {gun_name}"
                    for k in CITY_COORDS.keys():
                        if temp_key in k or k in f"{si_do} {si_gun}": region = k; break
            
            lat, lon = 0.0, 0.0
            if region in CITY_COORDS: lat, lon = CITY_COORDS[region]
            
            c.execute("INSERT OR REPLACE INTO junkyard_info (name, address, region, lat, lon) VALUES (?, ?, ?, ?, ?)", (yard_name, address, region, lat, lon))
            update_cnt += 1
            
        conn.commit()
        conn.close()
        return update_cnt
    except: return 0

@st.cache_data(ttl=300)
def load_all_data():
    try:
        conn = init_db()
        query = "SELECT v.*, j.region, j.lat, j.lon, j.address FROM vehicle_data v LEFT JOIN junkyard_info j ON v.junkyard = j.name"
        df = pd.read_sql(query, conn)
        conn.close()
        if not df.empty:
            df['model_name'] = df['model_name'].astype(str)
            df['manufacturer'] = df['manufacturer'].astype(str)
            df['engine_code'] = df['engine_code'].astype(str)
            df['junkyard'] = df['junkyard'].astype(str)
            df['model_year'] = pd.to_numeric(df['model_year'], errors='coerce').fillna(0)
            df['reg_date'] = pd.to_datetime(df['reg_date'], errors='coerce')
            df = optimize_dataframe(df)
        return df
    except Exception: return pd.DataFrame()

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

def load_yard_list():
    try:
        conn = init_db()
        df = pd.read_sql("SELECT name FROM junkyard_info ORDER BY name", conn)
        conn.close()
        return df['name'].tolist()
    except: return []

# ---------------------------------------------------------
# 메인 로직
# ---------------------------------------------------------
try:
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    
    if 'view_data' not in st.session_state: 
        st.session_state['view_data'] = pd.DataFrame()
        st.session_state['is_filtered'] = False

    df_models = load_model_list()
    list_engines = load_engine_list()
    list_yards = load_yard_list()
    # 전체 데이터는 여기서 로드하지 않음 (캐시된 것 사용)
    
    with st.sidebar:
        st.title("🛠️ 컨트롤 패널")
        
        if not st.session_state.logged_in:
            with st.expander("🔐 관리자 로그인", expanded=True):
                uid = st.text_input("ID")
                upw = st.text_input("PW", type="password")
                if st.button("로그인"):
                    if uid in ADMIN_CREDENTIALS and ADMIN_CREDENTIALS[uid] == upw:
                        st.session_state.logged_in = True
                        st.success("성공")
                        safe_rerun()
                    else: st.error("실패")
        else:
            st.success("👑 관리자 접속")
            if st.button("로그아웃"):
                st.session_state.logged_in = False
                safe_rerun()
        
        st.divider()

        with st.expander("📂 차량 데이터 업로드"):
            up_files = st.file_uploader("파일 선택", type=['xlsx', 'xls', 'csv'], accept_multiple_files=True, key="v_up")
            if up_files and st.button("DB 저장"):
                if st.session_state.logged_in:
                    total_n = 0
                    bar = st.progress(0)
                    for i, f in enumerate(up_files):
                        n, _ = save_vehicle_file(f)
                        total_n += n
                        bar.progress((i+1)/len(up_files))
                    bar.empty()
                    st.success(f"{total_n}건 저장 완료")
                    load_all_data.clear() 
                    safe_rerun()
                else: st.warning("권한 없음")

        with st.expander("🏢 주소 DB 업로드"):
            addr_file = st.file_uploader("주소 파일", type=['xlsx', 'xls', 'csv'], key="a_up")
            if addr_file and st.button("주소 저장"):
                if st.session_state.logged_in:
                    cnt = save_address_file(addr_file)
                    st.success(f"{cnt}곳 주소 저장")
                    load_all_data.clear()
                    safe_rerun()
                else: st.warning("권한 없음")

        st.divider()
        
        search_tabs = st.tabs(["🚙 차량", "🔧 엔진", "🏭 폐차장"])
        
        with search_tabs[0]:
            if not df_models.empty:
                makers = sorted(df_models['manufacturer'].unique().tolist())
                makers.insert(0, "전체")
                sel_maker = st.selectbox("제조사", makers, key="msel")
                
                current_year = datetime.datetime.now().year
                year_opts = list(range(1990, current_year + 2))
                c1, c2 = st.columns(2)
                with c1: sel_sy = st.selectbox("시작", year_opts, index=year_opts.index(2000), key="sy")
                with c2: sel_ey = st.selectbox("종료", year_opts, index=len(year_opts)-1, key="ey")
                
                if sel_maker != "전체":
                    f_models = sorted(df_models[df_models['manufacturer'] == sel_maker]['model_name'].tolist())
                else:
                    f_models = sorted(df_models['model_name'].unique().tolist())
                
                sel_models = st.multiselect(f"모델 ({len(f_models)}개)", f_models, key="mms")
                
                st.markdown("")
                if st.button("✅ 차량 검색 적용", type="primary", use_container_width=True):
                    full_df = load_all_data()
                    if sel_maker != "전체": full_df = full_df[full_df['manufacturer'] == sel_maker]
                    full_df = full_df[(full_df['model_year'] >= sel_sy) & (full_df['model_year'] <= sel_ey)]
                    if sel_models: full_df = full_df[full_df['model_name'].isin(sel_models)]
                    st.session_state['view_data'] = full_df.reset_index(drop=True)
                    st.session_state['is_filtered'] = True
                    safe_rerun()

        with search_tabs[1]:
            if list_engines:
                sel_engines = st.multiselect("엔진코드", list_engines, key="es")
                st.markdown("")
                if st.button("🔧 엔진 검색 적용", type="primary", use_container_width=True):
                    full_df = load_all_data()
                    if sel_engines: full_df = full_df[full_df['engine_code'].isin(sel_engines)]
                    st.session_state['view_data'] = full_df.reset_index(drop=True)
                    st.session_state['is_filtered'] = True
                    safe_rerun()

        with search_tabs[2]:
            if list_yards:
                sel_yards = st.multiselect("폐차장 이름", list_yards, key="ys")
                st.markdown("")
                if st.button("🏭 폐차장 검색 적용", type="primary", use_container_width=True):
                    full_df = load_all_data()
                    if sel_yards: full_df = full_df[full_df['junkyard'].isin(sel_yards)]
                    st.session_state['view_data'] = full_df.reset_index(drop=True)
                    st.session_state['is_filtered'] = True
                    safe_rerun()
        
        if st.button("🔄 전체 목록 보기 (메모리 주의)", use_container_width=True):
            st.session_state['view_data'] = load_all_data()
            st.session_state['is_filtered'] = False
            safe_rerun()

        if st.session_state.logged_in:
            st.divider()
            if st.button("🗑️ DB 초기화"):
                try:
                    conn = init_db()
                    c = conn.cursor()
                    c.execute("DROP TABLE vehicle_data")
                    c.execute("DROP TABLE junkyard_info")
                    c.execute("DROP TABLE model_list")
                    conn.commit()
                    conn.close()
                    load_all_data.clear()
                    st.session_state['view_data'] = pd.DataFrame()
                    st.success("완료")
                    safe_rerun()
                except: pass

    # 메인 화면
    st.title("🚗 전국 폐차장 실시간 재고 현황")
    
    df_view = st.session_state['view_data']
    is_filtered = st.session_state['is_filtered']

    if df_view.empty:
        st.info("👈 좌측 패널에서 검색 조건을 선택하고 **[적용]** 버튼을 눌러주세요.")
    
    else:
        # 마스킹
        if not st.session_state.logged_in:
            df_view = df_view.copy()
            df_view['junkyard'] = "🔒 회원전용"
            df_view['address'] = "🔒 비공개"
            df_view['region'] = "🔒"
            df_view['vin'] = "🔒 비공개"
            df_view['lat'] = 0.0
            df_view['lon'] = 0.0

        mode = "🔍 검색 결과" if is_filtered else "📊 전체 현황"
        st.caption(f"모드: {mode} | 데이터: {len(df_view):,}건")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("조회된 재고", f"{len(df_view):,}대")
        
        conn = init_db()
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        try: today_cnt = pd.read_sql(f"SELECT COUNT(*) as cnt FROM vehicle_data WHERE reg_date LIKE '{today}%'", conn)['cnt'][0]
        except: today_cnt = 0
        conn.close()
        
        c2.metric("오늘 전체 입고", f"{today_cnt}대")
        c3.metric("관련 업체", "🔒" if not st.session_state.logged_in else f"{df_view['junkyard'].nunique()}곳")
        
        if st.session_state.logged_in and 'region' in df_view.columns and not df_view['region'].empty:
            c4.metric("최다 지역", df_view['region'].mode()[0])
        else: c4.metric("최다 지역", "🔒")

        st.divider()
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.subheader("📍 위치 분포")
            if st.session_state.logged_in:
                map_df = df_view[(df_view['lat'] != 0.0) & (df_view['lat'].notnull())]
                if not map_df.empty:
                    try:
                        map_agg = map_df.groupby(['junkyard', 'region', 'lat', 'lon']).size().reset_index(name='count')
                        fig = px.scatter_mapbox(
                            map_agg, lat="lat", lon="lon", size="count", color="count",
                            hover_name="junkyard", zoom=6.5, center={"lat": 36.5, "lon": 127.8},
                            mapbox_style="carto-positron", color_continuous_scale="Reds", size_max=50
                        )
                        fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
                        st.plotly_chart(fig, use_container_width=True)
                    except Exception as e: st.error("지도 오류")
                else: st.warning("위치 데이터 없음 (주소 DB를 업로드해주세요)")
            else:
                st.warning("🔒 지도는 관리자(회원) 전용입니다.")

        with col2:
            st.subheader("🏭 보유량 TOP")
            if 'junkyard' in df_view.columns:
                top_yards = df_view.groupby(['junkyard']).size().reset_index(name='수량').sort_values('수량', ascending=False).head(15)
                st.dataframe(top_yards, width=None, use_container_width=True, hide_index=True, height=400)

        st.divider()

        if 'reg_date' in df_view.columns:
            st.subheader("📈 월별 입고 추이")
            monthly_data = df_view.dropna(subset=['reg_date']).copy()
            if not monthly_data.empty:
                monthly_data['month_str'] = monthly_data['reg_date'].dt.month.astype(str) + '월'
                monthly_data['sort_key'] = monthly_data['reg_date'].dt.strftime('%Y-%m')
                monthly_counts = monthly_data.groupby(['sort_key', 'month_str']).size().reset_index(name='입고량').sort_values('sort_key')
                fig_bar = px.bar(monthly_counts, x='month_str', y='입고량', text='입고량', color='입고량')
                fig_bar.update_layout(xaxis_title=None, coloraxis_showscale=False)
                st.plotly_chart(fig_bar, use_container_width=True)
        
        st.divider()
        
        if is_filtered:
            st.subheader("📑 견적 요청 & 주소 관리")
            
            view_copy = df_view.copy()
            if st.session_state.logged_in:
                view_copy['address'] = view_copy['address'].fillna('🔍 조회 필요').replace('검색실패', '🔍 조회 필요')
            
            yard_summary = view_copy.groupby(['junkyard', 'region', 'address']).size().reset_index(name='보유수량').sort_values('보유수량', ascending=False)
            
            selection = st.dataframe(
                yard_summary,
                width=None, use_container_width=True, hide_index=True, 
                selection_mode="single-row", on_select="rerun"
            )
            
            if len(selection.selection.rows) > 0:
                sel_idx = selection.selection.rows[0]
                sel_row = yard_summary.iloc[sel_idx]
                target_yard = sel_row['junkyard']
                current_addr = sel_row['address']
                
                if st.session_state.logged_in and "조회 필요" in str(current_addr):
                     if st.button(f"🔄 '{target_yard}' 주소 검색 실행"):
                        conn = init_db()
                        with st.spinner("주소 찾는 중..."):
                            success, new_addr = update_single_junkyard(conn, target_yard)
                        conn.close()
                        if success:
                            st.success(f"성공! ({new_addr})")
                            load_all_data.clear()
                            st.session_state['view_data'] = load_all_data() # 재로드
                            safe_rerun()
                        else: st.error("실패")

                st.info(f"📩 **{target_yard}**에 견적 요청")
                with st.form("quote"):
                    c_a, c_b = st.columns(2)
                    with c_a: 
                        st.text_input("수신", value=target_yard, disabled=True)
                        st.text_input("연락처", placeholder="010-0000-0000")
                    with c_b:
                        st.text_input("품목", value=f"검색 결과 {len(df_view)}건 관련")
                        st.text_input("희망가", placeholder="금액 입력")
                    st.text_area("내용", value=f"{target_yard} 사장님, 보유하신 {sel_row['보유수량']}대에 대한 견적 문의드립니다.", height=100)
                    if st.form_submit_button("전송"): st.toast("완료!", icon="📨")

            st.subheader("📋 차량 목록")
            cols = ['reg_date', 'manufacturer', 'model_name', 'model_year', 'engine_code', 'junkyard', 'address', 'vin']
            valid_cols = [c for c in cols if c in df_view.columns]
            st.dataframe(df_view[valid_cols].sort_values('reg_date', ascending=False), width=None, use_container_width=True)
        else:
            c_a, c_b = st.columns(2)
            with c_a:
                st.subheader("🔥 엔진 TOP 10")
                eng_d = df_view['engine_code'].value_counts().head(10).reset_index()
                eng_d.columns = ['코드', '수량']
                f_eng = px.bar(eng_d, x='코드', y='수량', text='수량', color='수량')
                f_eng.update_layout(xaxis_tickangle=0, coloraxis_showscale=False)
                st.plotly_chart(f_eng, use_container_width=True)
            with c_b:
                st.subheader("🚙 모델 TOP 10")
                mod_d = df_view['model_name'].value_counts().head(10).reset_index()
                mod_d.columns = ['모델', '수량']
                f_mod = px.bar(mod_d, x='모델', y='수량', text='수량', color='수량')
                f_mod.update_layout(xaxis_tickangle=0, coloraxis_showscale=False)
                st.plotly_chart(f_mod, use_container_width=True)

except Exception as e:
    st.error("⛔ 앱 실행 중 문제가 발생했습니다.")
    with st.expander("상세 오류 보기"):
        st.code(traceback.format_exc())
