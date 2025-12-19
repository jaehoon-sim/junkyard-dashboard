# app.py
import streamlit as st
import pandas as pd
import time
import os
from modules import db

# ---------------------------------------------------------
# 1. Page Configuration & Session Setup
# ---------------------------------------------------------
st.set_page_config(page_title="K-Used Car Hub", layout="wide")

if 'user_id' not in st.session_state:
    st.session_state.update({
        'logged_in': False, 'user_id': None, 'user_role': None,
        'view_data': pd.DataFrame(), 'total_count': 0, 'is_filtered': False,
        'models_df': pd.DataFrame(), 'engines_list': [], 'yards_list': [], 'months_list': [],
        'lang': 'English' # 기본 언어
    })

# ---------------------------------------------------------
# 다국어 번역 데이터 (English, Korean, Russian, Arabic)
# ---------------------------------------------------------
TRANS = {
    'English': {
        'title': "K-Used Car/Engine Inventory",
        'login': "Login", 'logout': "Logout", 'signup': "Sign Up", 'create_acc': "Create Account",
        'vehicle_inv': "Vehicle Inventory", 'engine_inv': "Engine Inventory",
        'my_orders': "My Orders", 'admin_tools': "Admin Tools",
        'search_btn_veh': "Search", 'search_btn_eng': "Search Engine",
        'manufacturer': "Manufacturer", 'model': "Model", 'detail': "Detail",
        'year_range': "Model Year", 'reg_date': "Registration Date", 'engine_code': "Engine Code",
        'junkyard': "Partner (Yard)", 'photo_only': "Photo Only 📸", 'price_only': "Price Only 💰",
        'reset': "Reset Filter", 'total': "Total", 'price': "Price", 'mileage': "Mileage",
        'admin_dashboard': "Admin Dashboard", 'user_mgmt': "User Management", 'bulk_upload': "Bulk Upload (Excel)",
        'role': "Role", 'email': "Email", 'phone': "Phone", 'update': "Update Info", 'delete': "Delete User",
        'upload_guide': "Upload Excel with headers: name, email, company, country, phone",
        'filter_title': "🔍 Search Options"
    },
    'Korean': {
        'title': "K-중고차/부품 통합 재고",
        'login': "로그인", 'logout': "로그아웃", 'signup': "회원가입", 'create_acc': "계정 생성",
        'vehicle_inv': "차량 재고", 'engine_inv': "엔진/부품 재고",
        'my_orders': "나의 주문내역", 'admin_tools': "관리자 도구",
        'search_btn_veh': "검색 조회", 'search_btn_eng': "엔진 검색",
        'manufacturer': "제조사", 'model': "모델", 'detail': "세부모델",
        'year_range': "연식 범위", 'reg_date': "등록일 범위", 'engine_code': "엔진 코드",
        'junkyard': "파트너사(폐차장)", 'photo_only': "사진 있는 매물만 📸", 'price_only': "가격 공개 매물만 💰",
        'reset': "필터 초기화", 'total': "총", 'price': "가격", 'mileage': "주행거리",
        'admin_dashboard': "관리자 대시보드", 'user_mgmt': "회원 관리", 'bulk_upload': "엑셀 일괄 등록",
        'role': "권한", 'email': "이메일", 'phone': "연락처", 'update': "정보 수정", 'delete': "회원 삭제",
        'upload_guide': "엑셀 헤더 양식: name, email, company, country, phone",
        'filter_title': "🔍 검색 옵션 (여기를 눌러 필터를 여세요)"
    },
    'Russian': {
        'title': "Склад б/у автомобилей и запчастей",
        'login': "Войти", 'logout': "Выйти", 'signup': "Регистрация", 'create_acc': "Создать аккаунт",
        'vehicle_inv': "Автомобили", 'engine_inv': "Двигатели/Запчасти",
        'my_orders': "Мои заказы", 'admin_tools': "Админ",
        'search_btn_veh': "Поиск", 'search_btn_eng': "Поиск двигателя",
        'manufacturer': "Производитель", 'model': "Модель", 'detail': "Детали",
        'year_range': "Год выпуска", 'reg_date': "Дата регистрации", 'engine_code': "Код двигателя",
        'junkyard': "Партнер (Склад)", 'photo_only': "С фото 📸", 'price_only': "С ценой 💰",
        'reset': "Сброс", 'total': "Всего", 'price': "Цена", 'mileage': "Пробег",
        'admin_dashboard': "Панель администратора", 'user_mgmt': "Управление пользователями", 'bulk_upload': "Массовая загрузка (Excel)",
        'role': "Роль", 'email': "Email", 'phone': "Телефон", 'update': "Обновить", 'delete': "Удалить",
        'upload_guide': "Заголовки Excel: name, email, company, country, phone",
        'filter_title': "🔍 Параметры поиска"
    },
    'Arabic': {
        'title': "مركز السيارات المستعملة وقطع الغيار",
        'login': "تسجيل الدخول", 'logout': "تسجيل الخروج", 'signup': "اشتراك", 'create_acc': "إنشاء حساب",
        'vehicle_inv': "مخزون السيارات", 'engine_inv': "مخزون المحركات",
        'my_orders': "طلباتي", 'admin_tools': "أدوات المسؤول",
        'search_btn_veh': "بحث", 'search_btn_eng': "بحث عن محرك",
        'manufacturer': "الصانع", 'model': "الموديل", 'detail': "التفاصيل",
        'year_range': "سنة الصنع", 'reg_date': "تاريخ التسجيل", 'engine_code': "رمز المحرك",
        'junkyard': "الشريك (المستودع)", 'photo_only': "مع صور فقط 📸", 'price_only': "مع السعر فقط 💰",
        'reset': "إعادة تعيين", 'total': "المجموع", 'price': "السعر", 'mileage': "العداد",
        'admin_dashboard': "لوحة التحكم", 'user_mgmt': "إدارة المستخدمين", 'bulk_upload': "تحميل جماعي (Excel)",
        'role': "الدور", 'email': "البريد الإلكتروني", 'phone': "الهاتف", 'update': "تحديث", 'delete': "حذف",
        'upload_guide': "رؤوس ملف Excel: name, email, company, country, phone",
        'filter_title': "🔍 خيارات البحث"
    }
}

def t(key):
    lang = st.session_state.get('lang', 'English')
    # 선택된 언어에 키가 없으면 영어로 대체
    return TRANS.get(lang, TRANS['English']).get(key, TRANS['English'].get(key, key))

# ---------------------------------------------------------
# 2. 메인 애플리케이션
# ---------------------------------------------------------
def main():
    # --- [사이드바] 언어 및 사용자 정보 ---
    with st.sidebar:
        # 4개 국어 선택 가능하도록 수정
        st.selectbox("Language / 언어 / Язык / اللغة", ["English", "Korean", "Russian", "Arabic"], key='lang')
        st.divider()
        if st.session_state.logged_in:
            st.info(f"User: {st.session_state.user_id}\nRole: {st.session_state.user_role}")
            if st.button(t('logout')):
                st.session_state.logged_in = False
                st.session_state.user_id = None
                st.session_state.user_role = None
                st.rerun()
        else:
            st.warning("Please Login")

    # --- [페이지 라우팅] ---
    if not st.session_state.logged_in:
        login_page()
    else:
        if st.session_state.user_role == 'admin':
            admin_dashboard()
        else:
            buyer_partner_dashboard()

# ---------------------------------------------------------
# 3. 상세 화면 함수들
# ---------------------------------------------------------

def login_page():
    st.title(t('title'))
    tab1, tab2 = st.tabs([t('login'), t('signup')])
    
    with tab1:
        uid = st.text_input("ID / Email", key="login_id")
        pwd = st.text_input("Password", type="password", key="login_pw")
        if st.button(t('login')):
            users = db.fetch_users_for_auth()
            if uid in users['usernames']:
                user_info = users['usernames'][uid]
                st.session_state.logged_in = True
                st.session_state.user_id = uid
                st.session_state.user_role = user_info['role']
                db.reset_dashboard()
                st.rerun()
            else:
                st.error("Invalid User ID or Password")

    with tab2:
        st.subheader(t('create_acc'))
        new_uid = st.text_input("ID (Email)", key="new_uid")
        new_pw = st.text_input("Password", type="password", key="new_pw")
        new_name = st.text_input("Name", key="new_name")
        col1, col2 = st.columns(2)
        new_comp = col1.text_input("Company", key="new_comp")
        new_country = col2.text_input("Country", key="new_country")
        new_phone = st.text_input("Phone", key="new_phone")
        
        if st.button(t('signup')):
            if db.create_user(new_uid, new_pw, new_name, new_comp, new_country, new_uid, new_phone):
                st.success("Account Created! Please Login.")
            else:
                st.error("ID already exists.")

def admin_dashboard():
    st.title(t('admin_dashboard'))
    tab1, tab2 = st.tabs([t('user_mgmt'), t('bulk_upload')])
    
    with tab1:
        users_df = db.fetch_all_users()
        if not users_df.empty:
            st.dataframe(users_df[['user_id', 'name', 'company', 'country', 'role', 'phone']], use_container_width=True)
            st.divider()
            
            st.subheader("Edit User Role / Info")
            target_uid = st.selectbox("Select User to Edit", users_df['user_id'].unique())
            
            if target_uid:
                cur_row = users_df[users_df['user_id'] == target_uid].iloc[0]
                with st.form("admin_edit_user"):
                    c1, c2, c3 = st.columns(3)
                    n_role = c1.selectbox(t('role'), ['buyer', 'partner', 'admin'], 
                                          index=['buyer','partner','admin'].index(cur_row['role']))
                    n_email = c2.text_input(t('email'), value=cur_row['email'] if cur_row['email'] else "")
                    n_phone = c3.text_input(t('phone'), value=cur_row['phone'] if cur_row['phone'] else "")
                    
                    if st.form_submit_button(t('update')):
                        db.update_user_role(target_uid, n_role)
                        db.update_user_info(target_uid, n_email, n_phone)
                        st.success("Updated Successfully!")
                        time.sleep(1)
                        st.rerun()
                
                with st.expander(t('delete')):
                    if st.button("Delete Permanently", type="primary"):
                        db.delete_user(target_uid)
                        st.warning("User Deleted")
                        st.rerun()

    with tab2:
        st.subheader(t('bulk_upload'))
        st.info(t('upload_guide'))
        uploaded_file = st.file_uploader("Upload Excel (.xlsx, .xls)", type=['xlsx', 'xls'])
        
        if uploaded_file:
            try:
                df = pd.read_excel(uploaded_file)
                st.write("Preview:", df.head())
                if st.button("Register Users to DB"):
                    user_list = df.to_dict('records')
                    suc, fail = db.create_user_bulk(user_list)
                    st.success(f"Upload Complete! Success: {suc}, Failed(Duplicate): {fail}")
            except Exception as e:
                st.error(f"Error reading file: {e}")

def buyer_partner_dashboard():
    st.title(t('title'))
    
    # [수정] 상단 Expander 필터
    with st.expander(t('filter_title'), expanded=True):
        if st.session_state.models_df.empty:
            db.reset_dashboard()
            
        m_df = st.session_state.models_df
        
        # 필터 행 1
        c1, c2, c3 = st.columns(3)
        with c1:
            mfr_list = ["All"] + sorted(m_df['manufacturer'].unique().tolist())
            sel_mfr = st.selectbox(t('manufacturer'), mfr_list)
        with c2:
            models_for_mfr = []
            if sel_mfr != "All":
                models_for_mfr = sorted(m_df[m_df['manufacturer'] == sel_mfr]['model_name'].unique().tolist())
            sel_models = st.multiselect(t('model'), models_for_mfr)
        with c3:
            sy, ey = st.slider(t('year_range'), 1990, 2025, (2000, 2025))

        # 필터 행 2
        c4, c5, c6 = st.columns(3)
        with c4:
            months = st.session_state.months_list
            if months:
                sm, em = st.select_slider(t('reg_date'), options=sorted(months), value=(min(months), max(months)))
            else:
                sm, em = "2000-01", "2025-12"
        with c5:
            sel_engines = st.multiselect(t('engine_code'), st.session_state.engines_list)
        with c6:
            sel_yards = st.multiselect(t('junkyard'), st.session_state.yards_list)

        # 필터 행 3 (체크박스 및 버튼)
        st.divider()
        cb1, cb2, cb3, cb4 = st.columns([1, 1, 1, 1])
        with cb1:
            chk_photo = st.checkbox(t('photo_only'))
        with cb2:
            chk_price = st.checkbox(t('price_only'))
        with cb3:
            if st.button(t('search_btn_veh'), type="primary", use_container_width=True):
                df, count = db.search_data(
                    sel_mfr, sel_models, [], sel_engines, 
                    sy, ey, sel_yards, sm, em, 
                    only_photo=chk_photo, only_price=chk_price
                )
                st.session_state.view_data = df
                st.session_state.total_count = count
                st.session_state.is_filtered = True
        with cb4:
            if st.button(t('reset'), use_container_width=True):
                db.reset_dashboard()
                st.rerun()

    # --- 메인 탭 화면 ---
    tab_veh, tab_eng, tab_order = st.tabs([t('vehicle_inv'), t('engine_inv'), t('my_orders')])
    
    # [수정] 차량 목록을 테이블 형태로 표시 (빠른 속도)
    with tab_veh:
        st.write(f"{t('total')}: {st.session_state.total_count}")
        
        df = st.session_state.view_data
        if not df.empty:
            # 표시용 데이터 준비
            display_df = df.copy()
            display_df['price_fmt'] = display_df['price'].apply(lambda x: f"${x:,.0f}" if x > 0 else "Contact")
            
            # 테이블 컬럼 설정
            cols_to_show = ['manufacturer', 'model_name', 'model_detail', 'model_year', 
                            'engine_code', 'mileage', 'price_fmt', 'junkyard', 'reg_date', 'vin']
            
            st.dataframe(
                display_df[cols_to_show], 
                use_container_width=True,
                column_config={
                    "manufacturer": t('manufacturer'),
                    "model_name": t('model'),
                    "model_detail": t('detail'),
                    "model_year": st.column_config.NumberColumn(t('year_range'), format="%d"),
                    "price_fmt": t('price'),
                    "mileage": st.column_config.NumberColumn(t('mileage'), format="%.0f km"),
                    "reg_date": st.column_config.DateColumn(t('reg_date')),
                    "junkyard": t('junkyard'),
                },
                hide_index=True
            )
        else:
            st.info("No vehicles found matching filters.")

    with tab_eng:
        st.info("Engine inventory module is under maintenance.")

    with tab_order:
        st.subheader(t('my_orders'))
        orders = db.get_orders(st.session_state.user_id, st.session_state.user_role)
        if not orders.empty:
            st.dataframe(orders, use_container_width=True)
        else:
            st.info("No order history.")

if __name__ == "__main__":
    main()