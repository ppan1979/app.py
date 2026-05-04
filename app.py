import streamlit as st
import yfinance as yf
import pandas as pd

# 設定網頁標題與移動端優化
st.set_page_config(page_title="股息估值APP", layout="centered")

st.title("💰 股息投資估值工具")
st.caption("適合手機操作的投資分析介面 (穩定版)")

# --- 1. 輸入區 ---
market_type = st.radio("選擇市場", ["美股 (US)", "台股 (TW)"], horizontal=True)

col_input, col_btn = st.columns([3, 1])
with col_input:
    ticker_input = st.text_input("輸入股票代碼", value="KO", placeholder="例如: 2330 或 AAPL").upper().strip()
with col_btn:
    st.write(" ") # 調整對齊
    analyze_btn = st.button("分析", use_container_width=True)

# 處理代碼格式
full_ticker = f"{ticker_input}.TW" if market_type == "台股 (TW)" else ticker_input
currency_symbol = "NT$" if market_type == "台股 (TW)" else "$"

# --- 2. 主要分析邏輯 ---
if analyze_btn:
    with st.spinner('正在從 Yahoo Finance 抓取資料...'):
        try:
            stock = yf.Ticker(full_ticker)
            
            # 使用 history 獲取最新價格，比 fast_info 更穩定
            hist = stock.history(period="5d")
            if hist.empty:
                st.error(f"❌ 找不到代碼 '{full_ticker}' 的資料，請確認輸入是否正確。")
                st.stop()
            
            current_price = hist['Close'].iloc[-1]
            
            # 獲取股息歷史
            div_history = stock.dividends

            if div_history.empty:
                st.warning("⚠️ 該股票查無歷史股息紀錄，無法進行估值。")
            else:
                # 計算過去一年的總股息
                last_year_div = div_history.last('365D').sum()
                
                # 如果過去一年沒發股息，改抓最後一次發放的金額 * 頻率 (簡易處理)
                if last_year_div == 0:
                    last_year_div = div_history.iloc[-1] * 4 # 假設季配息
                
                div_yield = (last_year_div / current_price) * 100

                # --- 顯示數據卡片 ---
                st.metric("目前股價", f"{currency_symbol}{current_price:.2f}")
                
                c1, c2 = st.columns(2)
                c1.metric("目前殖利率", f"{div_yield:.2f}%")
                
                # 計算 5 年成長率 (CAGR)
                div_resampled = div_history.resample('YE').sum() # 按年加總
                if len(div_resampled) >= 5:
                    v_final = div_resampled.iloc[-1]
                    v_start = div_resampled.iloc[-5]
                    if v_start > 0:
                        growth = ((v_final / v_start) ** (1/5) - 1) * 100
                    else:
                        growth = 0
                else:
                    growth = 0
                c2.metric("5年股息成長率", f"{growth:.1f}%")

                st.divider()

                # --- 3. 估值調整區 ---
                st.subheader("⚖️ 估值調整 (高登模型)")
                r = st.slider("期望回報率 (%)", 5.0, 15.0, 8.0, step=0.5) / 100
                g = st.slider("預估永續成長率 (%)", 0.0, 8.0, 3.0, step=0.5) / 100

                if r > g:
                    # 高登模型公式：P = D1 / (r - g)
                    fair_price = (last_year_div * (1 + g)) / (r - g)
                    
                    st.info(f"💡 預估合理價： **{currency_symbol}{fair_price:.2f}**")
                    
                    # 顯示買入建議
                    diff_pct = ((fair_price - current_price) / fair_price) * 100
                    if current_price < fair_price:
                        st.success(f"🔥 股價低於合理價 (安全邊際: {diff_pct:.1f}%)")
                    else:
                        st.warning(f"💎 目前股價高於估值 (溢價: {abs(diff_pct):.1f}%)")
                else:
                    st.error("⚠️ 期望回報率必須大於成長率，否則無法計算合理價。")
                
        except Exception as e:
            st.error(f"發生非預期錯誤：{e}")
            st.info("建議：請嘗試 Reboot App 或稍後再試。")

# 頁尾說明
st.caption("---")
st.caption("註：數據來源為 Yahoo Finance。本工具僅供參考，不構成投資建議。")
