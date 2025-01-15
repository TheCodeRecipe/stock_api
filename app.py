from flask import Flask, jsonify, send_file, request
from flask_cors import CORS
import pandas as pd
import os
from stock_codes import stock_codes
from stockAnalyzer import analyze_stocks_with_combined_logic
from korea_stock_downloader import fetch_yahoo_finance_data
from upload_korea_stock_data import connect_to_db, upload_data_to_db
import zipfile
import io

from fastapi import Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from jose import jwt, JWTError, ExpiredSignatureError
from datetime import datetime, timedelta

app = Flask(__name__)

# CORS 설정
CORS(app, resources={r"/*": {"origins": ["http://localhost:3000", "http://localhost:8080", "https://stock-signal-six.vercel.app"]}})

# 프로젝트의 루트 디렉토리를 기준으로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FOLDER = os.path.join(BASE_DIR, "korea_stocks_data_parts")
OUTPUT_CSV = os.path.join(BASE_DIR, "korea_analysis_combined.csv")

SECRET_KEY = os.environ["SECRET_KEY"]  # 필수 환경변수, 없으면 KeyError 발생
ALGORITHM = os.environ.get("ALGORITHM", "HS256")  # 선택적 환경변수
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"])  # 필수
VALID_PASSWORD = os.environ["VALID_PASSWORD"]  # 필수

@app.route("/")
def home():
    return jsonify({"message": "Welcome to the stock API sample project!"})

@app.route("/update-stocks", methods=["POST"])
def update_all_stocks():
    try:
        # 2. 주식 데이터 다운로드
        fetch_yahoo_finance_data(stock_codes, OUTPUT_FOLDER)
        
        # 3. 주식 데이터 분석
        analyze_stocks_with_combined_logic(OUTPUT_FOLDER, OUTPUT_CSV)
        
        return jsonify({"message": "All stock data updated successfully!"})
    except HTTPException as e:
        # 인증 실패 시 에러 반환
        return jsonify({"error": e.detail}), e.status_code
    except Exception as e:
        # 기타 에러 처리
        return jsonify({"error": f"Failed to update stocks: {str(e)}"}), 500

@app.route('/download/korea-analysis-combined', methods=['GET'])
def download_korea_analysis_combined():
    try:
        # 상위 디렉토리에 위치한 파일 경로
        file_path = os.path.join(os.getcwd(), "korea_analysis_combined.csv")

        # 파일이 존재하는지 확인
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            # 파일이 없으면 JSON 응답
            return jsonify({"success": False, "message": "File not found"}), 404
    except Exception as e:
        # 오류 발생 시 JSON 응답
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/download/folder', methods=['GET'])
def download_folder():
    try:
        # 폴더 경로 설정
        folder_path = os.path.join(os.getcwd(), "korea_stocks_data_parts")

        # 폴더 존재 여부 확인
        if not os.path.exists(folder_path):
            return jsonify({"success": False, "message": "Folder not found"}), 404

        # 압축 파일 생성
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, folder_path)  # 폴더 구조 유지
                    zip_file.write(file_path, arcname)

        zip_buffer.seek(0)  # 버퍼의 시작으로 이동

        # 압축 파일을 클라이언트로 전송
        return send_file(
            zip_buffer,
            mimetype="application/zip",
            as_attachment=True,
            download_name="korea_stocks_data_parts.zip",
        )
    
    except Exception as e:
        # 오류 발생 시 JSON 응답
        return jsonify({"success": False, "message": str(e)}), 500
    
if __name__ == "__main__":
    # 환경 변수 PORT가 있으면 사용하고, 없으면 5000번 포트를 사용
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
