from flask import Flask, jsonify, send_file
import pandas as pd
import csv
import os
from stock_codes import stock_codes
from stockAnalyzer import analyze_stocks_with_combined_logic
from korea_stock_downloader import fetch_yahoo_finance_data
from upload_korea_stock_data import connect_to_db, upload_data_to_db

app = Flask(__name__)

# 프로젝트의 루트 디렉토리를 기준으로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FOLDER = os.path.join(BASE_DIR, "korea_stocks_data_parts")
OUTPUT_CSV = os.path.join(BASE_DIR, "korea_analysis_combined.csv")

@app.route("/")
def home():
    return jsonify({"message": "Welcome to the stock API sample project!"})

@app.route("/stocks", methods=["GET"])
def get_all_stocks():
    try:
        conn = connect_to_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM korea_stock_analysis")
        rows = cur.fetchall()
        
        # 컬럼 이름 가져오기
        column_names = [desc[0] for desc in cur.description]
        
        # 데이터를 딕셔너리로 변환
        results = [dict(zip(column_names, row)) for row in rows]

        cur.close()
        conn.close()
        return jsonify({"stocks": results}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch stocks: {str(e)}"}), 500

@app.route("/stocks/<string:stock_code>", methods=["GET"])
def get_stock_by_code(stock_code):
    """특정 주식 데이터를 StockCode를 기준으로 DB에서 가져오는 API"""
    try:
        conn = connect_to_db()
        cur = conn.cursor()
        query = "SELECT * FROM korea_stock_analysis WHERE stockcode = %s"
        cur.execute(query, (stock_code,))
        row = cur.fetchone()

        # 컬럼 이름 가져오기
        column_names = [desc[0] for desc in cur.description]
        
        # 데이터 변환
        result = dict(zip(column_names, row)) if row else None

        cur.close()
        conn.close()

        if result:
            return jsonify({"stock": result}), 200
        else:
            return jsonify({"error": f"No stock found with code {stock_code}"}), 404
    except Exception as e:
        return jsonify({"error": f"Failed to fetch stock: {str(e)}"}), 500

@app.route("/update-stocks", methods=["POST"])
def update_all_stocks():
    try:
        # 1. 기존 CSV 파일 삭제
        if os.path.exists(OUTPUT_FOLDER):
            for file in os.listdir(OUTPUT_FOLDER):
                if file.endswith(".csv"):
                    file_path = os.path.join(OUTPUT_FOLDER, file)
                    os.remove(file_path)
                    print(f"기존 파일 삭제: {file_path}")

        # 2. 주식 데이터 다운로드
        fetch_yahoo_finance_data(stock_codes, OUTPUT_FOLDER)
        
        # 3. 주식 데이터 분석
        analyze_stocks_with_combined_logic(OUTPUT_FOLDER, OUTPUT_CSV)
        
        # 4. DB 연결 객체 생성
        connection = connect_to_db()
        if connection is None:
            raise Exception("DB 연결 실패")

        # 5. 분석 결과를 데이터베이스에 업로드
        upload_data_to_db(connection, OUTPUT_CSV)
        
        # 6. 연결 종료
        connection.close()
        
        return jsonify({"message": "All stock data updated successfully!"})
    except Exception as e:
        return jsonify({"error": f"Failed to update stocks: {str(e)}"}), 500


@app.route("/download-analysis", methods=["GET"])
def download_analysis():
    output_path = os.path.join(os.getcwd(), "korea_analysis_combined.csv")
    try:
        return send_file(output_path, as_attachment=True)
    except Exception as e:
        return jsonify({"error": f"Failed to download file: {str(e)}"}), 500

@app.route("/download-stock-data", methods=["POST"])
def trigger_stock_data_download():
    try:
        # 데이터를 저장할 폴더 지정
        output_folder = os.path.join(os.getcwd(), "korea_stocks_data_parts")
        # stock_codes는 korea_stock_downloader 내부에서 이미 정의됨
        fetch_yahoo_finance_data(output_folder)  
        return jsonify({"message": "Stock data download completed.", "folder": output_folder})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # 환경 변수 PORT가 있으면 사용하고, 없으면 5000번 포트를 사용
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
