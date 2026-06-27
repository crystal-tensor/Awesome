import heapq
import json
from datetime import datetime
from pathlib import Path


MARKETS = ["A股", "美股", "港股", "加密货币"]
STRATEGY_DIR = Path("strategy")
PASS_METRICS = ["totalReturn", "annualReturn", "sharpe", "maxDrawdown"]


MODE_LABELS = {
    "tail_denoise": "尾部去噪",
    "vol_squeeze": "波动压缩",
    "crypto_trend_guard": "加密趋势防护",
    "momentum_regime": "动量状态",
    "downside_guard": "下行防护",
    "trend_smooth": "趋势平滑",
}


def safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def pct(value):
    return safe_float(value)


def params_match(candidate, params):
    return (
        candidate.get("mode") == params.get("mode")
        and safe_float(candidate.get("qHead")) == safe_float(params.get("qHead"))
        and safe_float(candidate.get("qTail")) == safe_float(params.get("qTail"))
        and safe_float(candidate.get("eta")) == safe_float(params.get("eta"))
    )


def compact_stock(row, selected):
    improvement = selected.get("improvement", {})
    metrics = selected.get("metrics", {})
    return {
        "market": row.get("market"),
        "symbol": row.get("symbol"),
        "name": row.get("name") or row.get("symbol"),
        "rows": row.get("rows"),
        "score": safe_float(selected.get("score")),
        "baseline": row.get("baseline", {}),
        "metrics": metrics,
        "improvement": improvement,
        "passAll": all(safe_float(improvement.get(key)) > 0 for key in PASS_METRICS),
    }


def push_top(heap, score, row, limit=20):
    payload = (score, json.dumps(row, ensure_ascii=False))
    if len(heap) < limit:
        heapq.heappush(heap, payload)
    elif score > heap[0][0]:
        heapq.heapreplace(heap, payload)


def sorted_heap(heap):
    return [json.loads(payload) for _score, payload in sorted(heap, key=lambda item: item[0], reverse=True)]


def build_market(market):
    market_dir = STRATEGY_DIR / market
    model = json.loads((market_dir / "latest_growth_model.json").read_text(encoding="utf-8"))
    params = model.get("parameters", {})
    result_path = market_dir / "stock_results_fast.jsonl"

    top_score = []
    top_return = []
    top_sharpe = []
    top_balanced = []
    pass_count = 0
    selected_count = 0

    with result_path.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            row = json.loads(line)
            selected = None
            for candidate in row.get("candidateScores", []):
                if params_match(candidate, params):
                    selected = candidate
                    break
            if not selected:
                continue
            selected_count += 1
            compact = compact_stock(row, selected)
            improvement = compact["improvement"]
            if compact["passAll"]:
                pass_count += 1
            balanced_score = (
                safe_float(improvement.get("totalReturn")) * 0.35
                + safe_float(improvement.get("annualReturn")) * 0.2
                + safe_float(improvement.get("sharpe")) * 0.35
                + safe_float(improvement.get("maxDrawdown")) * 0.55
                + safe_float(selected.get("score")) * 0.2
            )
            push_top(top_score, safe_float(selected.get("score")), compact)
            push_top(top_return, safe_float(improvement.get("totalReturn")), compact)
            push_top(top_sharpe, safe_float(improvement.get("sharpe")), compact)
            push_top(top_balanced, balanced_score, compact)

    validation = model.get("validationEvidence", {})
    all_evidence = model.get("allEvidence", {})
    return {
        "market": market,
        "modelPath": str(market_dir / "latest_growth_model.json"),
        "parameters": {
            "mode": params.get("mode"),
            "modeLabel": MODE_LABELS.get(params.get("mode"), params.get("mode")),
            "qHead": params.get("qHead"),
            "qTail": params.get("qTail"),
            "eta": params.get("eta"),
        },
        "counts": model.get("counts", {}),
        "validationGate": model.get("validationGate", {}),
        "validationEvidence": validation,
        "allEvidence": all_evidence,
        "selectedStockCount": selected_count,
        "selectedPassAllRate": pass_count / selected_count if selected_count else 0,
        "topStocks": {
            "balanced": sorted_heap(top_balanced),
            "score": sorted_heap(top_score),
            "return": sorted_heap(top_return),
            "sharpe": sorted_heap(top_sharpe),
        },
    }


def main():
    verification_path = STRATEGY_DIR / "training_verification_report.json"
    verification = json.loads(verification_path.read_text(encoding="utf-8"))
    markets = [build_market(market) for market in MARKETS]
    total_success = sum(item["counts"].get("successfulStocks", 0) for item in markets)
    total_failed = sum(item["counts"].get("failedStocks", 0) for item in markets)
    payload = {
        "generatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "title": "PT 重尾合成数据模型总览",
        "productPositioning": "我们出售的是由 PT 重尾分布和市场级参数优化模型生成的合成 OHLCV 数据，而不是单一交易信号。",
        "modelName": "PT Heavy Tail OHLCV Transformer + Validation-Gated Market Optimizer",
        "optimizerName": "验证门控市场参数优化器",
        "grid": {
            "qHead": [0.7, 0.8, 0.85],
            "qTail": [0.9, 0.95, 0.97],
            "eta": [0.2, 0.5, 0.8],
            "modes": ["no_transform", "tail_denoise", "trend_smooth", "vol_squeeze", "downside_guard", "momentum_regime", "crypto_trend_guard"],
            "combinations": 163,
        },
        "ptBuckets": [
            {
                "key": "H",
                "name": "Head 常态区",
                "definition": "收益绝对值低于 qHead 分位数，代表多数正常交易日。",
                "role": "尽量保持真实市场结构，防止合成数据过度扰动。",
            },
            {
                "key": "M",
                "name": "Middle 过渡区",
                "definition": "收益绝对值位于 qHead 到 qTail 之间，是趋势、波动和反转开始显现的区域。",
                "role": "注入适度 PT 权重，让模型学习行情从常态滑向尾部时的形态。",
            },
            {
                "key": "L",
                "name": "Long-tail 极端区",
                "definition": "收益绝对值超过 qTail 分位数，代表少数但决定收益与回撤的尾部交易日。",
                "role": "用 Porter-Thomas 重尾权重重排极端状态，使合成数据更关注黑天鹅和大幅波动。",
            },
        ],
        "syntheticDataFields": ["pt_open", "pt_high", "pt_low", "pt_close", "pt_volume", "pt_weight", "pt_blend", "bucket"],
        "marketTotals": {
            "markets": len(markets),
            "successfulStocks": total_success,
            "failedStocks": total_failed,
            "verified": bool(verification.get("passed")),
        },
        "verification": verification,
        "markets": markets,
    }
    output = STRATEGY_DIR / "model_overview_data.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output), "markets": len(markets), "successfulStocks": total_success, "failedStocks": total_failed}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
