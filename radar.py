import FinanceDataReader as fdr
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
import yfinance as yf
import time
import os

# -----------------------------------------------------------
# 1. 텔레그램 전송
# -----------------------------------------------------------
def send_telegram_message(message):
    try:
        token = os.environ.get('BOT_TOKEN')
        chat_id = os.environ.get('CHAT_ID')
        if token and chat_id:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            data = {'chat_id': chat_id, 'text': message}
            requests.post(url, data=data)
    except:
        pass

# -----------------------------------------------------------
# 2. 미국 시장 분위기 (V14 핵심)
# -----------------------------------------------------------
def get_us_market_sentiment():
    try:
        tickers = ['^GSPC', '^IXIC', '^SOX'] 
        data = yf.download(tickers, period='5d', progress=False)['Close']
        if len(data) < 2: return 0, "미국 데이터 부족"

        pct_change = data.pct_change().iloc[-1].mean() * 100
        
        market_score = 0
        msg = "미국 시장: 보합세 (-)"
        
        if pct_change < -1.5:
            market_score = -20
            msg = f"🚨 미국 폭락 ({pct_change:.2f}%) -> 점수 차감!"
        elif pct_change < -0.5:
            market_score = -10
            msg = f"📉 미국 하락 ({pct_change:.2f}%) -> 보수적 접근"
        elif pct_change > 1.0:
            market_score = +10
            msg = f"🔥 미국 불장 ({pct_change:.2f}%) -> 적극 매수"
            
        return market_score, msg
    except:
        return 0, "미국 지수 조회 실패"

# -----------------------------------------------------------
# 3. 뉴스 점수 (광고 필터링)
# -----------------------------------------------------------
def get_news_score(code):
    try:
        url = f"https://finance.naver.com/item/news_news.nhn?code={code}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        titles = soup.select('.title')
        score = 0
        
        bad_words = ['특징주', '관련주', '무료', '카톡', '단독', '속보']
        good_words = ['수주', '계약', '체결', '공급', '실적', '배당', '자사주']

        for title in titles[:5]: 
            text = title.get_text().strip()
            if any(bad in text for bad in bad_words): continue
            if any(good in text for good in good_words): score += 5
        
        return min(score, 20)
    except:
        return 0

# -----------------------------------------------------------
# 4. 종목 분석 엔진 (기술적 분석)
# -----------------------------------------------------------
def analyze_stock(code, name):
    try:
        df = fdr.DataReader(code, '2025-01-01')
        if len(df) < 60: return None
            
        # RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        # 이격도 & 이평선
        ma20 = df['Close'].rolling(window=20).mean()
        last_close = df['Close'].iloc[-1]
        last_ma20 = ma20.iloc[-1]
        disparity = (last_close / last_ma20) * 100
        
        cur_rsi = rsi.iloc[-1]
        
        # 기술적 점수 계산
        tech_score = 0
        if cur_rsi < 40: tech_score += 30
        elif cur_rsi > 70: tech_score -= 20
        
        if last_close > last_ma20: tech_score += 20
        if disparity < 98: tech_score += 10 # 눌림목
        
        # 뉴스 점수 추가
        news_score = get_news_score(code)
        
        return {
            'code': code,
            'name': name,
            'price': int(last_close),
            'rsi': round(cur_rsi, 1),
            'disparity': round(disparity, 1),
            'tech_score': tech_score,
            'news_score': news_score,
            'final_score': tech_score + news_score
        }
    except:
        return None

# -----------------------------------------------------------
# 메인 실행
# -----------------------------------------------------------
if __name__ == "__main__":
    print("🚀 차트 레이더 V14 (Full Version) 가동...")
    us_score, us_msg = get_us_market_sentiment()
    
    results = []
    
    # 분석 대상 1: 코스피 시총 상위 50개 (대장주)
    kospi = fdr.StockListing('KOSPI')
    top50 = kospi.head(50)[['Code', 'Name']].values.tolist()
    
    # 분석 대상 2: 주요 ETF (2차전지, 반도체, 미국지수)
    etfs = [
        ['360750', 'TIGER 미국S&P500'],
        ['305540', 'TIGER 2차전지테마'],
        ['371460', 'TIGER 차이나전기차SOLACTIVE'],
        ['091160', 'KODEX 반도체'],
        ['133690', 'TIGER 미국나스닥100']
    ]
    
    target_list = top50 + etfs # 합체!

    for code, name in target_list:
        res = analyze_stock(code, name)
        if res:
            res['final_score'] += us_score # 글로벌 점수 반영
            res['us_impact'] = us_score
            
            # 조건: 점수 50점 이상인 녀석들만
            if res['final_score'] >= 50:
                results.append(res)
    
    # 결과 저장
    if results:
        df = pd.DataFrame(results)
    else:
        df = pd.DataFrame({'name': ['없음'], 'final_score': [0], 'price': [0]})
        
    df.to_excel('latest_analysis.xlsx', index=False)
    
    # 텔레그램 보고
    msg = f"🚀 [차트 레이더 V14] 통합 리포트\n\n{us_msg}\n\n"
    if results:
        df = df.sort_values(by='final_score', ascending=False)
        top3 = df.head(3)
        for _, row in top3.iterrows():
            msg += f"⭐ {row['name']} : {row['final_score']}점\n(현재가: {row['price']:,}원 / RSI: {row['rsi']})\n\n"
        msg += f"🔥 총 {len(results)}개 유망 종목 발굴!"
    else:
        msg += "💨 푹 쉬세요. 살만한 게 없습니다."
        
    send_telegram_message(msg)
