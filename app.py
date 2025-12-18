# app.py
import streamlit as st
import pandas as pd
import time
import os
from modules import db
from PIL import Image

# ---------------------------------------------------------
# 1. Page Configuration & Session Setup
# ---------------------------------------------------------
st.set_page_config(page_title="K-Used Car Hub", layout="wide")

if 'user_id' not in st.session_state:
    st.session_state.update({
        'logged_in': False, 'user_id': None, 'user_role': None,
        'view_data': pd.DataFrame(), 'total_count': 0, 'is_filtered': False,
        'models_df': pd.DataFrame(), 'engines_list': [], 'yards_list': [], 'months_list': [],
        'lang': 'English'
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
        'search_btn_veh': "Search Vehicle", 'search_btn_eng': "Search Engine",
        'manufacturer': "Manufacturer", 'model': "Model", 'detail': "Detailed Model",
        'from_year': "From Year", 'to_year': "To Year",
        'start_month': "Start Month", 'end_month': "End Month",
        'keyword': "Keyword Search", 'reset': "Reset Filter",
        'order_mgmt': "Order Management",
        'save_data': "Save Vehicle Data", 'save_addr': "Save Address Data",
        'records_saved': "{} records saved successfully.",
        'addr_updated': "{} address records updated."
    },
    'Korean': {
        'title': "수출차량/엔진 재고 현황",
        'login': "로그인", 'logout': "로그아웃", 'signup': "회원가입", 'create_acc': "계정 생성",
        'vehicle_inv': "차량 재고 검색", 'engine_inv': "엔진 재고 검색",
        'my_orders': "나의 주문 내역", 'admin_tools': "관리자 도구",
        'search_btn_veh': "차량 검색", 'search_btn_eng': "엔진 검색",
        'manufacturer': "제조사", 'model': "모델", 'detail': "세부 모델",
        'from_year': "연식 (부터)", 'to_year': "연식 (까지)",
        'start_month': "등록년월 (부터)", 'end_month': "등록년월 (까지)",
        'keyword': "키워드 검색", 'reset': "필터 초기화",
        'order_mgmt': "주문 관리",
        'save_data': "차량 데이터 저장", 'save_addr': "주소 데이터 저장",
        'records_saved': "{}건 저장 완료.",
        'addr_updated': "{}건 주소 업데이트 완료."
    },
    'Russian': {
        'title': "Склад б/у автомобилей и двигателей",
        'login': "Вход", 'logout': "Выход", 'signup': "Регистрация", 'create_acc': "Создать аккаунт",
        'vehicle_inv': "Поиск автомобилей", 'engine_inv': "Поиск двигателей",
        'my_orders': "Мои заказы", 'admin_tools': "Инструменты админа",
        'search_btn_veh': "Найти автомобиль", 'search_btn_eng': "Найти двигатель",
        'manufacturer': "Производитель", 'model': "Модель", 'detail': "Подробно",
        'from_year': "Год (с)", 'to_year': "Год (по)",
        'start_month': "Месяц (с)", 'end_month': "Месяц (по)",
        'keyword': "Поиск по слову", 'reset': "Сброс",
        'order_mgmt': "Управление заказами",
        'save_data': "Сохранить авто", 'save_addr': "Сохранить адреса",
        'records_saved': "Сохранено записей: {}.",
        'addr_updated': "Обновлено адресов: {}."
    },
    'Arabic': {
        'title': "مخزون السيارات والمحركات المستعملة",
        'login': "تسجيل الدخول", 'logout': "تسجيل الخروج", 'signup': "اشتراك", 'create_acc': "إنشاء حساب",
        'vehicle_inv': "مخزون السيارات", 'engine_inv': "مخزون المحركات",
        'my_orders': "طلباتي", 'admin_tools': "أدوات المسؤول",
        'search_btn_veh': "بحث سيارة", 'search_btn_eng': "بحث محرك",
        'manufacturer': "الشركة المصنعة", 'model': "الموديل", 'detail': "تفاصيل",
        'from_year': "من سنة", 'to_year': "إلى سنة",
        'start_month': "من شهر", 'end_month': "إلى شهر",
        'keyword': "بحث بالكلمة", 'reset': "إعادة تعيين",
        'order_mgmt': "إدارة الطلبات",
        'save_data': "حفظ البيانات", 'save_addr': "حفظ العناوين",
        'records_saved': "تم حفظ {} سجل بنجاح.",
        'addr_updated': "تم تحديث {} عنوان."
    }
}

def t(key):
    lang_dict = TRANS.get(st.session_state.lang, TRANS['English'])
    return lang_dict.get(key, TRANS['English'].get(key, key))

# DB 초기화 및 메타데이터 로드
db.init_dbs()
if st.session_state.get('models_df') is None or st.session_state.get('models_df').empty:
    db.reset_dashboard()

# ---------------------------------------------------------
# 2. Sidebar (Auth & Admin Tools)
# ---------------------------------------------------------
with st.sidebar:
    st.title("🚛 K-Auto Hub")
    
    # [언어 선택 메뉴]
    lang_opt = st.radio("", ["English", "Korean", "Russian", "Arabic"], horizontal=True)
    if lang_opt != st.session_state.lang:
        st.session_state.lang = lang_opt
        st.rerun()

    st.divider()

    # Login / Logout Logic
    if not st.session_state.logged_in:
        with st.form("login_form"):
            uid = st.text_input("ID")
            upw = st.text_input("Password", type="password")
            if st.form_submit_button(t('login')):
                users = db.fetch_users_for_auth()['usernames']
                if uid in users:
                    user_info = users[uid]
                    st.session_state.logged_in = True
                    st.session_state.user_id = uid
                    st.session_state.user_role = user_info['role']
                    st.success(f"Welcome {user_info['name']}")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("Invalid ID or Password")
        
        with st.expander(f"📝 {t('create_acc')}"):
            with st.form("signup_form"):
                new_uid = st.text_input("New ID")
                new_pw = st.text_input("Password", type="password")
                new_name = st.text_input("Name")
                new_comp = st.text_input("Company Name")
                new_phone = st.text_input("Phone")
                new_email = st.text_input("Email")
                
                if st.form_submit_button(t('signup')):
                    if new_uid and new_pw:
                        if db.create_user(new_uid, new_pw, new_name, new_comp, "Global", new_email, new_phone):
                            st.success("Account created! Please login.")
                        else:
                            st.error("ID already exists.")
                    else:
                        st.warning("Please fill in ID and Password.")

    else:
        st.write(f"👤 **{st.session_state.user_id}** ({st.session_state.user_role})")
        if st.button(t('logout')):
            st.session_state.clear()
            st.rerun()
            
        st.divider()

        # Admin Tools
        if st.session_state.user_role == 'admin':
            with st.expander(f"📂 {t('admin_tools')}"):
                with st.form("up_veh"):
                    st.write("Vehicle Data Upload")
                    vf = st.file_uploader("", type=['xlsx','csv','xls'], accept_multiple_files=True)
                    if st.form_submit_button(t('save_data')):
                        cnt = sum([db.save_vehicle_file(f) for f in vf]) if vf else 0
                        st.success(t('records_saved').format(cnt))
                        db.load_metadata.clear()
                
                with st.form("up_addr"):
                    st.write("Address Data Upload")
                    af = st.file_uploader("", type=['xlsx','csv'])
                    if st.form_submit_button(t('save_addr')):
                        if af: st.success(t('addr_updated').format(db.save_address_file(af)))
                        db.load_metadata.clear()

                st.divider()
                st.write("🔧 **Data Maintenance**")
                if st.button("Normalize & Clean DB (기존 데이터 정리)"):
                    with st.spinner("Standardizing database..."):
                        success, msg = db.standardize_existing_data()
                        if success:
                            st.success(f"✅ Database Normalized! Processed {msg} records.")
                            db.load_metadata.clear()
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"Error: {msg}")

# ---------------------------------------------------------
# 3. Main Content
# ---------------------------------------------------------
st.title(t('title'))

if not st.session_state.logged_in:
    st.info("Please login to access the inventory system.")
    st.subheader("🔥 Search Trends")
    e_df, m_df = db.get_trends()
    c1, c2 = st.columns(2)
    with c1: 
        st.write("**Top Searched Models**")
        st.dataframe(m_df, use_container_width=True)
    with c2: 
        st.write("**Top Searched Engines**")
        st.dataframe(e_df, use_container_width=True)

else:
    # -----------------------------------------------------------
    # [Partner Mode] 판매자(폐차장)
    # -----------------------------------------------------------
    if st.session_state.user_role == 'partner':
        tabs = st.tabs(["🏭 My Inventory", "📦 Orders", "📊 Market View"])
        
        with tabs[0]:
            st.subheader(f"Inventory Management: {st.session_state.user_id}")
            
            my_cars, my_cnt = db.search_data("All", [], [], [], 1990, 2030, [st.session_state.user_id], "1990-01", "2030-12")
            st.info(f"Total Vehicles: {my_cnt} EA")
            
            if not my_cars.empty:
                st.dataframe(my_cars[['vin', 'manufacturer', 'model_name', 'model_detail', 'model_year', 'car_no', 'price', 'mileage']], use_container_width=True)
                
                st.divider()
                st.write("### ✏️ Edit Vehicle Info")
                
                search_query = st.text_input("🔍 Find Vehicle (VIN or Car No)", placeholder="Enter VIN or Car Number...")
                
                my_cars['label'] = "[" + my_cars['car_no'] + "] " + my_cars['model_name'] + " " + my_cars['model_detail'] + " (" + my_cars['vin'] + ")"
                
                if search_query:
                    search_query = search_query.lower().strip()
                    filtered_cars = my_cars[
                        my_cars['vin'].str.lower().str.contains(search_query) | 
                        my_cars['car_no'].str.lower().str.contains(search_query)
                    ]
                else:
                    filtered_cars = my_cars
                
                if not filtered_cars.empty:
                    sel_veh_label = st.selectbox("Select Vehicle from list", filtered_cars['label'])
                    
                    if sel_veh_label:
                        target_vin = sel_veh_label.split("(")[-1].replace(")", "")
                        row = my_cars[my_cars['vin'] == target_vin].iloc[0]
                        
                        st.markdown(f"**Selected:** {row['manufacturer']} {row['model_name']} ({row['car_no']})")
                        
                        with st.form("edit_veh"):
                            c1, c2 = st.columns(2)
                            p_price = c1.number_input("Sales Price (KRW)", value=int(row['price']) if row['price'] else 0, step=10000)
                            p_mile = c2.number_input("Mileage (km)", value=int(row['mileage']) if row['mileage'] else 0, step=1000)
                            
                            st.write("Photos:")
                            if row['photos']: st.caption(row['photos'])
                            
                            p_files = st.file_uploader("Upload Photos", accept_multiple_files=True, type=['png','jpg','jpeg'])
                            
                            if st.form_submit_button("💾 Save Changes"):
                                if db.update_vehicle_sales_info(target_vin, p_price, p_mile, p_files):
                                    # [핵심 수정] 저장 후 즉시 검색 캐시 비우기
                                    db.search_data.clear()
                                    st.success("Updated Successfully!")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error("Failed to update.")
                else:
                    st.warning("No vehicles match your search.")
            else:
                st.warning("No vehicles found in your inventory.")

        with tabs[1]:
            st.subheader("Incoming Orders")
            odf = db.get_orders(st.session_state.user_id, 'partner')
            if not odf.empty:
                for idx, row in odf.iterrows():
                    with st.expander(f"[{row['status']}] {row['created_at']} - Buyer: {row['buyer_id']}"):
                        st.write(f"**Items:** {row['items_summary']}")
                        st.write(f"**Contact:** {row['contact_info']}")
                        
                        c1, c2 = st.columns(2)
                        n_stat = c1.selectbox("Status", ["PENDING", "CONFIRMED", "SHIPPED", "CANCELLED"], 
                                              index=["PENDING", "CONFIRMED", "SHIPPED", "CANCELLED"].index(row['status']), key=f"s_{row['id']}")
                        n_reply = c2.text_input("Reply Message", value=row['reply_text'] if row['reply_text'] else "", key=f"r_{row['id']}")
                        
                        if st.button("Update Order", key=f"btn_{row['id']}"):
                            db.update_order(row['id'], status=n_stat, reply=n_reply)
                            st.success("Order Updated!")
                            st.rerun()
            else:
                st.info("No orders yet.")
        
        is_partner_viewing_market = True

    # -----------------------------------------------------------
    # [Admin / Buyer Mode] 일반 뷰어 화면
    # -----------------------------------------------------------
    else:
        is_partner_viewing_market = False

    if st.session_state.user_role != 'partner' or (st.session_state.user_role == 'partner' and is_partner_viewing_market):
        
        if st.session_state.user_role == 'partner':
             target_container = tabs[2]
        else:
             main_tabs = st.tabs([f"🚗 {t('vehicle_inv')}", f"⚙️ {t('engine_inv')}", 
                                  "👤 Users" if st.session_state.user_role == 'admin' else f"📦 {t('my_orders')}"])
             target_container = main_tabs[0]

        # ---------------------
        # 1. Vehicle Inventory
        # ---------------------
        with target_container:
            with st.expander("🔍 Search Filters", expanded=not st.session_state.is_filtered):
                c1, c2, c3 = st.columns(3)
                df_meta = st.session_state['models_df']
                makers = sorted(df_meta['manufacturer'].unique().tolist())
                makers.insert(0, "All")
                s_maker = c1.selectbox(t('manufacturer'), makers)
                
                if s_maker != "All":
                    f_models = sorted(df_meta[df_meta['manufacturer'] == s_maker]['model_name'].unique())
                else:
                    f_models = []
                s_models = c2.multiselect(t('model'), f_models)
                
                f_details = []
                if s_models:
                    filtered_rows = df_meta[
                        (df_meta['manufacturer'] == s_maker) & 
                        (df_meta['model_name'].isin(s_models))
                    ]
                    f_details = sorted([d for d in filtered_rows['model_detail'].unique() if d])
                s_details = c3.multiselect(t('detail'), f_details)

                cc1, cc2, cc3 = st.columns(3)
                sy = cc1.number_input(t('from_year'), 1990, 2030, 2000)
                ey = cc2.number_input(t('to_year'), 1990, 2030, 2025)
                
                yards_list = st.session_state.get('yards_list', [])
                s_yards = cc3.multiselect("Junkyard", yards_list)

                months = st.session_state.get('months_list', [])
                d_s = months[-1] if months else "2000-01"
                d_e = months[0] if months else "2030-12"
                cc4, cc5 = st.columns(2)
                sm = cc4.selectbox(t('start_month'), sorted(months) if months else [d_s], index=0)
                em = cc5.selectbox(t('end_month'), sorted(months, reverse=True) if months else [d_e], index=0)

                if st.button(t('search_btn_veh'), type="primary"):
                    db.log_search(s_models, 'model')
                    res, tot = db.search_data(s_maker, s_models, s_details, [], sy, ey, s_yards, sm, em)
                    st.session_state.update({'view_data': res, 'total_count': tot, 'is_filtered': True})
                    st.rerun()

                if st.button(t('reset')):
                    db.reset_dashboard()
                    st.rerun()

            st.divider()
            st.write(f"**Total Results:** {st.session_state.total_count}")
            
            df_view = st.session_state.view_data
            
            if not df_view.empty:
                # [Masking Logic]
                display_df = df_view.copy()
                if st.session_state.user_role == 'buyer':
                    display_df['junkyard'] = "🔒 Partner Seller"
                
                cols = ['vin', 'manufacturer', 'model_name', 'model_detail', 'model_year', 'price', 'mileage', 'junkyard', 'photos']
                st.dataframe(display_df[cols], use_container_width=True)
                
                # ---------------------------------------------
                # [NEW] 상세 정보 및 사진 확인 (바이어용)
                # ---------------------------------------------
                if st.session_state.user_role == 'buyer':
                    with st.expander("📸 View Vehicle Details & Photos (Click to Open)"):
                        st.info("Select a VIN from the list below to view photos and details.")
                        
                        buyer_search = st.text_input("🔍 Find Vehicle (VIN or Car No)", key="buyer_vin_search", placeholder="Enter VIN or Car No...")
                        
                        display_df['select_label'] = display_df['vin'] + " - " + display_df['model_name'] + " (" + display_df['model_detail'] + ")"
                        
                        if buyer_search:
                            buyer_search = buyer_search.lower().strip()
                            filtered_buyer_list = display_df[
                                display_df['vin'].str.lower().str.contains(buyer_search) |
                                display_df['car_no'].str.lower().str.contains(buyer_search)
                            ]
                        else:
                            filtered_buyer_list = display_df

                        if not filtered_buyer_list.empty:
                            selected_vin_label = st.selectbox("Select Vehicle", filtered_buyer_list['select_label'])
                            
                            if selected_vin_label:
                                sel_vin = selected_vin_label.split(" - ")[0]
                                detail_row = df_view[df_view['vin'] == sel_vin].iloc[0]
                                
                                d1, d2 = st.columns(2)
                                d1.write(f"**Model:** {detail_row['manufacturer']} {detail_row['model_name']} {detail_row['model_detail']}")
                                d1.write(f"**Year:** {detail_row['model_year']}")
                                d1.write(f"**Price:** {int(detail_row['price'] or 0):,} KRW")
                                d2.write(f"**Mileage:** {int(detail_row['mileage'] or 0):,} km")
                                d2.write(f"**Engine:** {detail_row['engine_code']}")
                                
                                st.divider()
                                st.write("#### 🖼️ Vehicle Photos")
                                if detail_row['photos']:
                                    photo_paths = detail_row['photos'].split(",")
                                    img_cols = st.columns(3)
                                    for i, p_path in enumerate(photo_paths):
                                        if os.path.exists(p_path):
                                            try:
                                                image = Image.open(p_path)
                                                img_cols[i % 3].image(image, caption=f"Photo {i+1}", use_container_width=True)
                                            except:
                                                img_cols[i % 3].error("Image load failed")
                                        else:
                                            # 디버깅을 위해 경로는 보여주되 이미지는 없다고 표시
                                            img_cols[i % 3].warning(f"File not found: {os.path.basename(p_path)}")
                                else:
                                    st.warning("No photos available for this vehicle.")
                        else:
                            st.warning("No vehicles match your search.")

                    # ---------------------------------------------
                    # 주문 기능 (기존)
                    # ---------------------------------------------
                    st.divider()
                    with st.expander("⚡ Request Quote / Order"):
                        sel_indices = st.multiselect("Select VINs to Order", df_view['vin'].tolist())
                        if sel_indices:
                            st.write("Selected Items:")
                            subset = df_view[df_view['vin'].isin(sel_indices)]
                            st.dataframe(subset[['vin','model_name']])
                            
                            with st.form("order_form"):
                                contact = st.text_input("Your Contact Info (Phone/Email)")
                                msg = st.text_area("Message to Sellers")
                                if st.form_submit_button("Submit Order"):
                                    for yard, group in subset.groupby('junkyard'):
                                        summary = ", ".join([f"{r['model_name']} ({r['vin']})" for _, r in group.iterrows()])
                                        db.place_order(st.session_state.user_id, contact, yard, yard, f"{summary} // {msg}")
                                    st.success("Orders placed successfully!")
            else:
                st.info("No vehicles found.")

        # ---------------------
        # 2. Engine Inventory
        # ---------------------
        if st.session_state.user_role != 'partner':
            with main_tabs[1]:
                st.subheader("Engine Search")
                eng_list = st.session_state.get('engines_list', [])
                s_engs = st.multiselect("Engine Code", eng_list)
                
                if st.button(t('search_btn_eng')):
                    db.log_search(s_engs, 'engine')
                    res, tot = db.search_data("All", [], [], s_engs, 1990, 2030, [], "1990-01", "2030-12")
                    st.dataframe(res, use_container_width=True)

            # ---------------------
            # 3. Users / Orders
            # ---------------------
            with main_tabs[2]:
                if st.session_state.user_role == 'admin':
                    st.subheader("👤 User Management")
                    udf = db.fetch_all_users()
                    st.dataframe(udf, use_container_width=True)
                    
                    st.divider()
                    user_list = udf['user_id'].tolist()
                    target_uid = st.selectbox("Select User to Edit", user_list)
                    
                    if target_uid:
                        cur_row = udf[udf['user_id'] == target_uid].iloc[0]
                        cur_role = cur_row['role']
                        cur_email = cur_row['email'] if cur_row['email'] else ""
                        cur_phone = cur_row['phone'] if cur_row['phone'] else ""

                        with st.form("admin_edit_user"):
                            c1, c2, c3 = st.columns(3)
                            n_role = c1.selectbox("Role", ['buyer','partner','admin'], index=['buyer','partner','admin'].index(cur_role))
                            n_email = c2.text_input("Email", value=cur_email)
                            n_phone = c3.text_input("Phone", value=cur_phone)
                            
                            if st.form_submit_button("Update Info"):
                                db.update_user_role(target_uid, n_role)
                                db.update_user_info(target_uid, n_email, n_phone)
                                st.success("Updated!")
                                time.sleep(1)
                                st.rerun()
                        
                        with st.expander("Delete User"):
                            if st.button("Delete Permanently"):
                                db.delete_user(target_uid)
                                st.warning("User Deleted")
                                st.rerun()

                elif st.session_state.user_role == 'buyer':
                    st.subheader(t('my_orders'))
                    odf = db.get_orders(st.session_state.user_id, 'buyer')
                    st.dataframe(odf)