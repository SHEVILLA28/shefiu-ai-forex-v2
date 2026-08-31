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

            or

            data.get("message")

            or

            "FCSAPI did not return market data."

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

            candles = response_data.values()

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

                "datetime": candle.get(
                    "tm"
                ),

                "timestamp": candle.get(
                    "t"
                ),

                "open": candle.get(
                    "o"
                ),

                "high": candle.get(
                    "h"
                ),

                "low": candle.get(
                    "l"
                ),

                "close": candle.get(
                    "c"
                ),

            })


        df = pd.DataFrame(rows)


        if df.empty:

            return None, (
                "FCSAPI returned empty candle data."
            )


        # =================================================
        # DATETIME
        # =================================================

        if "datetime" in df.columns:

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
