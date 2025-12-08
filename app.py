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
# 🔐 [보안] 계정 설정 (관리자 vs 바이어)
# ---------------------------------------------------------
try:
    ADMIN_CREDENTIALS = st.secrets["ADMIN_CREDENTIALS"]
    NAVER_CLIENT_ID = st.secrets["NAVER_CLIENT_ID"]
    NAVER_CLIENT_SECRET = st.secrets["NAVER_CLIENT_SECRET"]
except:
    ADMIN_CREDENTIALS = {"admin": "1234"}
    BUYER_CREDENTIALS = {"buyer": "1111", "global": "2222"}
    NAVER_CLIENT_ID = "aic55XK2RCthRyeMMlJM"
    NAVER_CLIENT_SECRET = "ZqOAIOzYGf"
else:
    # Secrets에 바이어 정보가 없다면 기본값 사용
    BUYER_CREDENTIALS = {"buyer": "1111", "global": "2222"}

DB_NAME = 'junkyard.db'

# ---------------------------------------------------------
# 1. 데이터베이스 초기화
# ---------------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS vehicle_data (vin TEXT PRIMARY KEY, reg_date TEXT, car_no TEXT, manufacturer TEXT, model_name TEXT, model_year REAL, junkyard TEXT, engine_code TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS junkyard_info (name TEXT PRIMARY KEY, address TEXT, region TEXT, lat REAL, lon REAL, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
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
    conn.commit()
    return conn

# ---------------------------------------------------------
# 🕵️ [직거래 방지] 데이터 마스킹 함수
# ---------------------------------------------------------
def generate_alias(real_name):
    hash_object = hashlib.md5(str(real_name).encode())
    hash_int = int(hash_object.hexdigest(), 16) % 900 + 100 
    return f"Partner #{hash_int}"

def mask_dataframe(df):
    if df.empty: return df
    
    df_safe = df.copy()
    
    # 1. 업체명 익명화
    if 'junkyard' in df_safe.columns:
        df_safe['real_junkyard'] = df_safe['junkyard']
        df_safe['junkyard'] = df_safe['junkyard'].apply(generate_alias)
    
    # 2. 주소 광역화
    def simplify_address(addr):
        s = str(addr)
        if '경기' in s: return 'Gyeonggi-do, Korea'
        if '인천' in s: return 'Incheon, Korea'
        if '서울' in s: return 'Seoul, Korea'
        if '경남' in s or '부산' in s: return 'Busan/Gyeongnam, Korea'
        return 'South Korea (Domestic)'
    
    if 'address' in df_safe.columns:
        df_safe['address'] = df_safe['address'].apply(simplify_address)
        
    # 3. 민감정보 제거
    if 'vin' in df_safe.columns:
        df_safe['vin'] = df_safe['vin'].astype(str).apply(lambda x: x[:8] + "****" if len(x) > 8 else "****")
    
    if 'car_no' in df_safe.columns:
        df_safe = df_safe.drop(columns=['car_no'], errors='ignore')
        
    if 'lat' in df_safe.columns:
        df_safe['lat'] = 0.0
        df_safe['lon'] = 0.0

    return df_safe

# ---------------------------------------------------------
# 데이터 로드 함수
# ---------------------------------------------------------
@st.cache_data(ttl=300)
def load_all_data():
    try:
        conn = init_db()
        query = "SELECT v.*, j.region, j.lat, j.lon, j.address FROM vehicle_data v LEFT JOIN junkyard_info j ON v.junkyard = j.name"
        df = pd.read_sql(query, conn)
        conn.close()
        if not df.empty:
            df['model_year'] = pd.to_numeric(df['model_year'], errors='coerce').fillna(0)
            df['reg_date'] = pd.to_datetime(df['reg_date'], errors='coerce')
        return df
    except: return pd.DataFrame()

def save_vehicle_file(uploaded_file):
    # (이전의 대용량 처리 로직 그대로 유지 - 간략화)
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
        
        # 신규 폐차장 등록
        unique_yards = df_db['junkyard'].unique().tolist()
        for yard in unique_yards:
            c.execute("INSERT OR IGNORE INTO junkyard_info (name, address, region, lat, lon) VALUES (?, ?, ?, ?, ?)", (yard, '검색실패', '기타', 0.0, 0.0))
            
        conn.commit()
        conn.close()
        return cnt, 0
    except: return 0, 0

# ---------------------------------------------------------
# 🚀 메인 어플리케이션
# ---------------------------------------------------------
if 'user_role' not in st.session_state: st.session_state.user_role = 'guest'
if 'view_data' not in st.session_state: st.session_state['view_data'] = pd.DataFrame()
if 'is_filtered' not in st.session_state: st.session_state['is_filtered'] = False

df_raw = load_all_data()

# 1. 사이드바
with st.sidebar:
    st.title("K-Parts Global Hub")
    
    if st.session_state.user_role == 'guest':
        with st.expander("Login", expanded=True):
            uid = st.text_input("ID")
            upw = st.text_input("Password", type="password")
            if st.button("Sign In"):
                if uid in ADMIN_CREDENTIALS and ADMIN_CREDENTIALS[uid] == upw:
                    st.session_state.user_role = 'admin'
                    safe_rerun()
                elif uid in BUYER_CREDENTIALS and BUYER_CREDENTIALS[uid] == upw:
                    st.session_state.user_role = 'buyer'
                    safe_rerun()
                else:
                    st.error("Invalid Credentials")
    else:
        role_icon = "👑" if st.session_state.user_role == 'admin' else "🌍"
        st.success(f"{role_icon} Welcome, {st.session_state.user_role.upper()}!")
        if st.button("Logout"):
            st.session_state.user_role = 'guest'
            safe_rerun()

    st.divider()

    if st.session_state.user_role == 'admin':
        with st.expander("📂 Data Upload (Admin)"):
            up_files = st.file_uploader("Vehicle Data", type=['xlsx', 'xls', 'csv'], accept_multiple_files=True)
            if up_files and st.button("Upload"):
                tot = 0
                bar = st.progress(0)
                for i, f in enumerate(up_files):
                    n, _ = save_vehicle_file(f)
                    tot += n
                    bar.progress((i+1)/len(up_files))
                st.success(f"{tot} records uploaded.")
                load_all_data.clear()
                safe_rerun()

    st.subheader("🔍 Search Parts")
    
    if not df_raw.empty:
        makers = sorted(df_raw['manufacturer'].dropna().unique().tolist())
        makers.insert(0, "All")
        
        with st.form("search_form"):
            sel_maker = st.selectbox("Manufacturer", makers)
            
            all_models = sorted(df_raw['model_name'].dropna().unique().tolist())
            sel_models = st.multiselect("Model Name", all_models)
            
            all_engines = sorted(df_raw['engine_code'].dropna().unique().tolist())
            sel_engines = st.multiselect("Engine Code", all_engines)
            
            c1, c2 = st.columns(2)
            with c1: sel_sy = st.number_input("Year From", 1990, 2025, 2000)
            with c2: sel_ey = st.number_input("Year To", 1990, 2025, 2025)

            if st.form_submit_button("🔍 Search Inventory", type="primary"):
                res = df_raw.copy()
                if sel_maker != "All": res = res[res['manufacturer'] == sel_maker]
                if sel_models: res = res[res['model_name'].isin(sel_models)]
                if sel_engines: res = res[res['engine_code'].isin(sel_engines)]
                res = res[(res['model_year'] >= sel_sy) & (res['model_year'] <= sel_ey)]
                
                st.session_state['view_data'] = res
                st.session_state['is_filtered'] = True
                safe_rerun()

# 2. 메인 화면
st.title("🇰🇷 Korea Used Auto Parts Inventory")

df_view = st.session_state['view_data']

# 권한별 데이터 처리
if st.session_state.user_role == 'buyer':
    # ⚡ [수정] 데이터가 비어있지 않을 때만 마스킹
    if not df_view.empty:
        df_display = mask_dataframe(df_view)
    else:
        df_display = pd.DataFrame()
else:
    # 관리자
    df_display = df_view.copy()
    # ⚡ [수정] 데이터가 있고, 컬럼이 있을 때만 복사
    if not df_display.empty and 'junkyard' in df_display.columns:
        if 'real_junkyard' not in df_display.columns:
            df_display['real_junkyard'] = df_display['junkyard']

# 탭 구성
if st.session_state.user_role == 'admin':
    tabs = st.tabs(["📊 Inventory View", "📩 Order Management", "🗺️ Location Map"])
else:
    tabs = st.tabs(["📊 Search Results", "🛒 My Cart"])

# --- [탭 1] 재고 조회 ---
with tabs[0]:
    if df_display.empty:
        st.info("Please select filters from the sidebar to search.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Vehicles", f"{len(df_display):,} EA")
        c2.metric("Matched Engines", f"{df_display['engine_code'].nunique()} Types")
        
        sup_label = "Suppliers" if st.session_state.user_role == 'buyer' else "Real Junkyards"
        c3.metric(sup_label, f"{df_display['junkyard'].nunique()} EA")
        
        st.divider()
        st.subheader("📦 Stock by Supplier")
        
        group_cols = ['junkyard', 'address']
        if st.session_state.user_role == 'admin' and 'region' in df_display.columns:
            group_cols.append('region')

        stock_summary = df_display.groupby(group_cols).size().reset_index(name='stock_count').sort_values('stock_count', ascending=False)
        
        selection = st.dataframe(
            stock_summary,
            use_container_width=True,
            hide_index=True,
            selection_mode="single-row",
            on_select="rerun"
        )
        
        if len(selection.selection.rows) > 0:
            sel_idx = selection.selection.rows[0]
            sel_row = stock_summary.iloc[sel_idx]
            target_partner = sel_row['junkyard']
            stock_cnt = sel_row['stock_count']
            
            st.success(f"Selected: **{target_partner}** (Available: {stock_cnt} EA)")
            
            with st.form("order_form"):
                st.markdown(f"### 📨 Request Quote to {target_partner}")
                
                c_a, c_b = st.columns(2)
                with c_a:
                    buyer_name = st.text_input("Your Name / Company", value="Buyer1")
                    contact_info = st.text_input("Email / WhatsApp")
                with c_b:
                    st.text_input("Target Item", value=f"Search Results ({stock_cnt} items)", disabled=True)
                    offer_price = st.text_input("Target Price (USD)", placeholder="e.g. $1,500")
                
                msg = st.text_area("Message", height=100, placeholder="Inquiry details...")
                
                if st.form_submit_button("🚀 Submit Inquiry"):
                    conn = init_db()
                    cur = conn.cursor()
                    
                    real_name = target_partner
                    if st.session_state.user_role == 'buyer':
                        # 관리자가 알 수 있도록 원본 이름 추적 (간이 로직)
                        try:
                            # 현재 화면 데이터에서 해당 Alias를 가진 첫 행의 'real_junkyard'를 가져옴
                            match = df_display[df_display['junkyard'] == target_partner]
                            if not match.empty and 'real_junkyard' in match.columns:
                                real_name = match['real_junkyard'].iloc[0]
                            else:
                                real_name = "Unknown (Check DB)"
                        except: real_name = "Tracking Error"

                    cur.execute("""
                        INSERT INTO orders (buyer_id, target_partner_alias, real_junkyard_name, items_summary, status)
                        VALUES (?, ?, ?, ?, ?)
                    """, (buyer_name, target_partner, real_name, f"Qty: {stock_cnt}, Price: {offer_price}, Msg: {msg}", 'PENDING'))
                    conn.commit()
                    conn.close()
                    st.success("✅ Inquiry Sent!")

        st.markdown("---")
        st.subheader("📋 Item Details")
        st.dataframe(df_display, use_container_width=True)

# --- [탭 2] 주문 관리 (관리자) ---
if st.session_state.user_role == 'admin':
    with tabs[1]:
        st.subheader("📩 Incoming Quote Requests")
        conn = init_db()
        orders_df = pd.read_sql("SELECT * FROM orders ORDER BY created_at DESC", conn)
        conn.close()
        
        if not orders_df.empty:
            for idx, row in orders_df.iterrows():
                with st.expander(f"[{row['status']}] From: {row['buyer_id']} -> To: {row['real_junkyard_name']}"):
                    st.write(f"**Alias:** {row['target_partner_alias']}")
                    st.write(f"**Request:** {row['items_summary']}")
                    st.write(f"**Date:** {row['created_at']}")
                    c1, c2 = st.columns(2)
                    if c1.button("📞 Contact Junkyard", key=f"call_{row['id']}"):
                        st.info(f"Please call {row['real_junkyard_name']}.")
                    if c2.button("✅ Complete", key=f"done_{row['id']}"):
                        st.success("Marked as done.")
        else: st.info("No orders yet.")

    with tabs[2]:
        st.subheader("🗺️ Real Locations")
        if not df_display.empty and 'lat' in df_display.columns:
             fig_map = px.scatter_mapbox(
                df_display, lat="lat", lon="lon", hover_name="junkyard", 
                zoom=6.5, center={"lat": 36.5, "lon": 127.8},
                mapbox_style="carto-positron"
            )
             st.plotly_chart(fig_map, use_container_width=True)
