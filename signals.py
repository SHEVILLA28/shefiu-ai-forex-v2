import os
import time
import threading

import requests
import pandas as pd

from news_filter import get_news_status


# =========================================================
# TWELVE DATA SETTINGS
# =========================================================

API_KEY = os.getenv("TWELVE_DATA_API_KEY")

BASE_URL = "https://api.twelvedata.com/time_series"

MIN_CANDLES = 100


# =========================================================
# REQUEST PROTECTION
# =========================================================

API_REQUEST_LOCK = threading.Lock()

LAST_API_REQUEST_TIME = 0

MIN_REQUEST_INTERVAL = 8


# =========================================================
# TIMEFRAME CONVERSION
# =========================================================

TIMEFRAME_MAP = {
    "1M": "1min",
    "2M": "1min",
    "3M": "1min",
    "5M": "5min",
}


# =========================================================
# FORMAT SYMBOL
# =========================================================

def format_symbol(pair):

    return pair.upper().replace(" ", "")


# =========================================================
# WAIT FOR API RATE LIMIT
# =========================================================

def wait_for_rate_limit():

    global LAST_API_REQUEST_TIME

    with API_REQUEST_LOCK:

        current_time = time.time()

        time_since_last_request = (
            current_time - LAST_API_REQUEST_TIME
        )

        if LAST_API_REQUEST_TIME > 0:

            remaining_time = (
                MIN_REQUEST_INTERVAL
                - time_since_last_request
            )

            if remaining_time > 0:

                print(
                    f"Rate limit protection: waiting "
                    f"{remaining_time:.1f} seconds..."
                )

                time.sleep(remaining_time)

        LAST_API_REQUEST_TIME = time.time()


# =========================================================
# GET MARKET DATA FROM TWELVE DATA
# =========================================================

def get_market_data(pair, timeframe):

    if not API_KEY:

        error_message = (
            "TWELVE_DATA_API_KEY is not configured in Render."
        )

        print(error_message)

        return None, error_message


    interval = TIMEFRAME_MAP.get(
        timeframe,
        "5min"
    )

    symbol = format_symbol(pair)


    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": 150,
        "apikey": API_KEY,
        "format": "JSON",
    }


    try:

        wait_for_rate_limit()

        print(
            f"Requesting Twelve Data market data: "
            f"{symbol} | {interval}"
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


    except Exception as e:

        error_message = (
            f"Twelve Data market request error: {e}"
        )

        print(error_message)

        return None, error_message


    # =====================================================
    # CHECK API RESPONSE
    # =====================================================

    if data.get("status") == "error":

        error_message = (
            data.get("message")
            or "Twelve Data did not return market data."
        )

        print(
            "Twelve Data error:",
            data
        )

        return None, str(error_message)


    values = data.get("values")


    if not values:

        error_message = (
            data.get("message")
            or "Twelve Data returned no market candles."
        )

        print(
            "Twelve Data response:",
            data
        )

        return None, error_message


    # =====================================================
    # PROCESS MARKET DATA
    # =====================================================

    try:

        rows = []

        for candle in values:

            if not isinstance(candle, dict):

                continue


            rows.append({
                "datetime": candle.get("datetime"),
                "open": candle.get("open"),
                "high": candle.get("high"),
                "low": candle.get("low"),
                "close": candle.get("close"),
            })


        df = pd.DataFrame(rows)


        if df.empty:

            return None, (
                "Twelve Data returned empty candle data."
            )


        df["datetime"] = pd.to_datetime(
            df["datetime"],
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
        ).reset_index(
            drop=True
        )


        print(
            f"Twelve Data candles received: {len(df)}"
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
            f"Twelve Data data processing error: {e}"
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


    return 100 - (
        100 / (1 + rs)
    )


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

    high_low = (
        df["high"] - df["low"]
    )


    high_close = (
        df["high"]
        - df["close"].shift()
    ).abs()


    low_close = (
        df["low"]
        - df["close"].shift()
    ).abs()


    true_range = pd.concat(
        [
            high_low,
            high_close,
            low_close
        ],
        axis=1
    ).max(
        axis=1
    )


    return true_range.rolling(
        window=period
    ).mean()


# =========================================================
# SUPPORT AND RESISTANCE
# =========================================================

def calculate_support_resistance(df, lookback=50):

    recent_data = df.tail(
        lookback
    )


    support = recent_data["low"].min()

    resistance = recent_data["high"].max()


    return (
        float(support),
        float(resistance)
    )


# =========================================================
# FORMAT PRICE
# =========================================================

def format_price(price):

    if pd.isna(price):

        return "N/A"


    if price >= 100:

        return round(
            float(price),
            3
        )


    return round(
        float(price),
        5
    )


# =========================================================
# GET SIGNAL
# =========================================================

def get_signal(pair, timeframe="5M"):


    # =====================================================
    # ECONOMIC NEWS FILTER
    # =====================================================

    try:

        news_info = get_news_status(pair)


    except Exception as e:

        print(
            f"News filter check failed: {e}"
        )

        news_info = {
            "blocked": False,
            "status": "UNKNOWN",
            "message": (
                "Economic news filter could not be checked."
            ),
            "currency": None,
            "event": None
        }


    # =====================================================
    # BLOCK TRADE IF HIGH-IMPACT NEWS EXISTS
    # =====================================================

    if news_info.get("blocked", False):

        print(
            f"Trading paused for {pair}: "
            f"high-impact news detected."
        )

        return {
            "pair": pair,
            "timeframe": timeframe,
            "signal": "NO TRADE",
            "entry": "N/A",
            "take_profit": "N/A",
            "stop_loss": "N/A",
            "support": "N/A",
            "resistance": "N/A",
            "trend": "WAIT",
            "rsi": "N/A",
            "confidence": 0,
            "news_status": news_info.get("status", "BLOCKED"),
            "news_message": news_info.get(
                "message",
                "High-impact economic news detected."
            ),
            "reason": news_info.get(
                "message",
                "High-impact economic news is affecting "
                "this Forex pair. Trading is temporarily paused."
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
            "support": "N/A",
            "resistance": "N/A",
            "trend": "WAIT",
            "rsi": "N/A",
            "confidence": 0,
            "news_status": news_info.get("status", "UNKNOWN"),
            "news_message": news_info.get(
                "message",
                "Economic news status unavailable."
            ),
            "reason": error_message
        }


    try:

        # =================================================
        # INDICATORS
        # =================================================

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


        # =================================================
        # SUPPORT AND RESISTANCE
        # =================================================

        support, resistance = (
            calculate_support_resistance(
                df,
                50
            )
        )


        latest = df.iloc[-1]

        previous = df.iloc[-2]


        close = float(latest["close"])

        previous_close = float(
            previous["close"]
        )

        ema_20 = float(latest["ema_20"])

        ema_50 = float(latest["ema_50"])

        rsi = float(latest["rsi"])

        atr = float(latest["atr"])


    except Exception as e:

        return {
            "pair": pair,
            "timeframe": timeframe,
            "signal": "NO TRADE",
            "entry": "N/A",
            "take_profit": "N/A",
            "stop_loss": "N/A",
            "support": "N/A",
            "resistance": "N/A",
            "trend": "WAIT",
            "rsi": "N/A",
            "confidence": 0,
            "news_status": news_info.get("status", "UNKNOWN"),
            "news_message": news_info.get(
                "message",
                "Economic news status unavailable."
            ),
            "reason": f"Indicator calculation error: {e}"
        }


    # =====================================================
    # CHECK INDICATORS
    # =====================================================

    if pd.isna(rsi) or pd.isna(atr):

        return {
            "pair": pair,
            "timeframe": timeframe,
            "signal": "NO TRADE",
            "entry": "N/A",
            "take_profit": "N/A",
            "stop_loss": "N/A",
            "support": format_price(support),
            "resistance": format_price(resistance),
            "trend": "WAIT",
            "rsi": "N/A",
            "confidence": 0,
            "news_status": news_info.get("status", "UNKNOWN"),
            "news_message": news_info.get(
                "message",
                "Economic news status unavailable."
            ),
            "reason": (
                "Not enough data to calculate "
                "technical indicators."
            )
        }


    # =====================================================
    # DETERMINE MAIN TREND
    # =====================================================

    if ema_20 > ema_50:

        trend = "BUY"

    elif ema_20 < ema_50:

        trend = "SELL"

    else:

        trend = "WAIT"


    # =====================================================
    # SUPPORT / RESISTANCE DISTANCE
    # =====================================================

    distance_to_support = (
        close - support
    )


    distance_to_resistance = (
        resistance - close
    )


    # =====================================================
    # BUY CONDITIONS
    # =====================================================

    bullish_price = (
        close > ema_20
    )


    bullish_momentum = (
        close > previous_close
    )


    bullish_rsi = (
        rsi >= 45
        and rsi <= 70
    )


    buy_safe_from_resistance = (
        distance_to_resistance >= atr * 1.0
    )


    if (
        trend == "BUY"
        and bullish_price
        and bullish_momentum
        and bullish_rsi
        and buy_safe_from_resistance
    ):

        entry = close


        # STOP LOSS REMAINS ATR x 1.5

        stop_loss = (
            close - (atr * 1.5)
        )


        # TAKE PROFIT INCREASED TO ATR x 2.5

        take_profit = (
            close + (atr * 2.5)
        )


        confidence = 70


        if rsi >= 50:

            confidence += 10


        if rsi >= 55:

            confidence += 5


        confidence += 5


        return {
            "pair": pair,
            "timeframe": timeframe,
            "signal": "BUY",
            "entry": format_price(entry),
            "take_profit": format_price(take_profit),
            "stop_loss": format_price(stop_loss),
            "support": format_price(support),
            "resistance": format_price(resistance),
            "trend": "BUY",
            "rsi": round(rsi, 2),
            "confidence": confidence,
            "news_status": news_info.get("status", "UNKNOWN"),
            "news_message": news_info.get(
                "message",
                "Economic news status unavailable."
            ),
            "reason": (
                "Bullish trend confirmed by EMA 20 "
                "above EMA 50, price above EMA 20, "
                "positive momentum, bullish RSI and "
                "safe distance from resistance."
            )
        }


    # =====================================================
    # SELL CONDITIONS
    # =====================================================

    bearish_price = (
        close < ema_20
    )


    bearish_momentum = (
        close < previous_close
    )


    bearish_rsi = (
        rsi >= 30
        and rsi <= 55
    )


    sell_safe_from_support = (
        distance_to_support >= atr * 1.0
    )


    if (
        trend == "SELL"
        and bearish_price
        and bearish_momentum
        and bearish_rsi
        and sell_safe_from_support
    ):

        entry = close


        # STOP LOSS REMAINS ATR x 1.5

        stop_loss = (
            close + (atr * 1.5)
        )


        # TAKE PROFIT INCREASED TO ATR x 2.5

        take_profit = (
            close - (atr * 2.5)
        )


        confidence = 70


        if rsi <= 50:

            confidence += 10


        if rsi <= 45:

            confidence += 5


        confidence += 5


        return {
            "pair": pair,
            "timeframe": timeframe,
            "signal": "SELL",
            "entry": format_price(entry),
            "take_profit": format_price(take_profit),
            "stop_loss": format_price(stop_loss),
            "support": format_price(support),
            "resistance": format_price(resistance),
            "trend": "SELL",
            "rsi": round(rsi, 2),
            "confidence": confidence,
            "news_status": news_info.get("status", "UNKNOWN"),
            "news_message": news_info.get(
                "message",
                "Economic news status unavailable."
            ),
            "reason": (
                "Bearish trend confirmed by EMA 20 "
                "below EMA 50, price below EMA 20, "
                "negative momentum, bearish RSI and "
                "safe distance from support."
            )
        }


    # =====================================================
    # NO TRADE REASON
    # =====================================================

    if trend == "BUY" and not buy_safe_from_resistance:

        reason = (
            "BUY setup detected, but price is too "
            "close to resistance. Waiting for a safer "
            "entry."
        )


    elif trend == "SELL" and not sell_safe_from_support:

        reason = (
            "SELL setup detected, but price is too "
            "close to support. Waiting for a safer "
            "entry."
        )


    elif trend == "BUY":

        reason = (
            "Bullish trend detected, but price, "
            "momentum and RSI confirmation are not "
            "all strong enough yet."
        )


    elif trend == "SELL":

        reason = (
            "Bearish trend detected, but price, "
            "momentum and RSI confirmation are not "
            "all strong enough yet."
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
        "support": format_price(support),
        "resistance": format_price(resistance),
        "trend": trend,
        "rsi": round(rsi, 2),
        "confidence": 0,
        "news_status": news_info.get("status", "UNKNOWN"),
        "news_message": news_info.get(
            "message",
            "Economic news status unavailable."
        ),
        "reason": reason
        }
