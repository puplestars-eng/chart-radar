import FinanceDataReader as fdr
import pandas as pd

# ==========================================
# ⚔️ [시가 vs 종가] 수익률 데스매치
# ==========================================
TEST_STOCKS = {
    '069500': 'KODEX 200',
    '122630': 'KODEX 레버리지',
    '000660': 'SK하이닉스',
}

# 전략 설정
TAKE_PROFIT_RATIO = 1.10   # 익절 +10%
STOP_LOSS_RATIO = 0.95     # 손절 -5%
MA_LONG = 240
MA_SHORT = 10

def run_backtest(code, name, mode='open'):
    df = fdr.DataReader(code, '2023-01-01')
    df['MA_Long'] = df['Close'].rolling(MA_LONG).mean()
    df['MA_Short'] = df['Close'].rolling(MA_SHORT).mean()
    
    cash = 10000000
    shares = 0
    entry_price = 0
    half_sold = False
    
    # mode='open' : 시가 매수 (공격적)
    # mode='close': 종가 매수 (안정적, 확인매매)

    for i in range(MA_LONG, len(df)-1):
        today = df.iloc[i]
        tomorrow = df.iloc[i+1]
        
        # 1. 매수
        if shares == 0:
            if today['Close'] > today['MA_Long']:
                disparity = today['Close'] / today['MA_Short']
                
                # 눌림목 조건 만족
                if 0.98 <= disparity <= 1.05:
                    
                    # 🔥 [승부처] 매수 타이밍 결정
                    buy_price = 0
                    
                    if mode == 'open':
                        # 시가 매수: 갭하락만 아니면 시초가에 지른다
                        if tomorrow['Open'] > today['Close'] * 0.98:
                            buy_price = tomorrow['Open']
                            
                    elif mode == 'close':
                        # 종가 매수: 장 끝날때(3시20분)까지 빨간불(양봉)인지 확인하고 산다
                        if tomorrow['Close'] > tomorrow['Open']: # 양봉 확인
                            buy_price = tomorrow['Close']
                    
                    if buy_price > 0:
                        shares = int(cash / buy_price)
                        cash -= shares * buy_price
                        entry_price = buy_price
                        half_sold = False

        # 2. 매도 (로직 동일)
        else:
            current_price = tomorrow['Close']
            if tomorrow['Low'] <= entry_price * STOP_LOSS_RATIO:
                sell_price = entry_price * STOP_LOSS_RATIO
                cash += shares * sell_price
                shares = 0
                continue

            if not half_sold and tomorrow['High'] >= entry_price * TAKE_PROFIT_RATIO:
                sell_price = entry_price * TAKE_PROFIT_RATIO
                sell_qty = int(shares / 2)
                cash += sell_qty * sell_price
                shares -= sell_qty
                half_sold = True
            
            if current_price < tomorrow['MA_Short']:
                sell_price = current_price
                cash += shares * sell_price
                shares = 0

    final_value = cash + (shares * df.iloc[-1]['Close'])
    return int(final_value)

print(f"🥊 [시가 vs 종가] 수익률 대결 (2023 ~ 현재)\n")

for code, name in TEST_STOCKS.items():
    res_open = run_backtest(code, name, mode='open')
    res_close = run_backtest(code, name, mode='close')
    
    roi_open = (res_open - 10000000)/10000000 * 100
    roi_close = (res_close - 10000000)/10000000 * 100
    
    print(f"[{name}]")
    print(f"  ☀️ 아침에 샀을 때 (시가): {roi_open:.2f}%")
    print(f"  🌙 보고 샀을 때 (종가):   {roi_close:.2f}%")
    
    diff = roi_close - roi_open
    if diff > 0:
        print(f"  👉 결론: '확인 매매(종가)'가 {diff:.2f}%p 더 이득! 🏆")
    else:
        print(f"  👉 결론: '아침 매매(시가)'가 {abs(diff):.2f}%p 더 이득! 🚀")
    print("-" * 40)