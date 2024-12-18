from flask import Flask, jsonify
import csv
import os

app = Flask(__name__)

# 샘플 CSV 파일 경로
CSV_FILE = os.path.join("sample_data", "sample.csv")

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

if __name__ == "__main__":
    # 환경 변수 PORT가 있으면 사용하고, 없으면 5000번 포트를 사용
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
