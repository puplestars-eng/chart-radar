import FinanceDataReader as fdr
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
import yfinance as yf
import time
import os

# -----------------------------------------------------------
# 텔레그램 전송 기능 (부활!)
# -----------------------------------------------------------
def send_telegram_message(message):
    try:
        token = os.environ.get('BOT_TOKEN')
        chat_id = os.environ.get('CHAT_ID')
        
        if not token or not chat_id:
            print("❌ 텔레그램 토큰이 없습니다. 메시지를 못 보냅니다.")
            return

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {'chat_id': chat_id, 'text': message}
        requests.post(url, data=data)
        print("✅ 텔레그램 전송 완료")
    except Exception as e:
        print(f"텔레그램 전송 실패: {e}")

# -----------------------------------------------------------
# [V14 기능] 미국 시장 분위기 파악
# -----------------------------------------------------------
def get_us_market_sentiment():
    try:
        tickers = ['^GSPC', '^IXIC', '^SOX'] 
        data = yf.download(tickers, period='5d', progress=False)['Close']
        
        market_score = 0
        status_msg = "미국 시장: 보합세 (영향 없음)"
        
        # 데이터가 없거나 에러날 경우 방어
        if len(data) < 2:
            return 0, "미국 데이터 부족 (보합 가정)"

        pct_change = data.pct_change().iloc[-1].mean() * 100
        
        if pct_change < -1.5:
            market_score = -20
            status_msg = f"🚨 미국 폭락 ({pct_change:.2f}%) -> 점수 차감!"
        elif pct_change < -0.5:
            market_score = -10
            status_msg = f"📉 미국 하락 ({pct_change:.2f}%) -> 보수적 접근"
        elif pct_change > 1.0:
            market_score = +10
            status_msg = f"🔥 미국 불장 ({pct_change:.2f}%) -> 적극 매수"
            
        return market_score, status_msg
    except Exception as e:
        print(f"미국 지수 조회 실패: {e}")
        return 0, "미국 시장 조회 실패 (보합 가정)"

# -----------------------------------------------------------
# [V14 기능] 뉴스 크롤링 & 광고 필터
# -----------------------------------------------------------
def get_news_score(code):
    try:
        url = f"https://finance.naver.com/item/news_news.nhn?code={code}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        titles = soup.select('.title')
        news_score = 0
        
        blacklist = ['특징주', '관련주', '무료', '카톡', '단독', '속보']
        whitelist = ['수주', '계약', '체결', '공급', '실적', '배당']

        for title in titles[:5]: 
            text = title.get_text().strip()
            is_spam = False
            for bad in blacklist:
                if bad in text: is_spam = True
            if is_spam: continue
            
            for good in whitelist:
                if good in text: news_score += 5
        
        return min(news_score, 20)
    except:
        return 0

# -----------------------------------------------------------
# 메인 분석 로직
# -----------------------------------------------------------
def analyze_stock(code):
    try:
        df = fdr.DataReader(code, '2025-01-01')
        if len(df) < 60: return None
            
        # 보조지표
        df['MA20'] = df['Close'].rolling(window=20).mean()
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        last_row = df.iloc[-1]
        cur_rsi = last_row[rsi.name] if hasattr(rsi, 'name') else rsi.iloc[-1]
        
        tech_score = 0
        if cur_rsi < 40: tech_score += 30
        elif cur_rsi > 70: tech_score -= 20
        if last_row['Close'] > last_row['MA20']: tech_score += 20
        
        news_score = get_news_score(code)
        final_score = tech_score + news_score
        
        return {
            'code': code,
            'price': int(last_row['Close']),
            'rsi': round(cur_rsi, 1),
            'score': final_score,
            'news_score': news_score
        }
    except:
        return None

# -----------------------------------------------------------
# 실행 및 보고 (수정본)
# -----------------------------------------------------------
if __name__ == "__main__":
    print("🚀 차트 레이더 V14 가동 시작...")
    us_score, us_msg = get_us_market_sentiment()
    print(us_msg)
    
    # 분석 대상 종목 (테스트를 위해 몇 개 더 추가했습니다)
    codes = [
        '005930', '000660', '035420', '035720', '005380', 
        '000270', '051910', '006400', '005490', '036570',
        '003490', '032640', '086520', '011200', '010130' 
    ]
    results = []
    
    for code in codes:
        res = analyze_stock(code)
        if res:
            res['score'] += us_score # 글로벌 점수 반영
            # 기준 점수를 40점으로 낮춤 (테스트용)
            if res['score'] >= 40: 
                results.append(res)

    # 1. 엑셀 저장 (핵심 수정: 종목 없어도 무조건 파일 생성!)
    if results:
        df = pd.DataFrame(results)
    else:
        # 빈 파일이라도 만들어야 에러가 안 납니다
        df = pd.DataFrame({'code': ['-'], 'score': [0], 'msg': ['조건에 맞는 종목 없음']})
        
    df.to_excel('latest_analysis.xlsx', index=False)
    print("✅ 보고서 파일 생성 완료!")
    
    # 2. 텔레그램 전송
    message = f"🚀 [차트 레이더 V14] 글로벌 마켓 리포트\n\n{us_msg}\n\n"
    if results:
        top_stocks = sorted(results, key=lambda x: x['score'], reverse=True)[:3]
        for s in top_stocks:
            message += f"⭐ {s['code']} : {s['score']}점 (뉴스:{s['news_score']})\n"
    else:
        message += "💨 조건에 맞는 종목이 없습니다. (시장 관망 추천)"
        
    send_telegram_message(message)
