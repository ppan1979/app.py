import streamlit as st
import requests
import pandas as pd

# 設定網頁標題與移動端優化
st.set_page_config(page_title="全球股息估值工具", layout="centered")

# --- 自動配置 API Key ---
API_KEY = "WW8AGKVH1A1Z6B3R" 

st.title("💰 全球股息投資估值工具")
st.caption("數據來源：Alpha Vantage | 穩定版")

# --- 1. 使用者輸入區 ---
market = st.radio("選擇市場", ["台股 (TW)", "美股 (US)"], horizontal=True)

col1, col2 = st.columns([3, 1])
with col1:
    ticker_input = st.text_input("輸入股票代碼", value="2330" if market == "台股 (TW)" else "KO", placeholder="例如: 2330 或 AAPL").upper().strip()
with col2:
    st.write(" ")
    analyze_btn = st.button("分析", use_container_width=True, type="primary")

# 自動處理代碼格式
if market == "台股 (TW)" and ".TW" not in ticker_input:
    full_ticker = f"{ticker_input}.TW"
else:
    full_ticker = ticker_input

currency_symbol = "NT$" if ".TW" in full_ticker else "$"

# --- 2. 資料抓取函數 ---
def fetch_data(symbol):
    # 使用 TIME_SERIES_DAILY_ADJUSTED 獲取價格與股息
    url = f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol={symbol}&apikey={API_KEY}'
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if "Note" in data:
            return None, "API 請求太頻繁，請等一分鐘後再點一次。"
        if "Error Message" in data:
            return None, f"找不到代碼 '{symbol}'，如果是台股請確認格式為 2330.TW"
        if "Time Series (Daily)" not in data:
            return None, "資料庫暫時無回應，請稍後再試。"
            
        # 取得最新價格
        daily_series = data["Time Series (Daily)"]
        latest_day = list(daily_series.keys())[0]
        current_price = float(daily_series[latest_day]["4. close"])
        
        # 計算過去一年的總股息 (約 252 個交易日)
        total_dividend = 0.0
        dates = list(daily_series.keys())[:252]
        for d in dates:
            total_dividend += float(daily_series[d]["7. dividend amount"])
            
        return {"price": current_price, "annual_dividend": total_dividend}, None
    except Exception as e:
        return None, f"連線錯誤：{str(e)}"

# --- 3. 主要邏輯 ---
if analyze_btn:
    with st.spinner(f'正在分析 {full_ticker}...'):
        result, error_msg = fetch_data(full_ticker)
        
        if error_msg:
            st.error(error_msg)
        else:
            price = result["price"]
            div = result["annual_dividend"]
            yield_pct = (div / price * 100) if price > 0 else 0
            
            # 顯示數據卡片
            st.subheader(f"📊 {full_ticker} 分析結果")
            m1, m2 = st.columns(2)
            m1.metric("目前股價", f"{currency_symbol}{price:.2f}")
            m2.metric("目前殖利率", f"{yield_pct:.2f}%")
            
            st.divider()
            
            # --- 4. 估值計算 ---
            if div <= 0:
                st.warning("⚠️ 此股票過去一年無配息紀錄，無法進行股息估值。")
            else:
                st.subheader("⚖️ 估值調整 (高登模型)")
                r = st.slider("期望回報率 (%)", 5.0, 15.0, 8.0, 0.5) / 100
                g = st.slider("預估永續成長率 (%)", 0.0, 8.0, 3.0, 0.5) / 100
                
                if r > g:
                    # 公式: Fair Price = D * (1+g) / (r-g)
                    fair_price = (div * (1 + g)) / (r - g)
                    st.info(f"💡 預估合理價：**{currency_symbol}{fair_price:.2f}**")
                    
                    if price < fair_price:
                        st.success(f"🔥 股價低於合理價 (安全邊際約 {((1 - price/fair_price)*100):.1f}%)")
                    else:
                        st.warning(f"💎 目前股價略高於估值")
                else:
                    st.error("期望回報率必須大於成長率")

st.caption("---")
st.caption("註：免費版 API 每分鐘限 5 次查詢。投資請審慎評估風險。")
