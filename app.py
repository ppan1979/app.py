import streamlit as st
import requests
import pandas as pd

# 設定網頁標題與移動端優化
st.set_page_config(page_title="全球股息估值工具", layout="centered")

# --- 從 Secrets 安全讀取 API Key ---
# 請確認你在 Streamlit Secrets 中設定的名稱為 ALPHA_VANTAGE_KEY
try:
    API_KEY = st.secrets["ALPHA_VANTAGE_KEY"]
except:
    st.error("❌ 找不到 API Key。請確認已在 Streamlit Cloud 的 Secrets 中設定 'ALPHA_VANTAGE_KEY'。")
    st.stop()

st.title("💰 全球股息投資估值工具")
st.caption("數據來源：Alpha Vantage | 安全部署版")

# --- 1. 使用者輸入區 ---
market = st.radio("選擇市場", ["台股 (TW)", "美股 (US)"], horizontal=True)

col1, col2 = st.columns([3, 1])
with col1:
    # 根據市場預設初始代碼
    default_ticker = "2330" if market == "台股 (TW)" else "KO"
    ticker_input = st.text_input("輸入股票代碼", value=default_ticker).upper().strip()
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
            return None, "API 請求太頻繁，請等一分鐘後再試 (免費版限制)。"
        if "Error Message" in data:
            return None, f"找不到代碼 '{symbol}'，請確認輸入正確。"
        if "Time Series (Daily)" not in data:
            return None, "目前無法獲取資料，請檢查代碼或稍後再試。"
            
        daily_series = data["Time Series (Daily)"]
        latest_day = list(daily_series.keys())[0]
        current_price = float(daily_series[latest_day]["4. close"])
        
        # 計算過去一年 (252個交易日) 的總股息
        total_dividend = 0.0
        dates = list(daily_series.keys())[:252]
        for d in dates:
            total_dividend += float(daily_series[d]["7. dividend amount"])
            
        return {"price": current_price, "annual_dividend": total_dividend}, None
    except Exception as e:
        return None, f"連線錯誤：{str(e)}"

# --- 3. 主要分析邏輯 ---
if analyze_btn:
    with st.spinner(f'正在從全球資料庫分析 {full_ticker}...'):
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
            
            # --- 4. 估值計算 (高登模型) ---
            if div <= 0:
                st.warning("⚠️ 此股票過去一年無配息紀錄，無法進行股息估值。")
            else:
                st.subheader("⚖️ 估值調整 (高登模型)")
                r = st.slider("期望回報率 (%)", 5.0, 15.0, 8.0, 0.5) / 100
                g = st.slider("預估永續成長率 (%)", 0.0, 8.0, 3.0, 0.5) / 100
                
                if r > g:
                    # 公式: Fair Price = D1 / (r - g)
                    # 其中 D1 = 明年預期股息 = 今年股息 * (1 + g)
                    fair_price = (div * (1 + g)) / (r - g)
                    st.info(f"💡 預估合理價：**{currency_symbol}{fair_price:.2f}**")
                    
                    if price < fair_price:
                        discount = (1 - price/fair_price) * 100
                        st.success(f"🔥 股價低於合理價 (安全邊際約 {discount:.1f}%)")
                    else:
                        st.warning(f"💎 目前股價略高於估值")
                else:
                    st.error("期望回報率必須大於成長率，否則公式無法計算。")

st.caption("---")
st.caption("註：本工具僅供參考，不構成投資建議。數據由 Alpha Vantage 提供。")
