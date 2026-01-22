import streamlit as st
import pandas as pd
import plotly.express as px

# ==========================================
# 🎨 [설정] 페이지 기본 세팅 (아이언맨 테마)
# testing 
# ==========================================
st.set_page_config(
    page_title="Chart Radar V13",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 엑셀 파일 불러오기 함수
@st.cache_data # 데이터를 캐시에 저장해서 속도 빠르게!
def load_data():
    file_name = "ChartRadar_V12_AI.xlsx" # V12가 만든 파일
    try:
        df_stock = pd.read_excel(file_name, sheet_name='주식_랭킹')
        df_etf = pd.read_excel(file_name, sheet_name='ETF_랭킹')
        return df_stock, df_etf
    except FileNotFoundError:
        return None, None

# ==========================================
# 🖥️ [화면] 사이드바 (설정 메뉴)
# ==========================================
st.sidebar.title("📡 레이더 통제실")
st.sidebar.markdown("---")
view_option = st.sidebar.radio("보고 싶은 항목", ["🦁 주식 (공격수)", "🐢 ETF (수비수)"])
min_prob = st.sidebar.slider("🔮 AI 확률 필터 (최소)", 0, 100, 50)

st.sidebar.markdown("---")
st.sidebar.info("마지막 분석: 2026-01-21") # 나중엔 이것도 자동으로!

# ==========================================
# 🖥️ [화면] 메인 대시보드
# ==========================================
st.title("📡 차트 레이더 V13.0 Platform")
st.markdown("### :boom: AI가 찾아낸 급등 유망주 현황판")

# 데이터 로드
df_stock, df_etf = load_data()

if df_stock is None:
    st.error("🚨 데이터 파일('ChartRadar_V12_AI.xlsx')이 없습니다! 먼저 분석 코드를 실행해주세요.")
else:
    # 선택에 따른 데이터 세팅
    if "주식" in view_option:
        target_df = df_stock
        color_theme = "Reds" # 주식은 빨강
        icon = "🦁"
    else:
        target_df = df_etf
        color_theme = "Blues" # ETF는 파랑
        icon = "🐢"

    # 필터링 (사이드바 슬라이더 적용)
    target_df = target_df[target_df['AI확률'] >= min_prob]

    # 📊 [섹션 1] 핵심 지표 (KPI) 보여주기
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label=f"{icon} 포착된 종목", value=f"{len(target_df)}개")
    with col2:
        if len(target_df) > 0:
            avg_ai = target_df['AI확률'].mean()
            st.metric(label="🔮 평균 AI 승률", value=f"{avg_ai:.1f}%")
        else:
             st.metric(label="🔮 평균 AI 승률", value="0%")
    with col3:
        st.metric(label="💰 목표 수익률", value="+10%")
    with col4:
        st.metric(label="🛡️ 손절 라인", value="-5%")

    st.markdown("---")

    # 📊 [섹션 2] 데이터 테이블 & 차트
    col_main, col_chart = st.columns([1.5, 1]) # 왼쪽이 좀 더 넓게

    with col_main:
        st.subheader(f"{icon} 종목 리스트 (AI 확률순)")
        # 보기 좋게 컬럼 정리
        display_df = target_df[['종목명', '현재가', '이격도', 'AI확률', 'RSI', '코드']].sort_values(by='AI확률', ascending=False)
        
        # 데이터프레임 예쁘게 출력
        st.dataframe(
            display_df,
            column_config={
                "AI확률": st.column_config.ProgressColumn(
                    "AI 승률",
                    format="%.1f%%",
                    min_value=0,
                    max_value=100,
                ),
                "이격도": st.column_config.NumberColumn(
                    "이격도",
                    format="%.2f%%"
                )
            },
            hide_index=True,
            use_container_width=True
        )

    with col_chart:
        st.subheader("📈 AI 확률 분포")
        if len(target_df) > 0:
            fig = px.scatter(
                target_df, 
                x="이격도", 
                y="AI확률", 
                size="현재가", 
                color="AI확률",
                hover_name="종목명",
                color_continuous_scale=color_theme,
                title="이격도 vs AI확률 (원이 클수록 비싼 주식)"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("조건에 맞는 종목이 없습니다.")

    # 📊 [섹션 3] 개별 종목 상세 보기 (탭)
    st.markdown("---")
    st.subheader("🔍 개별 종목 정밀 분석")
    
    if len(target_df) > 0:
        selected_stock = st.selectbox("종목을 선택하세요", target_df['종목명'])
        
        # 선택한 종목 정보 가져오기
        stock_info = target_df[target_df['종목명'] == selected_stock].iloc[0]
        
        c1, c2, c3 = st.columns(3)
        c1.info(f"**현재가**: {stock_info['현재가']:,}원")
        c2.success(f"**AI 예측**: {stock_info['AI확률']}% 상승 확률")
        
        rsi_val = stock_info['RSI']
        if rsi_val < 40:
            c3.warning(f"**RSI**: {rsi_val} (과매도 - 반등 임박?)")
        elif rsi_val > 70:
            c3.error(f"**RSI**: {rsi_val} (과매수 - 조심!)")
        else:
            c3.info(f"**RSI**: {rsi_val} (안정적)")
            
        # 네이버 금융 링크 버튼
        st.link_button(f"👉 {selected_stock} 네이버 증권 바로가기", f"https://finance.naver.com/item/main.naver?code={stock_info['코드']}")