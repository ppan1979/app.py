import streamlit as st
import requests
import pandas as pd

# 網頁設定
st.set_page_config(page_title="全球股息估值-三引擎版", layout="centered")

# --- 安全讀取 Secrets ---
try:
    FINNHUB_KEY = st.secrets.get("FINNHUB_KEY", "")
    ITICK_KEY = st.secrets.get("ITICK_KEY", "")
except:
    st.warning("⚠️ 部分 API Key 尚未設定，可能影響自動抓取功能。")

st.title("💰 股息估值工具 (三引擎整合版)")

# --- 1. 使用者輸入與引擎選擇 ---
market = st.radio("選擇市場", ["台股 (TW)", "美股 (US)"], horizontal=True)

if market == "台股 (TW)":
    tw_engine = st.selectbox("台股數據源", ["官方直連 (免Key/最穩)", "iTick (自動股息/有期限)"])
else:
    us_engine = "Finnhub (自動抓取)"

col1, col2 = st.columns([3, 1])
with col1:
    default_ticker = "2330" if market == "台股 (TW)" else "AAPL"
    ticker = st.text_input("輸入股票代碼", value=default_ticker).upper().strip()
with col2:
    st.write(" ")
    btn = st.button("執行分析", use_container_width=True, type="primary")

# --- 側邊欄：手動補入區 (所有引擎的最後防線) ---
st.sidebar.header("🛠️ 數據手動修正")
manual_price = st.sidebar.number_input("手動股價 (0為自動)", value=0.0)
manual_div = st.sidebar.number_input("手動年股息 (0為自動)", value=0.0)

# --- 2. 各大引擎函數 ---

def get_tw_official_price(symbol):
    """引擎 A: 台灣證交所官方直連"""
    url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_AVG_ALL"
    try:
        res = requests.get(url, timeout=10)
        data = res.json()
        target = next((x for x in data if x['Code'] == symbol), None)
        return (float(target['ClosingPrice']), 0.0, None) if target else (0, 0, "找不到代碼")
    except:
        return 0, 0, "證交所連線失敗"

def get_tw_itick_data(symbol):
    """引擎 B: iTick 專業數據"""
    url = f"https://api.itick.io/v1/quotes/{symbol}?token={ITICK_KEY}"
    try:
        res = requests.get(url, timeout=10).json()
        price = res.get("last", 0)
        div = res.get("dividend_yield_value", 0.0) or res.get("dividend_per_share", 0.0)
        return price, div, None
    except:
        return 0, 0, "iTick 連線失敗或 Key 已過期"

def get_us_finnhub_data(symbol):
    """引擎 C: Finnhub 美股數據"""
    q_url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={FINNHUB_KEY}"
    d_url = f"https://finnhub.io/api/v1/stock/dividend?symbol={symbol}&token={FINNHUB_KEY}"
    try:
        q_res = requests.get(q_url, timeout=10).json()
        price = q_res.get('c', 0)
        d_res = requests.get(d_url, timeout=10).json()
        total_div = 0.0
        if isinstance(d_res, list) and len(d_res) > 0:
            df = pd.DataFrame(d_res)
            df['date'] = pd.to_datetime(df['date'])
            total_div = df[df['date'] > (pd.Timestamp.now() - pd.Timedelta(days=365))]['amount'].sum()
        return price, total_div, None
    except:
        return 0, 0, "Finnhub 連線失敗"

# --- 3. 執行分析邏輯 ---
if btn:
    with st.spinner('正在分析市場數據...'):
        if market == "台股 (TW)":
            if tw_engine == "iTick (自動股息/有期限)":
                a_price, a_div, err = get_tw_itick_data(ticker)
            else:
                a_price, a_div, err = get_tw_official_price(ticker)
        else:
            a_price, a_div, err = get_us_finnhub_data(ticker)

        final_price = manual_price if manual_price > 0 else a_price
        final_div = manual_div if manual_div > 0 else a_div

        if final_price == 0:
            st.error(err if err else "找不到資料")
            st.info("💡 提示：若 API 失效，請於左側手動輸入數據。")
        else:
            currency = "NT$" if market == "台股 (TW)" else "$"
            st.subheader(f"📊 {ticker} 分析結果")
            c1, c2 = st.columns(2)
            c1.metric("當前股價", f"{currency}{final_price:.2f}")
            c2.metric("預計年股息", f"{currency}{final_div:.2f}")
            
            # 高登模型計算
            if final_div > 0:
                st.divider()
                r = st.slider("期望回報率 (%)", 5.0, 15.0, 8.0, 0.5) / 100
                g = st.slider("預估永續成長率 (%)", 0.0, 8.0, 3.0, 0.5) / 100
                if r > g:
                    fair_price = (final_div * (1 + g)) / (r - g)
                    st.info(f"💡 預估合理價：**{currency}{fair_price:.2f}**")
                    if final_price < fair_price:
                        st.success("🔥 股價低於合理價 (適合分批布局)")
                    else:
                        st.warning("💎 股價目前高於估值")
            else:
                st.warning("⚠️ 缺少年股息數據，無法計算合理價。請在左側手動補入。")
