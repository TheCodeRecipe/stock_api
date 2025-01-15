import yfinance as yf
import pandas as pd
import os
from datetime import datetime, timedelta

# 데이터를 가져오는 함수
def fetch_yahoo_finance_data(stock_codes, output_folder):
    # 오늘 날짜 및 내일 날짜 설정
    today = datetime.now().strftime("%Y-%m-%d")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    for code, name in stock_codes.items():
        try:
            # 기존 파일 확인
            existing_files = [
                f for f in os.listdir(output_folder)
                if f.startswith(f"{name}_{code.replace('.KS', '').replace('.KQ', '')}")
            ]

            # 기존 파일에서 최신 날짜 추출
            latest_date = None
            existing_data = pd.DataFrame()
            if existing_files:
                latest_file = max(existing_files, key=lambda x: x.split("_")[-1].replace(".csv", ""))
                latest_date = latest_file.split("_")[-1].replace(".csv", "")
                existing_data = pd.read_csv(os.path.join(output_folder, latest_file), parse_dates=["Date"])

            # 데이터 가져올 시작 날짜 설정
            start_date = (datetime.strptime(latest_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d") if latest_date else "2020-01-01"

            # Yahoo Finance에서 데이터 가져오기
            new_data = yf.download(code, start=start_date, end=tomorrow)

            if new_data.empty:
                print(f"데이터가 비어 있음: {name} ({code})")
                break

            # 데이터 정리
            new_data.columns = new_data.columns.get_level_values(0)

            if "Adj Close" not in new_data.columns:
                print(f"'Adj Close'가 없음. 'Close'를 대신 사용합니다: {name} ({code})")
                new_data["Adj Close"] = new_data["Close"]

            new_data = new_data.reset_index()
            new_data = new_data.rename(columns={
                "Open": "Open",
                "High": "High",
                "Low": "Low",
                "Close": "Close",
                "Adj Close": "Adj Close",
                "Volume": "Volume",
                "Date": "Date"
            })

            # StockName과 StockCode 추가
            new_data["StockName"] = name
            new_data["StockCode"] = code.replace(".KS", "").replace(".KQ", "")

            # 컬럼 순서 재정리
            new_data = new_data[["Date", "StockName", "StockCode", "Open", "High", "Low", "Close", "Volume", "Adj Close"]]

            # 기존 데이터와 새로운 데이터 병합
            combined_data = pd.concat([existing_data, new_data])
            combined_data = combined_data.drop_duplicates(subset=["Date", "StockCode"]).sort_values(by="Date")

            # 새로운 파일 이름에 오늘 날짜 포함
            new_file_name = os.path.join(output_folder, f"{name}_{code.replace('.KS', '').replace('.KQ', '')}_{today}.csv")

            # 병합된 데이터 저장
            combined_data.to_csv(new_file_name, index=False, encoding="utf-8-sig")
            print(f"{name} ({code}) 데이터 저장 완료: {new_file_name}")

            # 기존 파일 삭제
            for old_file in existing_files:
                old_file_path = os.path.join(output_folder, old_file)
                os.remove(old_file_path)
                print(f"기존 파일 삭제 완료: {old_file_path}")

        except Exception as e:
            print(f"에러 발생: {name} ({code}): {e}")
