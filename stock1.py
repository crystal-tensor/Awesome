# ===================== 1. 导入依赖库 =====================
import argparse
import base64
import io
import json
import logging
import warnings
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import requests
import yfinance as yf

from classic_strategy import compute_classic_strategy
from pt_data_transformer import split_long_tail_bucket
from pt_strategy import compute_pt_strategy

# 忽略 matplotlib 的字体警告
warnings.filterlogging = logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib")

# 设置中文字体（解决matplotlib中文乱码，优先 macOS 字体）
plt.rcParams["font.family"] = ["Arial Unicode MS", "PingFang SC", "Heiti SC", "sans-serif"]
plt.rcParams["axes.unicode_minus"] = False

PROJECT_DIR = Path(__file__).resolve().parent
DATA_DIR = PROJECT_DIR / "data"
SELECTED_MARKET_STOCKS_PATH = PROJECT_DIR / ".tmp" / "selected-market-stocks.json"
LATEST_MODEL_PATH = PROJECT_DIR / ".tmp" / "latest-training-model.json"
STRATEGY_MODEL_DIR = PROJECT_DIR / "strategy"


# ===================== 3. 数据获取与预处理 =====================
def normalize_tencent_a_share_symbol(stock_code: str) -> str:
    code = stock_code.upper().replace(".SS", "").replace(".SZ", "").replace(".BJ", "")
    if stock_code.upper().endswith(".BJ") or code.startswith(("4", "8", "920")):
        prefix = "bj"
    else:
        prefix = "sh" if stock_code.upper().endswith(".SS") or code.startswith(("6", "9")) else "sz"
    return f"{prefix}{code}"


def normalize_tencent_hk_symbol(stock_code: str) -> str:
    return f"hk{stock_code.upper().replace('.HK', '').zfill(5)}"


def tencent_date(value: str) -> str:
    return pd.to_datetime(value).strftime("%Y-%m-%d")


def tencent_kline_count(start_date: str, end_date: str) -> int:
    days = max(1, (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days + 1)
    return min(2000, max(10, days * 2))


def normalize_tencent_symbols(stock_code: str) -> list[str]:
    """把常见市场代码转换成腾讯历史 K 线代码。"""
    code = stock_code.strip().upper()
    if code.endswith("-USD"):
        raise RuntimeError(f"当前只允许腾讯源，但暂未配置加密货币腾讯历史 K 线接口: {stock_code}")
    if code.endswith(".SS") or code.endswith(".SZ") or code.endswith(".BJ") or (code.isdigit() and len(code) == 6):
        return [normalize_tencent_a_share_symbol(code)]
    if code.endswith(".HK") or (code.isdigit() and len(code) <= 5):
        return [normalize_tencent_hk_symbol(code)]
    if code.startswith("US"):
        code = code[2:]
    ticker = code.replace("-", ".")
    if ticker.endswith((".OQ", ".N", ".A")):
        return [f"us{ticker}"]
    return [f"us{ticker}.OQ", f"us{ticker}.N", f"us{ticker}.A"]


def normalize_yahoo_symbol(stock_code: str) -> str:
    """把常见 A股/港股/美股/加密货币代码转换成 Yahoo Finance 代码。"""
    code = stock_code.strip().upper()
    if code.startswith(("SH", "SZ", "BJ")) and code[2:].isdigit():
        suffix = ".SS" if code.startswith("SH") else ".SZ"
        return f"{code[2:]}{suffix}"
    if "." in code or "-" in code or code.endswith("=F") or code.endswith("=X"):
        return code
    if code.isdigit() and len(code) == 6:
        return f"{code}.SS" if code.startswith(("6", "9")) else f"{code}.SZ"
    if code.isdigit() and len(code) <= 5:
        return f"{code.zfill(4)}.HK"
    return code


def identify_market_and_symbol(stock_code: str) -> tuple[str, str]:
    code = stock_code.strip().upper()
    if code.startswith(("SH", "SZ", "BJ")) and code[2:].isdigit():
        suffix = ".SS" if code.startswith("SH") else ".SZ" if code.startswith("SZ") else ".BJ"
        return "A股", f"{code[2:]}{suffix}"
    if code.endswith((".SS", ".SZ", ".BJ")):
        return "A股", code
    if code.isdigit() and len(code) == 6:
        suffix = ".BJ" if code.startswith(("4", "8", "920")) else ".SS" if code.startswith(("6", "9")) else ".SZ"
        return "A股", f"{code}{suffix}"
    if code.endswith(".HK"):
        return "港股", f"{code.replace('.HK', '').zfill(4)}.HK"
    if code.isdigit() and len(code) <= 5:
        return "港股", f"{code.zfill(4)}.HK"
    if code.endswith("-USD"):
        return "加密货币", code
    return "美股", code.replace(".OQ", "").replace(".N", "").replace(".A", "")


def data_csv_path(symbol: str, market: str) -> Path:
    safe_market = market.replace("/", "_").replace("\\", "_").replace(":", "_")
    safe_symbol = symbol.replace("/", "_").replace("\\", "_").replace(":", "_")
    return DATA_DIR / f"{safe_market}_{safe_symbol}.csv"


def prepare_price_frame(df: pd.DataFrame) -> pd.DataFrame:
    required_columns = ["open", "high", "low", "close", "volume"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise RuntimeError(f"行情数据缺少字段: {', '.join(missing_columns)}")

    df = df[required_columns].copy()
    df.index = pd.to_datetime(df.index)
    df.index.name = "date"
    for column in required_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df["daily_ret"] = df["close"].pct_change()
    df["daily_ret_abs"] = df["daily_ret"].abs()
    df["vol_20d"] = df["daily_ret"].rolling(window=20).std()
    df = df.dropna()
    if len(df) < 40:
        raise RuntimeError("可用历史数据不足，无法计算 20 日波动率和均线策略。")
    return df


def load_local_tencent_stock_data(stock_code: str, start_date: str, end_date: str, stale_days: int = 3) -> pd.DataFrame | None:
    market, symbol = identify_market_and_symbol(stock_code)
    path = data_csv_path(symbol, market)
    if not path.exists():
        return None
    raw = pd.read_csv(path)
    if "date" not in raw.columns:
        return None
    last_date = pd.to_datetime(raw["date"], errors="coerce").max()
    requested_end = pd.to_datetime(end_date)
    if pd.isna(last_date) or last_date < requested_end - pd.Timedelta(days=stale_days):
        return None
    raw["date"] = pd.to_datetime(raw["date"])
    raw = raw[(raw["date"] >= pd.to_datetime(start_date)) & (raw["date"] <= requested_end)]
    if raw.empty:
        return None
    raw = raw.set_index("date").sort_index()
    return prepare_price_frame(raw)


def get_yahoo_stock_data(stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
    """通过 Yahoo Finance 获取复权日线数据，保持旧版主回测口径。"""
    start = pd.to_datetime(start_date).strftime("%Y-%m-%d")
    end = (pd.to_datetime(end_date) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    ticker = normalize_yahoo_symbol(stock_code)
    df = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False, timeout=30)
    if df.empty:
        raise RuntimeError(f"Yahoo Finance 未返回数据，请检查股票代码或日期区间: {ticker}")

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.rename(
        columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        }
    )
    return prepare_price_frame(df)


def get_tencent_stock_data(stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
    """通过腾讯历史 K 线接口获取日线数据，作为 Yahoo 不可用时的兜底。"""
    last_error = None
    tencent_urls = [
        "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get",
        "https://ifzq.gtimg.cn/appstock/app/fqkline/get",
        "https://proxy.finance.qq.com/ifzqgtimg/appstock/app/fqkline/get",
    ]
    for tencent_symbol in normalize_tencent_symbols(stock_code):
        adjust = "" if tencent_symbol.startswith("us") else "qfq"
        params = {
            "param": (
                f"{tencent_symbol},day,{tencent_date(start_date)},"
                f"{tencent_date(end_date)},{tencent_kline_count(start_date, end_date)},{adjust}"
            )
        }
        for url in tencent_urls:
            try:
                response = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
                response.raise_for_status()
                payload = response.json()
                payload_data = payload.get("data", {})
                data = payload_data.get(tencent_symbol, {}) if isinstance(payload_data, dict) else {}
                rows = data.get("qfqday") or data.get("day") or []
                if not rows:
                    last_error = f"{tencent_symbol} 未返回历史 K 线"
                    continue

                df = pd.DataFrame([row[:6] for row in rows], columns=["date", "open", "close", "high", "low", "volume"])
                df["date"] = pd.to_datetime(df["date"])
                df = df.set_index("date").sort_index()
                return prepare_price_frame(df)
            except Exception as error:
                last_error = error
    detail = f": {last_error}" if last_error else ""
    raise RuntimeError(f"腾讯源未返回数据，请检查股票代码或日期区间: {stock_code}{detail}")


def get_stock_data(stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
    """主回测优先使用本地腾讯 CSV，其次腾讯接口，最后 Yahoo 兜底。"""
    local_df = load_local_tencent_stock_data(stock_code, start_date, end_date)
    if local_df is not None:
        return local_df

    try:
        return get_tencent_stock_data(stock_code, start_date, end_date)
    except Exception as tencent_error:
        local_fallback = None
        try:
            market, symbol = identify_market_and_symbol(stock_code)
            path = data_csv_path(symbol, market)
            if path.exists():
                raw = pd.read_csv(path)
                raw["date"] = pd.to_datetime(raw["date"])
                raw = raw[(raw["date"] >= pd.to_datetime(start_date)) & (raw["date"] <= pd.to_datetime(end_date))]
                if not raw.empty:
                    local_fallback = prepare_price_frame(raw.set_index("date").sort_index())
        except Exception:
            local_fallback = None
        if local_fallback is not None:
            return local_fallback
        try:
            return get_yahoo_stock_data(stock_code, start_date, end_date)
        except Exception as yahoo_error:
            raise RuntimeError(f"腾讯和 Yahoo 源都未返回可用数据: 腾讯={tencent_error}; Yahoo={yahoo_error}") from yahoo_error


def load_model_params_for_symbol(stock_code: str, eta_param: float) -> dict:
    market, symbol = identify_market_and_symbol(stock_code)

    if SELECTED_MARKET_STOCKS_PATH.exists():
        try:
            selected = json.loads(SELECTED_MARKET_STOCKS_PATH.read_text(encoding="utf-8"))
            for row in selected.get("markets", {}).get(market, {}).get("stocks", []):
                if str(row.get("symbol", "")).upper() == symbol.upper() and row.get("params"):
                    params = dict(row["params"])
                    params.update({"modelSource": "selected_market_stock", "modelMarket": market, "modelSymbol": symbol})
                    return params
        except Exception:
            pass

    latest_alpha_model_path = STRATEGY_MODEL_DIR / market / "latest_alpha_model.json"
    if latest_alpha_model_path.exists():
        try:
            model = json.loads(latest_alpha_model_path.read_text(encoding="utf-8"))
            per_stock = model.get("perStockParameters") or {}
            stock_model = per_stock.get(symbol.upper()) or per_stock.get(symbol)
            if stock_model and stock_model.get("params"):
                params = dict(stock_model["params"])
                return {
                    "mode": params.get("mode", "legacy_ot"),
                    "qHead": params.get("qHead", 0.8),
                    "qTail": params.get("qTail", 0.95),
                    "eta": params.get("eta", eta_param),
                    "modelSource": "latest_alpha_model",
                    "modelMarket": market,
                    "modelSymbol": symbol,
                    "modelPath": str(latest_alpha_model_path),
                    "alphaScore": stock_model.get("score"),
                }
        except Exception:
            pass

    if LATEST_MODEL_PATH.exists():
        try:
            model = json.loads(LATEST_MODEL_PATH.read_text(encoding="utf-8"))
            for item in model.get("marketSummary", []):
                if item.get("market") == market and item.get("bestParams"):
                    params = dict(item["bestParams"])
                    params.update({"modelSource": "legacy_training_model", "modelMarket": market, "modelSymbol": symbol, "modelPath": str(LATEST_MODEL_PATH)})
                    return params
        except Exception:
            pass

    latest_growth_model_path = STRATEGY_MODEL_DIR / market / "latest_growth_model.json"
    if latest_growth_model_path.exists():
        try:
            model = json.loads(latest_growth_model_path.read_text(encoding="utf-8"))
            params = dict(model.get("parameters") or {})
            if params:
                return {
                    "mode": params.get("mode", "legacy_ot"),
                    "qHead": params.get("qHead", 0.8),
                    "qTail": params.get("qTail", 0.95),
                    "eta": params.get("eta", eta_param),
                    "modelSource": "latest_growth_model",
                    "modelMarket": market,
                    "modelSymbol": symbol,
                    "modelPath": str(latest_growth_model_path),
                    "validationGate": model.get("validationGate", {}),
                }
        except Exception:
            pass
    return {"mode": "legacy_ot", "qHead": 0.8, "qTail": 0.95, "eta": eta_param, "modelSource": "fallback", "modelMarket": market, "modelSymbol": symbol}


def display_tencent_symbol(stock_code: str) -> str:
    try:
        return normalize_tencent_symbols(stock_code)[0]
    except Exception:
        return stock_code


# ===================== 4. 并行回测调度 =====================
def run_backtest(stock_code: str, stock_name: str, start_date: str, end_date: str, eta_param: float = 0.5) -> dict:
    """并行运行经典策略和 PT 策略，统一合并为页面使用的结果。"""
    tencent_symbol = display_tencent_symbol(stock_code)
    yahoo_symbol = normalize_yahoo_symbol(stock_code)
    pt_params = load_model_params_for_symbol(stock_code, eta_param)
    df_raw = get_stock_data(stock_code, start_date, end_date)
    df_raw = split_long_tail_bucket(df_raw)

    with ThreadPoolExecutor(max_workers=2) as executor:
        classic_future = executor.submit(compute_classic_strategy, df_raw)
        pt_future = executor.submit(
            compute_pt_strategy,
            df_raw,
            q_head=float(pt_params.get("qHead", 0.8)),
            q_tail=float(pt_params.get("qTail", 0.95)),
            eta_param=float(pt_params.get("eta", eta_param)),
            mode=str(pt_params.get("mode", "legacy_ot")),
        )
        classic_result = classic_future.result()
        pt_result = pt_future.result()

    chart_df = df_raw.reset_index()
    chart_df["date"] = chart_df["date"].dt.strftime("%Y-%m-%d")

    return {
        "stock": {
            "symbol": yahoo_symbol,
            "requestSymbol": stock_code,
            "yahooSymbol": yahoo_symbol,
            "tencentSymbol": tencent_symbol,
            "name": stock_name or yahoo_symbol,
        },
        "dateRange": {
            "start": str(chart_df["date"].iloc[0]),
            "end": str(chart_df["date"].iloc[-1]),
            "rows": int(len(chart_df)),
        },
        "bucketStats": {
            key: round(float(value) * 100, 2)
            for key, value in df_raw["bucket"].value_counts(normalize=True).sort_index().items()
        },
        "summary": {
            "mode": pt_result["summary"]["mode"],
            "qHead": pt_result["summary"]["qHead"],
            "qTail": pt_result["summary"]["qTail"],
            "eta": pt_result["summary"]["eta"],
            "modelSource": pt_params.get("modelSource", "unknown"),
            "modelMarket": pt_params.get("modelMarket"),
            "modelPath": pt_params.get("modelPath"),
            "alphaScore": pt_params.get("alphaScore"),
            "validationGate": pt_params.get("validationGate"),
            "originMean": pt_result["summary"]["originMean"],
            "perturbedMean": pt_result["summary"]["perturbedMean"],
        },
        "metrics": {
            "uniform": classic_result["metrics"],
            "pt": pt_result["metrics"],
        },
        "series": {
            "dates": chart_df["date"].tolist(),
            "uniform": classic_result["series"],
            "pt": pt_result["series"],
            "netUniform": classic_result["net"],
            "netPt": pt_result["net"],
        },
        "trades": {
            "uniform": classic_result["trades"],
            "pt": pt_result["trades"],
        },
        "tailSamples": pt_result["tailSamples"],
    }


# ===================== 5. HTML 报告生成 =====================
def build_report_image(result: dict) -> str:
    dates = pd.to_datetime(result["series"]["dates"])
    close = result["series"]["uniform"]["close"]
    ma5 = result["series"]["uniform"]["ma5"]
    ma20 = result["series"]["uniform"]["ma20"]
    net_origin = result["series"]["netUniform"]
    net_pt = result["series"]["netPt"]
    buy_points = result["series"]["uniform"]["buyPoints"]
    sell_points = result["series"]["uniform"]["sellPoints"]
    metrics_origin = result["metrics"]["uniform"]
    metrics_pt = result["metrics"]["pt"]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 12), gridspec_kw={"height_ratios": [2, 1]})

    line1 = ax1.plot(dates, net_origin, label="传统真实 (净值)", color="#3498db", linewidth=2)
    line2 = ax1.plot(dates, net_pt, label="PT重尾长尾方案 (净值)", color="#e74c3c", linewidth=2)

    ax1_twin = ax1.twinx()
    ax1_twin.plot(dates, close, label="收盘价", color="#2c3e50", linewidth=1.5, alpha=0.5, linestyle="--")
    ax1_twin.plot(dates, ma5, label="5日均线", color="#f1c40f", linewidth=1, alpha=0.4, linestyle=":")
    ax1_twin.plot(dates, ma20, label="20日均线", color="#9b59b6", linewidth=1, alpha=0.4, linestyle=":")

    if buy_points:
        buy_dates = pd.to_datetime([p["date"] for p in buy_points])
        buy_prices = [p["price"] for p in buy_points]
        ax1_twin.scatter(buy_dates, buy_prices, marker="^", color="red", s=100, label="买入", zorder=5)
    if sell_points:
        sell_dates = pd.to_datetime([p["date"] for p in sell_points])
        sell_prices = [p["price"] for p in sell_points]
        ax1_twin.scatter(sell_dates, sell_prices, marker="v", color="green", s=100, label="卖出", zorder=5)

    bbox_props = dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.8)
    text_origin = (
        f"【传统真实】\n"
        f"累计收益: {metrics_origin['累计收益率']:.2%}\n"
        f"年化收益: {metrics_origin['年化收益率']:.2%}\n"
        f"最大回撤: {metrics_origin['最大回撤']:.2%}\n"
        f"夏普比率: {metrics_origin['夏普比率']:.2f}"
    )
    text_pt = (
        f"【PT重尾长尾方案】\n"
        f"累计收益: {metrics_pt['累计收益率']:.2%}\n"
        f"年化收益: {metrics_pt['年化收益率']:.2%}\n"
        f"最大回撤: {metrics_pt['最大回撤']:.2%}\n"
        f"夏普比率: {metrics_pt['夏普比率']:.2f}"
    )

    ax1.text(0.02, 0.95, text_origin, transform=ax1.transAxes, fontsize=10, verticalalignment="top", bbox=bbox_props)
    ax1.text(0.18, 0.95, text_pt, transform=ax1.transAxes, fontsize=10, verticalalignment="top", bbox=bbox_props)

    title = f"{result['stock']['name']} 净值曲线与股价走势 (PT重尾长尾回测)"
    ax1.set_title(title, fontsize=14)
    ax1.set_ylabel("策略净值", fontsize=12)
    ax1_twin.set_ylabel("股票价格", fontsize=12)

    scatter_handles, scatter_labels = ax1_twin.get_legend_handles_labels()
    all_lines = line1 + line2 + scatter_handles
    all_labels = [line.get_label() for line in line1 + line2] + scatter_labels
    ax1.legend(all_lines, all_labels, loc="upper right")
    ax1.grid(True, alpha=0.3)

    ax2.plot(dates, close, label="收盘价", color="#334155", linewidth=1.5)
    ax2.set_title("历史收盘价", fontsize=14)
    ax2.set_xlabel("日期")
    ax2.set_ylabel("价格")
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    buffer = io.BytesIO()
    plt.savefig(buffer, format="png", dpi=150)
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.read()).decode("utf-8")
    plt.close()
    return image_base64


def write_html_report(result: dict, html_file: str = "backtest_report.html") -> None:
    image_base64 = build_report_image(result)
    trades = result["trades"]["uniform"]

    if trades:
        df_trades_html = pd.DataFrame(trades)

        def color_ret(val):
            color = "#e74c3c" if val > 0 else "#2ecc71"
            return f'<span style="color: {color}; font-weight: bold;">{val:.2%}</span>'

        def color_abs(val):
            color = "#e74c3c" if val > 0 else "#2ecc71"
            return f'<span style="color: {color}; font-weight: bold;">{val:.2f}</span>'

        df_trades_html["收益率"] = df_trades_html["收益率"].apply(color_ret)
        df_trades_html["绝对收益"] = df_trades_html["绝对收益"].apply(color_abs)
        table_html = df_trades_html.to_html(index=False, escape=False, classes="trade-table", border=0)
    else:
        table_html = "<p>区间内无完整交易。</p>"

    stock = result["stock"]
    html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>回测报告 - {stock['name']}</title>
    <style>
        body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #f0f2f5; margin: 0; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
        h1, h2 {{ text-align: center; color: #2c3e50; }}
        .chart-wrapper {{ text-align: center; margin: 30px 0; }}
        .chart-wrapper img {{ max-width: 100%; height: auto; border: 1px solid #eee; border-radius: 4px; }}
        .trade-table {{ width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 14px; }}
        .trade-table th, .trade-table td {{ padding: 12px 15px; text-align: center; border-bottom: 1px solid #eee; }}
        .trade-table th {{ background-color: #34495e; color: #fff; text-transform: uppercase; }}
        .trade-table tr:hover {{ background-color: #f8f9fa; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>量化策略回测报告 - {stock['name']} ({stock['tencentSymbol']})</h1>
        <div class="chart-wrapper">
            <img src="data:image/png;base64,{image_base64}" alt="回测图表">
        </div>
        <h2>历史交易明细</h2>
        {table_html}
    </div>
</body>
</html>
"""
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html_content)


def print_console_report(result: dict) -> None:
    stock = result["stock"]
    date_range = result["dateRange"]
    print("=" * 60)
    print(f"【{stock['name']} {stock['tencentSymbol']}】原始数据行数: {date_range['rows']}")
    print(f"数据区间: {date_range['start']} ~ {date_range['end']}")

    print("\n【样本分桶统计】")
    print(pd.Series(result["bucketStats"]).to_string())

    print(f"\n【PT框架处理完成】混合系数 η = {result['summary']['eta']}")
    print(f"原始收益率均值: {result['summary']['originMean']:.6f}")
    print(f"扰动后收益率均值: {result['summary']['perturbedMean']:.6f}")

    for key, title in [("uniform", "真实"), ("pt", "量子")]:
        print("\n" + "=" * 60)
        print(f"【{title}每次交易买卖点及收益】")
        trades = result["trades"][key]
        if trades:
            df_trades_print = pd.DataFrame(trades)
            df_trades_print["收益率"] = df_trades_print["收益率"].apply(lambda x: f"{x:.2%}")
            print(df_trades_print.to_markdown())
        else:
            print("区间内无完整交易。")

    print("\n" + "=" * 60)
    print("【回测指标对比】")
    print(f"传统真实回测: {result['metrics']['uniform']}")
    print(f"PT重尾长尾方案回测: {result['metrics']['pt']}")

    print("\n" + "=" * 60)
    print("【前10条长尾极端行情样本】")
    print(pd.DataFrame(result["tailSamples"]).to_string(index=False))


def main():
    parser = argparse.ArgumentParser(description="PT 重尾长尾策略回测")
    parser.add_argument("--symbol", default="688027.SS", help="股票代码，支持腾讯源代码，如 688027.SS、AAPL、0700.HK")
    parser.add_argument("--name", default="国盾量子", help="股票显示名称")
    parser.add_argument("--start", default="20220101", help="开始日期，如 20220101")
    parser.add_argument("--end", default=datetime.now().strftime("%Y%m%d"), help="结束日期，如 20260601")
    parser.add_argument("--eta", type=float, default=0.5, help="PT 混合系数")
    parser.add_argument("--json-output", default="", help="把结构化回测结果写入指定 JSON 文件")
    parser.add_argument("--html-output", default="backtest_report.html", help="HTML 报告路径")
    parser.add_argument("--no-html", action="store_true", help="不生成 HTML 报告")
    args = parser.parse_args()

    result = run_backtest(args.symbol, args.name, args.start, args.end, args.eta)

    if args.json_output:
        with open(args.json_output, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False)

    print_console_report(result)

    if not args.no_html:
        write_html_report(result, args.html_output)
        print(f"\n============================================================")
        print(f"回测 HTML 报告已生成完毕！请在浏览器中打开查看：{args.html_output}")


if __name__ == "__main__":
    main()
