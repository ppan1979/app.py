import streamlit as st
import requests
import pandas as pd

# 設定網頁標題與移動端優化
st.set_page_config(page_title="全球股息估值工具", layout="centered")

# --- 安全讀取 API Key ---
try:
    API_KEY = st.secrets["ALPHA_VANTAGE_KEY"]
except Exception:
    st.error("❌ 找不到 Secrets 設定，請確認後台已填寫 ALPHA_VANTAGE_KEY")
    st.stop()

st.title("💰 全球股息投資估值工具")
st.caption("數據來源：Alpha Vantage | 穩定強化版")

# --- 1. 使用者輸入區 ---
market = st.radio("選擇市場", ["台股 (TW)", "美股 (US)"], horizontal=True)

col1, col2 = st.columns([3, 1])
with col1:
    default_ticker = "2330" if market == "台股 (TW)" else "KO"
    ticker_input = st.text_input("輸入股票代碼", value=default_ticker).upper().strip()
with col2:
    st.write(" ")
    analyze_btn = st.button("分析", use_container_width=True, type="primary")

# 代碼處理
if market == "台股 (TW)" and ".TW" not in ticker_input:
    full_ticker = f"{ticker_input}.TW"
else:
    full_ticker = ticker_input

currency_symbol = "NT$" if ".TW" in full_ticker else "$"

# --- 2. 資料抓取函數 (強化穩定性) ---
def fetch_stable_data(symbol):
    # 使用 GLOBAL_QUOTE 獲取即時價格
    url = f'https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={API_KEY}'
    # 使用 DIVIDENDS 獲取股息紀錄
    div_url = f'https://www.alphavantage.co/query?function=DIVIDENDS&symbol={symbol}&apikey={API_KEY}'
    
    try:
        # 抓取股價
        price_res = requests.get(url, timeout=10).json()
        
        if "Note" in price_res:
            return None, "API 請求太頻繁，請等一分鐘後再試一次。"
            
        if "Global Quote" not in price_res or not price_res["Global Quote"]:
            return None, f"代碼 '{symbol}' 找不到即時報價，請確認代碼正確。"
            
        current_price = float(price_res["Global Quote"]["05. price"])
        
        # 抓取股息
        div_res = requests.get(div_url, timeout=10).json()
        total_div = 0.0
        
        if "data" in div_res:
            # 計算過去 365 天總股息
            df_div = pd.DataFrame(div_res["data"])
            df_div['ex_dividend_date'] = pd.to_datetime(df_div['ex_dividend_date'])
            # 取得一年內的時間點
            one_year_ago = pd.Timestamp.now() - pd.Timedelta(days=365)
            # 過濾並加總
            recent_divs = df_div[df_div['ex_dividend_date'] > one_year_ago]
            total_div = recent_divs['amount'].astype(float).sum()
            
        return {"price": current_price, "annual_dividend": total_div}, None
        
    except Exception as e:
        return None, f"連線異常：{str(e)}"

# --- 3. 分析邏輯 ---
if analyze_btn:
    with st.spinner(f'正在獲取 {full_ticker} 資料...'):
        result, error_msg = fetch_stable_data(full_ticker)
        
        if error_msg:
            st.error(error_msg)
            # 額外診斷提示
            if "連線異常" in error_msg:
                st.info("提示：可能是網際網路問題，請重新點擊分析按鈕。")
        else:
            price = result["price"]
            div = result["annual_dividend"]
            
            # 顯示結果卡片
            st.subheader(f"📊 {full_ticker} 分析結果")
            c1, c2 = st.columns(2)
            c1.metric("目前股價", f"{currency_symbol}{price:.2f}")
            
            # 若無股息顯示提示
            if div > 0:
                div_yield = (div / price) * 100
                c2.metric("近一年總股息", f"{currency_symbol}{div:.2f}")
                st.write(f"目前殖利率：**{div_yield:.2f}%**")
                
                st.divider()
                
                # --- 4. 估值 ---
                st.subheader("⚖️ 估值調整")
                r = st.slider("期望回報率 (%)", 5.0, 15.0, 8.0, 0.5) / 100
                g = st.slider("預估成長率 (%)", 0.0, 8.0, 3.0, 0.5) / 100
                
                if r > g:
                    fair_price = (div * (1 + g)) / (r - g)
                    st.info(f"💡 預估合理價：**{currency_symbol}{fair_price:.2f}**")
                    if price < fair_price:
                        st.success("🔥 股價低於合理價 (具有安全邊際)")
                    else:
                        st.warning("💎 股價目前高於預估值")
                else:
                    st.error("回報率需大於成長率")
            else:
                c2.metric("近一年總股息", "無資料")
                st.warning("⚠️ 此股票查無股息發放紀錄，無法進行估值計算。")

st.caption("---")
st.caption("備註：免費 API 限制每分鐘 5 次、每天 25 次。")
