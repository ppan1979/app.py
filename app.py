import streamlit as st
import yfinance as yf

# 設定網頁標題與移動端優化
st.set_page_config(page_title="股息估值APP", layout="centered")

st.title("💰 股息投資估值工具")
st.caption("適合手機操作的投資分析介面")

# --- 1. 輸入區（直接在主頁面，方便手機操作） ---
market_type = st.radio("選擇市場", ["美股 (US)", "台股 (TW)"], horizontal=True)

# 使用 columns 讓輸入框和按鈕並排
col_input, col_btn = st.columns([3, 1])
with col_input:
    ticker_input = st.text_input("輸入股票代碼", value="KO", placeholder="例如: 2330 或 AAPL").upper()
with col_btn:
    st.write(" ") # 調整對齊
    analyze_btn = st.button("分析", use_container_width=True)

# 處理代碼
full_ticker = f"{ticker_input}.TW" if market_type == "台股 (TW)" else ticker_input

# --- 2. 主要分析邏輯 ---
if analyze_btn:
    with st.spinner('計算中...'):
        try:
            stock = yf.Ticker(full_ticker)
            # 獲取價格與股息
            current_price = stock.fast_info['last_price']
            div_history = stock.dividends

            if div_history.empty:
                st.warning("⚠️ 找不到股息紀錄")
            else:
                last_year_div = div_history.last('365D').sum()
                div_yield = (last_year_div / current_price) * 100

                # 顯示核心數據卡片
                st.metric("目前股價", f"${current_price:.2f}")
                
                c1, c2 = st.columns(2)
                c1.metric("目前殖利率", f"{div_yield:.2f}%")
                
                # 簡單計算5年成長率
                div_5y = div_history.last('1825D')
                growth = ((div_5y.iloc[-1] / div_5y.iloc[0]) ** (1/5) - 1) * 100 if len(div_5y) > 1 else 0
                c2.metric("股息成長率", f"{growth:.1f}%")

                st.divider()

                # --- 3. 估值調整區（針對手機優化滑桿） ---
                st.subheader("⚖️ 估值調整")
                r = st.slider("期望回報率 (%)", 5.0, 12.0, 8.0) / 100
                g = st.slider("預估成長率 (%)", 0.0, 6.0, 3.0) / 100

                if r > g:
                    fair_price = (last_year_div * (1 + g)) / (r - g)
                    st.info(f"💡 預估合理價： **${fair_price:.2f}**")
                    
                    if current_price < fair_price:
                        st.success(f"🔥 股價低於合理價 (約打 {current_price/fair_price:.1f} 折)")
                    else:
                        st.warning("💎 目前股價略高於估值")
                
        except Exception as e:
            st.error("代碼錯誤或資料庫連線中斷")

# 頁尾說明
st.caption("註：本工具僅供參考，投資前請審慎評估風險。")
