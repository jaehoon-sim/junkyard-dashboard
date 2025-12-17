# modules/db.py
import sqlite3
import pandas as pd
import datetime
import os
import re
import streamlit as st
import streamlit_authenticator as stauth
from modules.constants import RAW_TRANSLATIONS

INVENTORY_DB = 'data/inventory.db'
SYSTEM_DB = 'data/system.db'

# ---------------------------------------------------------
# 1. 초기화 및 유틸리티
# ---------------------------------------------------------

def init_dbs():
    if not os.path.exists('data'): os.makedirs('data')
    
    # Inventory DB (차량, 폐차장, 모델 데이터)
    conn = sqlite3.connect(INVENTORY_DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS vehicle_data (
        vin TEXT PRIMARY KEY, reg_date TEXT, car_no TEXT, manufacturer TEXT, 
        model_name TEXT, model_year REAL, junkyard TEXT, engine_code TEXT, 
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS junkyard_info (
        name TEXT PRIMARY KEY, address TEXT, region TEXT, lat REAL, lon REAL, 
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS model_list (
        manufacturer TEXT, model_name TEXT, PRIMARY KEY (manufacturer, model_name))''')
    
    # 인덱스 생성
    c.execute("CREATE INDEX IF NOT EXISTS idx_mfr ON vehicle_data(manufacturer)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_year ON vehicle_data(model_year)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_yard ON vehicle_data(junkyard)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_engine ON vehicle_data(engine_code)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_model ON vehicle_data(model_name)")
    conn.commit()
    conn.close()

    # System DB (사용자, 주문, 로그, 번역)
    conn = sqlite3.connect(SYSTEM_DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY, password TEXT, name TEXT, company TEXT, 
        country TEXT, email TEXT, phone TEXT, role TEXT DEFAULT 'buyer', 
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT, buyer_id TEXT, contact_info TEXT, 
        target_partner_alias TEXT, real_junkyard_name TEXT, items_summary TEXT, 
        status TEXT DEFAULT 'PENDING', reply_text TEXT, reply_images TEXT, 
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS search_logs_v2 (
        id INTEGER PRIMARY KEY AUTOINCREMENT, keyword TEXT, search_type TEXT, 
        country TEXT, city TEXT, lat REAL, lon REAL, 
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # 번역 데이터 초기화
    c.execute("DROP TABLE IF EXISTS translations")
    c.execute('''CREATE TABLE translations (
        key TEXT PRIMARY KEY, English TEXT, Korean TEXT, Russian TEXT, Arabic TEXT)''')
    
    raw_data = RAW_TRANSLATIONS
    keys = raw_data["English"].keys()
    data_to_insert = []
    for k in keys:
        row = (k, raw_data.get("English", {}).get(k, k), raw_data.get("Korean", {}).get(k, k),
               raw_data.get("Russian", {}).get(k, k), raw_data.get("Arabic", {}).get(k, k))
        data_to_insert.append(row)
    c.executemany("INSERT INTO translations VALUES (?, ?, ?, ?, ?)", data_to_insert)

    # Admin 계정 생성
    if not c.execute("SELECT * FROM users WHERE user_id = 'admin'").fetchone():
        try: admin_hash = stauth.Hasher(['1234']).generate()[0]
        except: admin_hash = stauth.Hasher().hash('1234')
        c.execute("INSERT INTO users (user_id, password, name, role) VALUES (?, ?, ?, ?)", 
                  ('admin', admin_hash, 'Administrator', 'admin'))
    
    # 기존 폐차장 정보를 바탕으로 파트너 계정 자동생성
    try:
        conn_inv = sqlite3.connect(INVENTORY_DB)
        junkyards = pd.read_sql("SELECT name FROM junkyard_info", conn_inv)['name'].unique()
        conn_inv.close()
        
        try: partner_pw = stauth.Hasher(['1234']).generate()[0]
        except: partner_pw = stauth.Hasher().hash('1234')
        
        for yard in junkyards:
            if yard and len(yard) > 1:
                if not c.execute("SELECT * FROM users WHERE user_id = ?", (yard,)).fetchone():
                    c.execute("INSERT INTO users (user_id, password, name, company, role) VALUES (?, ?, ?, ?, ?)",
                              (yard, partner_pw, "Partner Manager", yard, 'partner'))
    except: pass

    conn.commit()
    conn.close()

# ---------------------------------------------------------
# 2. 파일 처리 (업로드 및 스마트 파싱)
# ---------------------------------------------------------

def read_file_smart(uploaded_file):
    """확장자에 따라 적절한 엔진과 인코딩을 사용하여 데이터프레임으로 변환"""
    file_ext = uploaded_file.name.split('.')[-1].lower()
    
    if file_ext == 'csv':
        try:
            uploaded_file.seek(0)
            return pd.read_csv(uploaded_file, dtype=str)
        except UnicodeDecodeError:
            uploaded_file.seek(0)
            return pd.read_csv(uploaded_file, encoding='cp949', dtype=str)
    
    elif file_ext in ['xls', 'xlsx', 'xlsm']:
        engine = 'openpyxl' if file_ext in ['xlsx', 'xlsm'] else 'xlrd'
        try:
            uploaded_file.seek(0)
            return pd.read_excel(uploaded_file, engine=engine, dtype=str)
        except Exception:
            try:
                alt_engine = 'xlrd' if engine == 'openpyxl' else 'openpyxl'
                uploaded_file.seek(0)
                return pd.read_excel(uploaded_file, engine=alt_engine, dtype=str)
            except:
                return None
    return None

def find_header_row(df, keywords=['차대번호', 'vin', '차량번호']):
    """데이터프레임 상단에서 키워드가 포함된 행(Header)을 찾음"""
    # 1. 현재 컬럼명 검사
    for col in df.columns:
        if any(k in str(col).lower() for k in keywords):
            return 0, df

    # 2. 상위 10개 행 검사
    for i, row in df.head(10).iterrows():
        row_str = " ".join([str(x).lower() for x in row.values])
        if any(k in row_str for k in keywords):
            return i + 1, None
            
    return -1, None

def save_vehicle_file(uploaded_file):
    try:
        # 1. 파일 읽기
        df = read_file_smart(uploaded_file)
        if df is None: return 0

        # 2. 헤더 찾기
        header_row_idx, clean_df = find_header_row(df, keywords=['차대번호', 'vin'])
        
        if clean_df is None:
            if header_row_idx != -1:
                uploaded_file.seek(0)
                file_ext = uploaded_file.name.split('.')[-1].lower()
                read_params = {'header': header_row_idx, 'dtype': str}
                
                if file_ext == 'csv':
                    try: df = pd.read_csv(uploaded_file, **read_params)
                    except: df = pd.read_csv(uploaded_file, encoding='cp949', **read_params)
                else:
                    eng = 'openpyxl' if file_ext in ['xlsx', 'xlsm'] else 'xlrd'
                    df = pd.read_excel(uploaded_file, engine=eng, **read_params)
            else:
                return 0 # 헤더 못 찾음
        else:
            df = clean_df

        # 3. 데이터 정제
        df.columns = [str(c).strip() for c in df.columns]
        
        # 필수 컬럼 확인 (VIN)
        if '차대번호' not in df.columns and 'VIN' not in df.columns:
            col_map = {'VIN': '차대번호', 'vin': '차대번호'}
            df.rename(columns=col_map, inplace=True)
            if '차대번호' not in df.columns: return 0

        conn = sqlite3.connect(INVENTORY_DB)
        c = conn.cursor()
        
        df_db = pd.DataFrame()
        df_db['vin'] = df.get('차대번호', df.get('VIN', '')).fillna('').astype(str).str.strip()
        df_db['reg_date'] = df.get('등록일자', '').fillna('').astype(str)
        df_db['car_no'] = df.get('차량번호', '').fillna('').astype(str)
        df_db['manufacturer'] = df.get('제조사', '').fillna('').astype(str)
        df_db['model_name'] = df.get('차량명', df.get('모델명', '')).fillna('').astype(str)
        df_db['junkyard'] = df.get('회원사', df.get('업체명', '')).fillna('').astype(str)
        df_db['engine_code'] = df.get('원동기형식', df.get('엔진코드', '')).fillna('').astype(str)
        
        def parse_year(x):
            try: return float(re.findall(r"[\d\.]+", str(x))[0])
            except: return 0.0
        
        if '연식' in df.columns: df_db['model_year'] = df['연식'].apply(parse_year)
        else: df_db['model_year'] = 0.0
        
        # 임시 테이블을 통한 병합 (Upsert)
        df_db.to_sql('temp_vehicles', conn, if_exists='replace', index=False)
        c.execute('''INSERT OR IGNORE INTO vehicle_data 
                     (vin, reg_date, car_no, manufacturer, model_name, model_year, junkyard, engine_code) 
                     SELECT vin, reg_date, car_no, manufacturer, model_name, model_year, junkyard, engine_code 
                     FROM temp_vehicles''')
        c.execute("DROP TABLE temp_vehicles")
        
        # 모델 목록 업데이트
        c.execute("INSERT OR IGNORE INTO model_list (manufacturer, model_name) SELECT DISTINCT manufacturer, model_name FROM vehicle_data")
            
        # 폐차장 정보 저장
        yards = df_db['junkyard'].unique().tolist()
        for y in yards:
            if y and len(str(y)) > 1:
                c.execute("INSERT OR IGNORE INTO junkyard_info (name, address, region) VALUES (?, ?, ?)", (y, '검색실패', '기타'))
        conn.commit()
        conn.close()
        
        # Partner 계정 자동 생성
        conn_sys = sqlite3.connect(SYSTEM_DB)
        try: pw = stauth.Hasher(['1234']).generate()[0]
        except: pw = stauth.Hasher().hash('1234')
        for y in yards:
            if y and len(str(y)) > 1:
                if not conn_sys.execute("SELECT * FROM users WHERE user_id = ?", (y,)).fetchone():
                    conn_sys.execute("INSERT INTO users (user_id, password, name, company, role) VALUES (?, ?, ?, ?, ?)", 
                                     (y, pw, "Partner", y, 'partner'))
        conn_sys.commit()
        conn_sys.close()
        
        return len(df_db)
    except Exception as e:
        print(f"Error saving file: {e}")
        return 0

def save_address_file(uploaded_file):
    try:
        if uploaded_file.name.endswith('.csv'): df = pd.read_csv(uploaded_file, dtype=str)
        else: 
            try: df = pd.read_excel(uploaded_file, engine='openpyxl', dtype=str)
            except: df = pd.read_excel(uploaded_file, engine='xlrd', dtype=str)
            
        name_col = next((c for c in df.columns if '폐차장' in c or '업체' in c), None)
        addr_col = next((c for c in df.columns if '주소' in c), None)
        
        if not name_col or not addr_col: return 0
        
        conn = sqlite3.connect(INVENTORY_DB)
        cnt = 0
        for _, r in df.iterrows():
            nm, ad = str(r[name_col]).strip(), str(r[addr_col]).strip()
            reg = ad.split()[0][:2] if len(ad.split()) >= 1 else '기타'
            conn.execute("INSERT OR REPLACE INTO junkyard_info (name, address, region) VALUES (?, ?, ?)", (nm, ad, reg))
            cnt += 1
        conn.commit()
        conn.close()
        return cnt
    except: return 0

# ---------------------------------------------------------
# 3. 사용자 관리 및 인증
# ---------------------------------------------------------

def fetch_users_for_auth():
    try: admin_pw = stauth.Hasher(['1234']).generate()[0]
    except: admin_pw = stauth.Hasher().hash('1234')
    
    credentials = {'usernames': {'admin': {'name': 'Administrator', 'password': admin_pw, 'role': 'admin', 'email': '', 'phone': ''}}}
    try:
        conn = sqlite3.connect(SYSTEM_DB)
        rows = conn.execute("SELECT user_id, password, name, role, email, phone FROM users").fetchall()
        conn.close()
        for r in rows:
            credentials['usernames'][r[0]] = {
                'name': r[2], 
                'password': r[1], 
                'role': r[3],
                'email': r[4] if r[4] else '',
                'phone': r[5] if r[5] else ''
            }
    except: pass
    return credentials

def create_user(uid, pw, name, comp, country, email, phone):
    try:
        conn = sqlite3.connect(SYSTEM_DB)
        try: hashed_pw = stauth.Hasher([pw]).generate()[0]
        except: hashed_pw = stauth.Hasher().hash(pw)
        conn.execute("INSERT INTO users (user_id, password, name, company, country, email, phone) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                     (uid, hashed_pw, name, comp, country, email, phone))
        conn.commit()
        conn.close()
        return True
    except: return False

def update_user_info(user_id, email, phone):
    try:
        conn = sqlite3.connect(SYSTEM_DB)
        conn.execute("UPDATE users SET email = ?, phone = ? WHERE user_id = ?", (email, phone, user_id))
        conn.commit()
        conn.close()
        return True
    except: return False

def update_user_password(user_id, new_password):
    try:
        try: hashed_pw = stauth.Hasher([new_password]).generate()[0]
        except: hashed_pw = stauth.Hasher().hash(new_password)
        conn = sqlite3.connect(SYSTEM_DB)
        conn.execute("UPDATE users SET password = ? WHERE user_id = ?", (hashed_pw, user_id))
        conn.commit()
        conn.close()
        return True
    except: return False

def fetch_all_users():
    conn = sqlite3.connect(SYSTEM_DB)
    df = pd.read_sql("SELECT * FROM users", conn)
    conn.close()
    return df

def delete_user(uid):
    conn = sqlite3.connect(SYSTEM_DB)
    conn.execute("DELETE FROM users WHERE user_id = ?", (uid,))
    conn.commit()
    conn.close()

def update_user_role(uid, role):
    conn = sqlite3.connect(SYSTEM_DB)
    conn.execute("UPDATE users SET role = ? WHERE user_id = ?", (role, uid))
    conn.commit()
    conn.close()

# ---------------------------------------------------------
# 4. 데이터 조회 및 검색
# ---------------------------------------------------------

@st.cache_data(ttl=60)
def search_data(maker, models, engines, sy, ey, yards, sm, em):
    try:
        conn = sqlite3.connect(INVENTORY_DB)
        base_cond = "1=1"
        params = []
        
        if maker and maker != "All":
            base_cond += " AND v.manufacturer = ?"
            params.append(maker)
        
        base_cond += " AND v.model_year >= ? AND v.model_year <= ?"
        params.extend([sy, ey])
        
        base_cond += " AND strftime('%Y-%m', v.reg_date) >= ? AND strftime('%Y-%m', v.reg_date) <= ?"
        params.extend([sm, em])
        
        if models:
            base_cond += f" AND v.model_name IN ({','.join(['?']*len(models))})"
            params.extend(models)
        if engines:
            base_cond += f" AND v.engine_code IN ({','.join(['?']*len(engines))})"
            params.extend(engines)
        if yards:
            base_cond += f" AND v.junkyard IN ({','.join(['?']*len(yards))})"
            params.extend(yards)
        
        count = conn.execute(f"SELECT COUNT(*) FROM vehicle_data v WHERE {base_cond}", params).fetchone()[0]
        df = pd.read_sql(f"SELECT v.*, j.region, j.address FROM vehicle_data v LEFT JOIN junkyard_info j ON v.junkyard = j.name WHERE {base_cond} ORDER BY v.reg_date DESC LIMIT 5000", conn, params=params)
        conn.close()
        
        if not df.empty:
            df['model_year'] = pd.to_numeric(df['model_year'], errors='coerce').fillna(0)
            df['reg_date'] = pd.to_datetime(df['reg_date'], errors='coerce')
        return df, count
    except: return pd.DataFrame(), 0

@st.cache_data(ttl=300)
def load_metadata():
    conn = sqlite3.connect(INVENTORY_DB)
    df_m = pd.read_sql("SELECT DISTINCT manufacturer, model_name FROM model_list", conn)
    df_e = pd.read_sql("SELECT DISTINCT engine_code FROM vehicle_data", conn)
    df_y = pd.read_sql("SELECT name FROM junkyard_info", conn)
    try: months = pd.read_sql("SELECT DISTINCT strftime('%Y-%m', reg_date) as m FROM vehicle_data WHERE reg_date IS NOT NULL ORDER BY m DESC", conn)['m'].tolist()
    except: months = []
    
    total = conn.execute("SELECT COUNT(*) FROM vehicle_data").fetchone()[0]
    df_init = pd.read_sql("SELECT v.*, j.region, j.address FROM vehicle_data v LEFT JOIN junkyard_info j ON v.junkyard = j.name ORDER BY v.reg_date DESC LIMIT 5000", conn)
    conn.close()
    
    if not df_init.empty:
        df_init['model_year'] = pd.to_numeric(df_init['model_year'], errors='coerce').fillna(0)
        df_init['reg_date'] = pd.to_datetime(df_init['reg_date'], errors='coerce')
        
    return df_m, df_e['engine_code'].tolist(), df_y['name'].tolist(), months, df_init, total

def reset_dashboard():
    """검색 필터 및 세션 상태를 초기화"""
    m_df, m_eng, m_yards, m_mon, init_df, init_total = load_metadata()
    st.session_state.update({
        'view_data': init_df,
        'total_count': init_total,
        'models_df': m_df,
        'engines_list': m_eng,
        'yards_list': m_yards,
        'months_list': m_mon,
        'is_filtered': False,
        'mode_demand': False
    })

def log_search(kw, stype):
    try:
        conn = sqlite3.connect(SYSTEM_DB)
        if isinstance(kw, list):
            for k in kw: conn.execute("INSERT INTO search_logs_v2 (keyword, search_type) VALUES (?, ?)", (str(k), stype))
        else: conn.execute("INSERT INTO search_logs_v2 (keyword, search_type) VALUES (?, ?)", (str(kw), stype))
        conn.commit()
        conn.close()
    except: pass

def get_trends():
    try:
        conn = sqlite3.connect(SYSTEM_DB)
        e = pd.read_sql("SELECT keyword, COUNT(*) as count FROM search_logs_v2 WHERE search_type='engine' GROUP BY keyword ORDER BY count DESC LIMIT 10", conn)
        m = pd.read_sql("SELECT keyword, COUNT(*) as count FROM search_logs_v2 WHERE search_type='model' GROUP BY keyword ORDER BY count DESC LIMIT 10", conn)
        conn.close()
        return e, m
    except: return pd.DataFrame(), pd.DataFrame()

# ---------------------------------------------------------
# 5. 주문 및 번역
# ---------------------------------------------------------

def place_order(buyer_id, contact, target, real_target, summary):
    conn = sqlite3.connect(SYSTEM_DB)
    conn.execute("INSERT INTO orders (buyer_id, contact_info, target_partner_alias, real_junkyard_name, items_summary, status) VALUES (?, ?, ?, ?, ?, ?)",
                 (buyer_id, contact, target, real_target, summary, 'PENDING'))
    conn.commit()
    conn.close()

def get_orders(user_id, role):
    conn = sqlite3.connect(SYSTEM_DB)
    try:
        if role == 'admin': q = "SELECT * FROM orders ORDER BY created_at DESC"
        elif role == 'partner': q = f"SELECT * FROM orders WHERE real_junkyard_name = '{user_id}' ORDER BY created_at DESC"
        else: q = f"SELECT * FROM orders WHERE buyer_id = '{user_id}' ORDER BY created_at DESC"
        df = pd.read_sql(q, conn)
    except: df = pd.DataFrame()
    conn.close()
    return df

def update_order(oid, status=None, reply=None, imgs=None):
    conn = sqlite3.connect(SYSTEM_DB)
    if status: conn.execute("UPDATE orders SET status = ? WHERE id = ?", (status, oid))
    if reply: conn.execute("UPDATE orders SET reply_text = ? WHERE id = ?", (reply, oid))
    if imgs: conn.execute("UPDATE orders SET reply_images = ? WHERE id = ?", (imgs, oid))
    conn.commit()
    conn.close()

def load_translations():
    conn = sqlite3.connect(SYSTEM_DB)
    try: df = pd.read_sql("SELECT * FROM translations", conn)
    except: return {}
    conn.close()
    
    trans_dict = {}
    if not df.empty:
        for lang in ['English', 'Korean', 'Russian', 'Arabic']:
            if lang in df.columns: trans_dict[lang] = dict(zip(df['key'], df[lang]))
    return trans_dict