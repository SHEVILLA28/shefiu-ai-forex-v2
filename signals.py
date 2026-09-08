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
# TIMEFRAME SETTINGS
# =========================================================

# Timeframes requested directly from Twelve Data.
DIRECT_TIMEFRAME_MAP = {
    "1M": "1min",
    "5M": "5min",
    "15M": "15min",
    "30M": "30min",
    "1H": "1h",
}

# Timeframes built locally from 1-minute candles.
# Pandas resample rules are used by resample_market_data().
RESAMPLED_TIMEFRAMES = {
    "2M": "2min",
    "3M": "3min",
}


# =========================================================
# TWELVE DATA REQUEST PROTECTION + CACHE
# =========================================================

API_REQUEST_LOCK = threading.Lock()

LAST_API_REQUEST_TIME = 0.0

# Keep requests deliberately slow enough for an automatic multi-pair scan.
MIN_REQUEST_INTERVAL = max(1.0, float(
    os.getenv("TWELVE_DATA_MIN_REQUEST_INTERVAL", "25")
))

# Cache successful responses so the same candles are not requested again
# unnecessarily during a scan or by another bot action.
DATA_CACHE = {}

CACHE_TTL_SECONDS = {
    "1min": 50,
    "2min": 110,
    "3min": 170,
    "5min": 300,
    "15min": 720,
    "30min": 1440,
    "1h": 3000,
}

# A 429 means the provider has already refused the account.  Do not keep
# hammering the API pair-by-pair.  Pause all new Twelve Data requests first.
RATE_LIMIT_BLOCK_UNTIL = 0.0
RATE_LIMIT_BLOCK_SECONDS = max(60, int(
    os.getenv("TWELVE_DATA_RATE_LIMIT_COOLDOWN", "900")
))


def is_rate_limit_error(message):
    """Return True when a scan should stop instead of hammering Twelve Data."""
    text = str(message or "").lower()
    return "rate limit" in text or "cooldown" in text or "too many" in text


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


    # Sunday before market opens
    if weekday == 6 and hour < 22:
        return False


    # Friday after market closes
    if weekday == 4 and hour >= 22:
        return False


    return True


# =========================================================
# CACHE HELPERS
# =========================================================

def _cache_key(symbol, interval, outputsize):

    return (symbol, interval, int(outputsize))


def _cache_ttl(interval):

    return CACHE_TTL_SECONDS.get(interval, 60)


def _get_cached_data(symbol, interval, outputsize):

    key = _cache_key(symbol, interval, outputsize)
    cached = DATA_CACHE.get(key)

    if not cached:
        return None

    cached_time, cached_data = cached

    age = time.monotonic() - cached_time

    if age < _cache_ttl(interval):
        print(
            f"Using cached market data: {symbol} | {interval} "
            f"({age:.0f}s old)"
        )
        return cached_data

    DATA_CACHE.pop(key, None)
    return None


# =========================================================
# WAIT FOR API SPACING
# =========================================================

def wait_for_rate_limit():

    global LAST_API_REQUEST_TIME

    current_time = time.monotonic()

    if LAST_API_REQUEST_TIME > 0:

        elapsed = current_time - LAST_API_REQUEST_TIME
        remaining = MIN_REQUEST_INTERVAL - elapsed

        if remaining > 0:

            print(
                f"Rate limit protection: waiting "
                f"{remaining:.1f} seconds..."
            )

            time.sleep(remaining)

    LAST_API_REQUEST_TIME = time.monotonic()


# =========================================================
# REQUEST DATA FROM TWELVE DATA
# =========================================================

def request_twelve_data(
    pair,
    interval,
    outputsize=150
):

    global RATE_LIMIT_BLOCK_UNTIL

    if not API_KEY:

        error_message = (
            "TWELVE_DATA_API_KEY is not configured "
            "in Render."
        )

        print(error_message)

        return None, error_message


    symbol = format_symbol(pair)

    cached_data = _get_cached_data(
        symbol,
        interval,
        outputsize
    )

    if cached_data is not None:
        return cached_data, None


    # If Twelve Data has already returned 429, stop every following pair
    # from immediately making another request.
    remaining_block = RATE_LIMIT_BLOCK_UNTIL - time.monotonic()

    if remaining_block > 0:

        error_message = (
            "Twelve Data rate limit cooldown is active. "
            f"Waiting about {int(remaining_block)} seconds before "
            "requesting market data again."
        )

        print(error_message)

        return None, error_message


    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": outputsize,
        "apikey": API_KEY,
        "format": "JSON"
    }


    with API_REQUEST_LOCK:

        # Another scanner action may have filled the cache while this call
        # was waiting for the lock.
        cached_data = _get_cached_data(
            symbol,
            interval,
            outputsize
        )

        if cached_data is not None:
            return cached_data, None


        remaining_block = RATE_LIMIT_BLOCK_UNTIL - time.monotonic()

        if remaining_block > 0:

            error_message = (
                "Twelve Data rate limit cooldown is active. "
                f"Waiting about {int(remaining_block)} seconds before "
                "requesting market data again."
            )

            print(error_message)

            return None, error_message


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
                    "Twelve Data returned an invalid response."
                )


        except requests.RequestException as e:

            error_message = f"Market request error: {e}"
            print(error_message)
            return None, error_message


        except Exception as e:

            error_message = f"Unexpected market error: {e}"
            print(error_message)
            return None, error_message


        # Rate limit: pause the whole provider, not just the current pair.
        if response.status_code == 429:

            RATE_LIMIT_BLOCK_UNTIL = (
                time.monotonic() + RATE_LIMIT_BLOCK_SECONDS
            )

            error_message = (
                data.get("message")
                or "Twelve Data rate limit reached."
            )

            print("TWELVE DATA RATE LIMIT REACHED")
            print(
                f"Pausing all Twelve Data requests for "
                f"{RATE_LIMIT_BLOCK_SECONDS} seconds."
            )

            return None, error_message


        if response.status_code >= 400:

            error_message = (
                data.get("message")
                or f"Twelve Data HTTP error {response.status_code}."
            )

            print("Twelve Data error:", data)

            return None, str(error_message)


        if isinstance(data, dict) and data.get("status") == "error":

            error_message = (
                data.get("message")
                or "Twelve Data did not return data."
            )

            print("Twelve Data error:", data)

            return None, str(error_message)


        DATA_CACHE[
            _cache_key(symbol, interval, outputsize)
        ] = (
            time.monotonic(),
            data
        )

        return data, None


# =========================================================
# CONVERT API DATA TO DATAFRAME
# =========================================================

def convert_to_dataframe(data):

    values = data.get("values")


    if not values:

        return None, (
            data.get("message")
            or "No market candles returned."
        )


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

                "close": candle.get("close")

            })


        df = pd.DataFrame(rows)


        if df.empty:

            return None, (
                "Market data is empty."
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


        return df, None


    except Exception as e:

        return None, (
            f"Data processing error: {e}"
        )


# =========================================================
# RESAMPLE 1-MINUTE DATA
# =========================================================

def resample_market_data(
    df,
    timeframe
):

    if timeframe not in RESAMPLED_TIMEFRAMES:

        return df


    rule = RESAMPLED_TIMEFRAMES[
        timeframe
    ]


    try:

        data = df.copy()


        data = data.set_index(
            "datetime"
        )


        resampled = data.resample(
            rule
        ).agg({

            "open": "first",

            "high": "max",

            "low": "min",

            "close": "last"

        })


        resampled = resampled.dropna().reset_index()


        print(
            f"Resampled to {timeframe}: "
            f"{len(resampled)} candles"
        )


        return resampled


    except Exception as e:

        print(
            f"Resampling error: {e}"
        )

        return None


# =========================================================
# GET MARKET DATA
# =========================================================

def get_market_data(pair, timeframe):


    # =====================================================
    # 2M / 3M
    # Get enough 1-minute candles for resampling
    # =====================================================

    if timeframe in RESAMPLED_TIMEFRAMES:

        interval = "1min"

        # Need more than 100 one-minute candles
        # so resampled candles can reach MIN_CANDLES
        outputsize = 350


        data, error_message = (
            request_twelve_data(
                pair,
                interval,
                outputsize
            )
        )


        if data is None:

            return None, error_message


        df, error_message = (
            convert_to_dataframe(data)
        )


        if df is None:

            return None, error_message


        df = resample_market_data(
            df,
            timeframe
        )


        if df is None:

            return None, (
                f"Could not create {timeframe} candles."
            )


    # =====================================================
    # DIRECT TIMEFRAMES
    # =====================================================

    else:

        interval = DIRECT_TIMEFRAME_MAP.get(
            timeframe,
            "5min"
        )


        # Request enough 5-minute history to derive the 15-minute
        # confirmation locally, avoiding a second API call per pair.
        outputsize = 300 if timeframe == "5M" else 150

        data, error_message = (
            request_twelve_data(
                pair,
                interval,
                outputsize
            )
        )


        if data is None:

            return None, error_message


        df, error_message = (
            convert_to_dataframe(data)
        )


        if df is None:

            return None, error_message


    # =====================================================
    # CHECK CANDLE COUNT
    # =====================================================

    print(
        f"Candles received for {timeframe}: "
        f"{len(df)}"
    )


    if len(df) < MIN_CANDLES:

        return None, (

            f"Not enough candles for {timeframe}. "
            f"Received {len(df)}, "
            f"need {MIN_CANDLES}."

        )


    return df, None


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
# CALCULATE MACD
# =========================================================

def calculate_macd(
    series,
    fast=12,
    slow=26,
    signal=9
):

    fast_ema = calculate_ema(
        series,
        fast
    )


    slow_ema = calculate_ema(
        series,
        slow
    )


    macd_line = (
        fast_ema
        - slow_ema
    )


    signal_line = calculate_ema(
        macd_line,
        signal
    )


    histogram = (
        macd_line
        - signal_line
    )


    return (
        macd_line,
        signal_line,
        histogram
    )


# =========================================================
# CALCULATE BOLLINGER BANDS
# =========================================================

def calculate_bollinger_bands(
    series,
    period=20,
    std_multiplier=2
):

    middle_band = series.rolling(
        window=period
    ).mean()


    rolling_std = series.rolling(
        window=period
    ).std()


    upper_band = (

        middle_band
        + (
            rolling_std
            * std_multiplier
        )

    )


    lower_band = (

        middle_band
        - (
            rolling_std
            * std_multiplier
        )

    )


    return (
        middle_band,
        upper_band,
        lower_band
    )


# =========================================================
# GET TREND FROM DATAFRAME
# =========================================================

def get_trend_from_df(df):

    data = df.copy()


    data["ema_20"] = calculate_ema(
        data["close"],
        20
    )


    data["ema_50"] = calculate_ema(
        data["close"],
        50
    )


    latest = data.iloc[-1]


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

def get_higher_timeframe_trend(pair, source_df=None, source_timeframe=None):

    # For the normal 5M scanner, build the 15M confirmation from the same
    # 5-minute candles. This removes one Twelve Data request for every pair.
    if (
        source_df is not None
        and source_timeframe == "5M"
        and len(source_df) >= 150
    ):
        try:
            data = source_df.copy().set_index("datetime")
            higher_df = (
                data.resample("15min")
                .agg({
                    "open": "first",
                    "high": "max",
                    "low": "min",
                    "close": "last"
                })
                .dropna()
                .reset_index()
            )

            if len(higher_df) >= 50:
                trend = get_trend_from_df(higher_df)
                print(
                    f"Higher timeframe trend for {pair}: {trend} "
                    "(derived from cached 5M candles)"
                )
                return trend

        except Exception as e:
            print(f"Higher timeframe resample error: {e}")


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

        trend = get_trend_from_df(
            df
        )


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


    bullish_engulfing = (

        previous_close < previous_open

        and current_close > current_open

        and current_open <= previous_close

        and current_close >= previous_open

    )


    bearish_engulfing = (

        previous_close > previous_open

        and current_close < current_open

        and current_open >= previous_close

        and current_close <= previous_open

    )


    hammer = (

        body > 0

        and lower_wick >= body * 2

        and upper_wick <= body * 1.5

        and current_close >= current_open

    )


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
    higher_trend="N/A",
    macd="N/A",
    macd_signal="N/A",
    macd_histogram="N/A",
    bb_middle="N/A",
    bb_upper="N/A",
    bb_lower="N/A"
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

        "macd": macd,

        "macd_signal": macd_signal,

        "macd_histogram": macd_histogram,

        "bb_middle": bb_middle,

        "bb_upper": bb_upper,

        "bb_lower": bb_lower,

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
    # MARKET CLOSED
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
    # NEWS FILTER
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

    if news_info.get("blocked", False):

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
    # GET MARKET DATA
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


        (
            df["macd"],
            df["macd_signal"],
            df["macd_histogram"]

        ) = calculate_macd(
            df["close"]
        )


        (
            df["bb_middle"],
            df["bb_upper"],
            df["bb_lower"]

        ) = calculate_bollinger_bands(
            df["close"]
        )


        support, resistance = (
            calculate_support_resistance(
                df,
                50
            )
        )


        candlestick = (
            get_candlestick_signal(df)
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


        macd = float(
            latest["macd"]
        )


        macd_signal = float(
            latest["macd_signal"]
        )


        macd_histogram = float(
            latest["macd_histogram"]
        )


        bb_middle = float(
            latest["bb_middle"]
        )


        bb_upper = float(
            latest["bb_upper"]
        )


        bb_lower = float(
            latest["bb_lower"]
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

    indicator_values = [

        rsi,
        atr,
        macd,
        macd_signal,
        macd_histogram,
        bb_middle,
        bb_upper,
        bb_lower

    ]


    if any(
        pd.isna(value)
        for value in indicator_values
    ):

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

    higher_trend = (
        get_higher_timeframe_trend(
            pair,
            source_df=df,
            source_timeframe=timeframe
        )
    )


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


    if (
        trend != "WAIT"
        and trend != higher_trend
    ):

        return create_no_trade_result(

            pair,

            timeframe,

            f"Timeframe conflict detected. "
            f"{timeframe} trend is {trend}, but "
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
    # MACD CONFIRMATION
    # =====================================================

    bullish_macd = (

        macd > macd_signal

        and macd_histogram > 0

    )


    bearish_macd = (

        macd < macd_signal

        and macd_histogram < 0

    )


    # =====================================================
    # BOLLINGER BAND SAFETY
    # =====================================================

    buy_bb_safe = (
        close < bb_upper
    )


    sell_bb_safe = (
        close > bb_lower
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

        distance_to_resistance
        >= atr * 1.0

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

        and bullish_macd

        and buy_bb_safe

        and buy_safe_from_resistance

        and bullish_candle

    ):


        entry = close


        stop_loss = (
            close - atr * 1.5
        )


        take_profit = (
            close + atr * 3.0
        )


        confidence = 85


        if rsi >= 50:

            confidence += 5


        if rsi >= 55:

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
                "STRONG BUY confirmed by trend, "
                "higher timeframe confirmation, RSI, "
                "MACD, support/resistance safety and "
                "bullish candlestick confirmation."
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

        distance_to_support
        >= atr * 1.0

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

        and bearish_macd

        and sell_bb_safe

        and sell_safe_from_support

        and bearish_candle

    ):


        entry = close


        stop_loss = (
            close + atr * 1.5
        )


        take_profit = (
            close - atr * 3.0
        )


        confidence = 85


        if rsi <= 50:

            confidence += 5


        if rsi <= 45:

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
                "STRONG SELL confirmed by trend, "
                "higher timeframe confirmation, RSI, "
                "MACD, support/resistance safety and "
                "bearish candlestick confirmation."
            )

        }


    # =====================================================
    # NO TRADE REASON
    # =====================================================

    if trend == "BUY" and not buy_safe_from_resistance:

        reason = (
            "BUY trend detected, but price is too "
            "close to resistance."
        )


    elif trend == "SELL" and not sell_safe_from_support:

        reason = (
            "SELL trend detected, but price is too "
            "close to support."
        )


    elif trend == "BUY" and not bullish_macd:

        reason = (
            "Bullish trend exists, but MACD has not "
            "confirmed bullish momentum yet."
        )


    elif trend == "SELL" and not bearish_macd:

        reason = (
            "Bearish trend exists, but MACD has not "
            "confirmed bearish momentum yet."
        )


    elif trend == "BUY" and not bullish_candle:

        reason = (
            f"Bullish trend exists, but no strong "
            f"bullish candlestick confirmation yet. "
            f"Pattern: {candlestick}."
        )


    elif trend == "SELL" and not bearish_candle:

        reason = (
            f"Bearish trend exists, but no strong "
            f"bearish candlestick confirmation yet. "
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
