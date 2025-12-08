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
    BUYER_CREDENTIALS = {"buyer": "1111", "global": "2222"}
    NAVER_CLIENT_ID = "aic55XK2RCthRyeMMlJM"
    NAVER_CLIENT_SECRET = "ZqOAIOzYGf"
else:
    if "buyer" not in locals(): 
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
    
    # 인덱스
    c.execute("CREATE INDEX IF NOT EXISTS idx_mfr ON vehicle_data(manufacturer)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_model ON vehicle_data(model_name)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_engine ON vehicle_data(engine_code)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_yard ON vehicle_data(junkyard)")
    conn.commit()
    return conn

# ---------------------------------------------------------
# 🕵️ [직거래 방지] 데이터 마스킹 (핵심)
# ---------------------------------------------------------
def generate_alias(real_name):
    """폐차장 실명을 고유한 Partner ID로 변환 (해시 기반)"""
    if not isinstance(real_name, str): return "Unknown"
    hash_object = hashlib.md5(real_name.encode())
    hash_int = int(hash_object.hexdigest(), 16) % 900 + 100 
    return f"Partner #{hash_int}"

def apply_security_policy(df, role):
    """사용자 권한(Role)에 따라 데이터를 변조하거나 삭제함"""
    if df.empty: return df
    
    # 원본 보호를 위해 복사
    df_secure = df.copy()
    
    # [공통] 가명(Alias) 컬럼 생성
    if 'junkyard' in df_secure.columns:
        df_secure['partner_alias'] = df_secure['junkyard'].apply(generate_alias)
    
    # [관리자(Admin)] -> 모든 정보 열람 가능
    if role == 'admin':
        return df_secure

    # [바이어(Buyer) & 게스트(Guest)] -> 정보 제한
    
    # 1. 실제 폐차장 이름 제거
    if 'junkyard' in df_secure.columns:
        # 화면 표시용 컬럼을 Alias로 교체
        df_secure['junkyard'] = df_secure['partner_alias'] 
    
    # 2. 차량번호 제거 (추적 방지)
    if 'car_no' in df_secure.columns:
        df_secure = df_secure.drop(columns=['car_no'])
        
    # 3. 차대번호 마스킹
    if 'vin' in df_secure.columns:
        df_secure['vin'] = df_secure['vin'].astype(str).apply(lambda x: x[:8] + "****" if len(x) > 8 else "****")
    
    # 4. 주소 마스킹 (광역 단위만 표시)
    def simplify_address(addr):
        s = str(addr)
        if '경기' in s: return 'Gyeonggi-do, Korea'
        if '인천' in s: return 'Incheon, Korea'
        if '서울' in s: return 'Seoul, Korea'
        if '경남' in s or '부산' in s: return 'Busan/Gyeongnam, Korea'
        return 'South Korea'
    
    if 'address' in df_secure.columns:
        if role == 'buyer':
            df_secure['address'] = df_secure['address'].apply(simplify_address)
        else: # Guest
            df_secure['address'] = "🔒 Login Required"
            df_secure['junkyard'] = "🔒 Login Required" # 게스트는 파트너명도 숨김

    # 5. 지도 좌표 제거 (게스트)
    if role == 'guest' and 'lat' in df_secure.columns:
        df_secure['lat'] = 0.0
        df_secure['lon'] = 0.0
        
    return df_secure

# ---------------------------------------------------------
# 기능 함수들
# ---------------------------------------------------------
def log_search(keywords, s_type):
    if not keywords: return
    try:
        conn = init_db()
        c = conn.cursor()
        # 임의 위치 (서울)
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
    # (파일 저장 로직 - 이전과 동일하여 생략, 실제 구동시엔 이전 코드의 내용을 그대로 사용)
    # 편의상 성공 리턴만 함. 실제로는 DB 저장 로직 수행됨.
    # *** 이전 답변의 save_vehicle_file 전체 내용을 여기에 복사해야 합니다. ***
    # 코드 길이 제한으로 인해 생략된 부분은 '이전 답변' 참조
    return 100, 0 

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

# 참조 데이터 로드
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

# [중요] 필터용 폐차장 목록 로드 (권한에 따라 다르게 리턴)
def load_yard_list_for_filter(role):
    try:
        conn = init_db()
        df = pd.read_sql("SELECT name FROM junkyard_info ORDER BY name", conn)
        conn.close()
        
        real_names = df['name'].tolist()
        
        if role == 'admin':
            return real_names # 관리자는 실명 리스트
        elif role == 'buyer':
            # 바이어는 Alias 리스트로 변환
            return sorted(list(set([generate_alias(name) for name in real_names])))
        else:
            return [] # 게스트는 검색 불가
    except: return []

# ---------------------------------------------------------
# 🚀 메인 어플리케이션
# ---------------------------------------------------------
if 'user_role' not in st.session_state: st.session_state.user_role = 'guest'
if 'view_data' not in st.session_state: st.session_state['view_data'] = pd.DataFrame()
if 'is_filtered' not in st.session_state: st.session_state['is_filtered'] = False
if 'mode_demand' not in st.session_state: st.session_state.mode_demand = False

# 원본 데이터 로드 (필터링 전)
df_raw = load_all_data()

# 참조 데이터 로드
df_models = load_model_list()
list_engines = load_engine_list()

# 1. 사이드바 (로그인 & 검색 탭)
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
                    safe_rerun()
                elif uid in BUYER_CREDENTIALS and BUYER_CREDENTIALS[uid] == upw:
                    st.session_state.user_role = 'buyer'
                    safe_rerun()
                else:
                    st.error("Invalid Credentials")
    else:
        role_text = "Manager" if st.session_state.user_role == 'admin' else "Global Buyer"
        st.success(f"Welcome, {role_text}!")
        if st.button("Logout"):
            st.session_state.user_role = 'guest'
            safe_rerun()

    st.divider()

    # 관리자 메뉴
    if st.session_state.user_role == 'admin':
        with st.expander("📂 Admin Tools"):
            up_files = st.file_uploader("Data Upload", type=['xlsx', 'xls', 'csv'], accept_multiple_files=True)
            if up_files and st.button("Save"):
                # (업로드 로직 생략 - 이전과 동일)
                st.success("Admin feature (Demo)")
                load_all_data.clear()
                safe_rerun()
            
            if st.button("🗑️ Reset DB"):
                conn = init_db()
                conn.execute("DROP TABLE vehicle_data")
                conn.execute("DROP TABLE junkyard_info")
                conn.execute("DROP TABLE model_list")
                conn.commit()
                conn.close()
                st.success("Reset Done")
                safe_rerun()

    # 🔍 검색 탭
    st.subheader("🔍 Search Filter")
    search_tabs = st.tabs(["🚙 Vehicle", "🔧 Engine", "🏭 Yard", "🔮 Forecast"])
    
    # 1) 차량 검색
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

    # 2) 엔진 검색
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

    # 3) 폐차장 검색 (보안 적용)
    with search_tabs[2]: 
        # 권한별 목록 로드
        filter_yards = load_yard_list_for_filter(st.session_state.user_role)
        
        if not filter_yards:
            st.warning("Login required to search by partner.")
        else:
            sel_yards = st.multiselect("Partner Name", filter_yards)
            if st.button("🔍 Search Partner", type="primary"):
                res = load_all_data() # 원본 로드 (실명 포함)
                
                if sel_yards:
                    # 필터링 로직: 
                    # 1. 원본 데이터에 alias 컬럼 생성
                    res['alias_temp'] = res['junkyard'].apply(generate_alias)
                    
                    if st.session_state.user_role == 'admin':
                        # 관리자는 실명으로 검색
                        res = res[res['junkyard'].isin(sel_yards)]
                    else:
                        # 바이어는 Alias로 검색
                        res = res[res['alias_temp'].isin(sel_yards)]
                    
                    # 임시 컬럼 삭제
                    if 'alias_temp' in res.columns: res = res.drop(columns=['alias_temp'])

                st.session_state['view_data'] = res.reset_index(drop=True)
                st.session_state['is_filtered'] = True
                st.session_state['mode_demand'] = False
                safe_rerun()

    # 4) 수요 예측
    with search_tabs[3]: 
        st.info("Check global search trends.")
        if st.button("🔮 Show Trends"):
            st.session_state['mode_demand'] = True
            safe_rerun()

    # 초기화
    if st.button("🔄 Reset Filters", use_container_width=True):
        st.session_state['view_data'] = load_all_data()
        st.session_state['is_filtered'] = False
        st.session_state['mode_demand'] = False
        safe_rerun()

# 2. 메인 화면
# ----------------------------------------
df_view = st.session_state['view_data']

# [A] 수요 예측 모드
if st.session_state.mode_demand:
    st.title("📈 Global Demand Trends (Real-time)")
    eng_trend, mod_trend = get_search_trends()
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🔥 Top Searched Engines")
        if not eng_trend.empty:
            fig = px.bar(eng_trend, x='count', y='keyword', orientation='h')
            st.plotly_chart(fig, use_container_width=True)
        else: st.info("No data yet.")
    with c2:
        st.subheader("🚙 Top Searched Models")
        if not mod_trend.empty:
            fig = px.bar(mod_trend, x='count', y='keyword', orientation='h')
            st.plotly_chart(fig, use_container_width=True)
        else: st.info("No data yet.")

# [B] 재고 조회 모드 (기본)
else:
    st.title("🇰🇷 Korea Used Auto Parts Inventory")
    
    # 🛡️ 화면 표시용 데이터 마스킹 적용 (가장 중요)
    df_display = apply_security_policy(df_view, st.session_state.user_role)
    
    # 탭 구성
    if st.session_state.user_role == 'admin':
        main_tabs = st.tabs(["📊 Inventory", "📩 Orders", "🗺️ Real Map"])
    else:
        main_tabs = st.tabs(["📊 Search Results"])

    # 1) Inventory Tab
    with main_tabs[0]:
        if df_display.empty:
            st.info("Please select filters from the sidebar to search.")
        else:
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Vehicles", f"{len(df_display):,} EA")
            c2.metric("Matched Engines", f"{df_display['engine_code'].nunique()} Types")
            
            # 공급자 수 표시 (게스트는 숨김)
            if st.session_state.user_role == 'guest':
                c3.metric("Suppliers", "🔒 Login Req.")
            else:
                sup_label = "Real Junkyards" if st.session_state.user_role == 'admin' else "Partners"
                c3.metric(sup_label, f"{df_display['junkyard'].nunique()} EA")
            
            st.divider()
            
            # 업체별 재고 요약
            st.subheader("📦 Stock by Partner")
            
            # 그룹핑 기준 (관리자는 실명/실주소, 바이어는 Alias/광역주소, 게스트는 잠금)
            grp_cols = ['junkyard', 'address']
            if st.session_state.user_role == 'admin': grp_cols.append('region')
            
            stock_summary = df_display.groupby(grp_cols).size().reset_index(name='qty').sort_values('qty', ascending=False)
            
            selection = st.dataframe(stock_summary, use_container_width=True, hide_index=True, selection_mode="single-row", on_select="rerun")
            
            # 선택 시 견적 폼
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
                            buyer_name = st.text_input("Name / Company", value="Buyer")
                            contact = st.text_input("Contact (Email/Phone)")
                        with c_b:
                            st.text_input("Item", value=f"Selected {stock_cnt} items", disabled=True)
                            offer = st.text_input("Offer Price (USD)")
                        msg = st.text_area("Message", height=80)
                        
                        if st.form_submit_button("🚀 Send Inquiry"):
                            conn = init_db()
                            cur = conn.cursor()
                            
                            # 실제 이름 추적 (관리자는 그대로, 바이어는 Alias 매칭)
                            real_name = target_partner
                            if st.session_state.user_role == 'buyer':
                                # 현재 뷰 데이터에서 Alias가 일치하는 행의 원본 이름(junkyard)을 찾음
                                # (load_all_data에서 원본을 가져왔고, mask_dataframe 함수 적용 전의 df_view를 참조해야 함)
                                try:
                                    # df_view에는 원본 실명이 'junkyard' 컬럼에 있음
                                    # df_view['alias']를 임시로 만들어 매칭
                                    temp_df = df_view.copy()
                                    temp_df['alias'] = temp_df['junkyard'].apply(generate_alias)
                                    match = temp_df[temp_df['alias'] == target_partner]
                                    if not match.empty:
                                        real_name = match['junkyard'].iloc[0]
                                except: real_name = "Unknown"

                            cur.execute("INSERT INTO orders (buyer_id, target_partner_alias, real_junkyard_name, items_summary, status) VALUES (?, ?, ?, ?, ?)",
                                        (buyer_name, target_partner, real_name, f"Qty:{stock_cnt}, Offer:{offer}, {msg}", 'PENDING'))
                            conn.commit()
                            conn.close()
                            st.success("✅ Inquiry has been sent to our sales team.")

            st.divider()
            st.subheader("📋 Item List")
            st.dataframe(df_display, use_container_width=True)

    # 2) Orders Tab (Admin Only)
    if st.session_state.user_role == 'admin':
        with main_tabs[1]:
            st.subheader("📩 Quote Requests")
            conn = init_db()
            orders = pd.read_sql("SELECT * FROM orders ORDER BY created_at DESC", conn)
            conn.close()
            if not orders.empty:
                st.dataframe(orders)
            else: st.info("No orders.")
            
        with main_tabs[2]: # Real Map
            st.subheader("🗺️ Location Map")
            if 'lat' in df_display.columns and not df_display.empty:
                 valid_map = df_display[df_display['lat'] != 0]
                 if not valid_map.empty:
                     fig = px.scatter_mapbox(
                        valid_map, lat="lat", lon="lon", hover_name="junkyard", 
                        zoom=6.5, center={"lat": 36.5, "lon": 127.8},
                        mapbox_style="carto-positron"
                    )
                     st.plotly_chart(fig, use_container_width=True)
                 else: st.warning("No location data available.")
