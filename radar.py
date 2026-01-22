import FinanceDataReader as fdr
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
import yfinance as yf
import time
import os

# -----------------------------------------------------------
# [V14 기능] 미국 시장 분위기 파악 (Global Sentiment)
# -----------------------------------------------------------
def get_us_market_sentiment():
    """
    미국 3대 지수(S&P500, 나스닥, 반도체)를 조회해서 시장 분위기 점수를 반환합니다.
    """
    try:
        # S&P500, 나스닥, 필라델피아반도체
        tickers = ['^GSPC', '^IXIC', '^SOX'] 
        data = yf.download(tickers, period='5d', progress=False)['Close']
        
        market_score = 0
        status_msg = "미국 시장: 보합세 (영향 없음)"
        
        # 어제 대비 등락률 평균 계산
        pct_change = data.pct_change().iloc[-1].mean() * 100
        
        if pct_change < -1.5:
            market_score = -20
            status_msg = f"🚨 미국 폭락 ({pct_change:.2f}%) -> 전체 매수 점수 차감!"
        elif pct_change < -0.5:
            market_score = -10
            status_msg = f"📉 미국 하락 ({pct_change:.2f}%) -> 보수적 접근 필요"
        elif pct_change > 1.0:
            market_score = +10
            status_msg = f"🔥 미국 불장 ({pct_change:.2f}%) -> 적극 매수 추천"
            
        return market_score, status_msg
    except Exception as e:
        print(f"미국 지수 조회 실패: {e}")
        return 0, "미국 시장 데이터 조회 실패"

# -----------------------------------------------------------
# [V14 기능] 뉴스 크롤링 & 광고 필터 (Clean Filter)
# -----------------------------------------------------------
def get_news_score(code):
    """
    네이버 금융에서 뉴스를 가져와 광고를 거르고 호재를 찾습니다.
    """
    try:
        url = f"https://finance.naver.com/item/news_news.nhn?code={code}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        titles = soup.select('.title')
        
        news_score = 0
        clean_news_count = 0
        
        # 🚫 블랙리스트 (거를 단어들)
        blacklist = ['특징주', '관련주', '무료', '카톡', '리딩', '단독', '속보', '테마', '추천']
        # ✅ 화이트리스트 (점수 줄 단어들)
        whitelist = ['수주', '계약', '체결', '공급', '개발', '특허', '실적', '흑자', '배당']

        for title in titles[:5]: # 최신 뉴스 5개만 분석
            text = title.get_text().strip()
            
            # 1. 광고/찌라시 필터링
            is_spam = False
            for bad_word in blacklist:
                if bad_word in text:
                    is_spam = True
                    break
            
            if is_spam:
                continue # 쓰레기 뉴스는 무시하고 다음으로 넘어감
            
            clean_news_count += 1
            
            # 2. 호재 키워드 점수 부여
            for good_word in whitelist:
                if good_word in text:
                    news_score += 5 # 호재 하나당 +5점
        
        # 뉴스가 너무 없으면 0점, 호재가 많으면 최대 20점까지
        return min(news_score, 20)
        
    except Exception as e:
        return 0

# -----------------------------------------------------------
# 기술적 분석 지표 계산 (기존 V13 기능 유지)
# -----------------------------------------------------------
def get_technical_indicators(df):
    # RSI 계산
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # 이동평균선
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    
    # 볼린저밴드
    df['std'] = df['Close'].rolling(window=20).std()
    df['upper'] = df['MA20'] + (df['std'] * 2)
    df['lower'] = df['MA20'] - (df['std'] * 2)
    
    return df

# -----------------------------------------------------------
# 메인 분석 로직 (V14 업데이트)
# -----------------------------------------------------------
def analyze_stock(code):
    try:
        df = fdr.DataReader(code, '2025-01-01') # 데이터 기간 충분히 확보
        if len(df) < 60:
            return None
            
        df = get_technical_indicators(df)
        last_row = df.iloc[-1]
        
        # 1. 기술적 점수 (기존)
        tech_score = 0
        if last_row['RSI'] < 40: tech_score += 30 # 과매도 구간 (매수 기회)
        elif last_row['RSI'] > 70: tech_score -= 20 # 과매수 구간 (위험)
        
        if last_row['Close'] > last_row['MA20']: tech_score += 20 # 추세 상승
        
        # 골든크로스 패턴 (최근 3일 내 발생 여부)
        recent_df = df.iloc[-3:]
        if (recent_df['MA20'].iloc[-2] < recent_df['MA60'].iloc[-2]) and \
           (recent_df['MA20'].iloc[-1] > recent_df['MA60'].iloc[-1]):
            tech_score += 30 # 강력한 매수 신호
            
        # 2. 뉴스 점수 (신규 V14)
        news_score = get_news_score(code)
        
        # 3. 최종 점수 합산
        final_score = tech_score + news_score
        
        return {
            'code': code,
            'price': int(last_row['Close']),
            'rsi': round(last_row['RSI'], 1),
            'tech_score': tech_score,
            'news_score': news_score,
            'final_score': final_score
        }
        
    except Exception as e:
        return None

# 실행 부분
if __name__ == "__main__":
    print("🚀 차트 레이더 V14 가동 시작...")
    
    # 1. 미국 시장 분위기 먼저 파악
    us_score, us_msg = get_us_market_sentiment()
    print(f"\n{us_msg}")
    print(f"-> 글로벌 보정 점수: {us_score}점 적용\n")
    
    # 분석할 종목 리스트 (예시: 시총 상위 + 관심 종목)
    # 실제로는 KRX 전체를 돌리거나 리스트를 늘려야 함
    codes = [
        '005930', '000660', '035420', '035720', '005380', # 대형주
        '000270', '051910', '006400', '005490', '036570'  # 2차전지, 게임 등
    ]
    
    results = []
    
    for code in codes:
        result = analyze_stock(code)
        if result:
            # 글로벌 점수 반영
            result['final_score'] += us_score
            result['us_impact'] = us_score
            
            # 60점 이상인 종목만 추천
            if result['final_score'] >= 60:
                results.append(result)
                print(f"✅ 포착: {code} | 점수: {result['final_score']} (뉴스점수: {result['news_score']})")
    
    # 엑셀 저장
    if results:
        res_df = pd.DataFrame(results)
        res_df.to_excel('ChartRadar_V14_Analysis.xlsx', index=False)
        print(f"\n🎉 분석 완료! {len(results)}개 유망 종목 발굴 성공.")
    else:
        print("\n💨 살만한 종목이 없습니다. (시장 관망 추천)")
