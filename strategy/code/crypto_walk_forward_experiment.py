import argparse
import json
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesRegressor

from classic_strategy import compute_classic_strategy
from model_training import format_improvement, format_metrics, score_candidate
from pt_strategy import compute_pt_strategy


DEFAULT_SOURCE = Path(".tmp/time-split-crypto-pool-latest.json")
DEFAULT_OUTPUT = Path(".tmp/crypto-walk-forward-latest.json")
DEFAULT_HISTORY = Path(".tmp/asset-selector-experiments.json")
DEFAULT_DATA_DIR = Path("data")
MODE_ORDER = [
    "tail_denoise",
    "pt_amplify",
    "trend_smooth",
    "vol_squeeze",
    "downside_guard",
    "momentum_regime",
    "crypto_trend_guard",
]


def safe_float(value) -> float:
    try:
        value = float(value)
    except Exception:
        return 0.0
    return value if np.isfinite(value) else 0.0


def data_csv_path(row: dict, data_dir: Path) -> Path:
    safe_market = row["market"].replace("/", "_").replace("\\", "_").replace(":", "_")
    safe_symbol = row["symbol"].replace("/", "_").replace("\\", "_").replace(":", "_")
    return data_dir / f"{safe_market}_{safe_symbol}.csv"


def candidate_key(candidate: dict) -> tuple[str, float, float, float]:
    return (
        str(candidate["mode"]),
        float(candidate["qHead"]),
        float(candidate["qTail"]),
        float(candidate["eta"]),
    )


def load_local_data(row: dict, data_dir: Path) -> pd.DataFrame:
    df = pd.read_csv(data_csv_path(row, data_dir), parse_dates=["date"])
    df = df.sort_values("date").set_index("date")
    for column in ["open", "high", "low", "close", "volume", "daily_ret"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    df["daily_ret"] = df["close"].pct_change().fillna(0)
    return df.dropna(subset=["open", "high", "low", "close", "volume", "daily_ret"])


def load_market_context(rows: list[dict], data_dir: Path) -> pd.DataFrame:
    close_map = {}
    for row in rows:
        path = data_csv_path(row, data_dir)
        if not path.exists():
            continue
        df = pd.read_csv(path, parse_dates=["date"])
        df = df.sort_values("date").set_index("date")
        close_map[row["symbol"]] = pd.to_numeric(df["close"], errors="coerce")
    if not close_map:
        return pd.DataFrame()
    close_df = pd.DataFrame(close_map).sort_index()
    ret_df = close_df.pct_change(fill_method=None).replace([np.inf, -np.inf], np.nan)
    context = pd.DataFrame(index=close_df.index)
    context["market_ret"] = ret_df.mean(axis=1)
    context["market_vol"] = ret_df.std(axis=1)
    context["breadth"] = (ret_df > 0).mean(axis=1)
    context["tail_risk"] = ret_df.quantile(0.10, axis=1)
    for symbol in ["BTC-USD", "ETH-USD"]:
        if symbol in ret_df:
            context[f"{symbol.split('-')[0].lower()}_ret"] = ret_df[symbol]
        else:
            context[f"{symbol.split('-')[0].lower()}_ret"] = 0
    context = context.replace([np.inf, -np.inf], np.nan).fillna(0)
    return context


def market_features(df: pd.DataFrame) -> list[float]:
    close = pd.to_numeric(df["close"], errors="coerce")
    ret = close.pct_change().dropna()
    volume = pd.to_numeric(df["volume"], errors="coerce").replace(0, np.nan)
    if len(ret) < 30:
        return [0.0] * 26
    net = (1 + ret).cumprod()
    drawdown = net / net.cummax() - 1
    high_low = ((df["high"] - df["low"]) / close.replace(0, np.nan)).replace([np.inf, -np.inf], np.nan)
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
    for window in [20, 60, 120]:
        tail = ret.tail(window)
        features.extend(
            [
                safe_float(close.pct_change(window).iloc[-1]),
                safe_float(tail.std()),
                safe_float(tail.mean()),
                safe_float((tail > 0).mean()),
            ]
        )
    return features


def context_features(context_df: pd.DataFrame, start, end) -> list[float]:
    if context_df.empty:
        return [0.0] * 30
    segment = context_df[(context_df.index >= start) & (context_df.index <= end)].copy()
    if len(segment) < 30:
        return [0.0] * 30
    features = []
    for column in ["market_ret", "market_vol", "breadth", "tail_risk", "btc_ret", "eth_ret"]:
        series = pd.to_numeric(segment[column], errors="coerce").dropna()
        if series.empty:
            features.extend([0.0] * 5)
            continue
        features.extend(
            [
                safe_float(series.mean()),
                safe_float(series.std()),
                safe_float(series.tail(20).mean()),
                safe_float(series.tail(60).mean()),
                safe_float(series.iloc[-1]),
            ]
        )
    return features


def candidate_features(candidate: dict, window: dict) -> list[float]:
    train_imp = candidate["trainImprovement"]
    stability_imp = candidate["stabilityImprovement"]
    return [
        safe_float(candidate["qHead"]),
        safe_float(candidate["qTail"]),
        safe_float(candidate["eta"]),
        safe_float(candidate["qTail"] - candidate["qHead"]),
        safe_float(candidate["trainScore"]),
        safe_float(candidate["stabilityScore"]),
        safe_float(candidate["trainScore"] - candidate["stabilityScore"]),
        safe_float(train_imp["totalReturn"]),
        safe_float(train_imp["annualReturn"]),
        safe_float(train_imp["sharpe"]),
        safe_float(train_imp["maxDrawdown"]),
        safe_float(stability_imp["totalReturn"]),
        safe_float(stability_imp["annualReturn"]),
        safe_float(stability_imp["sharpe"]),
        safe_float(stability_imp["maxDrawdown"]),
        *[1.0 if candidate["mode"] == mode else 0.0 for mode in MODE_ORDER],
        *window["preFeatures"],
        *window.get("contextFeatures", [0.0] * 30),
    ]


def target_values(candidate: dict) -> list[float]:
    improvement = candidate["validationImprovement"]
    all_objectives = float(
        improvement["totalReturn"] > 0 and improvement["sharpe"] > 0 and improvement["maxDrawdown"] > 0
    )
    return [
        safe_float(candidate["validationScore"]),
        safe_float(improvement["totalReturn"]),
        safe_float(improvement["annualReturn"]),
        safe_float(improvement["sharpe"]),
        safe_float(improvement["maxDrawdown"]),
        all_objectives,
    ]


def evaluate_candidate(params: dict, select_df: pd.DataFrame, stability_df: pd.DataFrame, train_df: pd.DataFrame, validation_df: pd.DataFrame, baselines: dict) -> dict:
    train_metrics = compute_pt_strategy(train_df, q_head=params["qHead"], q_tail=params["qTail"], eta_param=params["eta"], mode=params["mode"])["metrics"]
    stability_metrics = compute_pt_strategy(stability_df, q_head=params["qHead"], q_tail=params["qTail"], eta_param=params["eta"], mode=params["mode"])["metrics"]
    validation_metrics = compute_pt_strategy(validation_df, q_head=params["qHead"], q_tail=params["qTail"], eta_param=params["eta"], mode=params["mode"])["metrics"]
    select_metrics = compute_pt_strategy(select_df, q_head=params["qHead"], q_tail=params["qTail"], eta_param=params["eta"], mode=params["mode"])["metrics"]
    return {
        "mode": params["mode"],
        "qHead": params["qHead"],
        "qTail": params["qTail"],
        "eta": params["eta"],
        "trainMetrics": format_metrics(train_metrics),
        "trainImprovement": format_improvement(baselines["train"], train_metrics),
        "trainScore": score_candidate(baselines["train"], train_metrics),
        "selectMetrics": format_metrics(select_metrics),
        "selectImprovement": format_improvement(baselines["select"], select_metrics),
        "selectScore": score_candidate(baselines["select"], select_metrics),
        "stabilityMetrics": format_metrics(stability_metrics),
        "stabilityImprovement": format_improvement(baselines["stability"], stability_metrics),
        "stabilityScore": score_candidate(baselines["stability"], stability_metrics),
        "validationMetrics": format_metrics(validation_metrics),
        "validationImprovement": format_improvement(baselines["validation"], validation_metrics),
        "validationScore": score_candidate(baselines["validation"], validation_metrics),
    }


def unique_candidate_params(row: dict, limit: int) -> list[dict]:
    seen = set()
    params = []
    for candidate in row.get("candidatePool", []):
        key = candidate_key(candidate)
        if candidate["mode"] == "no_transform" or key in seen:
            continue
        seen.add(key)
        params.append({"mode": key[0], "qHead": key[1], "qTail": key[2], "eta": key[3]})
    return params[:limit]


def evaluate_asset(args: tuple[dict, Path, pd.DataFrame, int, int, int, int]) -> dict:
    row, data_dir, market_context, train_len, validation_len, step, candidate_limit = args
    df = load_local_data(row, data_dir)
    params_list = unique_candidate_params(row, candidate_limit)
    max_start = len(df) - train_len - validation_len
    if max_start < 0 or not params_list:
        raise RuntimeError(f"{row['symbol']} 样本不足或候选为空")
    starts = list(range(0, max_start + 1, step))
    windows = []
    for window_index, start in enumerate(starts):
        train_df = df.iloc[start : start + train_len].copy()
        validation_df = df.iloc[start + train_len : start + train_len + validation_len].copy()
        stability_cut = min(max(60, int(len(train_df) * 0.7)), len(train_df) - 40)
        select_df = train_df.iloc[:stability_cut].copy()
        stability_df = train_df.iloc[stability_cut:].copy()
        baselines = {
            "select": compute_classic_strategy(select_df)["metrics"],
            "stability": compute_classic_strategy(stability_df)["metrics"],
            "train": compute_classic_strategy(train_df)["metrics"],
            "validation": compute_classic_strategy(validation_df)["metrics"],
        }
        candidates = [
            evaluate_candidate(params, select_df, stability_df, train_df, validation_df, baselines)
            for params in params_list
        ]
        windows.append(
            {
                "windowIndex": window_index,
                "start": train_df.index[0].strftime("%Y-%m-%d"),
                "trainEnd": train_df.index[-1].strftime("%Y-%m-%d"),
                "validationEnd": validation_df.index[-1].strftime("%Y-%m-%d"),
                "preFeatures": market_features(train_df),
                "contextFeatures": context_features(market_context, train_df.index[0], train_df.index[-1]),
                "fallbackImprovement": {"totalReturn": 0, "annualReturn": 0, "sharpe": 0, "maxDrawdown": 0},
                "candidatePool": candidates,
                "oracle": max(candidates, key=lambda item: item["validationScore"]),
            }
        )
    return {"market": row["market"], "symbol": row["symbol"], "name": row["name"], "windows": windows}


def summarize(chosen_rows: list[dict]) -> dict:
    improvements = [item["chosen"]["validationImprovement"] for item in chosen_rows]
    count = len(improvements)
    return {
        "assets": count,
        "activeRate": round(sum(item["chosen"]["mode"] != "no_transform" for item in chosen_rows) / count, 6),
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
        "byMarket": {
            "加密货币": {
                "assets": count,
                "activeRate": round(sum(item["chosen"]["mode"] != "no_transform" for item in chosen_rows) / count, 6),
                "avgImprovement": {
                    metric: round(sum(item[metric] for item in improvements) / count, 6)
                    for metric in ["totalReturn", "annualReturn", "sharpe", "maxDrawdown"]
                },
                "allObjectivesImprovedRate": round(
                    sum(item["totalReturn"] > 0 and item["sharpe"] > 0 and item["maxDrawdown"] > 0 for item in improvements) / count,
                    6,
                ),
            }
        },
    }


def evaluate_selector(asset_results: list[dict]) -> tuple[dict, list[dict], dict]:
    train_samples = []
    validation_groups = []
    for asset in asset_results:
        windows = asset["windows"]
        if len(windows) < 2:
            continue
        for window in windows[:-1]:
            for candidate in window["candidatePool"]:
                train_samples.append((candidate_features(candidate, window), target_values(candidate)))
        latest = windows[-1]
        validation_groups.append({"asset": asset, "window": latest})

    x_train = np.asarray([item[0] for item in train_samples], dtype=float)
    y_train = np.asarray([item[1] for item in train_samples], dtype=float)
    model = ExtraTreesRegressor(n_estimators=220, min_samples_leaf=3, max_features=0.75, random_state=202, n_jobs=-1)
    model.fit(x_train, y_train)

    configs = []
    for score_min in [-0.2, -0.1, 0, 0.05, 0.1]:
        for return_min in [-0.05, -0.01, 0, 0.03]:
            for sharpe_min in [-0.05, -0.01, 0, 0.03]:
                for drawdown_min in [-0.03, -0.005, 0, 0.02]:
                    chosen_rows = []
                    for group in validation_groups:
                        window = group["window"]
                        x_values = np.asarray([candidate_features(candidate, window) for candidate in window["candidatePool"]], dtype=float)
                        predictions = model.predict(x_values)
                        eligible = []
                        for candidate, prediction in zip(window["candidatePool"], predictions):
                            if (
                                prediction[0] >= score_min
                                and prediction[1] >= return_min
                                and prediction[3] >= sharpe_min
                                and prediction[4] >= drawdown_min
                            ):
                                rank = prediction[0] + prediction[1] + prediction[3] + prediction[4] + 0.35 * prediction[5]
                                eligible.append((rank, candidate))
                        fallback = {
                            "mode": "no_transform",
                            "qHead": 0.7,
                            "qTail": 0.9,
                            "eta": 0.2,
                            "validationImprovement": {"totalReturn": 0, "annualReturn": 0, "sharpe": 0, "maxDrawdown": 0},
                        }
                        chosen = max(eligible, key=lambda item: item[0])[1] if eligible else fallback
                        chosen_rows.append({"asset": group["asset"]["symbol"], "chosen": chosen})
                    summary = summarize(chosen_rows)
                    avg = summary["avgImprovement"]
                    penalty = 3 * max(0, -avg["totalReturn"]) + 2.5 * max(0, -avg["sharpe"]) + 3.2 * max(0, -avg["maxDrawdown"])
                    objective = avg["totalReturn"] + avg["sharpe"] + avg["maxDrawdown"] + 0.75 * summary["allObjectivesImprovedRate"] + 0.04 * summary["activeRate"] - penalty
                    configs.append(
                        {
                            "model": "crypto-walk-forward-extra_trees",
                            "objective": round(objective, 6),
                            "thresholds": {
                                "predictedScoreMin": score_min,
                                "predictedTotalReturnMin": return_min,
                                "predictedSharpeMin": sharpe_min,
                                "predictedDrawdownMin": drawdown_min,
                            },
                            "summary": summary,
                        }
                    )
    configs.sort(
        key=lambda item: (
            all(v >= 0 for v in item["summary"]["avgImprovement"].values()),
            item["summary"]["allObjectivesImprovedRate"],
            item["summary"]["avgImprovement"]["totalReturn"],
            item["summary"]["avgImprovement"]["sharpe"],
            item["objective"],
        ),
        reverse=True,
    )
    oracle_rows = [
        {"asset": asset["symbol"], "chosen": asset["windows"][-1]["oracle"]}
        for asset in asset_results
        if len(asset["windows"]) >= 2
    ]
    return configs[0], configs[:20], summarize(oracle_rows)


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


def run_experiment(args) -> dict:
    source = Path(args.source)
    payload = json.loads(source.read_text(encoding="utf-8"))
    rows = [row for row in payload["stockResults"] if row["market"] == "加密货币"]
    if args.max_assets:
        rows = rows[: args.max_assets]
    market_context = load_market_context(rows, Path(args.data_dir))
    jobs = [(row, Path(args.data_dir), market_context, args.train_len, args.validation_len, args.step, args.candidate_limit) for row in rows]
    results = []
    failures = []
    with ProcessPoolExecutor(max_workers=max(1, args.workers)) as executor:
        future_map = {executor.submit(evaluate_asset, job): job[0] for job in jobs}
        for future in as_completed(future_map):
            row = future_map[future]
            try:
                results.append(future.result())
            except Exception as error:
                failures.append({"symbol": row["symbol"], "name": row["name"], "error": str(error)})
            print(f"[crypto-walk] completed {len(results)+len(failures)}/{len(jobs)} success={len(results)} failed={len(failures)} latest={row['symbol']}", flush=True)
    results.sort(key=lambda item: item["symbol"])
    best, top_configs, oracle = evaluate_selector(results)
    avg = best["summary"]["avgImprovement"]
    safe = all(value >= 0 for value in avg.values())
    return {
        "generatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "experimentName": "crypto-walk-forward-regime-cv",
        "status": "candidate_safer_not_promoted" if safe else "candidate_not_promoted",
        "conclusion": "加密货币滚动窗口状态模型验证期平均不为负，但覆盖率仍需提升。" if safe else "加密货币滚动窗口状态模型仍未稳定转正。",
        "sourceModelPath": str(source),
        "assetCount": len(results),
        "sampleCount": sum(len(asset["windows"]) * len(asset["windows"][0]["candidatePool"]) for asset in results if asset["windows"]),
        "featureCount": len(candidate_features(results[0]["windows"][0]["candidatePool"][0], results[0]["windows"][0])) if results and results[0]["windows"] else 0,
        "windowConfig": {
            "trainLen": args.train_len,
            "validationLen": args.validation_len,
            "step": args.step,
            "candidateLimit": args.candidate_limit,
            "contextFeatures": True,
        },
        "bestConfig": best,
        "topConfigs": top_configs,
        "oracleUpperBound": oracle,
        "assetResults": results,
        "failures": failures,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="加密货币滚动窗口 regime 选择实验")
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--history", default=str(DEFAULT_HISTORY))
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR))
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--max-assets", type=int, default=0)
    parser.add_argument("--train-len", type=int, default=360)
    parser.add_argument("--validation-len", type=int, default=120)
    parser.add_argument("--step", type=int, default=180)
    parser.add_argument("--candidate-limit", type=int, default=14)
    args = parser.parse_args()
    experiment = run_experiment(args)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(experiment, ensure_ascii=False, indent=2), encoding="utf-8")
    append_history(Path(args.history), experiment)
    print(json.dumps({"output": str(output), "bestConfig": experiment["bestConfig"], "oracleUpperBound": experiment["oracleUpperBound"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
