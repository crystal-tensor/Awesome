import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from model_training import average_metric_group, empty_evidence, summarize_evidence


MARKETS = ["A股", "美股", "港股", "加密货币"]


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


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


def clean_params(params: dict) -> dict:
    return {
        "mode": params.get("mode"),
        "qHead": safe_float(params.get("qHead")),
        "qTail": safe_float(params.get("qTail")),
        "eta": safe_float(params.get("eta")),
    }


def params_key(params: dict) -> str:
    cleaned = clean_params(params)
    return f"{cleaned['mode']}|{cleaned['qHead']}|{cleaned['qTail']}|{cleaned['eta']}"


def stock_rank_score(row: dict, best: dict) -> float:
    improvement = best.get("improvement", {})
    metrics = best.get("metrics", {})
    return (
        safe_float(best.get("score")) * 0.45
        + safe_float(improvement.get("totalReturn")) * 0.35
        + safe_float(improvement.get("annualReturn")) * 0.25
        + safe_float(improvement.get("sharpe")) * 0.35
        + safe_float(improvement.get("maxDrawdown")) * 0.25
        + safe_float(metrics.get("totalReturn")) * 0.18
        + safe_float(metrics.get("annualReturn")) * 0.12
    )


def compact_stock(row: dict, best: dict) -> dict:
    return {
        "market": row.get("market"),
        "symbol": row.get("symbol"),
        "name": row.get("name") or row.get("symbol"),
        "rows": row.get("rows"),
        "params": clean_params(best),
        "score": safe_float(best.get("score")),
        "rankScore": round(stock_rank_score(row, best), 6),
        "baseline": row.get("baseline", {}),
        "metrics": best.get("metrics", {}),
        "improvement": best.get("improvement", {}),
    }


def summarize_best_rows(rows: list[dict]) -> dict:
    baselines = []
    metrics = []
    improvements = []
    scores = []
    for row in rows:
        best = row.get("best")
        if not best:
            continue
        baselines.append(row.get("baseline", {}))
        metrics.append(best.get("metrics", {}))
        improvements.append(best.get("improvement", {}))
        scores.append(safe_float(best.get("score")))
    if not improvements:
        return empty_evidence()
    return summarize_evidence(baselines, metrics, improvements, scores)


def build_market_alpha(market: str, strategy_dir: Path, result_prefix: str) -> dict:
    market_dir = strategy_dir / market
    result_path = market_dir / f"{result_prefix}.jsonl"
    rows = load_jsonl(result_path)
    if not rows:
        raise RuntimeError(f"{market} 没有可提升的逐股训练结果: {result_path}")

    per_stock = {}
    compact_rows = []
    param_counter = Counter()
    param_scores = defaultdict(list)
    param_improvements = defaultdict(list)

    for row in rows:
        best = row.get("best")
        symbol = str(row.get("symbol") or "").upper()
        if not best or not symbol:
            continue
        stock = compact_stock(row, best)
        per_stock[symbol] = stock
        compact_rows.append(stock)
        key = params_key(best)
        param_counter[key] += 1
        param_scores[key].append(safe_float(best.get("score")))
        param_improvements[key].append(best.get("improvement", {}))

    representative_params = []
    for key, count in param_counter.most_common(20):
        mode, q_head, q_tail, eta = key.split("|")
        representative_params.append(
            {
                "mode": mode,
                "qHead": safe_float(q_head),
                "qTail": safe_float(q_tail),
                "eta": safe_float(eta),
                "stocks": count,
                "avgScore": round(sum(param_scores[key]) / len(param_scores[key]), 6),
                "avgImprovement": average_metric_group(param_improvements[key]),
            }
        )

    top_stocks = sorted(compact_rows, key=lambda item: item["rankScore"], reverse=True)[:100]
    alpha_evidence = summarize_best_rows(rows)
    model = {
        "market": market,
        "modelName": "PT Heavy Tail Per-Stock Alpha Enhancer",
        "modelVersion": "full-market-alpha-1.0",
        "generatedAt": now_text(),
        "resultPath": str(result_path),
        "selectionMethod": (
            "Full-data per-stock alpha promotion. Every stock keeps its own highest-scoring PT "
            "parameter set from the completed 163-combination candidate grid. The objective is "
            "single-stock return enhancement while preserving the original user strategy rules."
        ),
        "objective": "个股最优/收益增强模型",
        "counts": {
            "successfulStocks": len(compact_rows),
            "sourceRows": len(rows),
            "uniqueParameterSets": len(param_counter),
        },
        "alphaEvidence": alpha_evidence,
        "representativeParameterSets": representative_params,
        "topStocks": top_stocks,
        "perStockParameters": per_stock,
    }

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    timestamped_path = market_dir / f"alpha_model_{timestamp}.json"
    latest_path = market_dir / "latest_alpha_model.json"
    timestamped_path.write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    latest_path.write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "market": market,
        "latestAlphaModel": str(latest_path),
        "timestampedAlphaModel": str(timestamped_path),
        "counts": model["counts"],
        "alphaEvidence": model["alphaEvidence"],
        "topStocks": model["topStocks"][:10],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="把全量逐股候选结果提升为个股最优 PT alpha 模型")
    parser.add_argument("--strategy-dir", default="strategy")
    parser.add_argument("--markets", default="A股,美股,港股,加密货币")
    parser.add_argument("--result-prefix", default="stock_results_fast")
    args = parser.parse_args()

    strategy_dir = Path(args.strategy_dir)
    markets = [item.strip() for item in args.markets.split(",") if item.strip()]
    summary = {
        "generatedAt": now_text(),
        "objective": "个股最优/收益增强模型",
        "resultPrefix": args.result_prefix,
        "models": [build_market_alpha(market, strategy_dir, args.result_prefix) for market in markets],
    }
    summary_path = strategy_dir / "latest_alpha_training_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
