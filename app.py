import yfinance as yf
import pandas as pd
import os
from datetime import datetime

# 주식 종목 코드 리스트 (여기서 정의)
stock_codes = {
    "005930.KS": "삼성전자",
    "000660.KS": "SK하이닉스",
}

# 오늘 날짜 설정
today = datetime.now().strftime("%Y-%m-%d")

# 데이터를 가져오는 함수
def fetch_yahoo_finance_data(output_folder):
    for code, name in stock_codes.items():  # stock_codes는 내부에서 사용
        try:
            stock_data = yf.download(code, start="2020-01-01", end=today)

            # 컬럼 및 데이터 처리
            stock_data.columns = stock_data.columns.get_level_values(0)
            stock_data = stock_data.reset_index()
            stock_data = stock_data.rename(columns={
                "Open": "Open", "High": "High", "Low": "Low", 
                "Close": "Close", "Adj Close": "Adj Close", "Volume": "Volume"
            })
            stock_data["StockName"] = name
            stock_data["StockCode"] = code.replace(".KS", "").replace(".KQ", "")  # 확장자 제거

            # 컬럼 순서 재정리
            stock_data = stock_data[["Date", "StockName", "StockCode", "Open", "High", "Low", "Close", "Volume", "Adj Close"]]

            # 파일 저장
            file_name = os.path.join(output_folder, f"{name}_{stock_data['StockCode'][0]}_{today}.csv")
            stock_data.to_csv(file_name, index=False, encoding="utf-8-sig")
            print(f"{name} ({code}) 데이터 저장 완료: {file_name}")
        except Exception as e:
            print(f"에러 발생: {name} ({code}): {e}")
