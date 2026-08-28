import os
import requests

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


def get_signal(pair):
    if not API_KEY:
        raise RuntimeError("TWELVE_DATA_API_KEY is missing")

    url = "https://api.twelvedata.com/time_series"

    params = {
        "symbol": pair[:3] + "/" + pair[3:] if "/" not in pair else pair,
        "interval": "5min",
        "outputsize": 100,
        "apikey": API_KEY
    }

    response = requests.get(url, params=params, timeout=15)
    response.raise_for_status()

    data = response.json()

    if data.get("status") == "error":
        raise RuntimeError(data.get("message", "Twelve Data error"))

    values = data.get("values", [])

    if len(values) < 50:
        return None

    values = list(reversed(values))
    closes = [float(x["close"]) for x in values]

    price = closes[-1]
    ema50 = calculate_ema(closes, 50)
    rsi = calculate_rsi(closes, 14)

    if ema50 is None or rsi is None:
        return None

    if price > ema50 and rsi < 70:
        signal = "BUY"
        trend = "BUY"
    elif price < ema50 and rsi > 30:
        signal = "SELL"
        trend = "SELL"
    else:
        signal = "NO TRADE"
        trend = "SIDEWAYS"

    return {
        "pair": pair,
        "signal": signal,
        "entry": round(price, 5),
        "take_profit": "50 Pips",
        "stop_loss": "25 Pips",
        "trend": trend,
        "rsi": round(rsi, 2),
        "ema50": round(ema50, 5),
        "confidence": 90
    }
