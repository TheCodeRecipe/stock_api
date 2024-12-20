import yfinance as yf
import pandas as pd
import os
from datetime import datetime, timedelta

# 데이터를 가져오는 함수
def fetch_yahoo_finance_data(stock_codes, output_folder):
    # 오늘 날짜 설정
    today = datetime.now().strftime("%Y-%m-%d")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    for code, name in stock_codes.items():
        try:
            # Yahoo Finance에서 데이터 가져오기
            stock_data = yf.download(code, start="2020-01-01", end=tomorrow)

            # 데이터가 비어 있는 경우
            if stock_data.empty:
                print(f"데이터가 비어 있음: {name} ({code})")
                continue


            # 컬럼 확인 및 단일 레벨로 변환
            stock_data.columns = stock_data.columns.get_level_values(0)

            # Adj Close 확인
            if "Adj Close" in stock_data.columns:
                stock_data["Adj Close"] = stock_data["Adj Close"]
            else:
                print(f"'Adj Close'가 없음. 'Close'를 대신 사용합니다: {name} ({code})")
                stock_data["Adj Close"] = stock_data["Close"]


            # 컬럼명 재정의 (가격 순서 올바르게 설정)
            stock_data = stock_data.reset_index()
            stock_data = stock_data.rename(columns={
                "Open": "Open",
                "High": "High",
                "Low": "Low",
                "Close": "Close",
                "Adj Close": "Adj Close",
                "Volume": "Volume"
            })

            # StockName과 StockCode 추가 (.KS 제거)
            stock_data["StockName"] = name
            stock_data["StockCode"] = code.replace(".KS", "").replace(".KQ", "")  # 확장자 제거

            # 컬럼 순서 재정리
            stock_data = stock_data[["Date", "StockName", "StockCode", "Open", "High", "Low", "Close", "Volume", "Adj Close"]]

            # 파일 저장 (인덱스 제거)
            file_name = os.path.join(output_folder, f"{name}_{stock_data['StockCode'][0]}_{today}.csv")
            stock_data.to_csv(file_name, index=False, encoding="utf-8-sig")
            
            print(f"{name} ({code}) 데이터 저장 완료: {file_name}")
        except Exception as e:
            print(f"에러 발생: {name} ({code}): {e}")

