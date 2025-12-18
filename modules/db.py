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
# 0. 데이터 표준화 규칙 (Mapping Rules)
# ---------------------------------------------------------
BRAND_MAP = {
    '현대': 'Hyundai', '현대자동차': 'Hyundai', 'HYUNDAI': 'Hyundai',
    '기아': 'Kia', '기아자동차': 'Kia', 'KIA': 'Kia',
    '제네시스': 'Genesis', 'GENESIS': 'Genesis',
    '르노삼성': 'Renault Korea', '르노코리아': 'Renault Korea',
    '쉐보레': 'Chevrolet', '지엠대우': 'Chevrolet',
    '쌍용': 'KGM', 'KG모빌리티': 'KGM', 'SsangYong': 'KGM',
    '벤츠': 'Mercedes-Benz', '메르세데스벤츠': 'Mercedes-Benz', 'Benz': 'Mercedes-Benz',
    '비엠더블유': 'BMW', '아우디': 'Audi', '폭스바겐': 'Volkswagen'
}

# 1차 매핑 (한글/영문 명칭 -> 표준 모델명)
MODEL_MAP = {
    # Hyundai
    '그랜저': 'Grandeur', '그랜져': 'Grandeur', '쏘나타': 'Sonata', '소나타': 'Sonata',
    '아반떼': 'Avante', '싼타페': 'Santa Fe', '산타페': 'Santa Fe', '투싼': 'Tucson',
    '팰리세이드': 'Palisade', '스타렉스': 'Starex', '스타리아': 'Staria',
    # Kia
    'K5': 'K5', 'K7': 'K7', 'K8': 'K8', 'K9': 'K9', '쏘렌토': 'Sorento',
    '카니발': 'Carnival', '스포티지': 'Sportage', '모닝': 'Morning', '레이': 'Ray',
    # Genesis
    'G80': 'G80', 'G90': 'G90', 'G70': 'G70', 'GV80': 'GV80', 'GV70': 'GV70',
    # Imports (한글 표기 대응)
    'S클래스': 'S-Class', 'E클래스': 'E-Class', 'C클래스': 'C-Class',
    '5시리즈': '5 Series', '3시리즈': '3 Series', '7시리즈': '7 Series',
    'GLE클래스': 'GLE', 'GLC클래스': 'GLC', 'GLS클래스': 'GLS'
}

BRAND_REMOVE_REGEX = r"^(현대|기아|제네시스|르노|쉐보레|쌍용|벤츠|메르세데스|비엠|아우디|폭스바겐|HYUNDAI|KIA|GENESIS|BENZ|BMW|AUDI)\s*"

# ---------------------------------------------------------
# 1. 초기화 및 유틸리티
# ---------------------------------------------------------

def init_dbs():
    if not os.path.exists('data'): os.makedirs('data')
    
    # Inventory DB
    conn = sqlite3.connect(INVENTORY_DB)
    c = conn.cursor()
    
    # 테이블 생성 (model_detail 컬럼 포함)
    c.execute('''CREATE TABLE IF NOT EXISTS vehicle_data (
        vin TEXT PRIMARY KEY, reg_date TEXT, car_no TEXT, manufacturer TEXT, 
        model_name TEXT, model_detail TEXT, model_year REAL, junkyard TEXT, engine_code TEXT, 
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # 기존 테이블에 model_detail 컬럼이 없는 경우 추가 (Migration)
    try:
        c.execute("ALTER TABLE vehicle_data ADD COLUMN model_detail TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass 

    c.execute('''CREATE TABLE IF NOT EXISTS junkyard_info (
        name TEXT PRIMARY KEY, address TEXT, region TEXT, lat REAL, lon REAL, 
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS model_list (
        manufacturer TEXT, model_name TEXT, PRIMARY KEY (manufacturer, model_name))''')
    
    # 인덱스
    c.execute("CREATE INDEX IF NOT EXISTS idx_mfr ON vehicle_data(manufacturer)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_model ON vehicle_data(model_name)")
    conn.commit()
    conn.close()

    # System DB
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
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # 번역 데이터
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

    # Admin 생성
    if not c.execute("SELECT * FROM users WHERE user_id = 'admin'").fetchone():
        try: admin_hash = stauth.Hasher(['1234']).generate()[0]
        except: admin_hash = stauth.Hasher().hash('1234')
        c.execute("INSERT INTO users (user_id, password, name, role) VALUES (?, ?, ?, ?)", 
                  ('admin', admin_hash, 'Administrator', 'admin'))
    
    conn.commit()
    conn.close()

# ---------------------------------------------------------
# 2. 파일 처리 및 데이터 표준화 (스마트 로직 포함)
# ---------------------------------------------------------

def detect_german_model(text):
    """벤츠/BMW의 모델명 패턴(E220, 520d 등)을 분석하여 대표 모델을 반환"""
    text = text.upper().replace(" ", "")
    
    # Mercedes-Benz Patterns
    if re.match(r"^E\d{3}", text): return "E-Class"
    if re.match(r"^S\d{3}", text): return "S-Class"
    if re.match(r"^C\d{3}", text): return "C-Class"
    if text.startswith("GLE"): return "GLE"
    if text.startswith("GLC"): return "GLC"
    if text.startswith("GLS"): return "GLS"
    if text.startswith("CLA"): return "CLA"
    
    # BMW Patterns
    if re.match(r"^5\d{2}", text): return "5 Series"
    if re.match(r"^3\d{2}", text): return "3 Series"
    if re.match(r"^7\d{2}", text): return "7 Series"
    if text.startswith("X5"): return "X5"
    if text.startswith("X3"): return "X3"
    if text.startswith("X7"): return "X7"
    if text.startswith("X6"): return "X6"
    
    return None

def normalize_row(row):
    """행 단위 데이터 표준화 (브랜드/모델/세부모델 분리)"""
    raw_mfr = str(row.get('manufacturer', '')).strip()
    raw_model = str(row.get('model_name', '')).strip()
    
    # 1. 브랜드 표준화
    std_mfr = BRAND_MAP.get(raw_mfr, raw_mfr)
    if std_mfr == '현대': std_mfr = 'Hyundai'
    
    # 2. 모델명 정리 (브랜드명 제거)
    clean_model = re.sub(BRAND_REMOVE_REGEX, "", raw_model, flags=re.IGNORECASE).strip()
    
    std_model = clean_model
    std_detail = ""

    # 3. 모델/세부모델 분리 로직
    # [Step A] 1차 매핑 테이블 확인
    mapped = False
    for k, v in MODEL_MAP.items():
        if clean_model.startswith(k) or clean_model.upper().startswith(k.upper()):
            std_model = v
            det = re.sub(k, "", clean_model, flags=re.IGNORECASE).strip()
            std_detail = det if det else std_detail
            mapped = True
            break
            
    # [Step B] 독일 3사 패턴 매칭
    if not mapped:
        german_detected = detect_german_model(clean_model)
        if german_detected:
            std_model = german_detected
            if std_detail == "": std_detail = clean_model # 모델명 전체를 세부모델로 보존
            mapped = True

    # [Step C] 기본 분리 (공백 기준)
    if not mapped:
        parts = clean_model.split()
        if len(parts) >= 2:
            std_model = parts[0]
            std_detail = " ".join(parts[1:])
        else:
            std_model = clean_model

    # 특수문자 제거
    std_detail = std_detail.replace("(", "").replace(")", "").strip()
            
    return std_mfr, std_model, std_detail

def read_file_smart(uploaded_file):
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
        except:
            try:
                uploaded_file.seek(0)
                eng = 'xlrd' if engine == 'openpyxl' else 'openpyxl'
                return pd.read_excel(uploaded_file, engine=eng, dtype=str)
            except: return None
    return None

def find_header_row(df, keywords=['차대번호', 'vin']):
    for col in df.columns:
        if any(k in str(col).lower() for k in keywords): return 0, df
    for i, row in df.head(10).iterrows():
        if any(k in " ".join([str(x).lower() for x in row.values]) for k in keywords):
            return i + 1, None
    return -1, None

def save_vehicle_file(uploaded_file):
    try:
        df = read_file_smart(uploaded_file)
        if df is None: return 0

        header_idx, clean_df = find_header_row(df)
        if clean_df is None:
            if header_idx != -1:
                uploaded_file.seek(0)
                file_ext = uploaded_file.name.split('.')[-1].lower()
                p = {'header': header_idx, 'dtype': str}
                if file_ext == 'csv':
                    try: df = pd.read_csv(uploaded_file, **p)
                    except: df = pd.read_csv(uploaded_file, encoding='cp949', **p)
                else:
                    e = 'openpyxl' if file_ext in ['xlsx'] else 'xlrd'
                    df = pd.read_excel(uploaded_file, engine=e, **p)
            else: return 0
        else: df = clean_df

        df.columns = [str(c).strip() for c in df.columns]
        if '차대번호' not in df.columns and 'VIN' not in df.columns:
            df.rename(columns={'VIN': '차대번호', 'vin': '차대번호'}, inplace=True)
            if '차대번호' not in df.columns: return 0

        db_rows = []
        for _, row in df.iterrows():
            mfr = row.get('제조사', '').strip()
            mod = row.get('차량명', row.get('모델명', '')).strip()
            std_mfr, std_mod, std_det = normalize_row({'manufacturer': mfr, 'model_name': mod})
            
            vin = row.get('차대번호', '').strip()
            reg = row.get('등록일자', '').strip()
            no = row.get('차량번호', '').strip()
            yard = row.get('회원사', row.get('업체명', '')).strip()
            eng = row.get('원동기형식', row.get('엔진코드', '')).strip()
            
            try: year = float(re.findall(r"[\d\.]+", str(row.get('연식', 0)))[0])
            except: year = 0.0
            
            db_rows.append((vin, reg, no, std_mfr, std_mod, std_det, year, yard, eng))

        conn = sqlite3.connect(INVENTORY_DB)
        c = conn.cursor()
        c.executemany('''INSERT OR REPLACE INTO vehicle_data 
                         (vin, reg_date, car_no, manufacturer, model_name, model_detail, model_year, junkyard, engine_code) 
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', db_rows)
        
        c.execute("INSERT OR IGNORE INTO model_list (manufacturer, model_name) SELECT DISTINCT manufacturer, model_name FROM vehicle_data")
        
        yards = set([r[7] for r in db_rows if r[7] and len(r[7]) > 1])
        for y in yards:
            c.execute("INSERT OR IGNORE INTO junkyard_info (name, address, region) VALUES (?, ?, ?)", (y, '검색실패', '기타'))
        conn.commit()
        conn.close()
        
        conn_sys = sqlite3.connect(SYSTEM_DB)
        try: pw = stauth.Hasher(['1234']).generate()[0]
        except: pw = stauth.Hasher().hash('1234')
        for y in yards:
            if not conn_sys.execute("SELECT * FROM users WHERE user_id = ?", (y,)).fetchone():
                conn_sys.execute("INSERT INTO users (user_id, password, name, company, role) VALUES (?, ?, ?, ?, ?)", (y, pw, "Partner", y, 'partner'))
        conn_sys.commit()
        conn_sys.close()
        
        return len(db_rows)
    except Exception as e:
        print(f"Error: {e}")
        return 0

def save_address_file(uploaded_file):
    try:
        df = read_file_smart(uploaded_file)
        if df is None: return 0
        name_col = next((c for c in df.columns if '폐차장' in c or '업체' in c), None)
        addr_col = next((c for c in df.columns if '주소' in c), None)
        if not name_col: return 0
        
        conn = sqlite3.connect(INVENTORY_DB)
        cnt = 0
        for _, r in df.iterrows():
            nm, ad = str(r[name_col]).strip(), str(r.get(addr_col, '')).strip()
            reg = ad.split()[0][:2] if len(ad.split()) >= 1 else '기타'
            conn.execute("INSERT OR REPLACE INTO junkyard_info (name, address, region) VALUES (?, ?, ?)", (nm, ad, reg))
            cnt += 1
        conn.commit()
        conn.close()
        return cnt
    except: return 0

# ---------------------------------------------------------
# 3. 사용자 관리
# ---------------------------------------------------------

def fetch_users_for_auth():
    try: admin_pw = stauth.Hasher(['1234']).generate()[0]
    except: admin_pw = stauth.Hasher().hash('1234')
    creds = {'usernames': {'admin': {'name': 'Administrator', 'password': admin_pw, 'role': 'admin', 'email': '', 'phone': ''}}}
    try:
        conn = sqlite3.connect(SYSTEM_DB)
        for r in conn.execute("SELECT user_id, password, name, role, email, phone FROM users").fetchall():
            creds['usernames'][r[0]] = {'name': r[2], 'password': r[1], 'role': r[3], 'email': r[4] or '', 'phone': r[5] or ''}
        conn.close()
    except: pass
    return creds

def create_user(uid, pw, name, comp, country, email, phone):
    try:
        conn = sqlite3.connect(SYSTEM_DB)
        try: hpw = stauth.Hasher([pw]).generate()[0]
        except: hpw = stauth.Hasher().hash(pw)
        conn.execute("INSERT INTO users (user_id, password, name, company, country, email, phone) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                     (uid, hpw, name, comp, country, email, phone))
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

def update_user_password(user_id, new_pw):
    try:
        try: hpw = stauth.Hasher([new_pw]).generate()[0]
        except: hpw = stauth.Hasher().hash(new_pw)
        conn = sqlite3.connect(SYSTEM_DB)
        conn.execute("UPDATE users SET password = ? WHERE user_id = ?", (hpw, user_id))
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
# 4. 조회 및 검색
# ---------------------------------------------------------

@st.cache_data(ttl=60)
def search_data(maker, models, details, engines, sy, ey, yards, sm, em):
    try:
        conn = sqlite3.connect(INVENTORY_DB)
        cond, params = "1=1", []
        if maker and maker != "All":
            cond += " AND v.manufacturer = ?"; params.append(maker)
        cond += " AND v.model_year >= ? AND v.model_year <= ?"; params.extend([sy, ey])
        cond += " AND strftime('%Y-%m', v.reg_date) >= ? AND strftime('%Y-%m', v.reg_date) <= ?"; params.extend([sm, em])
        if models:
            cond += f" AND v.model_name IN ({','.join(['?']*len(models))})"; params.extend(models)
        if details:
            cond += f" AND v.model_detail IN ({','.join(['?']*len(details))})"; params.extend(details)
        if engines:
            cond += f" AND v.engine_code IN ({','.join(['?']*len(engines))})"; params.extend(engines)
        if yards:
            cond += f" AND v.junkyard IN ({','.join(['?']*len(yards))})"; params.extend(yards)
        
        q = f"SELECT v.vin, v.reg_date, v.car_no, v.manufacturer, v.model_name, v.model_detail, v.model_year, v.junkyard, v.engine_code, j.region, j.address FROM vehicle_data v LEFT JOIN junkyard_info j ON v.junkyard = j.name WHERE {cond} ORDER BY v.reg_date DESC LIMIT 5000"
        
        count = conn.execute(f"SELECT COUNT(*) FROM vehicle_data v WHERE {cond}", params).fetchone()[0]
        df = pd.read_sql(q, conn, params=params)
        conn.close()
        
        if not df.empty:
            df['model_year'] = pd.to_numeric(df['model_year'], errors='coerce').fillna(0)
            df['reg_date'] = pd.to_datetime(df['reg_date'], errors='coerce')
        return df, count
    except: return pd.DataFrame(), 0

@st.cache_data(ttl=300)
def load_metadata():
    conn = sqlite3.connect(INVENTORY_DB)
    # 3-Depth 구조를 위한 model_detail 포함
    query = """
        SELECT DISTINCT manufacturer, model_name, model_detail 
        FROM vehicle_data 
        WHERE manufacturer IS NOT NULL AND manufacturer != ''
        ORDER BY manufacturer, model_name, model_detail
    """
    df_m = pd.read_sql(query, conn)
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
    m_df, m_eng, m_yards, m_mon, init_df, init_total = load_metadata()
    st.session_state.update({
        'view_data': init_df, 'total_count': init_total, 'models_df': m_df,
        'engines_list': m_eng, 'yards_list': m_yards, 'months_list': m_mon,
        'is_filtered': False, 'mode_demand': False
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
# 5. 주문 처리 및 유지보수
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

def standardize_existing_data():
    """기존 DB 데이터 전체에 대해 표준화 로직 재적용"""
    try:
        conn = sqlite3.connect(INVENTORY_DB)
        c = conn.cursor()
        try: c.execute("ALTER TABLE vehicle_data ADD COLUMN model_detail TEXT DEFAULT ''")
        except: pass 
        df = pd.read_sql("SELECT vin, manufacturer, model_name FROM vehicle_data", conn)
        updates = []
        for _, row in df.iterrows():
            std_mfr, std_mod, std_det = normalize_row(row)
            updates.append((std_mfr, std_mod, std_det, row['vin']))
        if updates:
            c.executemany("UPDATE vehicle_data SET manufacturer = ?, model_name = ?, model_detail = ? WHERE vin = ?", updates)
            c.execute("DELETE FROM model_list")
            c.execute("INSERT OR IGNORE INTO model_list (manufacturer, model_name) SELECT DISTINCT manufacturer, model_name FROM vehicle_data")
            conn.commit()
        cnt = len(updates)
        conn.close()
        return True, cnt
    except Exception as e: return False, str(e)