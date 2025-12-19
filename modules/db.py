# modules/db.py
import sqlite3
import pandas as pd
import datetime
import os
import re
import shutil
import streamlit as st
import streamlit_authenticator as stauth
from modules.constants import RAW_TRANSLATIONS

INVENTORY_DB = 'data/inventory.db'
SYSTEM_DB = 'data/system.db'
IMAGE_DIR = 'data/vehicle_images'

# ---------------------------------------------------------
# 0. 데이터 표준화 규칙
# ---------------------------------------------------------
GARBAGE_TERMS = [
    'MERCEDES-BENZ', 'MERCEDES-AMG', 'MERCEDES-MAYBACH', 'BENZ', 
    'BMW', 'AUDI', 'VOLKSWAGEN', 'HYUNDAI', 'KIA', 'CHEVROLET',
    'LIMITED', 'SPECIAL', 'EDITION'
]

BRAND_MAP = {
    '현대': 'Hyundai', '현대자동차': 'Hyundai', 'HYUNDAI': 'Hyundai',
    '기아': 'Kia', '기아자동차': 'Kia', 'KIA': 'Kia',
    '제네시스': 'Genesis', 'GENESIS': 'Genesis',
    '르노삼성': 'Renault Korea', '르노코리아': 'Renault Korea', 'Samsung': 'Renault Korea',
    '쉐보레': 'Chevrolet', '지엠대우': 'Chevrolet',
    '쌍용': 'KGM', 'KG모빌리티': 'KGM', 'SsangYong': 'KGM',
    '벤츠': 'Mercedes-Benz', '메르세데스벤츠': 'Mercedes-Benz', 'Benz': 'Mercedes-Benz',
    '비엠더블유': 'BMW', '아우디': 'Audi', '폭스바겐': 'Volkswagen', '볼보': 'Volvo',
    '렉서스': 'Lexus', '도요타': 'Toyota', '혼다': 'Honda', '니산': 'Nissan',
    '랜드로버': 'Land Rover', '포르쉐': 'Porsche', '미니': 'Mini', '재규어': 'Jaguar',
    '지프': 'Jeep', '포드': 'Ford'
}

MODEL_MAP = {
    '그랜저': 'Grandeur', '그랜져': 'Grandeur', '쏘나타': 'Sonata', '소나타': 'Sonata',
    '아반떼': 'Avante', '싼타페': 'Santa Fe', '산타페': 'Santa Fe', '투싼': 'Tucson',
    '팰리세이드': 'Palisade', '스타렉스': 'Starex', '스타리아': 'Staria', '베뉴': 'Venue', '코나': 'Kona',
    'K3': 'K3', 'K5': 'K5', 'K7': 'K7', 'K8': 'K8', 'K9': 'K9', '쏘렌토': 'Sorento',
    '카니발': 'Carnival', '스포티지': 'Sportage', '모닝': 'Morning', '레이': 'Ray', '셀토스': 'Seltos', '니로': 'Niro',
    'G70': 'G70', 'G80': 'G80', 'G90': 'G90', 'GV60': 'GV60', 'GV70': 'GV70', 'GV80': 'GV80',
    'S클래스': 'S-Class', 'E클래스': 'E-Class', 'C클래스': 'C-Class', 
    'A클래스': 'A-Class', 'B클래스': 'B-Class',
    'GLE클래스': 'GLE', 'GLC클래스': 'GLC', 'GLS클래스': 'GLS', 
    'CLA클래스': 'CLA', 'CLS클래스': 'CLS', 'G클래스': 'G-Class',
    'M클래스': 'M-Class', 'ML클래스': 'M-Class',
    '1시리즈': '1 Series', '2시리즈': '2 Series', '3시리즈': '3 Series',
    '4시리즈': '4 Series', '5시리즈': '5 Series', '6시리즈': '6 Series',
    '7시리즈': '7 Series', '8시리즈': '8 Series',
    'X1': 'X1', 'X2': 'X2', 'X3': 'X3', 'X4': 'X4', 'X5': 'X5', 'X6': 'X6', 'X7': 'X7',
    '골프': 'Golf', '티구안': 'Tiguan', '파사트': 'Passat', '아테온': 'Arteon', '제타': 'Jetta', '투아렉': 'Touareg',
    '카이엔': 'Cayenne', '파나메라': 'Panamera', '마칸': 'Macan', '타이칸': 'Taycan', '박스터': 'Boxster', '카이맨': 'Cayman', '911': '911',
    '레인지로버': 'Range Rover', '디스커버리': 'Discovery', '디펜더': 'Defender',
    '캠리': 'Camry', '라브4': 'RAV4', '프리우스': 'Prius', '시에나': 'Sienna',
    '어코드': 'Accord', '시빅': 'Civic', 'CR-V': 'CR-V', '파일럿': 'Pilot',
    '익스플로러': 'Explorer', '머스탱': 'Mustang', '랭글러': 'Wrangler', '체로키': 'Cherokee'
}

BRAND_REMOVE_REGEX = r"^(현대|기아|제네시스|르노|쉐보레|쌍용|벤츠|메르세데스|비엠|아우디|폭스바겐|볼보|렉서스|도요타|혼다|닛산|랜드로버|포르쉐|미니|재규어|지프|포드|HYUNDAI|KIA|GENESIS|BENZ|BMW|AUDI|VOLVO|LEXUS|TOYOTA|HONDA|NISSAN|LANDROVER|PORSCHE|MINI|JAGUAR|JEEP|FORD)\s*"

# ---------------------------------------------------------
# 1. 초기화 및 유틸리티
# ---------------------------------------------------------
def init_dbs():
    if not os.path.exists('data'): os.makedirs('data')
    if not os.path.exists(IMAGE_DIR): os.makedirs(IMAGE_DIR)
    
    conn = sqlite3.connect(INVENTORY_DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS vehicle_data (
        vin TEXT PRIMARY KEY, reg_date TEXT, car_no TEXT, manufacturer TEXT, 
        model_name TEXT, model_detail TEXT, model_year REAL, junkyard TEXT, engine_code TEXT, 
        price REAL DEFAULT 0, mileage REAL DEFAULT 0, photos TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    try: c.execute("ALTER TABLE vehicle_data ADD COLUMN model_detail TEXT DEFAULT ''")
    except: pass
    try: c.execute("ALTER TABLE vehicle_data ADD COLUMN price REAL DEFAULT 0")
    except: pass
    try: c.execute("ALTER TABLE vehicle_data ADD COLUMN mileage REAL DEFAULT 0")
    except: pass
    try: c.execute("ALTER TABLE vehicle_data ADD COLUMN photos TEXT DEFAULT ''")
    except: pass

    c.execute('''CREATE TABLE IF NOT EXISTS junkyard_info (
        name TEXT PRIMARY KEY, address TEXT, region TEXT, lat REAL, lon REAL, 
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS model_list (
        manufacturer TEXT, model_name TEXT, PRIMARY KEY (manufacturer, model_name))''')
    conn.commit()
    conn.close()

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
    
    c.execute("DROP TABLE IF EXISTS translations")
    c.execute('''CREATE TABLE translations (
        key TEXT PRIMARY KEY, English TEXT, Korean TEXT, Russian TEXT, Arabic TEXT)''')
    
    raw_data = RAW_TRANSLATIONS if 'RAW_TRANSLATIONS' in globals() else {}
    if raw_data:
        keys = raw_data.get("English", {}).keys()
        data_to_insert = []
        for k in keys:
            row = (k, raw_data.get("English", {}).get(k, k), raw_data.get("Korean", {}).get(k, k),
                   raw_data.get("Russian", {}).get(k, k), raw_data.get("Arabic", {}).get(k, k))
            data_to_insert.append(row)
        c.executemany("INSERT INTO translations VALUES (?, ?, ?, ?, ?)", data_to_insert)

    if not c.execute("SELECT * FROM users WHERE user_id = 'admin'").fetchone():
        try: admin_hash = stauth.Hasher(['1234']).generate()[0]
        except: admin_hash = stauth.Hasher().hash('1234')
        c.execute("INSERT INTO users (user_id, password, name, role, company) VALUES (?, ?, ?, ?, ?)", 
                  ('admin', admin_hash, 'Administrator', 'admin', 'AdminHQ'))
    conn.commit()
    conn.close()

# ---------------------------------------------------------
# 파일 처리 및 표준화
# ---------------------------------------------------------
def detect_global_pattern(text):
    text = text.upper().replace(" ", "")
    if re.match(r"^([ABCEGS])\d{2,3}", text): return f"{text[0]}-Class"
    return None 

def normalize_row(row):
    raw_mfr = str(row.get('manufacturer', '')).strip()
    raw_model = str(row.get('model_name', '')).strip()
    std_mfr = BRAND_MAP.get(raw_mfr, raw_mfr)
    if std_mfr == '현대': std_mfr = 'Hyundai' 
    clean_model = re.sub(BRAND_REMOVE_REGEX, "", raw_model, flags=re.IGNORECASE).strip()
    if clean_model.upper() in GARBAGE_TERMS: clean_model = "Unknown" 
    std_model = clean_model
    std_detail = ""
    mapped = False
    for k, v in MODEL_MAP.items():
        if clean_model.upper() == k.upper() or clean_model.upper().startswith(k.upper()):
            std_model = v
            if clean_model.upper() == k.upper(): std_detail = ""
            else:
                det = re.sub(k, "", clean_model, flags=re.IGNORECASE).strip()
                std_detail = det if det else ""
            mapped = True
            break
    std_detail = std_detail.replace("(", "").replace(")", "").strip()
    if std_model.upper() in GARBAGE_TERMS: std_model = "Unknown"
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
        
        # 자동 파트너 생성
        conn_sys = sqlite3.connect(SYSTEM_DB)
        try: pw = stauth.Hasher(['1234']).generate()[0]
        except: pw = stauth.Hasher().hash('1234')
        for y in yards:
            if not conn_sys.execute("SELECT * FROM users WHERE user_id = ?", (y,)).fetchone():
                conn_sys.execute("INSERT INTO users (user_id, password, name, company, role) VALUES (?, ?, ?, ?, ?)", (y, pw, "Partner", y, 'partner'))
        conn_sys.commit()
        conn_sys.close()
        return len(db_rows)
    except Exception as e: return 0

# ---------------------------------------------------------
# 사용자 관리 (Company 포함)
# ---------------------------------------------------------
def fetch_users_for_auth():
    try: admin_pw = stauth.Hasher(['1234']).generate()[0]
    except: admin_pw = stauth.Hasher().hash('1234')
    
    creds = {'usernames': {'admin': {'name': 'Administrator', 'password': admin_pw, 'role': 'admin', 'email': '', 'phone': '', 'company': 'AdminHQ'}}}
    
    try:
        conn = sqlite3.connect(SYSTEM_DB)
        for r in conn.execute("SELECT user_id, password, name, role, email, phone, company FROM users").fetchall():
            creds['usernames'][r[0]] = {
                'name': r[2], 
                'password': r[1], 
                'role': r[3], 
                'email': r[4] or '', 
                'phone': r[5] or '',
                'company': r[6] or ''
            }
        conn.close()
    except: pass
    return creds

def create_user(uid, pw, name, comp, country, email, phone):
    try:
        conn = sqlite3.connect(SYSTEM_DB)
        try: hpw = stauth.Hasher([pw]).generate()[0]
        except: hpw = stauth.Hasher().hash(pw)
        conn.execute("INSERT INTO users (user_id, password, name, company, country, email, phone, role) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
                     (uid, hpw, name, comp, country, email, phone, 'buyer'))
        conn.commit()
        conn.close()
        return True
    except: return False

def create_user_bulk(user_data_list):
    conn = sqlite3.connect(SYSTEM_DB)
    c = conn.cursor()
    success_count, fail_count = 0, 0
    try: default_pw = stauth.Hasher(['1234']).generate()[0]
    except: default_pw = stauth.Hasher().hash('1234')

    for user in user_data_list:
        try:
            email = user.get('email', '')
            if not email: 
                fail_count += 1
                continue
            c.execute('''INSERT INTO users (user_id, password, name, company, country, email, phone, role) 
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', 
                      (email, default_pw, user.get('name', 'User'), 
                       user.get('company', ''), user.get('country', ''), 
                       email, str(user.get('phone', '')), 'buyer'))
            success_count += 1
        except: fail_count += 1
    conn.commit()
    conn.close()
    return success_count, fail_count

def update_user_role(uid, role):
    conn = sqlite3.connect(SYSTEM_DB)
    conn.execute("UPDATE users SET role = ? WHERE user_id = ?", (role, uid))
    conn.commit()
    conn.close()

def update_user_info(uid, email, phone):
    conn = sqlite3.connect(SYSTEM_DB)
    conn.execute("UPDATE users SET email = ?, phone = ? WHERE user_id = ?", (email, phone, uid))
    conn.commit()
    conn.close()

def delete_user(uid):
    conn = sqlite3.connect(SYSTEM_DB)
    conn.execute("DELETE FROM users WHERE user_id = ?", (uid,))
    conn.commit()
    conn.close()

def fetch_all_users():
    conn = sqlite3.connect(SYSTEM_DB)
    df = pd.read_sql("SELECT * FROM users", conn)
    conn.close()
    return df

# ---------------------------------------------------------
# 데이터 검색
# ---------------------------------------------------------
@st.cache_data(ttl=60)
def search_data(maker, models, details, engines, sy, ey, yards, sm, em, only_photo=False, only_price=False):
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

        if only_photo:
            cond += " AND v.photos IS NOT NULL AND v.photos != ''"
        if only_price:
            cond += " AND v.price > 0"
            
        q = f"SELECT v.vin, v.reg_date, v.car_no, v.manufacturer, v.model_name, v.model_detail, v.model_year, v.junkyard, v.engine_code, v.price, v.mileage, v.photos, j.region, j.address FROM vehicle_data v LEFT JOIN junkyard_info j ON v.junkyard = j.name WHERE {cond} ORDER BY v.reg_date DESC LIMIT 5000"
        count = conn.execute(f"SELECT COUNT(*) FROM vehicle_data v WHERE {cond}", params).fetchone()[0]
        df = pd.read_sql(q, conn, params=params)
        conn.close()
        if not df.empty:
            df['model_year'] = pd.to_numeric(df['model_year'], errors='coerce').fillna(0)
            df['reg_date'] = pd.to_datetime(df['reg_date'], errors='coerce')
        return df, count
    except: return pd.DataFrame(), 0

def update_vehicle_sales_info(vin, price, mileage, photo_files):
    try:
        conn = sqlite3.connect(INVENTORY_DB)
        saved_paths = []
        if photo_files:
            if not os.path.exists(IMAGE_DIR): os.makedirs(IMAGE_DIR)
            for f in photo_files:
                fname = f"{vin}_{datetime.datetime.now().strftime('%H%M%S')}_{f.name}"
                fpath = os.path.join(IMAGE_DIR, fname)
                with open(fpath, "wb") as buffer:
                    shutil.copyfileobj(f, buffer)
                saved_paths.append(fpath)
        
        if saved_paths:
            photo_str = ",".join(saved_paths)
            sql = "UPDATE vehicle_data SET price = ?, mileage = ?, photos = ? WHERE vin = ?"
            params = (price, mileage, photo_str, vin)
        else:
            sql = "UPDATE vehicle_data SET price = ?, mileage = ? WHERE vin = ?"
            params = (price, mileage, vin)
            
        conn.execute(sql, params)
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Update Error: {e}")
        return False

@st.cache_data(ttl=300)
def load_metadata():
    conn = sqlite3.connect(INVENTORY_DB)
    df_m = pd.read_sql("SELECT DISTINCT manufacturer, model_name FROM vehicle_data WHERE manufacturer IS NOT NULL ORDER BY manufacturer, model_name", conn)
    df_e = pd.read_sql("SELECT DISTINCT engine_code FROM vehicle_data", conn)
    df_y = pd.read_sql("SELECT name FROM junkyard_info", conn)
    try: months = pd.read_sql("SELECT DISTINCT strftime('%Y-%m', reg_date) as m FROM vehicle_data ORDER BY m DESC", conn)['m'].tolist()
    except: months = []
    total = conn.execute("SELECT COUNT(*) FROM vehicle_data").fetchone()[0]
    conn.close()
    return df_m, df_e['engine_code'].tolist(), df_y['name'].tolist(), months, pd.DataFrame(), total

def reset_dashboard():
    m_df, m_eng, m_yards, m_mon, _, init_total = load_metadata()
    st.session_state.update({
        'view_data': pd.DataFrame(), 'total_count': init_total, 'models_df': m_df,
        'engines_list': m_eng, 'yards_list': m_yards, 'months_list': m_mon,
        'is_filtered': False, 'selected_vin': None
    })

# ---------------------------------------------------------
# ✅ [NEW] 주문 관련 함수 (누락 복구)
# ---------------------------------------------------------
def place_order(buyer_id, target_partner, vin, model_info):
    """
    buyer_id: 주문자 ID
    target_partner: 판매자(폐차장) 이름 -> real_junkyard_name 컬럼에 매칭되어야 함
    vin: 차량 번호
    model_info: 차량 모델 정보
    """
    try:
        conn = sqlite3.connect(SYSTEM_DB)
        summary = f"Inquiry for {model_info} (VIN: {vin})"
        # real_junkyard_name 컬럼에 파트너 ID(회사명)를 넣어야 셀러가 볼 수 있음
        conn.execute('''INSERT INTO orders 
                        (buyer_id, target_partner_alias, real_junkyard_name, items_summary, status) 
                        VALUES (?, ?, ?, ?, ?)''', 
                     (buyer_id, target_partner, target_partner, summary, 'PENDING'))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Order Error: {e}")
        return False

def get_orders(user_id, role):
    conn = sqlite3.connect(SYSTEM_DB)
    try:
        if role == 'admin': 
            q = "SELECT * FROM orders ORDER BY created_at DESC"
        elif role == 'partner': 
            # 셀러는 real_junkyard_name이 자기 ID인 것만 조회
            q = f"SELECT * FROM orders WHERE real_junkyard_name = '{user_id}' ORDER BY created_at DESC"
        else: 
            # 바이어는 자기가 쓴 글만 조회
            q = f"SELECT * FROM orders WHERE buyer_id = '{user_id}' ORDER BY created_at DESC"
        df = pd.read_sql(q, conn)
    except: df = pd.DataFrame()
    conn.close()
    return df