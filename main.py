import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="Chart Radar V14", layout="wide")

st.title("🚀 차트 레이더 V14.0 Pro")
st.markdown("### 🇺🇸 글로벌 지수 & 🇰🇷 국내 주식 통합 분석")

try:
    df = pd.read_excel('latest_analysis.xlsx')
    
    # 데이터가 없을 때 방어
    if len(df) == 1 and df.iloc[0]['name'] == '없음':
        st.warning("현재 포착된 추천 종목이 없습니다. (시장 관망)")
    else:
        # 1. 상단 지표
        col1, col2, col3 = st.columns(3)
        col1.metric("발굴된 종목", f"{len(df)}개")
        col2.metric("최고 점수", f"{df['final_score'].max()}점")
        col3.metric("평균 RSI", f"{round(df['rsi'].mean(), 1)}")
        
        # 2. 버블 차트 (이게 예전 그 차트입니다!)
        st.subheader("📊 AI 확률 분포 (가격이 쌀수록, 점수가 높을수록)")
        
        chart = alt.Chart(df).mark_circle(size=60).encode(
            x=alt.X('rsi', title='RSI (낮을수록 과매도)'),
            y=alt.Y('final_score', title='AI 종합 점수'),
            color=alt.Color('final_score', scale=alt.Scale(scheme='turbo')),
            size='price',
            tooltip=['name', 'price', 'final_score', 'rsi', 'news_score']
        ).interactive()
        
        st.altair_chart(chart, use_container_width=True)
        
        # 3. 상세 리스트
        st.subheader("🏆 추천 종목 랭킹")
        st.dataframe(
            df[['name', 'price', 'final_score', 'rsi', 'disparity', 'news_score']]
            .sort_values(by='final_score', ascending=False)
            .style.background_gradient(subset=['final_score'], cmap='Reds')
        )

except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
    st.info("아직 분석 리포트가 생성되지 않았을 수 있습니다. GitHub Actions를 실행해주세요.")
