import yfinance as yf
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator

def get_signal(pair):
    symbol = pair.replace("/", "") + "=X"

    data = yf.download(symbol, period="5d", interval="5m")

    if data.empty:
        return None

    close = data["Close"]

    ema50 = EMAIndicator(close, window=50).ema_indicator()
    rsi = RSIIndicator(close, window=14).rsi()

    price = float(close.iloc[-1])
    ema = float(ema50.iloc[-1])
    rsi_value = float(rsi.iloc[-1])

    if price > ema and rsi_value < 70:
        signal = "BUY"
        trend = "BUY"
    elif price < ema and rsi_value > 30:
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
        "confidence": 90
    }
