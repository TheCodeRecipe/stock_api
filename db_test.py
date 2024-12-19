import psycopg2
from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

try:
    # PostgreSQL 연결 설정
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

    print("✅ PostgreSQL 연결 성공!")

    # 커서 생성 및 간단한 쿼리 실행
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    db_version = cursor.fetchone()
    print("PostgreSQL 버전:", db_version)

    # 연결 종료
    cursor.close()
    conn.close()
except Exception as e:
    print(f"❌ 오류 발생: {e}")
