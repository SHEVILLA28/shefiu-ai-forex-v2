import os
import requests
import pandas as pd


# =========================================================
# TWELVE DATA SETTINGS
# =========================================================

API_KEY = os.getenv("TWELVE_DATA_API_KEY")

BASE_URL = "https://api.twelvedata.com/time_series"

MIN_CANDLES = 100


# =========================================================
# TIMEFRAME CONVERSION
# =========================================================

TIMEFRAME_MAP = {
    "1M": "1min",
    "5M": "5min",
}


# =========================================================
# GET MARKET DATA
# =========================================================

def get_market_data(pair, timeframe):

    interval = TIMEFRAME_MAP.get(
        timeframe,
        "5min"
    )

    if not API_KEY:
        print("ERROR: TWELVE_DATA_API_KEY is missing.")
        return None, "TWELVE_DATA_API_KEY is not configured."

    params = {
        "symbol": pair,
        "interval": interval,
        "outputsize": 150,
        "apikey": API_KEY,
    }

    try:

        print(
            f"Requesting market data: "
            f"{pair} | {interval}"
        )

        response = requests.get(
            BASE_URL,
            params=params,
            timeout=30
        )

        print(
            f"Twelve Data status code: "
            f"{response.status_code}"
        )

        data = response.json()

        print(
            "Twelve Data response:",
            data if "values" not in data else "Market data received successfully."
        )

    except Exception as e:

        error_message = f"Market request error: {e}"

        print(error_message)

        return None, error_message


    # =====================================================
    # CHECK TWELVE DATA ERROR
    # =====================================================

    if "values" not in data:

        error_message = (
            data.get("message")
            or
            data.get("status")
            or
            "Twelve Data did not return market values."
        )

        print(
            "Twelve Data error:",
            data
        )

        return None, str(error_message)


    # =====================================================
    # PROCESS DATA
    # =====================================================

    try:

        df = pd.DataFrame(
            data["values"]
        )

        df["datetime"] = pd.to_datetime(
            df["datetime"]
        )

        df = df.sort_values(
            "datetime"
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

        df = df.dropna()

        print(
            f"Market candles received: {len(df)}"
        )

        return df, None


    except Exception as e:

        error_message = (
            f"Data processing error: {e}"
        )

        print(error_message)

        return None, error_message


# =========================================================
# CALCULATE RSI
# =========================================================

def calculate_rsi(series, period=14):

    delta = series.diff()

    gain = delta.clip(
        lower=0
    )

    loss = -delta.clip(
        upper=0
    )

    avg_gain = gain.rolling(
        window=period
    ).mean()

    avg_loss = loss.rolling(
        window=period
    ).mean()

    rs = avg_gain / avg_loss.replace(
        0,
        0.000001
    )

    rsi = 100 - (
        100 / (1 + rs)
    )

    return rsi


# =========================================================
# CALCULATE SIGNAL
# =========================================================

def get_signal(pair, timeframe="5M"):

    if not API_KEY:

        return {
            "pair": pair,
            "timeframe": timeframe,
            "signal": "NO TRADE",
            "entry": "N/A",
            "take_profit": "N/A",
            "stop_loss": "N/A",
            "trend": "WAIT",
            "rsi": "N/A",
            "confidence": 0,
            "reason": (
                "TWELVE_DATA_API_KEY is not configured "
                "in Render."
            )
        }


    # =====================================================
    # GET MARKET DATA
    # =====================================================

    df, error_message = get_market_data(
        pair,
        timeframe
    )


    if df is None:

        return {
            "pair": pair,
            "timeframe": timeframe,
            "signal": "NO TRADE",
            "entry": "N/A",
            "take_profit": "N/A",
            "stop_loss": "N/A",
            "trend": "WAIT",
            "rsi": "N/A",
            "confidence": 0,
            "reason": (
                f"Market data error: {error_message}"
            )
        }


    # =====================================================
    # CHECK CANDLES
    # =====================================================

    if len(df) < MIN_CANDLES:

        return {
            "pair": pair,
            "timeframe": timeframe,
            "signal": "NO TRADE",
            "entry": "N/A",
            "take_profit": "N/A",
            "stop_loss": "N/A",
            "trend": "WAIT",
            "rsi": "N/A",
            "confidence": 0,
            "reason": (
                f"Not enough market candles. "
                f"Received {len(df)}, need {MIN_CANDLES}."
            )
        }


    # =====================================================
    # INDICATORS
    # =====================================================

    df["EMA20"] = df["close"].ewm(
        span=20,
        adjust=False
    ).mean()

    df["EMA50"] = df["close"].ewm(
        span=50,
        adjust=False
    ).mean()

    df["RSI"] = calculate_rsi(
        df["close"],
        14
    )

    df["EMA12"] = df["close"].ewm(
        span=12,
        adjust=False
    ).mean()

    df["EMA26"] = df["close"].ewm(
        span=26,
        adjust=False
    ).mean()

    df["MACD"] = (
        df["EMA12"]
        -
        df["EMA26"]
    )

    df["MACD_SIGNAL"] = df["MACD"].ewm(
        span=9,
        adjust=False
    ).mean()


    # =====================================================
    # LATEST VALUES
    # =====================================================

    last = df.iloc[-1]

    close = float(last["close"])

    ema20 = float(last["EMA20"])

    ema50 = float(last["EMA50"])

    rsi = float(last["RSI"])

    macd = float(last["MACD"])

    macd_signal = float(last["MACD_SIGNAL"])

    recent_high = float(
        df["high"].tail(20).max()
    )

    recent_low = float(
        df["low"].tail(20).min()
    )


    # =====================================================
    # TREND
    # =====================================================

    if ema20 > ema50:
        trend = "BUY"

    elif ema20 < ema50:
        trend = "SELL"

    else:
        trend = "WAIT"


    # =====================================================
    # BUY SIGNAL
    # =====================================================

    if (
        trend == "BUY"
        and macd > macd_signal
        and rsi >= 50
        and rsi < 70
    ):

        risk = close - recent_low

        if risk <= 0:
            risk = close * 0.002

        stop_loss = close - risk

        take_profit = close + (
            risk * 1.5
        )

        return {
            "pair": pair,
            "timeframe": timeframe,
            "signal": "BUY",
            "entry": round(close, 5),
            "take_profit": round(
                take_profit,
                5
            ),
            "stop_loss": round(
                stop_loss,
                5
            ),
            "trend": trend,
            "rsi": round(rsi, 2),
            "confidence": 70,
            "reason": (
                "Bullish EMA trend with "
                "MACD confirmation and "
                "RSI support."
            )
        }


    # =====================================================
    # SELL SIGNAL
    # =====================================================

    if (
        trend == "SELL"
        and macd < macd_signal
        and rsi <= 50
        and rsi > 30
    ):

        risk = recent_high - close

        if risk <= 0:
            risk = close * 0.002

        stop_loss = close + risk

        take_profit = close - (
            risk * 1.5
        )

        return {
            "pair": pair,
            "timeframe": timeframe,
            "signal": "SELL",
            "entry": round(close, 5),
            "take_profit": round(
                take_profit,
                5
            ),
            "stop_loss": round(
                stop_loss,
                5
            ),
            "trend": trend,
            "rsi": round(rsi, 2),
            "confidence": 70,
            "reason": (
                "Bearish EMA trend with "
                "MACD confirmation and "
                "RSI support."
            )
        }


    # =====================================================
    # NO TRADE
    # =====================================================

    return {
        "pair": pair,
        "timeframe": timeframe,
        "signal": "NO TRADE",
        "entry": "N/A",
        "take_profit": "N/A",
        "stop_loss": "N/A",
        "trend": trend,
        "rsi": round(rsi, 2),
        "confidence": 0,
        "reason": (
            "Market conditions do not "
            "currently meet the BUY or "
            "SELL confirmation rules."
        )
        }
