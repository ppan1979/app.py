def fetch_data(symbol):
    # 使用最穩定的 Daily Time Series 功能
    url = f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&apikey={API_KEY}'
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        # 1. 檢查 API 頻率限制
        if "Note" in data:
            return None, "API 請求太頻繁，請等一分鐘後再試。"
            
        # 2. 檢查是否有資料
        if "Time Series (Daily)" not in data:
            return None, f"代碼 '{symbol}' 暫時無法獲取報價，請檢查代碼或稍後再試。"
            
        # 3. 解析最新價格
        daily_series = data["Time Series (Daily)"]
        latest_date = list(daily_series.keys())[0] # 抓取最近的一個交易日
        current_price = float(daily_series[latest_date]["4. close"])
        
        # 4. 股息部分：Alpha Vantage 免費版對台股股息支援較弱
        # 為了不讓程式閃退，我們先將股息預設為 0，並提示用戶
        total_dividend = 0.0
        
        # 嘗試抓取股息 (選用功能)
        div_url = f'https://www.alphavantage.co/query?function=DIVIDENDS&symbol={symbol}&apikey={API_KEY}'
        div_res = requests.get(div_url, timeout=10).json()
        if "data" in div_res and len(div_res["data"]) > 0:
            df_div = pd.DataFrame(div_res["data"])
            df_div['ex_dividend_date'] = pd.to_datetime(df_div['ex_dividend_date'])
            # 抓過去一年的股息
            one_year_ago = pd.Timestamp.now() - pd.Timedelta(days=365)
            recent_divs = df_div[df_div['ex_dividend_date'] > one_year_ago]
            total_dividend = recent_divs['amount'].astype(float).sum()
            
        return {"price": current_price, "annual_dividend": total_dividend}, None
        
    except Exception as e:
        return None, f"系統錯誤：{str(e)}"
