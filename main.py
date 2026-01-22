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
    
    df['type'] = df['name'].apply(lambda x: 'ETF' if 'TIGER' in x or 'KODEX' in x else 'Stock')
    
    tab1, tab2, tab3 = st.tabs(["🇰🇷 국내 주식", "🐢 ETF 섹터", "🔍 종목 상세 해부"])
    
    with tab1:
        st.subheader("📊 AI 확률 분포 (가격이 낮고 점수가 높을수록 기회)")
        # 툴팁 및 축 이름 한글화
        chart = alt.Chart(df[df['type']=='Stock']).mark_circle(size=100).encode(
            x=alt.X('rsi', title='RSI 점수 (0~100)', scale=alt.Scale(domain=[10, 90])),
            y=alt.Y('final_score', title='AI 예측 점수 (0~100)'),
            color=alt.Color('final_score', scale=alt.Scale(scheme='turbo'), title="예측 점수"),
            size=alt.Size('price', title="주가"),
            tooltip=[
                alt.Tooltip('name', title='종목'),
                alt.Tooltip('price', title='가격', format=','),
                alt.Tooltip('final_score', title='AI 예측 점수'),
                alt.Tooltip('rsi', title='RSI 점수'),
                alt.Tooltip('news_score', title='호재 점수'),
                alt.Tooltip('disparity', title='이격도')
            ]
        ).interactive()
        st.altair_chart(chart, use_container_width=True)
        
        # 표 항목 한글화
        display_df = df[df['type']=='Stock'][['name', 'price', 'final_score', 'rsi', 'disparity', 'news_score']]
        display_df.columns = ['종목', '가격', 'AI 예측 점수(0~100)', 'RSI 점수(0~100)', '이격도(80~120)', '호재 점수(0~20)']
        
        st.dataframe(
            display_df.sort_values(by='AI 예측 점수(0~100)', ascending=False)
            .style.background_gradient(subset=['AI 예측 점수(0~100)'], cmap='Reds')
            .format({'가격': '{:,}원'})
        )

    with tab3:
        selected_stock = st.selectbox("분석할 종목 선택", df['name'].unique())
        row = df[df['name'] == selected_stock].iloc[0]
        
        c1, c2, c3 = st.columns(3)
        c1.metric("현재 주가", f"{row['price']:,}원")
        c2.metric("AI 예측 점수", f"{row['final_score']}점 / 100")
        c3.metric("RSI 점수", f"{row['rsi']} / 100")
        
        st.info(f"💡 **분석 가이드**: 예측 점수가 **70점** 이상이면 매수 검토, RSI가 **30** 이하면 과매도(기회), 이격도가 **100** 아래면 저평가 상태입니다.")
