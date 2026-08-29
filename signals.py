import os
from datetime import datetime, timezone

import requests
import pandas as pd


API_KEY = os.getenv("TWELVE_DATA_API_KEY")

TIMEFRAME = "5min"
MIN_CANDLES = 80
MAX_DATA_AGE_MINUTES = 15


def no_trade(pair, reason="Conditions are not strong enough"):
    return {
        "pair": pair,
        "signal": "NO TRADE",
        "entry": None,
        "take_profit": None,
        "stop_loss": None,
        "trend": "WAIT",
        "rsi": None,
        "ema50": None,
        "macd": None,
        "macd_signal": None,
        "support": None,
        "resistance": None,
        "confidence": 0,
        "reason": reason,
    }


def ema(series, period):
    return series.ewm(
        span=period,
        adjust=False
    ).mean()


def rsi(series, period=14):
    delta = series.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(
        alpha=1 / period,
        adjust=False,
        min_periods=period
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / period,
        adjust=False,
        min_periods=period
    ).mean()

    avg_loss = avg_loss.replace(0, pd.NA)

    rs = avg_gain / avg_loss

    result = 100 - (100 / (1 + rs))

    return result.fillna(100)


def macd(series):
    ema12 = ema(series, 12)
    ema26 = ema(series, 26)

    macd_line = ema12 - ema26
    signal_line = ema(macd_line, 9)

    histogram = macd_line - signal_line

    return macd_line, signal_line, histogram


def pip_size(pair):
    if "JPY" in pair.upper():
        return 0.01

    return 0.0001


def get_signal(pair):
    """
    Main signal function used by main.py.

    Returns:
        BUY
        SELL
        NO TRADE
    """

    if not API_KEY:
        raise RuntimeError(
            "TWELVE_DATA_API_KEY is missing in Render Environment"
        )

    pair = pair.strip().upper()

    allowed_pairs = {
        "EUR/USD",
        "GBP/USD",
        "USD/JPY",
        "USD/CHF",
        "AUD/USD",
        "USD/CAD",
        "USDCAD",
        "NZD/USD",
        "XAUUSD",
    }

    if pair not in allowed_pairs:
        return no_trade(
            pair,
            "Pair is not in the allowed Forex list"
        )

    # Forex market is normally closed on Saturday and Sunday.
    now = datetime.now(timezone.utc)

    if now.weekday() >= 5:
        return no_trade(
            pair,
            "Market closed"
        )

    symbol = pair.replace("/", "")

    url = "https://api.twelvedata.com/time_series"

    params = {
        "symbol": symbol,
        "interval": TIMEFRAME,
        "outputsize": 120,
        "apikey": API_KEY,
    }

    response = requests.get(
        url,
        params=params,
        timeout=20
    )

    response.raise_for_status()

    data = response.json()

    if data.get("status") == "error":
        message = data.get(
            "message",
            "Twelve Data returned an error"
        )

        return no_trade(
            pair,
            f"Market data unavailable: {message}"
        )

    rows = data.get("values") or []

    if len(rows) < MIN_CANDLES:
        return no_trade(
            pair,
            "Not enough market data"
        )

    df = pd.DataFrame(rows)

    required = {
        "datetime",
        "open",
        "high",
        "low",
        "close"
    }

    if not required.issubset(df.columns):
        return no_trade(
            pair,
            "Incomplete market data"
        )

    df["datetime"] = pd.to_datetime(
        df["datetime"],
        utc=True,
        errors="coerce"
    )

    for column in [
        "open",
        "high",
        "low",
        "close"
    ]:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    df = df.dropna(
        subset=[
            "datetime",
            "open",
            "high",
            "low",
            "close"
        ]
    )

    df = df.sort_values(
        "datetime"
    ).reset_index(drop=True)

    if len(df) < MIN_CANDLES:
        return no_trade(
            pair,
            "Not enough valid candles"
        )

    latest_time = (
        df["datetime"]
        .iloc[-1]
        .to_pydatetime()
    )

    age_minutes = (
        now - latest_time
    ).total_seconds() / 60

    if age_minutes > MAX_DATA_AGE_MINUTES:
        return no_trade(
            pair,
            "Market data is stale / market may be closed"
        )

    close = df["close"]
    high = df["high"]
    low = df["low"]

    df["ema20"] = ema(close, 20)
    df["ema50"] = ema(close, 50)

    df["rsi"] = rsi(close, 14)

    (
        df["macd"],
        df["macd_signal"],
        df["macd_hist"]
    ) = macd(close)

    latest = df.iloc[-1]
    previous = df.iloc[-2]

    price = float(latest["close"])

    ema20 = float(latest["ema20"])
    ema50 = float(latest["ema50"])

    rsi_value = float(latest["rsi"])

    macd_value = float(latest["macd"])
    macd_signal_value = float(
        latest["macd_signal"]
    )

    support = float(
        low.tail(20).min()
    )

    resistance = float(
        high.tail(20).max()
    )

    buy_score = 0
    sell_score = 0

    # =========================
    # TREND
    # =========================

    if price > ema50 and ema20 > ema50:
        buy_score += 2
        trend = "BUY"

    elif price < ema50 and ema20 < ema50:
        sell_score += 2
        trend = "SELL"

    else:
        trend = "SIDEWAYS"

    # =========================
    # RSI
    # =========================

    if 50 <= rsi_value < 70:
        buy_score += 1

    elif 30 < rsi_value <= 50:
        sell_score += 1

    # =========================
    # MACD
    # =========================

    previous_macd = float(
        previous["macd"]
    )

    previous_signal = float(
        previous["macd_signal"]
    )

    if (
        macd_value > macd_signal_value
        and previous_macd <= previous_signal
    ):
        buy_score += 2

    elif (
        macd_value < macd_signal_value
        and previous_macd >= previous_signal
    ):
        sell_score += 2

    elif macd_value > macd_signal_value:
        buy_score += 1

    elif macd_value < macd_signal_value:
        sell_score += 1

    # =========================
    # SUPPORT / RESISTANCE
    # =========================

    pip = pip_size(pair)

    near_support = (
        price <= support + (15 * pip)
    )

    near_resistance = (
        price >= resistance - (15 * pip)
    )

    if near_support and price > support:
        buy_score += 1

    if near_resistance and price < resistance:
        sell_score += 1

    # =========================
    # STRONG SIGNAL FILTER
    # =========================

    if (
        buy_score >= 5
        and buy_score > sell_score
        and not near_resistance
    ):
        signal = "BUY"
        confidence = min(
            95,
            60 + buy_score * 5
        )
        trend = "BUY"

    elif (
        sell_score >= 5
        and sell_score > buy_score
        and not near_support
    ):
        signal = "SELL"
        confidence = min(
            95,
            60 + sell_score * 5
        )
        trend = "SELL"

    else:
        return {
            **no_trade(
                pair,
                "Indicators are not strongly aligned; WAIT"
            ),
            "entry": round(price, 5),
            "trend": trend,
            "rsi": round(rsi_value, 2),
            "ema50": round(ema50, 5),
            "macd": round(macd_value, 6),
            "macd_signal": round(
                macd_signal_value,
                6
            ),
            "support": round(support, 5),
            "resistance": round(
                resistance,
                5
            ),
        }

    # =========================
    # TAKE PROFIT / STOP LOSS
    # =========================

    tp_distance = 50 * pip
    sl_distance = 25 * pip

    if signal == "BUY":

        take_profit = round(
            price + tp_distance,
            5
        )

        stop_loss = round(
            price - sl_distance,
            5
        )

    else:

        take_profit = round(
            price - tp_distance,
            5
        )

        stop_loss = round(
            price + sl_distance,
            5
        )

    # =========================
    # FINAL RESULT
    # =========================

    return {
        "pair": pair,
        "signal": signal,
        "entry": round(price, 5),
        "take_profit": take_profit,
        "stop_loss": stop_loss,
        "trend": trend,
        "rsi": round(rsi_value, 2),
        "ema50": round(ema50, 5),
        "macd": round(macd_value, 6),
        "macd_signal": round(
            macd_signal_value,
            6
        ),
        "support": round(
            support,
            5
        ),
        "resistance": round(
            resistance,
            5
        ),
        "confidence": confidence,
        "reason": (
            "EMA + RSI + MACD + "
            "support/resistance confirmations"
        ),
        }
