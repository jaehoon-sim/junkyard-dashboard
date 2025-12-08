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
# 1. 데이터베이스 초기화 (lat, lon 제거됨)
# ---------------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # 1. 차량 데이터
    c.execute('''CREATE TABLE IF NOT EXISTS vehicle_data (
        vin TEXT PRIMARY KEY, 
        reg_date TEXT, 
        car_no TEXT, 
        manufacturer TEXT, 
        model_name TEXT, 
        model_year REAL, 
        junkyard TEXT, 
        engine_code TEXT, 
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # 2. 폐차장 정보 (좌표 제거, 지역/주소만 유지)
    c.execute('''CREATE TABLE IF NOT EXISTS junkyard_info (
        name TEXT PRIMARY KEY, 
        address TEXT, 
        region TEXT, 
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # 3. 모델 목록
    c.execute('''CREATE TABLE IF NOT EXISTS model_list (
        manufacturer TEXT, 
        model_name TEXT, 
        PRIMARY KEY (manufacturer, model_name)
    )''')
    
    # 4. 검색 로그 (좌표 제거)
    c.execute('''CREATE TABLE IF NOT EXISTS search_logs_v2 (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        keyword TEXT, 
        search_type TEXT, 
        country TEXT, 
        city TEXT, 
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # 5. 주문(견적)
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        buyer_id TEXT,
        target_partner_alias TEXT,
        real_junkyard_name TEXT,
        items_summary TEXT,
        status TEXT DEFAULT 'PENDING',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # 인덱스
    c.execute("CREATE INDEX IF NOT EXISTS idx_mfr ON vehicle_data(manufacturer)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_model ON vehicle_data(model_name)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_engine ON vehicle_data(engine_code)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_yard ON vehicle_data(junkyard)")
    conn.commit()
    return conn

# ---------------------------------------------------------
# 🕵️ [직거래 방지] 데이터 마스킹
# ---------------------------------------------------------
def generate_alias(real_name):
    if not isinstance(real_name, str): return "Unknown"
    hash_object = hashlib.md5(str(real_name).encode())
    hash_int = int(hash_object.hexdigest(), 16) % 900 + 100 
    return f"Partner #{hash_int}"

def mask_dataframe(df, role):
    if df.empty: return df
    df_safe = df.copy()
    
    if role == 'admin':
        if 'junkyard' in df_safe.columns:
            df_safe['partner_alias'] = df_safe['junkyard'].apply(generate_alias)
        return df_safe

    # 업체명 마스킹
    if 'junkyard' in df_safe.columns:
        df_safe['real_junkyard'] = df_safe['junkyard']
        if role == 'buyer':
            df_safe['junkyard'] = df_safe['junkyard'].apply(generate_alias)
        else:
            df_safe['junkyard'] = "🔒 Login Required"

    # 주소 마스킹
    def simplify_address(addr):
        s = str(addr)
        if '경기' in s: return 'Gyeonggi-do, Korea'
        if '인천' in s: return 'Incheon, Korea'
        if '서울' in s: return 'Seoul, Korea'
        if '경남' in s or '부산' in s: return 'Busan/Gyeongnam, Korea'
        return 'South Korea'
    
    if 'address' in df_safe.columns:
        if role == 'buyer':
            df_safe['address'] = df_safe['address'].apply(simplify_address)
        else:
            df_safe['address'] = "🔒 Login Required"

    # 민감정보 제거
    if 'vin' in df_safe.columns:
        df_safe['vin'] = df_safe['vin'].astype(str).apply(lambda x: x[:8] + "****" if len(x) > 8 else "****")
    
    if 'car_no' in df_safe.columns:
        df_safe = df_safe.drop(columns=['car_no'], errors='ignore')
    
    if 'real_junkyard' in df_safe.columns:
        df_safe = df_safe.drop(columns=['real_junkyard'], errors='ignore')

    return df_safe

# ---------------------------------------------------------
# 기능 함수들
# ---------------------------------------------------------
def log_search(keywords, s_type):
    if not keywords: return
    try:
        conn = init_db()
        c = conn.cursor()
        # IP 기반 위치 추적 (간소화)
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

        # 폐차장 정보 등록 (주소 없음 상태)
        unique_yards = df_db['junkyard'].unique().tolist()
        for yard in unique_yards:
            c.execute("INSERT OR IGNORE INTO junkyard_info (name, address, region) VALUES (?, ?, ?)", (yard, '주소없음', '기타'))
            
        conn.commit()
        conn.close()
        return cnt, 0
    except: return 0, 0

def save_address_file(uploaded_file):
    """주소 엑셀 업로드 (좌표 없이 주소만 저장)"""
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
            
            # 지역명 파싱
            addr_parts = address.split()
            region = addr_parts[0][:2] if len(addr_parts) > 0 else '기타'
            
            c.execute("INSERT OR REPLACE INTO junkyard_info (name, address, region) VALUES (?, ?, ?)", (yard_name, address, region))
            update_cnt += 1
            
        conn.commit()
        conn.close()
        return update_cnt
    except: return 0

def update_single_junkyard(conn, yard_name):
    """네이버 API로 주소 텍스트만 업데이트 (좌표 X)"""
    # 네이버 API 호출 로직 (주소 텍스트 확보용)
    cleaned_name = re.sub(r'\(주\)|주식회사|\(유\)|합자회사|유한회사', '', str(yard_name)).strip()
    search_query = cleaned_name + " 폐차장"
    
    url = "https://openapi.naver.com/v1/search/local.json"
    headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
    
    try:
        resp = requests.get(url, headers=headers, params={"query": search_query, "display": 1, "sort": "random"})
        if resp.status_code == 200:
            items = resp.json().get('items')
            if items:
                address = items[0]['address']
                region = address.split()[0][:2]
                
                c = conn.cursor()
                c.execute("INSERT OR REPLACE INTO junkyard_info (name, address, region) VALUES (?, ?, ?)", (yard_name, address, region))
                conn.commit()
                return True, address
    except: pass
    
    # 실패 시
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO junkyard_info (name, address, region) VALUES (?, ?, ?)", (yard_name, '검색실패', '기타'))
    conn.commit()
    return False, "검색실패"

@st.cache_data(ttl=300)
def load_all_data():
    try:
        conn = init_db()
        # lat, lon 제거됨
        query = "SELECT v.*, j.region, j.address FROM vehicle_data v LEFT JOIN junkyard_info j ON v.junkyard = j.name"
        df = pd.read_sql(query, conn)
        conn.close()
        if not df.empty:
            df['model_year'] = pd.to_numeric(df['model_year'], errors='coerce').fillna(0)
            df['reg_date'] = pd.to_datetime(df['reg_date'], errors='coerce')
            
            # 최적화
            for col in df.select_dtypes(include=['object']).columns:
                if len(df[col].unique()) / len(df) < 0.5:
                    df[col] = df[col].astype('category')
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
        if role == 'admin': return real_names
        elif role == 'buyer': return sorted(list(set([generate_alias(name) for name in real_names])))
        return []
    except: return []

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
            if up_files and st.button("Save Data"):
                tot = 0
                bar = st.progress(0)
                for i, f in enumerate(up_files):
                    n, _ = save_vehicle_file(f)
                    tot += n
                    bar.progress((i+1)/len(up_files))
                st.success(f"{tot} records uploaded.")
                load_all_data.clear()
                safe_rerun()
            
            addr_file = st.file_uploader("Address Upload", type=['xlsx', 'xls', 'csv'])
            if addr_file and st.button("Save Address"):
                cnt = save_address_file(addr_file)
                st.success(f"{cnt} addresses updated.")
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
            sel_models = st.multiselect("Model", f_models)
            
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
            sel_yards = st.multiselect("Partner Name", filter_yards)
            if st.button("🔍 Search Partner", type="primary"):
                res = load_all_data()
                if sel_yards:
                    # 마스킹 처리 전 원본에서 필터링
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

    if st.button("🔄 Reset Filters", use_container_width=True):
        st.session_state['view_data'] = load_all_data()
        st.session_state['is_filtered'] = False
        st.session_state['mode_demand'] = False
        safe_rerun()

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
            
            if len(selection.selection.rows) > 0:
                sel_idx = selection.selection.rows[0]
                sel_row = stock_summary.iloc[sel_idx]
                target_partner = sel_row['junkyard']
                stock_cnt = sel_row['qty']
                
                # 주소 업데이트 버튼 (관리자 전용 & 주소 없을때)
                if st.session_state.user_role == 'admin':
                    current_addr = sel_row['address']
                    if "검색실패" in str(current_addr) or "주소없음" in str(current_addr):
                        if st.button(f"🔄 '{target_partner}' Address Update"):
                            conn = init_db()
                            with st.spinner("Searching..."):
                                success, new_addr = update_single_junkyard(conn, target_partner)
                            conn.close()
                            if success:
                                st.success(f"Updated: {new_addr}")
                                load_all_data.clear()
                                time.sleep(1)
                                safe_rerun()
                            else: st.error("Failed.")

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
                            item = st.text_input("Item *", value=f"Selected {stock_cnt} items from search")
                            offer = st.text_input("Target Unit Price (USD) *", placeholder="e.g. $500/ea")
                        
                        msg = st.text_area("Message to Admin", height=80, placeholder="Details...")
                        
                        if st.form_submit_button("🚀 Send Inquiry"):
                            if not contact or not item or not offer:
                                st.error("⚠️ Please fill in Contact, Item, and Price.")
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
