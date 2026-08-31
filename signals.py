import os
import time
import threading
from datetime import datetime, timezone

import requests
import pandas as pd


API_KEY = os.getenv("TWELVE_DATA_API_KEY")

MIN_CANDLES = 80
MAX_DATA_AGE_MINUTES = 15


# =========================================================
# TWELVE DATA RATE LIMIT PROTECTION
# =========================================================

DATA_REQUEST_LOCK = threading.Lock()

LAST_DATA_REQUEST_TIME = 0.0

MIN_REQUEST_INTERVAL_SECONDS = 8


def market_data_request(url, params):
    """
    Request Twelve Data market data while spacing requests
    apart and retrying temporary 429 rate-limit responses.
    """

    global LAST_DATA_REQUEST_TIME

    with DATA_REQUEST_LOCK:

        now = time.monotonic()

        elapsed = (
            now - LAST_DATA_REQUEST_TIME
        )

        if elapsed < MIN_REQUEST_INTERVAL_SECONDS:

            time.sleep(
                MIN_REQUEST_INTERVAL_SECONDS
                - elapsed
            )

        LAST_DATA_REQUEST_TIME = time.monotonic()

        last_response = None

        for attempt in range(3):

            try:

                response = requests.get(
                    url,
                    params=params,
                    timeout=20
                )

                last_response = response

                if response.status_code == 429:

                    retry_after = response.headers.get(
                        "Retry-After"
                    )

                    try:
                        wait_seconds = float(
                            retry_after
                        )
                    except (
                        TypeError,
                        ValueError
                    ):
                        wait_seconds = 20 * (
                            attempt + 1
                        )

                    wait_seconds = max(
                        10,
                        min(
                            wait_seconds,
                            60
                        )
                    )

                    print(
                        "Twelve Data rate limit "
                        f"(429). Waiting "
                        f"{wait_seconds:.0f}s..."
                    )

                    time.sleep(
                        wait_seconds
                    )

                    LAST_DATA_REQUEST_TIME = (
                        time.monotonic()
                    )

                    continue

                response.raise_for_status()

                return response.json()

            except requests.RequestException as e:

                if attempt >= 2:

                    raise RuntimeError(
                        f"Market data request failed: {e}"
                    ) from e

                wait_seconds = 5 * (
                    attempt + 1
                )

                print(
                    "Market data request error. "
                    f"Retrying in {wait_seconds}s: {e}"
                )

                time.sleep(
                    wait_seconds
                )

                LAST_DATA_REQUEST_TIME = (
                    time.monotonic()
                )

        if last_response is not None:

            last_response.raise_for_status()

        raise RuntimeError(
            "Twelve Data request failed"
        )


# =========================================================
# TIMEFRAME SETTINGS
# =========================================================

TIMEFRAME_SETTINGS = {

    "1M": {
        "api_interval": "1min",
        "minutes": 1,
        "outputsize": 160,
    },

    "2M": {
        "api_interval": "1min",
        "minutes": 2,
        "outputsize": 220,
    },

    "3M": {
        "api_interval": "1min",
        "minutes": 3,
        "outputsize": 280,
    },

    "5M": {
        "api_interval": "5min",
        "minutes": 5,
        "outputsize": 140,
    },
}


# =========================================================
# ALLOWED MARKETS - 10 PAIRS
# =========================================================

DISPLAY_PAIRS = {

    "EUR/USD": "EUR/USD",

    "GBP/USD": "GBP/USD",

    "USD/JPY": "USD/JPY",

    "USD/CHF": "USD/CHF",

    "AUD/USD": "AUD/USD",

    "USD/CAD": "USD/CAD",

    "USDCAD": "USD/CAD",

    "NZD/USD": "NZD/USD",

    "XAU/USD": "XAU/USD",

    "XAUUSD": "XAU/USD",

    "EUR/GBP": "EUR/GBP",

    "USD/SGD": "USD/SGD",
}


# =========================================================
# NO TRADE
# =========================================================

def no_trade(
    pair,
    reason="Conditions are not strong enough",
    timeframe=None
):

    return {

        "pair": DISPLAY_PAIRS.get(
            pair,
            pair
        ),

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

        "timeframe": timeframe,
    }


# =========================================================
# EMA
# =========================================================

def ema(
    series,
    period
):

    return series.ewm(
        span=period,
        adjust=False
    ).mean()


# =========================================================
# RSI
# =========================================================

def rsi(
    series,
    period=14
):

    delta = series.diff()

    gain = delta.clip(
        lower=0
    )

    loss = -delta.clip(
        upper=0
    )

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

    avg_loss = avg_loss.replace(
        0,
        pd.NA
    )

    rs = avg_gain / avg_loss

    result = 100 - (
        100 / (1 + rs)
    )

    return result.fillna(100)


# =========================================================
# MACD
# =========================================================

def macd(
    series
):

    ema12 = ema(
        series,
        12
    )

    ema26 = ema(
        series,
        26
    )

    macd_line = (
        ema12 - ema26
    )

    signal_line = ema(
        macd_line,
        9
    )

    histogram = (
        macd_line - signal_line
    )

    return (
        macd_line,
        signal_line,
        histogram
    )


# =========================================================
# PIP SIZE
# =========================================================

def pip_size(
    pair
):

    normalized = DISPLAY_PAIRS.get(
        pair,
        pair
    ).upper()

    if "XAU/" in normalized:

        return 0.01

    if "JPY" in normalized:

        return 0.01

    return 0.0001


# =========================================================
# NORMALIZE TIMEFRAME
# =========================================================

def normalize_timeframe(
    timeframe
):

    if timeframe is None:

        return "5M"

    value = str(
        timeframe
    ).strip().upper()

    aliases = {

        "1": "1M",
        "1M": "1M",
        "1 MIN": "1M",
        "1MIN": "1M",

        "2": "2M",
        "2M": "2M",
        "2 MIN": "2M",
        "2MIN": "2M",

        "3": "3M",
        "3M": "3M",
        "3 MIN": "3M",
        "3MIN": "3M",

        "5": "5M",
        "5M": "5M",
        "5 MIN": "5M",
        "5MIN": "5M",
    }

    return aliases.get(
        value,
        "5M"
    )


# =========================================================
# RESAMPLE MINUTES
# =========================================================

def resample_minutes(
    df,
    minutes
):

    """
    Build 2-minute or 3-minute candles from
    Twelve Data 1-minute candles.
    """

    if minutes == 1:

        return df

    working = (
        df.set_index(
            "datetime"
        )
        .sort_index()
    )

    rule = f"{minutes}min"

    resampled = (

        working.resample(
            rule,
            label="right",
            closed="right"
        )

        .agg(
            {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
            }
        )

        .dropna()

        .reset_index()
    )

    return resampled


# =========================================================
# MAIN SIGNAL FUNCTION
# =========================================================

def get_signal(
    pair,
    timeframe="5M"
):

    """
    Main signal function used by main.py.

    Supported:

        1M
        2M
        3M
        5M

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

    display_pair = DISPLAY_PAIRS.get(
        pair
    )

    if not display_pair:

        return no_trade(
            pair,
            "Pair is not in the allowed market list",
            timeframe
        )

    timeframe = normalize_timeframe(
        timeframe
    )

    settings = TIMEFRAME_SETTINGS[
        timeframe
    ]

    minutes = settings[
        "minutes"
    ]

    # =====================================================
    # MARKET CLOSED CHECK
    # =====================================================

    now = datetime.now(
        timezone.utc
    )

    if now.weekday() >= 5:

        return no_trade(
            display_pair,
            "Market closed",
            timeframe
        )

    # =====================================================
    # TWELVE DATA REQUEST
    # =====================================================

    symbol = display_pair

    url = (
        "https://api.twelvedata.com/"
        "time_series"
    )

    params = {

        "symbol": symbol,

        "interval": settings[
            "api_interval"
        ],

        "outputsize": settings[
            "outputsize"
        ],

        "apikey": API_KEY,
    }

    data = market_data_request(
        url,
        params
    )

    # =====================================================
    # API ERROR
    # =====================================================

    if data.get(
        "status"
    ) == "error":

        message = data.get(
            "message",
            "Twelve Data returned an error"
        )

        return no_trade(
            display_pair,
            f"Market data unavailable: {message}",
            timeframe
        )

    rows = data.get(
        "values"
    ) or []

    if len(rows) < MIN_CANDLES:

        return no_trade(
            display_pair,
            "Not enough market data",
            timeframe
        )

    # =====================================================
    # DATAFRAME
    # =====================================================

    df = pd.DataFrame(
        rows
    )

    required = {

        "datetime",
        "open",
        "high",
        "low",
        "close",
    }

    if not required.issubset(
        df.columns
    ):

        return no_trade(
            display_pair,
            "Incomplete market data",
            timeframe
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
        "close",

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
            "close",

        ]
    )

    df = (
        df.sort_values(
            "datetime"
        )
        .reset_index(
            drop=True
        )
    )

    # =====================================================
    # BUILD 2M / 3M CANDLES
    # =====================================================

    if minutes in {

        2,
        3,

    }:

        df = resample_minutes(
            df,
            minutes
        )

    if len(df) < MIN_CANDLES:

        return no_trade(
            display_pair,
            "Not enough valid timeframe candles",
            timeframe
        )

    # =====================================================
    # DATA FRESHNESS
    # =====================================================

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
            display_pair,
            "Market data is stale / market may be closed",
            timeframe
        )

    # =====================================================
    # PRICE DATA
    # =====================================================

    close = df["close"]

    high = df["high"]

    low = df["low"]

    # =====================================================
    # INDICATORS
    # =====================================================

    df["ema20"] = ema(
        close,
        20
    )

    df["ema50"] = ema(
        close,
        50
    )

    df["rsi"] = rsi(
        close,
        14
    )

    (
        df["macd"],
        df["macd_signal"],
        df["macd_hist"]
    ) = macd(
        close
    )

    latest = df.iloc[-1]

    previous = df.iloc[-2]

    price = float(
        latest["close"]
    )

    ema20 = float(
        latest["ema20"]
    )

    ema50 = float(
        latest["ema50"]
    )

    rsi_value = float(
        latest["rsi"]
    )

    macd_value = float(
        latest["macd"]
    )

    macd_signal_value = float(
        latest["macd_signal"]
    )

    # =====================================================
    # SUPPORT / RESISTANCE
    # =====================================================

    support = float(
        low.tail(
            20
        ).min()
    )

    resistance = float(
        high.tail(
            20
        ).max()
    )

    # =====================================================
    # SCORES
    # =====================================================

    buy_score = 0

    sell_score = 0

    # =====================================================
    # TREND
    # =====================================================

    if (

        price > ema50

        and

        ema20 > ema50

    ):

        buy_score += 2

        trend = "BUY"

    elif (

        price < ema50

        and

        ema20 < ema50

    ):

        sell_score += 2

        trend = "SELL"

    else:

        trend = "SIDEWAYS"

    # =====================================================
    # RSI
    # =====================================================

    if (

        50 <= rsi_value < 70

    ):

        buy_score += 1

    elif (

        30 < rsi_value <= 50

    ):

        sell_score += 1

    # =====================================================
    # MACD
    # =====================================================

    previous_macd = float(
        previous["macd"]
    )

    previous_signal = float(
        previous["macd_signal"]
    )

    if (

        macd_value > macd_signal_value

        and

        previous_macd <= previous_signal

    ):

        buy_score += 2

    elif (

        macd_value < macd_signal_value

        and

        previous_macd >= previous_signal

    ):

        sell_score += 2

    elif macd_value > macd_signal_value:

        buy_score += 1

    elif macd_value < macd_signal_value:

        sell_score += 1

    # =====================================================
    # SUPPORT / RESISTANCE
    # =====================================================

    pip = pip_size(
        display_pair
    )

    near_support = (
        price <= support + (
            15 * pip
        )
    )

    near_resistance = (
        price >= resistance - (
            15 * pip
        )
    )

    if (

        near_support

        and

        price > support

    ):

        buy_score += 1

    if (

        near_resistance

        and

        price < resistance

    ):

        sell_score += 1

    # =====================================================
    # STRONG BUY
    # =====================================================

    if (

        buy_score >= 5

        and

        buy_score > sell_score

        and

        not near_resistance

    ):

        signal = "BUY"

        confidence = min(
            95,
            60 + buy_score * 5
        )

        trend = "BUY"

    # =====================================================
    # STRONG SELL
    # =====================================================

    elif (

        sell_score >= 5

        and

        sell_score > buy_score

        and

        not near_support

    ):

        signal = "SELL"

        confidence = min(
            95,
            60 + sell_score * 5
        )

        trend = "SELL"

    # =====================================================
    # NO TRADE
    # =====================================================

    else:

        return {

            **no_trade(
                display_pair,
                "Indicators are not strongly aligned; WAIT",
                timeframe
            ),

            "entry": round(
                price,
                5
            ),

            "trend": trend,

            "rsi": round(
                rsi_value,
                2
            ),

            "ema50": round(
                ema50,
                5
            ),

            "macd": round(
                macd_value,
                6
            ),

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
        }

    # =====================================================
    # TAKE PROFIT / STOP LOSS
    # =====================================================

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

    # =====================================================
    # FINAL RESULT
    # =====================================================

    return {

        "pair": display_pair,

        "signal": signal,

        "entry": round(
            price,
            5
        ),

        "take_profit": take_profit,

        "stop_loss": stop_loss,

        "trend": trend,

        "rsi": round(
            rsi_value,
            2
        ),

        "ema50": round(
            ema50,
            5
        ),

        "macd": round(
            macd_value,
            6
        ),

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

        "timeframe": timeframe,
        }
