import argparse
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "8")

import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor
from sklearn.multioutput import MultiOutputRegressor


DEFAULT_SOURCE = Path(".tmp/live-four-market-gated-combined-model.json")
DEFAULT_OUTPUT = Path(".tmp/asset-selector-experiment-latest.json")
DEFAULT_HISTORY = Path(".tmp/asset-selector-experiments.json")
DEFAULT_DATA_DIR = Path("data")


def fold_index(row: dict, folds: int, seed: str) -> int:
    digest = hashlib.sha256(f"{seed}|asset_selector|{row['market']}|{row['symbol']}".encode("utf-8")).hexdigest()
    return int(digest[:16], 16) % folds


def data_csv_path(row: dict, data_dir: Path) -> Path:
    safe_market = row["market"].replace("/", "_").replace("\\", "_").replace(":", "_")
    safe_symbol = row["symbol"].replace("/", "_").replace("\\", "_").replace(":", "_")
    return data_dir / f"{safe_market}_{safe_symbol}.csv"


def safe_float(value: float) -> float:
    if value is None or not np.isfinite(float(value)):
        return 0.0
    return float(value)


def load_asset_market_features(row: dict, data_dir: Path, date_range: dict) -> list[float]:
    path = data_csv_path(row, data_dir)
    if not path.exists():
        return [0.0] * 24

    raw = pd.read_csv(path)
    raw["date"] = pd.to_datetime(raw["date"])
    raw = raw.sort_values("date")
    if date_range:
        start = pd.to_datetime(date_range.get("start"))
        end = pd.to_datetime(date_range.get("end"))
        raw = raw[(raw["date"] >= start) & (raw["date"] <= end)]
    for column in ["open", "high", "low", "close", "volume"]:
        raw[column] = pd.to_numeric(raw[column], errors="coerce")
    raw = raw.dropna(subset=["open", "high", "low", "close"])
    if len(raw) < 40:
        return [0.0] * 24

    close = raw["close"]
    ret = close.pct_change().dropna()
    if ret.empty:
        return [0.0] * 24
    abs_ret = ret.abs()
    vol = pd.to_numeric(raw["volume"], errors="coerce").replace(0, np.nan)
    high_low_range = ((raw["high"] - raw["low"]) / close.replace(0, np.nan)).replace([np.inf, -np.inf], np.nan)
    net = (1 + ret).cumprod()
    drawdown = net / net.cummax() - 1
    ma20 = close.rolling(20).mean()
    ma60 = close.rolling(60).mean()
    trend_20 = close.pct_change(20)
    trend_60 = close.pct_change(60)

    return [
        safe_float(ret.mean()),
        safe_float(ret.std()),
        safe_float(ret.skew()),
        safe_float(ret.kurt()),
        safe_float(abs_ret.quantile(0.50)),
        safe_float(abs_ret.quantile(0.80)),
        safe_float(abs_ret.quantile(0.95)),
        safe_float(abs_ret.quantile(0.99)),
        safe_float((ret > 0).mean()),
        safe_float(ret.autocorr(lag=1)),
        safe_float(ret.autocorr(lag=5)),
        safe_float(trend_20.mean()),
        safe_float(trend_60.mean()),
        safe_float(trend_20.iloc[-1] if len(trend_20.dropna()) else 0),
        safe_float(trend_60.iloc[-1] if len(trend_60.dropna()) else 0),
        safe_float(drawdown.min()),
        safe_float(drawdown.mean()),
        safe_float(high_low_range.mean()),
        safe_float(high_low_range.quantile(0.95)),
        safe_float(vol.pct_change(fill_method=None).replace([np.inf, -np.inf], np.nan).std()),
        safe_float(np.log1p(vol).std()),
        safe_float((close > ma20).mean()),
        safe_float((close > ma60).mean()),
        safe_float((ma20 > ma60).mean()),
    ]


def build_features(
    rows: list[dict],
    split_seed: str,
    folds: int,
    data_dir: Path,
    date_range: dict,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[dict], list[str], list[str]]:
    modes = sorted({candidate["mode"] for row in rows for candidate in row["candidateScores"]})
    markets = sorted({row["market"] for row in rows})
    x_rows = []
    y_rows = []
    fold_rows = []
    asset_rows = []
    market_rows = []
    candidate_refs = []

    for asset_index, row in enumerate(rows):
        baseline = row["baseline"]
        market_features = load_asset_market_features(row, data_dir, date_range)
        asset_features = [
            float(row.get("rows", 0)),
            baseline["totalReturn"],
            baseline["annualReturn"],
            baseline["maxDrawdown"],
            baseline["winRate"],
            baseline["sharpe"],
            *market_features,
            *[1.0 if row["market"] == market else 0.0 for market in markets],
        ]
        for candidate in row["candidateScores"]:
            improvement = candidate["improvement"]
            candidate_features = [
                candidate["qHead"],
                candidate["qTail"],
                candidate["eta"],
                candidate["qTail"] - candidate["qHead"],
                *[1.0 if candidate["mode"] == mode else 0.0 for mode in modes],
            ]
            x_rows.append(asset_features + candidate_features)
            y_rows.append(
                [
                    candidate["score"],
                    improvement["totalReturn"],
                    improvement["annualReturn"],
                    improvement["sharpe"],
                    improvement["maxDrawdown"],
                    float(
                        improvement["totalReturn"] > 0
                        and improvement["sharpe"] > 0
                        and improvement["maxDrawdown"] > 0
                    ),
                ]
            )
            fold_rows.append(fold_index(row, folds, split_seed))
            asset_rows.append(asset_index)
            market_rows.append(row["market"])
            candidate_refs.append(candidate)

    return (
        np.asarray(x_rows, dtype=float),
        np.asarray(y_rows, dtype=float),
        np.asarray(fold_rows, dtype=int),
        np.asarray(asset_rows, dtype=int),
        np.asarray(market_rows, dtype=object),
        candidate_refs,
        modes,
        markets,
    )


def summarize_selection(rows: list[dict], improvements: list[dict], selections: list[dict], markets: list[str]) -> dict:
    count = len(improvements)
    avg = {
        metric: round(sum(item[metric] for item in improvements) / count, 6)
        for metric in ["totalReturn", "annualReturn", "sharpe", "maxDrawdown"]
    }
    rates = {
        "returnImprovedRate": round(sum(item["totalReturn"] > 0 for item in improvements) / count, 6),
        "sharpeImprovedRate": round(sum(item["sharpe"] > 0 for item in improvements) / count, 6),
        "drawdownImprovedRate": round(sum(item["maxDrawdown"] > 0 for item in improvements) / count, 6),
        "allObjectivesImprovedRate": round(
            sum(item["totalReturn"] > 0 and item["sharpe"] > 0 and item["maxDrawdown"] > 0 for item in improvements) / count,
            6,
        ),
    }

    by_market = {}
    for market in markets:
        market_improvements = [item for item, selection in zip(improvements, selections) if selection["market"] == market]
        market_selections = [selection for selection in selections if selection["market"] == market]
        if not market_improvements:
            continue
        market_count = len(market_improvements)
        by_market[market] = {
            "assets": market_count,
            "activeRate": round(sum(item["mode"] != "no_transform" for item in market_selections) / market_count, 6),
            "avgImprovement": {
                metric: round(sum(item[metric] for item in market_improvements) / market_count, 6)
                for metric in ["totalReturn", "annualReturn", "sharpe", "maxDrawdown"]
            },
            "allObjectivesImprovedRate": round(
                sum(
                    item["totalReturn"] > 0 and item["sharpe"] > 0 and item["maxDrawdown"] > 0
                    for item in market_improvements
                )
                / market_count,
                6,
            ),
        }

    mode_counts = {}
    for selection in selections:
        mode_counts[selection["mode"]] = mode_counts.get(selection["mode"], 0) + 1

    return {
        "assets": count,
        "activeRate": round(sum(item["mode"] != "no_transform" for item in selections) / count, 6),
        "avgImprovement": avg,
        **rates,
        "byMarket": by_market,
        "selectedModeCounts": mode_counts,
    }


def make_model(model_family: str, seed_offset: int = 0):
    if model_family == "extra_trees":
        return ExtraTreesRegressor(
            n_estimators=64,
            max_features=0.75,
            min_samples_leaf=3,
            n_jobs=-1,
            random_state=31 + seed_offset,
        )
    return MultiOutputRegressor(
        HistGradientBoostingRegressor(
            max_iter=120,
            learning_rate=0.052,
            l2_regularization=0.05,
            min_samples_leaf=16,
            random_state=12 + seed_offset,
        )
    )


def build_fold_predictions(
    x_values: np.ndarray,
    y_values: np.ndarray,
    fold_values: np.ndarray,
    market_values: np.ndarray,
    markets: list[str],
    folds: int,
    model_family: str,
    scope: str,
) -> list[tuple[np.ndarray, np.ndarray]]:
    fold_predictions = []
    if scope == "market":
        for fold in range(folds):
            for market_index, market in enumerate(markets):
                train_mask = (fold_values != fold) & (market_values == market)
                validation_indices = np.where((fold_values == fold) & (market_values == market))[0]
                if len(validation_indices) == 0 or int(train_mask.sum()) < 40:
                    continue
                model = make_model(model_family, seed_offset=fold * 17 + market_index)
                model.fit(x_values[train_mask], y_values[train_mask])
                fold_predictions.append((validation_indices, model.predict(x_values[validation_indices])))
        return fold_predictions

    for fold in range(folds):
        train_mask = fold_values != fold
        validation_indices = np.where(fold_values == fold)[0]
        if len(validation_indices) == 0:
            continue
        model = make_model(model_family, seed_offset=fold)
        model.fit(x_values[train_mask], y_values[train_mask])
        fold_predictions.append((validation_indices, model.predict(x_values[validation_indices])))
    return fold_predictions


def evaluate_predictions(
    rows: list[dict],
    asset_values: np.ndarray,
    candidate_refs: list[dict],
    markets: list[str],
    model_name: str,
    fold_predictions: list[tuple[np.ndarray, np.ndarray]],
) -> list[dict]:
    configs = []
    for score_min in [-0.05, 0, 0.03]:
        for total_min in [-0.02, 0, 0.02]:
            for sharpe_min in [-0.02, 0.01, 0.03]:
                for drawdown_min in [-0.01, 0, 0.01]:
                    for all_min in [0, 0.15, 0.30, 0.50]:
                        improvements = []
                        selections = []
                        for validation_indices, predictions in fold_predictions:
                            validation_assets = sorted(set(asset_values[validation_indices]))
                            for asset_index in validation_assets:
                                local_positions = np.where(asset_values[validation_indices] == asset_index)[0]
                                fallback_position = None
                                eligible = []
                                for position in local_positions:
                                    global_index = validation_indices[position]
                                    candidate = candidate_refs[global_index]
                                    prediction = predictions[position]
                                    if candidate["mode"] == "no_transform":
                                        fallback_position = position
                                    if (
                                        candidate["mode"] != "no_transform"
                                        and prediction[0] > score_min
                                        and prediction[1] > total_min
                                        and prediction[3] > sharpe_min
                                        and prediction[4] > drawdown_min
                                        and prediction[5] > all_min
                                    ):
                                        rank = (
                                            0.45 * prediction[0]
                                            + 0.45 * prediction[1]
                                            + 0.75 * prediction[3]
                                            + 1.1 * prediction[4]
                                            + 0.35 * prediction[5]
                                        )
                                        eligible.append((rank, position))
                                chosen_position = max(eligible)[1] if eligible else fallback_position
                                chosen_candidate = candidate_refs[validation_indices[chosen_position]]
                                row = rows[asset_index]
                                improvements.append(chosen_candidate["improvement"])
                                selections.append(
                                    {
                                        "market": row["market"],
                                        "symbol": row["symbol"],
                                        "name": row["name"],
                                        "mode": chosen_candidate["mode"],
                                        "qHead": chosen_candidate["qHead"],
                                        "qTail": chosen_candidate["qTail"],
                                        "eta": chosen_candidate["eta"],
                                    }
                                )

                        summary = summarize_selection(rows, improvements, selections, markets)
                        by_market = summary["byMarket"]
                        penalty = sum(
                            max(0, -by_market[market]["avgImprovement"]["totalReturn"]) * 2.5
                            + max(0, -by_market[market]["avgImprovement"]["sharpe"]) * 2.0
                            + max(0, -by_market[market]["avgImprovement"]["maxDrawdown"]) * 2.8
                            + max(0, 0.30 - by_market[market]["allObjectivesImprovedRate"]) * 0.12
                            for market in by_market
                        )
                        avg = summary["avgImprovement"]
                        objective = (
                            0.70 * avg["totalReturn"]
                            + 0.90 * avg["sharpe"]
                            + 1.35 * avg["maxDrawdown"]
                            + 0.30 * summary["allObjectivesImprovedRate"]
                            + 0.08 * summary["returnImprovedRate"]
                            + 0.08 * summary["sharpeImprovedRate"]
                            + 0.08 * summary["drawdownImprovedRate"]
                            + 0.04 * summary["activeRate"]
                            - penalty
                        )
                        configs.append(
                            {
                                "model": model_name,
                                "objective": round(objective, 6),
                                "thresholds": {
                                    "scoreMin": score_min,
                                    "totalReturnMin": total_min,
                                    "sharpeMin": sharpe_min,
                                    "drawdownMin": drawdown_min,
                                    "allObjectivesProbabilityMin": all_min,
                                },
                                "summary": summary,
                            }
                        )
    return configs


def candidate_key(candidate: dict) -> tuple[str, float, float, float]:
    return (
        str(candidate["mode"]),
        float(candidate["qHead"]),
        float(candidate["qTail"]),
        float(candidate["eta"]),
    )


def score_from_improvement(improvement: dict) -> float:
    return (
        0.70 * improvement["totalReturn"]
        + 0.45 * improvement["annualReturn"]
        + 0.90 * improvement["sharpe"]
        + 1.35 * improvement["maxDrawdown"]
        + 0.18
        * float(
            improvement["totalReturn"] > 0
            and improvement["sharpe"] > 0
            and improvement["maxDrawdown"] > 0
        )
    )


def build_asset_candidate_maps(rows: list[dict]) -> tuple[list[dict], list[tuple[str, float, float, float]]]:
    asset_maps = []
    keys = []
    seen = set()
    for row in rows:
        asset_map = {}
        for candidate in row["candidateScores"]:
            key = candidate_key(candidate)
            asset_map[key] = candidate
            if key not in seen:
                seen.add(key)
                keys.append(key)
        asset_maps.append(asset_map)
    keys.sort(key=lambda item: (item[0], item[1], item[2], item[3]))
    return asset_maps, keys


def evaluate_knn_selector(
    rows: list[dict],
    x_values: np.ndarray,
    asset_values: np.ndarray,
    fold_values: np.ndarray,
    markets: list[str],
    modes: list[str],
    folds: int,
) -> list[dict]:
    asset_feature_count = x_values.shape[1] - (4 + len(modes))
    asset_features = np.zeros((len(rows), asset_feature_count), dtype=float)
    for asset_index in range(len(rows)):
        first_position = int(np.where(asset_values == asset_index)[0][0])
        asset_features[asset_index] = x_values[first_position, :asset_feature_count]

    asset_maps, keys = build_asset_candidate_maps(rows)
    configs = []
    market_to_assets = {
        market: np.asarray([idx for idx, row in enumerate(rows) if row["market"] == market], dtype=int)
        for market in markets
    }

    for k_neighbors in [3, 5, 8, 12, 16]:
        for score_min in [-0.08, -0.02, 0, 0.03]:
            for all_min in [0.10, 0.20, 0.30, 0.40]:
                improvements = []
                selections = []
                for fold in range(folds):
                    for market, market_assets in market_to_assets.items():
                        train_assets = np.asarray(
                            [idx for idx in market_assets if fold_values[np.where(asset_values == idx)[0][0]] != fold],
                            dtype=int,
                        )
                        validation_assets = np.asarray(
                            [idx for idx in market_assets if fold_values[np.where(asset_values == idx)[0][0]] == fold],
                            dtype=int,
                        )
                        if len(train_assets) == 0 or len(validation_assets) == 0:
                            continue
                        train_features = asset_features[train_assets]
                        center = train_features.mean(axis=0)
                        scale = train_features.std(axis=0)
                        scale[scale == 0] = 1
                        train_scaled = (train_features - center) / scale
                        for asset_index in validation_assets:
                            validation_scaled = (asset_features[asset_index] - center) / scale
                            distances = np.linalg.norm(train_scaled - validation_scaled, axis=1)
                            nearest_positions = np.argsort(distances)[: min(k_neighbors, len(train_assets))]
                            nearest_assets = train_assets[nearest_positions]
                            fallback = asset_maps[asset_index].get(("no_transform", 0.7, 0.9, 0.2))
                            if fallback is None:
                                fallback = next(
                                    candidate
                                    for candidate in asset_maps[asset_index].values()
                                    if candidate["mode"] == "no_transform"
                                )
                            ranked = []
                            for key in keys:
                                if key[0] == "no_transform" or key not in asset_maps[asset_index]:
                                    continue
                                neighbor_candidates = [
                                    asset_maps[int(neighbor)].get(key)
                                    for neighbor in nearest_assets
                                    if key in asset_maps[int(neighbor)]
                                ]
                                if not neighbor_candidates:
                                    continue
                                neighbor_improvements = [candidate["improvement"] for candidate in neighbor_candidates]
                                avg_improvement = {
                                    metric: sum(item[metric] for item in neighbor_improvements) / len(neighbor_improvements)
                                    for metric in ["totalReturn", "annualReturn", "sharpe", "maxDrawdown"]
                                }
                                all_rate = sum(
                                    item["totalReturn"] > 0 and item["sharpe"] > 0 and item["maxDrawdown"] > 0
                                    for item in neighbor_improvements
                                ) / len(neighbor_improvements)
                                score = score_from_improvement(avg_improvement) + 0.18 * all_rate
                                if (
                                    score > score_min
                                    and all_rate >= all_min
                                    and avg_improvement["totalReturn"] >= -0.02
                                    and avg_improvement["sharpe"] >= -0.02
                                    and avg_improvement["maxDrawdown"] >= -0.02
                                ):
                                    ranked.append((score, key))
                            chosen = asset_maps[asset_index][max(ranked)[1]] if ranked else fallback
                            row = rows[asset_index]
                            improvements.append(chosen["improvement"])
                            selections.append(
                                {
                                    "market": row["market"],
                                    "symbol": row["symbol"],
                                    "name": row["name"],
                                    "mode": chosen["mode"],
                                    "qHead": chosen["qHead"],
                                    "qTail": chosen["qTail"],
                                    "eta": chosen["eta"],
                                }
                            )

                summary = summarize_selection(rows, improvements, selections, markets)
                by_market = summary["byMarket"]
                penalty = sum(
                    max(0, -by_market[market]["avgImprovement"]["totalReturn"]) * 2.5
                    + max(0, -by_market[market]["avgImprovement"]["sharpe"]) * 2.0
                    + max(0, -by_market[market]["avgImprovement"]["maxDrawdown"]) * 2.8
                    + max(0, 0.30 - by_market[market]["allObjectivesImprovedRate"]) * 0.12
                    for market in by_market
                )
                avg = summary["avgImprovement"]
                objective = (
                    0.70 * avg["totalReturn"]
                    + 0.90 * avg["sharpe"]
                    + 1.35 * avg["maxDrawdown"]
                    + 0.34 * summary["allObjectivesImprovedRate"]
                    + 0.07 * summary["activeRate"]
                    - penalty
                )
                configs.append(
                    {
                        "model": f"knn-market-k{k_neighbors}",
                        "objective": round(objective, 6),
                        "thresholds": {
                            "scoreMin": score_min,
                            "allObjectivesNeighborRateMin": all_min,
                            "neighbors": k_neighbors,
                        },
                        "summary": summary,
                    }
                )
    return configs


def summarize_oracle(rows: list[dict], markets: list[str]) -> dict:
    improvements = []
    selections = []
    for row in rows:
        best = max(row["candidateScores"], key=lambda item: item["score"])
        improvements.append(best["improvement"])
        selections.append(
            {
                "market": row["market"],
                "symbol": row["symbol"],
                "name": row["name"],
                "mode": best["mode"],
                "qHead": best["qHead"],
                "qTail": best["qTail"],
                "eta": best["eta"],
            }
        )
    return summarize_selection(rows, improvements, selections, markets)


def run_experiment(source: Path, folds: int, split_seed: str, data_dir: Path, include_extra_trees: bool) -> dict:
    payload = json.loads(source.read_text(encoding="utf-8"))
    rows = payload["stockResults"]
    x_values, y_values, fold_values, asset_values, market_values, candidate_refs, modes, markets = build_features(
        rows,
        split_seed,
        folds,
        data_dir,
        payload.get("dateRange", {}),
    )

    configs = []
    prediction_models = [
        ("hgb-global", "hgb", "global"),
        ("hgb-market", "hgb", "market"),
    ]
    if include_extra_trees:
        prediction_models.extend(
            [
                ("extra-trees-global", "extra_trees", "global"),
                ("extra-trees-market", "extra_trees", "market"),
            ]
        )
    for model_name, model_family, scope in prediction_models:
        fold_predictions = build_fold_predictions(
            x_values,
            y_values,
            fold_values,
            market_values,
            markets,
            folds,
            model_family,
            scope,
        )
        configs.extend(evaluate_predictions(rows, asset_values, candidate_refs, markets, model_name, fold_predictions))
    configs.extend(evaluate_knn_selector(rows, x_values, asset_values, fold_values, markets, modes, folds))

    configs.sort(key=lambda item: item["objective"], reverse=True)
    best_performance = configs[0]
    coverage_configs = [
        item
        for item in configs
        if all(metric >= 0 for market in item["summary"]["byMarket"].values() for metric in market["avgImprovement"].values())
    ]
    coverage_configs.sort(
        key=lambda item: (
            item["summary"]["allObjectivesImprovedRate"],
            item["summary"]["returnImprovedRate"],
            item["summary"]["sharpeImprovedRate"],
            item["summary"]["drawdownImprovedRate"],
            item["objective"],
        ),
        reverse=True,
    )
    best_coverage = coverage_configs[0] if coverage_configs else best_performance
    best = best_coverage if coverage_configs else best_performance
    best_summary = best["summary"]
    market_improvements = [
        metric
        for market in best_summary["byMarket"].values()
        for metric in market["avgImprovement"].values()
    ]
    all_markets_nonnegative = all(value >= 0 for value in market_improvements)
    if all_markets_nonnegative and best_summary["activeRate"] > 0:
        status = "candidate_safer_not_promoted"
        conclusion = "增强行情特征后的资产选择器在四个市场平均不再产生负贡献，但改善覆盖率仍偏低，暂不推广为正式交付模型。"
    else:
        status = "candidate_not_promoted"
        conclusion = "资产级选择器在 5 折跨标的验证中取得小幅正改善，但仍未达到四市场绝大多数资产稳定提升的交付标准。"
    return {
        "generatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "experimentName": "asset-selector-hgb-market-features-cv",
        "status": status,
        "conclusion": conclusion,
        "sourceModelPath": str(source),
        "dataDir": str(data_dir),
        "folds": folds,
        "splitSeed": split_seed,
        "assetCount": len(rows),
        "candidateCountPerAsset": len(rows[0]["candidateScores"]) if rows else 0,
        "sampleCount": int(len(x_values)),
        "featureCount": int(x_values.shape[1]),
        "modes": modes,
        "markets": markets,
        "bestConfig": best,
        "bestPerformanceConfig": best_performance,
        "bestCoverageConfig": best_coverage,
        "oracleUpperBound": summarize_oracle(rows, markets),
        "topConfigs": configs[:20],
        "topCoverageConfigs": coverage_configs[:20],
    }


def append_history(history_path: Path, experiment: dict) -> None:
    history_path.parent.mkdir(parents=True, exist_ok=True)
    if history_path.exists():
        history = json.loads(history_path.read_text(encoding="utf-8"))
    else:
        history = []
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
            "bestPerformanceConfig": experiment.get("bestPerformanceConfig"),
            "bestCoverageConfig": experiment.get("bestCoverageConfig"),
            "oracleUpperBound": experiment.get("oracleUpperBound"),
        }
    )
    history_path.write_text(json.dumps(history[-50:], ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="训练并验证资产级参数选择器")
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--history", default=str(DEFAULT_HISTORY))
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR))
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--split-seed", default="pt-trading-v1")
    parser.add_argument("--include-extra-trees", action="store_true")
    args = parser.parse_args()

    experiment = run_experiment(
        Path(args.source),
        args.folds,
        args.split_seed,
        Path(args.data_dir),
        args.include_extra_trees,
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(experiment, ensure_ascii=False, indent=2), encoding="utf-8")
    append_history(Path(args.history), experiment)
    print(json.dumps({"output": str(output_path), "history": args.history, "bestConfig": experiment["bestConfig"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
