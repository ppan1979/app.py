import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="全球股息估值-全自動修復版", layout="centered")

# --- 讀取所有可用 API ---
try:
    FINNHUB_KEY = st.secrets["FINNHUB_KEY"]
    FMP_KEY = st.secrets["FMP_KEY"]
except:
    st.error("❌ 請確保 Secrets 中有 FINNHUB_KEY 與 FMP_KEY。")
    st.stop()

st.title("💰 股息估值工具 (全自動抓取引擎)")

# --- 1. 使用者輸入 ---
market = st.radio("選擇市場", ["台股 (TW)", "美股 (US)"], horizontal=True)
ticker = st.text_input("輸入股票代碼", value="2330" if market == "台股 (TW)" else "AAPL").upper().strip()
analyze_btn = st.button("執行深度分析", type="primary")

# --- 2. 鋼鐵抓取邏輯 ---

def fetch_tw_data_robust(symbol):
    """台股多源抓取邏輯"""
    # 路徑 A: FMP (加上 .TW 或 .TWO 判定)
    for suffix in [".TW", ".TWO"]:
        f_url = f"https://financialmodelingprep.com/api/v3/quote/{symbol}{suffix}?apikey={FMP_KEY}"
        try:
            res = requests.get(f_url, timeout=5).json()
            if res and isinstance(res, list):
                return res[0].get("price"), res[0].get("dividend"), "FMP"
        except: continue

    # 路徑 B: 官方證交所直連 (如果 FMP 失敗)
    twse_url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_AVG_ALL"
    try:
        res = requests.get(twse_url, timeout=5).json()
        target = next((x for x in data if x['Code'] == symbol), None)
        if target:
            # 這裡我們甚至可以加入一個簡單的股息爬取邏輯，或從其他公開 JSON 抓取
            return float(target['ClosingPrice']), 0, "TWSE_Official"
    except: pass
    
    return None, None, "All Failed"

def fetch_us_data_robust(symbol):
    """美股多源抓取邏輯"""
    # 路徑 A: Finnhub
    q_url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={FINNHUB_KEY}"
    d_url = f"https://finnhub.io/api/v1/stock/dividend?symbol={symbol}&token={FINNHUB_KEY}"
    try:
        q_res = requests.get(q_url, timeout=5).json()
        d_res = requests.get(d_url, timeout=5).json()
        if q_res.get('c'):
            price = q_res['c']
            div = sum([d['amount'] for d in d_res[:4]]) if isinstance(d_res, list) else 0
            return price, div, "Finnhub"
    except: pass

    # 路徑 B: FMP 備援
    f_url = f"https://financialmodelingprep.com/api/v3/quote/{symbol}?apikey={FMP_KEY}"
    try:
        res = requests.get(f_url, timeout=5).json()
        if res: return res[0].get("price"), res[0].get("dividend"), "FMP"
    except: pass

    return None, None, "All Failed"

# --- 3. 執行與渲染 ---
if analyze_btn:
    with st.spinner(f'正在為您從全球節點抓取 {ticker} 的精確數據...'):
        if market == "台股 (TW)":
            price, div, source = fetch_tw_data_robust(ticker)
        else:
            price, div, source = fetch_us_data_robust(ticker)

        if price:
            st.success(f"✅ 成功通過 {source} 引擎獲取數據")
            currency = "NT$" if market == "台股 (TW)" else "$"
            c1, c2 = st.columns(2)
            c1.metric("即時股價", f"{currency}{price:.2f}")
            c2.metric("年度股息", f"{currency}{div:.2f}" if div else "需手動補入")
            
            # 股息補全邏輯
            final_div = div
            if not div or div == 0:
                final_div = st.number_input(f"API 暫無該標的股息資料，請補入年度總股息", value=0.0)

            if final_div > 0:
                st.divider()
                r = st.slider("期望回報率 (%)", 5.0, 15.0, 8.0) / 100
                g = st.slider("永續成長率 (%)", 0.0, 8.0, 3.0) / 100
                fair_price = (final_div * (1 + g)) / (r - g)
                st.subheader(f"💡 高登模型估值結果")
                st.info(f"合理價為 **{currency}{fair_price:.2f}**")
        else:
            st.error("🚨 深度抓取失敗。這可能是因為 API 額度用盡或該代碼暫時被封鎖。")
