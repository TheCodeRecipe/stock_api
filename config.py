import os
from dotenv import load_dotenv

# .env 파일 불러오기
load_dotenv()

# PostgreSQL 환경 변수 가져오기
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
