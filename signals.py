import os
import time
import threading
from datetime import datetime, timezone

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

MIN_REQUEST_INTERVAL = 10


# =========================================================
# RATE LIMIT RETRY SETTINGS
# =========================================================

MAX_RATE_LIMIT_RETRIES = 2

RATE_LIMIT_WAIT_TIME = 60


# =========================================================
# TIMEFRAME CONVERSION
# =========================================================

TIMEFRAME_MAP = {

    "1M": "1min",

    "2M": "1min",

    "3M": "1min",

    "5M": "5min",

    "15M": "15min",

    "30M": "30min",

    "1H": "1h",

}


# =========================================================
# HIGHER TIMEFRAME SETTINGS
# =========================================================

HIGHER_TIMEFRAME = "15M"


# =========================================================
# FORMAT SYMBOL
# =========================================================

def format_symbol(pair):

    return pair.upper().replace(" ", "")


# =========================================================
# CHECK FOREX MARKET STATUS
# =========================================================

def is_market_open():

    now = datetime.now(timezone.utc)

    weekday = now.weekday()

    hour = now.hour


    # Saturday

    if weekday == 5:

        return False


    # Sunday before Forex market normally opens

    if weekday == 6 and hour < 22:

        return False


    # Friday after market normally closes

    if weekday == 4 and hour >= 22:

        return False


    return True


# =========================================================
# WAIT FOR API RATE LIMIT
# =========================================================

def wait_for_rate_limit():

    global LAST_API_REQUEST_TIME

    with API_REQUEST_LOCK:

        current_time = time.time()


        if LAST_API_REQUEST_TIME > 0:

            time_since_last_request = (
                current_time
                - LAST_API_REQUEST_TIME
            )


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

            "TWELVE_DATA_API_KEY is not configured "
            "in Render."

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


    # =====================================================
    # REQUEST WITH RETRY
    # =====================================================

    for attempt in range(
        MAX_RATE_LIMIT_RETRIES + 1
    ):


        try:

            wait_for_rate_limit()


            print(

                f"Requesting market data: "
                f"{symbol} | {interval}"

            )


            response = requests.get(

                BASE_URL,

                params=params,

                timeout=30

            )


            print(

                f"Twelve Data status: "
                f"{response.status_code}"

            )


            try:

                data = response.json()


            except Exception:

                return None, (

                    "Twelve Data returned "
                    "an invalid response."

                )


        except Exception as e:

            error_message = (

                f"Market request error: {e}"

            )

            print(error_message)

            return None, error_message


        # =================================================
        # RATE LIMIT
        # =================================================

        if response.status_code == 429:


            error_message = (

                data.get("message")

                or "Twelve Data rate limit reached."

            )


            print(
                "TWELVE DATA RATE LIMIT REACHED"
            )


            if attempt < MAX_RATE_LIMIT_RETRIES:


                print(

                    f"Waiting "
                    f"{RATE_LIMIT_WAIT_TIME} seconds..."

                )


                time.sleep(
                    RATE_LIMIT_WAIT_TIME
                )


                continue


            return None, error_message


        # =================================================
        # API ERROR
        # =================================================

        if data.get("status") == "error":


            error_message = (

                data.get("message")

                or "Twelve Data did not return data."

            )


            print(
                "Twelve Data error:",
                data
            )


            return None, str(error_message)


        break


    values = data.get("values")


    if not values:

        return None, (

            data.get("message")

            or "No market candles returned."

        )


    # =====================================================
    # PROCESS DATA
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

            return None, "Market data is empty."


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

            f"Candles received: "
            f"{len(df)}"

        )


        if len(df) < MIN_CANDLES:

            return None, (

                f"Not enough candles. "
                f"Received {len(df)}, "
                f"need {MIN_CANDLES}."

            )


        return df, None


    except Exception as e:

        return None, (

            f"Data processing error: {e}"

        )


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

        df["high"]
        - df["low"]

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

    ).max(axis=1)


    return true_range.rolling(
        window=period
    ).mean()


# =========================================================
# GET TREND FROM DATAFRAME
# =========================================================

def get_trend_from_df(df):


    df["ema_20"] = calculate_ema(

        df["close"],

        20

    )


    df["ema_50"] = calculate_ema(

        df["close"],

        50

    )


    latest = df.iloc[-1]


    ema_20 = float(
        latest["ema_20"]
    )


    ema_50 = float(
        latest["ema_50"]
    )


    if ema_20 > ema_50:

        return "BUY"


    elif ema_20 < ema_50:

        return "SELL"


    return "WAIT"


# =========================================================
# GET HIGHER TIMEFRAME TREND
# =========================================================

def get_higher_timeframe_trend(pair):


    df, error_message = get_market_data(

        pair,

        HIGHER_TIMEFRAME

    )


    if df is None:

        print(

            f"Higher timeframe check failed "
            f"for {pair}: {error_message}"

        )


        return "UNKNOWN"


    try:

        trend = get_trend_from_df(df)


        print(

            f"Higher timeframe trend for "
            f"{pair}: {trend}"

        )


        return trend


    except Exception as e:

        print(

            f"Higher timeframe trend error: {e}"

        )


        return "UNKNOWN"


# =========================================================
# CANDLESTICK PATTERN DETECTION
# =========================================================

def get_candlestick_signal(df):


    latest = df.iloc[-1]

    previous = df.iloc[-2]


    current_open = float(
        latest["open"]
    )

    current_high = float(
        latest["high"]
    )

    current_low = float(
        latest["low"]
    )

    current_close = float(
        latest["close"]
    )


    previous_open = float(
        previous["open"]
    )

    previous_close = float(
        previous["close"]
    )


    body = abs(

        current_close
        - current_open

    )


    candle_range = (

        current_high
        - current_low

    )


    if candle_range <= 0:

        return "NONE"


    lower_wick = (

        min(
            current_open,
            current_close
        )

        - current_low

    )


    upper_wick = (

        current_high

        - max(
            current_open,
            current_close
        )

    )


    # =====================================================
    # BULLISH ENGULFING
    # =====================================================

    bullish_engulfing = (

        previous_close < previous_open

        and current_close > current_open

        and current_open <= previous_close

        and current_close >= previous_open

    )


    # =====================================================
    # BEARISH ENGULFING
    # =====================================================

    bearish_engulfing = (

        previous_close > previous_open

        and current_close < current_open

        and current_open >= previous_close

        and current_close <= previous_open

    )


    # =====================================================
    # HAMMER
    # =====================================================

    hammer = (

        body > 0

        and lower_wick >= body * 2

        and upper_wick <= body * 1.5

        and current_close >= current_open

    )


    # =====================================================
    # SHOOTING STAR
    # =====================================================

    shooting_star = (

        body > 0

        and upper_wick >= body * 2

        and lower_wick <= body * 1.5

        and current_close <= current_open

    )


    if bullish_engulfing:

        return "BULLISH ENGULFING"


    elif bearish_engulfing:

        return "BEARISH ENGULFING"


    elif hammer:

        return "HAMMER"


    elif shooting_star:

        return "SHOOTING STAR"


    return "NONE"


# =========================================================
# SUPPORT AND RESISTANCE
# =========================================================

def calculate_support_resistance(
    df,
    lookback=50
):


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
# CREATE NO TRADE RESULT
# =========================================================

def create_no_trade_result(
    pair,
    timeframe,
    reason,
    news_info=None,
    support="N/A",
    resistance="N/A",
    trend="WAIT",
    rsi="N/A",
    candlestick="N/A",
    higher_trend="N/A"
):


    if news_info is None:

        news_info = {}


    return {

        "pair": pair,

        "timeframe": timeframe,

        "signal": "NO TRADE",

        "entry": "N/A",

        "take_profit": "N/A",

        "stop_loss": "N/A",

        "support": support,

        "resistance": resistance,

        "trend": trend,

        "higher_trend": higher_trend,

        "rsi": rsi,

        "candlestick": candlestick,

        "confidence": 0,

        "news_status": news_info.get(
            "status",
            "UNKNOWN"
        ),

        "news_message": news_info.get(
            "message",
            "Economic news status unavailable."
        ),

        "reason": reason

    }


# =========================================================
# GET SIGNAL
# =========================================================

def get_signal(
    pair,
    timeframe="5M"
):


    # =====================================================
    # MARKET CLOSED PROTECTION
    # =====================================================

    if not is_market_open():

        print(
            f"Forex market is closed for {pair}."
        )


        return create_no_trade_result(

            pair,

            timeframe,

            "Forex market is currently closed. "
            "Automatic trading is paused until "
            "the market reopens."

        )


    # =====================================================
    # ECONOMIC NEWS FILTER
    # =====================================================

    try:


        news_info = get_news_status(
            pair
        )


    except Exception as e:


        print(
            f"News filter check failed: {e}"
        )


        news_info = {

            "blocked": False,

            "status": "UNKNOWN",

            "message": (
                "Economic news filter could not "
                "be checked."
            )

        }


    # =====================================================
    # BLOCK HIGH IMPACT NEWS
    # =====================================================

    if news_info.get(
        "blocked",
        False
    ):


        print(
            f"Trading paused for {pair}: "
            f"high-impact news."
        )


        return create_no_trade_result(

            pair,

            timeframe,

            news_info.get(
                "message",
                "High-impact economic news detected."
            ),

            news_info=news_info

        )


    # =====================================================
    # GET MAIN TIMEFRAME DATA
    # =====================================================

    df, error_message = get_market_data(

        pair,

        timeframe

    )


    if df is None:


        return create_no_trade_result(

            pair,

            timeframe,

            error_message,

            news_info=news_info

        )


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
        # SUPPORT / RESISTANCE
        # =================================================

        support, resistance = (
            calculate_support_resistance(
                df,
                50
            )
        )


        # =================================================
        # CANDLESTICK
        # =================================================

        candlestick = get_candlestick_signal(
            df
        )


        latest = df.iloc[-1]

        previous = df.iloc[-2]


        close = float(
            latest["close"]
        )


        previous_close = float(
            previous["close"]
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


        return create_no_trade_result(

            pair,

            timeframe,

            f"Indicator calculation error: {e}",

            news_info=news_info

        )


    # =====================================================
    # CHECK INDICATORS
    # =====================================================

    if pd.isna(rsi) or pd.isna(atr):


        return create_no_trade_result(

            pair,

            timeframe,

            "Not enough data to calculate "
            "technical indicators.",

            news_info=news_info,

            support=format_price(support),

            resistance=format_price(resistance),

            candlestick=candlestick

        )


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
    # HIGHER TIMEFRAME CONFIRMATION
    # =====================================================

    higher_trend = get_higher_timeframe_trend(
        pair
    )


    # =====================================================
    # HIGHER TIMEFRAME MUST AGREE
    # =====================================================

    if higher_trend == "UNKNOWN":


        return create_no_trade_result(

            pair,

            timeframe,

            "Higher timeframe confirmation "
            "could not be checked. Waiting for "
            "safer market confirmation.",

            news_info=news_info,

            support=format_price(support),

            resistance=format_price(resistance),

            trend=trend,

            rsi=round(rsi, 2),

            candlestick=candlestick,

            higher_trend=higher_trend

        )


    if trend != "WAIT" and trend != higher_trend:


        return create_no_trade_result(

            pair,

            timeframe,

            f"Timeframe conflict detected. "
            f"5M trend is {trend}, but "
            f"{HIGHER_TIMEFRAME} trend is "
            f"{higher_trend}. Waiting for both "
            f"timeframes to agree.",

            news_info=news_info,

            support=format_price(support),

            resistance=format_price(resistance),

            trend=trend,

            rsi=round(rsi, 2),

            candlestick=candlestick,

            higher_trend=higher_trend

        )


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
    # CANDLE CONFIRMATION
    # =====================================================

    bullish_candle = (

        candlestick == "BULLISH ENGULFING"

        or candlestick == "HAMMER"

    )


    bearish_candle = (

        candlestick == "BEARISH ENGULFING"

        or candlestick == "SHOOTING STAR"

    )


    # =====================================================
    # BUY CONDITIONS
    # =====================================================

    bullish_price = close > ema_20


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


    # =====================================================
    # BUY SIGNAL
    # =====================================================

    if (

        trend == "BUY"

        and higher_trend == "BUY"

        and bullish_price

        and bullish_momentum

        and bullish_rsi

        and buy_safe_from_resistance

        and bullish_candle

    ):


        entry = close


        stop_loss = (
            close - (atr * 1.5)
        )


        take_profit = (
            close + (atr * 3.0)
        )


        confidence = 70


        # Higher timeframe confirmation

        confidence += 10


        if rsi >= 50:

            confidence += 5


        if rsi >= 55:

            confidence += 5


        confidence += 5


        confidence = min(
            confidence,
            95
        )


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

            "support": format_price(
                support
            ),

            "resistance": format_price(
                resistance
            ),

            "trend": trend,

            "higher_trend": higher_trend,

            "rsi": round(rsi, 2),

            "candlestick": candlestick,

            "confidence": confidence,

            "news_status": news_info.get(
                "status",
                "UNKNOWN"
            ),

            "news_message": news_info.get(
                "message",
                "Economic news status unavailable."
            ),

            "reason": (

                "STRONG BUY confirmed by 5M and "
                f"{HIGHER_TIMEFRAME} EMA trend, "
                "price momentum, RSI, support and "
                "resistance safety, and bullish "
                f"candlestick: {candlestick}."

            )

        }


    # =====================================================
    # SELL CONDITIONS
    # =====================================================

    bearish_price = close < ema_20


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


    # =====================================================
    # SELL SIGNAL
    # =====================================================

    if (

        trend == "SELL"

        and higher_trend == "SELL"

        and bearish_price

        and bearish_momentum

        and bearish_rsi

        and sell_safe_from_support

        and bearish_candle

    ):


        entry = close


        stop_loss = (
            close + (atr * 1.5)
        )


        take_profit = (
            close - (atr * 3.0)
        )


        confidence = 70


        # Higher timeframe confirmation

        confidence += 10


        if rsi <= 50:

            confidence += 5


        if rsi <= 45:

            confidence += 5


        confidence += 5


        confidence = min(
            confidence,
            95
        )


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

            "support": format_price(
                support
            ),

            "resistance": format_price(
                resistance
            ),

            "trend": trend,

            "higher_trend": higher_trend,

            "rsi": round(rsi, 2),

            "candlestick": candlestick,

            "confidence": confidence,

            "news_status": news_info.get(
                "status",
                "UNKNOWN"
            ),

            "news_message": news_info.get(
                "message",
                "Economic news status unavailable."
            ),

            "reason": (

                "STRONG SELL confirmed by 5M and "
                f"{HIGHER_TIMEFRAME} EMA trend, "
                "price momentum, RSI, support and "
                "resistance safety, and bearish "
                f"candlestick: {candlestick}."

            )

        }


    # =====================================================
    # NO TRADE REASON
    # =====================================================

    if trend == "BUY" and not buy_safe_from_resistance:


        reason = (

            "BUY trend detected, but price is too "
            "close to resistance. Waiting for a "
            "safer entry."

        )


    elif trend == "SELL" and not sell_safe_from_support:


        reason = (

            "SELL trend detected, but price is too "
            "close to support. Waiting for a "
            "safer entry."

        )


    elif trend == "BUY" and not bullish_candle:


        reason = (

            "Bullish trend confirmed, but no strong "
            "bullish candlestick confirmation yet. "
            f"Pattern: {candlestick}."

        )


    elif trend == "SELL" and not bearish_candle:


        reason = (

            "Bearish trend confirmed, but no strong "
            "bearish candlestick confirmation yet. "
            f"Pattern: {candlestick}."

        )


    elif trend == "BUY":


        reason = (

            "Bullish trend exists, but not all BUY "
            "conditions are strong enough yet."

        )


    elif trend == "SELL":


        reason = (

            "Bearish trend exists, but not all SELL "
            "conditions are strong enough yet."

        )


    else:


        reason = (

            "Market direction is unclear. "
            "Waiting for a stronger setup."

        )


    # =====================================================
    # RETURN NO TRADE
    # =====================================================

    return create_no_trade_result(

        pair,

        timeframe,

        reason,

        news_info=news_info,

        support=format_price(support),

        resistance=format_price(resistance),

        trend=trend,

        rsi=round(rsi, 2),

        candlestick=candlestick,

        higher_trend=higher_trend

    )
