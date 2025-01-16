
# Stock Signal Backend (Python API)

이 프로젝트는 주식 데이터를 수집하고, 분석 및 가공하여 스프링(Spring) 서버에 전달하는 역할을 합니다. 
Python의 Flask 프레임워크를 기반으로 작성되었습니다.


## **기능**

1. **주식 데이터 수집 및 분석**
   - **Yahoo Finance API**를 활용하여 주식 데이터를 수집.
   - 전날 종가 데이터를 기반으로 기술적 분석(이동평균선, 지지선, 저항선)을 수행.
   - 커스텀 로직을 통해 주식의 상승/하락 신호를 추측.

2. **데이터 다운로드**
   - 분석된 데이터(CSV 파일)를 스프링 서버에서 사용할 수 있도록 제공.


## **사용 기술**
- **프레임워크**: Flask
- **데이터 출처**: Yahoo Finance API


🔗 **[Stock Signal 프론트엔드 리포지토리](https://github.com/TheCodeRecipe/stock-signal)**

🔗 **[Stock Signal 스프링 리포지토리](https://github.com/TheCodeRecipe/stock-spring)**
