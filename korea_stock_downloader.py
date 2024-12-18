import FinanceDataReader as fdr
import pandas as pd
import os
from datetime import datetime

# 주식 종목 코드 리스트
stock_codes = {
    "005930": "삼성전자",
    "000660": "SK하이닉스",
    # 필요에 따라 코드 추가
}

# 주식 데이터를 다운로드하고 CSV 파일로 저장하는 함수
def download_stock_data(output_folder):
    today = datetime.now().strftime("%Y-%m-%d")
    chunks = [dict(list(stock_codes.items())[i:i + 10]) for i in range(0, len(stock_codes), 10)]

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    for idx, chunk in enumerate(chunks, start=1):
        all_data = []

        for code, name in chunk.items():
            try:
                price_df = fdr.DataReader(code, start='2020-01-01', end=today)
                price_df['StockName'] = name
                price_df['StockCode'] = code
                all_data.append(price_df)
                print(f"{name} ({code}) 데이터 처리 완료.")
            except Exception as e:
                print(f"에러 발생: {name} ({code}): {e}")

        if all_data:
            final_df = pd.concat(all_data)
            columns_order = ['StockName', 'StockCode'] + [col for col in final_df.columns if col not in ['StockName', 'StockCode']]
            final_df = final_df[columns_order]

            file_name = f"korea_stocks_price_data_part_{idx}_{today}.csv"
            output_path = os.path.join(output_folder, file_name)
            final_df.to_csv(output_path, encoding='utf-8-sig', index=True)
            print(f"파일 저장 완료: {output_path}")
        else:
            print(f"저장할 데이터가 없습니다 (파트 {idx}).")
