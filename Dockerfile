# 1. 파이썬 3.10 슬림 버전 사용 (가볍고 안정적)
FROM python:3.10-slim

# 2. 작업 디렉토리 설정
WORKDIR /app

# 3. 필수 패키지 설치 (git, gcc 등 빌드 도구)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

# 4. requirements.txt 복사 및 라이브러리 설치
COPY requirements.txt .
RUN pip3 install -r requirements.txt

# 5. 소스 코드 전체 복사
COPY . .

# 6. Streamlit 포트 개방
EXPOSE 8501

# 7. 헬스체크 (앱이 살아있는지 확인)
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# 8. 실행 명령어 (Secrets는 환경변수로 주입하거나 서버 파일로 관리)
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]