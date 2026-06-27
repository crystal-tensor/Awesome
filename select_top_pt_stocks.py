import argparse
import json
import math
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

from classic_strategy import compute_classic_strategy
from download_tencent_data import load_all_a_share_stocks
from model_training import (
    DEFAULT_DATA_DIR,
    TRAINING_UNIVERSE,
    data_csv_path,
    format_improvement,
    format_metrics,
    get_tencent_history_data,
    load_market_data_csv,
    save_market_data_csv,
    score_candidate,
)
from pt_strategy import compute_pt_strategy


def metric(row: dict, key: str) -> float:
    value = row.get(key, 0)
    try:
        if value is None or math.isnan(float(value)):
            return 0.0
        return float(value)
    except Exception:
        return 0.0


def stock_key(stock: dict) -> str:
    return str(stock["symbol"]).upper()


def dedupe_stocks(stocks: list[dict]) -> list[dict]:
    seen = set()
    result = []
    for stock in stocks:
        symbol = str(stock.get("symbol", "")).strip()
        name = str(stock.get("name", "")).strip() or symbol
        if not symbol:
            continue
        key = symbol.upper()
        if key in seen:
            continue
        seen.add(key)
        result.append({"symbol": symbol, "name": name})
    return result


def fetch_eastmoney_limited_rows(url: str, fs: str, timeout: float, target: int = 260) -> list[dict]:
    rows = []
    page = 1
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://quote.eastmoney.com/center/gridlist.html",
    }
    while len(rows) < target:
        params = {
            "pn": page,
            "pz": 100,
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
        for attempt in range(1, 4):
            try:
                response = session.get(url, params=params, headers=headers, timeout=timeout)
                response.raise_for_status()
                batch = (response.json().get("data") or {}).get("diff") or []
                break
            except Exception as error:
                last_error = error
                time.sleep(min(attempt * 1.5, 5))
        else:
            if rows:
                print(f"  清单第 {page} 页中断，已拿到 {len(rows)} 条，继续使用现有清单: {last_error}", flush=True)
                break
            raise RuntimeError(f"东方财富清单第 {page} 页请求失败: {last_error}")
        if not batch:
            break
        rows.extend(batch)
        print(f"  清单第 {page} 页，累计 {len(rows)} 条", flush=True)
        if len(batch) < 100:
            break
        page += 1
    return rows


def load_limited_us_stocks(timeout: float) -> list[dict]:
    try:
        rows = fetch_eastmoney_limited_rows(
            "https://72.push2.eastmoney.com/api/qt/clist/get",
            "m:105,m:106,m:107",
            timeout,
        )
        return [
            {"symbol": str(row.get("f12", "")).strip(), "name": str(row.get("f14", "")).strip()}
            for row in rows
            if row.get("f12") and row.get("f14")
        ]
    except Exception as error:
        print(f"  美股东方财富清单不可用，改用 S&P 500 兜底清单: {error}", flush=True)
        response = requests.get(
            "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=timeout,
            verify=False,
        )
        response.raise_for_status()
        table = pd.read_html(response.text)[0]
        return [
            {"symbol": str(row["Symbol"]).replace(".", "-"), "name": str(row["Security"])}
            for _, row in table.iterrows()
            if row.get("Symbol") and row.get("Security")
        ]


def load_limited_hk_stocks(timeout: float) -> list[dict]:
    try:
        rows = fetch_eastmoney_limited_rows(
            "https://72.push2.eastmoney.com/api/qt/clist/get",
            "m:128 t:3,m:128 t:4,m:128 t:1,m:128 t:2",
            timeout,
        )
        return [
            {"symbol": f"{str(row.get('f12', '')).strip().zfill(4)}.HK", "name": str(row.get("f14", "")).strip()}
            for row in rows
            if row.get("f12") and row.get("f14")
        ]
    except Exception as error:
        print(f"  港股东方财富清单不可用，改用新浪港股清单: {error}", flush=True)
        try:
            import akshare as ak

            df = ak.stock_hk_spot()
            return [
                {"symbol": f"{str(row.get('代码', '')).strip().zfill(4)}.HK", "name": str(row.get("中文名称", "")).strip()}
                for _, row in df.iterrows()
                if row.get("代码") and row.get("中文名称")
            ]
        except Exception as sina_error:
            print(f"  新浪港股清单也不可用，改用港股代码段由腾讯接口验证: {sina_error}", flush=True)
            return [{"symbol": f"{code:04d}.HK", "name": f"{code:04d}.HK"} for code in range(1, 2500)]


MARKET_LOADERS = {
    "A股": load_all_a_share_stocks,
    "美股": load_limited_us_stocks,
    "港股": load_limited_hk_stocks,
}


def normalize_param_item(item: dict) -> dict:
    return {
        "mode": str(item.get("mode", "legacy_ot")),
        "qHead": float(item.get("qHead", 0.8)),
        "qTail": float(item.get("qTail", 0.95)),
        "eta": float(item.get("eta", 0.5)),
    }


def param_key(item: dict) -> tuple:
    normalized = normalize_param_item(item)
    return normalized["mode"], normalized["qHead"], normalized["qTail"], normalized["eta"]


def load_model_config(model_path: Path, max_templates: int = 14) -> tuple[dict, dict]:
    model = json.loads(model_path.read_text(encoding="utf-8"))
    summary_params = {
        item["market"]: item["bestParams"]
        for item in model.get("marketSummary", [])
        if item.get("market") and item.get("bestParams")
    }
    deliverable_params = model.get("deliverableModel", {}).get("marketParameters", {}) or {}
    params = {}
    templates = {}
    for market in MARKET_LOADERS:
        market_params = summary_params.get(market) or deliverable_params.get(market)
        params[market] = normalize_param_item(market_params) if market_params else None
        scored = {}
        if market_params:
            scored[param_key(market_params)] = {"params": normalize_param_item(market_params), "count": 999, "score": 999.0}
        for row in model.get("stockResults", []):
            if row.get("market") != market or not row.get("best"):
                continue
            key = param_key(row["best"])
            scored.setdefault(key, {"params": normalize_param_item(row["best"]), "count": 0, "score": 0.0})
            scored[key]["count"] += 1
            scored[key]["score"] += float(row["best"].get("score", 0) or 0)
        ordered = sorted(scored.values(), key=lambda item: (item["count"], item["score"]), reverse=True)
        templates[market] = [item["params"] for item in ordered[:max_templates]]
    return params, templates


def load_market_candidates(market: str, timeout: float) -> list[dict]:
    base = TRAINING_UNIVERSE.get(market, [])
    loader = MARKET_LOADERS[market]
    all_stocks = loader(timeout)
    return dedupe_stocks(base + all_stocks)


def local_is_fresh(symbol: str, market: str, end_date: str, data_dir: Path, stale_days: int) -> bool:
    path = data_csv_path(symbol, market, data_dir)
    if not path.exists():
        return False
    try:
        raw = pd.read_csv(path, usecols=["date"])
        if raw.empty:
            return False
        last_date = pd.to_datetime(raw["date"]).max()
        requested_end = pd.to_datetime(end_date)
        return last_date >= requested_end - pd.Timedelta(days=stale_days)
    except Exception:
        return False


def load_or_download(
    stock: dict,
    market: str,
    start_date: str,
    end_date: str,
    data_dir: Path,
    timeout: float,
    refresh_existing: bool,
    stale_days: int,
) -> tuple[pd.DataFrame | None, str | None]:
    symbol = stock["symbol"]
    should_refresh = refresh_existing or not local_is_fresh(symbol, market, end_date, data_dir, stale_days)
    if not should_refresh:
        df = load_market_data_csv(symbol, market, start_date, end_date, data_dir)
        if df is not None:
            return df, None

    try:
        df = get_tencent_history_data(symbol, market, start_date, end_date, timeout)
        save_market_data_csv(df, symbol, market, stock.get("name", symbol), data_dir)
        return df, None
    except Exception as error:
        local_df = load_market_data_csv(symbol, market, start_date, end_date, data_dir)
        if local_df is not None:
            return local_df, f"{symbol} 腾讯刷新失败，已使用本地 CSV: {error}"
        return None, str(error)


def evaluate_stock(stock: dict, market: str, df: pd.DataFrame, templates: list[dict]) -> dict:
    baseline = compute_classic_strategy(df)["metrics"]
    candidates = []
    for params in templates:
        pt_result = compute_pt_strategy(
            df,
            q_head=float(params["qHead"]),
            q_tail=float(params["qTail"]),
            eta_param=float(params["eta"]),
            mode=str(params["mode"]),
        )
        pt_metrics = pt_result["metrics"]
        candidates.append(
            {
                "params": params,
                "metrics": pt_metrics,
                "improvement": format_improvement(baseline, pt_metrics),
                "score": score_candidate(baseline, pt_metrics),
            }
        )

    best = max(candidates, key=lambda item: item["score"])
    params = best["params"]
    pt_metrics = best["metrics"]
    improvement = best["improvement"]
    base_score = best["score"]
    pt_total = metric(pt_metrics, "累计收益率")
    pt_annual = metric(pt_metrics, "年化收益率")
    pt_sharpe = metric(pt_metrics, "夏普比率")
    pt_drawdown = abs(metric(pt_metrics, "最大回撤"))
    return_gain = improvement["totalReturn"]
    drawdown_gain = improvement["maxDrawdown"]
    all_improved = return_gain > 0 and improvement["sharpe"] > 0 and drawdown_gain > 0
    ranking_score = (
        base_score
        + pt_total * 1.2
        + pt_annual * 0.7
        + pt_sharpe * 0.35
        - pt_drawdown * 0.9
        + max(return_gain, 0) * 0.8
        + max(drawdown_gain, 0) * 0.9
    )
    return {
        "market": market,
        "symbol": stock["symbol"],
        "name": stock.get("name") or stock["symbol"],
        "rows": int(len(df)),
        "params": params,
        "baseline": format_metrics(baseline),
        "pt": format_metrics(pt_metrics),
        "improvement": improvement,
        "score": round(float(base_score), 6),
        "rankingScore": round(float(ranking_score), 6),
        "allObjectivesImproved": all_improved,
    }


def select_market(args: argparse.Namespace, market: str, market_params: dict, templates: list[dict]) -> dict:
    print(f"\n[{market}] 加载股票清单", flush=True)
    candidates = load_market_candidates(market, args.timeout)
    successes = []
    failures = []
    selected_universe = []

    for index, stock in enumerate(candidates, start=1):
        if len(successes) >= args.market_size:
            break
        df, error = load_or_download(
            stock,
            market,
            args.start,
            args.end,
            args.data_dir,
            args.timeout,
            args.refresh_existing,
            args.stale_days,
        )
        if error:
            failures.append({"market": market, "symbol": stock["symbol"], "name": stock.get("name", ""), "error": error})
        if df is None:
            if index % 25 == 0:
                print(f"[{market}] 已检查 {index} 只，成功 {len(successes)}，失败 {len(failures)}", flush=True)
            continue
        successes.append(stock)
        selected_universe.append({"symbol": stock["symbol"], "name": stock.get("name", stock["symbol"]), "rows": int(len(df))})
        if len(successes) % 25 == 0 or len(successes) == args.market_size:
            print(f"[{market}] 腾讯 CSV 可用 {len(successes)}/{args.market_size}", flush=True)
        time.sleep(args.pause)

    evaluated = []
    for stock in successes:
        df = load_market_data_csv(stock["symbol"], market, args.start, args.end, args.data_dir)
        if df is None:
            failures.append({"market": market, "symbol": stock["symbol"], "name": stock.get("name", ""), "error": "本地 CSV 不可用"})
            continue
        try:
            evaluated.append(evaluate_stock(stock, market, df, templates))
        except Exception as error:
            failures.append({"market": market, "symbol": stock["symbol"], "name": stock.get("name", ""), "error": str(error)})

    evaluated.sort(
        key=lambda item: (
            item["allObjectivesImproved"],
            item["rankingScore"],
            item["pt"]["totalReturn"],
            -abs(item["pt"]["maxDrawdown"]),
        ),
        reverse=True,
    )
    top = evaluated[: args.pick_count]
    for rank, item in enumerate(top, start=1):
        item["rank"] = rank

    print(f"[{market}] 完成评分 {len(evaluated)} 只，入选 {len(top)} 只", flush=True)
    return {
        "params": market_params,
        "templateCount": len(templates),
        "templates": templates,
        "candidateCount": len(candidates),
        "downloadedUniverse": len(successes),
        "evaluatedCount": len(evaluated),
        "selectedCount": len(top),
        "universe": selected_universe,
        "stocks": top,
        "failures": failures,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="用腾讯数据和已训练模型筛选每个市场的 PT 策略优选股票")
    parser.add_argument("--markets", default="A股,美股,港股")
    parser.add_argument("--start", default="20220101")
    parser.add_argument("--end", default=datetime.now().strftime("%Y%m%d"))
    parser.add_argument("--market-size", type=int, default=200)
    parser.add_argument("--pick-count", type=int, default=30)
    parser.add_argument("--model-path", type=Path, default=Path(".tmp/latest-training-model.json"))
    parser.add_argument("--output", type=Path, default=Path(".tmp/selected-market-stocks.json"))
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--timeout", type=float, default=15)
    parser.add_argument("--pause", type=float, default=0.05)
    parser.add_argument("--stale-days", type=int, default=3)
    parser.add_argument("--refresh-existing", action="store_true")
    parser.add_argument("--resume-existing", action="store_true")
    args = parser.parse_args()

    params_by_market, templates_by_market = load_model_config(args.model_path)
    requested_markets = [item.strip() for item in args.markets.split(",") if item.strip()]
    if args.resume_existing and args.output.exists():
        result = json.loads(args.output.read_text(encoding="utf-8"))
        result["generatedAt"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        result["paramsByMarket"] = params_by_market
        result["templatesByMarket"] = templates_by_market
    else:
        result = {
            "generatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "modelPath": str(args.model_path),
            "dateRange": {"start": args.start, "end": args.end},
            "marketSize": args.market_size,
            "pickCount": args.pick_count,
            "paramsByMarket": params_by_market,
            "templatesByMarket": templates_by_market,
            "markets": {},
        }

    for market in requested_markets:
        existing = result.get("markets", {}).get(market)
        if (
            args.resume_existing
            and existing
            and existing.get("downloadedUniverse", 0) >= args.market_size
            and existing.get("selectedCount", 0) >= args.pick_count
        ):
            print(f"[{market}] 已有完整结果，跳过", flush=True)
            continue
        params = params_by_market.get(market)
        if not params:
            raise RuntimeError(f"模型里没有 {market} 的参数")
        result["markets"][market] = select_market(args, market, params, templates_by_market.get(market, [params]))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n筛选结果已写入: {args.output}", flush=True)


if __name__ == "__main__":
    main()
