import sqlite3
import pandas as pd

# ---------------------------------------------------------
# 1. 기존 데이터 정의 (app.py에서 추출)
# ---------------------------------------------------------

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

TRANSLATIONS = {
    "English": {
        "app_title": "K-Used Car Global Hub", "login_title": "Login", "id": "ID", "pw": "Password",
        "sign_in": "Sign In", "logout": "Logout", "welcome": "Welcome, {}!", "invalid_cred": "Invalid Credentials",
        "admin_tools": "Admin Tools", "data_upload": "Data Upload", "save_data": "Save Data",
        "addr_db": "Address DB", "save_addr": "Save Address", "reset_db": "Reset DB", "reset_done": "Reset Done",
        "records_saved": "{} records uploaded.", "addr_updated": "{} addresses updated.",
        "admin_menu": "Admin Menu", "demand_analysis": "Global Demand Analysis", "search_filter": "Search Filter",
        "tab_vehicle": "Vehicle", "tab_engine": "Engine", "tab_yard": "Yard", "manufacturer": "Manufacturer",
        "from_year": "From Year", "to_year": "To Year", "model": "Model", "engine_code": "Engine Code",
        "partner_name": "Partner Name", "search_btn_veh": "Search Vehicle", "search_btn_eng": "Search Engine",
        "search_btn_partners": "Search Partner", "reset_filters": "Reset Filters",
        "check_trends": "Check global search trends.", "show_trends": "Show Trends",
        "analysis_title": "Global Demand Trends (Real-time)", "top_engines": "Top Searched Engines",
        "top_models": "Top Searched Models", "main_title": "K-Used Car/Engine Inventory",
        "tab_inventory": "Inventory", "tab_orders": "Orders", "tab_results": "Search Results",
        "tab_my_orders": "My Orders", "no_results": "No results found.",
        "plz_select": "Please select filters from the sidebar to search.", "total_veh": "Total Vehicles",
        "matched_eng": "Matched Engines", "partners_cnt": "Partners", "real_yards": "Real Junkyards",
        "limit_warning": "⚠️ Showing top 5,000 results out of {:,}. Please refine filters.",
        "stock_by_partner": "Stock by Partner", "login_req_warn": "🔒 Login required to request a quote.",
        "selected_msg": "Selected: **{}** ({} EA)", "req_quote_title": "📨 Request Quote to {}",
        "name_company": "Name / Company", "contact": "Contact (Email/Phone) *", "qty": "Quantity *",
        "item": "Item *", "unit_price": "Target Unit Price (USD) *", "message": "Message to Admin",
        "send_btn": "🚀 Send Inquiry", "fill_error": "⚠️ Please fill in all required fields: Contact, Item, and Price.",
        "inquiry_sent": "✅ Inquiry has been sent to our sales team.", "item_list": "Item List",
        "incoming_quotes": "📩 Incoming Quote Requests", "my_quote_req": "🛒 My Quote Requests",
        "no_orders_admin": "No pending orders.", "no_orders_buyer": "You haven't requested any quotes yet.",
        "status_change": "Change Status", "update_btn": "Update", "updated_msg": "Updated!",
        "offer_received": "💬 Offer Received! Check your email/phone."
    },
    "Korean": {
        "app_title": "K-Used Car 글로벌 허브", "login_title": "로그인", "id": "아이디", "pw": "비밀번호",
        "sign_in": "로그인", "logout": "로그아웃", "welcome": "환영합니다, {}님!", "invalid_cred": "로그인 정보가 올바르지 않습니다.",
        "admin_tools": "관리자 도구", "data_upload": "데이터 업로드", "save_data": "데이터 저장",
        "addr_db": "주소 DB", "save_addr": "주소 저장", "reset_db": "DB 초기화", "reset_done": "초기화 완료",
        "records_saved": "{}건 저장 완료.", "addr_updated": "{}곳 주소 업데이트 완료.", "admin_menu": "관리자 메뉴",
        "demand_analysis": "글로벌 수요 분석", "search_filter": "검색 필터", "tab_vehicle": "차량",
        "tab_engine": "엔진", "tab_yard": "업체", "manufacturer": "제조사", "from_year": "시작 연식",
        "to_year": "종료 연식", "model": "모델명", "engine_code": "엔진코드", "partner_name": "파트너명",
        "search_btn_veh": "차량 검색", "search_btn_eng": "엔진 검색", "search_btn_partners": "파트너 검색",
        "reset_filters": "필터 초기화", "check_trends": "글로벌 검색 트렌드 확인", "show_trends": "트렌드 보기",
        "analysis_title": "글로벌 실시간 수요 분석", "top_engines": "인기 검색 엔진", "top_models": "인기 검색 차종",
        "main_title": "K-Used Car/Engine 재고 현황", "tab_inventory": "재고 조회", "tab_orders": "주문 관리",
        "tab_results": "검색 결과", "tab_my_orders": "내 주문 내역", "no_results": "검색 결과가 없습니다.",
        "plz_select": "사이드바에서 필터를 선택하여 검색하세요.", "total_veh": "총 차량", "matched_eng": "매칭 엔진",
        "partners_cnt": "파트너 수", "real_yards": "실제 폐차장",
        "limit_warning": "⚠️ 총 {:,}건 중 상위 5,000건만 표시됩니다. 필터를 상세 조정하세요.", "stock_by_partner": "업체별 보유 현황",
        "login_req_warn": "🔒 견적 요청을 위해 로그인이 필요합니다.", "selected_msg": "선택됨: **{}** ({} 개)",
        "req_quote_title": "📨 {}에 견적 요청", "name_company": "이름 / 회사명", "contact": "연락처 (이메일/전화) *",
        "qty": "요청 수량 *", "item": "품목 *", "unit_price": "희망 단가 (USD) *", "message": "메시지",
        "send_btn": "🚀 견적 요청 전송", "fill_error": "⚠️ 필수 입력 항목(연락처, 품목, 단가)을 입력해주세요.",
        "inquiry_sent": "✅ 영업팀으로 견적 요청이 전송되었습니다.", "item_list": "상세 목록",
        "incoming_quotes": "📩 접수된 견적 요청", "my_quote_req": "🛒 나의 견적 요청 내역",
        "no_orders_admin": "대기 중인 주문이 없습니다.", "no_orders_buyer": "아직 요청한 내역이 없습니다.",
        "status_change": "상태 변경", "update_btn": "업데이트", "updated_msg": "업데이트 완료!",
        "offer_received": "💬 견적 도착! 이메일/전화를 확인하세요."
    },
    "Russian": {
        "app_title": "K-Used Car Глобальный Хаб", "login_title": "Вход", "id": "ID", "pw": "Пароль",
        "sign_in": "Войти", "logout": "Выйти", "welcome": "Добро пожаловать, {}!", "invalid_cred": "Неверные учетные данные",
        "admin_tools": "Инструменты админа", "data_upload": "Загрузка данных", "save_data": "Сохранить данные",
        "addr_db": "БД Адресов", "save_addr": "Сохранить адрес", "reset_db": "Сброс БД", "reset_done": "Сброс выполнен",
        "records_saved": "{} записей загружено.", "addr_updated": "{} адресов обновлено.", "admin_menu": "Меню админа",
        "demand_analysis": "Анализ спроса", "search_filter": "Фильтр поиска", "tab_vehicle": "Автомобиль",
        "tab_engine": "Двигатель", "tab_yard": "Склад", "manufacturer": "Производитель", "from_year": "С года",
        "to_year": "По год", "model": "Модель", "engine_code": "Код двигателя", "partner_name": "Партнер",
        "search_btn_veh": "Поиск авто", "search_btn_eng": "Поиск двигателя", "search_btn_partners": "Поиск партнера",
        "reset_filters": "Сброс фильтров", "check_trends": "Глобальные тренды поиска", "show_trends": "Показать тренды",
        "analysis_title": "Анализ спроса в реальном времени", "top_engines": "Топ двигателей",
        "top_models": "Топ моделей", "main_title": "Инвентарь K-Used Car/Engine", "tab_inventory": "Инвентарь",
        "tab_orders": "Заказы", "tab_results": "Результаты", "tab_my_orders": "Мои заказы",
        "no_results": "Результатов не найдено.", "plz_select": "Выберите фильтры для поиска.",
        "total_veh": "Всего авто", "matched_eng": "Двигатели", "partners_cnt": "Партнеры", "real_yards": "Склады",
        "limit_warning": "⚠️ Показано топ 5,000 из {:,}. Уточните фильтры.", "stock_by_partner": "Наличие по партнерам",
        "login_req_warn": "🔒 Требуется вход для запроса цены.", "selected_msg": "Выбрано: **{}** ({} шт.)",
        "req_quote_title": "📨 Запрос цены у {}", "name_company": "Имя / Компания", "contact": "Контакт (Email/Тел) *",
        "qty": "Количество *", "item": "Товар *", "unit_price": "Целевая цена (USD) *", "message": "Сообщение админу",
        "send_btn": "🚀 Отправить запрос", "fill_error": "⚠️ Заполните обязательные поля: Контакт, Товар, Цена.",
        "inquiry_sent": "✅ Запрос отправлен в отдел продаж.", "item_list": "Список товаров",
        "incoming_quotes": "📩 Входящие запросы", "my_quote_req": "🛒 Мои запросы",
        "no_orders_admin": "Нет ожидающих заказов.", "no_orders_buyer": "Вы еще не делали запросов.",
        "status_change": "Изменить статус", "update_btn": "Обновить", "updated_msg": "Обновлено!",
        "offer_received": "💬 Предложение получено! Проверьте почту."
    },
    "Arabic": {
        "app_title": "K-Used Car Global Hub", "login_title": "تسجيل الدخول", "id": "المعرف", "pw": "كلمة المرور",
        "sign_in": "دخول", "logout": "خروج", "welcome": "مرحباً، {}!", "invalid_cred": "بيانات الاعتماد غير صالحة",
        "admin_tools": "أدوات المسؤول", "data_upload": "تحميل البيانات", "save_data": "حفظ البيانات",
        "addr_db": "قاعدة بيانات العناوين", "save_addr": "حفظ العنوان", "reset_db": "إعادة تعيين قاعدة البيانات",
        "reset_done": "تمت إعادة التعيين", "records_saved": "تم تحميل {} سجل.", "addr_updated": "تم تحديث {} عنوان.",
        "admin_menu": "قائمة المسؤول", "demand_analysis": "تحليل الطلب العالمي", "search_filter": "عامل تصفية البحث",
        "tab_vehicle": "مركبة", "tab_engine": "محرك", "tab_yard": "ساحة", "manufacturer": "الصانع",
        "from_year": "من سنة", "to_year": "إلى سنة", "model": "الموديل", "engine_code": "رمز المحرك",
        "partner_name": "اسم الشريك", "search_btn_veh": "بحث عن مركبة", "search_btn_eng": "بحث عن محرك",
        "search_btn_partners": "بحث عن شريك", "reset_filters": "إعادة تعيين المرشحات",
        "check_trends": "تحقق من اتجاهات البحث العالمية.", "show_trends": "عرض الاتجاهات",
        "analysis_title": "اتجاهات الطلب العالمي (مباشر)", "top_engines": "أفضل المحركات بحثًا",
        "top_models": "أفضل الموديلات بحثًا", "main_title": "مخزون السيارات/المحركات المستعملة الكورية",
        "tab_inventory": "المخزون", "tab_orders": "الطلبات", "tab_results": "نتائج البحث",
        "tab_my_orders": "طلباتي", "no_results": "لم يتم العثور على نتائج.", "plz_select": "يرجى تحديد مرشحات للبحث.",
        "total_veh": "إجمالي المركبات", "matched_eng": "المحركات المطابقة", "partners_cnt": "الشركاء",
        "real_yards": "ساحات الخردة الحقيقية", "limit_warning": "⚠️ يتم عرض أعلى 5000 نتيجة من {:,}. يرجى تحسين المرشحات.",
        "stock_by_partner": "المخزون حسب الشريك", "login_req_warn": "🔒 تسجيل الدخول مطلوب لطلب عرض أسعار.",
        "selected_msg": "محدد: **{}** ({} قطعة)", "req_quote_title": "📨 طلب عرض أسعار لـ {}",
        "name_company": "الاسم / الشركة", "contact": "الاتصال (بريد إلكتروني/هاتف) *", "qty": "الكمية *",
        "item": "العنصر *", "unit_price": "السعر المستهدف (دولار) *", "message": "رسالة للمسؤول",
        "send_btn": "🚀 إرسال الطلب", "fill_error": "⚠️ يرجى ملء الحقول المطلوبة: جهة الاتصال، العنصر، والسعر.",
        "inquiry_sent": "✅ تم إرسال الطلب إلى فريق المبيعات لدينا.", "item_list": "قائمة العناصر",
        "incoming_quotes": "📩 طلبات الأسعار الواردة", "my_quote_req": "🛒 طلبات الأسعار الخاصة بي",
        "no_orders_admin": "لا توجد طلبات معلقة.", "no_orders_buyer": "لم تقم بطلب أي عروض أسعار بعد.",
        "status_change": "تغيير الحالة", "update_btn": "تحديث", "updated_msg": "تم التحديث!",
        "offer_received": "💬 تم استلام العرض! تحقق من بريدك الإلكتروني/هاتفك."
    }
}

# ---------------------------------------------------------
# 2. DB 생성 및 데이터 이관
# ---------------------------------------------------------
conn = sqlite3.connect('dictionary.db')
c = conn.cursor()

# Province Table
c.execute("CREATE TABLE IF NOT EXISTS provinces (kr TEXT PRIMARY KEY, en TEXT)")
for k, v in PROVINCE_MAP.items():
    c.execute("INSERT OR REPLACE INTO provinces (kr, en) VALUES (?, ?)", (k, v))

# City Table
c.execute("CREATE TABLE IF NOT EXISTS cities (kr TEXT PRIMARY KEY, en TEXT)")
for k, v in CITY_MAP.items():
    c.execute("INSERT OR REPLACE INTO cities (kr, en) VALUES (?, ?)", (k, v))

# Translation Table (Flattened for easier query)
# Structure: key, English, Korean, Russian, Arabic
c.execute('''CREATE TABLE IF NOT EXISTS translations (
    key TEXT PRIMARY KEY,
    English TEXT,
    Korean TEXT,
    Russian TEXT,
    Arabic TEXT
)''')

# Flatten TRANSLATIONS dictionary
keys = TRANSLATIONS['English'].keys()
for key in keys:
    en = TRANSLATIONS['English'].get(key, key)
    kr = TRANSLATIONS['Korean'].get(key, key)
    ru = TRANSLATIONS['Russian'].get(key, key)
    ar = TRANSLATIONS['Arabic'].get(key, key)
    c.execute("INSERT OR REPLACE INTO translations (key, English, Korean, Russian, Arabic) VALUES (?, ?, ?, ?, ?)", (key, en, kr, ru, ar))

conn.commit()
conn.close()

print("✅ dictionary.db created successfully with all data!")
