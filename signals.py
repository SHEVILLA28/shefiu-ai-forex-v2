import os
import requests
from datetime import datetime, timezone

API_KEY = os.getenv("TWELVE_DATA_API_KEY")


def calculate_ema(values, period):
    if len(values) < period:
        return None

    ema = sum(values[:period]) / period
    multiplier = 2 / (period + 1)

    for price in values[period:]:
        ema = (price - ema) * multiplier + ema

    return ema


def calculate_rsi(values, period=14):
    if len(values) <= period:
        return None

    gains = []
    losses = []

    for i in range(1, len(values)):
        change = values[i] - values[i - 1]

        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        avg_gain = ((avg_gain * (period - 1)) + gains[i]) / period
        avg_loss = ((avg_loss * (period - 1)) + losses[i]) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def calculate_macd(values):
    ema12 = calculate_ema(values, 12)
    ema26 = calculate_ema(values, 26)

    if ema12 is None or ema26 is None:
        return None, None

    macd_line = ema12 - ema26

    # Approximation of MACD signal line using recent MACD values
    macd_values = []

    for i in range(26, len(values) + 1):
        subset = values[:i]

        e12 = calculate_ema(subset, 12)
        e26 = calculate_ema(subset, 26)

        if e12 is not None and e26 is not None:
            macd_values.append(e12 - e26)

    if len(macd_values) < 9:
        return macd_line, None

    signal_line = calculate_ema(macd_values, 9)

    return macd_line, signal_line


def get_signal(pair):

    if not API_KEY:
        raise RuntimeError("TWELVE_DATA_API_KEY is missing")

    # Normalize symbols
    symbol = pair.replace("/", "")

    if symbol == "USDCAD":
        symbol = "USDCAD"

    if symbol == "XAUUSD":
        symbol = "XAUUSD"

    url = "https://api.twelvedata.com/time_series"

    params = {
        "symbol": symbol,
        "interval": "5min",
        "outputsize": 150,
        "apikey": API_KEY
    }

    response = requests.get(
        url,
        params=params,
        timeout=15
    )

    response.raise_for_status()

    data = response.json()

    if data.get("status") == "error":
        raise RuntimeError(
            data.get("message", "Twelve Data error")
        )

    values = data.get("values", [])

    # No market data
    if not values:
        return None

    # Need enough candles
    if len(values) < 80:
        return None

    values = list(reversed(values))

    closes = []
    highs = []
    lows = []

    for candle in values:
        try:
            closes.append(float(candle["close"]))
            highs.append(float(candle["high"]))
            lows.append(float(candle["low"]))
        except (KeyError, ValueError, TypeError):
            continue

    if len(closes) < 80:
        return None

    # --------------------------------------------------
    # CHECK MARKET DATA FRESHNESS
    # --------------------------------------------------

    latest_time = values[-1].get("datetime")

    market_closed = False

    if latest_time:
        try:
            candle_time = datetime.strptime(
                latest_time,
                "%Y-%m-%d %H:%M:%S"
            )

            candle_time = candle_time.replace(tzinfo=timezone.utc)

            now = datetime.now(timezone.utc)

            age_minutes = (
                now - candle_time
            ).total_seconds() / 60

            # Data older than 30 minutes = do not trade
            if age_minutes > 30:
                market_closed = True

        except Exception:
            pass

    if market_closed:
        return {
            "pair": pair,
            "signal": "NO TRADE",
            "entry": None,
            "take_profit": None,
            "stop_loss": None,
            "trend": "MARKET CLOSED",
            "rsi": 0,
            "ema50": None,
            "macd": None,
            "macd_signal": None,
            "support": None,
            "resistance": None,
            "confidence": 0,
            "reason": "Market closed or market data is stale"
        }

    # --------------------------------------------------
    # INDICATORS
    # --------------------------------------------------

    price = closes[-1]

    ema50 = calculate_ema(closes, 50)
    ema12 = calculate_ema(closes, 12)
    ema26 = calculate_ema(closes, 26)

    rsi = calculate_rsi(closes, 14)

    macd, macd_signal = calculate_macd(closes)

    if (
        ema50 is None
        or ema12 is None
        or ema26 is None
        or rsi is None
        or macd is None
        or macd_signal is None
    ):
        return None

    # --------------------------------------------------
    # SUPPORT / RESISTANCE
    # --------------------------------------------------

    lookback = 50

    recent_highs = highs[-lookback:]
    recent_lows = lows[-lookback:]

    resistance = max(recent_highs)
    support = min(recent_lows)

    # Distance to support/resistance
    price_range = resistance - support

    if price_range <= 0:
        return None

    resistance_distance = (
        resistance - price
    ) / price_range

    support_distance = (
        price - support
    ) / price_range

    # --------------------------------------------------
    # CONFIRMATION SCORING
    # --------------------------------------------------

    buy_score = 0
    sell_score = 0

    # EMA 50 trend
    if price > ema50:
        buy_score += 1

    if price < ema50:
        sell_score += 1

    # EMA 12 / EMA 26
    if ema12 > ema26:
        buy_score += 1

    if ema12 < ema26:
        sell_score += 1

    # MACD
    if macd > macd_signal:
        buy_score += 1

    if macd < macd_signal:
        sell_score += 1

    # RSI
    if 52 <= rsi <= 68:
        buy_score += 1

    if 32 <= rsi <= 48:
        sell_score += 1

    # Support / resistance location
    if support_distance > 0.15:
        buy_score += 1

    if resistance_distance > 0.15:
        sell_score += 1

    # Avoid buying directly into resistance
    if resistance_distance < 0.10:
        buy_score -= 1

    # Avoid selling directly into support
    if support_distance < 0.10:
        sell_score -= 1

    # --------------------------------------------------
    # FINAL DECISION
    # --------------------------------------------------

    signal = "NO TRADE"
    trend = "SIDEWAYS"
    confidence = 0

    if buy_score >= 5 and buy_score > sell_score:
        signal = "BUY"
        trend = "BUY"
        confidence = min(95, 70 + (buy_score - 4) * 5)

    elif sell_score >= 5 and sell_score > buy_score:
        signal = "SELL"
        trend = "SELL"
        confidence = min(95, 70 + (sell_score - 4) * 5)

    # --------------------------------------------------
    # RISK LEVELS
    # --------------------------------------------------

    if signal == "BUY":
        take_profit = "50 Pips"
        stop_loss = "25 Pips"

    elif signal == "SELL":
        take_profit = "50 Pips"
        stop_loss = "25 Pips"

    else:
        take_profit = None
        stop_loss = None

    # --------------------------------------------------
    # RESULT
    # --------------------------------------------------

    return {
        "pair": pair,
        "signal": signal,
        "entry": round(price, 5),
        "take_profit": take_profit,
        "stop_loss": stop_loss,
        "trend": trend,
        "rsi": round(rsi, 2),
        "ema50": round(ema50, 5),
        "macd": round(macd, 6),
        "macd_signal": round(macd_signal, 6),
        "support": round(support, 5),
        "resistance": round(resistance, 5),
        "confidence": confidence,
        "reason": (
            "Strong multi-indicator confirmation"
            if signal != "NO TRADE"
            else "Conditions are not strong enough"
        )
                               }
