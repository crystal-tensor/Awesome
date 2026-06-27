import argparse
import io
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from threading import Lock
from urllib.parse import quote

import pandas as pd
import requests

from model_training import (
    DEFAULT_DATA_DIR,
    TRAINING_UNIVERSE,
    data_csv_path,
    normalize_tencent_market_symbol,
    normalize_training_price_frame,
    save_market_data_csv,
    tencent_date,
    tencent_kline_count,
)


def parse_markets(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def fetch_eastmoney_spot_rows(url: str, fs: str, timeout: float, page_size: int = 100, retries: int = 8) -> list[dict]:
    rows = []
    page = 1
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://quote.eastmoney.com/center/gridlist.html",
    }
    while True:
        params = {
            "pn": page,
            "pz": page_size,
            "po": "1",
            "np": "1",
            "ut": "bd1d9ddb04089700cf9c27f6f7426281",
            "fltt": "2",
            "invt": "2",
            "fid": "f12",
            "fs": fs,
            "fields": "f12,f13,f14",
        }
        last_error = None
        for attempt in range(1, retries + 1):
            try:
                response = session.get(url, params=params, headers=headers, timeout=timeout)
                response.raise_for_status()
                break
            except Exception as error:
                last_error = error
                if attempt < retries:
                    time.sleep(min(2 * attempt, 8))
        else:
            if rows:
                print(f"  清单第 {page} 页请求失败，已保留前 {len(rows)} 条: {last_error}", flush=True)
                break
            raise RuntimeError(f"东方财富清单第 {page} 页请求失败: {last_error}")

        data = response.json().get("data") or {}
        batch = data.get("diff") or []
        if not batch:
            break
        rows.extend(batch)
        print(f"  清单第 {page} 页，累计 {len(rows)} 条", flush=True)
        if len(batch) < page_size:
            break
        page += 1
    return rows


def a_share_symbol_from_code(code: str) -> str:
    clean = str(code).zfill(6)
    if clean.startswith("920"):
        return f"{clean}.BJ"
    if clean.startswith(("6", "9")):
        return f"{clean}.SS"
    if clean.startswith(("4", "8")):
        return f"{clean}.BJ"
    return f"{clean}.SZ"


def normalize_download_price_frame(df: pd.DataFrame, source_name: str, symbol: str) -> pd.DataFrame:
    required_columns = ["date", "open", "high", "low", "close", "volume"]
    missing_columns = [column for column in required_columns if column not in df.columns]
    if missing_columns:
        raise RuntimeError(f"{source_name} 数据缺少字段: {', '.join(missing_columns)}")
    work_df = df[required_columns].copy()
    work_df["date"] = pd.to_datetime(work_df["date"])
    work_df = work_df.set_index("date").sort_index()
    for column in ["open", "high", "low", "close", "volume"]:
        work_df[column] = pd.to_numeric(work_df[column], errors="coerce")
    work_df = work_df.dropna(subset=["open", "high", "low", "close", "volume"])
    if work_df.empty:
        raise RuntimeError(f"{source_name} 未返回可保存历史数据: {symbol}")
    work_df["daily_ret"] = work_df["close"].pct_change()
    work_df["daily_ret_abs"] = work_df["daily_ret"].abs()
    work_df["vol_20d"] = work_df["daily_ret"].rolling(window=20).std()
    return work_df


def get_tencent_history_download_data(symbol: str, market: str, start_date: str, end_date: str, timeout: float) -> pd.DataFrame:
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
                response = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=timeout)
                response.raise_for_status()
                payload = response.json()
                payload_data = payload.get("data", {})
                data = payload_data.get(tencent_symbol, {}) if isinstance(payload_data, dict) else {}
                rows = data.get("qfqday") or data.get("day") or []
                if not rows:
                    last_error = f"{tencent_symbol} 未返回历史 K 线"
                    continue
                raw = pd.DataFrame([row[:6] for row in rows], columns=["date", "open", "close", "high", "low", "volume"])
                return normalize_download_price_frame(raw, "腾讯历史 K 线源", symbol)
            except Exception as error:
                last_error = error
    detail = f": {last_error}" if last_error else ""
    raise RuntimeError(f"腾讯源未返回历史 K 线，请检查代码、市场或日期区间: {symbol}{detail}")


def generated_a_share_candidates() -> list[dict]:
    ranges = [
        range(1, 4000),
        range(300000, 302000),
        range(600000, 606000),
        range(688000, 690000),
        range(430000, 440000),
        range(830000, 840000),
        range(870000, 880000),
        range(920000, 930000),
    ]
    stocks = []
    seen = set()
    for code_range in ranges:
        for value in code_range:
            code = str(value).zfill(6)
            if code in seen:
                continue
            seen.add(code)
            symbol = a_share_symbol_from_code(code)
            stocks.append({"symbol": symbol, "name": symbol})
    return stocks


def load_all_a_share_stocks(timeout: float) -> list[dict]:
    try:
        import akshare as ak
    except ImportError as error:
        raise RuntimeError("本地未安装 AkShare，无法加载全 A股代码清单") from error

    last_error = None
    for attempt in range(1, 4):
        try:
            df = ak.stock_info_a_code_name()
            break
        except Exception as error:
            last_error = error
            print(f"  A股正式清单第 {attempt} 次加载失败: {error}", flush=True)
            time.sleep(min(attempt * 3, 10))
    else:
        print(f"  A股正式清单不可用，改用代码段候选兜底: {last_error}", flush=True)
        return generated_a_share_candidates()

    stocks = []
    for _, row in df.iterrows():
        code = str(row.get("code", "")).strip().zfill(6)
        name = str(row.get("name", "")).strip()
        if code and name and code != "000nan":
            stocks.append({"symbol": a_share_symbol_from_code(code), "name": name})
    return stocks


def load_all_us_stocks(timeout: float) -> list[dict]:
    try:
        rows = fetch_eastmoney_spot_rows(
            "https://72.push2.eastmoney.com/api/qt/clist/get",
            "m:105,m:106,m:107",
            timeout,
        )
        stocks = [
            {"symbol": str(row.get("f12", "")).strip(), "name": str(row.get("f14", "")).strip()}
            for row in rows
            if row.get("f12") and row.get("f14")
        ]
        if len(stocks) >= 500:
            return stocks
        print(f"  东方财富美股清单只有 {len(stocks)} 条，改用 Nasdaq Trader 兜底", flush=True)
    except Exception as error:
        print(f"  东方财富美股清单不可用，改用 Nasdaq Trader 兜底: {error}", flush=True)
    return load_nasdaq_trader_stocks(timeout)


def load_nasdaq_trader_stocks(timeout: float) -> list[dict]:
    urls = [
        ("https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt", "Security Name"),
        ("https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt", "Security Name"),
    ]
    stocks = []
    seen = set()
    headers = {"User-Agent": "Mozilla/5.0"}
    for url, name_column in urls:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        text = "\n".join(line for line in response.text.splitlines() if not line.startswith("File Creation Time"))
        df = pd.read_csv(io.StringIO(text), sep="|")
        symbol_col = "Symbol" if "Symbol" in df.columns else "ACT Symbol"
        for _, row in df.iterrows():
            symbol = str(row.get(symbol_col, "")).strip()
            name = str(row.get(name_column, "")).strip()
            test_issue = str(row.get("Test Issue", "N")).strip().upper()
            is_etf = str(row.get("ETF", "N")).strip().upper() == "Y"
            lowered_name = name.lower()
            non_stock_terms = [
                "warrant",
                "right",
                "unit",
                "fund",
                "etf",
                "etn",
                "trust",
                "notes due",
                "preferred",
                "preference",
            ]
            if (
                not symbol
                or not name
                or test_issue == "Y"
                or is_etf
                or any(term in lowered_name for term in non_stock_terms)
            ):
                continue
            clean_symbol = symbol.replace(".", "-")
            if clean_symbol in seen:
                continue
            seen.add(clean_symbol)
            stocks.append({"symbol": clean_symbol, "name": name.split(" - ")[0]})
    return stocks


def load_all_hk_stocks(timeout: float) -> list[dict]:
    try:
        rows = fetch_eastmoney_spot_rows(
            "https://72.push2.eastmoney.com/api/qt/clist/get",
            "m:128 t:3,m:128 t:4,m:128 t:1,m:128 t:2",
            timeout,
        )
        stocks = [
            {"symbol": f"{str(row.get('f12', '')).strip().zfill(4)}.HK", "name": str(row.get("f14", "")).strip()}
            for row in rows
            if row.get("f12") and row.get("f14")
        ]
        if len(stocks) >= 500:
            return stocks
        print(f"  东方财富港股清单只有 {len(stocks)} 条，改用 AkShare 新浪港股清单", flush=True)
    except Exception as error:
        print(f"  东方财富港股清单不可用，改用 AkShare 新浪港股清单: {error}", flush=True)
    try:
        import akshare as ak

        df = ak.stock_hk_spot()
        return [
            {"symbol": f"{str(row.get('代码', '')).strip().zfill(4)}.HK", "name": str(row.get("中文名称", "")).strip()}
            for _, row in df.iterrows()
            if row.get("代码") and row.get("中文名称")
        ]
    except Exception as error:
        print(f"  AkShare 港股清单不可用，改用港股代码段候选: {error}", flush=True)
        return [{"symbol": f"{code:04d}.HK", "name": f"{code:04d}.HK"} for code in range(1, 10000)]


def normalize_binance_symbol(symbol: str) -> str:
    code = symbol.upper().replace("-USD", "USDT").replace("-USDT", "USDT").replace("/", "")
    aliases = {"RNDRUSDT": "RENDERUSDT"}
    return aliases.get(code, code)


BINANCE_API_BASES = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
    "https://data-api.binance.vision",
]


def binance_get(path: str, timeout: float, **kwargs) -> requests.Response:
    last_error = None
    for base in BINANCE_API_BASES:
        try:
            response = requests.get(f"{base}{path}", timeout=timeout, **kwargs)
            response.raise_for_status()
            return response
        except Exception as error:
            last_error = error
    raise RuntimeError(f"Binance 所有接口均不可用: {last_error}") from last_error


def get_binance_crypto_history_data(symbol: str, start_date: str, end_date: str, timeout: float) -> pd.DataFrame:
    binance_symbol = normalize_binance_symbol(symbol)
    start_ms = int(pd.to_datetime(start_date).timestamp() * 1000)
    end_ms = int(pd.to_datetime(end_date).timestamp() * 1000)
    rows = []
    next_start = start_ms
    while next_start <= end_ms:
        response = binance_get(
            "/api/v3/klines",
            timeout,
            params={
                "symbol": binance_symbol,
                "interval": "1d",
                "startTime": next_start,
                "endTime": end_ms,
                "limit": 1000,
            },
        )
        batch = response.json()
        if not batch:
            break
        rows.extend(batch)
        next_start = int(batch[-1][0]) + 24 * 60 * 60 * 1000
        if len(batch) < 1000:
            break
    if not rows:
        raise RuntimeError(f"Binance 未返回历史 K 线: {symbol}")

    raw = pd.DataFrame(
        rows,
        columns=[
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_asset_volume",
            "number_of_trades",
            "taker_buy_base_volume",
            "taker_buy_quote_volume",
            "ignore",
        ],
    )
    raw["date"] = pd.to_datetime(raw["open_time"], unit="ms")
    return normalize_download_price_frame(raw, "Binance 加密货币源", symbol)


def get_yahoo_crypto_history_data(symbol: str, start_date: str, end_date: str, timeout: float) -> pd.DataFrame:
    period1 = int(pd.to_datetime(start_date).timestamp())
    period2 = int((pd.to_datetime(end_date) + pd.Timedelta(days=1)).timestamp())
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(symbol.upper())}"
    response = requests.get(
        url,
        params={
            "period1": period1,
            "period2": period2,
            "interval": "1d",
            "includePrePost": "false",
            "events": "history",
        },
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    result = (payload.get("chart") or {}).get("result") or []
    if not result:
        raise RuntimeError(f"Yahoo Chart 未返回加密货币历史数据: {symbol}")
    result0 = result[0]
    timestamps = result0.get("timestamp") or []
    quote_rows = ((result0.get("indicators") or {}).get("quote") or [{}])[0]
    if not timestamps or not quote_rows:
        raise RuntimeError(f"Yahoo Chart 历史数据为空: {symbol}")
    raw = pd.DataFrame(
        {
            "date": pd.to_datetime(timestamps, unit="s").normalize(),
            "open": quote_rows.get("open"),
            "high": quote_rows.get("high"),
            "low": quote_rows.get("low"),
            "close": quote_rows.get("close"),
            "volume": quote_rows.get("volume"),
        }
    )
    return normalize_download_price_frame(raw, "Yahoo Chart 加密货币源", symbol)


def get_crypto_history_data(stock: dict, start_date: str, end_date: str, timeout: float) -> pd.DataFrame:
    symbol = stock["symbol"]
    errors = []
    try:
        return get_binance_crypto_history_data(symbol, start_date, end_date, timeout)
    except Exception as error:
        errors.append(f"Binance={error}")
    try:
        return get_yahoo_crypto_history_data(symbol, start_date, end_date, timeout)
    except Exception as error:
        errors.append(f"Yahoo={error}")
    raise RuntimeError("; ".join(errors))


def load_coingecko_market_cap_symbols(timeout: float, pages: int = 4, per_page: int = 250) -> list[dict]:
    symbols = []
    seen = set()
    for page in range(1, pages + 1):
        response = requests.get(
            "https://api.coingecko.com/api/v3/coins/markets",
            params={
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": per_page,
                "page": page,
                "sparkline": "false",
            },
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=timeout,
        )
        response.raise_for_status()
        batch = response.json()
        if not batch:
            break
        for item in batch:
            base = str(item.get("symbol") or "").upper().strip()
            name = str(item.get("name") or base).strip()
            if not base or not base.replace("-", "").replace("_", "").isalnum():
                continue
            symbol = f"{base}-USD"
            if symbol in seen:
                continue
            seen.add(symbol)
            symbols.append({"symbol": symbol, "name": name})
        print(f"  CoinGecko 清单第 {page} 页，累计 {len(symbols)} 条", flush=True)
    return symbols


def load_all_binance_usdt_symbols(timeout: float) -> list[dict]:
    try:
        response = binance_get("/api/v3/exchangeInfo", timeout)
    except Exception as error:
        print(f"  Binance 清单不可用，改用 CoinGecko 市值清单: {error}", flush=True)
        return load_coingecko_market_cap_symbols(timeout)

    volumes = {}
    try:
        ticker_response = binance_get("/api/v3/ticker/24hr", timeout)
        volumes = {
            item.get("symbol"): float(item.get("quoteVolume") or 0)
            for item in ticker_response.json()
            if item.get("symbol")
        }
    except Exception as error:
        print(f"  Binance 24h 成交额排序不可用，改用交易所默认顺序: {error}", flush=True)

    symbols = []
    for item in response.json().get("symbols", []):
        if item.get("status") != "TRADING" or item.get("quoteAsset") != "USDT":
            continue
        base = item.get("baseAsset")
        raw_symbol = item.get("symbol")
        if not base or not raw_symbol:
            continue
        symbols.append({"symbol": f"{base}-USD", "name": base, "quoteVolume": volumes.get(raw_symbol, 0.0)})
    symbols.sort(key=lambda item: item.get("quoteVolume", 0.0), reverse=True)
    return [{"symbol": item["symbol"], "name": item["name"]} for item in symbols]


def build_universe(markets: list[str], universe: str, crypto_universe: str, timeout: float) -> dict[str, list[dict]]:
    if universe == "sample":
        selected = {market: TRAINING_UNIVERSE.get(market, []) for market in markets}
    else:
        selected = {}
        if "A股" in markets:
            print("加载全 A股代码清单……", flush=True)
            selected["A股"] = load_all_a_share_stocks(timeout)
        if "美股" in markets:
            print("加载全 美股代码清单……", flush=True)
            selected["美股"] = load_all_us_stocks(timeout)
        if "港股" in markets:
            print("加载全 港股代码清单……", flush=True)
            selected["港股"] = load_all_hk_stocks(timeout)
        if "加密货币" in markets:
            selected["加密货币"] = TRAINING_UNIVERSE.get("加密货币", [])

    if "加密货币" in markets and crypto_universe == "binance-usdt":
        print("加载 Binance USDT 加密货币清单……", flush=True)
        selected["加密货币"] = load_all_binance_usdt_symbols(timeout)
    elif "加密货币" in markets and crypto_universe == "coingecko-market-cap":
        print("加载 CoinGecko 市值前 1000 加密货币清单……", flush=True)
        selected["加密货币"] = load_coingecko_market_cap_symbols(timeout)
    return selected


def csv_is_fresh(path: Path, end_date: str, stale_days: int) -> bool:
    if not path.exists():
        return False
    try:
        raw = pd.read_csv(path, usecols=["date"])
        last_date = pd.to_datetime(raw["date"], errors="coerce").max()
        requested_end = pd.to_datetime(end_date)
        return pd.notna(last_date) and last_date >= requested_end - pd.Timedelta(days=stale_days)
    except Exception:
        return False


def download_market_data(
    markets: list[str],
    start_date: str,
    end_date: str,
    data_dir: Path,
    max_per_market: int | None,
    max_crypto: int | None,
    timeout: float,
    pause: float,
    workers: int,
    refresh: bool,
    universe: str,
    crypto_universe: str,
    stale_days: int,
    progress_output: Path | None = None,
) -> dict:
    universe_map = build_universe(markets, universe, crypto_universe, timeout)
    selected = []
    for market in markets:
        stocks = universe_map.get(market, [])
        if market == "加密货币" and max_crypto:
            stocks = stocks[:max_crypto]
        elif max_per_market:
            stocks = stocks[:max_per_market]
        for stock in stocks:
            selected.append((market, stock))

    successes = []
    failures = []
    result = {
        "generatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "dateRange": {"start": start_date, "end": end_date},
        "dataSource": "tencent+binance",
        "dataDir": str(data_dir),
        "universe": universe,
        "cryptoUniverse": crypto_universe,
        "counts": {
            "requested": len(selected),
            "successful": 0,
            "failed": 0,
            "processed": 0,
        },
        "successes": successes,
        "failures": failures,
    }

    def write_progress() -> None:
        if not progress_output:
            return
        result["updatedAt"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        result["counts"]["successful"] = len(successes)
        result["counts"]["failed"] = len(failures)
        result["counts"]["processed"] = len(successes) + len(failures)
        progress_output.parent.mkdir(parents=True, exist_ok=True)
        progress_output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    def process_one(index: int, market: str, stock: dict) -> tuple[str, dict, str]:
        path = data_csv_path(stock["symbol"], market, data_dir)
        if path.exists() and not refresh and csv_is_fresh(path, end_date, stale_days):
            item = {
                "market": market,
                "symbol": stock["symbol"],
                "name": stock["name"],
                "rows": None,
                "path": str(path),
                "cached": True,
            }
            return "success", item, f"[{index}/{len(selected)}] 已存在 {stock['symbol']} -> {path}"

        if path.exists() and not refresh:
            stale_message = f"[{index}/{len(selected)}] 缓存过旧，刷新 {stock['symbol']} -> {path}"
        else:
            stale_message = ""

        try:
            if market == "加密货币":
                df = get_crypto_history_data(stock, start_date, end_date, timeout)
            else:
                df = get_tencent_history_download_data(stock["symbol"], market, start_date, end_date, timeout)
            path = save_market_data_csv(df, stock["symbol"], market, stock["name"], data_dir)
            if pause > 0:
                time.sleep(pause)
            item = {
                "market": market,
                "symbol": stock["symbol"],
                "name": stock["name"],
                "rows": int(len(df)),
                "path": str(path),
                "cached": False,
            }
            prefix = f"{stale_message}\n" if stale_message else ""
            return "success", item, f"{prefix}[{index}/{len(selected)}] 完成 {stock['symbol']}，{len(df)} 行 -> {path}"
        except Exception as error:
            item = {
                "market": market,
                "symbol": stock["symbol"],
                "name": stock["name"],
                "error": str(error),
            }
            prefix = f"{stale_message}\n" if stale_message else ""
            return "failure", item, f"{prefix}[{index}/{len(selected)}] 失败 {stock['symbol']}: {error}"

    lock = Lock()
    actual_workers = max(1, workers)
    if actual_workers == 1:
        for index, (market, stock) in enumerate(selected, start=1):
            status, item, message = process_one(index, market, stock)
            print(message, flush=True)
            if status == "success":
                successes.append(item)
            else:
                failures.append(item)
            write_progress()
    else:
        print(f"并发下载启动：workers={actual_workers}，任务数={len(selected)}", flush=True)
        with ThreadPoolExecutor(max_workers=actual_workers) as executor:
            futures = {
                executor.submit(process_one, index, market, stock): (index, market, stock)
                for index, (market, stock) in enumerate(selected, start=1)
            }
            for future in as_completed(futures):
                status, item, message = future.result()
                with lock:
                    print(message, flush=True)
                    if status == "success":
                        successes.append(item)
                    else:
                        failures.append(item)
                    write_progress()

    write_progress()
    return result


def main() -> None:
    today = datetime.now().strftime("%Y%m%d")
    parser = argparse.ArgumentParser(description="下载腾讯源历史 K 线到本地 data 目录")
    parser.add_argument("--markets", default="A股,美股,港股,加密货币")
    parser.add_argument("--start", default="20220101")
    parser.add_argument("--end", default=today)
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR))
    parser.add_argument("--max-per-market", type=int, default=None)
    parser.add_argument("--max-crypto", type=int, default=None)
    parser.add_argument("--universe", choices=["sample", "all"], default="sample")
    parser.add_argument("--crypto-universe", choices=["sample", "binance-usdt", "coingecko-market-cap"], default="sample")
    parser.add_argument("--timeout", type=float, default=15)
    parser.add_argument("--pause", type=float, default=0.1)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--stale-days", type=int, default=7)
    parser.add_argument("--json-output", default="")
    parser.add_argument("--progress-output", default="")
    args = parser.parse_args()

    result = download_market_data(
        markets=parse_markets(args.markets),
        start_date=args.start,
        end_date=args.end,
        data_dir=Path(args.data_dir),
        max_per_market=args.max_per_market,
        max_crypto=args.max_crypto,
        timeout=args.timeout,
        pause=args.pause,
        workers=args.workers,
        refresh=args.refresh,
        universe=args.universe,
        crypto_universe=args.crypto_universe,
        stale_days=args.stale_days,
        progress_output=Path(args.progress_output) if args.progress_output else None,
    )
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.json_output:
        Path(args.json_output).write_text(payload, encoding="utf-8")
        summary = {
            "jsonOutput": args.json_output,
            "dataSource": result["dataSource"],
            "dataDir": result["dataDir"],
            "counts": result["counts"],
            "failures": result["failures"][:10],
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(payload)


if __name__ == "__main__":
    main()
