import numpy as np
import pandas as pd
from scipy.stats import beta, expon


def generate_pt_sample(n: int, random_state: int = 42) -> np.ndarray:
    """Generate Porter-Thomas-like Exp(1) samples."""
    return expon.rvs(size=n, random_state=random_state)


def pt_rank_weight(return_series: np.ndarray, vol_series: np.ndarray, eta: float = 0.5, random_state: int = 42) -> np.ndarray:
    """Match heavy-tail PT weights to larger return/volatility events."""
    n = len(return_series)
    tau = np.abs(return_series) + vol_series
    pt_y = generate_pt_sample(n, random_state=random_state)
    pt_weight = pt_y / pt_y.sum()

    idx_tau_desc = np.argsort(-tau)
    idx_pt_desc = np.argsort(-pt_weight)

    matched_weight = np.zeros(n)
    matched_weight[idx_tau_desc] = pt_weight[idx_pt_desc]

    uniform_w = np.ones(n) / n
    return (1 - eta) * uniform_w + eta * matched_weight


def pt_ot_perturb(original_ret: np.ndarray, pt_y: np.ndarray) -> np.ndarray:
    """Perturb selected returns with a PT + OT-style heavy-tail map."""
    cdf_pt = expon.cdf(pt_y)
    xi = 0.85 * beta.ppf(cdf_pt, 2, 12) + 0.15 * beta.ppf(cdf_pt, 8, 2)
    return original_ret * (1 + xi * np.sign(original_ret))


def ensure_market_features(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure daily returns, absolute returns, and 20-day volatility exist."""
    work_df = df.copy()
    work_df["daily_ret"] = work_df["close"].pct_change()
    work_df["daily_ret_abs"] = work_df["daily_ret"].abs()
    work_df["vol_20d"] = work_df["daily_ret"].rolling(window=20).std()
    return work_df.dropna()


def split_long_tail_bucket(df: pd.DataFrame, q_head: float = 0.8, q_tail: float = 0.95) -> pd.DataFrame:
    """Bucket returns into head, middle, and long-tail regimes."""
    work_df = df.copy()
    ret_abs = work_df["daily_ret_abs"]
    h_threshold = ret_abs.quantile(q_head)
    l_threshold = ret_abs.quantile(q_tail)

    def label_bucket(value):
        if value <= h_threshold:
            return "H"
        if value <= l_threshold:
            return "M"
        return "L"

    work_df["bucket"] = ret_abs.apply(label_bucket)
    return work_df


def transform_ohlcv_with_pt_model(
    df: pd.DataFrame,
    q_head: float = 0.8,
    q_tail: float = 0.95,
    eta: float = 0.5,
    mode: str = "tail_denoise",
    random_state: int = 42,
) -> pd.DataFrame:
    """Return original data plus PT model OHLCV columns for strategy replay.

    Required input columns: open, high, low, close, volume. The output keeps
    original prices and adds pt_open, pt_high, pt_low, pt_close, ret_perturbed,
    pt_weight, and bucket. A trading institution can run its existing strategy
    against the pt_* price columns without changing strategy logic.
    """
    required = ["open", "high", "low", "close", "volume"]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"缺少行情字段: {', '.join(missing)}")

    work_df = df.copy()
    if not {"daily_ret", "daily_ret_abs", "vol_20d"}.issubset(work_df.columns):
        work_df = ensure_market_features(work_df)
    work_df = split_long_tail_bucket(work_df, q_head=q_head, q_tail=q_tail)

    ret_arr = work_df["daily_ret"].values
    vol_arr = work_df["vol_20d"].values
    n_data = len(ret_arr)

    work_df["pt_weight"] = pt_rank_weight(ret_arr, vol_arr, eta=eta, random_state=random_state)
    pt_y_all = generate_pt_sample(n_data, random_state=random_state)
    work_df["ret_perturbed"] = work_df["daily_ret"].copy()

    mask_ml = work_df["bucket"].isin(["M", "L"])
    pt_mapped_ret = pt_ot_perturb(work_df.loc[mask_ml, "daily_ret"].values, pt_y_all[mask_ml])
    work_df.loc[mask_ml, "ret_pt_raw"] = pt_mapped_ret
    work_df["pt_mode"] = mode

    if mode == "legacy_ot":
        work_df.loc[mask_ml, "ret_perturbed"] = pt_mapped_ret
        work_df["pt_blend"] = mask_ml.astype(float)
    elif mode == "no_transform":
        work_df["ret_perturbed"] = work_df["daily_ret"]
        work_df["pt_blend"] = 0.0
        work_df["pt_open"] = work_df["open"]
        work_df["pt_high"] = work_df["high"]
        work_df["pt_low"] = work_df["low"]
        work_df["pt_close"] = work_df["close"]
        work_df["pt_volume"] = work_df["volume"]
        return work_df
    elif mode == "pt_amplify":
        work_df.loc[mask_ml, "ret_perturbed"] = (
            (1 - eta) * work_df.loc[mask_ml, "daily_ret"] + eta * pt_mapped_ret
        )
        work_df["pt_blend"] = eta * mask_ml.astype(float)
    elif mode == "tail_denoise":
        trend_ret = work_df["daily_ret"].ewm(span=5, adjust=False).mean()
        tail_rank = work_df["pt_weight"].rank(pct=True).fillna(0)
        bucket_strength = work_df["bucket"].map({"H": 0.0, "M": 0.55, "L": 1.0}).astype(float)
        blend = (eta * bucket_strength * (0.5 + 0.5 * tail_rank)).clip(0, 0.95)
        work_df["ret_perturbed"] = (1 - blend) * work_df["daily_ret"] + blend * trend_ret
        work_df["pt_blend"] = blend
    elif mode == "trend_smooth":
        trend_ret = work_df["daily_ret"].ewm(span=8, adjust=False).mean()
        tail_rank = work_df["pt_weight"].rank(pct=True).fillna(0)
        blend = (eta * (0.25 + 0.75 * tail_rank)).clip(0, 0.9)
        work_df["ret_perturbed"] = (1 - blend) * work_df["daily_ret"] + blend * trend_ret
        work_df["pt_blend"] = blend
    elif mode == "vol_squeeze":
        tail_rank = work_df["pt_weight"].rank(pct=True).fillna(0)
        bucket_strength = work_df["bucket"].map({"H": 0.15, "M": 0.6, "L": 1.0}).astype(float)
        squeeze = (eta * 0.75 * bucket_strength * (0.4 + 0.6 * tail_rank)).clip(0, 0.85)
        work_df["ret_perturbed"] = work_df["daily_ret"] * (1 - squeeze)
        work_df["pt_blend"] = squeeze
    elif mode == "downside_guard":
        trend_ret = work_df["daily_ret"].ewm(span=8, adjust=False).mean()
        tail_rank = work_df["pt_weight"].rank(pct=True).fillna(0)
        bucket_strength = work_df["bucket"].map({"H": 0.1, "M": 0.55, "L": 1.0}).astype(float)
        blend = (eta * bucket_strength * (0.45 + 0.55 * tail_rank)).clip(0, 0.9)
        downside_mask = work_df["daily_ret"] < 0
        guarded_ret = np.maximum(trend_ret, work_df["daily_ret"] * (1 - blend))
        work_df.loc[downside_mask, "ret_perturbed"] = guarded_ret[downside_mask]
        work_df.loc[~downside_mask, "ret_perturbed"] = (
            (1 - blend[~downside_mask] * 0.35) * work_df.loc[~downside_mask, "daily_ret"]
            + (blend[~downside_mask] * 0.35) * trend_ret[~downside_mask]
        )
        work_df["pt_blend"] = blend
    elif mode == "momentum_regime":
        trend_ret = work_df["daily_ret"].ewm(span=10, adjust=False).mean()
        vol_floor = work_df["vol_20d"].replace(0, np.nan).ffill().bfill().fillna(work_df["daily_ret"].std())
        normalized_trend = (trend_ret / (vol_floor + 1e-9)).clip(-3, 3)
        regime = np.tanh(normalized_trend * 1.8)
        tail_rank = work_df["pt_weight"].rank(pct=True).fillna(0)
        bucket_strength = work_df["bucket"].map({"H": 0.35, "M": 0.7, "L": 1.0}).astype(float)
        blend = (eta * bucket_strength * (0.35 + 0.65 * tail_rank)).clip(0, 0.9)
        regime_ret = regime * vol_floor * (0.45 + eta * 0.55)
        work_df["ret_perturbed"] = (1 - blend) * work_df["daily_ret"] + blend * regime_ret
        work_df["pt_blend"] = blend
    elif mode == "crypto_trend_guard":
        trend_ret = work_df["daily_ret"].ewm(span=12, adjust=False).mean()
        slow_trend = work_df["close"].pct_change(30).fillna(0)
        drawdown = work_df["close"] / work_df["close"].cummax() - 1
        tail_rank = work_df["pt_weight"].rank(pct=True).fillna(0)
        bucket_strength = work_df["bucket"].map({"H": 0.25, "M": 0.65, "L": 1.0}).astype(float)
        vol_floor = work_df["vol_20d"].replace(0, np.nan).ffill().bfill().fillna(work_df["daily_ret"].std())
        high_vol = work_df["vol_20d"] > work_df["vol_20d"].rolling(120, min_periods=30).quantile(0.65)
        risk_off = ((slow_trend < 0) | (drawdown < -0.14)) & high_vol.fillna(False)
        blend = (eta * bucket_strength * (0.45 + 0.55 * tail_rank)).clip(0, 0.92)
        guarded = work_df["daily_ret"].copy()
        down_mask = risk_off & (work_df["daily_ret"] < 0)
        rebound_mask = risk_off & (work_df["daily_ret"] >= 0)
        trend_mask = ~risk_off
        guarded.loc[down_mask] = work_df.loc[down_mask, "daily_ret"] * (1 + blend[down_mask] * 0.85)
        guarded.loc[rebound_mask] = work_df.loc[rebound_mask, "daily_ret"] * (1 - blend[rebound_mask] * 0.65)
        trend_blend = (blend[trend_mask] * 0.6).clip(0, 0.7)
        guarded.loc[trend_mask] = (
            (1 - trend_blend) * work_df.loc[trend_mask, "daily_ret"]
            + trend_blend * trend_ret[trend_mask]
            + np.maximum(slow_trend[trend_mask], 0) * vol_floor[trend_mask] * eta * 0.08
        )
        work_df["ret_perturbed"] = guarded.clip(-0.45, 0.45)
        work_df["pt_blend"] = blend
    else:
        raise ValueError(f"未知 PT 转换模式: {mode}")

    pt_factors = 1 + work_df["ret_perturbed"]
    pt_factors.iloc[0] = 1
    work_df["pt_close"] = float(work_df["close"].iloc[0]) * pt_factors.cumprod()
    pt_scale = work_df["pt_close"] / work_df["close"]
    work_df["pt_open"] = work_df["open"] * pt_scale
    work_df["pt_high"] = work_df["high"] * pt_scale
    work_df["pt_low"] = work_df["low"] * pt_scale
    work_df["pt_high"] = np.maximum.reduce([work_df["pt_high"], work_df["pt_open"], work_df["pt_close"]])
    work_df["pt_low"] = np.minimum.reduce([work_df["pt_low"], work_df["pt_open"], work_df["pt_close"]])
    work_df["pt_volume"] = work_df["volume"]
    return work_df


def export_model_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """Return a conventional OHLCV table backed by PT model prices."""
    required = ["pt_open", "pt_high", "pt_low", "pt_close", "pt_volume"]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"缺少 PT 模型字段: {', '.join(missing)}")
    exported = pd.DataFrame(index=df.index)
    exported["open"] = df["pt_open"]
    exported["high"] = df["pt_high"]
    exported["low"] = df["pt_low"]
    exported["close"] = df["pt_close"]
    exported["volume"] = df["pt_volume"]
    return exported
