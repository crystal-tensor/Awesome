import yfinance as yf
df = yf.download("688027.SS", start="2022-01-01", end="2022-01-10", progress=False)
print("Type of columns:", type(df.columns))
print("Columns:")
print(df.columns)
print(df.head())
