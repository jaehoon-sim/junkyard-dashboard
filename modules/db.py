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
# 0. 데이터 표준화 규칙 (Global Mapping Rules)
# ---------------------------------------------------------

# [신규] 모델명으로 사용하기에 부적절한 단어들 (브랜드명 중복 등)
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
    # Hyundai
    '그랜저': 'Grandeur', '그랜져': 'Grandeur', '쏘나타': 'Sonata', '소나타': 'Sonata',
    '아반떼': 'Avante', '싼타페': 'Santa Fe', '산타페': 'Santa Fe', '투싼': 'Tucson',
    '팰리세이드': 'Palisade', '스타렉스': 'Starex', '스타리아': 'Staria', '베뉴': 'Venue', '코나': 'Kona',
    # Kia
    'K3': 'K3', 'K5': 'K5', 'K7': 'K7', 'K8': 'K8', 'K9': 'K9', '쏘렌토': 'Sorento',
    '카니발': 'Carnival', '스포티지': 'Sportage', '모닝': 'Morning', '레이': 'Ray', '셀토스': 'Seltos', '니로': 'Niro',
    # Genesis
    'G70': 'G70', 'G80': 'G80', 'G90': 'G90', 'GV60': 'GV60', 'GV70': 'GV70', 'GV80': 'GV80',
    
    # Mercedes-Benz (주요 클래스)
    'S클래스': 'S-Class', 'E클래스': 'E-Class', 'C클래스': 'C-Class', 
    'A클래스': 'A-Class', 'B클래스': 'B-Class',
    'GLE클래스': 'GLE', 'GLC클래스': 'GLC', 'GLS클래스': 'GLS', 
    'CLA클래스': 'CLA', 'CLS클래스': 'CLS', 'G클래스': 'G-Class',
    'M클래스': 'M-Class', 'ML클래스': 'M-Class', # 구형 ML
    
    # BMW (시리즈 보호)
    '1시리즈': '1 Series', '1 Series': '1 Series', '1Series': '1 Series',
    '2시리즈': '2 Series', '2 Series': '2 Series', '2Series': '2 Series',
    '3시리즈': '3 Series', '3 Series': '3 Series', '3Series': '3 Series',
    '4시리즈': '4 Series', '4 Series': '4 Series', '4Series': '4 Series',
    '5시리즈': '5 Series', '5 Series': '5 Series', '5Series': '5 Series',
    '6시리즈': '6 Series', '6 Series': '6 Series', '6Series': '6 Series',
    '7시리즈': '7 Series', '7 Series': '7 Series', '7Series': '7 Series',
    '8시리즈': '8 Series', '8 Series': '8 Series', '8Series': '8 Series',
    'X1': 'X1', 'X2': 'X2', 'X3': 'X3', 'X4': 'X4', 'X5': 'X5', 'X6': 'X6', 'X7': 'X7',

    # Volkswagen
    '골프': 'Golf', '티구안': 'Tiguan', '파사트': 'Passat', '아테온': 'Arteon', '제타': 'Jetta', '투아렉': 'Touareg',
    # Porsche
    '카이엔': 'Cayenne', '파나메라': 'Panamera', '마칸': 'Macan', '타이칸': 'Taycan', '박스터': 'Boxster', '카이맨': 'Cayman', '911': '911',
    # Land Rover
    '레인지로버': 'Range Rover', '디스커버리': 'Discovery', '디펜더': 'Defender',
    # Others
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
    
    # Inventory DB
    conn = sqlite3.connect(INVENTORY_DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS vehicle_data (
        vin TEXT PRIMARY KEY, reg_date TEXT, car_no TEXT, manufacturer TEXT, 
        model_name TEXT, model_detail TEXT, model_year REAL, junkyard TEXT, engine_code TEXT, 
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    try: c.execute("ALTER TABLE vehicle_data ADD COLUMN model_detail TEXT DEFAULT ''")
    except: pass 
    c.execute('''CREATE TABLE IF NOT EXISTS junkyard_info (
        name TEXT PRIMARY KEY, address TEXT, region TEXT, lat REAL, lon REAL, 
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS model_list (
        manufacturer TEXT, model_name TEXT, PRIMARY KEY (manufacturer, model_name))''')
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

    if not c.execute("SELECT * FROM users WHERE user_id = 'admin'").fetchone():
        try: admin_hash = stauth.Hasher(['1234']).generate()[0]
        except: admin_hash = stauth.Hasher().hash('1234')
        c.execute("INSERT INTO users (user_id, password, name, role) VALUES (?, ?, ?, ?)", 
                  ('admin', admin_hash, 'Administrator', 'admin'))
    conn.commit()
    conn.close()

# ---------------------------------------------------------
# 2. 파일 처리 및 데이터 표준화 (Global Smart Logic)
# ---------------------------------------------------------

def detect_global_pattern(text):
    """
    글로벌 브랜드의 모델명 패턴(알파벳+숫자)을 분석하여 대표 모델(Series/Class/Type) 반환
    """
    text = text.upper().replace(" ", "")
    
    # 1. Mercedes-Benz (구형 모델 ML, R, SLK 등 추가)
    if re.match(r"^([ABCEGS])\d{2,3}", text): return f"{text[0]}-Class" # A200, S500
    
    # [추가] M-Class (ML350, ML500 등)
    if re.match(r"^ML\d{2,3}", text): return "M-Class"
    # [추가] R-Class (R350, R500 등)
    if re.match(r"^R\d{2,3}", text): return "R-Class"
    # [추가] GLK, SLK, CLK 등
    if re.match(r"^GLK", text): return "GLK"
    if re.match(r"^SLK", text): return "SLK"
    if re.match(r"^CLK", text): return "CLK"
    
    if text.startswith("CLA"): return "CLA"
    if text.startswith("CLS"): return "CLS"
    if text.startswith("GLA"): return "GLA"
    if text.startswith("GLB"): return "GLB"
    if text.startswith("GLC"): return "GLC"
    if text.startswith("GLE"): return "GLE"
    if text.startswith("GLS"): return "GLS"
    if text.startswith("G63"): return "G-Class"
    if text.startswith("EQ"): return "EQ Series"

    # 2. BMW
    if re.match(r"^([1-8])\d{2}[A-Z]*$", text): return f"{text[0]} Series"
    if re.match(r"^([1-8])$", text): return f"{text[0]} Series"
    
    if re.match(r"^X([1-7])", text): return f"X{text[1]}"
    if re.match(r"^Z([348])", text): return f"Z{text[1]}"
    if re.match(r"^M([2-8])", text): return f"M{text[1]}"
    if text.startswith("I"): return "i Series"

    # 3. Audi
    if re.match(r"^(A|S|RS)([1-8])", text):
        match = re.match(r"^(A|S|RS)([1-8])", text)
        return f"{match.group(1)}{match.group(2)}"
    if re.match(r"^Q([2-8])", text):
        return f"Q{text[1]}"
    if text.startswith("TT"): return "TT"
    if text.startswith("R8"): return "R8"
    if text.startswith("E-TRON"): return "e-tron"

    # 4. Others
    lexus_prefix = ["CT", "IS", "ES", "GS", "LS", "UX", "NX", "RX", "GX", "LX", "LC", "RC"]
    for p in lexus_prefix:
        if text.startswith(p): return p

    if re.match(r"^(XC|S|V|C)\d{2}", text):
        match = re.match(r"^(XC|S|V|C)\d{2}", text)
        return match.group(0)

    if re.match(r"^(SM|QM|XM)\d{1}", text):
        match = re.match(r"^(SM|QM|XM)\d{1}", text)
        return match.group(0)

    if re.match(r"^X[EFJ]", text): return text[:2]
    if "PACE" in text:
        if text.startswith("F"): return "F-Pace"
        if text.startswith("E"): return "E-Pace"
        if text.startswith("I"): return "I-Pace"

    if text.startswith("RANGE") or text.startswith("레인지"): return "Range Rover"
    if text.startswith("DISCO") or text.startswith("디스"): return "Discovery"
    
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
    
    # [신규] 쓰레기 데이터 필터링 (브랜드 이름만 덩그러니 있거나 의미 없는 단어)
    if clean_model.upper() in GARBAGE_TERMS:
        clean_model = "Unknown" 

    std_model = clean_model
    std_detail = ""

    mapped = False
    
    # [Step A] 1차 매핑
    for k, v in MODEL_MAP.items():
        if clean_model.upper() == k.upper() or clean_model.upper().startswith(k.upper()):
            std_model = v
            if clean_model.upper() == k.upper():
                std_detail = ""
            else:
                det = re.sub(k, "", clean_model, flags=re.IGNORECASE).strip()
                std_detail = det if det else ""
            mapped = True
            break
            
    # [Step B] 글로벌 패턴 매칭
    if not mapped:
        pattern_detected = detect_global_pattern(clean_model)
        if pattern_detected:
            std_model = pattern_detected
            if std_detail == "": std_detail = clean_model
            mapped = True

    # [Step C] 기본 분리
    if not mapped:
        parts = clean_model.split()
        if len(parts) >= 2:
            std_model = parts[0]
            std_detail = " ".join(parts[1:])
        else:
            std_model = clean_model

    std_detail = std_detail.replace("(", "").replace(")", "").strip()
    
    # 최종 안전장치: 모델명이 쓰레기 단어와 같아졌다면 Unknown 처리
    if std_model.upper() in GARBAGE_TERMS:
        std_model = "Unknown"
        
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
    except Exception as e: return 0

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