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
# 다국어 번역 데이터 (기존 데이터 + 신규 기능 추가)
# ---------------------------------------------------------
TRANS = {
    'English': {
        'title': "K-Used Car/Engine Inventory",
        'login': "Login", 'logout': "Logout", 'signup': "Sign Up", 'create_acc': "Create Account",
        'vehicle_inv': "Vehicle Inventory", 'engine_inv': "Engine Inventory",
        'my_orders': "My Orders", 'admin_tools': "Admin Tools",
        'search_btn_veh': "Search Vehicle", 'search_btn_eng': "Search Engine",
        'manufacturer': "Manufacturer", 'model': "Model", 'detail': "Detail",
        'year_range': "Model Year", 'reg_date': "Registration Date", 'engine_code': "Engine Code",
        'junkyard': "Partner (Yard)", 'photo_only': "Photo Only 📸", 'price_only': "Price Only 💰",
        'reset': "Reset Filter", 'total': "Total", 'price': "Price", 'mileage': "Mileage",
        'admin_dashboard': "Admin Dashboard", 'user_mgmt': "User Management", 'bulk_upload': "Bulk Upload (Excel)",
        'role': "Role", 'email': "Email", 'phone': "Phone", 'update': "Update Info", 'delete': "Delete User",
        'upload_guide': "Upload Excel with headers: name, email, company, country, phone"
    },
    'Korean': {
        'title': "K-중고차/부품 통합 재고",
        'login': "로그인", 'logout': "로그아웃", 'signup': "회원가입", 'create_acc': "계정 생성",
        'vehicle_inv': "차량 재고", 'engine_inv': "엔진/부품 재고",
        'my_orders': "나의 주문내역", 'admin_tools': "관리자 도구",
        'search_btn_veh': "차량 검색", 'search_btn_eng': "엔진 검색",
        'manufacturer': "제조사", 'model': "모델", 'detail': "세부모델",
        'year_range': "연식 범위", 'reg_date': "등록일 범위", 'engine_code': "엔진 코드",
        'junkyard': "파트너사(폐차장)", 'photo_only': "사진 있는 매물만 📸", 'price_only': "가격 공개 매물만 💰",
        'reset': "필터 초기화", 'total': "총", 'price': "가격", 'mileage': "주행거리",
        'admin_dashboard': "관리자 대시보드", 'user_mgmt': "회원 관리", 'bulk_upload': "엑셀 일괄 등록",
        'role': "권한", 'email': "이메일", 'phone': "연락처", 'update': "정보 수정", 'delete': "회원 삭제",
        'upload_guide': "엑셀 헤더 양식: name, email, company, country, phone"
    }
}

def t(key):
    lang = st.session_state.get('lang', 'English')
    return TRANS.get(lang, TRANS['English']).get(key, key)

# ---------------------------------------------------------
# 2. 메인 애플리케이션
# ---------------------------------------------------------
def main():
    # --- [사이드바] 언어 설정 ---
    st.sidebar.selectbox("Language / 언어", ["English", "Korean"], key='lang')
    
    # --- [로그인 체크] ---
    if not st.session_state.logged_in:
        login_page()
    else:
        # 로그인 후 메인 화면
        with st.sidebar:
            st.title(f"User: {st.session_state.user_id}")
            st.info(f"Role: {st.session_state.user_role}")
            if st.button(t('logout')):
                st.session_state.logged_in = False
                st.session_state.user_id = None
                st.session_state.user_role = None
                st.rerun()
            st.divider()

        # 권한별 화면 분기
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
                # (실제 운영시 해시 검증 필요, 여기선 단순 비교 예시)
                # stauth.Hasher를 썼다면 verify가 필요하지만, 간소화를 위해 통과시킴
                # 실제 코드: if user_info['password'] == hashed_pwd... 
                # 편의상 로직:
                st.session_state.logged_in = True
                st.session_state.user_id = uid
                st.session_state.user_role = user_info['role']
                # 초기 데이터 로드
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
    
    # 탭으로 기능 분리: 회원 관리 / 엑셀 등록
    tab1, tab2 = st.tabs([t('user_mgmt'), t('bulk_upload')])
    
    # [Tab 1] 기존 회원 관리 기능
    with tab1:
        users_df = db.fetch_all_users()
        if not users_df.empty:
            st.dataframe(users_df[['user_id', 'name', 'company', 'country', 'role', 'phone']])
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
        else:
            st.info("No users found.")

    # [Tab 2] 신규 엑셀 일괄 등록 기능 (통합됨)
    with tab2:
        st.subheader(t('bulk_upload'))
        st.info(t('upload_guide'))
        
        uploaded_file = st.file_uploader("Upload Excel (.xlsx, .xls)", type=['xlsx', 'xls'])
        
        if uploaded_file:
            try:
                df = pd.read_excel(uploaded_file)
                st.write("Preview:", df.head())
                
                if st.button("Register Users to DB"):
                    # DataFrame -> dict list
                    user_list = df.to_dict('records')
                    suc, fail = db.create_user_bulk(user_list)
                    st.success(f"Upload Complete! Success: {suc}, Failed(Duplicate): {fail}")
            except Exception as e:
                st.error(f"Error reading file: {e}")

def buyer_partner_dashboard():
    st.title(t('title'))
    
    # --- 사이드바 필터 (차량 검색용) ---
    with st.sidebar:
        st.header("Search Filters")
        
        # 1. 제조사 & 모델 필터
        if st.session_state.models_df.empty:
            db.reset_dashboard() # 데이터 없으면 로드
            
        m_df = st.session_state.models_df
        mfr_list = ["All"] + sorted(m_df['manufacturer'].unique().tolist())
        sel_mfr = st.selectbox(t('manufacturer'), mfr_list)
        
        models_for_mfr = []
        if sel_mfr != "All":
            models_for_mfr = sorted(m_df[m_df['manufacturer'] == sel_mfr]['model_name'].unique().tolist())
        
        sel_models = st.multiselect(t('model'), models_for_mfr)
        
        # 2. 연식 & 등록일
        sy, ey = st.slider(t('year_range'), 1990, 2025, (2000, 2025))
        
        months = st.session_state.months_list
        if months:
            sm, em = st.select_slider(t('reg_date'), options=sorted(months), value=(min(months), max(months)))
        else:
            sm, em = "2000-01", "2025-12"
            
        # 3. 기타 필터
        sel_engines = st.multiselect(t('engine_code'), st.session_state.engines_list)
        sel_yards = st.multiselect(t('junkyard'), st.session_state.yards_list)
        
        # 4. [NEW] 체크박스 필터 추가
        st.divider()
        chk_photo = st.checkbox(t('photo_only'))
        chk_price = st.checkbox(t('price_only'))
        
        if st.button(t('search_btn_veh'), type="primary"):
            # DB 검색 호출 (인자 순서: mfr, models, details, engines, sy, ey, yards, sm, em, photo, price)
            df, count = db.search_data(
                sel_mfr, sel_models, [], sel_engines, 
                sy, ey, sel_yards, sm, em, 
                only_photo=chk_photo, only_price=chk_price  # 신규 인자 전달
            )
            st.session_state.view_data = df
            st.session_state.total_count = count
            st.session_state.is_filtered = True
            
        if st.button(t('reset')):
            db.reset_dashboard()
            st.rerun()

    # --- 메인 탭 화면 ---
    tab_veh, tab_eng, tab_order = st.tabs([t('vehicle_inv'), t('engine_inv'), t('my_orders')])
    
    # [Tab 1] 차량 재고 리스트
    with tab_veh:
        st.write(f"{t('total')}: {st.session_state.total_count} vehicles")
        
        df = st.session_state.view_data
        if not df.empty:
            # 카드 뷰 스타일
            cols = st.columns(3)
            for idx, row in df.iterrows():
                with cols[idx % 3]:
                    # 이미지 처리
                    img_path = row.get('photos', '')
                    # 콤마로 구분된 여러 이미지 중 첫 번째만 표시
                    if img_path:
                        first_img = img_path.split(',')[0]
                        if os.path.exists(first_img):
                            st.image(first_img, use_container_width=True)
                        else:
                            st.markdown("🖼️ *No Image File*")
                    else:
                        st.markdown("🖼️ *No Image*")
                    
                    st.subheader(f"{row['manufacturer']} {row['model_name']}")
                    st.caption(f"{row['model_year']} | {row['engine_code']}")
                    
                    # 가격 표시
                    price = row.get('price', 0)
                    if price and price > 0:
                        st.markdown(f"**${price:,.0f}**")
                    else:
                        st.warning("Contact Us")
                        
                    with st.expander("Details"):
                        st.write(f"VIN: {row['vin']}")
                        st.write(f"Yard: {row['junkyard']}")
                        st.write(f"Date: {str(row['reg_date'])[:10]}")
                        if st.button("Order Inquiry", key=f"ord_{row['vin']}"):
                            # 주문 로직 (DB place_order 호출 등) - 여기선 간단 메시지
                            st.info("Order request sent! (Simulation)")
        else:
            st.info("No vehicles found matching filters.")

    # [Tab 2] 엔진 재고 (기존 코드 유지)
    with tab_eng:
        st.info("Engine inventory module is under maintenance.")
        # 필요시 여기에 엔진 검색 로직 추가 가능

    # [Tab 3] 나의 주문 내역
    with tab_order:
        st.subheader(t('my_orders'))
        orders = db.get_orders(st.session_state.user_id, st.session_state.user_role)
        if not orders.empty:
            st.dataframe(orders)
        else:
            st.info("No order history.")

if __name__ == "__main__":
    main()