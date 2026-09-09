import pandas as pd
from datetime import datetime, timezone

from news_filter import get_news_status
from market_data import get_market_data


# =========================================================
# SHEFIU AI FOREX V2
# SIGNAL ENGINE - MT5 / METAAPI MARKET DATA
# =========================================================

MIN_CANDLES = 100
HIGHER_TIMEFRAME = "15M"


def is_rate_limit_error(message):
    """Compatibility helper for older callers.

    The market-data provider is MetaAPI/MT5.
    """
    text = str(message or "").lower()
    return (
        "metaapi" in text
        and ("rate" in text or "too many" in text)
    )


def is_market_open():
    now = datetime.now(timezone.utc)
    weekday = now.weekday()
    hour = now.hour

    if weekday == 5:
        return False

    if weekday == 6 and hour < 22:
        return False

    if weekday == 4 and hour >= 22:
        return False

    return True


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
    # 5-minute candles when enough source candles are available.
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
