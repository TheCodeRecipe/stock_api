from flask import Flask, jsonify
import csv
import os

app = Flask(__name__)

# 프로젝트의 루트 디렉토리를 기준으로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 샘플 CSV 파일 경로
CSV_FILE = os.path.join(BASE_DIR, "sample_data", "sample.csv")

# 결과 CSV 파일 경로
OUTPUT_CSV = os.path.join(BASE_DIR, "korea_analysis_combined.csv")

@app.route("/")
def home():
    return jsonify({"message": "Welcome to the stock API sample project!"})

@app.route("/stocks", methods=["GET"])
def get_stocks():
    try:
        stocks = []
        with open(CSV_FILE, "r") as file:
            reader = csv.DictReader(file)
            for row in reader:
                stocks.append(row)
        return jsonify({"data": stocks})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# /korea-stocks 경로: 분석된 주식 데이터를 가져오기
@app.route("/korea-stocks", methods=["GET"])
def get_korea_stocks():
    try:
        # CSV 파일 읽기
        if not os.path.exists(OUTPUT_CSV):
            return jsonify({"error": "Analysis data not found. Please run the analysis first."}), 404
        
        # CSV를 DataFrame으로 불러오기
        data = pd.read_csv(OUTPUT_CSV)
        data = data.fillna("")  # 결측값은 빈 문자열로 처리
        
        # DataFrame을 JSON으로 변환 후 반환
        result = data.to_dict(orient="records")  # JSON 형태: 리스트[딕셔너리, ...]
        return jsonify({"data": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # 환경 변수 PORT가 있으면 사용하고, 없으면 5000번 포트를 사용
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
