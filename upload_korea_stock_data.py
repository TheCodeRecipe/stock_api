import psycopg2
import pandas as pd
from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
from datetime import datetime

# DB 연결 설정
def connect_to_db():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        print("PostgreSQL 연결 성공!")
        return conn
    except Exception as e:
        print("PostgreSQL 연결 실패:", e)
        return None

# 데이터 삽입 함수
def upload_data_to_db(conn, csv_file):
    try:
        # CSV 파일 읽기
        data = pd.read_csv(csv_file)

        # 업로드 날짜와 시간 설정
        upload_timestamp = datetime.now()  # 현재 날짜와 시간 (YYYY-MM-DD HH:MM:SS)

        # Cursor 생성
        cur = conn.cursor()

        # 기존 데이터 삭제 (전체 삭제)
        delete_query = "DELETE FROM korea_stock_analysis"
        cur.execute(delete_query)
        print("기존 데이터 삭제 완료.")

        # SQL INSERT문
        insert_query = """
        INSERT INTO korea_stock_analysis (
            StockName, StockCode, CurrentPrice, Price_Change_Value, Price_Change_Status, 
            Volume, VolumeChangeRate, Action, Candle_Pattern, MACD_Trend, RSI_Status, 
            Volume_Trend, Price_vs_Bollinger, Slope_5, Slope_20, Slope_60, Slope_120, 
            Recent_Max_Volume_Date, Recent_Max_Volume_Change, Recent_Max_Volume_Trend, 
            Recent_Max_Volume_Value, Support_1, Support_2, Support_3, Resistance_1, 
            Resistance_2, Resistance_3, upload_date
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        # 데이터 삽입
        for _, row in data.iterrows():
            cur.execute(insert_query, (
                row['StockName'], row['StockCode'], row['CurrentPrice'], row['Price_Change_Value'], row['Price_Change_Status'],
                row['Volume'], row['VolumeChangeRate'], row['Action'], row['Candle_Pattern'], row['MACD_Trend'], row['RSI_Status'],
                row['Volume_Trend'], row['Price_vs_Bollinger'], row['Slope_5'], row['Slope_20'], row['Slope_60'], row['Slope_120'],
                row['Recent_Max_Volume_Date'], row['Recent_Max_Volume_Change'], row['Recent_Max_Volume_Trend'], row['Recent_Max_Volume_Value'],
                row['Support_1'], row['Support_2'], row['Support_3'], row['Resistance_1'], row['Resistance_2'], row['Resistance_3'],
                upload_timestamp  # 업로드 날짜 추가
            ))

        # 커밋
        conn.commit()
        print("데이터 삽입 성공!")
        cur.close()

    except Exception as e:
        print("데이터 삽입 실패:", e)
        conn.rollback()  # 트랜잭션 롤백
        raise e  # 예외를 호출한 곳으로 전달


# 메인 실행
if __name__ == "__main__":
    # DB 연결
    connection = connect_to_db()
    if connection:
        # CSV 파일 경로
        csv_file_path = "korea_analysis_combined.csv"

        # 데이터 삽입
        insert_data_to_db(connection, csv_file_path)

        # 연결 닫기
        connection.close()
