import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from model_training import average_metric_group, empty_evidence, summarize_evidence


MARKETS = ["A股", "美股", "港股", "加密货币"]
REQUIRED_IMPROVEMENTS = ["totalReturn", "annualReturn", "sharpe"]


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


def clean_params(candidate: dict) -> dict:
    return {
        "mode": candidate.get("mode"),
        "qHead": safe_float(candidate.get("qHead")),
        "qTail": safe_float(candidate.get("qTail")),
        "eta": safe_float(candidate.get("eta")),
    }


def params_key(candidate: dict) -> str:
    params = clean_params(candidate)
    return f"{params['mode']}|{params['qHead']}|{params['qTail']}|{params['eta']}"


def strict_pass(candidate: dict) -> bool:
    improvement = candidate.get("improvement", {})
    return all(safe_float(improvement.get(key)) > 0 for key in REQUIRED_IMPROVEMENTS)


def drawdown_pass(candidate: dict) -> bool:
    return safe_float(candidate.get("improvement", {}).get("maxDrawdown")) > 0


def hard_objective(candidate: dict) -> float:
    improvement = candidate.get("improvement", {})
    metrics = candidate.get("metrics", {})
    drawdown_gain = safe_float(improvement.get("maxDrawdown"))
    return (
        safe_float(improvement.get("totalReturn")) * 0.90
        + safe_float(improvement.get("annualReturn")) * 0.70
        + safe_float(improvement.get("sharpe")) * 1.20
        + max(drawdown_gain, 0.0) * 1.80
        + min(drawdown_gain, 0.0) * 0.35
        + safe_float(candidate.get("score")) * 0.18
        + safe_float(metrics.get("totalReturn")) * 0.08
        + safe_float(metrics.get("annualReturn")) * 0.06
    )


def soft_objective(candidate: dict) -> float:
    improvement = candidate.get("improvement", {})
    positive_required = sum(1 for key in REQUIRED_IMPROVEMENTS if safe_float(improvement.get(key)) > 0)
    return (
        positive_required * 10.0
        + safe_float(improvement.get("totalReturn")) * 0.55
        + safe_float(improvement.get("annualReturn")) * 0.45
        + safe_float(improvement.get("sharpe")) * 0.90
        + safe_float(improvement.get("maxDrawdown")) * 1.25
        + safe_float(candidate.get("score")) * 0.15
    )


def select_candidate(row: dict) -> tuple[dict | None, str]:
    candidates = [item for item in row.get("candidateScores", []) if item.get("mode") != "no_transform"]
    strict = [item for item in candidates if strict_pass(item)]
    if strict:
        drawdown_positive = [item for item in strict if drawdown_pass(item)]
        pool = drawdown_positive or strict
        selected = max(pool, key=hard_objective)
        return selected, "strict_plus_drawdown" if drawdown_positive else "strict_return_annual_sharpe"
    if candidates:
        return max(candidates, key=soft_objective), "fallback_best_available"
    return None, "missing_candidates"


def compact_stock(row: dict, selected: dict, status: str) -> dict:
    improvement = selected.get("improvement", {})
    return {
        "market": row.get("market"),
        "symbol": row.get("symbol"),
        "name": row.get("name") or row.get("symbol"),
        "rows": row.get("rows"),
        "params": clean_params(selected),
        "score": safe_float(selected.get("score")),
        "strictObjective": round(hard_objective(selected), 6),
        "selectionStatus": status,
        "strictPass": strict_pass(selected),
        "drawdownPass": drawdown_pass(selected),
        "baseline": row.get("baseline", {}),
        "metrics": selected.get("metrics", {}),
        "improvement": improvement,
    }


def summarize_selected(stocks: list[dict]) -> dict:
    baselines = [item.get("baseline", {}) for item in stocks]
    metrics = [item.get("metrics", {}) for item in stocks]
    improvements = [item.get("improvement", {}) for item in stocks]
    scores = [safe_float(item.get("score")) for item in stocks]
    if not improvements:
        return empty_evidence()
    evidence = summarize_evidence(baselines, metrics, improvements, scores)
    total = len(stocks)
    evidence["strictPassRate"] = round(sum(1 for item in stocks if item.get("strictPass")) / total, 6)
    evidence["strictPlusDrawdownPassRate"] = round(
        sum(1 for item in stocks if item.get("strictPass") and item.get("drawdownPass")) / total,
        6,
    )
    evidence["fallbackRate"] = round(
        sum(1 for item in stocks if item.get("selectionStatus") == "fallback_best_available") / total,
        6,
    )
    return evidence


def promote_market(market: str, strategy_dir: Path, result_prefix: str) -> dict:
    market_dir = strategy_dir / market
    result_path = market_dir / f"{result_prefix}.jsonl"
    rows = load_jsonl(result_path)
    if not rows:
        raise RuntimeError(f"{market} 没有可用全量候选训练结果: {result_path}")

    per_stock = {}
    selected_stocks = []
    status_counter = Counter()
    params_counter = Counter()
    params_scores = defaultdict(list)
    params_improvements = defaultdict(list)

    for row in rows:
        selected, status = select_candidate(row)
        status_counter[status] += 1
        if not selected:
            continue
        stock = compact_stock(row, selected, status)
        symbol = str(row.get("symbol") or "").upper()
        if symbol:
            per_stock[symbol] = stock
        selected_stocks.append(stock)
        key = params_key(selected)
        params_counter[key] += 1
        params_scores[key].append(safe_float(selected.get("score")))
        params_improvements[key].append(selected.get("improvement", {}))

    representative_params = []
    for key, count in params_counter.most_common(20):
        mode, q_head, q_tail, eta = key.split("|")
        representative_params.append(
            {
                "mode": mode,
                "qHead": safe_float(q_head),
                "qTail": safe_float(q_tail),
                "eta": safe_float(eta),
                "stocks": count,
                "avgScore": round(sum(params_scores[key]) / len(params_scores[key]), 6),
                "avgImprovement": average_metric_group(params_improvements[key]),
            }
        )

    top_stocks = sorted(selected_stocks, key=lambda item: item["strictObjective"], reverse=True)[:100]
    model = {
        "market": market,
        "modelName": "PT Strict Per-Stock Alpha Enhancer",
        "modelVersion": "strict-full-market-alpha-2.0",
        "generatedAt": now_text(),
        "resultPath": str(result_path),
        "objective": "累计收益、年化收益、夏普比率必须提升；最大回撤尽可能变小",
        "selectionMethod": (
            "Every stock is selected independently from the full-market candidate grid. "
            "The selector first requires positive total return, annual return, and Sharpe improvements. "
            "Among passing candidates it prefers positive max-drawdown improvement, then ranks by a weighted strict objective. "
            "Only when no candidate satisfies the three required improvements does it fall back to the best available candidate."
        ),
        "requiredImprovements": REQUIRED_IMPROVEMENTS,
        "preferredImprovement": "maxDrawdown",
        "counts": {
            "sourceRows": len(rows),
            "successfulStocks": len(selected_stocks),
            "uniqueParameterSets": len(params_counter),
            "selectionStatus": dict(status_counter),
        },
        "alphaEvidence": summarize_selected(selected_stocks),
        "representativeParameterSets": representative_params,
        "topStocks": top_stocks,
        "perStockParameters": per_stock,
    }

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    timestamped_path = market_dir / f"strict_alpha_model_{timestamp}.json"
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
    parser = argparse.ArgumentParser(description="从全量候选结果重新训练严格逐股收益增强模型")
    parser.add_argument("--strategy-dir", default="strategy")
    parser.add_argument("--markets", default="A股,美股,港股,加密货币")
    parser.add_argument("--result-prefix", default="stock_results_fast")
    args = parser.parse_args()

    strategy_dir = Path(args.strategy_dir)
    markets = [item.strip() for item in args.markets.split(",") if item.strip()]
    summary = {
        "generatedAt": now_text(),
        "objective": "累计收益、年化收益、夏普比率必须提升；最大回撤尽可能变小",
        "resultPrefix": args.result_prefix,
        "models": [promote_market(market, strategy_dir, args.result_prefix) for market in markets],
    }
    summary_path = strategy_dir / "latest_alpha_training_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
