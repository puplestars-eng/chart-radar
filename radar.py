import FinanceDataReader as fdr
import pandas as pd
import requests
from openpyxl.styles import Font
from sklearn.ensemble import RandomForestClassifier # AI 모델
from sklearn.model_selection import train_test_split

# ==========================================
# 👇 [설정] 텔레그램 정보 입력
# ==========================================
BOT_TOKEN = "8543838124:AAGE6vjqiFAmFeglh2nlGYCEFZiSfhiWLD4"
CHAT_ID = "8546696621"
# ==========================================

# --- [전략 설정] ---
MA_SHORT = 10
STOCK_MA_LONG = 240
ETF_MA_LONG = 60

ETF_MIN_AMOUNT = 50000000
STOCK_MIN_AMOUNT = 1000000000
STOCK_MIN_MARCAP = 300000000000
STOCK_VOL_SPIKE = 2.0

# 🚑 [ETF 자체 생산 공장]
CUSTOM_ETF_DICT = {
    '069500': 'KODEX 200', '102110': 'TIGER 200', '252670': 'KODEX 200선물인버스2X',
    '122630': 'KODEX 레버리지', '233740': 'KODEX 코스닥150레버리지', '251340': 'KODEX 코스닥150선물인버스',
    '305720': 'KODEX 2차전지산업', '360750': 'TIGER 미국S&P500', '379800': 'KODEX 미국S&P500TR',
    '364960': 'TIGER KRX2차전지K-뉴딜', '229200': 'KODEX 코스닥150', '133690': 'TIGER 미국나스닥100',
    '102780': 'KODEX 삼성그룹', '091160': 'KODEX 반도체', '305540': 'TIGER 2차전지테마',
    '148020': 'KBSTAR 200', '379810': 'KODEX 미국나스닥100TR', '453950': 'KODEX 2차전지핵심소재10Fn',
    '114800': 'KODEX 인버스', '278530': 'KODEX MSCI Korea TR', '278540': 'KODEX MSCI Korea TR',
    '310970': 'TIGER MSCI Korea TR', '139260': 'TIGER 200 IT', '143850': 'TIGER 미국S&P500선물(H)',
    '192090': 'TIGER 차이나CSI300', '292150': 'TIGER TOP10', '329750': 'TIGER 부동산인프라고배당',
    '261240': 'KODEX 미국달러선물', '371460': 'TIGER 차이나전기차SOLACTIVE', '091220': 'KODEX 헬스케어',
    '409820': 'KODEX 미국나스닥100레버리지(합성 H)',
}

def send_telegram_message(message):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {'chat_id': CHAT_ID, 'text': message}
        requests.post(url, data=data)
    except Exception: pass

def calculate_rsi(series, period=14):
    delta = series.diff(1)
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    rs = gain.rolling(window=period).mean() / loss.rolling(window=period).mean()
    return 100 - (100 / (1 + rs))

# 🧠 [AI 엔진] 내일 오를 확률 예측 (Random Forest)
def get_ai_prediction(df):
    try:
        # 데이터가 너무 적으면 학습 불가
        if len(df) < 100: return 0
        
        data = df.copy()
        
        # 1. 학습에 쓸 특징(Feature) 만들기
        # (과거의 패턴을 숫자로 정의)
        data['Change'] = data['Close'].pct_change() # 등락률
        data['MA5'] = data['Close'].rolling(5).mean()
        data['MA20'] = data['Close'].rolling(20).mean()
        data['RSI'] = calculate_rsi(data['Close'])
        data['Vol_Ratio'] = data['Volume'] / data['Volume'].rolling(5).mean() # 거래량 비율
        
        # NaN 제거 (지표 계산 초반부)
        data.dropna(inplace=True)
        
        # 2. 정답지(Label) 만들기: "다음 날 올랐니?" (1=상승, 0=하락)
        # shift(-1)은 다음 행의 데이터를 가져옴
        data['Target'] = (data['Close'].shift(-1) > data['Close']).astype(int)
        
        # 마지막 행은 내일 데이터가 없어서 정답을 모르니 학습에서 제외
        train_data = data.iloc[:-1]
        
        # 학습용 데이터셋 (X: 문제, y: 정답)
        features = ['Change', 'RSI', 'Vol_Ratio'] # AI에게 보여줄 힌트들
        X = train_data[features]
        y = train_data['Target']
        
        # 3. AI 모델 생성 및 학습
        # (n_estimators=100: 100명의 AI 심사위원이 투표함)
        model = RandomForestClassifier(n_estimators=100, min_samples_split=10, random_state=42)
        model.fit(X, y)
        
        # 4. 실전 문제 풀기 (오늘 데이터로 내일 예측)
        today_features = data.iloc[[-1]][features] # 오늘 자 데이터
        
        # 상승할 확률(%) 반환 (predict_proba -> [하락확률, 상승확률])
        prob = model.predict_proba(today_features)[0][1] * 100
        
        return round(prob, 1)

    except Exception:
        return 50.0 # 에러나면 반반

# 🏥 재무제표 확인
def check_financial_health(code):
    try:
        url = f"https://finance.naver.com/item/main.naver?code={code}"
        dfs = pd.read_html(url, encoding='cp949', header=0)
        fin_df = dfs[3] 
        if fin_df is None or len(fin_df) < 2: return True, "데이터없음"
        fin_df.columns = [c[0] if isinstance(c, tuple) else c for c in fin_df.columns]
        if '영업이익' not in fin_df.iloc[:, 0].values: return True, "확인불가"
        
        # 최근 확정 실적 (문자열 처리 강화)
        try:
            op_str = str(fin_df.set_index(fin_df.columns[0]).loc['영업이익'].iloc[1])
            # 쉼표 제거 등 숫자 변환
            operating_profit = int(pd.to_numeric(op_str, errors='coerce'))
            if operating_profit < 0: return False, f"영업적자"
        except: return True, "변환오류"

        return True, "우량기업"
    except: return True, "검사패스"

print(f"📡 [차트 레이더 V12.0] AI 오라클 가동 (확률 예측)")

# --- 데이터 준비 ---
print("   Step 1. 데이터 리스트 생성...")
try:
    df_kospi = fdr.StockListing('KOSPI')
    df_kosdaq = fdr.StockListing('KOSDAQ')
    df_stocks = pd.concat([df_kospi, df_kosdaq])
    cols = ['Code', 'Name', 'Close', 'Marcap', 'Amount']
    for c in cols:
        if c not in df_stocks.columns: df_stocks[c] = 0
    df_stocks = df_stocks[cols]
except:
    df_stocks = pd.DataFrame(columns=['Code', 'Name', 'Close', 'Marcap', 'Amount'])

etf_rows = []
for code, name in CUSTOM_ETF_DICT.items():
    etf_rows.append({'Code': code, 'Name': name, 'Close': 0, 'Marcap': 0, 'Amount': 0})
df_etfs = pd.DataFrame(etf_rows)
df_krx = pd.concat([df_stocks, df_etfs], ignore_index=True)
df_krx.drop_duplicates(subset=['Code'], keep='last', inplace=True)

def classify_type(row):
    code = str(row['Code'])
    if code in CUSTOM_ETF_DICT: return 'ETF'
    if row['Marcap'] >= STOCK_MIN_MARCAP: return '주식'
    return 'DROP'

df_krx['Type'] = df_krx.apply(classify_type, axis=1)
target_stocks = df_krx[df_krx['Type'] != 'DROP'].copy()

print(f"\n🔍 총 {len(target_stocks)}개 분석 및 AI 학습 시작...\n")

candidates = [] 

count = 0
total = len(target_stocks)

for idx, row in target_stocks.iterrows():
    code = str(row['Code'])
    name = row['Name']
    stock_type = row['Type']
    
    count += 1
    if count % 50 == 0: print(f"[{count}/{total}] 분석 중...", end='\r')

    try:
        df_day = fdr.DataReader(code, '2019-01-01')
        target_ma_long = STOCK_MA_LONG if stock_type == '주식' else ETF_MA_LONG
        
        if len(df_day) < target_ma_long + 10: continue
        if df_day['Volume'].iloc[-1] == 0: continue

        # 거래대금
        today_close = df_day['Close'].iloc[-1]
        today_amount = today_close * df_day['Volume'].iloc[-1]
        
        if stock_type == 'ETF':
             if code not in CUSTOM_ETF_DICT and today_amount < ETF_MIN_AMOUNT: continue
        elif stock_type == '주식':
            if today_amount < STOCK_MIN_AMOUNT: continue
            df_day['Vol_MA20'] = df_day['Volume'].rolling(20).mean()
            recent_20 = df_day.iloc[-20:]
            has_spike = (recent_20['Volume'] > recent_20['Vol_MA20'] * STOCK_VOL_SPIKE).any()
            if not has_spike: continue 

        # 추세선
        df_day['MA_Long'] = df_day['Close'].rolling(target_ma_long).mean()
        if df_day['Close'].iloc[-1] < df_day['MA_Long'].iloc[-1]: continue

        # 이격도
        df_day['MA_Short'] = df_day['Close'].rolling(MA_SHORT).mean()
        curr = df_day.iloc[-1]
        disparity = curr['Close'] / curr['MA_Short']
        
        upper_limit = 1.08 if stock_type == 'ETF' else 1.05
        lower_limit = 0.99 if stock_type == 'ETF' else 1.0
        
        if not (lower_limit <= disparity <= upper_limit): continue

        # RSI
        df_day['RSI'] = calculate_rsi(df_day['Close'])
        rsi = df_day['RSI'].iloc[-1]
        if rsi < 35: continue
        
        # --- 2차 심사: 재무제표 (주식만) ---
        if stock_type == '주식':
            is_healthy, reason = check_financial_health(code)
            if not is_healthy: continue

        # --- 🔥 3차 심사: AI 예측 (여기서 실행!) ---
        # 1차, 2차 다 통과한 녀석들만 AI가 정밀 분석합니다.
        ai_prob = get_ai_prediction(df_day)
        
        candidates.append({
            '종목명': name,
            '현재가': int(curr['Close']),
            '이격도': round(disparity * 100, 2),
            'RSI': round(rsi, 1),
            'AI확률': ai_prob, # 🔮 추가됨
            '구분': stock_type,
            '코드': code
        })

    except Exception:
        continue

print("\n" + "=" * 60)
print(f"🎉 V12.0 분석 종료! 총 {len(candidates)}개 종목 선별")
print("=" * 60)

if candidates:
    df_result = pd.DataFrame(candidates)
    
    # 정렬: 이격도 순 (원하면 AI확률 순으로 바꿔도 됨)
    df_stock = df_result[df_result['구분'] == '주식'].sort_values(by='이격도')
    df_etf = df_result[df_result['구분'] == 'ETF'].sort_values(by='이격도')
    
    file_name = "ChartRadar_V12_AI.xlsx"
    with pd.ExcelWriter(file_name, engine='openpyxl') as writer:
        df_stock.to_excel(writer, index=False, sheet_name='주식_랭킹')
        df_etf.to_excel(writer, index=False, sheet_name='ETF_랭킹')
        
        big_font = Font(name='맑은 고딕', size=14)
        for sheet_name in writer.sheets:
            worksheet = writer.sheets[sheet_name]
            for column_cells in worksheet.columns:
                col_letter = column_cells[0].column_letter 
                max_length = 0
                for cell in column_cells:
                    cell.font = big_font
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except: pass
                worksheet.column_dimensions[col_letter].width = max_length * 2.2
    
    print(f"📂 엑셀 저장 완료: '{file_name}'")

    msg = f"📡 [차트 레이더 V12.0] AI 오라클 예측\n"
    
    msg += f"🦁 [주식 Top 3] (총 {len(df_stock)}개)\n"
    for idx, row in df_stock.head(3).iterrows():
        msg += f"{row['종목명']} ({row['현재가']:,}원) / 이격 {row['이격도']}%\n"
        msg += f"   🔮 AI 상승확률: {row['AI확률']}%\n" # 메시지 추가
        
    msg += f"\n🐢 [ETF Top 3] (총 {len(df_etf)}개)\n"
    for idx, row in df_etf.head(3).iterrows():
        msg += f"{row['종목명']} ({row['현재가']:,}원) / 이격 {row['이격도']}%\n"
        msg += f"   🔮 AI 상승확률: {row['AI확률']}%\n"

    send_telegram_message(msg)
else:
    print("조건 만족 종목 없음")