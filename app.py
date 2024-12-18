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
        return jsonify({"error": str(e)})), 500

if __name__ == "__main__":
    app.run(debug=True)
