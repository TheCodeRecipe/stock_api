from flask import Flask, jsonify, send_file, request
from flask_cors import CORS
import pandas as pd
import csv
import os
from stock_codes import stock_codes
from stockAnalyzer import analyze_stocks_with_combined_logic
from korea_stock_downloader import fetch_yahoo_finance_data
from upload_korea_stock_data import connect_to_db, upload_data_to_db

from fastapi import Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from jose import jwt, JWTError, ExpiredSignatureError
from datetime import datetime, timedelta

app = Flask(__name__)

# CORS 설정
CORS(app, resources={r"/*": {"origins": ["http://localhost:3000", "https://stock-signal-six.vercel.app"]}})

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

# JWT 토큰 검증 함수
def verify_jwt_token():
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No token provided")

    token = auth_header.split(" ")[1]  # "Bearer <token>"에서 토큰만 추출
    try:
        # 토큰 검증
        jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


@app.route("/update-stocks", methods=["POST"])
def update_all_stocks():
    try:
        # JWT 토큰 인증
        # verify_jwt_token()

        # 폴더 생성
        if not os.path.exists(OUTPUT_FOLDER):
            os.makedirs(OUTPUT_FOLDER)
            print(f"폴더 생성 완료: {OUTPUT_FOLDER}")

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
        upload_data_to_db(connection, OUTPUT_CSV, market_type="KR")
        
        # 6. 연결 종료
        connection.close()
        
        return jsonify({"message": "All stock data updated successfully!"})
    # except HTTPException as e:
    #     # 인증 실패 시 에러 반환
    #     return jsonify({"error": e.detail}), e.status_code
    except Exception as e:
        # 기타 에러 처리
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


@app.route("/last-update", methods=["GET"])
def get_last_update():
    try:
        market_type = request.args.get("market_type", "KR")  # 기본값은 'KR'
        conn = connect_to_db()
        cur = conn.cursor()

        query = """
            SELECT update_time, market_type 
            FROM update_logs 
            WHERE market_type = %s 
            ORDER BY update_time DESC 
            LIMIT 1
        """
        cur.execute(query, (market_type,))
        last_update = cur.fetchone()

        cur.close()
        conn.close()

        if last_update:
            return jsonify({
                "last_update": last_update[0],
                "market_type": last_update[1]
            })
        else:
            return jsonify({"message": f"No updates yet for market type '{market_type}'."}), 404
    except Exception as e:
        return jsonify({"error": f"Failed to fetch last update: {str(e)}"}), 500


@app.post("/auth/login")
def login():
    # JSON 데이터 읽기
    data = request.get_json()  # Flask의 request 객체에서 JSON 데이터 읽기
    password = data.get("password") if data else None
    print(f"Received password: {password}")

    if password != VALID_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid password")

    # JWT 토큰 생성
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = jwt.encode({"exp": expire}, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token}


# JWT 인증 확인
@app.get("/auth/verify")
def verify_token():
    # Authorization 헤더에서 토큰 읽기
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No token provided")

    token = auth_header.split(" ")[1]  # "Bearer <token>"에서 토큰만 추출
    try:
        jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])  # JWT 검증
        return jsonify({"valid": True})
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


if __name__ == "__main__":
    # 환경 변수 PORT가 있으면 사용하고, 없으면 5000번 포트를 사용
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
