import argparse
import hashlib
import json
import math
import os
import time
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import pandas as pd

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

from classic_strategy import compute_classic_strategy
from pt_strategy import compute_pt_strategy

warnings.filterwarnings("ignore")


if not hasattr(pd.DataFrame, "append"):
    def _compat_dataframe_append(self, other, ignore_index=False, **_kwargs):
        if isinstance(other, dict):
            other = pd.DataFrame([other])
        elif isinstance(other, pd.Series):
            other = other.to_frame().T
        return pd.concat([self, other], ignore_index=ignore_index)

    pd.DataFrame.append = _compat_dataframe_append


TRAINING_UNIVERSE = {
    "A股": [
        {"symbol": "600519.SS", "name": "贵州茅台"},
        {"symbol": "601318.SS", "name": "中国平安"},
        {"symbol": "600036.SS", "name": "招商银行"},
        {"symbol": "600900.SS", "name": "长江电力"},
        {"symbol": "601398.SS", "name": "工商银行"},
        {"symbol": "601988.SS", "name": "中国银行"},
        {"symbol": "601288.SS", "name": "农业银行"},
        {"symbol": "601328.SS", "name": "交通银行"},
        {"symbol": "601166.SS", "name": "兴业银行"},
        {"symbol": "600030.SS", "name": "中信证券"},
        {"symbol": "600276.SS", "name": "恒瑞医药"},
        {"symbol": "601899.SS", "name": "紫金矿业"},
        {"symbol": "600887.SS", "name": "伊利股份"},
        {"symbol": "601088.SS", "name": "中国神华"},
        {"symbol": "600309.SS", "name": "万华化学"},
        {"symbol": "600406.SS", "name": "国电南瑞"},
        {"symbol": "600809.SS", "name": "山西汾酒"},
        {"symbol": "601012.SS", "name": "隆基绿能"},
        {"symbol": "601857.SS", "name": "中国石油"},
        {"symbol": "600028.SS", "name": "中国石化"},
        {"symbol": "688027.SS", "name": "国盾量子"},
        {"symbol": "688981.SS", "name": "中芯国际"},
        {"symbol": "688111.SS", "name": "金山办公"},
        {"symbol": "688012.SS", "name": "中微公司"},
        {"symbol": "688036.SS", "name": "传音控股"},
        {"symbol": "000858.SZ", "name": "五粮液"},
        {"symbol": "000333.SZ", "name": "美的集团"},
        {"symbol": "000651.SZ", "name": "格力电器"},
        {"symbol": "000001.SZ", "name": "平安银行"},
        {"symbol": "000002.SZ", "name": "万科A"},
        {"symbol": "000568.SZ", "name": "泸州老窖"},
        {"symbol": "000725.SZ", "name": "京东方A"},
        {"symbol": "000776.SZ", "name": "广发证券"},
        {"symbol": "000063.SZ", "name": "中兴通讯"},
        {"symbol": "000895.SZ", "name": "双汇发展"},
        {"symbol": "002027.SZ", "name": "分众传媒"},
        {"symbol": "002142.SZ", "name": "宁波银行"},
        {"symbol": "002230.SZ", "name": "科大讯飞"},
        {"symbol": "002304.SZ", "name": "洋河股份"},
        {"symbol": "002415.SZ", "name": "海康威视"},
        {"symbol": "002594.SZ", "name": "比亚迪"},
        {"symbol": "002714.SZ", "name": "牧原股份"},
        {"symbol": "300014.SZ", "name": "亿纬锂能"},
        {"symbol": "300015.SZ", "name": "爱尔眼科"},
        {"symbol": "300059.SZ", "name": "东方财富"},
        {"symbol": "300124.SZ", "name": "汇川技术"},
        {"symbol": "300274.SZ", "name": "阳光电源"},
        {"symbol": "300498.SZ", "name": "温氏股份"},
        {"symbol": "300750.SZ", "name": "宁德时代"},
        {"symbol": "300760.SZ", "name": "迈瑞医疗"},
    ],
    "美股": [
        {"symbol": "AAPL", "name": "Apple"},
        {"symbol": "MSFT", "name": "Microsoft"},
        {"symbol": "NVDA", "name": "NVIDIA"},
        {"symbol": "GOOGL", "name": "Alphabet A"},
        {"symbol": "GOOG", "name": "Alphabet C"},
        {"symbol": "AMZN", "name": "Amazon"},
        {"symbol": "META", "name": "Meta"},
        {"symbol": "TSLA", "name": "Tesla"},
        {"symbol": "BRK-B", "name": "Berkshire Hathaway"},
        {"symbol": "JPM", "name": "JPMorgan Chase"},
        {"symbol": "V", "name": "Visa"},
        {"symbol": "MA", "name": "Mastercard"},
        {"symbol": "LLY", "name": "Eli Lilly"},
        {"symbol": "AVGO", "name": "Broadcom"},
        {"symbol": "WMT", "name": "Walmart"},
        {"symbol": "UNH", "name": "UnitedHealth"},
        {"symbol": "XOM", "name": "Exxon Mobil"},
        {"symbol": "COST", "name": "Costco"},
        {"symbol": "ORCL", "name": "Oracle"},
        {"symbol": "NFLX", "name": "Netflix"},
        {"symbol": "AMD", "name": "AMD"},
        {"symbol": "CRM", "name": "Salesforce"},
        {"symbol": "ADBE", "name": "Adobe"},
        {"symbol": "CSCO", "name": "Cisco"},
        {"symbol": "ACN", "name": "Accenture"},
        {"symbol": "BAC", "name": "Bank of America"},
        {"symbol": "KO", "name": "Coca-Cola"},
        {"symbol": "PEP", "name": "PepsiCo"},
        {"symbol": "MCD", "name": "McDonald's"},
        {"symbol": "DIS", "name": "Disney"},
        {"symbol": "INTC", "name": "Intel"},
        {"symbol": "IBM", "name": "IBM"},
        {"symbol": "QCOM", "name": "Qualcomm"},
        {"symbol": "TXN", "name": "Texas Instruments"},
        {"symbol": "AMAT", "name": "Applied Materials"},
        {"symbol": "GE", "name": "GE Aerospace"},
        {"symbol": "CAT", "name": "Caterpillar"},
        {"symbol": "BA", "name": "Boeing"},
        {"symbol": "GS", "name": "Goldman Sachs"},
        {"symbol": "MS", "name": "Morgan Stanley"},
        {"symbol": "HD", "name": "Home Depot"},
        {"symbol": "NKE", "name": "Nike"},
        {"symbol": "SBUX", "name": "Starbucks"},
        {"symbol": "TMO", "name": "Thermo Fisher"},
        {"symbol": "ABT", "name": "Abbott"},
        {"symbol": "MRK", "name": "Merck"},
        {"symbol": "PFE", "name": "Pfizer"},
        {"symbol": "T", "name": "AT&T"},
        {"symbol": "PLTR", "name": "Palantir"},
        {"symbol": "COIN", "name": "Coinbase"},
    ],
    "港股": [
        {"symbol": "0700.HK", "name": "腾讯控股"},
        {"symbol": "9988.HK", "name": "阿里巴巴-W"},
        {"symbol": "3690.HK", "name": "美团-W"},
        {"symbol": "9618.HK", "name": "京东集团-SW"},
        {"symbol": "1810.HK", "name": "小米集团-W"},
        {"symbol": "1299.HK", "name": "友邦保险"},
        {"symbol": "0941.HK", "name": "中国移动"},
        {"symbol": "0883.HK", "name": "中国海洋石油"},
        {"symbol": "2318.HK", "name": "中国平安"},
        {"symbol": "0939.HK", "name": "建设银行"},
        {"symbol": "1398.HK", "name": "工商银行"},
        {"symbol": "3988.HK", "name": "中国银行"},
        {"symbol": "1211.HK", "name": "比亚迪股份"},
        {"symbol": "1024.HK", "name": "快手-W"},
        {"symbol": "9999.HK", "name": "网易-S"},
        {"symbol": "2015.HK", "name": "理想汽车-W"},
        {"symbol": "9868.HK", "name": "小鹏汽车-W"},
        {"symbol": "0981.HK", "name": "中芯国际"},
        {"symbol": "0388.HK", "name": "香港交易所"},
        {"symbol": "0005.HK", "name": "汇丰控股"},
        {"symbol": "0011.HK", "name": "恒生银行"},
        {"symbol": "0002.HK", "name": "中电控股"},
        {"symbol": "0003.HK", "name": "香港中华煤气"},
        {"symbol": "0016.HK", "name": "新鸿基地产"},
        {"symbol": "0027.HK", "name": "银河娱乐"},
        {"symbol": "0066.HK", "name": "港铁公司"},
        {"symbol": "0175.HK", "name": "吉利汽车"},
        {"symbol": "0241.HK", "name": "阿里健康"},
        {"symbol": "0267.HK", "name": "中信股份"},
        {"symbol": "0288.HK", "name": "万洲国际"},
        {"symbol": "0291.HK", "name": "华润啤酒"},
        {"symbol": "0322.HK", "name": "康师傅控股"},
        {"symbol": "0386.HK", "name": "中国石油化工股份"},
        {"symbol": "0669.HK", "name": "创科实业"},
        {"symbol": "0762.HK", "name": "中国联通"},
        {"symbol": "0823.HK", "name": "领展房产基金"},
        {"symbol": "0857.HK", "name": "中国石油股份"},
        {"symbol": "0960.HK", "name": "龙湖集团"},
        {"symbol": "1038.HK", "name": "长江基建集团"},
        {"symbol": "1044.HK", "name": "恒安国际"},
        {"symbol": "1093.HK", "name": "石药集团"},
        {"symbol": "1109.HK", "name": "华润置地"},
        {"symbol": "1113.HK", "name": "长实集团"},
        {"symbol": "1177.HK", "name": "中国生物制药"},
        {"symbol": "1928.HK", "name": "金沙中国有限公司"},
        {"symbol": "2269.HK", "name": "药明生物"},
        {"symbol": "2382.HK", "name": "舜宇光学科技"},
        {"symbol": "2388.HK", "name": "中银香港"},
        {"symbol": "2628.HK", "name": "中国人寿"},
        {"symbol": "2899.HK", "name": "紫金矿业"},
    ],
    "加密货币": [
        {"symbol": "BTC-USD", "name": "Bitcoin"},
        {"symbol": "ETH-USD", "name": "Ethereum"},
        {"symbol": "BNB-USD", "name": "BNB"},
        {"symbol": "SOL-USD", "name": "Solana"},
        {"symbol": "XRP-USD", "name": "XRP"},
        {"symbol": "DOGE-USD", "name": "Dogecoin"},
        {"symbol": "ADA-USD", "name": "Cardano"},
        {"symbol": "TRX-USD", "name": "TRON"},
        {"symbol": "AVAX-USD", "name": "Avalanche"},
        {"symbol": "LINK-USD", "name": "Chainlink"},
        {"symbol": "DOT-USD", "name": "Polkadot"},
        {"symbol": "LTC-USD", "name": "Litecoin"},
        {"symbol": "BCH-USD", "name": "Bitcoin Cash"},
        {"symbol": "UNI-USD", "name": "Uniswap"},
        {"symbol": "AAVE-USD", "name": "Aave"},
        {"symbol": "ETC-USD", "name": "Ethereum Classic"},
        {"symbol": "XLM-USD", "name": "Stellar"},
        {"symbol": "HBAR-USD", "name": "Hedera"},
        {"symbol": "FIL-USD", "name": "Filecoin"},
        {"symbol": "ATOM-USD", "name": "Cosmos"},
        {"symbol": "NEAR-USD", "name": "NEAR Protocol"},
        {"symbol": "APT-USD", "name": "Aptos"},
        {"symbol": "ARB-USD", "name": "Arbitrum"},
        {"symbol": "OP-USD", "name": "Optimism"},
        {"symbol": "ICP-USD", "name": "Internet Computer"},
        {"symbol": "INJ-USD", "name": "Injective"},
        {"symbol": "RNDR-USD", "name": "Render"},
        {"symbol": "MKR-USD", "name": "Maker"},
        {"symbol": "GRT-USD", "name": "The Graph"},
        {"symbol": "SAND-USD", "name": "The Sandbox"},
        {"symbol": "MANA-USD", "name": "Decentraland"},
        {"symbol": "AXS-USD", "name": "Axie Infinity"},
        {"symbol": "FTM-USD", "name": "Fantom"},
        {"symbol": "ALGO-USD", "name": "Algorand"},
        {"symbol": "VET-USD", "name": "VeChain"},
        {"symbol": "THETA-USD", "name": "Theta Network"},
        {"symbol": "EOS-USD", "name": "EOS"},
        {"symbol": "XTZ-USD", "name": "Tezos"},
        {"symbol": "KAVA-USD", "name": "Kava"},
        {"symbol": "FLOW-USD", "name": "Flow"},
        {"symbol": "CHZ-USD", "name": "Chiliz"},
        {"symbol": "ZEC-USD", "name": "Zcash"},
        {"symbol": "DASH-USD", "name": "Dash"},
        {"symbol": "COMP-USD", "name": "Compound"},
        {"symbol": "SNX-USD", "name": "Synthetix"},
        {"symbol": "CRV-USD", "name": "Curve DAO"},
        {"symbol": "DYDX-USD", "name": "dYdX"},
        {"symbol": "1INCH-USD", "name": "1inch"},
        {"symbol": "ENJ-USD", "name": "Enjin Coin"},
        {"symbol": "BAT-USD", "name": "Basic Attention Token"},
    ],
}


DEFAULT_Q_HEADS = [0.7, 0.75, 0.8, 0.85]
DEFAULT_Q_TAILS = [0.9, 0.93, 0.95, 0.97]
DEFAULT_ETAS = [0.2, 0.35, 0.5, 0.65, 0.8]
DEFAULT_MODES = [
    "no_transform",
    "tail_denoise",
    "pt_amplify",
    "trend_smooth",
    "vol_squeeze",
    "downside_guard",
    "momentum_regime",
    "crypto_trend_guard",
]
DEFAULT_VALIDATION_FRACTION = 0.3
DEFAULT_SPLIT_SEED = "pt-trading-v1"
DEFAULT_CV_FOLDS = 5
DEFAULT_CACHE_DIR = Path(".tmp/training_data_cache")
DEFAULT_DATA_DIR = Path("data")
TENCENT_SOURCE_ALIASES = {"tencent", "腾讯"}


def parse_float_grid(value: str, fallback: list[float]) -> list[float]:
    if not value:
        return fallback
    return [float(item.strip()) for item in value.split(",") if item.strip()]


def parse_string_grid(value: str, fallback: list[str]) -> list[str]:
    if not value:
        return fallback
    return [item.strip() for item in value.split(",") if item.strip()]


def build_parameter_grid(q_heads: list[float], q_tails: list[float], etas: list[float], modes: list[str]) -> list[dict]:
    grid = []
    for mode in modes:
        if mode == "no_transform":
            grid.append({"mode": mode, "qHead": q_heads[0], "qTail": q_tails[0], "eta": etas[0]})
            continue
        for q_head in q_heads:
            for q_tail in q_tails:
                if q_tail <= q_head:
                    continue
                for eta in etas:
                    grid.append({"mode": mode, "qHead": q_head, "qTail": q_tail, "eta": eta})
    return grid


def normalize_a_share_symbol(symbol: str) -> str:
    return symbol.upper().replace(".SS", "").replace(".SZ", "").replace(".BJ", "")


def normalize_tencent_symbol(symbol: str) -> str:
    code = normalize_a_share_symbol(symbol)
    if symbol.upper().endswith(".BJ") or code.startswith(("4", "8", "920")):
        prefix = "bj"
    else:
        prefix = "sh" if symbol.upper().endswith(".SS") or code.startswith(("6", "9")) else "sz"
    return f"{prefix}{code}"


def normalize_hk_symbol(symbol: str) -> str:
    return symbol.upper().replace(".HK", "").zfill(5)


def tencent_date(value: str) -> str:
    return pd.to_datetime(value).strftime("%Y-%m-%d")


def tencent_kline_count(start_date: str, end_date: str) -> int:
    days = max(1, (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days + 1)
    return min(2000, max(10, days * 2))


def normalize_tencent_market_symbol(symbol: str, market: str) -> list[str]:
    code = symbol.strip().upper()
    if market == "A股":
        return [normalize_tencent_symbol(code)]
    if market == "港股":
        return [f"hk{normalize_hk_symbol(code)}"]
    if market == "美股":
        ticker = code.replace("-", ".")
        if ticker.endswith((".OQ", ".N", ".A")):
            return [f"us{ticker}"]
        return [f"us{ticker}.OQ", f"us{ticker}.N", f"us{ticker}.A"]
    raise RuntimeError(f"当前只允许腾讯源，但暂未配置 {market} 的腾讯历史 K 线接口: {symbol}")


def get_tencent_history_data(symbol: str, market: str, start_date: str, end_date: str, download_timeout: float) -> pd.DataFrame:
    try:
        import requests
    except ImportError as error:
        raise RuntimeError("本地未安装 requests，无法访问腾讯行情源") from error

    last_error = None
    tencent_urls = [
        "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get",
        "https://ifzq.gtimg.cn/appstock/app/fqkline/get",
        "https://proxy.finance.qq.com/ifzqgtimg/appstock/app/fqkline/get",
    ]
    for tencent_symbol in normalize_tencent_market_symbol(symbol, market):
        adjust = "" if market == "美股" else "qfq"
        params = {
            "param": (
                f"{tencent_symbol},day,{tencent_date(start_date)},"
                f"{tencent_date(end_date)},{tencent_kline_count(start_date, end_date)},{adjust}"
            )
        }
        for url in tencent_urls:
            try:
                response = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=download_timeout)
                response.raise_for_status()
                payload = response.json()
                payload_data = payload.get("data", {})
                data = payload_data.get(tencent_symbol, {}) if isinstance(payload_data, dict) else {}
                rows = data.get("qfqday") or data.get("day") or []
                if not rows:
                    last_error = f"{tencent_symbol} 未返回历史 K 线"
                    continue
                raw = pd.DataFrame([row[:6] for row in rows], columns=["date", "open", "close", "high", "low", "volume"])
                return normalize_training_price_frame(raw, "腾讯历史 K 线源", symbol)
            except Exception as error:
                last_error = error
    detail = f": {last_error}" if last_error else ""
    raise RuntimeError(f"腾讯源未返回历史 K 线，请检查代码、市场或日期区间: {symbol}{detail}")


def normalize_training_price_frame(df: pd.DataFrame, source_name: str, symbol: str) -> pd.DataFrame:
    required_columns = ["date", "open", "high", "low", "close", "volume"]
    missing_columns = [column for column in required_columns if column not in df.columns]
    if missing_columns:
        raise RuntimeError(f"{source_name} 数据缺少字段: {', '.join(missing_columns)}")

    optional_feature_columns = [
        column
        for column in ["daily_ret", "daily_ret_abs", "vol_20d"]
        if column in df.columns
    ]
    work_df = df[required_columns + optional_feature_columns].copy()
    work_df["date"] = pd.to_datetime(work_df["date"])
    work_df = work_df.set_index("date").sort_index()
    for column in ["open", "high", "low", "close", "volume"]:
        work_df[column] = pd.to_numeric(work_df[column], errors="coerce")

    if {"daily_ret", "daily_ret_abs", "vol_20d"}.issubset(work_df.columns):
        for column in ["daily_ret", "daily_ret_abs", "vol_20d"]:
            work_df[column] = pd.to_numeric(work_df[column], errors="coerce")
    else:
        work_df["daily_ret"] = work_df["close"].pct_change()
        work_df["daily_ret_abs"] = work_df["daily_ret"].abs()
        work_df["vol_20d"] = work_df["daily_ret"].rolling(window=20).std()
    work_df = work_df.dropna()
    if len(work_df) < 40:
        raise RuntimeError(f"{source_name} 可用历史数据不足，无法训练: {symbol}")
    return work_df


def should_use_tencent_source(market: str, data_source: str) -> bool:
    source = data_source.lower()
    return source in TENCENT_SOURCE_ALIASES


def get_training_stock_data(
    symbol: str,
    market: str,
    start_date: str,
    end_date: str,
    data_source: str,
    download_timeout: float,
) -> pd.DataFrame:
    if should_use_tencent_source(market, data_source):
        return get_tencent_history_data(symbol, market, start_date, end_date, download_timeout)
    raise RuntimeError(f"当前已按要求禁用非腾讯数据源: {data_source}")


def cache_key(symbol: str, start_date: str, end_date: str, data_source: str) -> str:
    safe_symbol = symbol.replace("/", "_").replace("\\", "_").replace(":", "_")
    safe_source = data_source.replace("/", "_").replace("\\", "_").replace(":", "_")
    return f"{safe_source}-{safe_symbol}-{start_date}-{end_date}.csv"


def data_csv_path(symbol: str, market: str, data_dir: Path = DEFAULT_DATA_DIR) -> Path:
    safe_market = market.replace("/", "_").replace("\\", "_").replace(":", "_")
    safe_symbol = symbol.replace("/", "_").replace("\\", "_").replace(":", "_")
    return data_dir / f"{safe_market}_{safe_symbol}.csv"


def save_market_data_csv(df: pd.DataFrame, symbol: str, market: str, name: str, data_dir: Path = DEFAULT_DATA_DIR) -> Path:
    data_dir.mkdir(parents=True, exist_ok=True)
    path = data_csv_path(symbol, market, data_dir)
    export = df.reset_index().copy()
    export.insert(1, "market", market)
    export.insert(2, "symbol", symbol)
    export.insert(3, "name", name)
    export.to_csv(path, index=False)
    return path


def load_market_data_csv(symbol: str, market: str, start_date: str, end_date: str, data_dir: Path = DEFAULT_DATA_DIR) -> pd.DataFrame | None:
    path = data_csv_path(symbol, market, data_dir)
    if not path.exists():
        return None
    raw = pd.read_csv(path)
    frame = normalize_training_price_frame(raw, "本地腾讯 CSV", symbol)
    start_ts = pd.to_datetime(start_date)
    end_ts = pd.to_datetime(end_date)
    frame = frame[(frame.index >= start_ts) & (frame.index <= end_ts)]
    if len(frame) < 40:
        return None
    return frame


def load_or_download_stock_data(
    symbol: str,
    market: str,
    start_date: str,
    end_date: str,
    cache_dir: Path,
    refresh_cache: bool,
    data_source: str,
    download_timeout: float,
    data_dir: Path = DEFAULT_DATA_DIR,
    stock_name: str = "",
) -> pd.DataFrame:
    if not refresh_cache:
        local_df = load_market_data_csv(symbol, market, start_date, end_date, data_dir)
        if local_df is not None:
            return local_df

    cache_dir.mkdir(parents=True, exist_ok=True)
    effective_source = "tencent"
    cache_path = cache_dir / cache_key(symbol, start_date, end_date, effective_source)
    if cache_path.exists() and not refresh_cache:
        df = pd.read_csv(cache_path, parse_dates=["date"])
        df = df.set_index("date")
        return df

    df = get_training_stock_data(symbol, market, start_date, end_date, data_source, download_timeout)
    save_market_data_csv(df, symbol, market, stock_name or symbol, data_dir)
    df.reset_index().to_csv(cache_path, index=False)
    return df


def metric_value(metrics: dict, key: str) -> float:
    value = metrics.get(key, 0)
    if value is None or math.isnan(float(value)):
        return 0.0
    return float(value)


def score_candidate(baseline: dict, candidate: dict) -> float:
    total_gain = metric_value(candidate, "累计收益率") - metric_value(baseline, "累计收益率")
    annual_gain = metric_value(candidate, "年化收益率") - metric_value(baseline, "年化收益率")
    sharpe_gain = metric_value(candidate, "夏普比率") - metric_value(baseline, "夏普比率")
    drawdown_reduction = abs(metric_value(baseline, "最大回撤")) - abs(metric_value(candidate, "最大回撤"))
    score = total_gain * 0.9 + annual_gain * 0.5 + sharpe_gain * 1.0 + drawdown_reduction * 1.6
    if total_gain < 0:
        score += total_gain * 0.5
    if sharpe_gain < 0:
        score += sharpe_gain * 0.7
    if drawdown_reduction < 0:
        score += drawdown_reduction * 1.6
    return round(score, 6)


def params_key(item: dict) -> tuple[str, float, float, float]:
    return (
        str(item.get("mode", "tail_denoise")),
        float(item["qHead"]),
        float(item["qTail"]),
        float(item["eta"]),
    )


def format_metrics(metrics: dict) -> dict:
    return {
        "totalReturn": metric_value(metrics, "累计收益率"),
        "annualReturn": metric_value(metrics, "年化收益率"),
        "maxDrawdown": metric_value(metrics, "最大回撤"),
        "winRate": metric_value(metrics, "胜率"),
        "sharpe": metric_value(metrics, "夏普比率"),
    }


def format_improvement(baseline: dict, candidate: dict) -> dict:
    return {
        "totalReturn": round(metric_value(candidate, "累计收益率") - metric_value(baseline, "累计收益率"), 6),
        "annualReturn": round(metric_value(candidate, "年化收益率") - metric_value(baseline, "年化收益率"), 6),
        "sharpe": round(metric_value(candidate, "夏普比率") - metric_value(baseline, "夏普比率"), 6),
        "maxDrawdown": round(abs(metric_value(baseline, "最大回撤")) - abs(metric_value(candidate, "最大回撤")), 6),
    }


def evaluate_single_stock(stock: dict, market: str, df_raw: pd.DataFrame, grid: list[dict]) -> dict:
    baseline_result = compute_classic_strategy(df_raw)
    baseline_metrics = baseline_result["metrics"]
    candidates = []

    for params in grid:
        pt_result = compute_pt_strategy(
            df_raw,
            q_head=params["qHead"],
            q_tail=params["qTail"],
            eta_param=params["eta"],
            mode=params["mode"],
        )
        metrics = pt_result["metrics"]
        candidates.append(
            {
                "mode": params["mode"],
                "qHead": params["qHead"],
                "qTail": params["qTail"],
                "eta": params["eta"],
                "metrics": metrics,
                "improvement": format_improvement(baseline_metrics, metrics),
                "score": score_candidate(baseline_metrics, metrics),
            }
        )

    best = max(candidates, key=lambda item: item["score"])
    best_metrics = best["metrics"]

    return {
        "market": market,
        "symbol": stock["symbol"],
        "name": stock["name"],
        "rows": int(len(df_raw)),
        "baseline": format_metrics(baseline_metrics),
        "best": {
            "mode": best["mode"],
            "qHead": best["qHead"],
            "qTail": best["qTail"],
            "eta": best["eta"],
            "score": best["score"],
            "metrics": format_metrics(best_metrics),
            "improvement": best["improvement"],
        },
        "candidateScores": [
            {
                "mode": candidate["mode"],
                "qHead": candidate["qHead"],
                "qTail": candidate["qTail"],
                "eta": candidate["eta"],
                "metrics": format_metrics(candidate["metrics"]),
                "improvement": candidate["improvement"],
                "score": candidate["score"],
            }
            for candidate in candidates
        ],
        "topCandidates": sorted(candidates, key=lambda item: item["score"], reverse=True)[:5],
    }


def stable_split_value(seed: str, market: str, symbol: str) -> int:
    digest = hashlib.sha256(f"{seed}|{market}|{symbol}".encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def assign_train_validation_split(stock_results: list[dict], validation_fraction: float, split_seed: str) -> None:
    for market in TRAINING_UNIVERSE.keys():
        rows = [item for item in stock_results if item["market"] == market]
        if not rows:
            continue
        rows.sort(key=lambda item: stable_split_value(split_seed, item["market"], item["symbol"]))
        validation_count = 0
        if len(rows) >= 2:
            validation_count = max(1, int(round(len(rows) * validation_fraction)))
            validation_count = min(validation_count, len(rows) - 1)
        validation_symbols = {item["symbol"] for item in rows[:validation_count]} if validation_count else set()
        for item in rows:
            item["split"] = "validation" if item["symbol"] in validation_symbols else "train"


def find_candidate(stock_result: dict, key: tuple[float, float, float]) -> dict | None:
    for candidate in stock_result["candidateScores"]:
        if params_key(candidate) == key:
            return candidate
    return None


def robustness_gate_thresholds(rows: list[dict]) -> dict:
    markets = {row.get("market") for row in rows}
    if markets == {"A股"}:
        return {
            "returnRate": 0.55,
            "sharpeRate": 0.55,
            "drawdownRate": 0.50,
            "allRate": 0.35,
        }
    return {
        "returnRate": 0.70,
        "sharpeRate": 0.70,
        "drawdownRate": 0.65,
        "allRate": 0.55,
    }


def select_best_params(rows: list[dict], grid: list[dict]) -> dict | None:
    if not rows:
        return None
    best = None
    fallback_no_transform = None
    thresholds = robustness_gate_thresholds(rows)
    for params in grid:
        key = params_key(params)
        scores = []
        improvements = []
        for row in rows:
            candidate = find_candidate(row, key)
            if candidate:
                scores.append(float(candidate["score"]))
                improvements.append(candidate["improvement"])
        if not scores:
            continue
        count = len(scores)
        return_rate = sum(1 for item in improvements if item["totalReturn"] > 0) / count
        sharpe_rate = sum(1 for item in improvements if item["sharpe"] > 0) / count
        drawdown_rate = sum(1 for item in improvements if item["maxDrawdown"] > 0) / count
        all_rate = sum(
            1
            for item in improvements
            if item["totalReturn"] > 0 and item["sharpe"] > 0 and item["maxDrawdown"] > 0
        ) / count
        avg_score = sum(scores) / count
        avg_improvement = average_metric_group(improvements)
        robustness_score = (
            avg_score
            + return_rate * 0.08
            + sharpe_rate * 0.10
            + drawdown_rate * 0.18
            + all_rate * 0.16
        )
        contender = {
            "mode": params["mode"],
            "qHead": params["qHead"],
            "qTail": params["qTail"],
            "eta": params["eta"],
            "avgScore": round(avg_score, 6),
            "robustnessScore": round(robustness_score, 6),
            "returnImprovedRate": round(return_rate, 6),
            "sharpeImprovedRate": round(sharpe_rate, 6),
            "drawdownImprovedRate": round(drawdown_rate, 6),
            "allObjectivesImprovedRate": round(all_rate, 6),
            "avgImprovement": avg_improvement,
            "stocks": count,
        }
        if params["mode"] == "no_transform":
            fallback_no_transform = contender
            continue

        is_eligible = (
            avg_score > 0
            and avg_improvement.get("totalReturn", 0) > 0
            and avg_improvement.get("sharpe", 0) > 0
            and avg_improvement.get("maxDrawdown", 0) > 0
            and return_rate >= thresholds["returnRate"]
            and sharpe_rate >= thresholds["sharpeRate"]
            and drawdown_rate >= thresholds["drawdownRate"]
            and all_rate >= thresholds["allRate"]
        )
        if not is_eligible:
            continue
        if best is None or contender["robustnessScore"] > best["robustnessScore"]:
            best = contender
    return best or fallback_no_transform


def evaluate_fixed_params(rows: list[dict], params: dict | None) -> dict:
    if not rows or not params:
        return empty_evidence()

    key = params_key(params)
    candidate_rows = []
    baselines = []
    metrics = []
    improvements = []
    scores = []
    for row in rows:
        candidate = find_candidate(row, key)
        if not candidate:
            continue
        candidate_rows.append(row)
        baselines.append(row["baseline"])
        metrics.append(candidate["metrics"])
        improvements.append(candidate["improvement"])
        scores.append(float(candidate["score"]))

    if not candidate_rows:
        return empty_evidence()

    return summarize_evidence(baselines, metrics, improvements, scores)


def summarize_evidence(baselines: list[dict], metrics: list[dict], improvements: list[dict], scores: list[float]) -> dict:
    if not improvements:
        return empty_evidence()
    positive_score = sum(1 for value in scores if value > 0)
    return_improved = sum(1 for item in improvements if item["totalReturn"] > 0)
    sharpe_improved = sum(1 for item in improvements if item["sharpe"] > 0)
    drawdown_improved = sum(1 for item in improvements if item["maxDrawdown"] > 0)
    all_objectives = sum(
        1
        for item in improvements
        if item["totalReturn"] > 0 and item["sharpe"] > 0 and item["maxDrawdown"] > 0
    )
    count = len(improvements)
    return {
        "stocks": count,
        "avgScore": round(sum(scores) / count, 6),
        "positiveScoreRate": round(positive_score / count, 6),
        "returnImprovedRate": round(return_improved / count, 6),
        "sharpeImprovedRate": round(sharpe_improved / count, 6),
        "drawdownImprovedRate": round(drawdown_improved / count, 6),
        "allObjectivesImprovedRate": round(all_objectives / count, 6),
        "avgBaseline": average_metric_group(baselines),
        "avgModel": average_metric_group(metrics),
        "avgImprovement": average_metric_group(improvements),
    }


def fold_index(row: dict, folds: int, split_seed: str) -> int:
    return stable_split_value(f"{split_seed}|cv", row["market"], row["symbol"]) % max(2, folds)


def cross_validate_param_selection(rows: list[dict], grid: list[dict], folds: int, split_seed: str) -> dict:
    if not rows:
        return {"folds": [], "aggregateEvidence": empty_evidence()}

    actual_folds = min(max(2, folds), len(rows))
    fold_results = []
    selected_baselines = []
    selected_metrics = []
    selected_improvements = []
    selected_scores = []
    for fold in range(actual_folds):
        train_rows = [row for row in rows if fold_index(row, actual_folds, split_seed) != fold]
        validation_rows = [row for row in rows if fold_index(row, actual_folds, split_seed) == fold]
        if not train_rows or not validation_rows:
            continue
        params = select_best_params(train_rows, grid)
        evidence = evaluate_fixed_params(validation_rows, params)
        fold_results.append(
            {
                "fold": fold,
                "params": params,
                "validationEvidence": evidence,
            }
        )
        if params:
            key = params_key(params)
            for row in validation_rows:
                candidate = find_candidate(row, key)
                if candidate:
                    selected_baselines.append(row["baseline"])
                    selected_metrics.append(candidate["metrics"])
                    selected_improvements.append(candidate["improvement"])
                    selected_scores.append(float(candidate["score"]))

    if not selected_improvements:
        return {"folds": fold_results, "aggregateEvidence": empty_evidence()}

    return {
        "folds": fold_results,
        "aggregateEvidence": summarize_evidence(
            selected_baselines,
            selected_metrics,
            selected_improvements,
            selected_scores,
        ),
    }


def empty_evidence() -> dict:
    return {
        "stocks": 0,
        "avgScore": 0,
        "positiveScoreRate": 0,
        "returnImprovedRate": 0,
        "sharpeImprovedRate": 0,
        "drawdownImprovedRate": 0,
        "allObjectivesImprovedRate": 0,
        "avgBaseline": {},
        "avgModel": {},
        "avgImprovement": {},
    }


def build_model_summary(stock_results: list[dict], grid: list[dict], cv_folds: int, split_seed: str) -> dict:
    train_rows = [item for item in stock_results if item.get("split") == "train"]
    validation_rows = [item for item in stock_results if item.get("split") == "validation"]
    global_params = select_best_params(train_rows, grid)
    global_cv = cross_validate_param_selection(stock_results, grid, cv_folds, split_seed)

    market_models = []
    for market in TRAINING_UNIVERSE.keys():
        market_rows = [item for item in stock_results if item["market"] == market]
        market_train = [item for item in train_rows if item["market"] == market]
        market_validation = [item for item in validation_rows if item["market"] == market]
        market_params = select_best_params(market_train, grid)
        if not market_params:
            continue
        market_models.append(
            {
                "market": market,
                "params": market_params,
                "trainEvidence": evaluate_fixed_params(market_train, market_params),
                "validationEvidence": evaluate_fixed_params(market_validation, market_params),
                "crossValidation": cross_validate_param_selection(market_rows, grid, cv_folds, split_seed),
            }
        )

    return {
        "globalModel": {
            "params": global_params,
            "trainEvidence": evaluate_fixed_params(train_rows, global_params),
            "validationEvidence": evaluate_fixed_params(validation_rows, global_params),
            "crossValidation": global_cv,
        },
        "marketModels": market_models,
    }


def build_deliverable_model(model_summary: dict, date_range: dict, grid: dict) -> dict:
    global_model = model_summary["globalModel"]
    market_params = {
        item["market"]: {
            "mode": item["params"]["mode"],
            "qHead": item["params"]["qHead"],
            "qTail": item["params"]["qTail"],
            "eta": item["params"]["eta"],
            "validationEvidence": item["validationEvidence"],
            "crossValidation": item["crossValidation"]["aggregateEvidence"],
        }
        for item in model_summary["marketModels"]
    }
    global_params = global_model["params"]
    return {
        "modelName": "PT Heavy Tail OHLCV Transformer",
        "modelVersion": "0.1.0",
        "generatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "trainingRange": date_range,
        "selectionMethod": (
            "Conservative grid search on training split. Transform parameters are selected only when "
            "average return, Sharpe, drawdown, and improvement rates clear market-aware robustness gates; "
            "otherwise the model falls back to no_transform. Validation is reported out-of-sample by symbol split."
        ),
        "parameterGrid": grid,
        "integrationContract": {
            "input": "OHLCV table with columns: open, high, low, close, volume",
            "output": "Transformed OHLCV table with PT model prices: pt_open, pt_high, pt_low, pt_close, pt_volume",
            "institutionUsage": "Run existing trading strategies against the transformed OHLCV columns without changing strategy rules",
        },
        "globalParameters": {
            "mode": global_params["mode"] if global_params else None,
            "qHead": global_params["qHead"] if global_params else None,
            "qTail": global_params["qTail"] if global_params else None,
            "eta": global_params["eta"] if global_params else None,
            "validationEvidence": global_model["validationEvidence"],
            "crossValidation": global_model["crossValidation"]["aggregateEvidence"],
        },
        "marketParameters": market_params,
    }


def summarize_markets(stock_results: list[dict], grid: list[dict]) -> list[dict]:
    summaries = []
    for market in TRAINING_UNIVERSE.keys():
        rows = [item for item in stock_results if item["market"] == market]
        if not rows:
            continue

        param_scores = {}
        for params in grid:
            key = params_key(params)
            matching_scores = []
            for stock in rows:
                for candidate in stock["candidateScores"]:
                    if params_key(candidate) == key:
                        matching_scores.append(candidate["score"])
                        break
            if matching_scores:
                param_scores[key] = sum(matching_scores) / len(matching_scores)

        best_market_key = max(param_scores, key=param_scores.get) if param_scores else None
        best_params = {
            "mode": best_market_key[0],
            "qHead": best_market_key[1],
            "qTail": best_market_key[2],
            "eta": best_market_key[3],
        } if best_market_key else {
            "mode": rows[0]["best"].get("mode", "tail_denoise"),
            "qHead": round(sum(item["best"]["qHead"] for item in rows) / len(rows), 4),
            "qTail": round(sum(item["best"]["qTail"] for item in rows) / len(rows), 4),
            "eta": round(sum(item["best"]["eta"] for item in rows) / len(rows), 4),
        }

        summaries.append(
            {
                "market": market,
                "stocks": len(rows),
                "bestParams": best_params,
                "avgScore": round(sum(item["best"]["score"] for item in rows) / len(rows), 6),
                "avgBaseline": average_metric_group([item["baseline"] for item in rows]),
                "avgBest": average_metric_group([item["best"]["metrics"] for item in rows]),
                "avgImprovement": average_metric_group([item["best"]["improvement"] for item in rows]),
            }
        )
    return summaries


def average_metric_group(groups: list[dict]) -> dict:
    if not groups:
        return {}
    keys = groups[0].keys()
    return {
        key: round(sum(float(group.get(key, 0)) for group in groups) / len(groups), 6)
        for key in keys
    }


def train_model(
    start_date: str,
    end_date: str,
    markets: list[str],
    max_per_market: int | None,
    workers: int,
    q_heads: list[float],
    q_tails: list[float],
    etas: list[float],
    modes: list[str],
    validation_fraction: float,
    split_seed: str,
    cv_folds: int,
    cache_dir: Path,
    refresh_cache: bool,
    download_pause: float,
    data_source: str,
    download_timeout: float,
    data_dir: Path,
) -> dict:
    grid = build_parameter_grid(q_heads, q_tails, etas, modes)
    selected = []
    for market in markets:
        stocks = TRAINING_UNIVERSE.get(market, [])
        if max_per_market:
            stocks = stocks[:max_per_market]
        for stock in stocks:
            selected.append((market, stock))

    stock_results = []
    failures = []
    downloaded = []
    for index, (market, stock) in enumerate(selected, start=1):
        try:
            print(f"[{index}/{len(selected)}] 下载 {market} {stock['symbol']} {stock['name']}", flush=True)
            df_raw = load_or_download_stock_data(
                stock["symbol"],
                market,
                start_date,
                end_date,
                cache_dir,
                refresh_cache,
                data_source,
                download_timeout,
                data_dir,
                stock["name"],
            )
            if len(df_raw) < 80:
                raise RuntimeError("可用历史数据不足")
            downloaded.append((market, stock, df_raw))
            print(f"[{index}/{len(selected)}] 完成 {stock['symbol']}，{len(df_raw)} 行", flush=True)
            if download_pause > 0:
                time.sleep(download_pause)
        except Exception as error:
            print(f"[{index}/{len(selected)}] 失败 {stock['symbol']}: {error}", flush=True)
            failures.append(
                {
                    "market": market,
                    "symbol": stock["symbol"],
                    "name": stock["name"],
                    "error": str(error),
                }
            )

    print(f"开始参数搜索：{len(downloaded)} 只股票 x {len(grid)} 组参数", flush=True)
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = {
            executor.submit(evaluate_single_stock, stock, market, df_raw, grid): (market, stock)
            for market, stock, df_raw in downloaded
        }
        for future in as_completed(futures):
            market, stock = futures[future]
            try:
                stock_results.append(future.result())
                done_count = len(stock_results)
                print(f"[参数搜索] 完成 {done_count}/{len(downloaded)}", flush=True)
            except Exception as error:
                failures.append(
                    {
                        "market": market,
                        "symbol": stock["symbol"],
                        "name": stock["name"],
                        "error": str(error),
                    }
                )

    stock_results.sort(key=lambda item: (item["market"], item["symbol"]))
    assign_train_validation_split(stock_results, validation_fraction, split_seed)
    market_summary = summarize_markets(stock_results, grid)
    model_summary = build_model_summary(stock_results, grid, cv_folds, split_seed)
    grid_summary = {
        "modes": modes,
        "qHeads": q_heads,
        "qTails": q_tails,
        "etas": etas,
        "combinations": len(grid),
    }
    split_counts = {
        "train": sum(1 for item in stock_results if item.get("split") == "train"),
        "validation": sum(1 for item in stock_results if item.get("split") == "validation"),
    }

    return {
        "generatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "dateRange": {"start": start_date, "end": end_date},
        "validationFraction": validation_fraction,
        "splitSeed": split_seed,
        "cvFolds": cv_folds,
        "cache": {
            "dir": str(cache_dir),
            "refresh": refresh_cache,
            "downloadPause": download_pause,
            "downloadTimeout": download_timeout,
            "cachedOrDownloadedStocks": len(downloaded),
        },
        "dataSource": data_source,
        "dataDir": str(data_dir),
        "grid": grid_summary,
        "counts": {
            "requestedStocks": len(selected),
            "successfulStocks": len(stock_results),
            "failedStocks": len(failures),
        },
        "splitCounts": split_counts,
        "modelSummary": model_summary,
        "deliverableModel": build_deliverable_model(
            model_summary,
            {"start": start_date, "end": end_date},
            grid_summary,
        ),
        "marketSummary": market_summary,
        "stockResults": stock_results,
        "failures": failures,
    }


def main() -> None:
    today = datetime.now().strftime("%Y%m%d")
    parser = argparse.ArgumentParser(description="训练 PT 分桶分位数与混合系数")
    parser.add_argument("--start", default="20220101")
    parser.add_argument("--end", default=today)
    parser.add_argument("--markets", default="A股,美股,港股,加密货币")
    parser.add_argument("--max-per-market", type=int, default=None)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--q-heads", default="")
    parser.add_argument("--q-tails", default="")
    parser.add_argument("--etas", default="")
    parser.add_argument("--modes", default="")
    parser.add_argument("--validation-fraction", type=float, default=DEFAULT_VALIDATION_FRACTION)
    parser.add_argument("--split-seed", default=DEFAULT_SPLIT_SEED)
    parser.add_argument("--cv-folds", type=int, default=DEFAULT_CV_FOLDS)
    parser.add_argument("--cache-dir", default=str(DEFAULT_CACHE_DIR))
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR))
    parser.add_argument("--refresh-cache", action="store_true")
    parser.add_argument("--download-pause", type=float, default=0.5)
    parser.add_argument("--download-timeout", type=float, default=15)
    parser.add_argument(
        "--data-source",
        default="tencent",
        choices=["tencent", "腾讯"],
    )
    parser.add_argument("--json-output", default="")
    args = parser.parse_args()

    selected_markets = [item.strip() for item in args.markets.split(",") if item.strip()]
    result = train_model(
        start_date=args.start,
        end_date=args.end,
        markets=selected_markets,
        max_per_market=args.max_per_market,
        workers=args.workers,
        q_heads=parse_float_grid(args.q_heads, DEFAULT_Q_HEADS),
        q_tails=parse_float_grid(args.q_tails, DEFAULT_Q_TAILS),
        etas=parse_float_grid(args.etas, DEFAULT_ETAS),
        modes=parse_string_grid(args.modes, DEFAULT_MODES),
        validation_fraction=args.validation_fraction,
        split_seed=args.split_seed,
        cv_folds=args.cv_folds,
        cache_dir=Path(args.cache_dir),
        refresh_cache=args.refresh_cache,
        download_pause=args.download_pause,
        data_source=args.data_source,
        download_timeout=args.download_timeout,
        data_dir=Path(args.data_dir),
    )

    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.json_output:
        with open(args.json_output, "w", encoding="utf-8") as file:
            file.write(payload)
        summary = {
            "jsonOutput": args.json_output,
            "dataSource": result["dataSource"],
            "counts": result["counts"],
            "splitCounts": result["splitCounts"],
            "globalParameters": result["deliverableModel"]["globalParameters"],
            "marketSummary": result["marketSummary"],
            "failures": result["failures"][:10],
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(payload)


if __name__ == "__main__":
    main()
