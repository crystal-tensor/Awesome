import pandas as pd

from classic_strategy import build_chart_series, build_strategy, clean_numeric_list
from pt_data_transformer import transform_ohlcv_with_pt_model


def compute_pt_strategy(
    df: pd.DataFrame,
    q_head: float = 0.8,
    q_tail: float = 0.95,
    eta_param: float = 0.5,
    mode: str = "legacy_ot",
) -> dict:
    work_df = transform_ohlcv_with_pt_model(df, q_head=q_head, q_tail=q_tail, eta=eta_param, mode=mode)

    strategy = build_strategy(
        work_df,
        "pt",
        "pt_open",
        "pt_high",
        "pt_low",
        "pt_close",
        "close",
        "daily_ret",
    )

    chart_df = work_df.reset_index()
    chart_df["date"] = chart_df["date"].dt.strftime("%Y-%m-%d")
    return {
        "metrics": strategy["metrics"],
        "series": build_chart_series(chart_df, strategy),
        "net": clean_numeric_list(chart_df["pt_net"], 6),
        "trades": strategy["trades"],
        "summary": {
            "mode": mode,
            "qHead": q_head,
            "qTail": q_tail,
            "eta": eta_param,
            "originMean": round(float(work_df["daily_ret"].mean()), 6),
            "perturbedMean": round(float(work_df["ret_perturbed"].mean()), 6),
        },
        "tailSamples": chart_df[chart_df["bucket"] == "L"][["date", "close", "daily_ret", "vol_20d", "pt_weight"]]
        .head(10)
        .round(6)
        .to_dict(orient="records"),
    }
