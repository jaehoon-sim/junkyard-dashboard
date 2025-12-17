# modules/utils.py
import hashlib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import streamlit as st
import modules.constants as const

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text: return True
    return False

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
            files = attachment_files if isinstance(attachment_files, list) else [attachment_files]
            for file in files:
                try:
                    file.seek(0)
                    file_data = file.read()
                    fname = file.name if hasattr(file, 'name') else "attachment"
                    part = MIMEApplication(file_data, Name=fname)
                    part['Content-Disposition'] = f'attachment; filename="{fname}"'
                    msg.attach(part)
                except: continue

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        return True
    except: return False

def generate_alias(real_name):
    if not isinstance(real_name, str): return "Unknown"
    hash_object = hashlib.md5(str(real_name).encode())
    hash_int = int(hash_object.hexdigest(), 16) % 900 + 100 
    return f"Partner #{hash_int}"

def translate_address(addr, lang='English'):
    if not isinstance(addr, str) or addr == "검색실패" or "조회" in addr: return "Unknown Address"
    parts = addr.split()
    if len(parts) < 2: return "South Korea"
    k_do, k_city = parts[0][:2], parts[1]
    
    if lang == 'Russian': pmap, cmap = const.PROVINCE_MAP_RU, const.CITY_MAP
    elif lang == 'Arabic': pmap, cmap = const.PROVINCE_MAP_AR, const.CITY_MAP
    else: pmap, cmap = const.PROVINCE_MAP, const.CITY_MAP

    en_do = pmap.get(k_do, const.PROVINCE_MAP.get(k_do, k_do))
    city_core = k_city.replace('시','').replace('군','').replace('구','')
    en_city = cmap.get(city_core, const.CITY_MAP.get(city_core, city_core))
    
    if en_do in ['Seoul', 'Incheon', 'Busan', 'Daegu', 'Daejeon', 'Gwangju', 'Ulsan']:
        return f"{en_do}, Korea"
    else:
        suffix = "-si" if "시" in k_city else ("-gun" if "군" in k_city else "")
        if en_city != city_core: return f"{en_do}, {en_city}{suffix}"
        else: return f"{en_do}, Korea"

def mask_dataframe(df, role, lang='English'):
    if df.empty: return df
    df_safe = df.copy()
    
    if role in ['admin', 'partner']:
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
            df_safe['address'] = df_safe['address'].apply(lambda x: translate_address(x, lang))
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