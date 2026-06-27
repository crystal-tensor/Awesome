import argparse
import json
import os
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import pandas as pd

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

from model_training import (
    DEFAULT_ETAS,
    DEFAULT_MODES,
    DEFAULT_Q_HEADS,
    DEFAULT_Q_TAILS,
    DEFAULT_SPLIT_SEED,
    DEFAULT_VALIDATION_FRACTION,
    average_metric_group,
    build_parameter_grid,
    cross_validate_param_selection,
    empty_evidence,
    evaluate_fixed_params,
    format_improvement,
    format_metrics,
    parse_float_grid,
    parse_string_grid,
    select_best_params,
    score_candidate,
    summarize_evidence,
)
from model_training import assign_train_validation_split, normalize_training_price_frame
from classic_strategy import calc_backtest_metrics
from pt_data_transformer import transform_ohlcv_with_pt_model


MARKETS = ["A股", "美股", "港股", "加密货币"]


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def safe_float(value, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def discover_market_files(data_dir: Path, market: str) -> list[Path]:
    return sorted(data_dir.glob(f"{market}_*.csv"))


def read_identity(path: Path, market: str) -> dict:
    fallback_symbol = path.stem[len(f"{market}_") :]
    try:
        head = pd.read_csv(path, nrows=1)
        symbol = str(head.get("symbol", pd.Series([fallback_symbol])).iloc[0] or fallback_symbol)
        name = str(head.get("name", pd.Series([symbol])).iloc[0] or symbol)
        return {"market": market, "symbol": symbol, "name": name, "path": str(path)}
    except Exception:
        return {"market": market, "symbol": fallback_symbol, "name": fallback_symbol, "path": str(path)}


def load_done_symbols(jsonl_path: Path) -> set[str]:
    if not jsonl_path.exists():
        return set()
    done = set()
    with jsonl_path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                if row.get("symbol"):
                    done.add(str(row["symbol"]))
            except Exception:
                continue
    return done


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def append_jsonl(path: Path, row: dict) -> None:
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(row, ensure_ascii=False) + "\n")


def fast_strategy_metrics(df: pd.DataFrame, close_col: str, real_ret_col: str = "daily_ret") -> dict:
    ma5 = df[close_col].rolling(5).mean()
    ma20 = df[close_col].rolling(20).mean()
    signal = (ma5 > ma20).astype(int)
    strategy_ret = signal.shift(1).fillna(0) * df[real_ret_col]
    net = (1 + strategy_ret).cumprod()
    return calc_backtest_metrics(net, strategy_ret)


def compute_pt_metrics_fast(df: pd.DataFrame, params: dict) -> dict:
    work_df = transform_ohlcv_with_pt_model(
        df,
        q_head=params["qHead"],
        q_tail=params["qTail"],
        eta=params["eta"],
        mode=params["mode"],
    )
    return fast_strategy_metrics(work_df, "pt_close", "daily_ret")


def evaluate_single_stock_fast(stock: dict, market: str, df_raw: pd.DataFrame, grid: list[dict]) -> dict:
    baseline_metrics_raw = fast_strategy_metrics(df_raw, "close", "daily_ret")
    baseline_metrics = format_metrics(baseline_metrics_raw)
    candidates = []

    for params in grid:
        metrics_raw = compute_pt_metrics_fast(df_raw, params)
        metrics = format_metrics(metrics_raw)
        candidates.append(
            {
                "mode": params["mode"],
                "qHead": params["qHead"],
                "qTail": params["qTail"],
                "eta": params["eta"],
                "metrics": metrics,
                "improvement": format_improvement(baseline_metrics_raw, metrics_raw),
                "score": score_candidate(baseline_metrics_raw, metrics_raw),
            }
        )

    best = max(candidates, key=lambda item: item["score"])
    return {
        "market": market,
        "symbol": stock["symbol"],
        "name": stock["name"],
        "rows": int(len(df_raw)),
        "baseline": baseline_metrics,
        "best": {
            "mode": best["mode"],
            "qHead": best["qHead"],
            "qTail": best["qTail"],
            "eta": best["eta"],
            "score": best["score"],
            "metrics": best["metrics"],
            "improvement": best["improvement"],
        },
        "candidateScores": candidates,
        "topCandidates": sorted(candidates, key=lambda item: item["score"], reverse=True)[:5],
    }


def evaluate_market_file(args: tuple[str, str, str, str, list[dict]]) -> dict:
    path_text, market, start_date, end_date, grid = args
    path = Path(path_text)
    identity = read_identity(path, market)
    try:
        raw = pd.read_csv(path)
        symbol = str(raw["symbol"].dropna().iloc[0]) if "symbol" in raw.columns and raw["symbol"].notna().any() else identity["symbol"]
        name = str(raw["name"].dropna().iloc[0]) if "name" in raw.columns and raw["name"].notna().any() else symbol
        df = normalize_training_price_frame(raw, "本地全量 CSV", symbol)
        start_ts = pd.to_datetime(start_date)
        end_ts = pd.to_datetime(end_date)
        df = df[(df.index >= start_ts) & (df.index <= end_ts)]
        if len(df) < 80:
            raise RuntimeError("可用历史数据不足 80 行")
        return {
            "ok": True,
            "result": evaluate_single_stock_fast({"symbol": symbol, "name": name}, market, df, grid),
        }
    except Exception as error:
        return {
            "ok": False,
            "failure": {
                **identity,
                "error": str(error),
                "traceback": traceback.format_exc(limit=3),
            },
        }


def compact_candidate_aggregate(rows: list[dict], grid: list[dict]) -> list[dict]:
    aggregate = []
    for params in grid:
        scores = []
        improvements = []
        for row in rows:
            for candidate in row.get("candidateScores", []):
                if (
                    candidate["mode"] == params["mode"]
                    and float(candidate["qHead"]) == float(params["qHead"])
                    and float(candidate["qTail"]) == float(params["qTail"])
                    and float(candidate["eta"]) == float(params["eta"])
                ):
                    scores.append(safe_float(candidate.get("score")))
                    improvements.append(candidate.get("improvement", {}))
                    break
        if not scores:
            continue
        aggregate.append(
            {
                **params,
                "stocks": len(scores),
                "avgScore": round(sum(scores) / len(scores), 6),
                "avgImprovement": average_metric_group(improvements),
                "positiveScoreRate": round(sum(1 for value in scores if value > 0) / len(scores), 6),
            }
        )
    return sorted(aggregate, key=lambda item: item["avgScore"], reverse=True)


def build_market_model(
    market: str,
    rows: list[dict],
    failures: list[dict],
    grid: list[dict],
    start_date: str,
    end_date: str,
    validation_fraction: float,
    split_seed: str,
    cv_folds: int,
    data_dir: Path,
    output_dir: Path,
    result_path: Path,
) -> dict:
    assign_train_validation_split(rows, validation_fraction, split_seed)
    train_rows = [row for row in rows if row.get("split") == "train"]
    validation_rows = [row for row in rows if row.get("split") == "validation"]
    params = select_best_params(train_rows, grid)
    train_evidence = evaluate_fixed_params(train_rows, params)
    validation_evidence = evaluate_fixed_params(validation_rows, params)
    cv = cross_validate_param_selection(rows, grid, cv_folds, split_seed) if len(rows) >= 2 else {
        "folds": [],
        "aggregateEvidence": empty_evidence(),
    }
    best_rows = [row["best"]["improvement"] for row in rows if row.get("best")]
    baselines = [row["baseline"] for row in rows if row.get("baseline")]
    best_metrics = [row["best"]["metrics"] for row in rows if row.get("best")]
    best_scores = [safe_float(row.get("best", {}).get("score")) for row in rows if row.get("best")]
    model = {
        "market": market,
        "modelName": "PT Heavy Tail OHLCV Transformer",
        "modelVersion": "full-market-1.0",
        "generatedAt": now_text(),
        "dataDir": str(data_dir),
        "outputDir": str(output_dir),
        "resultPath": str(result_path),
        "dateRange": {"start": start_date, "end": end_date},
        "selectionMethod": (
            "Full local CSV market scan. Each stock is evaluated on the same PT parameter grid; "
            "the market model chooses parameters on the train split and reports validation plus cross-validation evidence."
        ),
        "grid": {
            "modes": sorted({item["mode"] for item in grid}),
            "qHeads": sorted({item["qHead"] for item in grid}),
            "qTails": sorted({item["qTail"] for item in grid}),
            "etas": sorted({item["eta"] for item in grid}),
            "combinations": len(grid),
        },
        "counts": {
            "successfulStocks": len(rows),
            "failedStocks": len(failures),
            "trainStocks": len(train_rows),
            "validationStocks": len(validation_rows),
        },
        "parameters": params,
        "trainEvidence": train_evidence,
        "validationEvidence": validation_evidence,
        "crossValidation": cv["aggregateEvidence"],
        "oraclePerStockUpperBound": summarize_evidence(baselines, best_metrics, best_rows, best_scores)
        if best_rows
        else empty_evidence(),
        "candidateAggregateTop20": compact_candidate_aggregate(rows, grid)[:20],
        "sampleFailures": failures[:50],
    }
    return model


def write_progress(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def train_market(
    market: str,
    data_dir: Path,
    strategy_dir: Path,
    start_date: str,
    end_date: str,
    grid: list[dict],
    workers: int,
    validation_fraction: float,
    split_seed: str,
    cv_folds: int,
    limit: int | None,
    resume: bool,
    result_prefix: str,
) -> dict:
    output_dir = strategy_dir / market
    output_dir.mkdir(parents=True, exist_ok=True)
    result_path = output_dir / f"{result_prefix}.jsonl"
    failure_path = output_dir / f"{result_prefix}_failures.jsonl"
    progress_path = output_dir / f"{result_prefix}_progress.json"
    files = discover_market_files(data_dir, market)
    if limit:
        files = files[:limit]
    done_symbols = load_done_symbols(result_path) if resume else set()
    jobs = []
    for path in files:
        identity = read_identity(path, market)
        if identity["symbol"] not in done_symbols:
            jobs.append((str(path), market, start_date, end_date, grid))

    existing_rows = load_jsonl(result_path) if resume else []
    failures = load_jsonl(failure_path) if resume else []
    started_at = now_text()
    write_progress(
        progress_path,
        {
            "status": "running",
            "market": market,
            "startedAt": started_at,
            "updatedAt": started_at,
            "totalFiles": len(files),
            "alreadyCompleted": len(existing_rows),
            "remainingJobs": len(jobs),
            "successfulStocks": len(existing_rows),
            "failedStocks": len(failures),
            "gridCombinations": len(grid),
        },
    )
    print(
        f"[{market}] start total={len(files)} already={len(existing_rows)} remaining={len(jobs)} grid={len(grid)}",
        flush=True,
    )

    rows = list(existing_rows)
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        future_map = {executor.submit(evaluate_market_file, job): job for job in jobs}
        for future in as_completed(future_map):
            payload = future.result()
            if payload["ok"]:
                row = payload["result"]
                rows.append(row)
                append_jsonl(result_path, row)
                latest = f"{row['symbol']} {row['name']}"
            else:
                failure = payload["failure"]
                failures.append(failure)
                append_jsonl(failure_path, failure)
                latest = f"{failure.get('symbol')} failed"
            completed = len(rows) + len(failures)
            print(f"[{market}] completed={completed}/{len(files)} success={len(rows)} failed={len(failures)} latest={latest}", flush=True)
            if completed % 25 == 0 or completed == len(files):
                write_progress(
                    progress_path,
                    {
                        "status": "running",
                        "market": market,
                        "startedAt": started_at,
                        "updatedAt": now_text(),
                        "totalFiles": len(files),
                        "completed": completed,
                        "successfulStocks": len(rows),
                        "failedStocks": len(failures),
                        "gridCombinations": len(grid),
                        "latest": latest,
                    },
                )

    model = build_market_model(
        market,
        rows,
        failures,
        grid,
        start_date,
        end_date,
        validation_fraction,
        split_seed,
        cv_folds,
        data_dir,
        output_dir,
        result_path,
    )
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    timestamped_model_path = output_dir / f"model_{timestamp}.json"
    latest_model_path = output_dir / "latest_model.json"
    timestamped_model_path.write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    latest_model_path.write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    write_progress(
        progress_path,
        {
            "status": "complete",
            "market": market,
            "startedAt": started_at,
            "completedAt": now_text(),
            "totalFiles": len(files),
            "successfulStocks": len(rows),
            "failedStocks": len(failures),
            "latestModel": str(latest_model_path),
            "timestampedModel": str(timestamped_model_path),
            "parameters": model["parameters"],
            "validationEvidence": model["validationEvidence"],
        },
    )
    return model


def main() -> None:
    today = datetime.now().strftime("%Y%m%d")
    parser = argparse.ArgumentParser(description="按市场全量训练 PT 策略参数")
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--strategy-dir", default="strategy")
    parser.add_argument("--markets", default="A股,美股,港股,加密货币")
    parser.add_argument("--start", default="20220101")
    parser.add_argument("--end", default=today)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--q-heads", default="")
    parser.add_argument("--q-tails", default="")
    parser.add_argument("--etas", default="")
    parser.add_argument("--modes", default="")
    parser.add_argument("--validation-fraction", type=float, default=DEFAULT_VALIDATION_FRACTION)
    parser.add_argument("--split-seed", default=DEFAULT_SPLIT_SEED)
    parser.add_argument("--cv-folds", type=int, default=5)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--result-prefix", default="stock_results")
    parser.add_argument("--no-resume", action="store_true")
    args = parser.parse_args()

    markets = [item.strip() for item in args.markets.split(",") if item.strip()]
    grid = build_parameter_grid(
        parse_float_grid(args.q_heads, DEFAULT_Q_HEADS),
        parse_float_grid(args.q_tails, DEFAULT_Q_TAILS),
        parse_float_grid(args.etas, DEFAULT_ETAS),
        parse_string_grid(args.modes, DEFAULT_MODES),
    )
    summary = {
        "generatedAt": now_text(),
        "markets": markets,
        "models": [],
    }
    for market in markets:
        model = train_market(
            market=market,
            data_dir=Path(args.data_dir),
            strategy_dir=Path(args.strategy_dir),
            start_date=args.start,
            end_date=args.end,
            grid=grid,
            workers=args.workers,
            validation_fraction=args.validation_fraction,
            split_seed=args.split_seed,
            cv_folds=args.cv_folds,
            limit=args.limit or None,
            resume=not args.no_resume,
            result_prefix=args.result_prefix,
        )
        summary["models"].append(
            {
                "market": market,
                "parameters": model["parameters"],
                "counts": model["counts"],
                "validationEvidence": model["validationEvidence"],
                "crossValidation": model["crossValidation"],
            }
        )
        Path(args.strategy_dir, "latest_training_summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
