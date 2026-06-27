import argparse
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.multioutput import MultiOutputRegressor


DEFAULT_SOURCE = Path(".tmp/time-split-crypto-stability-latest.json")
DEFAULT_OUTPUT = Path(".tmp/crypto-regime-gate-latest.json")
DEFAULT_HISTORY = Path(".tmp/asset-selector-experiments.json")
DEFAULT_DATA_DIR = Path("data")


def data_csv_path(row: dict, data_dir: Path) -> Path:
    safe_market = row["market"].replace("/", "_").replace("\\", "_").replace(":", "_")
    safe_symbol = row["symbol"].replace("/", "_").replace("\\", "_").replace(":", "_")
    return data_dir / f"{safe_market}_{safe_symbol}.csv"


def safe_float(value) -> float:
    try:
        value = float(value)
    except Exception:
        return 0.0
    if not np.isfinite(value):
        return 0.0
    return value


def pre_validation_features(row: dict, data_dir: Path) -> list[float]:
    path = data_csv_path(row, data_dir)
    if not path.exists():
        return [0.0] * 26
    raw = pd.read_csv(path, parse_dates=["date"])
    raw = raw.sort_values("date")
    split_rows = row.get("splitRows", {})
    cut = int(split_rows.get("train", len(raw) * 0.7))
    pre = raw.iloc[:cut].copy()
    for column in ["open", "high", "low", "close", "volume"]:
        pre[column] = pd.to_numeric(pre[column], errors="coerce")
    pre = pre.dropna(subset=["open", "high", "low", "close"])
    if len(pre) < 80:
        return [0.0] * 26
    close = pre["close"]
    ret = close.pct_change().dropna()
    volume = pd.to_numeric(pre["volume"], errors="coerce").replace(0, np.nan)
    net = (1 + ret).cumprod()
    drawdown = net / net.cummax() - 1
    high_low = ((pre["high"] - pre["low"]) / close.replace(0, np.nan)).replace([np.inf, -np.inf], np.nan)
    windows = [20, 60, 120]
    features = [
        safe_float(ret.mean()),
        safe_float(ret.std()),
        safe_float(ret.skew()),
        safe_float(ret.kurt()),
        safe_float((ret > 0).mean()),
        safe_float(ret.autocorr(lag=1)),
        safe_float(ret.autocorr(lag=5)),
        safe_float(drawdown.min()),
        safe_float(drawdown.iloc[-1]),
        safe_float(drawdown.tail(60).min()),
        safe_float(high_low.mean()),
        safe_float(high_low.quantile(0.95)),
        safe_float(np.log1p(volume).std()),
        safe_float(volume.pct_change(fill_method=None).replace([np.inf, -np.inf], np.nan).std()),
    ]
    for window in windows:
        features.extend(
            [
                safe_float(close.pct_change(window).iloc[-1]),
                safe_float(ret.tail(window).std()),
                safe_float(ret.tail(window).mean()),
                safe_float((ret.tail(window) > 0).mean()),
            ]
        )
    return features


def candidate_features(candidate: dict, row: dict, data_dir: Path, candidate_kind: str) -> list[float]:
    mode_order = [
        "no_transform",
        "tail_denoise",
        "pt_amplify",
        "trend_smooth",
        "vol_squeeze",
        "downside_guard",
        "momentum_regime",
        "crypto_trend_guard",
    ]
    features = [
        safe_float(candidate.get("qHead")),
        safe_float(candidate.get("qTail")),
        safe_float(candidate.get("eta")),
        safe_float(candidate.get("qTail", 0) - candidate.get("qHead", 0)),
        1.0 if candidate_kind == "calibrated" else 0.0,
        1.0 if candidate_kind == "stableSelected" else 0.0,
        1.0 if candidate_kind == "candidatePool" else 0.0,
        safe_float(candidate.get("trainScore")),
        safe_float(candidate.get("selectScore")),
        safe_float(candidate.get("stabilityScore")),
        safe_float(candidate.get("selectScore", 0) - candidate.get("stabilityScore", 0)),
        safe_float(candidate.get("trainScore", 0) - candidate.get("stabilityScore", 0)),
    ]
    for metric_group in ["trainImprovement", "selectImprovement", "stabilityImprovement"]:
        improvement = candidate.get(metric_group, {})
        features.extend(
            [
                safe_float(improvement.get("totalReturn")),
                safe_float(improvement.get("annualReturn")),
                safe_float(improvement.get("sharpe")),
                safe_float(improvement.get("maxDrawdown")),
            ]
        )
    features.extend([1.0 if candidate.get("mode") == mode else 0.0 for mode in mode_order])
    features.extend(pre_validation_features(row, data_dir))
    return features


def target_values(candidate: dict) -> list[float]:
    improvement = candidate["validationImprovement"]
    all_objectives = float(
        improvement["totalReturn"] > 0
        and improvement["sharpe"] > 0
        and improvement["maxDrawdown"] > 0
    )
    return [
        safe_float(candidate.get("validationScore")),
        safe_float(improvement["totalReturn"]),
        safe_float(improvement["annualReturn"]),
        safe_float(improvement["sharpe"]),
        safe_float(improvement["maxDrawdown"]),
        all_objectives,
    ]


def summarize(rows: list[dict]) -> dict:
    improvements = [item["chosen"]["validationImprovement"] for item in rows]
    count = len(improvements)
    by_market = {}
    for market in sorted({item["market"] for item in rows}):
        market_rows = [item for item in rows if item["market"] == market]
        market_improvements = [item["chosen"]["validationImprovement"] for item in market_rows]
        n_market = len(market_rows)
        by_market[market] = {
            "assets": n_market,
            "activeRate": round(sum(item["chosen"]["mode"] != "no_transform" for item in market_rows) / n_market, 6),
            "avgImprovement": {
                metric: round(sum(item[metric] for item in market_improvements) / n_market, 6)
                for metric in ["totalReturn", "annualReturn", "sharpe", "maxDrawdown"]
            },
            "allObjectivesImprovedRate": round(
                sum(item["totalReturn"] > 0 and item["sharpe"] > 0 and item["maxDrawdown"] > 0 for item in market_improvements)
                / n_market,
                6,
            ),
        }
    return {
        "assets": count,
        "activeRate": round(sum(item["chosen"]["mode"] != "no_transform" for item in rows) / count, 6),
        "avgImprovement": {
            metric: round(sum(item[metric] for item in improvements) / count, 6)
            for metric in ["totalReturn", "annualReturn", "sharpe", "maxDrawdown"]
        },
        "returnImprovedRate": round(sum(item["totalReturn"] > 0 for item in improvements) / count, 6),
        "sharpeImprovedRate": round(sum(item["sharpe"] > 0 for item in improvements) / count, 6),
        "drawdownImprovedRate": round(sum(item["maxDrawdown"] > 0 for item in improvements) / count, 6),
        "allObjectivesImprovedRate": round(
            sum(item["totalReturn"] > 0 and item["sharpe"] > 0 and item["maxDrawdown"] > 0 for item in improvements) / count,
            6,
        ),
        "byMarket": by_market,
    }


def make_model(model_name: str, fast: bool = False):
    if model_name == "extra_trees":
        return ExtraTreesRegressor(
            n_estimators=72 if fast else 160,
            min_samples_leaf=3 if fast else 2,
            max_features=0.75 if fast else 0.8,
            random_state=73,
            n_jobs=-1,
        )
    if model_name == "random_forest":
        return RandomForestRegressor(
            n_estimators=72 if fast else 160,
            min_samples_leaf=3 if fast else 2,
            max_features=0.75 if fast else 0.8,
            random_state=41,
            n_jobs=-1,
        )
    return MultiOutputRegressor(
        HistGradientBoostingRegressor(max_iter=90, learning_rate=0.06, min_samples_leaf=6, l2_regularization=0.05, random_state=29)
    )


def build_samples(payload: dict, data_dir: Path) -> tuple[list[dict], np.ndarray, np.ndarray, list[dict]]:
    rows = payload["stockResults"]
    samples = []
    x_rows = []
    y_rows = []
    for asset_index, row in enumerate(rows):
        candidates = []
        if row.get("candidatePool"):
            candidates.extend(("candidatePool", candidate) for candidate in row["candidatePool"])
        else:
            candidates.extend((kind, row[kind]) for kind in ["calibrated", "stableSelected"])
        seen = set()
        for kind, candidate in candidates:
            if candidate["mode"] == "no_transform":
                continue
            key = (
                candidate.get("mode"),
                safe_float(candidate.get("qHead")),
                safe_float(candidate.get("qTail")),
                safe_float(candidate.get("eta")),
            )
            if key in seen:
                continue
            seen.add(key)
            samples.append({"assetIndex": asset_index, "kind": kind, "candidate": candidate})
            x_rows.append(candidate_features(candidate, row, data_dir, kind))
            y_rows.append(target_values(candidate))
    return rows, np.asarray(x_rows, dtype=float), np.asarray(y_rows, dtype=float), samples


def cross_validated_predictions(
    rows: list[dict],
    x_values: np.ndarray,
    y_values: np.ndarray,
    samples: list[dict],
    model_name: str,
    fast: bool = False,
) -> dict[int, list[dict]]:
    predictions_by_asset = {idx: [] for idx in range(len(rows))}
    for asset_index in range(len(rows)):
        train_indices = [idx for idx, sample in enumerate(samples) if sample["assetIndex"] != asset_index]
        validation_indices = [idx for idx, sample in enumerate(samples) if sample["assetIndex"] == asset_index]
        if not train_indices or not validation_indices:
            continue
        model = make_model(model_name, fast=fast)
        model.fit(x_values[train_indices], y_values[train_indices])
        predictions = model.predict(x_values[validation_indices])
        for local_idx, prediction in zip(validation_indices, predictions):
            predictions_by_asset[asset_index].append(
                {
                    "kind": samples[local_idx]["kind"],
                    "candidate": samples[local_idx]["candidate"],
                    "prediction": [safe_float(value) for value in prediction],
                }
            )
    return predictions_by_asset


def evaluate_gate(payload: dict, data_dir: Path, model_prefix: str, fast: bool = False) -> dict:
    rows, x_values, y_values, samples = build_samples(payload, data_dir)
    configs = []
    model_names = ["extra_trees"] if fast else ["extra_trees", "random_forest", "hgb"]
    score_grid = [-0.15, 0, 0.10] if fast else [-0.15, -0.05, 0, 0.05, 0.10]
    return_grid = [-0.05, 0, 0.03] if fast else [-0.05, -0.01, 0, 0.03]
    sharpe_grid = [-0.05, 0, 0.03] if fast else [-0.05, -0.01, 0, 0.03]
    drawdown_grid = [-0.03, 0, 0.02] if fast else [-0.03, -0.005, 0, 0.02]
    for model_name in model_names:
        predictions_by_asset = cross_validated_predictions(rows, x_values, y_values, samples, model_name, fast=fast)
        for score_min in score_grid:
            for ret_min in return_grid:
                for sharpe_min in sharpe_grid:
                    for dd_min in drawdown_grid:
                        chosen_rows = []
                        for asset_index, row in enumerate(rows):
                            fallback = row["fallback"]
                            eligible = []
                            for item in predictions_by_asset.get(asset_index, []):
                                pred = item["prediction"]
                                if (
                                    pred[0] >= score_min
                                    and pred[1] >= ret_min
                                    and pred[3] >= sharpe_min
                                    and pred[4] >= dd_min
                                ):
                                    rank = pred[0] + pred[1] + pred[3] + pred[4] + 0.35 * pred[5]
                                    eligible.append((rank, item["candidate"]))
                            chosen = max(eligible, key=lambda item: item[0])[1] if eligible else fallback
                            chosen_rows.append(
                                {
                                    "market": row["market"],
                                    "symbol": row["symbol"],
                                    "name": row["name"],
                                    "chosen": chosen,
                                }
                            )
                        summary = summarize(chosen_rows)
                        avg = summary["avgImprovement"]
                        penalty = sum(
                            max(0, -market["avgImprovement"]["totalReturn"]) * 3
                            + max(0, -market["avgImprovement"]["sharpe"]) * 2.4
                            + max(0, -market["avgImprovement"]["maxDrawdown"]) * 3.2
                            for market in summary["byMarket"].values()
                        )
                        objective = (
                            avg["totalReturn"]
                            + avg["sharpe"]
                            + avg["maxDrawdown"]
                            + 0.85 * summary["allObjectivesImprovedRate"]
                            + 0.06 * summary["activeRate"]
                            - penalty
                        )
                        configs.append(
                            {
                                "model": f"{model_prefix}-{model_name}",
                                "objective": round(objective, 6),
                                "thresholds": {
                                    "predictedScoreMin": score_min,
                                    "predictedTotalReturnMin": ret_min,
                                    "predictedSharpeMin": sharpe_min,
                                    "predictedDrawdownMin": dd_min,
                                },
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
    return ranked[0], configs[:20], safe_configs[:20]


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


def run_experiment(source: Path, data_dir: Path, fast: bool = False) -> dict:
    payload = json.loads(source.read_text(encoding="utf-8"))
    rows, x_values, _y_values, _samples = build_samples(payload, data_dir)
    markets = sorted({row["market"] for row in payload["stockResults"]})
    market_label = "、".join(markets)
    is_crypto_only = markets == ["加密货币"]
    model_prefix = "crypto-regime-gate" if is_crypto_only else "time-split-regime-gate"
    best, top_configs, top_safe_configs = evaluate_gate(payload, data_dir, model_prefix, fast=fast)
    market_values = [
        metric
        for market in best["summary"]["byMarket"].values()
        for metric in market["avgImprovement"].values()
    ]
    safe = all(value >= 0 for value in market_values)
    return {
        "generatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "experimentName": "crypto-regime-gate-cv" if is_crypto_only else "time-split-regime-gate-cv",
        "status": "candidate_safer_not_promoted" if safe else "candidate_not_promoted",
        "conclusion": (
            "加密货币状态门控在交叉验证中保持平均不为负，但覆盖率仍未达到多数资产。"
            if safe and is_crypto_only
            else f"{market_label} 状态门控在交叉验证中保持平均不为负，但覆盖率仍未达到多数资产。"
            if safe
            else "加密货币状态门控仍无法避免验证期负贡献。"
            if is_crypto_only
            else f"{market_label} 状态门控仍无法避免验证期负贡献。"
        ),
        "sourceModelPath": str(source),
        "fastMode": fast,
        "assetCount": len(payload["stockResults"]),
        "sampleCount": int(len(_samples)),
        "featureCount": int(x_values.shape[1]) if len(_samples) else 0,
        "bestConfig": best,
        "oracleUpperBound": payload.get("oracleUpperBound", {}),
        "topConfigs": top_configs,
        "topSafeConfigs": top_safe_configs,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="加密货币市场状态门控实验")
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--history", default=str(DEFAULT_HISTORY))
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR))
    parser.add_argument("--fast", action="store_true")
    args = parser.parse_args()
    experiment = run_experiment(Path(args.source), Path(args.data_dir), fast=args.fast)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(experiment, ensure_ascii=False, indent=2), encoding="utf-8")
    append_history(Path(args.history), experiment)
    print(json.dumps({"output": str(output), "bestConfig": experiment["bestConfig"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
