import streamlit as st
import pandas as pd
import altair as alt
import datetime
import os

st.set_page_config(page_title="Chart Radar V14.6", layout="wide")
st.title("🚀 차트 레이더 V14.6 Dashboard")

def load_data():
    if os.path.exists('latest_analysis.xlsx'):
        return pd.read_excel('latest_analysis.xlsx')
    return None

df = load_data()

if df is None:
    st.error("데이터가 없습니다. GitHub Actions를 실행해주세요.")
else:
    file_time = datetime.datetime.fromtimestamp(os.path.getmtime('latest_analysis.xlsx'))
    st.caption(f"📅 업데이트: {file_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # ETF와 주식 분류 (TIGER/KODEX 포함 여부)
    df['type'] = df['name'].apply(lambda x: 'ETF' if any(keyword in str(x) for keyword in ['TIGER', 'KODEX']) else 'Stock')
    
    tab1, tab2, tab3 = st.tabs(["🇰🇷 국내 주식", "🐢 ETF 섹터", "🔍 종목 상세 해부"])
    
    # --- [탭 1] 국내 주식 ---
    with tab1:
        stock_df = df[df['type'] == 'Stock']
        st.subheader(f"📊 주식 분석 현황 ({len(stock_df)}개)")
        
        chart = alt.Chart(stock_df).mark_circle(size=100).encode(
            x=alt.X('rsi', title='RSI 점수 (낮을수록 과매도)', scale=alt.Scale(domain=[10, 90])),
            y=alt.Y('final_score', title='AI 예측 점수 (높을수록 좋음)'),
            color=alt.Color('final_score', scale=alt.Scale(scheme='turbo')),
            tooltip=['name', 'price', 'final_score', 'rsi', 'disparity']
        ).interactive()
        st.altair_chart(chart, use_container_width=True)
        
        display_stock = stock_df[['name', 'price', 'final_score', 'rsi', 'disparity', 'news_score']]
        display_stock.columns = ['종목', '가격', 'AI 예측 점수', 'RSI 점수', '이격도', '호재 점수']
        st.dataframe(display_stock.sort_values(by='AI 예측 점수', ascending=False).style.background_gradient(cmap='Reds'))

    # --- [탭 2] ETF (복구 완료!) ---
    with tab2:
        etf_df = df[df['type'] == 'ETF']
        st.subheader(f"🛡️ 안정적인 ETF 10선 ({len(etf_df)}개)")
        
        if not etf_df.empty:
            display_etf = etf_df[['name', 'price', 'final_score', 'rsi', 'disparity']]
            display_etf.columns = ['ETF 명칭', '현재가', 'AI 예측 점수', 'RSI 점수', '이격도']
            
            st.dataframe(
                display_etf.sort_values(by='AI 예측 점수', ascending=False)
                .style.background_gradient(cmap='Blues')
                .format({'현재가': '{:,}원'})
            )
        else:
            st.warning("표시할 ETF 데이터가 없습니다. radar.py 분석을 다시 실행해 보세요.")

    # --- [탭 3] 상세 분석 ---
    with tab3:
        selected = st.selectbox("분석할 종목/ETF 선택", df['name'].unique())
        row = df[df['name'] == selected].iloc[0]
        
        c1, c2, c3 = st.columns(3)
        c1.metric("현재 가격", f"{row['price']:,}원")
        c2.metric("AI 예측 점수", f"{row['final_score']} / 100")
        c3.metric("RSI (심리도)", f"{row['rsi']}")
        
        st.divider()
        st.markdown(f"### 🤖 AI 분석 결과: **{selected}**")
        if row['final_score'] >= 60:
            st.success("✅ **매수 검토 가능**: 기술적 지표와 시장 상황이 긍정적입니다.")
        elif row['final_score'] >= 40:
            st.info("⚠️ **관망 필요**: 추세가 확인될 때까지 기다리는 것을 추천합니다.")
        else:
            st.error("🚨 **주의**: 하락 추세거나 고점일 확률이 높습니다.")
