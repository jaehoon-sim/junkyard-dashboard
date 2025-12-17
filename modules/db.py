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

def init_dbs():
    if not os.path.exists('data'): os.makedirs('data')
    
    # Inventory
    conn = sqlite3.connect(INVENTORY_DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS vehicle_data (vin TEXT PRIMARY KEY, reg_date TEXT, car_no TEXT, manufacturer TEXT, model_name TEXT, model_year REAL, junkyard TEXT, engine_code TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS junkyard_info (name TEXT PRIMARY KEY, address TEXT, region TEXT, lat REAL, lon REAL, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS model_list (manufacturer TEXT, model_name TEXT, PRIMARY KEY (manufacturer, model_name))''')
    c.execute("CREATE INDEX IF NOT EXISTS idx_mfr ON vehicle_data(manufacturer)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_year ON vehicle_data(model_year)")
    conn.commit()
    conn.close()

    # System
    conn = sqlite3.connect(SYSTEM_DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, password TEXT, name TEXT, company TEXT, country TEXT, email TEXT, phone TEXT, role TEXT DEFAULT 'buyer', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, buyer_id TEXT, contact_info TEXT, target_partner_alias TEXT, real_junkyard_name TEXT, items_summary TEXT, status TEXT DEFAULT 'PENDING', reply_text TEXT, reply_images TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS search_logs_v2 (id INTEGER PRIMARY KEY AUTOINCREMENT, keyword TEXT, search_type TEXT, country TEXT, city TEXT, lat REAL, lon REAL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # 번역 데이터 초기화
    c.execute("DROP TABLE IF EXISTS translations")
    c.execute('''CREATE TABLE translations (key TEXT PRIMARY KEY, English TEXT, Korean TEXT, Russian TEXT, Arabic TEXT)''')
    
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
        c.execute("INSERT INTO users (user_id, password, name, role) VALUES (?, ?, ?, ?)", ('admin', admin_hash, 'Administrator', 'admin'))
    
    # 파트너 계정 자동생성
    try:
        conn_inv = sqlite3.connect(INVENTORY_DB)
        junkyards = pd.read_sql("SELECT name FROM junkyard_info", conn_inv)['name'].unique()
        conn_inv.close()
        try: partner_pw = stauth.Hasher(['1234']).generate()[0]
        except: partner_pw = stauth.Hasher().hash('1234')
        for yard in junkyards:
            if not c.execute("SELECT * FROM users WHERE user_id = ?", (yard,)).fetchone():
                c.execute("INSERT INTO users (user_id, password, name, company, role) VALUES (?, ?, ?, ?, ?)",
                          (yard, partner_pw, "Partner Manager", yard, 'partner'))
    except: pass

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

def fetch_users_for_auth():
    # Admin 기본값
    try: admin_pw = stauth.Hasher(['1234']).generate()[0]
    except: admin_pw = stauth.Hasher().hash('1234')
    credentials = {'usernames': {'admin': {'name': 'Administrator', 'password': admin_pw, 'role': 'admin'}}}
    try:
        conn = sqlite3.connect(SYSTEM_DB)
        rows = conn.execute("SELECT user_id, password, name, role FROM users").fetchall()
        conn.close()
        for r in rows:
            credentials['usernames'][r[0]] = {'name': r[2], 'password': r[1], 'role': r[3]}
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

def save_vehicle_file(uploaded_file):
    try:
        if uploaded_file.name.endswith('.csv'): df = pd.read_csv(uploaded_file, dtype=str)
        else: 
            try: df = pd.read_excel(uploaded_file, engine='openpyxl', dtype=str)
            except: df = pd.read_excel(uploaded_file, engine='xlrd', dtype=str)
        if '차대번호' not in df.columns:
            uploaded_file.seek(0)
            if uploaded_file.name.endswith('.csv'): df = pd.read_csv(uploaded_file, header=2, dtype=str)
            else: 
                try: df = pd.read_excel(uploaded_file, header=2, engine='openpyxl', dtype=str)
                except: df = pd.read_excel(uploaded_file, header=2, engine='xlrd', dtype=str)
        df.columns = [str(c).strip() for c in df.columns]
        
        conn = sqlite3.connect(INVENTORY_DB)
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
        c.execute("INSERT OR IGNORE INTO vehicle_data (vin, reg_date, car_no, manufacturer, model_name, model_year, junkyard, engine_code) SELECT vin, reg_date, car_no, manufacturer, model_name, model_year, junkyard, engine_code FROM temp_vehicles")
        c.execute("DROP TABLE temp_vehicles")
        
        model_list = df_db[['manufacturer', 'model_name']].drop_duplicates()
        for _, r in model_list.iterrows():
            c.execute("INSERT OR IGNORE INTO model_list (manufacturer, model_name) VALUES (?, ?)", (r['manufacturer'], r['model_name']))
            
        yards = df_db['junkyard'].unique().tolist()
        for y in yards:
            c.execute("INSERT OR IGNORE INTO junkyard_info (name, address, region) VALUES (?, ?, ?)", (y, '검색실패', '기타'))
        conn.commit()
        conn.close()
        
        # Partner 생성
        conn_sys = sqlite3.connect(SYSTEM_DB)
        try: pw = stauth.Hasher(['1234']).generate()[0]
        except: pw = stauth.Hasher().hash('1234')
        for y in yards:
            if not conn_sys.execute("SELECT * FROM users WHERE user_id = ?", (y,)).fetchone():
                conn_sys.execute("INSERT INTO users (user_id, password, name, company, role) VALUES (?, ?, ?, ?, ?)", (y, pw, "Partner", y, 'partner'))
        conn_sys.commit()
        conn_sys.close()
        return len(df_db)
    except: return 0

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

def update_role(uid, role):
    conn = sqlite3.connect(SYSTEM_DB)
    conn.execute("UPDATE users SET role = ? WHERE user_id = ?", (role, uid))
    conn.commit()
    conn.close()