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
            with st.form("up_veh"):
                st.write("Vehicle Data")
                vf = st.file_uploader("", type=['xlsx','csv'], accept_multiple_files=True)
                if st.form_submit_button(t('save_data')):
                    cnt = sum([db.save_vehicle_file(f) for f in vf]) if vf else 0
                    st.success(t('records_saved').format(cnt))
                    db.load_metadata.clear()
            
            with st.form("up_addr"):
                st.write("Address Data")
                af = st.file_uploader("", type=['xlsx','csv'])
                if st.form_submit_button(t('save_addr')):
                    if af: st.success(t('addr_updated').format(db.save_address_file(af)))
                    db.load_metadata.clear()

        if st.button(t('demand_analysis')): 
            st.session_state.mode_demand = True
            st.rerun()

    # Filters
    st.subheader(f"🔍 {t('search_filter')}")
    tab_v, tab_e, tab_y = st.tabs([t('tab_vehicle'), t('tab_engine'), t('tab_yard')])
    
    with tab_v:
        makers = sorted(st.session_state['models_df']['manufacturer'].unique().tolist())
        makers.insert(0, "All")
        s_maker = st.selectbox(t('manufacturer'), makers)
        
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

        f_models = sorted(st.session_state['models_df'][st.session_state['models_df']['manufacturer']==s_maker]['model_name'].unique()) if s_maker != "All" else []
        s_models = st.multiselect(t('model'), f_models)
        
        if st.button(t('search_btn_veh')):
            db.log_search(s_models, 'model')
            res, tot = db.search_data(s_maker, s_models, [], sy, ey, [], sm, em)
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
            udf = db.fetch_all_users()
            st.dataframe(udf)
            with st.form("u_mgmt"):
                uid = st.selectbox("Select User", udf['user_id'].tolist())
                role = st.selectbox("New Role", ['buyer','partner','admin'])
                c1, c2 = st.columns(2)
                if c1.form_submit_button("Update Role"):
                    db.update_user_role(uid, role); st.success("Updated"); st.rerun()
                if c2.form_submit_button("Delete User"):
                    db.delete_user(uid); st.warning("Deleted"); st.rerun()