import streamlit as st
import requests
import pandas as pd

# 網頁基礎設定
st.set_page_config(page_title="全球股息估值工具-終極版", layout="centered")

# --- 安全讀取 Secrets ---
try:
    FINNHUB_KEY = st.secrets["FINNHUB_KEY"]
    FMP_KEY = st.secrets["FMP_KEY"]
except Exception:
    st.error("❌ 找不到 API Key。請在 Streamlit Cloud Secrets 設定 'FINNHUB_KEY' 與 'FMP_KEY'。")
    st.stop()

st.title("💰 全球股息估值工具")
st.caption("2026 長效穩定版：美股 (Finnhub) | 台股 (FMP)")

# --- 1. 使用者輸入區 ---
market = st.radio("選擇市場", ["台股 (TW)", "美股 (US)"], horizontal=True)

col_t, col_b = st.columns([3, 1])
with col_t:
    default_ticker = "2330" if market == "台股 (TW)" else "AAPL"
    ticker_input = st.text_input("輸入股票代碼", value=default_ticker).upper().strip()
with col_b:
    st.write(" ")
    analyze_btn = st.button("分析", use_container_width=True, type="primary")

# --- 側邊欄：手動輸入備案 ---
st.sidebar.header("🛠️ 數據微調/手動輸入")
st.sidebar.info("若自動抓取資料有誤，可在此手動覆蓋數值。")
manual_price = st.sidebar.number_input("手動設定股價 (0為自動)", value=0.0)
manual_div = st.sidebar.number_input("手動設定年股息 (0為自動)", value=0.0)

# --- 2. 核心抓取引擎 ---
def fetch_data(market, symbol):
    if market == "美股 (US)":
        # Finnhub 引擎
        q_url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={FINNHUB_KEY}"
        d_url = f"https://finnhub.io/api/v1/stock/dividend?symbol={symbol}&token={FINNHUB_KEY}"
        try:
            q_res = requests.get(q_url, timeout=10).json()
            d_res = requests.get(d_url, timeout=10).json()
            price = q_res.get('c', 0)
            # 加總過去 365 天股息
            total_div = 0.0
            if isinstance(d_res, list) and len(d_res) > 0:
                df = pd.DataFrame(d_res)
                df['date'] = pd.to_datetime(df['date'])
                one_year_ago = pd.Timestamp.now() - pd.Timedelta(days=365)
                total_div = df[df['date'] > one_year_ago]['amount'].sum()
            return price, total_div, None
        except Exception as e:
            return 0, 0, f"Finnhub 錯誤: {e}"
    else:
        # FMP 引擎 (台股格式為 2330.TW)
        f_symbol = f"{symbol}.TW"
        url = f"https://financialmodelingprep.com/api/v3/quote/{f_symbol}?apikey={FMP_KEY}"
        try:
            res = requests.get(url, timeout=10).json()
            if not res or not isinstance(res, list):
                return 0, 0, f"FMP 找不到台股代碼 {f_symbol}"
            price = res[0].get("price", 0)
            div = res[0].get("dividend", 0) # FMP 年度預估股息
            return price, div, None
        except Exception as e:
            return 0, 0, f"FMP 錯誤: {e}"

# --- 3. 畫面顯示邏輯 ---
if analyze_btn:
    with st.spinner('正在從全球資料庫同步數據...'):
        auto_price, auto_div, error = fetch_data(market, ticker_input)
        
        # 決定最終使用的數值 (手動優先)
        final_price = manual_price if manual_price > 0 else auto_price
        final_div = manual_div if manual_div > 0 else auto_div
        
        if error and final_price == 0:
            st.error(error)
            st.info("💡 提示：若 API 暫時失效，您可以在左側側邊欄手動輸入股價與股息。")
        elif final_price == 0:
            st.warning(f"⚠️ 無法取得 {ticker_input} 的數據，請檢查代碼或手動輸入。")
        else:
            currency = "$" if market == "美股 (US)" else "NT$"
            st.subheader(f"📊 {ticker_input} 數據分析")
            c1, c2 = st.columns(2)
            c1.metric("目前股價", f"{currency}{final_price:.2f}")
            c2.metric("年度總股息", f"{currency}{final_div:.2f}")
            
            if final_div > 0:
                st.divider()
                st.subheader("⚖️ 高登模型估值 (Gordon Growth)")
                r = st.slider("期望回報率 (%)", 5.0, 15.0, 8.0, 0.5) / 100
                g = st.slider("預估永續成長率 (%)", 0.0, 8.0, 3.0, 0.5) / 100
                
                if r > g:
                    # 公式：Fair Price = D * (1 + g) / (r - g)
                    fair_price = (final_div * (1 + g)) / (r - g)
                    st.info(f"💡 預估合理價：**{currency}{fair_price:.2f}**")
                    
                    if final_price < fair_price:
                        discount = (1 - final_price/fair_price) * 100
                        st.success(f"🔥 股價低於合理價！(安全邊際：{discount:.1f}%)")
                    else:
                        premium = (final_price/fair_price - 1) * 100
                        st.warning(f"💎 股價目前高於估值 (溢價：{premium:.1f}%)")
                else:
                    st.error("計算失敗：期望回報率必須大於成長率。")
            else:
                st.warning("⚠️ 該標的目前查無配息數據，不適用高登模型估值。")

st.caption("---")
st.caption("免責聲明：本工具數據僅供參考。數據庫 FMP 每日免費額度為 250 次查詢。")
