import os
import requests
import pandas as pd


# =========================================================
# FCSAPI SETTINGS
# =========================================================

API_KEY = os.getenv("FCSAPI_API_KEY")

BASE_URL = "https://api-v4.fcsapi.com/forex/history"

MIN_CANDLES = 100


# =========================================================
# TIMEFRAME CONVERSION
# =========================================================

TIMEFRAME_MAP = {
    "1M": "1m",
    "2M": "2m",
    "3M": "3m",
    "5M": "5m",
}


# =========================================================
# CONVERT PAIR FORMAT
# =========================================================

def format_symbol(pair):

    return pair.replace("/", "")


# =========================================================
# GET MARKET DATA
# =========================================================

def get_market_data(pair, timeframe):

    if not API_KEY:

        error_message = (
            "FCSAPI_API_KEY is not configured in Render."
        )

        print(error_message)

        return None, error_message


    period = TIMEFRAME_MAP.get(
        timeframe,
        "5m"
    )

    symbol = format_symbol(pair)


    params = {

        "symbol": symbol,

        "period": period,

        "length": 150,

        "access_key": API_KEY,

    }


    try:

        print(
            f"Requesting FCSAPI market data: "
            f"{symbol} | {period}"
        )


        response = requests.get(

            BASE_URL,

            params=params,

            timeout=30

        )


        print(
            f"FCSAPI status code: "
            f"{response.status_code}"
        )


        data = response.json()


    except Exception as e:

        error_message = (
            f"FCSAPI market request error: {e}"
        )

        print(error_message)

        return None, error_message


    # =====================================================
    # CHECK API RESPONSE
    # =====================================================

    if not data.get("status"):

        error_message = (

            data.get("msg")

            or data.get("message")

            or "FCSAPI did not return market data."

        )

        print(
            "FCSAPI error:",
            data
        )

        return None, str(error_message)


    response_data = data.get("response")


    if not response_data:

        error_message = (
            "FCSAPI returned no market candles."
        )

        print(error_message)

        return None, error_message


    # =====================================================
    # PROCESS MARKET DATA
    # =====================================================

    try:

        rows = []


        if isinstance(response_data, dict):

            candles = list(
                response_data.values()
            )

        elif isinstance(response_data, list):

            candles = response_data

        else:

            return None, (
                "Unexpected FCSAPI response format."
            )


        for candle in candles:

            if not isinstance(candle, dict):

                continue


            rows.append({

                "datetime": candle.get("tm"),

                "timestamp": candle.get("t"),

                "open": candle.get("o"),

                "high": candle.get("h"),

                "low": candle.get("l"),

                "close": candle.get("c"),

            })


        df = pd.DataFrame(rows)


        if df.empty:

            return None, (
                "FCSAPI returned empty candle data."
            )


        # =================================================
        # DATETIME
        # =================================================

        df["datetime"] = pd.to_datetime(

            df["datetime"],

            errors="coerce"

        )


        # =================================================
        # NUMERIC DATA
        # =================================================

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

        ).reset_index(

            drop=True

        )


        print(

            f"FCSAPI candles received: "
            f"{len(df)}"

        )


        if len(df) < MIN_CANDLES:

            return None, (
                f"Not enough market candles. "
                f"Received {len(df)}, "
                f"need at least {MIN_CANDLES}."
            )


        return df, None


    except Exception as e:

        error_message = (

            f"FCSAPI data processing error: {e}"

        )

        print(error_message)

        return None, error_message


# =========================================================
# CALCULATE RSI
# =========================================================

def calculate_rsi(series, period=14):

    delta = series.diff()

    gain = delta.clip(lower=0)

    loss = -delta.clip(upper=0)


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
# CALCULATE EMA
# =========================================================

def calculate_ema(series, period):

    return series.ewm(
        span=period,
        adjust=False
    ).mean()


# =========================================================
# CALCULATE ATR
# =========================================================

def calculate_atr(df, period=14):

    high_low = df["high"] - df["low"]

    high_close = (
        df["high"]
        -
        df["close"].shift()
    ).abs()

    low_close = (
        df["low"]
        -
        df["close"].shift()
    ).abs()


    true_range = pd.concat(

        [

            high_low,

            high_close,

            low_close

        ],

        axis=1

    ).max(axis=1)


    atr = true_range.rolling(
        window=period
    ).mean()


    return atr


# =========================================================
# FORMAT PRICE
# =========================================================

def format_price(price):

    if pd.isna(price):

        return "N/A"


    if price >= 100:

        return round(float(price), 3)


    return round(float(price), 5)


# =========================================================
# CALCULATE SIGNAL
# =========================================================

def get_signal(pair, timeframe="5M"):


    # =====================================================
    # CHECK API KEY
    # =====================================================

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
                "FCSAPI_API_KEY is not configured "
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

            "reason": error_message

        }


    # =====================================================
    # CALCULATE INDICATORS
    # =====================================================

    try:

        df["ema_20"] = calculate_ema(

            df["close"],

            20

        )


        df["ema_50"] = calculate_ema(

            df["close"],

            50

        )


        df["rsi"] = calculate_rsi(

            df["close"],

            14

        )


        df["atr"] = calculate_atr(

            df,

            14

        )


        latest = df.iloc[-1]


        previous = df.iloc[-2]


        close = float(
            latest["close"]
        )


        ema_20 = float(
            latest["ema_20"]
        )


        ema_50 = float(
            latest["ema_50"]
        )


        rsi = float(
            latest["rsi"]
        )


        atr = float(
            latest["atr"]
        )


    except Exception as e:

        print(
            "Indicator calculation error:",
            e
        )

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
                f"Indicator calculation error: {e}"
            )

        }


    # =====================================================
    # CHECK FOR INVALID INDICATORS
    # =====================================================

    if pd.isna(rsi) or pd.isna(atr):

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
                "Not enough data to calculate "
                "technical indicators."
            )

        }


    # =====================================================
    # DETERMINE TREND
    # =====================================================

    if ema_20 > ema_50:

        trend = "BUY"

    elif ema_20 < ema_50:

        trend = "SELL"

    else:

        trend = "WAIT"


    # =====================================================
    # BUY SIGNAL
    # =====================================================

    if (

        trend == "BUY"

        and

        close > ema_20

        and

        rsi >= 50

        and

        rsi <= 70

    ):

        entry = close

        stop_loss = close - (
            atr * 1.5
        )

        take_profit = close + (
            atr * 2.0
        )


        confidence = 70


        if rsi >= 55:

            confidence += 10


        return {

            "pair": pair,

            "timeframe": timeframe,

            "signal": "BUY",

            "entry": format_price(entry),

            "take_profit": format_price(
                take_profit
            ),

            "stop_loss": format_price(
                stop_loss
            ),

            "trend": "BUY",

            "rsi": round(rsi, 2),

            "confidence": confidence,

            "reason": (
                "Bullish trend confirmed by "
                "EMA 20 above EMA 50, with "
                "price above EMA 20 and RSI "
                "showing bullish momentum."
            )

        }


    # =====================================================
    # SELL SIGNAL
    # =====================================================

    if (

        trend == "SELL"

        and

        close < ema_20

        and

        rsi >= 30

        and

        rsi <= 50

    ):

        entry = close

        stop_loss = close + (
            atr * 1.5
        )

        take_profit = close - (
            atr * 2.0
        )


        confidence = 70


        if rsi <= 45:

            confidence += 10


        return {

            "pair": pair,

            "timeframe": timeframe,

            "signal": "SELL",

            "entry": format_price(entry),

            "take_profit": format_price(
                take_profit
            ),

            "stop_loss": format_price(
                stop_loss
            ),

            "trend": "SELL",

            "rsi": round(rsi, 2),

            "confidence": confidence,

            "reason": (
                "Bearish trend confirmed by "
                "EMA 20 below EMA 50, with "
                "price below EMA 20 and RSI "
                "showing bearish momentum."
            )

        }


    # =====================================================
    # NO TRADE
    # =====================================================

    if trend == "BUY":

        reason = (
            "Bullish trend detected, but the "
            "entry conditions are not strong "
            "enough yet."
        )

    elif trend == "SELL":

        reason = (
            "Bearish trend detected, but the "
            "entry conditions are not strong "
            "enough yet."
        )

    else:

        reason = (
            "Market direction is unclear. "
            "Waiting for a stronger setup."
        )


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

        "reason": reason

}
