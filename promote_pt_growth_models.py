import argparse
import json
from datetime import datetime
from pathlib import Path

from model_training import (
    DEFAULT_SPLIT_SEED,
    DEFAULT_VALIDATION_FRACTION,
    assign_train_validation_split,
    average_metric_group,
    empty_evidence,
    evaluate_fixed_params,
    find_candidate,
    params_key,
    summarize_evidence,
)


MARKETS = ["A股", "美股", "港股", "加密货币"]


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def aggregate_candidates(rows: list[dict], exclude_modes: set[str]) -> list[dict]:
    buckets: dict[tuple[str, float, float, float], dict] = {}
    for row in rows:
        for candidate in row.get("candidateScores", []):
            if candidate.get("mode") in exclude_modes:
                continue
            key = params_key(candidate)
            bucket = buckets.setdefault(
                key,
                {
                    "mode": candidate["mode"],
                    "qHead": candidate["qHead"],
                    "qTail": candidate["qTail"],
                    "eta": candidate["eta"],
                    "scores": [],
                    "improvements": [],
                    "metrics": [],
                    "baselines": [],
                },
            )
            bucket["scores"].append(safe_float(candidate.get("score")))
            bucket["improvements"].append(candidate.get("improvement", {}))
            bucket["metrics"].append(candidate.get("metrics", {}))
            bucket["baselines"].append(row.get("baseline", {}))

    aggregate = []
    for bucket in buckets.values():
        scores = bucket["scores"]
        improvements = bucket["improvements"]
        if not scores:
            continue
        count = len(scores)
        avg_improvement = average_metric_group(improvements)
        return_rate = sum(1 for item in improvements if safe_float(item.get("totalReturn")) > 0) / count
        sharpe_rate = sum(1 for item in improvements if safe_float(item.get("sharpe")) > 0) / count
        drawdown_rate = sum(1 for item in improvements if safe_float(item.get("maxDrawdown")) > 0) / count
        annual_rate = sum(1 for item in improvements if safe_float(item.get("annualReturn")) > 0) / count
        positive_score_rate = sum(1 for value in scores if value > 0) / count
        all_rate = sum(
            1
            for item in improvements
            if safe_float(item.get("totalReturn")) > 0
            and safe_float(item.get("sharpe")) > 0
            and safe_float(item.get("maxDrawdown")) > 0
        ) / count
        avg_score = sum(scores) / count
        objective = (
            avg_score
            + safe_float(avg_improvement.get("totalReturn")) * 0.35
            + safe_float(avg_improvement.get("annualReturn")) * 0.25
            + safe_float(avg_improvement.get("sharpe")) * 0.7
            + safe_float(avg_improvement.get("maxDrawdown")) * 1.1
            + positive_score_rate * 0.10
            + return_rate * 0.08
            + annual_rate * 0.05
            + sharpe_rate * 0.10
            + drawdown_rate * 0.16
            + all_rate * 0.18
        )
        aggregate.append(
            {
                "mode": bucket["mode"],
                "qHead": bucket["qHead"],
                "qTail": bucket["qTail"],
                "eta": bucket["eta"],
                "stocks": count,
                "avgScore": round(avg_score, 6),
                "growthObjective": round(objective, 6),
                "positiveScoreRate": round(positive_score_rate, 6),
                "returnImprovedRate": round(return_rate, 6),
                "annualReturnImprovedRate": round(annual_rate, 6),
                "sharpeImprovedRate": round(sharpe_rate, 6),
                "drawdownImprovedRate": round(drawdown_rate, 6),
                "allObjectivesImprovedRate": round(all_rate, 6),
                "avgBaseline": average_metric_group(bucket["baselines"]),
                "avgModel": average_metric_group(bucket["metrics"]),
                "avgImprovement": avg_improvement,
            }
        )
    return sorted(aggregate, key=lambda item: item["growthObjective"], reverse=True)


PASS_METRICS = ["totalReturn", "annualReturn", "sharpe", "maxDrawdown"]


def candidate_passes_metric_gate(item: dict) -> bool:
    improvement = item.get("avgImprovement", {})
    return all(safe_float(improvement.get(key)) > 0 for key in PASS_METRICS)


def choose_growth_params(rows: list[dict]) -> tuple[dict | None, list[dict]]:
    ranked = aggregate_candidates(rows, {"no_transform"})
    if not ranked:
        return None, []

    def positive_enough(item: dict) -> bool:
        improvement = item.get("avgImprovement", {})
        return (
            safe_float(improvement.get("totalReturn")) > 0
            and safe_float(improvement.get("annualReturn")) > 0
            and safe_float(improvement.get("sharpe")) > 0
        )

    def defensive_enough(item: dict) -> bool:
        improvement = item.get("avgImprovement", {})
        return safe_float(improvement.get("totalReturn")) > 0 and safe_float(improvement.get("maxDrawdown")) > 0

    selected = next((item for item in ranked if positive_enough(item)), None)
    if selected is None:
        selected = next((item for item in ranked if defensive_enough(item)), None)
    if selected is None:
        selected = ranked[0]
    return selected, ranked


def choose_validated_params(train_rows: list[dict], validation_rows: list[dict]) -> tuple[dict | None, list[dict], dict]:
    train_params, train_ranked = choose_growth_params(train_rows)
    validation_ranked = aggregate_candidates(validation_rows, {"no_transform"})
    validation_passed = [item for item in validation_ranked if candidate_passes_metric_gate(item)]

    if validation_passed:
        positive_score = [item for item in validation_passed if safe_float(item.get("avgScore")) > 0]
        pool = positive_score or validation_passed
        selected = sorted(
            pool,
            key=lambda item: (
                safe_float(item.get("avgScore")),
                safe_float(item.get("avgImprovement", {}).get("totalReturn")),
                safe_float(item.get("avgImprovement", {}).get("sharpe")),
                safe_float(item.get("avgImprovement", {}).get("maxDrawdown")),
            ),
            reverse=True,
        )[0]
        gate = {
            "status": "passed",
            "type": "validation_metric_gate",
            "requiredMetrics": PASS_METRICS,
            "validationPassedCandidates": len(validation_passed),
            "selectedFromPositiveScorePool": bool(positive_score),
            "trainingPreferredParameters": train_params,
        }
        return selected, validation_ranked, gate

    gate = {
        "status": "fallback",
        "type": "validation_metric_gate",
        "requiredMetrics": PASS_METRICS,
        "validationPassedCandidates": 0,
        "reason": "No non-no_transform parameter set improved all required validation metrics.",
        "trainingPreferredParameters": train_params,
    }
    return train_params, train_ranked, gate


def cross_validate_growth(rows: list[dict], folds: int, split_seed: str) -> dict:
    if not rows:
        return {"folds": [], "aggregateEvidence": empty_evidence()}
    actual_folds = min(max(2, folds), len(rows))
    fold_results = []
    baselines = []
    metrics = []
    improvements = []
    scores = []

    from model_training import fold_index

    for fold in range(actual_folds):
        train_rows = [row for row in rows if fold_index(row, actual_folds, split_seed) != fold]
        validation_rows = [row for row in rows if fold_index(row, actual_folds, split_seed) == fold]
        params, _ranked = choose_growth_params(train_rows)
        evidence = evaluate_fixed_params(validation_rows, params)
        fold_results.append({"fold": fold, "params": params, "validationEvidence": evidence})
        if not params:
            continue
        key = params_key(params)
        for row in validation_rows:
            candidate = find_candidate(row, key)
            if not candidate:
                continue
            baselines.append(row["baseline"])
            metrics.append(candidate["metrics"])
            improvements.append(candidate["improvement"])
            scores.append(safe_float(candidate.get("score")))

    if not improvements:
        return {"folds": fold_results, "aggregateEvidence": empty_evidence()}
    return {
        "folds": fold_results,
        "aggregateEvidence": summarize_evidence(baselines, metrics, improvements, scores),
    }


def promote_market(
    market: str,
    strategy_dir: Path,
    result_prefix: str,
    validation_fraction: float,
    split_seed: str,
    cv_folds: int,
) -> dict:
    market_dir = strategy_dir / market
    result_path = market_dir / f"{result_prefix}.jsonl"
    rows = load_jsonl(result_path)
    if not rows:
        raise RuntimeError(f"{market} 没有可整理的训练结果: {result_path}")

    assign_train_validation_split(rows, validation_fraction, split_seed)
    train_rows = [row for row in rows if row.get("split") == "train"]
    validation_rows = [row for row in rows if row.get("split") == "validation"]
    params, ranked, validation_gate = choose_validated_params(train_rows, validation_rows)
    latest_conservative_path = market_dir / "latest_model.json"
    conservative = {}
    if latest_conservative_path.exists():
        conservative = json.loads(latest_conservative_path.read_text(encoding="utf-8"))

    model = {
        **conservative,
        "market": market,
        "modelName": "PT Heavy Tail OHLCV Transformer",
        "modelVersion": "full-market-growth-1.0",
        "generatedAt": now_text(),
        "resultPath": str(result_path),
        "baseConservativeModelPath": str(latest_conservative_path),
        "conservativeParameters": conservative.get("parameters"),
        "parameters": params,
        "selectionMethod": (
            "Validation-gated promotion pass over the completed full-market candidate grid. "
            "It excludes no_transform and chooses a fixed market-level PT parameter set. "
            "Priority is given to parameters that improve validation-set total return, annual return, "
            "Sharpe ratio, and max drawdown at the same time."
        ),
        "validationGate": validation_gate,
        "counts": {
            "successfulStocks": len(rows),
            "trainStocks": len(train_rows),
            "validationStocks": len(validation_rows),
            "failedStocks": conservative.get("counts", {}).get("failedStocks", 0),
        },
        "trainEvidence": evaluate_fixed_params(train_rows, params),
        "validationEvidence": evaluate_fixed_params(validation_rows, params),
        "allEvidence": evaluate_fixed_params(rows, params),
        "crossValidation": cross_validate_growth(rows, cv_folds, split_seed)["aggregateEvidence"],
        "candidateAggregateTop20": ranked[:20],
    }
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    timestamped_path = market_dir / f"growth_model_{timestamp}.json"
    latest_path = market_dir / "latest_growth_model.json"
    timestamped_path.write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    latest_path.write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "market": market,
        "latestGrowthModel": str(latest_path),
        "timestampedGrowthModel": str(timestamped_path),
        "parameters": params,
        "counts": model["counts"],
        "validationEvidence": model["validationEvidence"],
        "allEvidence": model["allEvidence"],
        "conservativeParameters": model["conservativeParameters"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="从全量训练结果中提取 PT 提升型市场参数")
    parser.add_argument("--strategy-dir", default="strategy")
    parser.add_argument("--markets", default="A股,美股,港股,加密货币")
    parser.add_argument("--result-prefix", default="stock_results_fast")
    parser.add_argument("--validation-fraction", type=float, default=DEFAULT_VALIDATION_FRACTION)
    parser.add_argument("--split-seed", default=DEFAULT_SPLIT_SEED)
    parser.add_argument("--cv-folds", type=int, default=5)
    args = parser.parse_args()

    strategy_dir = Path(args.strategy_dir)
    markets = [item.strip() for item in args.markets.split(",") if item.strip()]
    summary = {"generatedAt": now_text(), "models": []}
    for market in markets:
        summary["models"].append(
            promote_market(
                market,
                strategy_dir,
                args.result_prefix,
                args.validation_fraction,
                args.split_seed,
                args.cv_folds,
            )
        )
    summary_path = strategy_dir / "latest_growth_training_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
