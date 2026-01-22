import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Chart Radar V14", layout="wide")

st.title("🚀 차트 레이더 V14 Global")

# 데이터 파일 읽기
if os.path.exists('latest_analysis.xlsx'):
    df = pd.read_excel('latest_analysis.xlsx')
    
    # 1. 미국 시장 점수 추정 (1등 종목 점수 역산)
    st.info("데이터가 성공적으로 업데이트되었습니다!")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("발굴된 종목 수", f"{len(df)}개")
    with col2:
        top_score = df['score'].max()
        st.metric("최고 점수", f"{top_score}점")
        
    st.subheader("🏆 AI 추천 종목 랭킹")
    # 점수 높은 순 정렬
    df = df.sort_values(by='score', ascending=False)
    st.dataframe(df)
    
else:
    st.warning("아직 분석된 데이터가 없습니다. (GitHub Actions가 실행될 때까지 기다려주세요)")
