import json
from pathlib import Path


MARKETS = ["A股", "美股", "港股", "加密货币"]
PASS_METRICS = ["totalReturn", "annualReturn", "sharpe", "maxDrawdown"]


def count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8") as file:
        return sum(1 for line in file if line.strip())


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def check_market(strategy_dir: Path, market: str) -> dict:
    market_dir = strategy_dir / market
    progress_path = market_dir / "stock_results_fast_progress.json"
    conservative_path = market_dir / "latest_model.json"
    growth_path = market_dir / "latest_growth_model.json"
    result_path = market_dir / "stock_results_fast.jsonl"
    failure_path = market_dir / "stock_results_fast_failures.jsonl"
    issues = []

    for path in [progress_path, conservative_path, growth_path, result_path, failure_path]:
        if not path.exists():
            issues.append(f"缺少文件: {path}")

    progress = load_json(progress_path) if progress_path.exists() else {}
    growth = load_json(growth_path) if growth_path.exists() else {}
    rows = count_jsonl(result_path)
    failures = count_jsonl(failure_path)
    total_files = int(progress.get("totalFiles", 0) or 0)

    if progress.get("status") != "complete":
        issues.append("训练进度不是 complete")
    if rows != int(progress.get("successfulStocks", -1)):
        issues.append("成功股票数与结果文件行数不一致")
    if failures != int(progress.get("failedStocks", -1)):
        issues.append("失败股票数与失败文件行数不一致")
    if total_files and rows + failures != total_files:
        issues.append("成功股票数 + 失败股票数不等于 totalFiles")

    params = growth.get("parameters") or {}
    if not params:
        issues.append("提升模型缺少 parameters")
    if params.get("mode") == "no_transform":
        issues.append("提升模型不能是 no_transform")

    validation_gate = growth.get("validationGate") or {}
    if validation_gate.get("status") != "passed":
        issues.append("validationGate 未通过")

    validation = growth.get("validationEvidence") or {}
    if int(validation.get("stocks", 0) or 0) <= 0:
        issues.append("验证集股票数为空")
    improvement = validation.get("avgImprovement") or {}
    metric_pass = {}
    for key in PASS_METRICS:
        value = float(improvement.get(key, 0) or 0)
        metric_pass[key] = value > 0
        if value <= 0:
            issues.append(f"验证集 {key} 平均改善未大于 0: {value}")

    counts = growth.get("counts") or {}
    if rows != int(counts.get("successfulStocks", -1)):
        issues.append("提升模型 counts.successfulStocks 与结果文件行数不一致")
    if failures != int(counts.get("failedStocks", -1)):
        issues.append("提升模型 counts.failedStocks 与失败文件行数不一致")

    return {
        "market": market,
        "passed": not issues,
        "issues": issues,
        "files": {
            "progress": str(progress_path),
            "conservativeModel": str(conservative_path),
            "growthModel": str(growth_path),
            "results": str(result_path),
            "failures": str(failure_path),
        },
        "counts": {
            "totalFiles": total_files,
            "successfulStocks": rows,
            "failedStocks": failures,
            "trainStocks": counts.get("trainStocks"),
            "validationStocks": counts.get("validationStocks"),
        },
        "parameters": {
            "mode": params.get("mode"),
            "qHead": params.get("qHead"),
            "qTail": params.get("qTail"),
            "eta": params.get("eta"),
        },
        "validationGate": validation_gate,
        "validationEvidence": {
            "stocks": validation.get("stocks"),
            "avgScore": validation.get("avgScore"),
            "avgImprovement": improvement,
            "metricPass": metric_pass,
        },
    }


def main() -> None:
    strategy_dir = Path("strategy")
    old_dir = strategy_dir / "old"
    code_dir = strategy_dir / "code"
    report = {
        "passed": True,
        "strategyDir": str(strategy_dir),
        "oldParameterFiles": count_jsonl(Path("/dev/null")),
        "checks": [],
        "globalIssues": [],
    }

    if not old_dir.exists() or not any(old_dir.iterdir()):
        report["globalIssues"].append("strategy/old 没有旧参数文件")
    report["oldParameterFiles"] = len([item for item in old_dir.iterdir() if item.is_file()]) if old_dir.exists() else 0
    if not code_dir.exists() or not any(code_dir.glob("*.py")):
        report["globalIssues"].append("strategy/code 没有策略代码归档")

    for market in MARKETS:
        market_report = check_market(strategy_dir, market)
        report["checks"].append(market_report)

    report["passed"] = not report["globalIssues"] and all(item["passed"] for item in report["checks"])
    output_path = strategy_dir / "training_verification_report.json"
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
