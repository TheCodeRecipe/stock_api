# Stock Signal Backend

Stock Signal 프로젝트의 백엔드 코드입니다. Flask를 기반으로 작성되었으며, JWT 인증과 주식 데이터 분석 기능을 포함합니다.

## **기능**
- **JWT 인증**: 로그인 후 토큰 발급 및 검증.
- **주식 데이터 분석 로직**:
  - Yahoo Finance API를 통해 단순 주식 가격 데이터를 가져옵니다.
  - 이동평균선, 저항선, 지지선을 계산하여 기술적 분석을 수행합니다.
  - 커스텀 로직을 통해 주식의 상승/하락 신호를 추측합니다.
- **데이터베이스 관리**:
  - Render PostgreSQL 데이터베이스에 분석 결과를 저장하고 관리.


## **자세한 내용**
프로젝트의 전체적인 설명과 자세한 내용을 보려면 아래 링크를 참고하세요:

🔗 **[Stock Signal 프론트엔드 리포지토리](https://github.com/TheCodeRecipe/stock-signal)**
