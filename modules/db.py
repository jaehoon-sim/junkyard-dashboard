# modules/db.py
import sqlite3
import pandas as pd
import datetime
import os
import re
import shutil
import io
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
    '쉐보레': 'Chevrolet', '지엠대우': 'Chevrolet', 'GM대우': 'Chevrolet',
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
    
    # 마이그레이션
    for col in ['model_detail', 'price', 'mileage', 'photos']:
        try: c.execute(f"ALTER TABLE vehicle_data ADD COLUMN {col} TEXT DEFAULT ''" if col == 'photos' or col == 'model_detail' else f"ALTER TABLE vehicle_data ADD COLUMN {col} REAL DEFAULT 0")
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
# 파일 처리 및 표준화 (헤더 감지 강화)
# ---------------------------------------------------------
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

def read_file_smart(uploaded_file, header=None):
    """
    다양한 포맷과 인코딩, 헤더 위치를 고려하여 DataFrame을 반환합니다.
    header=None으로 읽어 전체 데이터를 가져옵니다.
    """
    file_ext = uploaded_file.name.split('.')[-1].lower()
    
    # 파일을 바이트로 읽기 (재사용을 위해)
    uploaded_file.seek(0)
    file_bytes = uploaded_file.read()
    
    # 1. CSV 시도
    if file_ext == 'csv' or 'csv' in uploaded_file.type:
        try:
            return pd.read_csv(io.BytesIO(file_bytes), header=header, dtype=str)
        except:
            try:
                return pd.read_csv(io.BytesIO(file_bytes), header=header, encoding='cp949', dtype=str)
            except:
                pass
    
    # 2. Excel 시도 (xls, xlsx) - openpyxl 또는 xlrd
    try:
        return pd.read_excel(io.BytesIO(file_bytes), header=header, dtype=str)
    except:
        try:
            # xls지만 실제론 csv인 경우 등 대비
            return pd.read_csv(io.BytesIO(file_bytes), header=header, dtype=str)
        except:
            return None

def save_vehicle_file(uploaded_file):
    try:
        # 1. 헤더 없이 전체 데이터 읽기 (상단 경고문구 무시용)
        df = read_file_smart(uploaded_file, header=None)
        if df is None: return 0
        
        # 2. 실제 헤더 행 찾기 (키워드 기반 탐색)
        # 키워드: 차대번호, VIN, 차대 번호 등
        header_idx = -1
        target_keywords = ['차대번호', 'vin', '차량번호', 'car_no', '등록일자']
        
        # 상위 20줄만 검사
        for i, row in df.head(20).iterrows():
            # 행 전체를 하나의 문자열로 합쳐서 검색
            row_str = " ".join([str(x).lower() for x in row.values])
            if any(k in row_str for k in target_keywords):
                header_idx = i
                break
        
        if header_idx == -1:
            # 못 찾았으면 첫 줄을 헤더로 가정
            header_idx = 0
        
        # 3. 데이터프레임 재구성 (헤더 적용)
        # 찾은 행을 컬럼명으로 설정
        df.columns = df.iloc[header_idx]
        df = df.iloc[header_idx+1:] # 헤더 다음 행부터 데이터
        
        # 4. 컬럼명 정리 (공백 제거)
        df.columns = [str(c).strip() for c in df.columns]
        
        # 5. 필수 컬럼 확인 및 매핑
        # (VIN이나 차대번호 컬럼이 없으면 저장 불가)
        vin_col = next((c for c in df.columns if '차대번호' in c or 'VIN' in c or 'vin' in c), None)
        if not vin_col: return 0
        
        db_rows = []
        for _, row in df.iterrows():
            # 각 컬럼 매핑
            mfr = str(row.get('제조사', row.get('Manufacturer', ''))).strip()
            mod = str(row.get('차량명', row.get('Model', ''))).strip()
            std_mfr, std_mod, std_det = normalize_row({'manufacturer': mfr, 'model_name': mod})
            
            vin = str(row.get(vin_col, '')).strip()
            reg = str(row.get('등록일자', row.get('RegDate', ''))).strip()
            no = str(row.get('차량번호', row.get('CarNo', ''))).strip()
            yard = str(row.get('회원사', row.get('Junkyard', row.get('Company', '')))).strip()
            eng = str(row.get('원동기형식', row.get('Engine', ''))).strip()
            
            # 연식 처리
            year_val = row.get('연식', row.get('Year', 0))
            try: year = float(re.findall(r"[\d\.]+", str(year_val))[0])
            except: year = 0.0
            
            # 빈 행 무시
            if len(vin) < 5: continue
            
            db_rows.append((vin, reg, no, std_mfr, std_mod, std_det, year, yard, eng))
            
        # 6. DB 저장
        conn = sqlite3.connect(INVENTORY_DB)
        c = conn.cursor()
        c.executemany('''INSERT OR REPLACE INTO vehicle_data 
                         (vin, reg_date, car_no, manufacturer, model_name, model_detail, model_year, junkyard, engine_code) 
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', db_rows)
        
        # 모델 목록 업데이트
        c.execute("INSERT OR IGNORE INTO model_list (manufacturer, model_name) SELECT DISTINCT manufacturer, model_name FROM vehicle_data")
        
        # 7. 폐차장 정보(파트너) 자동 생성 (회원가입 안 된 경우 대비)
        yards = set([r[7] for r in db_rows if r[7] and len(r[7]) > 1])
        for y in yards:
            c.execute("INSERT OR IGNORE INTO junkyard_info (name, address, region) VALUES (?, ?, ?)", (y, '주소 미등록', '기타'))
        conn.commit()
        conn.close()
        
        # 시스템 DB에 파트너 계정 자동 생성 (비번 1234)
        conn_sys = sqlite3.connect(SYSTEM_DB)
        try: pw = stauth.Hasher(['1234']).generate()[0]
        except: pw = stauth.Hasher().hash('1234')
        for y in yards:
            # 이미 있으면 패스
            if not conn_sys.execute("SELECT * FROM users WHERE user_id = ?", (y,)).fetchone():
                # ID=회사명, 비번=1234, Role=partner, Company=회사명
                conn_sys.execute("INSERT INTO users (user_id, password, name, company, role) VALUES (?, ?, ?, ?, ?)", 
                                 (y, pw, y, y, 'partner'))
        conn_sys.commit()
        conn_sys.close()
        
        return len(db_rows)
    except Exception as e:
        print(f"File Save Error: {e}")
        return 0

# [NEW] 폐차장 주소록 업로드
def save_address_file(uploaded_file):
    try:
        df = read_file_smart(uploaded_file, header=None)
        if df is None: return 0
        
        # 헤더 찾기 (업체명, 주소)
        header_idx = 0
        for i, row in df.head(10).iterrows():
            row_str = " ".join([str(x) for x in row.values])
            if '업체' in row_str or '상호' in row_str or '주소' in row_str:
                header_idx = i
                break
        
        df.columns = df.iloc[header_idx]
        df = df.iloc[header_idx+1:]
        
        # 컬럼 매칭
        name_col = next((c for c in df.columns if '업체' in str(c) or '상호' in str(c) or 'Name' in str(c)), None)
        addr_col = next((c for c in df.columns if '주소' in str(c) or 'Address' in str(c)), None)
        
        if not name_col: return 0
        
        conn = sqlite3.connect(INVENTORY_DB)
        cnt = 0
        for _, r in df.iterrows():
            nm = str(r[name_col]).strip()
            ad = str(r[addr_col]).strip() if addr_col else ''
            reg = ad[:2] if len(ad) >= 2 else '기타'
            if nm:
                conn.execute("INSERT OR REPLACE INTO junkyard_info (name, address, region) VALUES (?, ?, ?)", (nm, ad, reg))
                cnt += 1
        conn.commit()
        conn.close()
        return cnt
    except: return 0

def get_all_junkyards():
    conn = sqlite3.connect(INVENTORY_DB)
    df = pd.read_sql("SELECT * FROM junkyard_info", conn)
    conn.close()
    return df

# ---------------------------------------------------------
# 사용자 관리
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
# 데이터 검색 및 주문 관리
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

def place_order(buyer_id, target_partner, vin, model_info):
    try:
        conn = sqlite3.connect(SYSTEM_DB)
        summary = f"Inquiry for {model_info} (VIN: {vin})"
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

def update_order(order_id, status=None, reply=None):
    conn = sqlite3.connect(SYSTEM_DB)
    try:
        if status:
            conn.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
        if reply:
            conn.execute("UPDATE orders SET reply_text = ? WHERE id = ?", (reply, order_id))
        conn.commit()
        return True
    except Exception as e:
        print(e)
        return False
    finally:
        conn.close()

def get_orders(user_id, role):
    conn = sqlite3.connect(SYSTEM_DB)
    try:
        if role == 'admin': 
            q = "SELECT * FROM orders ORDER BY created_at DESC"
        elif role == 'partner': 
            q = f"SELECT * FROM orders WHERE real_junkyard_name = '{user_id}' ORDER BY created_at DESC"
        else: 
            q = f"SELECT * FROM orders WHERE buyer_id = '{user_id}' ORDER BY created_at DESC"
        df = pd.read_sql(q, conn)
    except: df = pd.DataFrame()
    conn.close()
    return df