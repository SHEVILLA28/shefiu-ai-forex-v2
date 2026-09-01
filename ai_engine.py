import os
import requests
import pandas as pd

# =========================================================
# SHEFIU AI FOREX V2 - AI ENGINE
# LIVE FOREX DATA ONLY - NO OTC
# =========================================================

API_KEY = os.getenv("TWELVE_DATA_API_KEY")
BASE_URL = "https://api.twelvedata.com/time_series"


def get_market_data(symbol, interval="5min", outputsize=100):
    if not API_KEY:
        return None

    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": outputsize,
        "apikey": API_KEY,
        "format": "JSON"
    }

    try:
        response = requests.get(BASE_URL, params=params, timeout=15)
        data = response.json()

        if "values" not in data:
            print(f"Market data error for {symbol}: {data}")
            return None

        df = pd.DataFrame(data["values"])
        df = df.rename(columns={"datetime": "time"})

        for column in ["open", "high", "low", "close"]:
            df[column] = pd.to_numeric(df[column])

        return df.iloc[::-1].reset_index(drop=True)

    except Exception as e:
        print(f"Market data error: {e}")
        return None


def calculate_indicators(df):
    if df is None or len(df) < 60:
        return None

    df["EMA20"] = df["close"].ewm(span=20, adjust=False).mean()
    df["EMA50"] = df["close"].ewm(span=50, adjust=False).mean()

    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    df["RSI"] = 100 - (100 / (1 + rs))

    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["MACD_SIGNAL"] = df["MACD"].ewm(span=9, adjust=False).mean()

    return df


def analyze_market(symbol, interval="5min"):
    df = get_market_data(symbol, interval)

    if df is None:
        return {
            "symbol": symbol,
            "signal": "NO TRADE",
            "confidence": 0,
            "reason": "Unable to get live market data"
        }

    df = calculate_indicators(df)

    if df is None:
        return {
            "symbol": symbol,
            "signal": "NO TRADE",
            "confidence": 0,
            "reason": "Not enough market data"
        }

    latest = df.iloc[-1]

    price = float(latest["close"])
    ema20 = float(latest["EMA20"])
    ema50 = float(latest["EMA50"])
    rsi = float(latest["RSI"])
    macd = float(latest["MACD"])
    macd_signal = float(latest["MACD_SIGNAL"])

    buy_score = 0
    buy_reason = []

    if price > ema50:
        buy_score += 1
        buy_reason.append("Price above EMA50")
    if ema20 > ema50:
        buy_score += 1
        buy_reason.append("EMA20 above EMA50")
    if 45 <= rsi <= 70:
        buy_score += 1
        buy_reason.append("RSI supports bullish trend")
    if macd > macd_signal:
        buy_score += 1
        buy_reason.append("MACD bullish")

    sell_score = 0
    sell_reason = []

    if price < ema50:
        sell_score += 1
        sell_reason.append("Price below EMA50")
    if ema20 < ema50:
        sell_score += 1
        sell_reason.append("EMA20 below EMA50")
    if 30 <= rsi <= 55:
        sell_score += 1
        sell_reason.append("RSI supports bearish trend")
    if macd < macd_signal:
        sell_score += 1
        sell_reason.append("MACD bearish")

    if buy_score >= 3 and buy_score > sell_score:
        signal = "BUY"
        confidence = min(95, 55 + buy_score * 10)
        reason = " | ".join(buy_reason)
    elif sell_score >= 3 and sell_score > buy_score:
        signal = "SELL"
        confidence = min(95, 55 + sell_score * 10)
        reason = " | ".join(sell_reason)
    else:
        signal = "NO TRADE"
        confidence = max(buy_score, sell_score) * 15
        reason = "Market conditions are not strong enough"

    return {
        "symbol": symbol,
        "signal": signal,
        "confidence": confidence,
        "price": round(price, 5),
        "ema20": round(ema20, 5),
        "ema50": round(ema50, 5),
        "rsi": round(rsi, 2),
        "macd": round(macd, 6),
        "interval": interval,
        "reason": reason
    }


def get_signal(symbol, interval="5min"):
    return analyze_market(symbol, interval)


if __name__ == "__main__":
    print(analyze_market("EUR/USD"))
