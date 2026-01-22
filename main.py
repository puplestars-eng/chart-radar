import streamlit as st
import pandas as pd
import altair as alt
import datetime
import os

# 1. 페이지 기본 설정
st.set_page_config(page_title="Chart Radar V14.5", layout="wide")

st.title("🚀 차트 레이더 V14.5 Dashboard")

# 2. 데이터 불러오기 함수
def load_data():
    if os.path.exists('latest_analysis.xlsx'):
        df = pd.read_excel('latest_analysis.xlsx')
        return df
    return None

df = load_data()

if df is None:
    st.error("아직 데이터가 없습니다. GitHub Actions를 실행해주세요.")
else:
    # 3. 날짜 표시 (파일이 생성된 날짜)
    file_time = datetime.datetime.fromtimestamp(os.path.getmtime('latest_analysis.xlsx'))
    st.caption(f"📅 데이터 업데이트: {file_time.strftime('%Y-%m-%d %H:%M:%S')} (한국 시간 기준)")
    
    # 4. 데이터 분리 (ETF vs 일반 주식)
    # 이름에 'TIGER'나 'KODEX'가 들어가면 ETF로 분류
    df['type'] = df['name'].apply(lambda x: 'ETF' if 'TIGER' in x or 'KODEX' in x else 'Stock')
    
    etf_df = df[df['type'] == 'ETF']
    stock_df = df[df['type'] == 'Stock']
    
    # 5. 메인 탭 생성
    tab1, tab2, tab3 = st.tabs(["🇰🇷 국내 주식 Top 30", "🐢 ETF 섹터", "🔍 종목 상세 해부"])
    
    # --- [탭 1] 국내 주식 ---
    with tab1:
        st.subheader(f"🔥 발굴된 유망 주식 ({len(stock_df)}개)")
        if not stock_df.empty:
            # 버블 차트
            chart = alt.Chart(stock_df).mark_circle(size=60).encode(
                x=alt.X('rsi', title='RSI (심리도)', scale=alt.Scale(domain=[20, 80])),
                y=alt.Y('final_score', title='AI 종합 점수'),
                color=alt.Color('final_score', scale=alt.Scale(scheme='turbo')),
                size='price',
                tooltip=['name', 'price', 'final_score', 'rsi']
            ).interactive()
            st.altair_chart(chart, use_container_width=True)
            
            # 랭킹 표 (스타일링 적용)
            st.dataframe(
                stock_df[['name', 'price', 'final_score', 'rsi', 'disparity', 'news_score']]
                .sort_values(by='final_score', ascending=False)
                .style.background_gradient(subset=['final_score'], cmap='Reds')
                .format({'price': '{:,}원'}) # 가격 쉼표 표시
            )
        else:
            st.info("조건에 맞는 주식이 없습니다.")

    # --- [탭 2] ETF ---
    with tab2:
        st.subheader(f"🛡️ 안정적인 ETF ({len(etf_df)}개)")
        if not etf_df.empty:
            st.dataframe(
                etf_df[['name', 'price', 'final_score', 'rsi']]
                .sort_values(by='final_score', ascending=False)
                .style.background_gradient(subset=['final_score'], cmap='Blues')
                .format({'price': '{:,}원'})
            )
        else:
            st.info("조건에 맞는 ETF가 없습니다.")

    # --- [탭 3] 상세 분석 (여기가 대장님이 원하시던 기능!) ---
    with tab3:
        st.subheader("🕵️‍♂️ 종목 정밀 분석기")
        
        # 선택 상자
        selected_stock = st.selectbox("분석할 종목을 선택하세요", df['name'].unique())
        
        # 선택된 종목 데이터 가져오기
        row = df[df['name'] == selected_stock].iloc[0]
        
        # 3단 컬럼으로 정보 보여주기
        c1, c2, c3 = st.columns(3)
        c1.metric("현재 주가", f"{row['price']:,}원")
        c2.metric("AI 종합 점수", f"{row['final_score']}점")
        c3.metric("RSI (심리)", f"{row['rsi']}")
        
        st.divider()
        
        # 상세 코멘트 (AI처럼 말하기)
        st.markdown(f"### 🤖 AI 분석 리포트: **{selected_stock}**")
        
        # 뉴스 점수 해석
        if row['news_score'] > 0:
            st.success(f"📰 호재 뉴스 발견! (+{row['news_score']}점) - 긍정적인 기사가 포착되었습니다.")
        else:
            st.warning("📰 특별한 뉴스는 없습니다. (0점) - 조용한 상태입니다.")
            
        # 기술적 분석 해석
        if row['rsi'] < 30:
            st.error("📉 과매도 구간! - 너무 많이 떨어졌습니다. 반등 기회입니다.")
        elif row['rsi'] > 70:
            st.error("📈 과매수 구간! - 너무 올랐습니다. 조정 조심하세요.")
        else:
            st.info("➖ RSI 중립 구간 - 안정적인 흐름입니다.")
            
        # 이격도 해석
        if row['disparity'] < 98:
            st.success("💰 눌림목 포착! - 이동평균선 아래에 있어 가격 메리트가 있습니다.")
