import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import datetime
import re
import os
import traceback

# ---------------------------------------------------------
# 🔐 [보안] 관리자 계정
# ---------------------------------------------------------
try:
    ADMIN_CREDENTIALS = st.secrets["ADMIN_CREDENTIALS"]
except:
    ADMIN_CREDENTIALS = {"admin": "1234"}

DB_NAME = 'junkyard.db'

# 📍 전국 시/군/구 단위 상세 좌표 데이터베이스 (주소 매핑용)
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
# 🛠️ [유틸] 안전한 Rerun
# ---------------------------------------------------------
def safe_rerun():
    try:
        st.rerun()
    except AttributeError:
        st.experimental_rerun()

# ---------------------------------------------------------
# 1. 데이터베이스 초기화
# ---------------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS vehicle_data (vin TEXT PRIMARY KEY, reg_date TEXT, car_no TEXT, manufacturer TEXT, model_name TEXT, model_year REAL, junkyard TEXT, engine_code TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS junkyard_info (name TEXT PRIMARY KEY, address TEXT, region TEXT, lat REAL, lon REAL, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS model_list (manufacturer TEXT, model_name TEXT, PRIMARY KEY (manufacturer, model_name))''')
    
    # 인덱스
    c.execute("CREATE INDEX IF NOT EXISTS idx_mfr ON vehicle_data(manufacturer)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_model ON vehicle_data(model_name)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_engine ON vehicle_data(engine_code)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_yard ON vehicle_data(junkyard)")
    conn.commit()
    return conn

def clean_name(name):
    # (주), 공백 등 제거
    return re.sub(r'\(주\)|주식회사|\(유\)|합자회사|유한회사|지점', '', str(name)).strip()

# ---------------------------------------------------------
# 2. 파일 업로드 처리 함수 (차량 데이터 / 주소 데이터)
# ---------------------------------------------------------
def save_vehicle_file(uploaded_file):
    """차량 입고 현황 파일 업로드"""
    try:
        if uploaded_file.name.endswith('.csv'): df = pd.read_csv(uploaded_file)
        else: 
            try: df = pd.read_excel(uploaded_file, engine='openpyxl')
            except: df = pd.read_excel(uploaded_file, engine='xlrd')

        # 헤더 찾기
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
        
        # 데이터프레임 생성
        df_db = pd.DataFrame()
        df_db['vin'] = df['차대번호'].astype(str).str.strip()
        df_db['reg_date'] = df['등록일자'].astype(str)
        df_db['car_no'] = df['차량번호'].astype(str)
        df_db['manufacturer'] = df['제조사'].astype(str)
        df_db['model_name'] = df['차량명'].astype(str)
        df_db['junkyard'] = df['회원사'].astype(str)
        df_db['engine_code'] = df['원동기형식'].astype(str)
        
        def parse_year(x):
            try: return float(re.findall(r"[\d\.]+", str(x))[0])
            except: return 0.0
        df_db['model_year'] = df['연식'].apply(parse_year)

        # Bulk Insert
        c.execute("CREATE TEMP TABLE IF NOT EXISTS temp_vehicles AS SELECT * FROM vehicle_data WHERE 0")
        df_db.to_sql('temp_vehicles', conn, if_exists='append', index=False)
        c.execute("""INSERT OR IGNORE INTO vehicle_data (vin, reg_date, car_no, manufacturer, model_name, model_year, junkyard, engine_code)
                     SELECT vin, reg_date, car_no, manufacturer, model_name, model_year, junkyard, engine_code FROM temp_vehicles""")
        
        new_cnt = len(df_db)
        c.execute("DROP TABLE temp_vehicles")
        
        # 모델 리스트 업데이트
        model_list_df = df_db[['manufacturer', 'model_name']].drop_duplicates()
        for _, row in model_list_df.iterrows():
            c.execute("INSERT OR IGNORE INTO model_list (manufacturer, model_name) VALUES (?, ?)", (row['manufacturer'], row['model_name']))
        
        conn.commit()
        conn.close()
        return new_cnt, 0
    except: return 0, 0

def save_address_file(uploaded_file):
    """[신규] 폐차장 주소 DB 파일 업로드"""
    try:
        if uploaded_file.name.endswith('.csv'): df = pd.read_csv(uploaded_file)
        else: 
            try: df = pd.read_excel(uploaded_file, engine='openpyxl')
            except: df = pd.read_excel(uploaded_file, engine='xlrd')
        
        # 컬럼명 유연하게 찾기 ('폐차장', '업체명', '회원사' 중 하나 / '주소', '소재지' 중 하나)
        name_col = next((c for c in df.columns if '폐차장' in c or '업체' in c or '회원' in c), None)
        addr_col = next((c for c in df.columns if '주소' in c or '소재' in c), None)
        
        if not name_col or not addr_col:
            st.error(f"필수 컬럼을 찾을 수 없습니다. (현재 컬럼: {list(df.columns)})")
            return 0

        conn = init_db()
        c = conn.cursor()
        update_cnt = 0
        
        for _, row in df.iterrows():
            yard_name = str(row[name_col]).strip()
            address = str(row[addr_col]).strip()
            
            # 1. 지역명(Region) 추출 (앞 두 글자)
            addr_parts = address.split()
            region = '기타'
            if len(addr_parts) >= 2:
                si_do = addr_parts[0][:2]
                si_gun = addr_parts[1]
                
                if si_do in ['서울', '인천', '대전', '대구', '광주', '부산', '울산', '제주', '세종']:
                    region = si_do
                else:
                    # 경기 이천, 충남 천안 형식으로 변환
                    gun_name = si_gun.replace('시','').replace('군','').replace('구','')
                    if len(gun_name) < 1: gun_name = si_gun
                    
                    # 매칭 시도
                    temp_key = f"{si_do} {gun_name}"
                    found = False
                    for k in CITY_COORDS.keys():
                        if temp_key in k or k in f"{si_do} {si_gun}":
                            region = k
                            found = True
                            break
                    if not found: region = f"{si_do} {si_gun}"
            elif len(addr_parts) == 1:
                region = addr_parts[0][:2]

            # 2. 좌표 매핑 (CITY_COORDS 사용)
            lat, lon = 0.0, 0.0
            
            # 정확한 키 매칭 시도
            if region in CITY_COORDS:
                lat, lon = CITY_COORDS[region]
            else:
                # 부분 일치 (예: 주소에 '수원'이 있으면 경기 수원 좌표 사용)
                for k, v in CITY_COORDS.items():
                    if k.split()[-1] in address:
                        region = k
                        lat, lon = v
                        break
            
            # 3. DB 업데이트 (이미 있으면 덮어쓰기)
            c.execute("""
                INSERT OR REPLACE INTO junkyard_info (name, address, region, lat, lon) 
                VALUES (?, ?, ?, ?, ?)
            """, (yard_name, address, region, lat, lon))
            update_cnt += 1
            
        conn.commit()
        conn.close()
        return update_cnt
    except Exception as e:
        st.error(f"주소 파일 처리 중 오류: {e}")
        return 0

# ---------------------------------------------------------
# [캐싱] 데이터 로드
# ---------------------------------------------------------
@st.cache_data(ttl=300)
def load_all_data():
    try:
        conn = init_db()
        # 차량 데이터와 폐차장 정보(주소)를 조인
        query = """
            SELECT v.*, j.region, j.lat, j.lon, j.address 
            FROM vehicle_data v 
            LEFT JOIN junkyard_info j ON v.junkyard = j.name
        """
        df = pd.read_sql(query, conn)
        conn.close()
        if not df.empty:
            df['model_name'] = df['model_name'].astype(str)
            df['manufacturer'] = df['manufacturer'].astype(str)
            df['engine_code'] = df['engine_code'].astype(str)
            df['junkyard'] = df['junkyard'].astype(str)
            df['model_year'] = pd.to_numeric(df['model_year'], errors='coerce').fillna(0)
            df['reg_date'] = pd.to_datetime(df['reg_date'], errors='coerce')
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
    st.set_page_config(page_title="폐차 관제 시스템 Pro", layout="wide")
    
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    if 'view_data' not in st.session_state: 
        st.session_state['view_data'] = load_all_data()
        st.session_state['is_filtered'] = False

    # 데이터 로드
    df_all_source = load_all_data()
    df_models = load_model_list()
    list_engines = load_engine_list()
    list_yards = load_yard_list()

    # 사이드바
    with st.sidebar:
        st.title("🛠️ 컨트롤 패널")
        
        # 로그인
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

        # 1. 차량 데이터 업로드
        with st.expander("📂 차량 데이터 업로드"):
            up_files = st.file_uploader("일일 입고 파일 (다중)", type=['xlsx', 'xls', 'csv'], accept_multiple_files=True, key="veh_up")
            if up_files and st.button("차량 DB 업로드"):
                if st.session_state.logged_in:
                    total_n = 0
                    bar = st.progress(0)
                    for i, f in enumerate(up_files):
                        n, _ = save_vehicle_file(f)
                        total_n += n
                        bar.progress((i+1)/len(up_files))
                    bar.empty()
                    st.success(f"차량 {total_n}대 저장 완료")
                    load_all_data.clear()
                    st.session_state['view_data'] = load_all_data()
                    safe_rerun()
                else: st.warning("관리자만 가능")

        # 2. 주소 데이터 업로드 (신규 추가)
        with st.expander("🏢 폐차장 주소 DB 업로드"):
            addr_file = st.file_uploader("주소 엑셀 파일", type=['xlsx', 'xls', 'csv'], key="addr_up")
            if addr_file and st.button("주소 DB 업데이트"):
                if st.session_state.logged_in:
                    cnt = save_address_file(addr_file)
                    st.success(f"폐차장 {cnt}곳 주소 업데이트 완료!")
                    load_all_data.clear()
                    st.session_state['view_data'] = load_all_data()
                    safe_rerun()
                else: st.warning("관리자만 가능")

        st.divider()
        
        # 검색 탭
        search_tabs = st.tabs(["🚙 차량", "🔧 엔진", "🏭 폐차장"])
        
        with search_tabs[0]:
            if not df_models.empty:
                makers = sorted(df_models['manufacturer'].unique().tolist())
                makers.insert(0, "전체")
                sel_maker = st.selectbox("제조사", makers, key="maker_sel")

                current_year = datetime.datetime.now().year
                year_opts = list(range(1990, current_year + 2))
                c1, c2 = st.columns(2)
                with c1: sel_start_y = st.selectbox("시작", year_opts, index=year_opts.index(2000), key="sy")
                with c2: 
                    end_opts = [y for y in year_opts if y >= sel_start_y]
                    sel_end_y = st.selectbox("종료", end_opts, index=len(end_opts)-1, key="ey")
                
                if sel_maker != "전체":
                    filtered_models = sorted(df_models[df_models['manufacturer'] == sel_maker]['model_name'].tolist())
                else:
                    filtered_models = sorted(df_models['model_name'].unique().tolist())
                
                sel_models = st.multiselect(f"모델 ({len(filtered_models)}개)", filtered_models, key="ms")
                
                st.markdown("")
                if st.button("✅ 차량 검색 적용", type="primary", use_container_width=True):
                    full_df = load_all_data()
                    if sel_maker != "전체": full_df = full_df[full_df['manufacturer'] == sel_maker]
                    full_df = full_df[(full_df['model_year'] >= sel_start_y) & (full_df['model_year'] <= sel_end_y)]
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
        
        if st.button("🔄 전체 목록 보기", use_container_width=True):
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

    # 메인
    st.title("🚗 전국 폐차장 실시간 재고 현황")
    df_view = st.session_state['view_data']
    is_filtered = st.session_state['is_filtered']

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
                    except: st.error("지도 오류")
                else: st.warning("위치 데이터 없음 (주소 DB를 업로드해주세요)")
            else: st.warning("🔒 지도는 관리자(회원) 전용 기능입니다.")

        with col2:
            st.subheader("🏭 보유량 TOP")
            if 'junkyard' in df_view.columns:
                top_yards = df_view.groupby(['junkyard']).size().reset_index(name='수량').sort_values('수량', ascending=False).head(15)
                st.dataframe(top_yards, width=None, use_container_width=True, hide_index=True, height=400)

        st.divider()
        
        if 'reg_date' in df_view.columns and not df_view.empty:
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
            st.subheader("📑 견적 요청")
            if st.session_state.logged_in:
                yard_summary = df_view.groupby(['junkyard', 'region', 'address']).size().reset_index(name='보유수량').sort_values('보유수량', ascending=False)
            else:
                yard_summary = df_view.groupby(['junkyard']).size().reset_index(name='보유수량').sort_values('보유수량', ascending=False)
                yard_summary['address'] = "🔒"
                yard_summary['region'] = "🔒"

            selection = st.dataframe(yard_summary, width=None, use_container_width=True, hide_index=True, selection_mode="single-row", on_select="rerun")
            
            if len(selection.selection.rows) > 0:
                sel_row = yard_summary.iloc[selection.selection.rows[0]]
                target = sel_row['junkyard']
                st.info(f"📩 **{target}** 견적 요청")
                with st.form("quote"):
                    c_a, c_b = st.columns(2)
                    with c_a: 
                        st.text_input("수신", value=target, disabled=True)
                        st.text_input("연락처", placeholder="010-0000-0000")
                    with c_b:
                        st.text_input("품목", value=f"검색 결과 {len(df_view)}건 관련")
                        st.text_input("희망가", placeholder="금액 입력")
                    st.text_area("내용", value=f"{target} 사장님, 보유하신 {sel_row['보유수량']}대에 대한 견적 문의드립니다.", height=100)
                    if st.form_submit_button("전송"): st.toast("발송 완료!", icon="📨")
            
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
    else:
        st.info("데이터가 없습니다.")
except Exception as e:
    st.error("앱 실행 중 오류")
    st.code(traceback.format_exc())
