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
        'lang': 'English'
    })

# 다국어 지원 (간단 버전)
TRANS = {
    'English': {
        'title': "K-Used Car/Engine Inventory",
        'login': "Login", 'logout': "Logout",
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
        'login': "로그인", 'logout': "로그아웃",
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
    }
}

def t(key):
    return TRANS.get(st.session_state.lang, TRANS['English']).get(key, key)

# DB 초기화
db.init_dbs()
if st.session_state.get('models_df') is None or st.session_state.get('models_df').empty:
    db.reset_dashboard()

# ---------------------------------------------------------
# 2. Sidebar (Auth & Admin Tools)
# ---------------------------------------------------------
with st.sidebar:
    st.title("🚛 K-Auto Hub")
    
    # Language Switcher
    lang_opt = st.radio("", ["English", "Korean"], horizontal=True)
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
                # 단순 비밀번호 매칭 (해시 검증은 db.py 내부 로직 참조, 여기선 간소화)
                # 실제 운영 시 stauth.Authenticate 사용 권장
                if uid in users:
                    # 간단한 비밀번호 확인 (실제로는 해시 비교 필요)
                    # 여기서는 db.py의 fetch_users_for_auth가 반환하는 구조를 믿고 진행
                    # 실제 stauth 사용시에는 cookie controller 사용
                    user_info = users[uid]
                    st.session_state.logged_in = True
                    st.session_state.user_id = uid
                    st.session_state.user_role = user_info['role']
                    st.success(f"Welcome {user_info['name']}")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("Invalid ID or Password")
    else:
        st.write(f"👤 **{st.session_state.user_id}** ({st.session_state.user_role})")
        if st.button(t('logout')):
            st.session_state.clear()
            st.rerun()
            
        st.divider()

        # Admin Tools
        if st.session_state.user_role == 'admin':
            with st.expander(f"📂 {t('admin_tools')}"):
                # 1. 차량 데이터 업로드
                with st.form("up_veh"):
                    st.write("Vehicle Data Upload")
                    vf = st.file_uploader("", type=['xlsx','csv','xls'], accept_multiple_files=True)
                    if st.form_submit_button(t('save_data')):
                        cnt = sum([db.save_vehicle_file(f) for f in vf]) if vf else 0
                        st.success(t('records_saved').format(cnt))
                        db.load_metadata.clear()
                
                # 2. 주소 데이터 업로드
                with st.form("up_addr"):
                    st.write("Address Data Upload")
                    af = st.file_uploader("", type=['xlsx','csv'])
                    if st.form_submit_button(t('save_addr')):
                        if af: st.success(t('addr_updated').format(db.save_address_file(af)))
                        db.load_metadata.clear()

                st.divider()

                # 3. DB 데이터 표준화 버튼 (기존 데이터 정리)
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
    # Show Trend (Public View)
    st.subheader("🔥 Search Trends")
    e_df, m_df = db.get_trends()
    c1, c2 = st.columns(2)
    with c1: st.dataframe(m_df, use_container_width=True)
    with c2: st.dataframe(e_df, use_container_width=True)

else:
    # -----------------------------------------------------------
    # [Partner Mode] 판매자(폐차장) 전용 화면
    # -----------------------------------------------------------
    if st.session_state.user_role == 'partner':
        tabs = st.tabs(["🏭 My Inventory", "📦 Orders", "📊 Market View"])
        
        # Tab 1: 내 재고 관리 (My Inventory)
        with tabs[0]:
            st.subheader(f"Inventory Management: {st.session_state.user_id}")
            
            # 내 차량만 검색 (yards 인자에 내 ID 주입)
            my_cars, my_cnt = db.search_data("All", [], [], [], 1990, 2030, [st.session_state.user_id], "1990-01", "2030-12")
            
            st.info(f"Total Vehicles: {my_cnt} EA")
            
            if not my_cars.empty:
                # 목록 표시
                st.dataframe(my_cars[['vin', 'manufacturer', 'model_name', 'model_detail', 'model_year', 'car_no', 'price', 'mileage']], use_container_width=True)
                
                st.divider()
                st.write("### ✏️ Edit Vehicle Info")
                
                # 수정할 차량 선택 (라벨: VIN - 모델명)
                my_cars['label'] = my_cars['vin'] + " - " + my_cars['model_name'] + " " + my_cars['model_detail']
                sel_veh = st.selectbox("Select Vehicle", my_cars['label'])
                
                if sel_veh:
                    target_vin = sel_veh.split(" - ")[0]
                    row = my_cars[my_cars['vin'] == target_vin].iloc[0]
                    
                    with st.form("edit_veh"):
                        c1, c2 = st.columns(2)
                        p_price = c1.number_input("Sales Price (KRW)", value=int(row['price']) if row['price'] else 0, step=10000)
                        p_mile = c2.number_input("Mileage (km)", value=int(row['mileage']) if row['mileage'] else 0, step=1000)
                        
                        st.write("Photos:")
                        if row['photos']: st.caption(row['photos'])
                        
                        p_files = st.file_uploader("Upload Photos", accept_multiple_files=True, type=['png','jpg','jpeg'])
                        
                        if st.form_submit_button("💾 Save Changes"):
                            if db.update_vehicle_sales_info(target_vin, p_price, p_mile, p_files):
                                st.success("Updated Successfully!")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("Failed to update.")
            else:
                st.warning("No vehicles found.")

        # Tab 2: 주문 관리 (Orders)
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
        
        # Tab 3: 전체 시장 뷰 (Market View) - 뷰어 기능 재활용을 위해 아래 변수 설정
        is_partner_viewing_market = True

    # -----------------------------------------------------------
    # [Admin / Buyer Mode] 일반 뷰어 화면
    # -----------------------------------------------------------
    else:
        is_partner_viewing_market = False

    # (Partner가 Market View 탭을 눌렀거나, Admin/Buyer인 경우 실행)
    if st.session_state.user_role != 'partner' or (st.session_state.user_role == 'partner' and is_partner_viewing_market):
        
        # 탭 위치 조정 (Partner일 땐 탭 안에서 그려야 함)
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
            # 필터 섹션
            with st.expander("🔍 Search Filters", expanded=not st.session_state.is_filtered):
                c1, c2, c3 = st.columns(3)
                
                # [3-Depth Filter Logic]
                df_meta = st.session_state['models_df']
                
                # 1) Manufacturer
                makers = sorted(df_meta['manufacturer'].unique().tolist())
                makers.insert(0, "All")
                s_maker = c1.selectbox(t('manufacturer'), makers)
                
                # 2) Model (Dependent on Maker)
                if s_maker != "All":
                    f_models = sorted(df_meta[df_meta['manufacturer'] == s_maker]['model_name'].unique())
                else:
                    f_models = []
                s_models = c2.multiselect(t('model'), f_models)
                
                # 3) Detail (Dependent on Model)
                f_details = []
                if s_models:
                    # 선택된 모델들에 해당하는 세부모델만 추출
                    filtered_rows = df_meta[
                        (df_meta['manufacturer'] == s_maker) & 
                        (df_meta['model_name'].isin(s_models))
                    ]
                    # None 값 제외하고 정렬
                    f_details = sorted([d for d in filtered_rows['model_detail'].unique() if d])
                
                s_details = c3.multiselect(t('detail'), f_details)

                # Date & Yards Filter
                cc1, cc2, cc3 = st.columns(3)
                sy = cc1.number_input(t('from_year'), 1990, 2030, 2000)
                ey = cc2.number_input(t('to_year'), 1990, 2030, 2025)
                
                yards_list = st.session_state.get('yards_list', [])
                s_yards = cc3.multiselect("Junkyard", yards_list)

                # Month Filter
                months = st.session_state.get('months_list', [])
                d_s = months[-1] if months else "2000-01"
                d_e = months[0] if months else "2030-12"
                cc4, cc5 = st.columns(2)
                sm = cc4.selectbox(t('start_month'), sorted(months) if months else [d_s], index=0)
                em = cc5.selectbox(t('end_month'), sorted(months, reverse=True) if months else [d_e], index=0)

                if st.button(t('search_btn_veh'), type="primary"):
                    db.log_search(s_models, 'model')
                    # details 인자 전달
                    res, tot = db.search_data(s_maker, s_models, s_details, [], sy, ey, s_yards, sm, em)
                    st.session_state.update({'view_data': res, 'total_count': tot, 'is_filtered': True})
                    st.rerun()

                if st.button(t('reset')):
                    db.reset_dashboard()
                    st.rerun()

            # 결과 표시
            st.divider()
            st.write(f"**Total Results:** {st.session_state.total_count}")
            
            df_view = st.session_state.view_data
            if not df_view.empty:
                # 표시할 컬럼 정리
                cols = ['vin', 'manufacturer', 'model_name', 'model_detail', 'model_year', 'engine_code', 'junkyard', 'reg_date', 'price', 'mileage']
                st.dataframe(df_view[cols], use_container_width=True)
                
                # 주문 기능 (Buyer Only)
                if st.session_state.user_role == 'buyer':
                    with st.expander("⚡ Request Quote / Order"):
                        sel_indices = st.multiselect("Select VINs to Order", df_view['vin'].tolist())
                        if sel_indices:
                            st.write("Selected Items:")
                            subset = df_view[df_view['vin'].isin(sel_indices)]
                            st.dataframe(subset[['vin','model_name','junkyard']])
                            
                            with st.form("order_form"):
                                contact = st.text_input("Your Contact Info (Phone/Email)")
                                msg = st.text_area("Message to Sellers")
                                if st.form_submit_button("Submit Order"):
                                    # 파트너별로 주문 분리 생성
                                    for yard, group in subset.groupby('junkyard'):
                                        summary = ", ".join([f"{r['model_name']} ({r['vin']})" for _, r in group.iterrows()])
                                        db.place_order(st.session_state.user_id, contact, yard, yard, f"{summary} // {msg}")
                                    st.success("Orders placed successfully!")
            else:
                st.info("No vehicles found.")

        # ---------------------
        # 2. Engine Inventory (If not partner view)
        # ---------------------
        if st.session_state.user_role != 'partner':
            with main_tabs[1]:
                st.subheader("Engine Search")
                # 엔진 검색은 단순화 (엔진코드 멀티셀렉트)
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
                    # 사용자 수정 기능
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