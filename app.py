import streamlit as st
import requests
import pandas as pd

# 網頁基礎設定
st.set_page_config(page_title="全球股息估值-穩定加強版", layout="centered")

# --- 安全讀取 Secrets ---
try:
    # 只需要你的 Finnhub Key 即可
    FINNHUB_KEY = st.secrets["FINNHUB_KEY"]
except:
    st.error("❌ 找不到 FINNHUB_KEY，請在 Streamlit Cloud Secrets 設定。")
    st.stop()

st.title("💰 全球股息估值工具")
st.caption("台股：證交所官方直連 (免Key) | 美股：Finnhub 精準引擎")

# --- 1. 使用者輸入區 ---
market = st.radio("選擇市場", ["台股 (TW)", "美股 (US)"], horizontal=True)

col1, col2 = st.columns([3, 1])
with col1:
    default_ticker = "2330" if market == "台股 (TW)" else "AAPL"
    ticker = st.text_input("輸入股票代碼", value=default_ticker).upper().strip()
with col2:
    st.write(" ")
    btn = st.button("分析數據", use_container_width=True, type="primary")

# --- 側邊欄：手動補入區 ---
st.sidebar.header("🛠️ 數據微調/補入")
st.sidebar.write("若自動抓取的股息不準（如台股），請在此手動輸入。")
manual_price = st.sidebar.number_input("手動股價 (0為自動)", value=0.0)
manual_div = st.sidebar.number_input("手動年股息 (0為自動)", value=0.0)

# --- 2. 抓取引擎 ---

def get_tw_official_price(symbol):
    """直接調用台灣證交所官方 OpenAPI"""
    url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_AVG_ALL"
    try:
        res = requests.get(url, timeout=10)
        data = res.json()
        target = next((x for x in data if x['Code'] == symbol), None)
        if target:
            return float(target['ClosingPrice']), None
        return 0, f"證交所目前找不到代碼 {symbol}"
    except:
        return 0, "連線證交所失敗，請檢查網路。"

def get_us_finnhub_data(symbol):
    """使用你原本正常的 Finnhub API"""
    q_url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={FINNHUB_KEY}"
    d_url = f"https://finnhub.io/api/v1/stock/dividend?symbol={symbol}&token={FINNHUB_KEY}"
    try:
        q_res = requests.get(q_url, timeout=10).json()
        d_res = requests.get(d_url, timeout=10).json()
        price = q_res.get('c', 0)
        total_div = 0.0
        if isinstance(d_res, list) and len(d_res) > 0:
            df = pd.DataFrame(d_res)
            df['date'] = pd.to_datetime(df['date'])
            # 加總一年內股息
            one_year_ago = pd.Timestamp.now() - pd.Timedelta(days=365)
            total_div = df[df['date'] > one_year_ago]['amount'].sum()
        return price, total_div, None
    except Exception as e:
        return 0, 0, f"Finnhub 連線錯誤"

# --- 3. 邏輯執行 ---
if btn:
    with st.spinner('正在同步數據...'):
        if market == "台股 (TW)":
            auto_price, err = get_tw_official_price(ticker)
            auto_div = 0.0 # 證交所 API 不含股息，需手動輸入
        else:
            auto_price, auto_div, err = get_us_finnhub_data(ticker)

        # 優先權：手動 > 自動
        final_price = manual_price if manual_price > 0 else auto_price
        final_div = manual_div if manual_div > 0 else auto_div

        if final_price == 0:
            st.error(err if err else "找不到數據")
        else:
            currency = "NT$" if market == "台股 (TW)" else "$"
            st.subheader(f"📊 {ticker} 分析摘要")
            c1, c2 = st.columns(2)
            c1.metric("當前股價", f"{currency}{final_price:.2f}")
            c2.metric("預計年股息", f"{currency}{final_div:.2f}")
            
            if market == "台股 (TW)" and manual_div == 0:
                st.warning("ℹ️ 請在左側輸入『手動年股息』即可計算合理價（例如 2330 輸入 16）。")

            if final_div > 0:
                st.divider()
                st.subheader("⚖️ 高登模型估值")
                r = st.slider("期望回報率 (%)", 5.0, 15.0, 8.0, 0.5) / 100
                g = st.slider("預估永續成長率 (%)", 0.0, 8.0, 3.0, 0.5) / 100
                
                if r > g:
                    fair_price = (final_div * (1 + g)) / (r - g)
                    st.info(f"💡 預估合理價：**{currency}{fair_price:.2f}**")
                    if final_price < fair_price:
                        st.success("🔥 股價低於合理價 (安全邊際充足)")
                    else:
                        st.warning("💎 股價目前高於估值")
                else:
                    st.error("期望回報率必須大於成長率")
