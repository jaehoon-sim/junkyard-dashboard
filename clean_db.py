import sqlite3
import pandas as pd
import re
import os  # os 모듈 추가

# [수정된 부분] 실행 위치와 상관없이 현재 파일 기준으로 DB 경로를 잡습니다.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INVENTORY_DB = os.path.join(BASE_DIR, 'data', 'inventory.db')

# ---------------------------------------------------------
# 1. 표준화 매핑 규칙 (Dictionary)
# ---------------------------------------------------------
# 브랜드 표준화 (오타 -> 표준명)
BRAND_MAP = {
    '현대': 'Hyundai', '현대자동차': 'Hyundai', 'HYUNDAI': 'Hyundai',
    '기아': 'Kia', '기아자동차': 'Kia', 'KIA': 'Kia',
    '제네시스': 'Genesis', 'GENESIS': 'Genesis',
    '르노삼성': 'Renault Korea', '르노코리아': 'Renault Korea',
    '쉐보레': 'Chevrolet', '지엠대우': 'Chevrolet',
    '쌍용': 'KGM', 'KG모빌리티': 'KGM', 'SsangYong': 'KGM',
    '벤츠': 'Mercedes-Benz', '메르세데스벤츠': 'Mercedes-Benz', 'Benz': 'Mercedes-Benz',
    '비엠더블유': 'BMW', '아우디': 'Audi', '폭스바겐': 'Volkswagen'
}

# 모델명에서 브랜드 제거용 패턴 (예: "벤츠 S클래스" -> "S클래스")
BRAND_REMOVE_REGEX = r"^(현대|기아|제네시스|르노|쉐보레|쌍용|벤츠|메르세데스|비엠|아우디|폭스바겐|HYUNDAI|KIA|GENESIS|BENZ|BMW|AUDI)\s*"

# 주요 모델 매핑 (입력값 -> [표준모델명, 세부모델])
# 3Depth를 위해 세부 모델을 분리합니다.
MODEL_MAP = {
    # Hyundai
    '그랜저': ['Grandeur', ''], '그랜져': ['Grandeur', ''],
    '그랜저HG': ['Grandeur', 'HG'], '그랜저IG': ['Grandeur', 'IG'], '더뉴그랜저': ['Grandeur', 'The New'],
    '쏘나타': ['Sonata', ''], '소나타': ['Sonata', ''],
    '쏘나타DN8': ['Sonata', 'DN8'], 'LF쏘나타': ['Sonata', 'LF'],
    '아반떼': ['Avante', ''], '아반떼CN7': ['Avante', 'CN7'], '아반떼AD': ['Avante', 'AD'],
    '싼타페': ['Santa Fe', ''], '산타페': ['Santa Fe', ''], '싼타페TM': ['Santa Fe', 'TM'],
    '팰리세이드': ['Palisade', ''], '투싼': ['Tucson', ''], '스타렉스': ['Starex', ''], '스타리아': ['Staria', ''],
    
    # Kia
    'K5': ['K5', ''], 'K7': ['K7', ''], 'K8': ['K8', ''], 'K9': ['K9', ''],
    '쏘렌토': ['Sorento', ''], '쏘렌토MQ4': ['Sorento', 'MQ4'],
    '카니발': ['Carnival', ''], '더뉴카니발': ['Carnival', 'The New'], '카니발KA4': ['Carnival', 'KA4'],
    '스포티지': ['Sportage', ''], '모닝': ['Morning', ''], '레이': ['Ray', ''],
    
    # Genesis
    'G80': ['G80', ''], 'G90': ['G90', ''], 'G70': ['G70', ''], 'GV80': ['GV80', ''], 'GV70': ['GV70', ''],
    
    # Mercedes-Benz
    'S클래스': ['S-Class', ''], 'S-Class': ['S-Class', ''], 'S-Klasse': ['S-Class', ''],
    'E클래스': ['E-Class', ''], 'E-Class': ['E-Class', ''],
    'C클래스': ['C-Class', ''], 'C-Class': ['C-Class', ''],
    'GLE': ['GLE', ''], 'GLC': ['GLC', ''], 'GLS': ['GLS', ''],
    
    # BMW
    '5시리즈': ['5 Series', ''], '3시리즈': ['3 Series', ''], '7시리즈': ['7 Series', ''],
    'X5': ['X5', ''], 'X3': ['X3', ''], 'X7': ['X7', ''],
}

def standardize_data():
    conn = sqlite3.connect(INVENTORY_DB)
    c = conn.cursor()

    print("1. DB 구조 변경 중 (model_detail 컬럼 추가)...")
    try:
        c.execute("ALTER TABLE vehicle_data ADD COLUMN model_detail TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        print("   -> 이미 model_detail 컬럼이 존재합니다. 패스.")

    print("2. 데이터 읽어오는 중...")
    df = pd.read_sql("SELECT vin, manufacturer, model_name FROM vehicle_data", conn)
    
    updates = []
    
    for _, row in df.iterrows():
        vin = row['vin']
        raw_mfr = str(row['manufacturer']).strip()
        raw_model = str(row['model_name']).strip()
        
        # [Step 1] 브랜드 표준화
        std_mfr = BRAND_MAP.get(raw_mfr, raw_mfr) # 매핑 없으면 원래 값 유지
        
        # [Step 2] 모델명 정리 (브랜드명이 모델명에 섞여 있으면 제거)
        # 예: "벤츠 S클래스" -> "S클래스"
        clean_model_name = re.sub(BRAND_REMOVE_REGEX, "", raw_model, flags=re.IGNORECASE).strip()
        
        # [Step 3] 모델 & 세부모델 분리
        # 매핑 테이블에 있으면 그 값을 쓰고, 없으면 그냥 모델명만 유지
        if clean_model_name in MODEL_MAP:
            std_model = MODEL_MAP[clean_model_name][0]
            std_detail = MODEL_MAP[clean_model_name][1]
        else:
            # 매핑 테이블에 없는 경우 (자동 추론 로직)
            # 영어+숫자 조합이 뒤에 붙으면 분리 시도 (예: "Sonata DN8" -> "Sonata", "DN8")
            parts = clean_model_name.split()
            if len(parts) >= 2:
                std_model = parts[0]
                std_detail = " ".join(parts[1:])
            else:
                std_model = clean_model_name
                std_detail = ""

        # 영어로 변환이 안 된 한글 브랜드는 영어로 강제 변환 (선택사항)
        if std_mfr == "현대": std_mfr = "Hyundai"
        
        updates.append((std_mfr, std_model, std_detail, vin))

    print(f"3. {len(updates)}건 데이터 업데이트 중...")
    c.executemany("UPDATE vehicle_data SET manufacturer = ?, model_name = ?, model_detail = ? WHERE vin = ?", updates)
    
    # 모델 리스트 테이블도 갱신
    c.execute("DELETE FROM model_list")
    c.execute("INSERT OR IGNORE INTO model_list (manufacturer, model_name) SELECT DISTINCT manufacturer, model_name FROM vehicle_data")
    
    conn.commit()
    conn.close()
    print("✅ 데이터 표준화 완료!")

if __name__ == "__main__":
    standardize_data()