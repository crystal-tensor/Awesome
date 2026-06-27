import argparse
import json
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import pandas as pd

from classic_strategy import compute_classic_strategy
from model_training import (
    DEFAULT_ETAS,
    DEFAULT_MODES,
    DEFAULT_Q_HEADS,
    DEFAULT_Q_TAILS,
    build_parameter_grid,
    format_improvement,
    format_metrics,
    score_candidate,
)
from pt_strategy import compute_pt_strategy


DEFAULT_SOURCE = Path(".tmp/live-four-market-with-crypto-momentum-model.json")
DEFAULT_OUTPUT = Path(".tmp/time-split-calibration-latest.json")
DEFAULT_HISTORY = Path(".tmp/asset-selector-experiments.json")
DEFAULT_DATA_DIR = Path("data")
DEFAULT_PROGRESS = Path(".tmp/time-split-progress.json")


def data_csv_path(row: dict, data_dir: Path) -> Path:
    safe_market = row["market"].replace("/", "_").replace("\\", "_").replace(":", "_")
    safe_symbol = row["symbol"].replace("/", "_").replace("\\", "_").replace(":", "_")
    return data_dir / f"{safe_market}_{safe_symbol}.csv"


def load_local_data(row: dict, data_dir: Path) -> pd.DataFrame:
    path = data_csv_path(row, data_dir)
    if not path.exists():
        raise FileNotFoundError(f"缺少本地行情 CSV: {path}")
    df = pd.read_csv(path, parse_dates=["date"])
    df = df.sort_values("date").set_index("date")
    for column in ["open", "high", "low", "close", "volume"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    return df.dropna(subset=["open", "high", "low", "close", "volume"])


def candidate_key(candidate: dict) -> tuple[str, float, float, float]:
    return (candidate["mode"], candidate["qHead"], candidate["qTail"], candidate["eta"])


def passes_stability_gate(candidate: dict) -> bool:
    improvement = candidate["stabilityImprovement"]
    return (
        candidate["stabilityScore"] > 0
        and improvement["totalReturn"] >= 0
        and improvement["sharpe"] >= 0
        and improvement["maxDrawdown"] >= 0
    )


def build_candidate_pool(candidates: list[dict], limit: int = 24) -> list[dict]:
    selected = {}

    def add_ranked(ranked: list[dict], take: int) -> None:
        for item in ranked[:take]:
            selected[candidate_key(item)] = item

    non_fallback = [item for item in candidates if item["mode"] != "no_transform"]
    add_ranked(sorted(non_fallback, key=lambda item: item["trainScore"], reverse=True), 8)
    add_ranked(sorted(non_fallback, key=lambda item: item["selectScore"] + item["stabilityScore"], reverse=True), 8)
    add_ranked(sorted(non_fallback, key=lambda item: item["stabilityScore"], reverse=True), 8)
    add_ranked(
        sorted(
            non_fallback,
            key=lambda item: (
                item["stabilityImprovement"]["maxDrawdown"],
                item["stabilityImprovement"]["totalReturn"],
                item["stabilityImprovement"]["sharpe"],
            ),
            reverse=True,
        ),
        8,
    )
    add_ranked(
        sorted(
            non_fallback,
            key=lambda item: (
                item["trainImprovement"]["totalReturn"] > 0,
                item["stabilityImprovement"]["totalReturn"] > 0,
                item["trainImprovement"]["sharpe"] > 0,
                item["stabilityImprovement"]["sharpe"] > 0,
                item["trainScore"] + item["stabilityScore"],
            ),
            reverse=True,
        ),
        8,
    )
    ranked_selected = sorted(
        selected.values(),
        key=lambda item: (
            item["trainScore"] + item["selectScore"] + item["stabilityScore"],
            item["stabilityImprovement"]["totalReturn"],
            item["stabilityImprovement"]["sharpe"],
            item["stabilityImprovement"]["maxDrawdown"],
        ),
        reverse=True,
    )
    return ranked_selected[:limit]


def evaluate_asset(args: tuple[dict, str, int, list[dict], Path]) -> dict:
    row, market, split_index, grid, data_dir = args
    df = load_local_data(row, data_dir)
    if len(df) < 120:
        raise RuntimeError(f"{row['symbol']} 样本不足: {len(df)}")
    split_index = min(max(60, split_index), len(df) - 40)
    train_df = df.iloc[:split_index].copy()
    validation_df = df.iloc[split_index:].copy()
    stability_index = min(max(40, int(len(train_df) * 0.7)), len(train_df) - 30)
    select_df = train_df.iloc[:stability_index].copy()
    stability_df = train_df.iloc[stability_index:].copy()

    train_baseline = compute_classic_strategy(train_df)["metrics"]
    select_baseline = compute_classic_strategy(select_df)["metrics"]
    stability_baseline = compute_classic_strategy(stability_df)["metrics"]
    validation_baseline = compute_classic_strategy(validation_df)["metrics"]

    train_candidates = []
    validation_candidates = {}
    for params in grid:
        train_metrics = compute_pt_strategy(
            train_df,
            q_head=params["qHead"],
            q_tail=params["qTail"],
            eta_param=params["eta"],
            mode=params["mode"],
        )["metrics"]
        select_metrics = compute_pt_strategy(
            select_df,
            q_head=params["qHead"],
            q_tail=params["qTail"],
            eta_param=params["eta"],
            mode=params["mode"],
        )["metrics"]
        stability_metrics = compute_pt_strategy(
            stability_df,
            q_head=params["qHead"],
            q_tail=params["qTail"],
            eta_param=params["eta"],
            mode=params["mode"],
        )["metrics"]
        validation_metrics = compute_pt_strategy(
            validation_df,
            q_head=params["qHead"],
            q_tail=params["qTail"],
            eta_param=params["eta"],
            mode=params["mode"],
        )["metrics"]
        candidate = {
            "mode": params["mode"],
            "qHead": params["qHead"],
            "qTail": params["qTail"],
            "eta": params["eta"],
            "trainMetrics": format_metrics(train_metrics),
            "trainImprovement": format_improvement(train_baseline, train_metrics),
            "trainScore": score_candidate(train_baseline, train_metrics),
            "selectMetrics": format_metrics(select_metrics),
            "selectImprovement": format_improvement(select_baseline, select_metrics),
            "selectScore": score_candidate(select_baseline, select_metrics),
            "stabilityMetrics": format_metrics(stability_metrics),
            "stabilityImprovement": format_improvement(stability_baseline, stability_metrics),
            "stabilityScore": score_candidate(stability_baseline, stability_metrics),
            "validationMetrics": format_metrics(validation_metrics),
            "validationImprovement": format_improvement(validation_baseline, validation_metrics),
            "validationScore": score_candidate(validation_baseline, validation_metrics),
        }
        train_candidates.append(candidate)
        validation_candidates[candidate_key(candidate)] = candidate

    selected_train = max(train_candidates, key=lambda item: item["trainScore"])
    selected = validation_candidates[candidate_key(selected_train)]
    stable_train_candidates = [item for item in train_candidates if item["mode"] != "no_transform" and passes_stability_gate(item)]
    selected_stable_train = (
        max(stable_train_candidates, key=lambda item: item["selectScore"] + item["stabilityScore"])
        if stable_train_candidates
        else None
    )
    stable_selected = validation_candidates[candidate_key(selected_stable_train)] if selected_stable_train else None
    fallback = next(item for item in validation_candidates.values() if item["mode"] == "no_transform")
    oracle = max(validation_candidates.values(), key=lambda item: item["validationScore"])
    return {
        "market": market,
        "symbol": row["symbol"],
        "name": row["name"],
        "rows": len(df),
        "splitRows": {
            "select": len(select_df),
            "stability": len(stability_df),
            "train": len(train_df),
            "validation": len(validation_df),
        },
        "baseline": format_metrics(validation_baseline),
        "calibrated": selected,
        "stableSelected": stable_selected or fallback,
        "candidatePool": build_candidate_pool(train_candidates),
        "fallback": fallback,
        "oracle": oracle,
    }


def average_improvement(items: list[dict]) -> dict:
    if not items:
        return {"totalReturn": 0, "annualReturn": 0, "sharpe": 0, "maxDrawdown": 0}
    return {
        metric: round(sum(item[metric] for item in items) / len(items), 6)
        for metric in ["totalReturn", "annualReturn", "sharpe", "maxDrawdown"]
    }


def summarize_results(results: list[dict], key: str) -> dict:
    improvements = [item[key]["validationImprovement"] for item in results]
    count = len(improvements)
    by_market = {}
    for market in sorted({item["market"] for item in results}):
        market_rows = [item for item in results if item["market"] == market]
        market_improvements = [item[key]["validationImprovement"] for item in market_rows]
        market_count = len(market_rows)
        by_market[market] = {
            "assets": market_count,
            "activeRate": round(sum(item[key]["mode"] != "no_transform" for item in market_rows) / market_count, 6),
            "avgImprovement": average_improvement(market_improvements),
            "allObjectivesImprovedRate": round(
                sum(
                    imp["totalReturn"] > 0 and imp["sharpe"] > 0 and imp["maxDrawdown"] > 0
                    for imp in market_improvements
                )
                / market_count,
                6,
            ),
        }
    return {
        "assets": count,
        "activeRate": round(sum(item[key]["mode"] != "no_transform" for item in results) / count, 6),
        "avgImprovement": average_improvement(improvements),
        "returnImprovedRate": round(sum(item["totalReturn"] > 0 for item in improvements) / count, 6),
        "sharpeImprovedRate": round(sum(item["sharpe"] > 0 for item in improvements) / count, 6),
        "drawdownImprovedRate": round(sum(item["maxDrawdown"] > 0 for item in improvements) / count, 6),
        "allObjectivesImprovedRate": round(
            sum(item["totalReturn"] > 0 and item["sharpe"] > 0 and item["maxDrawdown"] > 0 for item in improvements)
            / count,
            6,
        ),
        "byMarket": by_market,
    }


def summarize_threshold_choice(results: list[dict], thresholds: dict) -> dict:
    choice_rows = []
    for item in results:
        candidate = item["calibrated"]
        train_improvement = candidate["trainImprovement"]
        use_candidate = (
            candidate["trainScore"] >= thresholds["trainScoreMin"]
            and train_improvement["totalReturn"] >= thresholds["trainTotalReturnMin"]
            and train_improvement["sharpe"] >= thresholds["trainSharpeMin"]
            and train_improvement["maxDrawdown"] >= thresholds["trainDrawdownMin"]
        )
        choice_rows.append({**item, "selected": candidate if use_candidate else item["fallback"]})
    return summarize_results(choice_rows, "selected")


def choose_best_threshold_config(results: list[dict]) -> tuple[dict, list[dict]]:
    configs = []
    for train_score_min in [-0.2, 0, 0.05, 0.1, 0.2, 0.35]:
        for train_total_min in [-0.05, 0, 0.05, 0.1]:
            for train_sharpe_min in [-0.05, 0, 0.05]:
                for train_drawdown_min in [-0.05, 0, 0.02]:
                    thresholds = {
                        "trainScoreMin": train_score_min,
                        "trainTotalReturnMin": train_total_min,
                        "trainSharpeMin": train_sharpe_min,
                        "trainDrawdownMin": train_drawdown_min,
                    }
                    summary = summarize_threshold_choice(results, thresholds)
                    by_market = summary["byMarket"]
                    penalty = sum(
                        max(0, -market["avgImprovement"]["totalReturn"]) * 2.5
                        + max(0, -market["avgImprovement"]["sharpe"]) * 2.0
                        + max(0, -market["avgImprovement"]["maxDrawdown"]) * 2.8
                        for market in by_market.values()
                    )
                    avg = summary["avgImprovement"]
                    objective = (
                        avg["totalReturn"]
                        + avg["sharpe"]
                        + avg["maxDrawdown"]
                        + 0.7 * summary["allObjectivesImprovedRate"]
                        + 0.08 * summary["activeRate"]
                        - penalty
                    )
                    configs.append(
                        {
                            "model": "per-asset-time-split-calibration-with-gate",
                            "objective": round(objective, 6),
                            "thresholds": thresholds,
                            "summary": summary,
                        }
                    )
    safe_configs = [
        item
        for item in configs
        if all(metric >= 0 for market in item["summary"]["byMarket"].values() for metric in market["avgImprovement"].values())
    ]
    ranked = safe_configs or configs
    ranked.sort(
        key=lambda item: (
            item["summary"]["allObjectivesImprovedRate"],
            item["summary"]["avgImprovement"]["totalReturn"],
            item["summary"]["avgImprovement"]["sharpe"],
            item["objective"],
        ),
        reverse=True,
    )
    configs.sort(key=lambda item: item["objective"], reverse=True)
    return ranked[0], configs[:20]


def append_history(history_path: Path, experiment: dict) -> None:
    history_path.parent.mkdir(parents=True, exist_ok=True)
    history = json.loads(history_path.read_text(encoding="utf-8")) if history_path.exists() else []
    history.append(
        {
            "generatedAt": experiment["generatedAt"],
            "experimentName": experiment["experimentName"],
            "status": experiment["status"],
            "conclusion": experiment["conclusion"],
            "sourceModelPath": experiment["sourceModelPath"],
            "assetCount": experiment["assetCount"],
            "sampleCount": experiment["sampleCount"],
            "featureCount": experiment["featureCount"],
            "bestConfig": experiment["bestConfig"],
            "oracleUpperBound": experiment["oracleUpperBound"],
        }
    )
    history_path.write_text(json.dumps(history[-50:], ensure_ascii=False, indent=2), encoding="utf-8")


def write_progress(progress_path: Path, progress: dict) -> None:
    progress_path.parent.mkdir(parents=True, exist_ok=True)
    progress_path.write_text(json.dumps(progress, ensure_ascii=False, indent=2), encoding="utf-8")


def build_partial_progress(
    started_at: str,
    jobs: list[tuple[dict, str, int, list[dict], Path]],
    results: list[dict],
    failures: list[dict],
    markets: list[str],
) -> dict:
    completed = len(results) + len(failures)
    progress = {
        "startedAt": started_at,
        "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "running",
        "markets": markets,
        "totalAssets": len(jobs),
        "completedAssets": completed,
        "successAssets": len(results),
        "failedAssets": len(failures),
        "percent": round(completed / len(jobs), 4) if jobs else 1,
        "latestCompleted": {
            "market": results[-1]["market"],
            "symbol": results[-1]["symbol"],
            "name": results[-1]["name"],
        }
        if results
        else None,
        "failures": failures[-10:],
    }
    if results:
        progress["partial"] = {
            "calibrated": summarize_results(results, "calibrated"),
            "stableSelected": summarize_results(results, "stableSelected"),
            "oracleUpperBound": summarize_results(results, "oracle"),
        }
    return progress


def run_experiment(
    source: Path,
    data_dir: Path,
    markets: list[str],
    split_fraction: float,
    workers: int,
    max_assets: int | None,
    progress_path: Path | None = None,
) -> dict:
    payload = json.loads(source.read_text(encoding="utf-8"))
    rows = [row for row in payload["stockResults"] if not markets or row["market"] in markets]
    if max_assets:
        grouped = []
        for market in sorted({row["market"] for row in rows}):
            grouped.extend([row for row in rows if row["market"] == market][:max_assets])
        rows = grouped
    grid = build_parameter_grid(DEFAULT_Q_HEADS, DEFAULT_Q_TAILS, DEFAULT_ETAS, DEFAULT_MODES)
    jobs = []
    for row in rows:
        csv_path = data_csv_path(row, data_dir)
        if not csv_path.exists():
            continue
        local_len = max(1, sum(1 for _ in csv_path.open("r", encoding="utf-8")) - 1)
        jobs.append((row, row["market"], int(local_len * split_fraction), grid, data_dir))

    results = []
    failures = []
    started_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    progress_markets = markets or sorted({row["market"] for row, *_ in jobs})
    if progress_path:
        write_progress(
            progress_path,
            build_partial_progress(started_at, jobs, results, failures, progress_markets),
        )
    print(
        f"[time-split] started assets={len(jobs)} markets={','.join(progress_markets) or '全部'} "
        f"workers={workers} split={split_fraction}",
        flush=True,
    )
    with ProcessPoolExecutor(max_workers=max(1, workers)) as executor:
        future_map = {executor.submit(evaluate_asset, job): job[0] for job in jobs}
        for future in as_completed(future_map):
            row = future_map[future]
            try:
                results.append(future.result())
            except Exception as error:
                failures.append({"market": row["market"], "symbol": row["symbol"], "name": row["name"], "error": str(error)})
            completed = len(results) + len(failures)
            print(
                f"[time-split] completed {completed}/{len(jobs)} "
                f"success={len(results)} failed={len(failures)} latest={row['market']} {row['symbol']}",
                flush=True,
            )
            if progress_path:
                write_progress(
                    progress_path,
                    build_partial_progress(started_at, jobs, results, failures, progress_markets),
                )

    results.sort(key=lambda item: (item["market"], item["symbol"]))
    best_config, top_configs = choose_best_threshold_config(results)
    selected_summary = best_config["summary"]
    oracle_summary = summarize_results(results, "oracle")
    market_values = [
        metric
        for market in selected_summary["byMarket"].values()
        for metric in market["avgImprovement"].values()
    ]
    safe = all(value >= 0 for value in market_values)
    status = "candidate_safer_not_promoted" if safe else "candidate_not_promoted"
    conclusion = (
        "时间切分校准在验证期四市场平均不为负，但覆盖率仍未达到多数资产。"
        if safe
        else "时间切分校准验证期仍存在市场负贡献，不能推广。"
    )
    experiment = {
        "generatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "experimentName": "time-split-per-asset-calibration",
        "status": status,
        "conclusion": conclusion,
        "sourceModelPath": str(source),
        "dataDir": str(data_dir),
        "splitFraction": split_fraction,
        "assetCount": len(results),
        "sampleCount": len(results) * len(grid),
        "featureCount": 0,
        "bestConfig": {
            **best_config,
            "thresholds": {**best_config["thresholds"], "splitFraction": split_fraction},
        },
        "rawCalibrationConfig": {
            "model": "per-asset-time-split-calibration-no-gate",
            "objective": 0,
            "thresholds": {"splitFraction": split_fraction},
            "summary": summarize_results(results, "calibrated"),
        },
        "stabilityGateConfig": {
            "model": "per-asset-three-stage-stability-gate",
            "objective": 0,
            "thresholds": {
                "splitFraction": split_fraction,
                "innerSelectFraction": 0.7,
                "stabilityScoreMin": 0,
                "stabilityTotalReturnMin": 0,
                "stabilitySharpeMin": 0,
                "stabilityDrawdownMin": 0,
            },
            "summary": summarize_results(results, "stableSelected"),
        },
        "topConfigs": top_configs,
        "oracleUpperBound": oracle_summary,
        "stockResults": results,
        "failures": failures,
    }
    if progress_path:
        final_progress = build_partial_progress(started_at, jobs, results, failures, progress_markets)
        final_progress["status"] = "complete"
        final_progress["final"] = {
            "bestConfig": experiment["bestConfig"],
            "stabilityGateConfig": experiment["stabilityGateConfig"],
            "oracleUpperBound": experiment["oracleUpperBound"],
        }
        write_progress(progress_path, final_progress)
    return experiment


def main() -> None:
    parser = argparse.ArgumentParser(description="按资产做时间切分参数校准实验")
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--history", default=str(DEFAULT_HISTORY))
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR))
    parser.add_argument("--markets", default="")
    parser.add_argument("--split-fraction", type=float, default=0.7)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--max-assets", type=int, default=0)
    parser.add_argument("--progress-output", default=str(DEFAULT_PROGRESS))
    args = parser.parse_args()

    experiment = run_experiment(
        Path(args.source),
        Path(args.data_dir),
        [item.strip() for item in args.markets.split(",") if item.strip()],
        args.split_fraction,
        args.workers,
        args.max_assets or None,
        Path(args.progress_output) if args.progress_output else None,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(experiment, ensure_ascii=False, indent=2), encoding="utf-8")
    append_history(Path(args.history), experiment)
    print(json.dumps({"output": str(output), "bestConfig": experiment["bestConfig"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
