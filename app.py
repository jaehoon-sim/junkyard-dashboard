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
import smtplib
import json
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

# ---------------------------------------------------------
# 🛠️ [설정] 페이지 설정
# ---------------------------------------------------------
st.set_page_config(page_title="K-Used Car Global Hub", layout="wide")

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
    NAVER_CLIENT_ID = "aic55XK2RCthRyeMMlJM"
    NAVER_CLIENT_SECRET = "ZqOAIOzYGf"

BUYER_CREDENTIALS = {
    "buyer": "1111",
    "global": "2222",
    "testbuyer": "1234"
}

# 🟢 [설정] 데이터베이스 파일 분리
INVENTORY_DB = 'inventory.db'  # 재고, 폐차장, 모델 (대용량)
SYSTEM_DB = 'system.db'        # 유저, 주문, 로그, 번역 (소용량)

# ---------------------------------------------------------
# 📧 [기능] 이메일 발송 함수
# ---------------------------------------------------------
def send_email(to_email, subject, content, attachment_files=[]):
    if "@" not in to_email: return False
    try:
        if "EMAIL" not in st.secrets: return False
        
        smtp_server = st.secrets["EMAIL"]["smtp_server"]
        smtp_port = st.secrets["EMAIL"]["smtp_port"]
        sender_email = st.secrets["EMAIL"]["sender_email"]
        sender_password = st.secrets["EMAIL"]["sender_password"]

        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(content, 'plain'))

        if attachment_files:
            for file in attachment_files:
                try:
                    file.seek(0)
                    file_data = file.read()
                    part = MIMEApplication(file_data, Name=file.name)
                    part['Content-Disposition'] = f'attachment; filename="{file.name}"'
                    msg.attach(part)
                except: continue

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        return True
    except: return False

# ---------------------------------------------------------
# 🌍 [설정] 데이터 (국가, 주소 매핑)
# ---------------------------------------------------------
COUNTRY_LIST = [
    "Select Country", "Russia", "Jordan", "Saudi Arabia", "UAE", "Egypt", "Kazakhstan", "Kyrgyzstan", 
    "Mongolia", "Vietnam", "Philippines", "Chile", "Dominican Rep.", "Ghana", "Nigeria", 
    "Cambodia", "Uzbekistan", "Tajikistan", "USA", "Canada", "Other"
]

PROVINCE_MAP = {
    '경기': 'Gyeonggi-do', '서울': 'Seoul', '인천': 'Incheon', '강원': 'Gangwon-do',
    '충북': 'Chungbuk', '충남': 'Chungnam', '대전': 'Daejeon', '세종': 'Sejong',
    '전북': 'Jeonbuk', '전남': 'Jeonnam', '광주': 'Gwangju',
    '경북': 'Gyeongbuk', '경남': 'Gyeongnam', '대구': 'Daegu', '부산': 'Busan', '울산': 'Ulsan',
    '제주': 'Jeju', '경상남도': 'Gyeongnam', '경상북도': 'Gyeongbuk', 
    '전라남도': 'Jeonnam', '전라북도': 'Jeonbuk', '충청남도': 'Chungnam', '충청북도': 'Chungbuk',
    '경기도': 'Gyeonggi-do', '강원도': 'Gangwon-do', '제주도': 'Jeju'
}

CITY_MAP = {
    '수원': 'Suwon', '성남': 'Seongnam', '의정부': 'Uijeongbu', '안양': 'Anyang',
    '부천': 'Bucheon', '광명': 'Gwangmyeong', '평택': 'Pyeongtaek', '동두천': 'Dongducheon',
    '안산': 'Ansan', '고양': 'Goyang', '과천': 'Gwacheon', '구리': 'Guri',
    '남양주': 'Namyangju', '오산': 'Osan', '시흥': 'Siheung', '군포': 'Gunpo',
    '의왕': 'Uiwang', '하남': 'Hanam', '용인': 'Yongin', '파주': 'Paju',
    '이천': 'Icheon', '안성': 'Anseong', '김포': 'Gimpo', '화성': 'Hwaseong',
    '광주': 'Gwangju', '양주': 'Yangju', '포천': 'Pocheon', '여주': 'Yeoju',
    '연천': 'Yeoncheon', '가평': 'Gapyeong', '양평': 'Yangpyeong',
    '천안': 'Cheonan', '공주': 'Gongju', '보령': 'Boryeong', '아산': 'Asan',
    '서산': 'Seosan', '논산': 'Nonsan', '계룡': 'Gyeryong', '당진': 'Dangjin',
    '금산': 'Geumsan', '부여': 'Buyeo', '서천': 'Seocheon', '청양': 'Cheongyang',
    '홍성': 'Hongseong', '예산': 'Yesan', '태안': 'Taean',
    '청주': 'Cheongju', '충주': 'Chungju', '제천': 'Jecheon', '보은': 'Boeun',
    '옥천': 'Okcheon', '영동': 'Yeongdong', '증평': 'Jeungpyeong', '진천': 'Jincheon',
    '괴산': 'Goesan', '음성': 'Eumseong', '단양': 'Danyang',
    '포항': 'Pohang', '경주': 'Gyeongju', '김천': 'Gimcheon', '안동': 'Andong',
    '구미': 'Gumi', '영주': 'Yeongju', '영천': 'Yeongcheon', '상주': 'Sangju',
    '문경': 'Mungyeong', '경산': 'Gyeongsan', '군위': 'Gunwi', '의성': 'Uiseong',
    '청송': 'Cheongsong', '영양': 'Yeongyang', '영덕': 'Yeongdeok', '청도': 'Cheongdo',
    '고령': 'Goryeong', '성주': 'Seongju', '칠곡': 'Chilgok', '예천': 'Yecheon',
    '봉화': 'Bonghwa', '울진': 'Uljin', '울릉': 'Ulleung',
    '창원': 'Changwon', '진주': 'Jinju', '통영': 'Tongyeong', '사천': 'Sacheon',
    '김해': 'Gimhae', '밀양': 'Miryang', '거제': 'Geoje', '양산': 'Yangsan',
    '의령': 'Uiryeong', '함안': 'Haman', '창녕': 'Changnyeong', '고성': 'Goseong',
    '남해': 'Namhae', '하동': 'Hadong', '산청': 'Sancheong', '함양': 'Hamyang',
    '거창': 'Geochang', '합천': 'Hapcheon',
    '전주': 'Jeonju', '군산': 'Gunsan', '익산': 'Iksan', '정읍': 'Jeongeup',
    '남원': 'Namwon', '김제': 'Gimje', '완주': 'Wanju', '진안': 'Jinan',
    '무주': 'Muju', '장수': 'Jangsu', '임실': 'Imsil', '순창': 'Sunchang',
    '고창': 'Gochang', '부안': 'Buan',
    '목포': 'Mokpo', '여수': 'Yeosu', '순천': 'Suncheon', '나주': 'Naju',
    '광양': 'Gwangyang', '담양': 'Damyang', '곡성': 'Gokseong', '구례': 'Gurye',
    '고흥': 'Goheung', '보성': 'Boseong', '화순': 'Hwasun', '장흥': 'Jangheung',
    '강진': 'Gangjin', '해남': 'Haenam', '영암': 'Yeongam', '무안': 'Muan',
    '함평': 'Hampyeong', '영광': 'Yeonggwang', '장성': 'Jangseong', '완도': 'Wando',
    '진도': 'Jindo', '신안': 'Sinan', '제주': 'Jeju', '서귀포': 'Seogwipo'
}

# 비밀번호 해싱
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text: return True
    return False

# ---------------------------------------------------------
# 🗄️ [DB] 데이터베이스 초기화 (분리됨)
# ---------------------------------------------------------
def _get_raw_translations():
    return {
        "English": {
            "app_title": "K-Used Car Global Hub", "login_title": "Login", "id": "ID *", "pw": "Password *",
            "sign_in": "Sign In", "sign_up": "Sign Up", "logout": "Logout", "welcome": "Welcome, {}!", 
            "invalid_cred": "Invalid Credentials", "user_exists": "User ID already exists.", "signup_success": "Account created! Please login.",
            "admin_tools": "Admin Tools", "data_upload": "Data Upload", "save_data": "Save Data", "addr_db": "Address DB",
            "save_addr": "Save Address", "reset_db": "Reset System DB", "reset_inv": "Reset Inventory DB", "reset_done": "Reset Done",
            "records_saved": "{} records uploaded.", "addr_updated": "{} addresses updated.", "admin_menu": "Admin Menu", 
            "demand_analysis": "Global Demand Analysis", "search_filter": "Search Filter", "tab_vehicle": "Vehicle", 
            "tab_engine": "Engine", "tab_yard": "Yard", "manufacturer": "Manufacturer", "from_year": "From Year", 
            "to_year": "To Year", "model": "Model", "engine_code": "Engine Code", "partner_name": "Partner Name", 
            "search_btn_veh": "Search Vehicle", "search_btn_eng": "Search Engine", "search_btn_partners": "Search Partner", 
            "reset_filters": "Reset Filters", "check_trends": "Check global search trends.", "show_trends": "Show Trends", 
            "analysis_title": "Global Demand Trends (Real-time)", "top_engines": "Top Searched Engines", 
            "top_models": "Top Searched Models", "main_title": "K-Used Car/Engine Inventory", "tab_inventory": "Inventory", 
            "tab_orders": "Orders", "tab_results": "Search Results", "tab_my_orders": "My Orders", "no_results": "No results found.", 
            "plz_select": "Please select filters from the sidebar to search.", "total_veh": "Total Vehicles", 
            "matched_eng": "Matched Engines", "partners_cnt": "Partners", "real_yards": "Real Junkyards", 
            "limit_warning": "⚠️ Showing top 5,000 results out of {:,}. Please refine filters.", "stock_by_partner": "Stock by Partner", 
            "login_req_warn": "🔒 Login required to request a quote.", "selected_msg": "Selected: **{}** ({} EA)", 
            "req_quote_title": "📨 Request Quote to {}", "name_company": "Name / Company", "contact": "Contact (Email/Phone) *", 
            "qty": "Quantity *", "item": "Item *", "unit_price": "Target Unit Price (USD) *", "message": "Message to Admin", 
            "send_btn": "🚀 Send Inquiry", "fill_error": "⚠️ Please fill in all required fields: Contact, Item, and Price.", 
            "inquiry_sent": "✅ Inquiry has been sent to our sales team.", "item_list": "Item List", "incoming_quotes": "📩 Incoming Quote Requests", 
            "my_quote_req": "🛒 My Quote Requests", "no_orders_admin": "No pending orders.", "no_orders_buyer": "You haven't requested any quotes yet.", 
            "status_change": "Change Status", "update_btn": "Update", "updated_msg": "Updated!", 
            "offer_received": "💬 Offer Received! Check your email/phone.", "company_name": "Company Name *", 
            "country": "Country *", "email": "Email *", "phone": "Phone Number", "user_name": "Name (Person) *", 
            "signup_missing_fields": "⚠️ Please fill in all required fields (marked with *)."
        },
        "Korean": {
            "app_title": "K-Used Car 글로벌 허브", "login_title": "로그인", "id": "아이디 *", "pw": "비밀번호 *",
            "sign_in": "로그인", "sign_up": "회원가입", "logout": "로그아웃", "welcome": "환영합니다, {}님!", 
            "invalid_cred": "로그인 정보가 올바르지 않습니다.", "user_exists": "이미 존재하는 아이디입니다.", "signup_success": "가입 완료! 로그인해주세요.",
            "admin_tools": "관리자 도구", "data_upload": "데이터 업로드", "save_data": "데이터 저장", "addr_db": "주소 DB",
            "save_addr": "주소 저장", "reset_db": "시스템 DB 초기화", "reset_inv": "재고 DB 초기화", "reset_done": "초기화 완료",
            "records_saved": "{}건 저장 완료.", "addr_updated": "{}곳 주소 업데이트 완료.", "admin_menu": "관리자 메뉴", 
            "demand_analysis": "글로벌 수요 분석", "search_filter": "검색 필터", "tab_vehicle": "차량", "tab_engine": "엔진", 
            "tab_yard": "업체", "manufacturer": "제조사", "from_year": "시작 연식", "to_year": "종료 연식", "model": "모델명", 
            "engine_code": "엔진코드", "partner_name": "파트너명", "search_btn_veh": "차량 검색", "search_btn_eng": "엔진 검색", 
            "search_btn_partners": "파트너 검색", "reset_filters": "필터 초기화", "check_trends": "글로벌 검색 트렌드 확인", 
            "show_trends": "트렌드 보기", "analysis_title": "글로벌 실시간 수요 분석", "top_engines": "인기 검색 엔진", 
            "top_models": "인기 검색 차종", "main_title": "K-Used Car/Engine 재고 현황", "tab_inventory": "재고 조회", 
            "tab_orders": "주문 관리", "tab_results": "검색 결과", "tab_my_orders": "내 주문 내역", "no_results": "검색 결과가 없습니다.", 
            "plz_select": "사이드바에서 필터를 선택하여 검색하세요.", "total_veh": "총 차량", "matched_eng": "매칭 엔진", 
            "partners_cnt": "파트너 수", "real_yards": "실제 폐차장", "limit_warning": "⚠️ 총 {:,}건 중 상위 5,000건만 표시됩니다. 필터를 상세 조정하세요.", 
            "stock_by_partner": "업체별 보유 현황", "login_req_warn": "🔒 견적 요청을 위해 로그인이 필요합니다.", "selected_msg": "선택됨: **{}** ({} 개)", 
            "req_quote_title": "📨 {}에 견적 요청", "name_company": "이름 / 회사명", "contact": "연락처 (이메일/전화) *", 
            "qty": "요청 수량 *", "item": "품목 *", "unit_price": "희망 단가 (USD) *", "message": "메시지", 
            "send_btn": "🚀 견적 요청 전송", "fill_error": "⚠️ 필수 입력 항목(연락처, 품목, 단가)을 입력해주세요.", 
            "inquiry_sent": "✅ 영업팀으로 견적 요청이 전송되었습니다.", "item_list": "상세 목록", "incoming_quotes": "📩 접수된 견적 요청", 
            "my_quote_req": "🛒 나의 견적 요청 내역", "no_orders_admin": "대기 중인 주문이 없습니다.", "no_orders_buyer": "아직 요청한 내역이 없습니다.", 
            "status_change": "상태 변경", "update_btn": "업데이트", "updated_msg": "업데이트 완료!", "offer_received": "💬 견적 도착! 이메일/전화를 확인하세요.",
            "company_name": "회사명 *", "country": "국가 *", "email": "이메일 *", "phone": "전화번호",
            "user_name": "담당자 성함 *", "signup_missing_fields": "⚠️ 필수 정보(*)를 모두 입력해주세요."
        }
    }
    # (다른 언어는 생략, 자동 생성 시 영어 기반으로 채워짐)

def init_inventory_db():
    """재고 DB (차량, 주소, 모델) 초기화 - 대용량"""
    conn = sqlite3.connect(INVENTORY_DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS vehicle_data (vin TEXT PRIMARY KEY, reg_date TEXT, car_no TEXT, manufacturer TEXT, model_name TEXT, model_year REAL, junkyard TEXT, engine_code TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS junkyard_info (name TEXT PRIMARY KEY, address TEXT, region TEXT, lat REAL, lon REAL, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS model_list (manufacturer TEXT, model_name TEXT, PRIMARY KEY (manufacturer, model_name))''')
    c.execute("CREATE INDEX IF NOT EXISTS idx_mfr ON vehicle_data(manufacturer)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_model ON vehicle_data(model_name)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_year ON vehicle_data(model_year)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_engine ON vehicle_data(engine_code)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_yard ON vehicle_data(junkyard)")
    conn.commit()
    conn.close()

def init_system_db():
    """시스템 DB (유저, 주문, 로그, 번역) 초기화 - 소용량"""
    conn = sqlite3.connect(SYSTEM_DB)
    c = conn.cursor()
    
    # 유저
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, password TEXT, name TEXT, company TEXT, country TEXT, email TEXT, phone TEXT, role TEXT DEFAULT 'buyer', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    # 주문 (답장 컬럼 포함)
    c.execute('''CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, buyer_id TEXT, contact_info TEXT, target_partner_alias TEXT, real_junkyard_name TEXT, items_summary TEXT, status TEXT DEFAULT 'PENDING', reply_text TEXT, reply_images TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    # 로그
    c.execute('''CREATE TABLE IF NOT EXISTS search_logs_v2 (id INTEGER PRIMARY KEY AUTOINCREMENT, keyword TEXT, search_type TEXT, country TEXT, city TEXT, lat REAL, lon REAL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    # 번역
    c.execute('''CREATE TABLE IF NOT EXISTS translations (key TEXT PRIMARY KEY, English TEXT, Korean TEXT, Russian TEXT, Arabic TEXT)''')

    # 번역 데이터 갱신 (항상 최신 코드 반영)
    raw_data = _get_raw_translations()
    keys = raw_data["English"].keys()
    data_to_insert = []
    for k in keys:
        row = (
            k,
            raw_data.get("English", {}).get(k, k),
            raw_data.get("Korean", {}).get(k, k),
            raw_data.get("Russian", {}).get(k, k),
            raw_data.get("Arabic", {}).get(k, k)
        )
        data_to_insert.append(row)
    c.executemany("INSERT OR REPLACE INTO translations VALUES (?, ?, ?, ?, ?)", data_to_insert)
    
    conn.commit()
    conn.close()

# ---------------------------------------------------------
# 👥 [User] 회원가입 & 로그인 (SYSTEM_DB)
# ---------------------------------------------------------
def create_user(user_id, password, name, company, country, email, phone):
    try:
        conn = sqlite3.connect(SYSTEM_DB)
        c = conn.cursor()
        hashed_pw = make_hashes(password)
        c.execute("INSERT INTO users (user_id, password, name, company, country, email, phone) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                  (user_id, hashed_pw, name, company, country, email, phone))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError: return False
    except: return False

def login_user(user_id, password):
    if user_id in ADMIN_CREDENTIALS and ADMIN_CREDENTIALS[user_id] == password:
        return "admin", "admin"
    
    try:
        conn = sqlite3.connect(SYSTEM_DB)
        c = conn.cursor()
        c.execute("SELECT password, role, name FROM users WHERE user_id = ?", (user_id,))
        data = c.fetchone()
        conn.close()
        if data:
            db_pw, role, name = data
            if check_hashes(password, db_pw):
                return role, name
    except: pass
    return None, None

# ---------------------------------------------------------
# 🌐 [i18n] 번역 로딩 (SYSTEM_DB)
# ---------------------------------------------------------
# 🔴 [중요] 캐시 제거: 항상 최신 번역 데이터를 DB에서 읽어오도록 수정
def load_translations():
    conn = sqlite3.connect(SYSTEM_DB)
    try:
        df = pd.read_sql("SELECT * FROM translations", conn)
    except:
        return {} # DB 생성 전일 경우 예외 처리
    conn.close()
    
    trans_dict = {}
    if not df.empty:
        for lang in ['English', 'Korean', 'Russian', 'Arabic']:
            if lang in df.columns:
                trans_dict[lang] = dict(zip(df['key'], df[lang]))
    return trans_dict

def t(key):
    translations = load_translations()
    lang = st.session_state.get('language', 'English')
    lang_dict = translations.get(lang, translations.get('English', {}))
    return lang_dict.get(key, key)

# ---------------------------------------------------------
# 🕵️ [Data] 데이터 처리 함수들 (INVENTORY_DB & SYSTEM_DB)
# ---------------------------------------------------------
def generate_alias(real_name):
    if not isinstance(real_name, str): return "Unknown"
    hash_object = hashlib.md5(str(real_name).encode())
    hash_int = int(hash_object.hexdigest(), 16) % 900 + 100 
    return f"Partner #{hash_int}"

def translate_address(addr):
    if not isinstance(addr, str) or addr == "검색실패" or "조회" in addr: return "Unknown Address"
    parts = addr.split()
    if len(parts) < 2: return "South Korea"
    k_do, k_city = parts[0][:2], parts[1]
    
    en_do = PROVINCE_MAP.get(k_do, k_do)
    city_core = k_city.replace('시','').replace('군','').replace('구','')
    en_city = CITY_MAP.get(city_core, city_core)
    
    if en_do in ['Seoul', 'Incheon', 'Busan', 'Daegu', 'Daejeon', 'Gwangju', 'Ulsan']:
        return f"{en_do}, Korea"
    else:
        suffix = "-si" if "시" in k_city else ("-gun" if "군" in k_city else "")
        if en_city != city_core: return f"{en_do}, {en_city}{suffix}"
        else: return f"{en_do}, Korea"

def mask_dataframe(df, role):
    if df.empty: return df
    df_safe = df.copy()
    
    if role == 'admin':
        if 'junkyard' in df_safe.columns:
            df_safe['partner_alias'] = df_safe['junkyard'].apply(generate_alias)
        return df_safe

    if 'junkyard' in df_safe.columns:
        df_safe['real_junkyard'] = df_safe['junkyard']
        if role == 'buyer':
            df_safe['junkyard'] = df_safe['junkyard'].apply(generate_alias)
        else:
            df_safe['junkyard'] = "🔒 Login Required"

    if 'address' in df_safe.columns:
        if role == 'buyer':
            df_safe['address'] = df_safe['address'].apply(translate_address)
            if 'region' in df_safe.columns:
                df_safe['region'] = df_safe['address'].apply(lambda x: x.split(',')[0] if ',' in str(x) else x)
        else:
            df_safe['address'] = "🔒 Login Required"
            df_safe['region'] = "🔒"

    if 'vin' in df_safe.columns:
        df_safe['vin'] = df_safe['vin'].astype(str).apply(lambda x: x[:8] + "****" if len(x) > 8 else "****")
    
    drop_cols = ['car_no', 'lat', 'lon', 'real_junkyard']
    df_safe = df_safe.drop(columns=[c for c in drop_cols if c in df_safe.columns], errors='ignore')
    return df_safe

def log_search(keywords, s_type):
    if not keywords: return
    try:
        conn = sqlite3.connect(SYSTEM_DB)
        c = conn.cursor()
        if isinstance(keywords, list):
            for k in keywords:
                c.execute("INSERT INTO search_logs_v2 (keyword, search_type, country, city) VALUES (?, ?, ?, ?)", (str(k), s_type, 'KR', 'Seoul'))
        else:
            c.execute("INSERT INTO search_logs_v2 (keyword, search_type, country, city) VALUES (?, ?, ?, ?)", (str(keywords), s_type, 'KR', 'Seoul'))
        conn.commit()
        conn.close()
    except: pass

def get_search_trends():
    try:
        conn = sqlite3.connect(SYSTEM_DB)
        eng = pd.read_sql("SELECT keyword, COUNT(*) as count FROM search_logs_v2 WHERE search_type='engine' GROUP BY keyword ORDER BY count DESC LIMIT 10", conn)
        mod = pd.read_sql("SELECT keyword, COUNT(*) as count FROM search_logs_v2 WHERE search_type='model' GROUP BY keyword ORDER BY count DESC LIMIT 10", conn)
        conn.close()
        
        if eng.empty and mod.empty: return pd.DataFrame(), pd.DataFrame()
        
        def process_counts(sub_df):
            if sub_df.empty: return pd.DataFrame()
            sub_df['clean_keyword'] = sub_df['keyword'].astype(str).apply(lambda x: x.replace('[', '').replace(']', '').replace("'", "").replace('"', ''))
            sub_df['split_keyword'] = sub_df['clean_keyword'].apply(lambda x: [i.strip() for i in x.split(',') if i.strip()])
            exploded = sub_df.explode('split_keyword')
            counts = exploded['split_keyword'].value_counts().reset_index()
            counts.columns = ['keyword', 'count']
            return counts.head(10)

        eng_counts = process_counts(eng)
        mod_counts = process_counts(mod)
        return eng_counts, mod_counts
    except: return pd.DataFrame(), pd.DataFrame()

def save_vehicle_file(uploaded_file):
    try:
        if uploaded_file.name.endswith('.csv'): df = pd.read_csv(uploaded_file, dtype=str)
        else: 
            try: df = pd.read_excel(uploaded_file, engine='openpyxl', dtype=str)
            except: df = pd.read_excel(uploaded_file, engine='xlrd', dtype=str)

        if '차대번호' not in df.columns:
            if uploaded_file.name.endswith('.csv'): uploaded_file.seek(0); df = pd.read_csv(uploaded_file, header=2, dtype=str)
            else: 
                try: df = pd.read_excel(uploaded_file, header=2, engine='openpyxl', dtype=str)
                except: df = pd.read_excel(uploaded_file, header=2, engine='xlrd', dtype=str)
        
        df.columns = [str(c).strip() for c in df.columns]
        required = ['등록일자', '차량번호', '차대번호', '제조사', '차량명', '회원사', '원동기형식']
        if not all(col in df.columns for col in required): return 0, 0

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
        c.execute("""INSERT OR IGNORE INTO vehicle_data (vin, reg_date, car_no, manufacturer, model_name, model_year, junkyard, engine_code)
                     SELECT vin, reg_date, car_no, manufacturer, model_name, model_year, junkyard, engine_code FROM temp_vehicles""")
        cnt = len(df_db)
        c.execute("DROP TABLE temp_vehicles")
        
        model_list_df = df_db[['manufacturer', 'model_name']].drop_duplicates()
        for _, row in model_list_df.iterrows():
            c.execute("INSERT OR IGNORE INTO model_list (manufacturer, model_name) VALUES (?, ?)", (row['manufacturer'], row['model_name']))

        unique_yards = df_db['junkyard'].unique().tolist()
        for yard in unique_yards:
            c.execute("INSERT OR IGNORE INTO junkyard_info (name, address, region) VALUES (?, ?, ?)", (yard, '검색실패', '기타'))
            
        conn.commit()
        conn.close()
        return cnt, 0
    except: return 0, 0

def save_address_file(uploaded_file):
    try:
        if uploaded_file.name.endswith('.csv'): df = pd.read_csv(uploaded_file, dtype=str)
        else: 
            try: df = pd.read_excel(uploaded_file, engine='openpyxl', dtype=str)
            except: df = pd.read_excel(uploaded_file, engine='xlrd', dtype=str)
        
        name_col = next((c for c in df.columns if '폐차장' in c or '업체' in c or '회원' in c), None)
        addr_col = next((c for c in df.columns if '주소' in c or '소재' in c), None)
        if not name_col or not addr_col: return 0

        conn = sqlite3.connect(INVENTORY_DB)
        c = conn.cursor()
        update_cnt = 0
        
        for _, row in df.iterrows():
            yard_name = str(row[name_col]).strip()
            address = str(row[addr_col]).strip()
            region = address.split()[0][:2] if len(address.split()) >= 1 else '기타'
            c.execute("INSERT OR REPLACE INTO junkyard_info (name, address, region) VALUES (?, ?, ?)", (yard_name, address, region))
            update_cnt += 1
            
        conn.commit()
        conn.close()
        return update_cnt
    except: return 0

@st.cache_data(ttl=60)
def search_data_from_db(maker, models, engines, sy, ey, yards):
    try:
        conn = sqlite3.connect(INVENTORY_DB)
        base_cond = "1=1"
        params = []
        
        if maker and maker != "All":
            base_cond += " AND v.manufacturer = ?"
            params.append(maker)
        
        base_cond += " AND v.model_year >= ? AND v.model_year <= ?"
        params.extend([sy, ey])
        
        if models:
            placeholders = ','.join(['?'] * len(models))
            base_cond += f" AND v.model_name IN ({placeholders})"
            params.extend(models)
            
        if engines:
            placeholders = ','.join(['?'] * len(engines))
            base_cond += f" AND v.engine_code IN ({placeholders})"
            params.extend(engines)
            
        if yards:
            placeholders = ','.join(['?'] * len(yards))
            base_cond += f" AND v.junkyard IN ({placeholders})"
            params.extend(yards)
            
        count_q = f"SELECT COUNT(*) FROM vehicle_data v WHERE {base_cond}"
        total_count = conn.execute(count_q, params).fetchone()[0]
        
        data_q = f"""
            SELECT v.*, j.region, j.address 
            FROM vehicle_data v 
            LEFT JOIN junkyard_info j ON v.junkyard = j.name
            WHERE {base_cond}
            ORDER BY v.reg_date DESC LIMIT 5000
        """
        df = pd.read_sql(data_q, conn, params=params)
        conn.close()
        
        if not df.empty:
            df['model_year'] = pd.to_numeric(df['model_year'], errors='coerce').fillna(0)
            df['reg_date'] = pd.to_datetime(df['reg_date'], errors='coerce')
            
        return df, total_count
    except Exception as e: return pd.DataFrame(), 0

@st.cache_data(ttl=300)
def load_metadata_and_init_data():
    conn = sqlite3.connect(INVENTORY_DB)
    df_m = pd.read_sql("SELECT DISTINCT manufacturer, model_name FROM model_list", conn)
    df_e = pd.read_sql("SELECT DISTINCT engine_code FROM vehicle_data", conn)
    df_y = pd.read_sql("SELECT name FROM junkyard_info", conn)
    total_cnt = conn.execute("SELECT COUNT(*) FROM vehicle_data").fetchone()[0]
    df_init = pd.read_sql("SELECT v.*, j.region, j.address FROM vehicle_data v LEFT JOIN junkyard_info j ON v.junkyard = j.name ORDER BY v.reg_date DESC LIMIT 5000", conn)
    conn.close()
    
    if not df_init.empty:
        df_init['model_year'] = pd.to_numeric(df_init['model_year'], errors='coerce').fillna(0)
        df_init['reg_date'] = pd.to_datetime(df_init['reg_date'], errors='coerce')
        
    return df_m, df_e['engine_code'].tolist(), df_y['name'].tolist(), df_init, total_cnt

# 🟢 reset_dashboard 함수를 위쪽으로 이동
def reset_dashboard():
    _, _, _, df_init, total = load_metadata_and_init_data()
    st.session_state['view_data'] = df_init
    st.session_state['total_count'] = total
    st.session_state['is_filtered'] = False
    st.session_state['mode_demand'] = False
    
    if 'msel' in st.session_state: st.session_state['msel'] = "All"
    if 'sy' in st.session_state: st.session_state['sy'] = 2000
    if 'ey' in st.session_state: st.session_state['ey'] = datetime.datetime.now().year
    if 'mms' in st.session_state: st.session_state['mms'] = []
    if 'es' in st.session_state: st.session_state['es'] = []
    if 'ys' in st.session_state: st.session_state['ys'] = []

# ---------------------------------------------------------
# 🚀 메인 어플리케이션
# ---------------------------------------------------------
try:
    if 'user_role' not in st.session_state: st.session_state.user_role = 'guest'
    if 'username' not in st.session_state: st.session_state.username = 'Guest'
    if 'language' not in st.session_state: st.session_state.language = 'English'

    # DB 초기화 (Inventory & System)
    init_inventory_db()
    init_system_db()

    if 'view_data' not in st.session_state or 'metadata_loaded' not in st.session_state:
        m_df, m_eng, m_yards, init_df, init_total = load_metadata_and_init_data()
        st.session_state['view_data'] = init_df
        st.session_state['total_count'] = init_total
        st.session_state['models_df'] = m_df
        st.session_state['engines_list'] = m_eng
        st.session_state['yards_list'] = m_yards
        st.session_state['metadata_loaded'] = True
        st.session_state['is_filtered'] = False
        st.session_state['mode_demand'] = False

    df_raw = st.session_state['view_data']
    total_records = st.session_state['total_count']
    df_models = st.session_state['models_df']
    list_engines = st.session_state['engines_list']
    list_yards = st.session_state['yards_list']

    # 1. 사이드바
    with st.sidebar:
        st.title(t('app_title'))
        
        lang_choice = st.selectbox("Language / Язык / اللغة", ["English", "Korean", "Russian", "Arabic"], key='lang_selector')
        if lang_choice != st.session_state.language:
            st.session_state.language = lang_choice
            safe_rerun()

        st.divider()
        
        if st.session_state.user_role == 'guest':
            log_tab, sign_tab = st.tabs([t('login_title'), t('sign_up')])
            with log_tab:
                uid = st.text_input(f"👤 {t('id')}", key="l_id")
                upw = st.text_input(f"🔒 {t('pw')}", type="password", key="l_pw")
                if st.button(t('sign_in'), use_container_width=True):
                    role, name = login_user(uid, upw)
                    if role:
                        st.session_state.user_role = role
                        st.session_state.username = name if name else uid
                        safe_rerun()
                    else:
                        st.error(t('invalid_cred'))
                        
            with sign_tab:
                new_id = st.text_input(f"👤 {t('id')}", key="s_id")
                new_pw = st.text_input(f"🔒 {t('pw')}", type="password", key="s_pw")
                new_name = st.text_input(f"📛 {t('user_name')}", key="s_name")
                new_comp = st.text_input(f"🏢 {t('company_name')}", key="s_comp")
                new_country = st.selectbox(f"🌍 {t('country')}", COUNTRY_LIST, key="s_country")
                new_email = st.text_input(f"📧 {t('email')}", key="s_email")
                new_phone = st.text_input(f"📞 {t('phone')}", key="s_phone")
                
                if st.button(t('sign_up'), use_container_width=True):
                    if not all([new_id, new_pw, new_name, new_comp, new_country, new_email]) or new_country == "Select Country":
                        st.error(t('signup_missing_fields'))
                    else:
                        if create_user(new_id, new_pw, new_name, new_comp, new_country, new_email, new_phone):
                            st.success(t('signup_success'))
                        else:
                            st.error(t('user_exists'))

        else:
            role_text = "Manager" if st.session_state.user_role == 'admin' else "Buyer"
            st.success(t('welcome').format(st.session_state.username))
            if st.button(t('logout')):
                st.session_state.user_role = 'guest'
                st.session_state.username = 'Guest'
                del st.session_state['metadata_loaded']
                safe_rerun()

        st.divider()

        if st.session_state.user_role == 'admin':
            with st.expander(f"📂 {t('admin_tools')}"):
                up_files = st.file_uploader(t('data_upload'), type=['xlsx', 'xls', 'csv'], accept_multiple_files=True)
                if up_files and st.button(t('save_data')):
                    tot = 0
                    bar = st.progress(0)
                    for i, f in enumerate(up_files):
                        n, _ = save_vehicle_file(f)
                        tot += n
                        bar.progress((i+1)/len(up_files))
                    st.success(t('records_saved').format(tot))
                    load_metadata_and_init_data.clear()
                    safe_rerun()
                
                addr_file = st.file_uploader(t('addr_db'), type=['xlsx', 'xls', 'csv'], key="a_up")
                if addr_file and st.button(t('save_addr')):
                    cnt = save_address_file(addr_file)
                    st.success(t('addr_updated').format(cnt))
                    load_metadata_and_init_data.clear()
                    safe_rerun()

                if st.button(f"🗑️ {t('reset_inv')}"):
                    conn = sqlite3.connect(INVENTORY_DB)
                    conn.execute("DROP TABLE IF EXISTS vehicle_data")
                    conn.execute("DROP TABLE IF EXISTS junkyard_info")
                    conn.execute("DROP TABLE IF EXISTS model_list")
                    conn.commit()
                    conn.close()
                    init_inventory_db() # 즉시 복구
                    st.success(t('reset_done'))
                    load_metadata_and_init_data.clear()
                    safe_rerun()

                if st.button(f"⚙️ {t('reset_db')}"):
                    conn = sqlite3.connect(SYSTEM_DB)
                    conn.execute("DROP TABLE IF EXISTS users")
                    conn.execute("DROP TABLE IF EXISTS orders")
                    conn.execute("DROP TABLE IF EXISTS search_logs_v2")
                    conn.execute("DROP TABLE IF EXISTS translations")
                    conn.commit()
                    conn.close()
                    init_system_db() # 즉시 복구
                    st.success(t('reset_done'))
                    safe_rerun()
            
            st.divider()
            st.subheader(f"👑 {t('admin_menu')}")
            if st.button(f"🔮 {t('demand_analysis')}", use_container_width=True):
                st.session_state['mode_demand'] = True
                safe_rerun()

        st.subheader(f"🔍 {t('search_filter')}")
        search_tabs = st.tabs([f"🚙 {t('tab_vehicle')}", f"🔧 {t('tab_engine')}", f"🏭 {t('tab_yard')}"])
        
        with search_tabs[0]: 
            makers = sorted(df_models['manufacturer'].unique().tolist())
            makers.insert(0, "All")
            sel_maker = st.selectbox(t('manufacturer'), makers, key="msel")
            
            c1, c2 = st.columns(2)
            with c1: sel_sy = st.number_input(t('from_year'), 1990, 2030, 2000, key="sy")
            with c2: sel_ey = st.number_input(t('to_year'), 1990, 2030, 2025, key="ey")
            
            if sel_maker != "All":
                f_models = sorted(df_models[df_models['manufacturer'] == sel_maker]['model_name'].unique().tolist())
            else:
                f_models = sorted(df_models['model_name'].unique().tolist())
            sel_models = st.multiselect(t('model'), f_models, key="mms")
            
            if st.button(f"🔍 {t('search_btn_veh')}", type="primary"):
                log_search(sel_models, 'model')
                res, tot = search_data_from_db(sel_maker, sel_models, [], sel_sy, sel_ey, [])
                st.session_state['view_data'] = res
                st.session_state['total_count'] = tot
                st.session_state['is_filtered'] = True
                st.session_state['mode_demand'] = False
                safe_rerun()

        with search_tabs[1]: 
            sel_engines = st.multiselect(t('engine_code'), sorted(list_engines), key="es")
            if st.button(f"🔍 {t('search_btn_eng')}", type="primary"):
                log_search(sel_engines, 'engine')
                res, tot = search_data_from_db(None, [], sel_engines, 1990, 2030, [])
                st.session_state['view_data'] = res
                st.session_state['total_count'] = tot
                st.session_state['is_filtered'] = True
                st.session_state['mode_demand'] = False
                safe_rerun()

        with search_tabs[2]: 
            yard_opts = list_yards
            if st.session_state.user_role == 'buyer':
                yard_opts = sorted(list(set([generate_alias(name) for name in list_yards])))
            else:
                yard_opts = sorted(list_yards)
                
            sel_yards = st.multiselect(t('partner_name'), yard_opts, key="ys")
            
            if st.button(f"🔍 {t('search_btn_partners')}", type="primary"):
                real_yard_names = []
                if st.session_state.user_role == 'buyer':
                    for y in list_yards:
                        if generate_alias(y) in sel_yards:
                            real_yard_names.append(y)
                else:
                    real_yard_names = sel_yards
                    
                res, tot = search_data_from_db(None, [], [], 1990, 2030, real_yard_names)
                st.session_state['view_data'] = res
                st.session_state['total_count'] = tot
                st.session_state['is_filtered'] = True
                st.session_state['mode_demand'] = False
                safe_rerun()

        if st.button(f"🔄 {t('reset_filters')}", use_container_width=True, on_click=reset_dashboard):
            pass

    # 2. 메인 화면
    if st.session_state.mode_demand and st.session_state.user_role == 'admin':
        st.title(f"📈 {t('analysis_title')}")
        eng_trend, mod_trend = get_search_trends()
        c1, c2 = st.columns(2)
        with c1:
            st.subheader(f"🔥 {t('top_engines')}")
            if not eng_trend.empty:
                fig = px.bar(eng_trend, x='count', y='keyword', orientation='h', text='count')
                st.plotly_chart(fig, use_container_width=True)
            else: st.info(t('no_results'))
        with c2:
            st.subheader(f"🚙 {t('top_models')}")
            if not mod_trend.empty:
                fig = px.bar(mod_trend, x='count', y='keyword', orientation='h', text='count')
                st.plotly_chart(fig, use_container_width=True)
            else: st.info(t('no_results'))
    else:
        st.title(t('main_title'))
        
        df_view = st.session_state['view_data']
        total_cnt = st.session_state['total_count']
        
        df_display = mask_dataframe(df_view, st.session_state.user_role)
        
        if st.session_state.user_role == 'admin':
            main_tabs = st.tabs([f"📊 {t('tab_inventory')}", f"📩 {t('tab_orders')}"])
        else:
            main_tabs = st.tabs([f"📊 {t('tab_results')}", f"🛒 {t('tab_my_orders')}"])

        with main_tabs[0]:
            if df_display.empty:
                if st.session_state['is_filtered']:
                    st.warning(t('no_results'))
                else:
                    st.info(t('plz_select'))
            else:
                c1, c2, c3 = st.columns(3)
                c1.metric(t('total_veh'), f"{total_cnt:,} EA")
                c2.metric(t('matched_eng'), f"{df_display['engine_code'].nunique()} Types")
                sup_label = t('real_yards') if st.session_state.user_role == 'admin' else t('partners_cnt')
                c3.metric(sup_label, f"{df_display['junkyard'].nunique()} EA")
                
                if total_cnt > 5000:
                    st.warning(t('limit_warning').format(total_cnt))
                
                st.divider()
                st.subheader(f"📦 {t('stock_by_partner')}")
                
                grp_cols = ['junkyard', 'address']
                if st.session_state.user_role == 'admin' and 'region' in df_display.columns:
                    grp_cols.append('region')
                
                if 'address' in df_display.columns:
                    df_display['address'] = df_display['address'].fillna("Unknown")

                stock_summary = df_display.groupby(grp_cols).size().reset_index(name='qty').sort_values('qty', ascending=False)
                selection = st.dataframe(stock_summary, use_container_width=True, hide_index=True, selection_mode="single-row", on_select="rerun")
                
                if len(selection.selection.rows) > 0:
                    sel_idx = selection.selection.rows[0]
                    sel_row = stock_summary.iloc[sel_idx]
                    target_partner = sel_row['junkyard']
                    stock_cnt = sel_row['qty']
                    
                    if st.session_state.user_role == 'guest':
                        st.warning(t('login_req_warn'))
                    else:
                        st.success(t('selected_msg').format(target_partner, stock_cnt))
                        
                        with st.form("order_form"):
                            st.markdown(f"### {t('req_quote_title').format(target_partner)}")
                            c_a, c_b = st.columns(2)
                            with c_a:
                                buyer_name = st.text_input(t('name_company'), value=st.session_state.username)
                                contact = st.text_input(t('contact'))
                                req_qty = st.number_input(t('qty'), min_value=1, value=1)
                            with c_b:
                                s_maker = st.session_state.get('msel', 'All')
                                s_models = st.session_state.get('mms', [])
                                s_engines = st.session_state.get('es', [])
                                s_sy = st.session_state.get('sy', 2000)
                                s_ey = st.session_state.get('ey', 2025)

                                item_desc = []
                                if s_engines: item_desc.append(f"Engine: {','.join(s_engines[:3])}")
                                elif s_models: item_desc.append(f"Model: {','.join(s_models[:3])}")
                                elif s_maker != "All": item_desc.append(f"{s_maker} Cars")
                                else: item_desc.append("Auto Parts")
                                
                                if not s_engines: item_desc.append(f"({s_sy}~{s_ey})")
                                def_item = " ".join(item_desc)
                                
                                item = st.text_input(t('item'), value=def_item)
                                offer = st.text_input(t('unit_price'), placeholder="e.g. $500/ea")
                            
                            msg = st.text_area(t('message'), height=80)
                            
                            if st.form_submit_button(t('send_btn')):
                                if not contact or not item or not offer:
                                    st.error(t('fill_error'))
                                else:
                                    conn = sqlite3.connect(SYSTEM_DB)
                                    cur = conn.cursor()
                                    real_name = target_partner
                                    if st.session_state.user_role == 'buyer':
                                        try:
                                            temp_df = df_view.copy()
                                            temp_df['alias'] = temp_df['junkyard'].apply(generate_alias)
                                            match = temp_df[temp_df['alias'] == target_partner]
                                            if not match.empty:
                                                real_name = match['junkyard'].iloc[0]
                                        except: real_name = "Unknown"
                                    
                                    if "EMAIL" in st.secrets:
                                        admin_email = st.secrets["EMAIL"]["admin_email"]
                                        send_email(admin_email, f"[K-Used Car] New Quote Request from {buyer_name}",
                                                   f"Buyer: {buyer_name}\nContact: {contact}\nItem: {item}\nQty: {req_qty}\nPrice: {offer}\nMessage: {msg}")

                                    summary = f"Qty: {req_qty} (Total Stock: {stock_cnt}), Item: {item}, Price: {offer}, Msg: {msg}"
                                    cur.execute("INSERT INTO orders (buyer_id, contact_info, target_partner_alias, real_junkyard_name, items_summary, status) VALUES (?, ?, ?, ?, ?, ?)",
                                                (buyer_name, contact, target_partner, real_name, summary, 'PENDING'))
                                    conn.commit()
                                    conn.close()
                                    st.success(t('inquiry_sent'))

                st.divider()
                st.subheader(f"📋 {t('item_list')}")
                st.dataframe(df_display, use_container_width=True)

        if st.session_state.user_role == 'admin':
            with main_tabs[1]:
                st.subheader(f"{t('incoming_quotes')}")
                conn = sqlite3.connect(SYSTEM_DB)
                orders = pd.read_sql("SELECT * FROM orders ORDER BY created_at DESC", conn)
                conn.close()
                
                if not orders.empty:
                    for idx, row in orders.iterrows():
                        with st.expander(f"[{row['status']}] {row['created_at']} | From: {row['buyer_id']}"):
                            st.write(f"**Contact:** {row['contact_info']}")
                            st.write(f"**Target:** {row['real_junkyard_name']} ({row['target_partner_alias']})")
                            st.info(f"**Request:** {row['items_summary']}")
                            
                            st.markdown("### ✍️ Reply & Quote")
                            with st.form(f"reply_form_{row['id']}"):
                                c1, c2 = st.columns(2)
                                with c1:
                                    reply_price = st.text_input("Final Quote Price (USD)", placeholder="$000")
                                with c2:
                                    reply_files = st.file_uploader("Attach Images (Max 5)", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
                                
                                reply_msg = st.text_area("Message to Buyer", value=f"Dear {row['buyer_id']},\n\nThank you for your inquiry. We are pleased to offer:\n\n", height=150)
                                
                                if st.form_submit_button("Send Reply & Set to QUOTED"):
                                    email_content = f"{reply_msg}\n\n[Quote Price]: {reply_price}"
                                    sent = send_email(row['contact_info'], f"[K-Used Car] Quote for your request #{row['id']}", email_content, reply_files)
                                    
                                    if sent:
                                        img_list = []
                                        if reply_files:
                                            for f in reply_files:
                                                f.seek(0)
                                                b64_str = base64.b64encode(f.read()).decode('utf-8')
                                                img_list.append(b64_str)
                                        
                                        conn_up = sqlite3.connect(SYSTEM_DB)
                                        conn_up.execute("UPDATE orders SET status = 'QUOTED', reply_text = ?, reply_images = ? WHERE id = ?", 
                                                        (f"Price: {reply_price}\n\n{reply_msg}", json.dumps(img_list), row['id']))
                                        conn_up.commit()
                                        conn_up.close()
                                        st.success("Reply sent and status updated to QUOTED!")
                                        time.sleep(1)
                                        safe_rerun()
                                    else:
                                        st.error("Failed to send email. Check SMTP settings.")

                            st.divider()
                            c1, c2 = st.columns([3, 1])
                            with c1:
                                new_status = st.selectbox(t('status_change'), 
                                                          ["PENDING", "QUOTED", "PAID", "PROCESSING", "SHIPPING", "DONE", "CANCELLED"],
                                                          index=["PENDING", "QUOTED", "PAID", "PROCESSING", "SHIPPING", "DONE", "CANCELLED"].index(row['status']),
                                                          key=f"st_{row['id']}")
                            with c2:
                                st.write("")
                                st.write("")
                                if st.button(t('update_btn'), key=f"btn_{row['id']}"):
                                    update_order_status(row['id'], new_status)
                                    st.success(t('updated_msg'))
                                    time.sleep(0.5)
                                    safe_rerun()
                else:
                    st.info(t('no_orders_admin'))

        if st.session_state.user_role == 'buyer':
            with main_tabs[1]: 
                st.subheader(f"{t('my_quote_req')}")
                conn = sqlite3.connect(SYSTEM_DB)
                try:
                    my_orders = pd.read_sql("SELECT * FROM orders WHERE buyer_id = ? ORDER BY created_at DESC", conn, params=(st.session_state.username,))
                except:
                    my_orders = pd.DataFrame()
                conn.close()

                if not my_orders.empty:
                    for idx, row in my_orders.iterrows():
                        status_color = "green" if row['status'] == 'DONE' else "orange" if row['status'] == 'PENDING' else "blue"
                        with st.expander(f"[{row['created_at']}] {row['target_partner_alias']} ({row['status']})"):
                            st.caption(f"Status: :{status_color}[{row['status']}]")
                            st.write(f"**Request Details:** {row['items_summary']}")
                            
                            if row['status'] == 'QUOTED' or row.get('reply_text'):
                                st.divider()
                                st.info("📬 Admin Reply:")
                                if row.get('reply_text'):
                                    st.text(row['reply_text'])
                                
                                if row.get('reply_images'):
                                    try:
                                        img_data = json.loads(row['reply_images'])
                                        if img_data:
                                            st.write("**Attached Images:**")
                                            cols = st.columns(len(img_data))
                                            for i, b64_img in enumerate(img_data):
                                                with cols[i]:
                                                    st.image(base64.b64decode(b64_img), use_container_width=True)
                                    except: pass
                            
                            if row['status'] == 'QUOTED':
                                st.success(t('offer_received'))
                else:
                    st.info(t('no_orders_buyer'))

except Exception as e:
    st.error("⛔ 앱 실행 중 문제가 발생했습니다.")
    with st.expander("상세 오류 보기"):
        st.code(traceback.format_exc())
