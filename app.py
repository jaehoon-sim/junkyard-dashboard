import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import datetime
import requests
import re
import os
import traceback

# ---------------------------------------------------------
# 🛠️ [유틸] 안전한 Rerun 처리
# ---------------------------------------------------------
def safe_rerun():
    try:
        st.rerun()
    except AttributeError:
        st.experimental_rerun()

# ---------------------------------------------------------
# 🔐 [보안] 관리자 계정
# ---------------------------------------------------------
try:
    ADMIN_CREDENTIALS = st.secrets["ADMIN_CREDENTIALS"]
except:
    ADMIN_CREDENTIALS = {"admin": "1234"}

# ---------------------------------------------------------
# 🔧 [설정] 네이버 검색 API 키
# ---------------------------------------------------------
try:
    NAVER_CLIENT_ID = st.secrets["NAVER_CLIENT_ID"]
    NAVER_CLIENT_SECRET = st.secrets["NAVER_CLIENT_SECRET"]
except:
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
    conn.commit()
    return conn

def clean_junkyard_name(name):
    cleaned = re.sub(r'\(주\)|주식회사|\(유\)|합자회사|유한회사', '', str(name))
    cleaned = re.sub(r'지점', '', cleaned) 
    return cleaned.strip()

def search_place_naver(query):
    cleaned_name = clean_junkyard_name(query)
    search_query = cleaned_name
    if '폐차' not in cleaned_name and len(cleaned_name) < 5: search_query += " 폐차장"
    
    url = "https://openapi.naver.com/v1/search/local.json"
    headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
    params = {"query": search_query, "display": 1, "sort": "random"} 

    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            items = response.json().get('items')
            if items:
                address = items[0]['address']
                addr_parts = address.split()
                if len(addr_parts) >= 2:
                    si_do = addr_parts[0][:2]
                    si_gun = addr_parts[1]
                    if si_do in ['서울', '인천', '대전', '대구', '광주', '부산', '울산', '세종', '제주']: short_region = si_do
                    else:
                        gun_name = si_gun.replace('시','').replace('군','').replace('구','')
                        if len(gun_name) < 1: gun_name = si_gun
                        temp_key = f"{si_do} {gun_name}"
                        match_found = False
                        for k in CITY_COORDS.keys():
                            if temp_key in k or k in f"{si_do} {si_gun}":
                                short_region = k
                                match_found = True
                                break
                        if not match_found: short_region = f"{si_do} {si_gun}"
                else: short_region = addr_parts[0][:2]

                lat, lon = 0.0, 0.0
                if short_region in CITY_COORDS: lat, lon = CITY_COORDS[short_region]
                else:
                    for k, v in CITY_COORDS.items():
                        if k in address: short_region = k; lat, lon = v; break
                return {'address': address, 'region': short_region, 'lat': lat, 'lon': lon}
    except: pass
    return None

def sync_junkyard_info(conn):
    query = """SELECT DISTINCT v.junkyard FROM vehicle_data v LEFT JOIN junkyard_info j ON v.junkyard = j.name WHERE j.name IS NULL AND v.junkyard IS NOT NULL"""
    target_yards = pd.read_sql(query, conn)['junkyard'].tolist()
    if not target_yards: return 0
    c = conn.cursor()
    success_count = 0
    progress_bar = st.progress(0)
    for i, yard_name in enumerate(target_yards):
        info = search_place_naver(yard_name)
        if info:
            c.execute("INSERT OR REPLACE INTO junkyard_info (name, address, region, lat, lon) VALUES (?, ?, ?, ?, ?)", (yard_name, info['address'], info['region'], info['lat'], info['lon']))
            if info['lat'] != 0.0: success_count += 1
        else:
            region, lat, lon = '기타', 0.0, 0.0
            for k, v in CITY_COORDS.items():
                if k.split()[-1] in yard_name: region, lat, lon = k, v[0], v[1]; break
            c.execute("INSERT OR REPLACE INTO junkyard_info (name, address, region, lat, lon) VALUES (?, ?, ?, ?, ?)", (yard_name, '검색실패', region, lat, lon))
        progress_bar.progress((i + 1) / len(target_yards))
    conn.commit()
    progress_bar.empty()
    return success_count

def save_uploaded_file(uploaded_file):
    try:
        if uploaded_file.name.endswith('.csv'): df = pd.read_csv(uploaded_file)
        else: 
            try: df = pd.read_excel(uploaded_file, engine='openpyxl')
            except: df = pd.read_excel(uploaded_file, engine='xlrd')

        if '차대번호' not in df.columns:
            if uploaded_file.name.endswith('.csv'): uploaded_file.seek(0); df = pd.read_csv(uploaded_file, header=2)
            else: 
                try: df = pd.read_excel(uploaded_file, header=2, engine='openpyxl')
                except: df = pd.read_excel(uploaded_file, header=2, engine='xlrd')
        
        df.columns = [str(c).strip() for c in df.columns]
        required = ['등록일자', '차량번호', '차대번호', '제조사', '차량명', '회원사', '원동기형식']
        if not all(col in df.columns for col in required): return 0, 0
        conn = init_db()
        c = conn.cursor()
        new_cnt, dup_cnt = 0, 0
        for _, row in df.iterrows():
            vin = str(row['차대번호']).strip()
            try:
                raw_year = str(row['연식'])
                year = float(re.findall(r"[\d\.]+", raw_year)[0]) if re.findall(r"[\d\.]+", raw_year) else 0.0
            except: year = 0.0
            c.execute('''INSERT OR IGNORE INTO vehicle_data (vin, reg_date, car_no, manufacturer, model_name, model_year, junkyard, engine_code) VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', 
                      (vin, str(row['등록일자']), str(row['차량번호']), str(row['제조사']), str(row['차량명']), year, str(row['회원사']), str(row['원동기형식'])))
            if c.rowcount > 0: new_cnt += 1
            else: dup_cnt += 1
        conn.commit()
        if new_cnt > 0:
            with st.spinner("📍 위치 정보 업데이트 중..."): sync_junkyard_info(conn)
        conn.close()
        return new_cnt, dup_cnt
    except: return 0, 0

# ---------------------------------------------------------
# [성능최적화] 데이터 로드 캐싱
# ---------------------------------------------------------
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
            df['model_year'] = pd.to_numeric(df['model_year'], errors='coerce').fillna(0)
            # 날짜 변환 (월별 집계용)
            df['reg_date'] = pd.to_datetime(df['reg_date'], errors='coerce')
        return df
    except Exception: return pd.DataFrame()

# ---------------------------------------------------------
# 메인 어플리케이션 로직
# ---------------------------------------------------------
try:
    st.set_page_config(page_title="폐차 관제 시스템 Pro", layout="wide")
    
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    if 'view_data' not in st.session_state: 
        st.session_state['view_data'] = load_all_data()
        st.session_state['is_filtered'] = False

    df_all_source = load_all_data()

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
        with st.expander("📂 데이터 업로드"):
            up_files = st.file_uploader("파일 선택", type=['xlsx', 'xls', 'csv'], accept_multiple_files=True)
            if up_files and st.button("업로드"):
                if st.session_state.logged_in:
                    total_n, total_d = 0, 0
                    for f in up_files:
                        n, d = save_uploaded_file(f)
                        total_n += n
                        total_d += d
                    st.success(f"총 신규: {total_n}건")
                    load_all_data.clear()
                    st.session_state['view_data'] = load_all_data()
                    safe_rerun()
                else: st.warning("권한 없음")

        st.divider()
        
        search_tabs = st.tabs(["🚙 차량 검색", "🔧 엔진 검색", "🏭 폐차장 검색"])
        
        with search_tabs[0]:
            if not df_all_source.empty:
                makers = sorted(df_all_source['manufacturer'].unique().tolist())
                makers.insert(0, "전체")
                sel_maker = st.selectbox("제조사(브랜드)", makers, key="maker_sel")

                valid_years = df_all_source['model_year'][df_all_source['model_year'] > 0]
                max_y = int(valid_years.max()) if not valid_years.empty else 2025
                end_range = max(max_y, datetime.datetime.now().year)
                year_opts = list(range(1990, end_range + 2))
                
                c1, c2 = st.columns(2)
                with c1: 
                    start_idx = year_opts.index(2000) if 2000 in year_opts else 0
                    sel_start_y = st.selectbox("시작 연식", year_opts, index=start_idx, key="start_y")
                with c2: 
                    end_opts = [y for y in year_opts if y >= sel_start_y]
                    sel_end_y = st.selectbox("종료 연식", end_opts, index=len(end_opts)-1, key="end_y")
                    
                df_temp = df_all_source.copy()
                if sel_maker != "전체":
                    df_temp = df_temp[df_temp['manufacturer'] == sel_maker]
                df_temp = df_temp[(df_temp['model_year'] >= sel_start_y) & (df_temp['model_year'] <= sel_end_y)]
                
                avail_models = sorted(df_temp['model_name'].astype(str).unique().tolist())
                sel_models = st.multiselect(f"모델 선택 ({len(avail_models)}개)", avail_models, key="model_sel")
                
                st.markdown("")
                if st.button("✅ 차량 검색 적용", type="primary", use_container_width=True):
                    final_df = df_temp.copy()
                    if sel_models:
                        final_df = final_df[final_df['model_name'].astype(str).isin(sel_models)]
                    st.session_state['view_data'] = final_df.reset_index(drop=True)
                    st.session_state['is_filtered'] = True
                    safe_rerun()

        with search_tabs[1]:
            if not df_all_source.empty:
                st.caption("엔진코드(예: D4CB) 선택")
                all_engines = sorted(df_all_source['engine_code'].dropna().unique().tolist())
                sel_engines = st.multiselect("엔진코드", all_engines, key="eng_sel")
                
                st.markdown("")
                if st.button("🔧 엔진 검색 적용", type="primary", use_container_width=True):
                    engine_df = df_all_source.copy()
                    if sel_engines:
                        engine_df = engine_df[engine_df['engine_code'].isin(sel_engines)]
                    st.session_state['view_data'] = engine_df.reset_index(drop=True)
                    st.session_state['is_filtered'] = True
                    safe_rerun()

        with search_tabs[2]:
            if not df_all_source.empty:
                st.caption("폐차장 이름 검색")
                all_yards = sorted(df_all_source['junkyard'].dropna().unique().tolist())
                sel_yards = st.multiselect("폐차장 선택", all_yards, key="yard_sel")
                st.markdown("")
                if st.button("🏭 폐차장 검색 적용", type="primary", use_container_width=True):
                    yard_df = df_all_source.copy()
                    if sel_yards:
                        yard_df = yard_df[yard_df['junkyard'].isin(sel_yards)]
                    st.session_state['view_data'] = yard_df.reset_index(drop=True)
                    st.session_state['is_filtered'] = True
                    safe_rerun()
        
        if not df_all_source.empty:
            if st.button("🔄 전체 목록 보기", use_container_width=True):
                st.session_state['view_data'] = df_all_source
                st.session_state['is_filtered'] = False
                safe_rerun()

        if st.session_state.logged_in:
            st.divider()
            if st.button("🗑️ DB 초기화"):
                try:
                    conn = init_db()
                    conn.execute("DROP TABLE vehicle_data")
                    conn.execute("DROP TABLE junkyard_info")
                    conn.commit()
                    conn.close()
                    load_all_data.clear()
                    st.session_state['view_data'] = pd.DataFrame()
                    st.success("완료")
                    safe_rerun()
                except: pass

    # ------------------- 메인 컨텐츠 -------------------
    st.title("🚗 전국 폐차장 실시간 재고 현황")

    df_view = st.session_state['view_data']
    is_filtered = st.session_state['is_filtered']

    # 🔐 마스킹 처리
    if not st.session_state.logged_in and not df_view.empty:
        df_view = df_view.copy()
        df_view['junkyard'] = "🔒 회원전용"
        df_view['address'] = "🔒 비공개"
        df_view['region'] = "🔒"
        df_view['vin'] = "🔒 비공개"
        df_view['lat'] = 0.0
        df_view['lon'] = 0.0

    if not df_view.empty:
        mode = "🔍 검색 결과" if is_filtered else "📊 전체 현황"
        st.caption(f"모드: {mode} | 데이터: {len(df_view):,}건")
        
        if not is_filtered:
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            today_cnt = len(df_all_source[df_all_source['reg_date'].astype(str).str.contains(today)])
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("총 재고", f"{len(df_view):,}대")
            c2.metric("오늘 입고", f"{today_cnt}대")
            c3.metric("가맹점", "🔒" if not st.session_state.logged_in else f"{df_view['junkyard'].nunique()}곳")
            top_reg = df_view['region'].mode()[0] if 'region' in df_view.columns and not df_view['region'].empty else "-"
            c4.metric("최다 지역", "🔒" if not st.session_state.logged_in else top_reg)
        
        st.divider()
        
        # 지도 시각화
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
                    except Exception as e: st.error("지도 생성 중 오류")
                else: st.warning("위치 데이터 없음")
            else:
                st.warning("🔒 지도는 관리자(회원) 전용 기능입니다.")

        with col2:
            st.subheader("🏭 보유량 TOP")
            if 'junkyard' in df_view.columns:
                top_yards = df_view.groupby(['junkyard']).size().reset_index(name='수량').sort_values('수량', ascending=False).head(15)
                st.dataframe(top_yards, hide_index=True, height=400)

        st.divider()

        # [추가] 월별 입고 추이 그래프 (데이터가 존재할 경우 표시)
        if 'reg_date' in df_view.columns and not df_view.empty:
            st.subheader("📈 월별 입고 추이")
            # 날짜 컬럼이 datetime인지 확인 (로드 시 변환했지만 안전장치)
            df_view['reg_date'] = pd.to_datetime(df_view['reg_date'], errors='coerce')
            
            # 'YYYY-MM' 형태로 변환하여 그룹핑
            monthly_data = df_view.dropna(subset=['reg_date']).copy()
            if not monthly_data.empty:
                monthly_data['month'] = monthly_data['reg_date'].dt.strftime('%Y-%m')
                monthly_counts = monthly_data.groupby('month').size().reset_index(name='입고량')
                
                fig_line = px.line(monthly_counts, x='month', y='입고량', markers=True)
                fig_line.update_layout(xaxis_title="월(Month)", yaxis_title="입고 수량")
                st.plotly_chart(fig_line, use_container_width=True)
            else:
                st.info("날짜 데이터가 없어 추이 그래프를 표시할 수 없습니다.")
            
            st.divider()
        
        # [폐차장별 재고 요약 & 견적 요청]
        if is_filtered:
            st.subheader("📑 폐차장별 재고 요약 & 견적 요청")
            
            if st.session_state.logged_in:
                yard_summary = df_view.groupby(['junkyard', 'region', 'address']).size().reset_index(name='보유수량')
            else:
                yard_summary = df_view.groupby(['junkyard']).size().reset_index(name='보유수량')
                yard_summary['address'] = "🔒 비공개"
                yard_summary['region'] = "🔒"
            
            yard_summary = yard_summary.sort_values('보유수량', ascending=False)
            
            selection = st.dataframe(
                yard_summary,
                use_container_width=True,
                hide_index=True,
                selection_mode="single-row",
                on_select="rerun"
            )
            
            if len(selection.selection.rows) > 0:
                selected_idx = selection.selection.rows[0]
                selected_row = yard_summary.iloc[selected_idx]
                target_yard = selected_row['junkyard']
                
                st.info(f"📩 **{target_yard}**에 견적 요청 보내기")
                
                with st.form("quote_form"):
                    c_a, c_b = st.columns(2)
                    with c_a: 
                        st.text_input("수신 업체", value=target_yard, disabled=True)
                        st.text_input("신청자 연락처", placeholder="010-0000-0000")
                    with c_b:
                        st.text_input("요청 품목", value=f"검색된 {len(df_view)}대 차량 관련 부품 일체")
                        st.text_input("희망 단가", placeholder="예: 개당 00만원")
                    
                    msg_body = f"안녕하세요, {target_yard} 사장님.\n귀사에 보유 중인 아래 차량/엔진에 대한 견적을 요청드립니다.\n\n[요청 내역]\n- 대상 수량: {selected_row['보유수량']}대\n- 상세: (검색된 목록 기반)\n\n빠른 회신 부탁드립니다."
                    st.text_area("메시지 내용", value=msg_body, height=150)
                    
                    if st.form_submit_button("🚀 견적 요청서 발송"):
                        st.toast(f"✅ {target_yard} 앞으로 견적 요청이 발송되었습니다!", icon="📨")

            st.divider()
            
            st.subheader("📋 상세 차량 리스트")
            display_cols = ['reg_date', 'manufacturer', 'model_name', 'model_year', 'engine_code', 'junkyard', 'address', 'vin']
            valid_cols = [c for c in display_cols if c in df_view.columns]
            st.dataframe(df_view[valid_cols].sort_values('reg_date', ascending=False), use_container_width=True)
            
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
    else:
        st.info("데이터가 없습니다.")

except Exception as e:
    st.error("⛔ 앱 실행 중 문제가 발생했습니다.")
    with st.expander("상세 오류 보기"):
        st.code(traceback.format_exc())
