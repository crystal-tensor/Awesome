import akshare as ak
df = ak.stock_zh_a_hist(symbol="688027", period="daily", start_date="20220101", end_date="20260601", adjust="qfq")
print(df.head())
