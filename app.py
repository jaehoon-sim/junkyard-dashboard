# app.py
import streamlit as st
import pandas as pd
import time
import os
import streamlit_authenticator as stauth
from modules import db

# ---------------------------------------------------------
# 1. Page Configuration & Session Setup
# ---------------------------------------------------------
st.set_page_config(page_title="K-Used Car Hub", layout="wide")

if 'user_id' not in st.session_state:
    st.session_state.update({
        'logged_in': False, 'user_id': None, 'user_role': None, 'user_company': None,
        'view_data': pd.DataFrame(), 'total_count': 0, 'is_filtered': False,
        'models_df': pd.DataFrame(), 'engines_list': [], 'yards_list': [], 'months_list': [],
        'lang': 'English',
        'authentication_status': None, 'username': None, 'name': None,
        'selected_vin': None
    })

# ---------------------------------------------------------
# 다국어 번역 데이터
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
        'filter_title': "🔍 Search Options",
        'detail_view': "🚗 Selected Vehicle Detail"
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
        'filter_title': "🔍 검색 옵션 (여기를 눌러 필터를 여세요)",
        'detail_view': "🚗 선택된 차량 상세 정보"
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
        'filter_title': "🔍 Параметры поиска",
        'detail_view': "🚗 Детали выбранного автомобиля"
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
        'filter_title': "🔍 خيارات البحث",
        'detail_view': "🚗 تفاصيل السيارة المختارة"
    }
}

def t(key):
    lang = st.session_state.get('lang', 'English')
    return TRANS.get(lang, TRANS['English']).get(key, TRANS['English'].get(key, key))

# ---------------------------------------------------------
# [기능] 상단 상세 정보 렌더링
# ---------------------------------------------------------
def render_top_detail_view(container, row):
    with container:
        with st.container(border=True):
            st.subheader(f"{t('detail_view')} : {row['model_name']} ({row['vin']})")
            
            col1, col2 = st.columns([1, 1.5])
            
            with col1:
                img_str = str(row.get('photos', ''))
                images = [img.strip() for img in img_str.split(',') if img.strip()]
                
                if images:
                    first_img = images[0]
                    if os.path.exists(first_img):
                        st.image(first_img, use_container_width=True)
                    else:
                        st.warning("Image missing")
                    
                    if len(images) > 1:
                        with st.expander(f"📸 More Photos ({len(images)-1})"):
                            sub_cols = st.columns(3)
                            for i, img in enumerate(images[1:]):
                                if os.path.exists(img):
                                    sub_cols[i % 3].image(img, use_container_width=True)
                else:
                    st.info("🖼️ No Images Available")

            with col2:
                c_a, c_b = st.columns(2)
                with c_a:
                    st.markdown(f"**Manufacturer:** {row['manufacturer']}")
                    st.markdown(f"**Model:** {row['model_name']}")
                    st.markdown(f"**Detail:** {row['model_detail']}")
                    st.markdown(f"**Year:** {row['model_year']}")
                with c_b:
                    price = row.get('price', 0)
                    price_txt = f"${price:,.0f}" if price > 0 else "Contact Us"
                    st.markdown(f"### {t('price')}: :green[{price_txt}]")
                    
                    mileage = row.get('mileage', 0)
                    st.markdown(f"**{t('mileage')}:** {mileage:,.0f} km")
                    st.markdown(f"**Engine:** {row['engine_code']}")
                
                st.divider()
                st.markdown(f"**Location (Yard):** {row['junkyard']}")
                st.markdown(f"**Reg Date:** {str(row['reg_date'])[:10]}")
                
                if st.button("📩 Send Inquiry", type="primary", use_container_width=True):
                    st.success(f"Inquiry sent for VIN: {row['vin']}")

# ---------------------------------------------------------
# 회원가입 폼
# ---------------------------------------------------------
def show_signup_expander():
    with st.expander(t('create_acc') + " (New User?)"):
        with st.form("signup_form"):
            new_uid = st.text_input("ID (Email)")
            new_pw = st.text_input("Password", type="password")
            new_name = st.text_input("Name")
            c1, c2 = st.columns(2)
            new_comp = c1.text_input("Company")
            new_country = c2.text_input("Country")
            new_phone = st.text_input("Phone")
            
            if st.form_submit_button(t('signup')):
                if new_uid and new_pw:
                    if db.create_user(new_uid, new_pw, new_name, new_comp, new_country, new_uid, new_phone):
                        st.success("Account Created! Please Login above.")
                    else:
                        st.error("ID already exists.")
                else:
                    st.warning("Please fill in ID and Password.")

# ---------------------------------------------------------
# 2. 메인 애플리케이션
# ---------------------------------------------------------
def main():
    with st.sidebar:
        st.selectbox("Language / 언어 / Язык / اللغة", ["English", "Korean", "Russian", "Arabic"], key='lang')
        st.divider()

    credentials = db.fetch_users_for_auth()
    
    authenticator = stauth.Authenticate(
        credentials,
        'k_used_car_hub',
        'auth_key_signature',
        cookie_expiry_days=30
    )

    authenticator.login(location='main')

    if st.session_state["authentication_status"]:
        username = st.session_state["username"]
        name = st.session_state["name"]
        
        st.session_state.logged_in = True
        st.session_state.user_id = username
        
        # ✅ [핵심] 회사 정보 세션 저장
        user_info = credentials['usernames'][username]
        st.session_state.user_role = user_info.get('role', 'buyer')
        st.session_state.user_company = user_info.get('company') or username
        
        with st.sidebar:
            st.info(f"Welcome, **{name}**\n({st.session_state.user_role})")
            if st.session_state.user_role == 'partner':
                st.caption(f"Yard: {st.session_state.user_company}")
            authenticator.logout(button_name=t('logout'), location='sidebar')
        
        if st.session_state.user_role == 'admin':
            admin_dashboard()
        else:
            buyer_partner_dashboard()

    elif st.session_state["authentication_status"] is False:
        st.error('Username/password is incorrect')
        show_signup_expander()
        
    elif st.session_state["authentication_status"] is None:
        st.warning('Please enter your username and password')
        show_signup_expander()

# ---------------------------------------------------------
# 3. 상세 화면 함수들
# ---------------------------------------------------------

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
    
    # [1] 상세 정보 영역 (상단)
    detail_placeholder = st.container()

    # [2] 검색 필터
    with st.expander(t('filter_title'), expanded=False):
        if st.session_state.models_df.empty:
            db.reset_dashboard()
            
        m_df = st.session_state.models_df
        
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
            # ✅ [핵심] 파트너 권한 시 본인 회사만 선택 가능 (강제)
            if st.session_state.user_role == 'partner':
                my_yard = st.session_state.user_company
                # 기본값 고정 + 변경 불가
                sel_yards = st.multiselect(t('junkyard'), [my_yard], default=[my_yard], disabled=True)
            else:
                sel_yards = st.multiselect(t('junkyard'), st.session_state.yards_list)

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
                st.session_state.selected_vin = None 
        with cb4:
            if st.button(t('reset'), use_container_width=True):
                db.reset_dashboard()
                st.session_state.selected_vin = None
                st.rerun()

    # --- 메인 탭 화면 ---
    tab_veh, tab_eng, tab_order = st.tabs([t('vehicle_inv'), t('engine_inv'), t('my_orders')])
    
    with tab_veh:
        st.write(f"{t('total')}: {st.session_state.total_count}")
        
        df = st.session_state.view_data
        if not df.empty:
            display_df = df.copy()
            display_df['price_fmt'] = display_df['price'].apply(lambda x: f"${x:,.0f}" if x > 0 else "Contact")
            
            cols_to_show = ['manufacturer', 'model_name', 'model_detail', 'model_year', 
                            'engine_code', 'mileage', 'price_fmt', 'junkyard', 'reg_date', 'vin']
            
            # [테이블 뷰 + 선택]
            event = st.dataframe(
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
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row"
            )
            
            # [선택 시 상단 렌더링]
            if len(event.selection.rows) > 0:
                selected_index = event.selection.rows[0]
                selected_row = df.iloc[selected_index]
                render_top_detail_view(detail_placeholder, selected_row)
            
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