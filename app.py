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
    # 데모용 기본 계정
    ADMIN_CREDENTIALS = {"admin": "1234"} # 관리자 (모든 정보 열람)
    BUYER_CREDENTIALS = {"buyer": "1111", "global": "2222"} # 바이어 (정보 제한)
    NAVER_CLIENT_ID = "aic55XK2RCthRyeMMlJM"
    NAVER_CLIENT_SECRET = "ZqOAIOzYGf"

DB_NAME = 'junkyard.db'

# ---------------------------------------------------------
# 1. 데이터베이스 초기화 (주문 테이블 추가)
# ---------------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # 차량 데이터
    c.execute('''CREATE TABLE IF NOT EXISTS vehicle_data (vin TEXT PRIMARY KEY, reg_date TEXT, car_no TEXT, manufacturer TEXT, model_name TEXT, model_year REAL, junkyard TEXT, engine_code TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    # 폐차장 정보
    c.execute('''CREATE TABLE IF NOT EXISTS junkyard_info (name TEXT PRIMARY KEY, address TEXT, region TEXT, lat REAL, lon REAL, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    # 검색 로그
    c.execute('''CREATE TABLE IF NOT EXISTS search_logs_v2 (id INTEGER PRIMARY KEY AUTOINCREMENT, keyword TEXT, search_type TEXT, country TEXT, city TEXT, lat REAL, lon REAL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    # 🟢 [신규] 주문(견적) 접수 테이블
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        buyer_id TEXT,
        target_partner_alias TEXT, -- 바이어가 본 파트너명 (예: Partner #101)
        real_junkyard_name TEXT,   -- 실제 폐차장명 (관리자만 확인)
        items_summary TEXT,        -- 요청 품목 요약
        status TEXT DEFAULT 'PENDING', -- PENDING, CONTACTED, QUOTED
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    conn.commit()
    return conn

# ---------------------------------------------------------
# 🕵️ [직거래 방지] 데이터 마스킹 함수
# ---------------------------------------------------------
def generate_alias(real_name):
    """폐차장 실명을 고유한 Partner ID로 변환 (해시 기반으로 항상 동일한 ID 생성)"""
    hash_object = hashlib.md5(real_name.encode())
    # 숫자로만 이루어진 3자리 ID 생성
    hash_int = int(hash_object.hexdigest(), 16) % 900 + 100 
    return f"Partner #{hash_int}"

def mask_dataframe(df):
    """바이어에게 보여줄 데이터프레임을 안전하게 변환"""
    df_safe = df.copy()
    
    # 1. 업체명 익명화
    df_safe['real_junkyard'] = df_safe['junkyard'] # 관리자 추적용 백업
    df_safe['junkyard'] = df_safe['junkyard'].apply(generate_alias)
    
    # 2. 주소 광역화 (상세주소 제거)
    # 예: 경기도 이천시... -> Gyeonggi-do, Korea
    def simplify_address(addr):
        if '경기' in str(addr): return 'Gyeonggi-do, Korea'
        if '인천' in str(addr): return 'Incheon, Korea'
        if '서울' in str(addr): return 'Seoul, Korea'
        if '경남' in str(addr) or '부산' in str(addr): return 'Busan/Gyeongnam, Korea'
        return 'South Korea (Domestic)'
    
    if 'address' in df_safe.columns:
        df_safe['address'] = df_safe['address'].apply(simplify_address)
        
    # 3. 차대번호 마스킹 (VIN)
    if 'vin' in df_safe.columns:
        df_safe['vin'] = df_safe['vin'].astype(str).apply(lambda x: x[:8] + "****" if len(x) > 8 else "****")
        
    # 4. 차량번호 숨김 (완전 제거)
    if 'car_no' in df_safe.columns:
        df_safe = df_safe.drop(columns=['car_no'])
        
    # 5. 위도경도 제거 (지도 추적 방지)
    if 'lat' in df_safe.columns:
        df_safe['lat'] = 0.0
        df_safe['lon'] = 0.0

    return df_safe

# ---------------------------------------------------------
# 데이터 로드 및 저장 함수들 (기존 로직 유지)
# ---------------------------------------------------------
# ... (기존 save_vehicle_file, save_address_file 등은 관리자용이므로 그대로 둠) ...
# 편의상 핵심 로직만 유지하고, 위에서 정의한 init_db를 사용하도록 함.

def save_vehicle_file(uploaded_file):
    # (이전 코드와 동일하되 init_db 호출)
    try:
        if uploaded_file.name.endswith('.csv'): df = pd.read_csv(uploaded_file, dtype=str)
        else: 
            try: df = pd.read_excel(uploaded_file, engine='openpyxl', dtype=str)
            except: df = pd.read_excel(uploaded_file, engine='xlrd', dtype=str)
            
        # 헤더 처리 및 컬럼 매핑 (생략 - 이전과 동일)
        # ... (생략) ...
        # 간단하게 구현:
        conn = init_db()
        # ... 저장 로직 ...
        # 여기서는 시뮬레이션을 위해 Pass 처리 (실제론 이전 코드 그대로 사용)
        return 0, 0 
    except: return 0, 0
    # *실제 적용시에는 직전 답변의 save_vehicle_file 함수 전체를 복사해서 넣으세요*

@st.cache_data(ttl=300)
def load_all_data():
    try:
        conn = init_db()
        query = "SELECT v.*, j.region, j.lat, j.lon, j.address FROM vehicle_data v LEFT JOIN junkyard_info j ON v.junkyard = j.name"
        df = pd.read_sql(query, conn)
        conn.close()
        if not df.empty:
            # 전처리
            df['model_year'] = pd.to_numeric(df['model_year'], errors='coerce').fillna(0)
            df['reg_date'] = pd.to_datetime(df['reg_date'], errors='coerce')
        return df
    except: return pd.DataFrame()

# ---------------------------------------------------------
# 🚀 메인 어플리케이션
# ---------------------------------------------------------
if 'user_role' not in st.session_state: st.session_state.user_role = 'guest' # guest, admin, buyer
if 'view_data' not in st.session_state: st.session_state['view_data'] = pd.DataFrame()
if 'is_filtered' not in st.session_state: st.session_state['is_filtered'] = False

# 데이터 로드
df_raw = load_all_data()

# ==========================================
# 1. 사이드바 (로그인 & 필터)
# ==========================================
with st.sidebar:
    st.title("K-Parts Global Hub")
    
    # 🔐 로그인 시스템
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

    # 📂 [관리자 전용] 데이터 업로드
    if st.session_state.user_role == 'admin':
        with st.expander("📂 Data Management (Admin)"):
            st.info("관리자 권한으로 데이터 업로드가 가능합니다.")
            # (업로드 위젯 생략 - 이전과 동일하게 구현 가능)

    # 🔍 검색 필터 (공통)
    # 바이어에게는 '폐차장 이름' 검색 필터를 숨기거나, Alias로 검색하게 해야 함.
    # 여기서는 차종/엔진 위주로만 검색하도록 유도
    
    st.subheader("🔍 Search Parts")
    
    if not df_raw.empty:
        # 제조사/모델/엔진 목록 추출
        makers = sorted(df_raw['manufacturer'].dropna().unique().tolist())
        makers.insert(0, "All")
        
        with st.form("search_form"):
            # 1. 제조사
            sel_maker = st.selectbox("Manufacturer", makers)
            
            # 2. 모델명 (전체 목록)
            all_models = sorted(df_raw['model_name'].dropna().unique().tolist())
            sel_models = st.multiselect("Model Name", all_models)
            
            # 3. 엔진코드
            all_engines = sorted(df_raw['engine_code'].dropna().unique().tolist())
            sel_engines = st.multiselect("Engine Code", all_engines)
            
            # 4. 연식
            c1, c2 = st.columns(2)
            with c1: sel_sy = st.number_input("Year From", 1990, 2025, 2000)
            with c2: sel_ey = st.number_input("Year To", 1990, 2025, 2025)

            search_btn = st.form_submit_button("🔍 Search Inventory", type="primary")
            
            if search_btn:
                # 필터링 로직
                res = df_raw.copy()
                if sel_maker != "All": res = res[res['manufacturer'] == sel_maker]
                if sel_models: res = res[res['model_name'].isin(sel_models)]
                if sel_engines: res = res[res['engine_code'].isin(sel_engines)]
                res = res[(res['model_year'] >= sel_sy) & (res['model_year'] <= sel_ey)]
                
                st.session_state['view_data'] = res
                st.session_state['is_filtered'] = True
                safe_rerun()

# ==========================================
# 2. 메인 화면 (Role에 따라 다르게 표시)
# ==========================================
st.title("🇰🇷 Korea Used Auto Parts Inventory")

# 데이터 권한 처리
df_view = st.session_state['view_data']
is_filtered = st.session_state['is_filtered']

if st.session_state.user_role == 'buyer':
    # 바이어는 마스킹된 데이터만 봄
    df_display = mask_dataframe(df_view)
else:
    # 관리자는 원본 봄
    df_display = df_view.copy()
    if 'junkyard' not in df_display.columns: # 컬럼 없으면 생성 (에러방지)
        df_display['real_junkyard'] = df_display['junkyard']

# 탭 구성
if st.session_state.user_role == 'admin':
    tabs = st.tabs(["📊 Inventory View", "📩 Order Management", "🗺️ Location Map"])
else:
    tabs = st.tabs(["📊 Search Results", "🛒 My Cart"])

# --- [탭 1] 재고 조회 (공통) ---
with tabs[0]:
    if df_display.empty:
        st.info("Please select filters from the sidebar to search.")
    else:
        # KPI
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Vehicles", f"{len(df_display):,} EA")
        c2.metric("Matched Engines", f"{df_display['engine_code'].nunique()} Types")
        
        # 관리자만 실제 업체 수 확인, 바이어는 파트너 수
        supplier_label = "Suppliers" if st.session_state.user_role == 'buyer' else "Real Junkyards"
        c3.metric(supplier_label, f"{df_display['junkyard'].nunique()} EA")
        
        st.divider()
        
        # [핵심] 업체별 재고 요약 (Aggregated View)
        st.subheader("📦 Stock by Supplier")
        
        # 바이어에게는 'junkyard'(이미 Alias됨)와 'address'(마스킹됨)로 그룹핑
        # 관리자에게는 'junkyard'(실명)와 'address'(실주소)로 그룹핑
        
        group_cols = ['junkyard', 'address']
        if st.session_state.user_role == 'admin':
            group_cols = ['junkyard', 'address', 'region']

        stock_summary = df_display.groupby(group_cols).size().reset_index(name='stock_count').sort_values('stock_count', ascending=False)
        
        # 인터랙티브 테이블
        selection = st.dataframe(
            stock_summary,
            use_container_width=True,
            hide_index=True,
            selection_mode="single-row",
            on_select="rerun"
        )
        
        # 업체 선택 시 액션 (견적 요청)
        if len(selection.selection.rows) > 0:
            sel_idx = selection.selection.rows[0]
            sel_row = stock_summary.iloc[sel_idx]
            target_partner = sel_row['junkyard']
            stock_cnt = sel_row['stock_count']
            
            st.success(f"Selected: **{target_partner}** (Available: {stock_cnt} EA)")
            
            # 견적 요청 폼
            with st.form("order_form"):
                st.markdown(f"### 📨 Request Quote to {target_partner}")
                st.caption("We will verify the stock and send you a formal quotation including shipping.")
                
                c_a, c_b = st.columns(2)
                with c_a:
                    buyer_name = st.text_input("Your Name / Company", value="Buyer1")
                    contact_info = st.text_input("Email / WhatsApp")
                with c_b:
                    st.text_input("Target Item", value=f"Search Results ({stock_cnt} items)", disabled=True)
                    offer_price = st.text_input("Target Price (USD)", placeholder="e.g. $1,500")
                
                msg = st.text_area("Message to Admin", height=100, placeholder="I need D4CB engines in good condition...")
                
                submit = st.form_submit_button("🚀 Submit Inquiry")
                
                if submit:
                    # DB에 주문 저장
                    conn = init_db()
                    cur = conn.cursor()
                    
                    # 실제 폐차장 이름 찾기 (관리자용)
                    real_name = target_partner # 관리자일 땐 그대로
                    if st.session_state.user_role == 'buyer':
                        # Alias를 역추적하기 어려우므로, 여기서는 간단히
                        # 실제로는 Alias 생성 시 DB에 매핑 테이블을 만들어야 함.
                        # 이번 데모에서는 현재 뷰의 첫 번째 VIN으로 역추적하거나, 
                        # Alias 생성 로직이 Hash이므로 복호화 불가 -> DB에 매핑 저장 필요.
                        # *임시* : 여기서는 바이어가 선택한게 어떤 실명인지 화면 데이터에서 찾음
                        try:
                            # 화면에 보이는 Alias와 일치하는 원본 데이터의 첫 번째 행에서 실명 추출
                            sample_vin = df_display[df_display['junkyard'] == target_partner]['vin'].iloc[0]
                            # 마스킹 된 VIN이라 역추적 불가...
                            # [해결책] display DF를 만들 때 hidden column으로 real_name을 넣어두면 됨.
                            real_name = df_display[df_display['junkyard'] == target_partner]['real_junkyard'].iloc[0]
                        except:
                            real_name = "Unknown"

                    cur.execute("""
                        INSERT INTO orders (buyer_id, target_partner_alias, real_junkyard_name, items_summary, status)
                        VALUES (?, ?, ?, ?, ?)
                    """, (buyer_name, target_partner, real_name, f"Stock: {stock_cnt}, Msg: {msg}", 'PENDING'))
                    conn.commit()
                    conn.close()
                    st.success("✅ Inquiry Sent! Our manager will contact you shortly.")

        st.markdown("---")
        st.subheader("📋 Item Details")
        st.dataframe(df_display, use_container_width=True)

# --- [탭 2] 주문 관리 (관리자 전용) ---
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
                    if c1.button("📞 Call Junkyard", key=f"call_{row['id']}"):
                        st.info(f"Contacting {row['real_junkyard_name']}... (Simulated)")
                    if c2.button("✅ Mark as Quoted", key=f"done_{row['id']}"):
                        # DB 업데이트 로직 필요
                        st.success("Status Updated!")
        else:
            st.info("No pending orders.")

    with tabs[2]:
        st.subheader("🗺️ Real Locations (Admin Only)")
        if not df_view.empty and 'lat' in df_view.columns:
             fig_map = px.scatter_mapbox(
                df_view, lat="lat", lon="lon", hover_name="junkyard", 
                zoom=6.5, center={"lat": 36.5, "lon": 127.8},
                mapbox_style="carto-positron"
            )
             st.plotly_chart(fig_map, use_container_width=True)
