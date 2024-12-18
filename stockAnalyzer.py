import pandas as pd
import os

def calculate_rsi(data, period=14):
    delta = data['Close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(window=period, min_periods=1).mean()
    avg_loss = loss.rolling(window=period, min_periods=1).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_macd(data, short_period=12, long_period=26, signal_period=9):
    short_ema = data['Close'].ewm(span=short_period, adjust=False).mean()
    long_ema = data['Close'].ewm(span=long_period, adjust=False).mean()
    macd = short_ema - long_ema
    signal = macd.ewm(span=signal_period, adjust=False).mean()
    return macd, signal


def calculate_bollinger_bands(data, period=20, num_std_dev=2):
    middle_band = data['Close'].rolling(window=period).mean()
    std_dev = data['Close'].rolling(window=period).std()
    upper_band = middle_band + (num_std_dev * std_dev)
    lower_band = middle_band - (num_std_dev * std_dev)
    return upper_band, middle_band, lower_band


def calculate_volume_patterns(data, period=5):
    data['VolumeChangeRate'] = data['Volume'].pct_change() * 100
    data['RecentVolumeAvg'] = data['Volume'].rolling(window=period).mean()
    return data


def detect_significant_turning_points(data, window=10, min_gap_percentage=5.0):
    """
    전체 데이터를 기준으로 강한 지지선과 저항선을 탐지합니다.
    Args:
        data (pd.DataFrame): 종목 데이터 (Date, Close 포함)
        window (int): 터닝포인트를 확인할 이동 평균 범위
        min_gap_percentage (float): 지지선/저항선 간 최소 차이 비율
    Returns:
        supports (list): [(가격, 날짜), ...] 형태의 지지선 목록
        resistances (list): [(가격, 날짜), ...] 형태의 저항선 목록
    """
    data = data.reset_index(drop=True)  # 인덱스 초기화
    data['rolling_max'] = data['Close'].rolling(window=window, center=True).max()
    data['rolling_min'] = data['Close'].rolling(window=window, center=True).min()
    
    supports = []
    resistances = []

    for i in range(window, len(data) - window):
        current_price = data['Close'].iloc[i]
        
        # 저점 (지지선): 최저값과 일치하는 포인트
        if current_price == data['rolling_min'].iloc[i]:
            supports.append((current_price, data['Date'].iloc[i]))

        # 고점 (저항선): 최고값과 일치하는 포인트
        if current_price == data['rolling_max'].iloc[i]:
            resistances.append((current_price, data['Date'].iloc[i]))

    # 중복 및 가까운 포인트 필터링
    def filter_points(points):
        filtered = []
        for price, date in points:
            if not filtered or abs(price - filtered[-1][0]) > (filtered[-1][0] * min_gap_percentage / 100):
                filtered.append((price, date))
        return filtered

    supports = filter_points(sorted(supports, key=lambda x: x[1]))  # 날짜순 정렬
    resistances = filter_points(sorted(resistances, key=lambda x: x[1], reverse=True))  # 날짜 역순 정렬

    return supports, resistances


def calculate_support_resistance(current_price, supports, resistances, max_levels=3):
    """
    지지선과 저항선을 현재 가격 기준으로 통합하여 나눕니다.
    Args:
        current_price (float): 현재 가격
        supports (list): [(가격, 날짜), ...] 형태의 지지선 목록
        resistances (list): [(가격, 날짜), ...] 형태의 저항선 목록
        max_levels (int): 최대 반환할 지지선/저항선 개수
    Returns:
        filtered_supports (list): 현재 가격보다 낮은 지지선 (가까운 순서대로)
        filtered_resistances (list): 현재 가격보다 높은 저항선 (가까운 순서대로)
    """
    # 지지선과 저항선을 통합
    turning_points = supports + resistances
    turning_points = sorted(turning_points, key=lambda x: x[0])  # 가격 기준 정렬

    # 현재 가격 기준으로 나눔
    filtered_supports = [(price, date) for price, date in turning_points if price < current_price]
    filtered_resistances = [(price, date) for price, date in turning_points if price > current_price]

    # 가까운 순서대로 최대 max_levels 개수 선택
    filtered_supports = sorted(filtered_supports, reverse=True)[:max_levels]
    filtered_resistances = sorted(filtered_resistances)[:max_levels]

    return filtered_supports, filtered_resistances


def determine_weighted_max_volume_date(stock_df):
    """
    가장 거래량 가중치가 높은 날짜와 해당 날짜의 추세, 거래량, 가격 변동률을 반환
    """
    stock_df = stock_df.copy()

    # 거래량 가중치 계산
    stock_df['WeightedVolume'] = stock_df['Volume'] * (1 + stock_df['pct_change'].abs())

    # 가중치가 가장 높은 날 찾기
    max_weighted_date = stock_df.loc[stock_df['WeightedVolume'].idxmax(), 'Date']
    max_weighted_data = stock_df[stock_df['Date'] == max_weighted_date]

    # 결과 반환
    if not max_weighted_data.empty:
        max_weighted_pct_change = max_weighted_data.iloc[0]['pct_change']
        max_weighted_volume = max_weighted_data.iloc[0]['Volume']
        max_weighted_trend = "상승" if max_weighted_pct_change > 0 else "하락"
    else:
        max_weighted_pct_change, max_weighted_volume, max_weighted_trend = None, None, None

    return max_weighted_date, max_weighted_trend, max_weighted_volume, max_weighted_pct_change


def detect_pullback_pattern(data, macd, signal, upper_band, middle_band, lower_band, 
                            recent_days=10, volume_threshold=1.5, avg_volume_threshold=2, 
                            tolerance=0.05, max_deviation=0.1):
    """
    거래량 조건을 강화하여 눌림목 패턴 감지.
    """
    recent_data = data.tail(recent_days).copy()
    if len(recent_data) < 3:
        return False, "데이터 부족: 패턴 감지에 필요한 데이터가 충분하지 않습니다."

    recent_close = recent_data['Close'].values
    recent_volume = recent_data['Volume'].values

    # 상승 추세 여부
    is_uptrend = macd > signal

    # 1. 최고점 이후 하락 흐름 확인
    highest_price = max(recent_close)
    highest_index = recent_close.argmax()
    after_highest = recent_close[highest_index:]
    is_downtrend = sum(after_highest[i] > after_highest[i + 1] for i in range(len(after_highest) - 1)) >= 2

    # 2. 최저점 조건 (최저점 근처 및 현재 종가와 이격도 확인)
    recent_min = min(recent_close[-5:])
    tolerance_range = recent_min * (1 + tolerance)
    deviation = abs(recent_close[-1] - recent_min) / recent_min

    yesterday_is_min_near = recent_close[-2] <= tolerance_range
    is_close_to_min = deviation <= max_deviation

    # 3. 오늘 종가 상승 확인
    today_rising = recent_close[-1] > recent_close[-2]

    # 4. 거래량 조건 강화
    recent_avg_volume = recent_volume[:-1].mean()
    volume_spike = recent_volume[-1] > recent_volume[-2] * volume_threshold  # 전날 대비 거래량 증가
    volume_significant = recent_volume[-1] > recent_avg_volume * avg_volume_threshold  # 평균 대비 거래량 증가

    # 5. 볼린저 밴드 조건
    if is_uptrend:
        # 상승 추세: 중간선 이상도 허용
        is_valid_band_position = recent_close[-1] >= middle_band
    else:
        # 하락 추세: 반드시 하단 근처
        is_valid_band_position = lower_band * 0.95 <= recent_close[-1] <= lower_band * 1.05

    # 디버깅용 출력
    # print(f"추세: {'상승' if is_uptrend else '하락'}")
    # print(f"최고점 이후 하락 흐름: {is_downtrend}")
    # print(f"최저점: {recent_min:.2f}, 허용 범위: {tolerance_range:.2f}, 이격도: {deviation:.2%}")
    # print(f"전날 최저점 근처 여부: {yesterday_is_min_near}")
    # print(f"오늘 종가 상승 여부: {today_rising}")
    # print(f"거래량 조건: 전날 대비 증가 {volume_spike}, 평균 대비 증가 {volume_significant}")
    # print(f"볼린저 밴드 조건: {'충족' if is_valid_band_position else '미충족'}")
    # print(f"현재 종가: {recent_close[-1]:.2f}, 중간선: {middle_band:.2f}, 하단선: {lower_band:.2f}, 상단선: {upper_band:.2f}")

    # 최종 조건 확인
    if is_downtrend and is_valid_band_position and yesterday_is_min_near and today_rising and (volume_spike or volume_significant):
        return True, "눌림목 패턴 감지: 추세와 볼린저 밴드 조건 충족"
    elif is_downtrend and is_valid_band_position and today_rising and (volume_spike or volume_significant):
        return True, "눌림목 패턴 감지(최저점 조건 제외): 추세와 볼린저 밴드 조건 충족"
    else:
        return False, "눌림목 조건 미충족: 거래량 조건 부족"


def calculate_moving_average_slopes(data, periods=[5, 20, 60, 120]):
    """
    이동평균선의 기울기(상승/하락)를 계산하여 데이터프레임에 추가합니다.
    Args:
        data (pd.DataFrame): 주식 데이터
        periods (list): 이동평균선의 기간 리스트
    Returns:
        pd.DataFrame: 이동평균 기울기가 추가된 데이터프레임
    """
    for period in periods:
        ma_column = f"MA_{period}"
        slope_column = f"Slope_{period}"

        # 이동평균선 계산
        data[ma_column] = data['Close'].rolling(window=period).mean()

        # 이동평균선 기울기 계산
        data[slope_column] = data[ma_column] - data[ma_column].shift(1)

        # 상승/하락 여부 판단
        data[slope_column] = data[slope_column].apply(lambda x: "상승" if x > 0 else "하락" if x < 0 else "유지")

    return data

def detect_candle_patterns(data):
    patterns = []

    for i in range(1, len(data)):
        open_price = data['Open'].iloc[i]
        close_price = data['Close'].iloc[i]
        high_price = data['High'].iloc[i]
        low_price = data['Low'].iloc[i]
        prev_close = data['Close'].iloc[i - 1]

        body = abs(close_price - open_price)
        upper_wick = high_price - max(close_price, open_price)
        lower_wick = min(close_price, open_price) - low_price

        # 패턴 감지 조건
        if close_price > open_price and body > (upper_wick + lower_wick) * 2:
            patterns.append((data['Date'].iloc[i], '장대양봉'))  # 큰 상승 신호
        elif lower_wick > body * 2 and lower_wick > upper_wick:
            patterns.append((data['Date'].iloc[i], '아랫꼬리 긴 캔들'))  # 바닥 확인 신호
        elif upper_wick > body * 2 and upper_wick > lower_wick and close_price < open_price:
            patterns.append((data['Date'].iloc[i], '위꼬리 긴 음봉'))  # 매도 압력 신호
        elif body < (upper_wick + lower_wick) * 0.3:
            patterns.append((data['Date'].iloc[i], '도지'))  # 도지 캔들
        elif close_price > prev_close:
            patterns.append((data['Date'].iloc[i], '양봉'))
        elif close_price < prev_close:
            patterns.append((data['Date'].iloc[i], '음봉'))
        else:
            patterns.append((data['Date'].iloc[i], '기타'))

    return patterns


def determine_action_with_all_factors(
    current_price, supports, resistances, rsi, macd, signal, 
    upper_band, middle_band, lower_band, 
    current_volume, volume_series, volume_change_rate, recent_volume_avg, pct_change,stock_df, candle_pattern,slope_5,slope_20
):
    # MACD 추세 결정
    trend = "상승 추세" if macd > signal else "하방 추세"

    # 볼린저 밴드 폭 기반 동적 허용 범위 설정
    band_width = upper_band - lower_band
    dynamic_margin = max(0.01 * middle_band, band_width * 0.1)  # 최소 1% 또는 밴드 폭의 10%

    # 볼린저 밴드 위치 계산
    lower_proximity = lower_band - dynamic_margin <= current_price <= lower_band + dynamic_margin
    middle_proximity = middle_band - dynamic_margin <= current_price <= middle_band + dynamic_margin
    upper_proximity = upper_band - dynamic_margin <= current_price <= upper_band + dynamic_margin

    # 볼린저 밴드 외부 계산
    below_lower_band = current_price < lower_band - dynamic_margin
    above_upper_band = current_price > upper_band + dynamic_margin

   # **거래량 상태 재계산**
    recent_max_volume = volume_series.tail(5).max()
    recent_avg_volume = volume_series.tail(5).mean()

    # 거래량 조건 확인
    is_high_volume = current_volume > recent_avg_volume * 1.5
    is_low_volume = current_volume < recent_avg_volume * 0.8

    # 거래량 코멘트 생성
    volume_comment = (
        "거래량 급증" if is_high_volume else
        "거래량 감소" if is_low_volume else
        "거래량 평타"
    )

    recent_days = 5 
    limited_stock_df = stock_df.tail(recent_days)
    max_weighted_date, max_weighted_trend, max_weighted_volume, max_weighted_pct_change = determine_weighted_max_volume_date(limited_stock_df)

    # 눌림목 패턴 확인
    is_pullback, pullback_message = detect_pullback_pattern(
        stock_df,
        macd,
        signal,
        upper_band,
        middle_band,
        lower_band,
    )
    # print(f"메시지: {pullback_message}")
    # 기본 메시지 생성 함수
    def build_message(description):
        direction = "상승 중" if pct_change > 0 else "하락 중"
        return f"{max_weighted_trend}, {volume_comment}, {trend}, {description}, 가격 {direction} ({pct_change:+.2f}%)"

    def determine_action():
        # 캔들 패턴 + 볼린저 밴드 + RSI 조건
        if candle_pattern == "장대양봉" and trend == "상승 추세" and is_high_volume:
            return "매수 적극 고려(장대양봉 확인, 강한 상승 추세)"
        elif candle_pattern == "아랫꼬리 긴 캔들" and rsi < 35 and lower_proximity:
            return "바닥 확인(아랫꼬리 긴 캔들, 매수 고려)"
        elif candle_pattern == "위꼬리 긴 음봉" and rsi > 70:
            return "매도 고려(위꼬리 긴 음봉, 과매수 상태)"
        
        # 볼린저 밴드 상단
        if above_upper_band:
            if rsi > 70 and is_high_volume:
                return "매도 고려(과매수, 거래량 급증)"
            elif rsi > 70 and is_low_volume:
                return "관망(과매수 상태, 거래량 감소)"
            elif 60 <= rsi <= 70 and not is_high_volume:
                return "관망(볼린저 상단, RSI 중립 상단)"
            else:
                return "관망(볼린저 상단, 신호 부족)"
        
        # 볼린저 밴드 하단
        if below_lower_band:
            if rsi < 30 and is_high_volume:
                return "매수 적극 고려(반등 가능성 높음, 거래량 급증)"
            elif rsi < 30 and is_low_volume:
                return "매수 대기(과매도, 거래량 부족)"
            elif rsi < 50 and lower_proximity:
                return "매수 고려(볼린저 하단 근처, RSI 중립 이하)"
            else:
                return "관망(볼린저 하단, 신호 부족)"

        # 볼린저 밴드 중간선 근처
        if middle_proximity:
            if slope_5 == "상승" and slope_20 == "상승" and rsi < 60:
                return "매수 고려(이동평균선 상승, 추세 강화 가능성)"
            elif rsi > 60 and is_high_volume:
                return "관망(RSI 상승 과열 가능성)"
            else:
                return "관망(볼린저 중간선, 신호 부족)"

        # 이동평균선 기울기 조건
        if slope_5 == "상승" and slope_20 == "상승" and trend == "상승 추세":
            return "매수 고려(이동평균선 상승 일치)"
        elif slope_5 == "하락" and slope_20 == "하락" and lower_proximity:
            return "관망(단기 하락세, 추세 확인 필요)"

        # 거래량 기반 판단
        if is_high_volume and pct_change > 2:
            return "매수 고려(거래량 급증, 강한 상승)"
        elif is_low_volume and pct_change < -3:
            return "매수 대기(하락폭 과도, 거래량 부족)"
        elif is_high_volume and pct_change < -2:
            return "관망(하락 중 거래량 급증, 추세 확인 필요)"

        # RSI 기반 판단
        if rsi > 70:
            return "매도 고려(과매수 상태)"
        elif rsi < 30:
            return "매수 고려(과매도 상태, 반등 가능성)"
        elif 60 <= rsi < 70 and trend == "상승 추세":
            return "매수 대기(RSI 상승, 추세 확인 필요)"
        elif 30 <= rsi < 50 and trend == "하방 추세":
            return "관망(약한 하락 추세, 신호 부족)"
        
        # 기본 관망
        return "관망(추가 신호 대기)"


    # 함수 외부에서 액션 및 메시지 반환
    action = determine_action()
    if is_pullback:
        action, message = action, build_message("눌림목 패턴 감지")
    elif below_lower_band:
        action, message = action, build_message(f"볼린저 밴드 하단 외부 {lower_band:.2f}")
    elif above_upper_band:
        action, message = action, build_message(f"볼린저 밴드 상단 외부 {upper_band:.2f}")
    elif lower_proximity:
        action, message = action, build_message(f"볼린저 밴드 하단 부근 {lower_band:.2f}")
    elif middle_proximity:
        action, message = action, build_message(f"볼린저 밴드 중간선 부근 {middle_band:.2f}")
    elif upper_proximity:
        action, message = action, build_message(f"볼린저 밴드 상단 부근 {upper_band:.2f}")
    else:
        if is_high_volume:  # 거래량 급증
            if pct_change > 0:
                action, message = "매수 고려(거래량 급증)", build_message("거래량 급증으로 추세 강화 가능성")
            else:
                action, message = "관망(거래량 급증)", build_message("거래량 급증, 추세 반전 가능성 확인 필요")
        elif is_low_volume:  # 거래량 감소
            if pct_change < -3:
                action, message = "매수 대기(반등 가능성 높음)", build_message("거래량 감소, 큰 하락 이후 반등 가능성")
            else:
                action, message = "관망(거래량 감소)", build_message("추세 약화 가능성")
        else:
            action, message = "관망", build_message("추가 신호 대기")

    return action, message


def analyze_stocks_with_combined_logic(input_folder, output_path):
    all_results = []

    # 폴더 내 모든 CSV 파일 읽기
    input_files = [os.path.join(input_folder, f) for f in os.listdir(input_folder) if f.endswith('.csv')]

    for file_path in input_files:
        stock_data = pd.read_csv(file_path)
        stock_data['Date'] = pd.to_datetime(stock_data['Date'])
        stock_data = stock_data.sort_values(['StockName', 'Date'])

        stock_data['RSI'] = calculate_rsi(stock_data)
        stock_data['MACD'], stock_data['Signal'] = calculate_macd(stock_data)
        stock_data['UpperBand'], stock_data['MiddleBand'], stock_data['LowerBand'] = calculate_bollinger_bands(stock_data)
        stock_data = calculate_volume_patterns(stock_data)

        stock_data['pct_change'] = stock_data['Close'].pct_change().fillna(0) * 100

        unique_stocks = stock_data['StockName'].unique()

        for stock in unique_stocks:
            # 종목별 독립적인 데이터프레임 생성
            stock_df = stock_data[stock_data['StockName'] == stock].copy()
            stock_df = stock_df.sort_values('Date')

            # StockCode를 6자리로 맞추기
            stock_code = stock_df['StockCode'].iloc[0]


            # 이동평균 기울기 계산
            stock_df = calculate_moving_average_slopes(stock_df)

            # 캔들모양
            candle_patterns = detect_candle_patterns(stock_df)
            candle_pattern = candle_patterns[-1][1] if candle_patterns else "없음"

            # 최신 데이터 가져오기
            latest_row = stock_df.iloc[-1]
            current_price = latest_row['Close']
            rsi = latest_row['RSI']
            macd = latest_row['MACD']
            signal = latest_row['Signal']
            upper_band = latest_row['UpperBand']
            middle_band = latest_row['MiddleBand']
            lower_band = latest_row['LowerBand']
            volume = latest_row['Volume']
            volume_change_rate = latest_row['VolumeChangeRate']
            recent_volume_avg = latest_row['RecentVolumeAvg']
            pct_change = latest_row['pct_change']

            # 지지와 저항선 계산
            # supports, resistances = detect_significant_turning_points(stock_df)


            supports, resistances = detect_significant_turning_points(stock_df, window=20, min_gap_percentage=3.0)

            # 종목 이름 가져오기
            stock_name = stock_df['StockName'].iloc[0]  # 첫 번째 행의 'StockName'을 가져옴

            # print(f"\n최근 유용한 지지선 ({stock_name}):")
            # # 결과 출력
            # print("\n최근 유용한 지지선:")
            # for price, date in supports:
            #     print(f"가격: {price:.2f}, 날짜: {date}")

            # print("\n최근 유용한 저항선:")
            # for price, date in resistances:
            #     print(f"가격: {price:.2f}, 날짜: {date}")
                

            # 지지선과 저항선 통합 후 현재 가격 기준 필터링
            selected_supports, selected_resistances = calculate_support_resistance(
                current_price, supports, resistances
            )

            # print(f"\n최근 유용한 지지선2 ({stock_name}):")
            # for price, date in selected_supports:
            #     print(f"가격: {price:.2f}, 날짜: {date}")

            # print(f"\n최근 유용한 저항선2 ({stock_name}):")
            # for price, date in selected_resistances:
            #     print(f"가격: {price:.2f}, 날짜: {date}")

            # 액션 및 어드바이스 결정
            action, advice = determine_action_with_all_factors(
                current_price, selected_supports, selected_resistances, rsi, macd, signal, upper_band, middle_band,
                lower_band, volume, stock_df['Volume'], volume_change_rate, recent_volume_avg, pct_change, stock_df, candle_pattern,latest_row['Slope_5'],latest_row['Slope_20']
            )

            # 디버깅용 Slope 출력
            # print(f"{stock} 최신 Slope 값:")
            # print(f"Slope_5: {latest_row['Slope_5']}, Slope_20: {latest_row['Slope_20']}, "
            #       f"Slope_60: {latest_row['Slope_60']}, Slope_120: {latest_row['Slope_120']}")


            # 최근 5일 거래량 가중치 계산
            recent_days = 5
            limited_stock_df = stock_df.tail(recent_days)
            max_weighted_date, max_weighted_trend, max_weighted_volume, max_weighted_pct_change = determine_weighted_max_volume_date(limited_stock_df)

            # 지지선과 저항선을 (가격, 날짜) 형태의 문자열로 저장
            def format_support_resistance(points, index):
                return f"{points[index][0]:.2f} ({points[index][1].date()})" if len(points) > index else None

            all_results.append({
                'StockName': stock,
                'StockCode': stock_code,
                'CurrentPrice': current_price,

                # 현재 가격변화/상승하락/거래량/거래량변동률
                'Price_Change_Value': pct_change,  # 가격변화
                'Price_Change_Status': "상승" if pct_change > 0 else "하락",
                'Volume': volume,
                'VolumeChangeRate': volume_change_rate,


                'Action': action,

                 #캔들패턴
                'Candle_Pattern': candle_pattern,

                # 현재 MACD/RSI/거래량 증감/볼린저밴드 위치
                'MACD_Trend': "상승" if macd > signal else "하락",
                'RSI_Status': "과매도" if rsi < 30 else "과매수" if rsi > 70 else "중립",
                'Volume_Trend': "증가" if volume > recent_volume_avg else "감소",
                'Price_vs_Bollinger': "상단" if current_price > upper_band else "하단" if current_price < lower_band else "중간",

                # 이동평균선
                'Slope_5': latest_row['Slope_5'],
                'Slope_20': latest_row['Slope_20'],
                'Slope_60': latest_row['Slope_60'],
                'Slope_120': latest_row['Slope_120'],

                # 최근 거래 많은 날 날짜/가격/상승하락/거래량
                'Recent_Max_Volume_Date': max_weighted_date,  # 최근 5일 기준 날짜
                'Recent_Max_Volume_Change': max_weighted_pct_change,  # 가격변화
                'Recent_Max_Volume_Trend': max_weighted_trend,  # 상승/하락 여부
                'Recent_Max_Volume_Value': max_weighted_volume,  # 거래량

                # 지지선
                'Support_1': format_support_resistance(selected_supports, 0),
                'Support_2': format_support_resistance(selected_supports, 1),
                'Support_3': format_support_resistance(selected_supports, 2),

                # 저항선
                'Resistance_1': format_support_resistance(selected_resistances, 0),
                'Resistance_2': format_support_resistance(selected_resistances, 1),
                'Resistance_3': format_support_resistance(selected_resistances, 2)
            })
  

    # 모든 결과를 하나의 데이터프레임으로 변환
    results_df = pd.DataFrame(all_results)

    # Define priority mapping for actions
    action_priority = {
        # 매수 강한
        "매수 적극 고려(장대양봉 확인, 강한 상승 추세)": 10,
        "매수 고려(거래량 급증, 강한 상승)": 20,
        "매수 고려(반등 가능성 높음)": 30,
        "매수 고려(볼린저 하단 근처, RSI 중립 이하)": 40,
        "매수 고려(이동평균선 상승, 추세 강화 가능성)": 50,
        "매수 고려(이동평균선 상승 일치)": 60,
        "매수 고려(과매도 상태, 반등 가능성)": 70,

        # 매수 대기
        "매수 대기(과매도, 거래량 부족)": 80,
        "매수 대기(돌파 가능성)": 90,
        "매수 대기(RSI 상승, 추세 확인 필요)": 100,

        # 관망
        "관망(볼린저 상단, RSI 중립 상단)": 110,
        "관망(과매수 상태, 거래량 감소)": 120,
        "관망(추세 확인 필요)": 130,
        "관망(추세 강화 가능성)": 140,
        "관망(하락 중 거래량 급증, 추세 확인 필요)": 150,
        "관망(단기 하락세, 추세 확인 필요)": 160,
        "관망(볼린저 중간선, 신호 부족)": 170,
        "관망(볼린저 하단, 신호 부족)": 180,
        "관망(거래량 감소)": 190,
        "관망(추세 약화 가능성)": 200,
        "관망(조정 가능성)": 210,
        "관망(추가 하락 가능성)": 220,

        # 매도 약한
        "매도 고려(과매수, 거래량 급증)": 230,
        "매도 고려(위꼬리 긴 음봉, 과매수 상태)": 240,

        # 매도 강한
        "매도 고려(상승 피로 누적)": 250
    }

    # Map priority values to a new column
    results_df['Priority'] = results_df['Action'].map(action_priority)

    # Sort the results by priority (ascending) and then by CurrentPrice (descending)
    results_df = results_df.sort_values(by=['Priority', 'CurrentPrice'], ascending=[True, False])

    # Drop the priority column before saving
    results_df.drop(columns=['Priority'], inplace=True)

    # print("최종 데이터프레임 확인:")
    # print(results_df.columns)
    # print(results_df.tail())      


    # Save the sorted results to the output CSV
    results_df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"Analysis saved to {output_path}")


# 실행
input_folder = os.path.join(os.getcwd(), "korea_stocks_data_parts")
output_path = os.path.join(os.getcwd(), "korea_analysis_combined.csv")
analyze_stocks_with_combined_logic(input_folder, output_path)