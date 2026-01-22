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
# 4. 종목 분석 엔진
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
        if disparity < 98: tech_score += 10 
        
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
    print("🚀 차트 레이더 V14.5 (Extended) 가동...")
    us_score, us_msg = get_us_market_sentiment()
    
    results = []
    
    # 1. 코스피 시총 상위 50개
    kospi = fdr.StockListing('KOSPI')
    top50 = kospi.head(50)[['Code', 'Name']].values.tolist()
    
    # 2. ETF 10선 (확장판!)
    etfs = [
        ['360750', 'TIGER 미국S&P500'],        # 미국 대표
        ['133690', 'TIGER 미국나스닥100'],       # 미국 기술
        ['305540', 'TIGER 2차전지테마'],         # 배터리
        ['091160', 'KODEX 반도체'],             # 반도체
        ['371460', 'TIGER 차이나전기차SOLACTIVE'], # 중국 전기차
        ['069500', 'KODEX 200'],               # 한국 시장 대표
        ['292150', 'TIGER TOP10'],             # 한국 우량주 10개
        ['132030', 'KODEX 골드선물(H)'],        # 금 (안전 자산)
        ['143850', 'TIGER 헬스케어'],           # 바이오
        ['091170', 'KODEX 은행']                # 금융/배당
    ]
    
    target_list = top50 + etfs 

    print(f"총 {len(target_list)}개 종목 분석 시작...")

    for code, name in target_list:
        res = analyze_stock(code, name)
        if res:
            res['final_score'] += us_score 
            res['us_impact'] = us_score
            results.append(res)
    
    # 상위 30개 + ETF는 점수 낮아도 무조건 포함시키는 로직으로 변경
    if results:
        # ETF만 따로 빼서 무조건 살리기
        etf_results = [r for r in results if 'TIGER' in r['name'] or 'KODEX' in r['name']]
        stock_results = [r for r in results if r not in etf_results]
        
        # 주식은 점수순 정렬해서 상위 25개만
        stock_results.sort(key=lambda x: x['final_score'], reverse=True)
        final_results = stock_results[:25] + etf_results # 합체!
        
        df = pd.DataFrame(final_results)
        df.to_excel('latest_analysis.xlsx', index=False)
        print(f"✅ 분석 완료! 총 {len(final_results)}개 저장.")
        
        # 텔레그램 보고
        msg = f"🚀 [차트 레이더 V14.5] ETF 확장판\n\n{us_msg}\n\n"
        # ETF 1등 보여주기
        if etf_results:
            best_etf = max(etf_results, key=lambda x:x['final_score'])
            msg += f"🐢 추천 ETF: {best_etf['name']} ({best_etf['final_score']}점)\n"
            
        send_telegram_message(msg)
        
    else:
        df = pd.DataFrame({'name': ['데이터없음'], 'final_score': [0], 'price': [0], 'rsi': [0]})
        df.to_excel('latest_analysis.xlsx', index=False)
        send_telegram_message("❌ 데이터 수집 실패")
