import streamlit as st
import requests
import pandas as pd

# 設定網頁標題與移動端優化
st.set_page_config(page_title="雙引擎股息估值工具", layout="centered")

# --- 安全讀取 Secrets ---
try:
    FINNHUB_KEY = st.secrets["FINNHUB_KEY"]
    ITICK_KEY = st.secrets["ITICK_KEY"]
except:
    st.error("❌ 找不到 API Key。請在 Streamlit Cloud Secrets 設定 'FINNHUB_KEY' 與 'ITICK_KEY'。")
    st.stop()

st.title("💰 雙引擎股息估值工具")
st.caption("台股：iTick 穩定引擎 | 美股：Finnhub 精準引擎")

# --- 1. 使用者輸入區 ---
market = st.radio("選擇市場", ["台股 (TW)", "美股 (US)"], horizontal=True)

col1, col2 = st.columns([3, 1])
with col1:
    default_ticker = "2330" if market == "台股 (TW)" else "AAPL"
    ticker_input = st.text_input("輸入股票代碼", value=default_ticker).upper().strip()
with col2:
    st.write(" ")
    analyze_btn = st.button("分析", use_container_width=True, type="primary")

# --- 2. 雙引擎抓取邏輯 ---

def fetch_us_data(symbol):
    """美股專用 (Finnhub)"""
    quote_url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={FINNHUB_KEY}"
    div_url = f"https://finnhub.io/api/v1/stock/dividend?symbol={symbol}&token={FINNHUB_KEY}"
    try:
        q_res = requests.get(quote_url, timeout=10).json()
        if 'c' not in q_res or q_res['c'] == 0:
            return None, f"Finnhub 找不到代碼 {symbol}"
        
        price = q_res['c']
        d_res = requests.get(div_url, timeout=10).json()
        total_div = 0.0
        if isinstance(d_res, list) and len(d_res) > 0:
            df = pd.DataFrame(d_res)
            df['date'] = pd.to_datetime(df['date'])
            one_year_ago = pd.Timestamp.now() - pd.Timedelta(days=365)
            total_div = df[df['date'] > one_year_ago]['amount'].sum()
        return {"price": price, "div": total_div}, None
    except Exception as e:
        return None, f"Finnhub 連線失敗: {e}"

def fetch_tw_data(symbol):
    """台股專用 (iTick)"""
    # iTick API 獲取即時報價與財務數據
    url = f"https://api.itick.io/v1/quotes/{symbol}?token={ITICK_KEY}"
    try:
        res = requests.get(url, timeout=10).json()
        # 檢查 iTick 回傳結構 (標準為 dict 包含 price 資訊)
        if "last" not in res:
            return None, f"iTick 找不到台股代碼 {symbol}"
        
        price = res["last"]
        # 直接抓取 iTick 提供的年化股息資訊，這對台股最準
        div = res.get("dividend_yield_value", 0.0) 
        if div == 0:
             # 如果欄位沒值，嘗試抓取股利發放總額
             div = res.get("dividend_per_share", 0.0)
             
        return {"price": price, "div": div}, None
    except Exception as e:
        return None, f"iTick 連線失敗: {e}"

# --- 3. 執行邏輯 ---
if analyze_btn:
    with st.spinner('引擎啟動中...'):
        if market == "美股 (US)":
            result, error = fetch_us_data(ticker_input)
        else:
            result, error = fetch_tw_data(ticker_input)
            
        if error:
            st.error(error)
        else:
            price = result["price"]
            div = result["div"]
            currency = "$" if market == "美股 (US)" else "NT$"
            
            st.subheader(f"📊 {ticker_input} 分析結果")
            c1, c2 = st.columns(2)
            c1.metric("目前股價", f"{currency}{price:.2f}")
            c2.metric("預計年化股息", f"{currency}{div:.2f}")
            
            if div > 0:
                st.divider()
                st.subheader("⚖️ 估值調整 (高登模型)")
                r = st.slider("期望回報率 (%)", 5.0, 15.0, 8.0, 0.5) / 100
                g = st.slider("預估永續成長率 (%)", 0.0, 8.0, 3.0, 0.5) / 100
                
                if r > g:
                    fair_price = (div * (1 + g)) / (r - g)
                    st.info(f"💡 預估合理價：**{currency}{fair_price:.2f}**")
                    if price < fair_price:
                        st.success(f"🔥 股價低於合理價 (安全邊際約 {((1 - price/fair_price)*100):.1f}%)")
                    else:
                        st.warning("💎 股價目前高於估值")
                else:
                    st.error("期望回報率須大於成長率")
            else:
                st.warning("⚠️ 該代碼目前查無配息資料，無法進行估值。")

st.caption("---")
st.caption("系統備註：本工具結合 Finnhub 與 iTick API，提供跨市場穩定數據支援。")
