import streamlit as st
import pandas as pd
import datetime
import time
import json
import base64
import plotly.express as px
import streamlit_authenticator as stauth
import modules.constants as const
import modules.db as db
import modules.utils as utils

# 1. 설정
st.set_page_config(page_title="K-Used Car Global Hub", layout="wide", initial_sidebar_state="expanded")
st.markdown("""<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}</style>""", unsafe_allow_html=True)

# 2. 초기화
if 'db_init' not in st.session_state:
    db.init_dbs()
    st.session_state.db_init = True

if 'language' not in st.session_state: st.session_state.language = 'English'

# 번역 Helper
def t(key):
    translations = db.load_translations()
    lang_dict = translations.get(st.session_state.language, translations.get('English', {}))
    return lang_dict.get(key, key)

# 3. 인증
users = db.fetch_users_for_auth()
authenticator = stauth.Authenticate(users, 'k_used_car_cookie', 'secret_key', 30)

# 4. 데이터 로드
if 'view_data' not in st.session_state:
    m_df, m_eng, m_yards, m_mon, init_df, init_total = db.load_metadata()
    st.session_state.update({'view_data': init_df, 'total_count': init_total, 'models_df': m_df, 
                             'engines_list': m_eng, 'yards_list': m_yards, 'months_list': m_mon,
                             'is_filtered': False, 'mode_demand': False})

# ---------------------------------------------------------
# Sidebar
# ---------------------------------------------------------
with st.sidebar:
    st.title(t('app_title'))
    lang = st.selectbox("Language", ["English", "Korean", "Russian", "Arabic"])
    if lang != st.session_state.language:
        st.session_state.language = lang
        st.rerun()
    
    st.divider()
    authenticator.login()

    if st.session_state["authentication_status"]:
        user = st.session_state["username"]
        role = users['usernames'][user]['role']
        st.session_state.user_role = role
        st.success(t('welcome').format(user))
        authenticator.logout(t('logout'), 'sidebar')
        
    elif st.session_state["authentication_status"] is False:
        st.error(t('invalid_cred'))
        st.session_state.user_role = 'guest'
    else:
        st.session_state.user_role = 'guest'
        with st.expander(f"📝 {t('sign_up')}"):
            with st.form("signup"):
                nid = st.text_input(f"👤 {t('id')}")
                npw = st.text_input(f"🔒 {t('pw')}", type="password")
                nnm = st.text_input(f"📛 {t('user_name')}")
                ncp = st.text_input(f"🏢 {t('company_name')}")
                nct = st.selectbox(f"🌍 {t('country')}", const.COUNTRY_LIST)
                nem = st.text_input(f"📧 {t('email')}")
                nph = st.text_input(f"📞 {t('phone')}")
                if st.form_submit_button(t('sign_up')):
                    if db.create_user(nid, npw, nnm, ncp, nct, nem, nph): st.success(t('signup_success'))
                    else: st.error(t('user_exists'))

    st.divider()
    
# Admin Tools
    if st.session_state.user_role == 'admin':
        with st.expander(f"📂 {t('admin_tools')}"):
            # 1. 차량 데이터 업로드 (기존 코드)
            with st.form("up_veh"):
                st.write("Vehicle Data Upload")
                vf = st.file_uploader("", type=['xlsx','csv','xls'], accept_multiple_files=True)
                if st.form_submit_button(t('save_data')):
                    cnt = sum([db.save_vehicle_file(f) for f in vf]) if vf else 0
                    st.success(t('records_saved').format(cnt))
                    db.load_metadata.clear() # 캐시 초기화
            
            # 2. 주소 데이터 업로드 (기존 코드)
            with st.form("up_addr"):
                st.write("Address Data Upload")
                af = st.file_uploader("", type=['xlsx','csv'])
                if st.form_submit_button(t('save_addr')):
                    if af: st.success(t('addr_updated').format(db.save_address_file(af)))
                    db.load_metadata.clear()

            st.divider()

            # [새로 추가된 기능] 3. DB 데이터 표준화 버튼
            st.write("🔧 **Data Maintenance**")
            if st.button("Normalize & Clean DB (기존 데이터 정리)"):
                with st.spinner("Standardizing database..."):
                    success, msg = db.standardize_existing_data()
                    if success:
                        st.success(f"✅ Database Normalized! Processed {msg} records.")
                        db.load_metadata.clear() # 캐시 초기화
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"Error: {msg}")
    # Filters
    st.subheader(f"🔍 {t('search_filter')}")
    tab_v, tab_e, tab_y = st.tabs([t('tab_vehicle'), t('tab_engine'), t('tab_yard')])
    
# app.py 내 with tab_v: 부분 교체

    with tab_v:
        # 1. Manufacturer (제조사) 선택
        # models_df에는 이제 [manufacturer, model_name, model_detail] 3개 컬럼이 있습니다.
        df_meta = st.session_state['models_df']
        
        makers = sorted(df_meta['manufacturer'].unique().tolist())
        makers.insert(0, "All")
        s_maker = st.selectbox(t('manufacturer'), makers)
        
        # 2. Model (대표 모델) 선택 - 제조사 선택에 종속
        if s_maker != "All":
            # 선택된 제조사의 모델명만 필터링
            f_models = sorted(df_meta[df_meta['manufacturer'] == s_maker]['model_name'].unique())
        else:
            f_models = []
            
        s_models = st.multiselect(t('model'), f_models)
        
        # 3. Detail (세부 모델) 선택 - 모델 선택에 종속 [신규 기능]
        f_details = []
        if s_models:
            # 선택된 제조사 및 모델에 해당하는 세부 모델만 필터링
            # (예: Benz -> E-Class 선택 시 -> E220, E300 등 표시)
            filtered_rows = df_meta[
                (df_meta['manufacturer'] == s_maker) & 
                (df_meta['model_name'].isin(s_models))
            ]
            # None이나 빈 문자열도 필터에 표시하여 선택할 수 있게 함 (상세 모델 없는 차량 검색용)
            f_details = sorted([d for d in filtered_rows['model_detail'].unique() if d is not None])
        
        s_details = st.multiselect("Detailed Model", f_details)

        # 연식 및 기간 필터
        c1, c2 = st.columns(2)
        sy = c1.number_input(t('from_year'), 2000, 2030, 2000)
        ey = c2.number_input(t('to_year'), 2000, 2030, 2025)
        
        st.caption(t('period'))
        months = st.session_state.get('months_list', [])
        d_s = months[-1] if months else "2000-01"
        d_e = months[0] if months else "2030-12"
        c3, c4 = st.columns(2)
        sm = c3.selectbox(t('start_month'), sorted(months) if months else [d_s], index=0)
        em = c4.selectbox(t('end_month'), sorted(months, reverse=True) if months else [d_e], index=0)

        # 검색 버튼
        if st.button(t('search_btn_veh')):
            db.log_search(s_models, 'model')
            # [수정] search_data 호출 시 s_details 인자 추가
            res, tot = db.search_data(s_maker, s_models, s_details, [], sy, ey, [], sm, em)
            st.session_state.update({'view_data': res, 'total_count': tot, 'is_filtered': True, 'mode_demand': False})
            st.rerun()

    with tab_e:
        s_eng = st.multiselect(t('engine_code'), sorted(st.session_state['engines_list']))
        if st.button(t('search_btn_eng')):
            db.log_search(s_eng, 'engine')
            res, tot = db.search_data(None, [], s_eng, 2000, 2030, [], "1990-01", "2099-12")
            st.session_state.update({'view_data': res, 'total_count': tot, 'is_filtered': True, 'mode_demand': False})
            st.rerun()

    with tab_y:
        y_opts = sorted(st.session_state['yards_list'])
        s_yard = st.multiselect(t('partner_name'), y_opts)
        if st.button(t('search_btn_partners')):
            res, tot = db.search_data(None, [], [], 2000, 2030, s_yard, "1990-01", "2099-12")
            st.session_state.update({'view_data': res, 'total_count': tot, 'is_filtered': True, 'mode_demand': False})
            st.rerun()

    if st.button(t('reset_filters')):
        db.reset_dashboard()
        st.rerun()

# ---------------------------------------------------------
# Main Content
# ---------------------------------------------------------
if st.session_state.mode_demand and st.session_state.user_role == 'admin':
    st.title(f"📈 {t('analysis_title')}")
    e_trend, m_trend = db.get_trends()
    c1, c2 = st.columns(2)
    with c1: st.plotly_chart(px.bar(e_trend, x='count', y='keyword', orientation='h'), use_container_width=True)
    with c2: st.plotly_chart(px.bar(m_trend, x='count', y='keyword', orientation='h'), use_container_width=True)

else:
    st.title(t('main_title'))
    df_disp = utils.mask_dataframe(st.session_state['view_data'], st.session_state.user_role, st.session_state.language)
    
    tabs = [t('tab_inventory')]
    if st.session_state.user_role == 'admin': tabs.append(t('tab_orders')); tabs.append("Users")
    elif st.session_state.user_role == 'partner': tabs.append("My Orders")
    else: tabs.append(t('tab_my_orders'))
    
    main_tabs = st.tabs(tabs)

    # 1. Inventory
    with main_tabs[0]:
        c1, c2, c3 = st.columns(3)
        c1.metric(t('total_veh'), f"{st.session_state['total_count']:,}")
        c2.metric(t('matched_eng'), f"{df_disp['engine_code'].nunique() if not df_disp.empty else 0}")
        c3.metric(t('partners_cnt'), f"{df_disp['junkyard'].nunique() if not df_disp.empty else 0}")
        
        st.divider()
        st.subheader(t('stock_by_partner'))
        if not df_disp.empty:
            grp = df_disp.groupby(['junkyard', 'address']).size().reset_index(name='qty').sort_values('qty', ascending=False)
            sel = st.dataframe(grp, use_container_width=True, selection_mode="single-row", on_select="rerun")
            
            if len(sel.selection.rows) > 0:
                row = grp.iloc[sel.selection.rows[0]]
                target = row['junkyard']
                
                if st.session_state.user_role == 'guest': st.warning(t('login_req_warn'))
                else:
                    with st.form("req"):
                        st.write(f"Request Quote to **{target}**")
                        item = st.text_input(t('item'))
                        qty = st.number_input(t('qty'), 1, 999, 1)
                        msg = st.text_area(t('message'))
                        if st.form_submit_button(t('send_btn')):
                            # 실제 이름 찾기 (Buyer인 경우 Alias 복원 로직 필요하지만 생략, 표시된 이름 저장)
                            db.place_order(st.session_state.username, "Contact Info", target, target, f"{item} ({qty}) - {msg}")
                            st.success(t('inquiry_sent'))
        st.dataframe(df_disp, use_container_width=True)

    # 2. Orders
    with main_tabs[1]:
        orders = db.get_orders(st.session_state.username, st.session_state.user_role)
        if not orders.empty:
            for _, row in orders.iterrows():
                with st.expander(f"[{row['status']}] {row['created_at']} | {row['buyer_id']}"):
                    st.write(f"**Item:** {row['items_summary']}")
                    if row['reply_text']: st.info(f"Reply: {row['reply_text']}")
                    
                    if st.session_state.user_role in ['admin', 'partner']:
                        with st.form(f"rep_{row['id']}"):
                            reply = st.text_area("Reply")
                            stat = st.selectbox("Status", ['PENDING','QUOTED','SHIPPING','DONE'], index=0)
                            if st.form_submit_button("Update"):
                                db.update_order(row['id'], stat, reply)
                                utils.send_email(row['contact_info'], "Update", reply)
                                st.rerun()
        else: st.info(t('no_results'))

# 3. Users (Admin Only)
    if st.session_state.user_role == 'admin':
        with main_tabs[2]:
            st.subheader("👤 User Management")
            
            # 최신 사용자 데이터 로드
            udf = db.fetch_all_users()
            st.dataframe(udf, use_container_width=True)
            
            st.divider()
            
            # [Step 1] 수정할 사용자 선택 (폼 외부에서 선택해야 즉시 데이터가 로드됨)
            user_list = udf['user_id'].tolist()
            target_uid = st.selectbox("Select User to Edit", user_list)
            
            # 선택된 사용자의 현재 정보 가져오기
            if target_uid:
                current_row = udf[udf['user_id'] == target_uid].iloc[0]
                cur_role = current_row['role']
                # None 값을 빈 문자열로 처리
                cur_email = current_row['email'] if current_row['email'] else ""
                cur_phone = current_row['phone'] if current_row['phone'] else ""
                cur_company = current_row['company'] if current_row['company'] else ""

                # [Step 2] 정보 수정 폼
                with st.form("admin_update_user"):
                    st.write(f"**Edit Info: {target_uid}**")
                    
                    c1, c2, c3 = st.columns(3)
                    new_role = c1.selectbox("Role", ['buyer', 'partner', 'admin'], index=['buyer', 'partner', 'admin'].index(cur_role))
                    new_email = c2.text_input("Email", value=cur_email)
                    new_phone = c3.text_input("Phone", value=cur_phone)
                    
                    # (선택) 회사명도 수정하고 싶다면 아래 주석 해제
                    # new_company = st.text_input("Company", value=cur_company)

                    c_btn1, c_btn2 = st.columns([1, 4])
                    
                    # 업데이트 버튼
                    if c_btn1.form_submit_button("💾 Update Info"):
                        # 1. 권한 업데이트
                        db.update_user_role(target_uid, new_role)
                        # 2. 정보(이메일/폰) 업데이트
                        db.update_user_info(target_uid, new_email, new_phone)
                        
                        st.success(f"User '{target_uid}' updated successfully!")
                        time.sleep(1)
                        st.rerun()

                # [Step 3] 사용자 삭제 (별도 버튼으로 분리하여 안전성 확보)
                with st.expander(f"🗑️ Delete User '{target_uid}'"):
                    st.warning("This action cannot be undone.")
                    if st.button("Delete User Permanently"):
                        db.delete_user(target_uid)
                        st.error(f"User '{target_uid}' deleted.")
                        time.sleep(1)
                        st.rerun()