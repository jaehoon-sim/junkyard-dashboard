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
# 다국어 번역 데이터 (4개 국어)
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
        'admin_dashboard': "Admin Dashboard", 'user_mgmt': "User Management", 
        'data_upload': "Data Upload", 'stock_upload': "Stock Upload", 'partner_upload': "Partner Info Upload",
        'role': "Role", 'email': "Email", 'phone': "Phone", 'update': "Update Info", 'delete': "Delete User",
        'upload_guide': "Upload Excel with headers: name, email, company, country, phone",
        'filter_title': "🔍 Search Options",
        'detail_view': "🚗 Vehicle Detail",
        'edit_view': "✏️ Edit Vehicle Info (My Stock)",
        'update_btn': "Update Vehicle",
        'upload_photo': "Upload New Photos"
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
        'admin_dashboard': "관리자 대시보드", 'user_mgmt': "회원 관리", 
        'data_upload': "데이터 업로드", 'stock_upload': "차량 재고 업로드", 'partner_upload': "회원사(폐차장) 정보 업로드",
        'role': "권한", 'email': "이메일", 'phone': "연락처", 'update': "정보 수정", 'delete': "회원 삭제",
        'upload_guide': "엑셀 헤더 양식: name, email, company, country, phone",
        'filter_title': "🔍 검색 옵션 (여기를 눌러 필터를 여세요)",
        'detail_view': "🚗 차량 상세 정보",
        'edit_view': "✏️ 매물 정보 수정 (내 차량)",
        'update_btn': "정보 업데이트 저장",
        'upload_photo': "새로운 사진 업로드"
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
        'admin_dashboard': "Панель администратора", 'user_mgmt': "Управление пользователями", 
        'data_upload': "Загрузка данных", 'stock_upload': "Загрузка склада", 'partner_upload': "Информация о партнере",
        'role': "Роль", 'email': "Email", 'phone': "Телефон", 'update': "Обновить", 'delete': "Удалить",
        'upload_guide': "Заголовки Excel: name, email, company, country, phone",
        'filter_title': "🔍 Параметры поиска",
        'detail_view': "🚗 Детали выбранного автомобиля",
        'edit_view': "✏️ Редактировать (Мой склад)",
        'update_btn': "Обновить",
        'upload_photo': "Загрузить фото"
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
        'admin_dashboard': "لوحة التحكم", 'user_mgmt': "إدارة المستخدمين", 
        'data_upload': "تحميل البيانات", 'stock_upload': "تحميل المخزون", 'partner_upload': "تحميل معلومات الشريك",
        'role': "الدور", 'email': "البريد الإلكتروني", 'phone': "الهاتف", 'update': "تحديث", 'delete': "حذف",
        'upload_guide': "رؤوس ملف Excel: name, email, company, country, phone",
        'filter_title': "🔍 خيارات البحث",
        'detail_view': "🚗 تفاصيل السيارة المختارة",
        'edit_view': "✏️ تعديل المعلومات (مخزوني)",
        'update_btn': "تحديث",
        'upload_photo': "تحميل صور جديدة"
    }
}

def t(key):
    lang = st.session_state.get('lang', 'English')
    return TRANS.get(lang, TRANS['English']).get(key, TRANS['English'].get(key, key))

# ---------------------------------------------------------
# [기능] 상단 상세 뷰 (마스킹 및 수정 기능)
# ---------------------------------------------------------
def render_top_detail_view(container, row, role, my_company):
    with container:
        with st.container(border=True):
            is_my_car = (role == 'partner' and str(row['junkyard']) == str(my_company))
            
            display_yard = row['junkyard']
            if role == 'buyer':
                display_yard = "Verified Partner (인증 파트너)"

            if is_my_car:
                st.subheader(f"{t('edit_view')} : {row['model_name']} ({row['vin']})")
                with st.form(key=f"edit_form_{row['vin']}"):
                    c1, c2 = st.columns([1, 1.5])
                    with c1:
                        img_str = str(row.get('photos', ''))
                        images = [img.strip() for img in img_str.split(',') if img.strip()]
                        if images and os.path.exists(images[0]):
                            st.image(images[0], width=300)
                            st.caption(f"Photos: {len(images)}")
                        else: st.info("No Image")
                        new_files = st.file_uploader(t('upload_photo'), accept_multiple_files=True, type=['png','jpg','jpeg'])
                    with c2:
                        st.info(f"Model: {row['manufacturer']} {row['model_name']} ({row['model_year']})")
                        new_price = st.number_input(t('price') + " ($)", value=float(row['price']), step=100.0)
                        new_mileage = st.number_input(t('mileage') + " (km)", value=float(row['mileage']), step=1000.0)
                        st.write(f"**VIN:** {row['vin']}")
                        st.write(f"**Engine:** {row['engine_code']}")
                    
                    if st.form_submit_button(t('update_btn'), type="primary"):
                        if db.update_vehicle_sales_info(row['vin'], new_price, new_mileage, new_files):
                            st.success("Updated Successfully!")
                            time.sleep(1)
                            st.rerun()
                        else: st.error("Failed to update.")
            else:
                st.subheader(f"{t('detail_view')} : {row['model_name']} ({row['vin']})")
                col1, col2 = st.columns([1, 1.5])
                with col1:
                    img_str = str(row.get('photos', ''))
                    images = [img.strip() for img in img_str.split(',') if img.strip()]
                    if images:
                        if os.path.exists(images[0]): st.image(images[0], use_container_width=True)
                        else: st.warning("Image missing")
                        if len(images) > 1:
                            with st.expander(f"📸 More Photos ({len(images)-1})"):
                                sub_cols = st.columns(3)
                                for i, img in enumerate(images[1:]):
                                    if os.path.exists(img): sub_cols[i % 3].image(img, use_container_width=True)
                    else: st.info("🖼️ No Images Available")

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
                    st.markdown(f"**Location (Yard):** {display_yard}")
                    st.markdown(f"**Reg Date:** {str(row['reg_date'])[:10]}")
                    
                    if st.button("📩 Send Inquiry", type="primary", use_container_width=True):
                        if db.place_order(st.session_state.user_id, row['junkyard'], row['vin'], row['model_name']):
                            st.success(f"Inquiry sent!")
                        else:
                            st.error("Failed to send inquiry.")

# ---------------------------------------------------------
# ✅ [복구된 함수] 회원가입 폼
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
# [공통] 마켓플레이스 UI
# ---------------------------------------------------------
def render_marketplace_ui(role):
    st.title(t('title'))
    detail_placeholder = st.container()

    with st.expander(t('filter_title'), expanded=True):
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
            if role == 'buyer':
                st.selectbox(t('junkyard'), ["All Partners (Hidden)"], disabled=True)
                sel_yards = []
            elif role == 'partner':
                my_yard = st.session_state.user_company
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

    tab_veh, tab_eng, tab_order, tab_yard = st.tabs([t('vehicle_inv'), t('engine_inv'), t('my_orders'), "Partners (Junkyards)"])
    
    with tab_veh:
        st.write(f"{t('total')}: {st.session_state.total_count}")
        df = st.session_state.view_data
        if not df.empty:
            display_df = df.copy()
            if role == 'buyer':
                display_df['junkyard'] = "Verified Partner"
            
            display_df['price_fmt'] = display_df['price'].apply(lambda x: f"${x:,.0f}" if x > 0 else "Contact")
            cols = ['manufacturer', 'model_name', 'model_detail', 'model_year', 
                    'engine_code', 'mileage', 'price_fmt', 'junkyard', 'reg_date', 'vin']
            
            event = st.dataframe(display_df[cols], use_container_width=True, on_select="rerun", selection_mode="single-row", hide_index=True)
            
            if len(event.selection.rows) > 0:
                selected_row = df.iloc[event.selection.rows[0]]
                render_top_detail_view(detail_placeholder, selected_row, role, st.session_state.user_company)
        else:
            st.info("No vehicles found.")

    with tab_eng:
        df = st.session_state.view_data
        if not df.empty:
            df_eng = df[df['engine_code'].notna() & (df['engine_code'] != '')].copy()
            if not df_eng.empty:
                display_df = df_eng.copy()
                if role == 'buyer': display_df['junkyard'] = "Verified Partner"
                display_df['price_fmt'] = display_df['price'].apply(lambda x: f"${x:,.0f}" if x > 0 else "Contact")
                
                cols = ['engine_code', 'manufacturer', 'model_name', 'model_year', 'mileage', 'price_fmt', 'junkyard', 'vin']
                event = st.dataframe(display_df[cols], use_container_width=True, on_select="rerun", selection_mode="single-row", hide_index=True)
                
                if len(event.selection.rows) > 0:
                    selected_row = df_eng.iloc[event.selection.rows[0]]
                    render_top_detail_view(detail_placeholder, selected_row, role, st.session_state.user_company)
            else: st.info("No engine data.")
        else: st.info("No data.")

    with tab_order:
        st.subheader(t('my_orders'))
        orders = db.get_orders(st.session_state.user_id, role)
        if not orders.empty:
            if role == 'partner' or role == 'admin':
                for index, row in orders.iterrows():
                    with st.expander(f"{row['created_at'][:16]} - {row['items_summary']} ({row['status']})"):
                        st.write(f"**Buyer:** {row['buyer_id']}")
                        st.write(f"**Target:** {row['real_junkyard_name']}")
                        st.write(f"**Details:** {row['items_summary']}")
                        new_status = st.selectbox("Status", ["PENDING", "CONFIRMED", "SHIPPED", "CANCELLED"], key=f"st_{row['id']}", index=["PENDING", "CONFIRMED", "SHIPPED", "CANCELLED"].index(row['status']) if row['status'] in ["PENDING", "CONFIRMED", "SHIPPED", "CANCELLED"] else 0)
                        reply_txt = st.text_area("Reply", value=row['reply_text'] if row['reply_text'] else "", key=f"rp_{row['id']}")
                        if st.button("Update", key=f"upd_{row['id']}"):
                            db.update_order(row['id'], new_status, reply_txt)
                            st.success("Updated")
                            st.rerun()
            else:
                st.dataframe(orders, use_container_width=True)
        else:
            st.info("No orders.")

    with tab_yard:
        if role == 'admin':
            yards = db.get_all_junkyards()
            if not yards.empty:
                st.dataframe(yards, use_container_width=True)
            else:
                st.info("No partner info uploaded.")
        else:
            st.info("Partner list is available for Admins only.")

# ---------------------------------------------------------
# 관리자 대시보드 (통합)
# ---------------------------------------------------------
def admin_dashboard():
    main_tab1, main_tab2, main_tab3 = st.tabs(["🔍 Marketplace", "👥 User Management", "📂 Data Upload"])
    
    with main_tab1:
        render_marketplace_ui('admin')

    with main_tab2:
        st.subheader("User Management")
        users_df = db.fetch_all_users()
        if not users_df.empty:
            st.dataframe(users_df, use_container_width=True)
            st.divider()
            target_uid = st.selectbox("Select User", users_df['user_id'].unique())
            if target_uid:
                cur_row = users_df[users_df['user_id'] == target_uid].iloc[0]
                with st.form("admin_edit"):
                    c1, c2, c3 = st.columns(3)
                    n_role = c1.selectbox("Role", ['buyer', 'partner', 'admin'], index=['buyer','partner','admin'].index(cur_row['role']))
                    n_email = c2.text_input("Email", value=cur_row['email'])
                    n_phone = c3.text_input("Phone", value=cur_row['phone'])
                    if st.form_submit_button("Update Info"):
                        db.update_user_role(target_uid, n_role)
                        db.update_user_info(target_uid, n_email, n_phone)
                        st.success("Updated!")
                        st.rerun()
                if st.button("Delete User"):
                    db.delete_user(target_uid)
                    st.warning("User Deleted")
                    st.rerun()

    with main_tab3:
        st.subheader("Data Upload Center")
        
        with st.expander("1. Bulk User Upload"):
            u_file = st.file_uploader("User Excel", type=['xlsx', 'xls'])
            if u_file and st.button("Upload Users"):
                df = pd.read_excel(u_file)
                s, f = db.create_user_bulk(df.to_dict('records'))
                st.success(f"Result: Success {s}, Fail {f}")

        with st.expander("2. Vehicle Stock Upload"):
            v_file = st.file_uploader("Stock Excel", type=['xlsx', 'xls', 'csv'])
            if v_file and st.button("Upload Stock"):
                cnt = db.save_vehicle_file(v_file)
                st.success(f"{cnt} vehicles uploaded.")

        with st.expander("3. Partner Info Upload (Junkyard Address)"):
            p_file = st.file_uploader("Partner Excel (Name, Address)", type=['xlsx', 'xls'])
            if p_file and st.button("Upload Partners"):
                cnt = db.save_address_file(p_file)
                st.success(f"{cnt} partners updated.")

# ---------------------------------------------------------
# 일반 사용자 (바이어/파트너) 대시보드
# ---------------------------------------------------------
def buyer_partner_dashboard():
    render_marketplace_ui(st.session_state.user_role)

# ---------------------------------------------------------
# 메인 함수
# ---------------------------------------------------------
def main():
    with st.sidebar:
        st.selectbox("Language / 언어 / Язык / اللغة", ["English", "Korean", "Russian", "Arabic"], key='lang')
        st.divider()

    credentials = db.fetch_users_for_auth()
    authenticator = stauth.Authenticate(credentials, 'k_hub', 'key', cookie_expiry_days=30)
    authenticator.login(location='main')

    if st.session_state["authentication_status"]:
        username = st.session_state["username"]
        name = st.session_state["name"]
        
        st.session_state.logged_in = True
        st.session_state.user_id = username
        
        user_info = credentials['usernames'][username]
        st.session_state.user_role = user_info.get('role', 'buyer')
        st.session_state.user_company = user_info.get('company') or username
        
        with st.sidebar:
            st.info(f"User: {name}\nRole: {st.session_state.user_role}")
            authenticator.logout(button_name=t('logout'), location='sidebar')

        if st.session_state.user_role == 'admin':
            admin_dashboard()
        else:
            buyer_partner_dashboard()

    elif st.session_state["authentication_status"] is False:
        st.error('Incorrect password')
        show_signup_expander()
    elif st.session_state["authentication_status"] is None:
        st.warning('Please login')
        show_signup_expander()

if __name__ == "__main__":
    main()