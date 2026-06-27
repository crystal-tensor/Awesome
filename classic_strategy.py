import numpy as np
import pandas as pd


def calc_backtest_metrics(net_series: pd.Series, ret_series: pd.Series) -> dict:
    """计算回测核心指标：累计收益、年化收益、最大回撤、胜率、夏普比率。"""
    total_ret = net_series.iloc[-1] - 1
    days = len(net_series)
    annual_ret = (1 + total_ret) ** (252 / days) - 1

    rolling_max = net_series.cummax()
    drawdown = (net_series - rolling_max) / rolling_max
    max_dd = drawdown.min()

    win_rate = (ret_series > 0).sum() / len(ret_series)

    daily_mean = ret_series.mean()
    daily_std = ret_series.std()
    sharpe = (daily_mean / daily_std) * np.sqrt(252) if daily_std > 0 else 0

    return {
        "累计收益率": round(float(total_ret), 4),
        "年化收益率": round(float(annual_ret), 4),
        "最大回撤": round(float(max_dd), 4),
        "胜率": round(float(win_rate), 4),
        "夏普比率": round(float(sharpe), 4),
    }


def build_strategy(
    df: pd.DataFrame,
    prefix: str,
    open_col: str,
    high_col: str,
    low_col: str,
    close_col: str,
    real_close_col: str,
    real_ret_col: str,
) -> dict:
    """基于指定价格路径生成信号；收益使用真实历史价格/收益率计算。"""
    ma5_col = f"{prefix}_ma5"
    ma20_col = f"{prefix}_ma20"
    signal_col = f"{prefix}_signal"
    signal_shift_col = f"{prefix}_signal_shift"
    action_col = f"{prefix}_trade_action"
    strategy_ret_col = f"{prefix}_strategy_ret"
    net_col = f"{prefix}_net"

    df[ma5_col] = df[close_col].rolling(5).mean()
    df[ma20_col] = df[close_col].rolling(20).mean()
    df[signal_col] = np.where(df[ma5_col] > df[ma20_col], 1, 0)
    df[signal_shift_col] = df[signal_col].shift(1).fillna(0)
    df[action_col] = df[signal_col].diff()

    trades = []
    algo_buy_price = 0
    real_buy_price = 0
    buy_date = None
    for date, row in df.iterrows():
        if row[action_col] == 1:
            algo_buy_price = row[close_col]
            real_buy_price = row[real_close_col]
            buy_date = date
        elif row[action_col] == -1 and algo_buy_price > 0:
            algo_sell_price = row[close_col]
            real_sell_price = row[real_close_col]
            abs_ret = real_sell_price - real_buy_price
            trade_ret = abs_ret / real_buy_price

            trade_data = {
                "买入日期": buy_date.strftime("%Y-%m-%d"),
                "卖出日期": date.strftime("%Y-%m-%d"),
            }
            if prefix == "pt":
                trade_data["量子算法买入价"] = round(float(algo_buy_price), 2)
                trade_data["量子算法卖出价"] = round(float(algo_sell_price), 2)

            trade_data["买入价"] = round(float(real_buy_price), 2)
            trade_data["卖出价"] = round(float(real_sell_price), 2)
            trade_data["绝对收益"] = round(float(abs_ret), 2)
            trade_data["收益率"] = round(float(trade_ret), 6)

            trades.append(trade_data)
            algo_buy_price = 0
            real_buy_price = 0

    df[strategy_ret_col] = df[signal_shift_col] * df[real_ret_col]
    df[net_col] = (1 + df[strategy_ret_col]).cumprod()

    buy_points = []
    sell_points = []
    for date, row in df.iterrows():
        point = {"date": date.strftime("%Y-%m-%d"), "price": round(float(row[close_col]), 4)}
        if row[action_col] == 1:
            buy_points.append(point)
        elif row[action_col] == -1:
            sell_points.append(point)

    return {
        "columns": {
            "open": open_col,
            "high": high_col,
            "low": low_col,
            "close": close_col,
            "ma5": ma5_col,
            "ma20": ma20_col,
            "net": net_col,
        },
        "metrics": calc_backtest_metrics(df[net_col], df[strategy_ret_col]),
        "trades": trades,
        "buyPoints": buy_points,
        "sellPoints": sell_points,
    }


def clean_numeric_list(series: pd.Series, digits: int = 4) -> list:
    values = []
    for value in series:
        values.append(None if pd.isna(value) else round(float(value), digits))
    return values


def build_chart_series(chart_df: pd.DataFrame, strategy: dict) -> dict:
    cols = strategy["columns"]
    return {
        "kline": chart_df[[cols["open"], cols["close"], cols["low"], cols["high"]]].round(4).values.tolist(),
        "close": clean_numeric_list(chart_df[cols["close"]], 4),
        "ma5": clean_numeric_list(chart_df[cols["ma5"]], 4),
        "ma20": clean_numeric_list(chart_df[cols["ma20"]], 4),
        "buyPoints": strategy["buyPoints"],
        "sellPoints": strategy["sellPoints"],
    }


def compute_classic_strategy(df: pd.DataFrame) -> dict:
    work_df = df.copy()
    strategy = build_strategy(
        work_df,
        "uniform",
        "open",
        "high",
        "low",
        "close",
        "close",
        "daily_ret",
    )
    chart_df = work_df.reset_index()
    chart_df["date"] = chart_df["date"].dt.strftime("%Y-%m-%d")
    return {
        "metrics": strategy["metrics"],
        "series": build_chart_series(chart_df, strategy),
        "net": clean_numeric_list(chart_df["uniform_net"], 6),
        "trades": strategy["trades"],
    }
