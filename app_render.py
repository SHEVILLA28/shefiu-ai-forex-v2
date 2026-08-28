import os
import json
import requests
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

DATA_KEY = os.environ.get("TWELVE_DATA_API_KEY")

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def forex_market_open():
    now = datetime.now(timezone.utc)
    wd = now.weekday()
    if wd == 5:
        return False
    if wd == 6 and now.hour < 21:
        return False
    if wd == 4 and now.hour >= 21:
        return False
    return True


def send_telegram_signal(result):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return

    if result.get("signal") not in ("BUY", "SELL"):
        return

    text = (
        "🤖 FOREX AI SIGNAL\n\n"
        f"Pair: {result['symbol']}\n"
        f"Signal: {result['signal']}\n"
        f"Price: {result['price']}\n"
        f"RSI: {result['rsi']}\n"
        f"EMA Trend: {result['ema_trend']}\n"
        f"MACD Trend: {result['macd_trend']}\n"
        f"Confidence: {result['confidence']}%\n\n"
        "⚠️ Analysis only — trade at your own risk."
    )

    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            data={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": text
            },
            timeout=10
        )
    except Exception:
        pass


def ema(values, period):
    if len(values) < period:
        return None
    k = 2 / (period + 1)
    result = sum(values[:period]) / period
    for price in values[period:]:
        result = price * k + result * (1 - k)
    return result

def ema_series(values, period):
    if len(values) < period:
        return []
    result = [sum(values[:period]) / period]
    k = 2 / (period + 1)
    for price in values[period:]:
        result.append(price * k + result[-1] * (1 - k))
    return result

def rsi(values, period=14):
    if len(values) < period + 1:
        return None

    gains = []
    losses = []

    for i in range(1, len(values)):
        change = values[i] - values[i - 1]
        gains.append(max(change, 0))
        losses.append(max(-change, 0))

    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def get_data(symbol):
    params = {
        "symbol": symbol,
        "interval": "5min",
        "outputsize": 100,
        "apikey": DATA_KEY
    }

    response = requests.get(
        "https://api.twelvedata.com/time_series",
        params=params,
        timeout=20
    )

    data = response.json()

    if "values" not in data:
        raise Exception(data.get("message", "No candle data returned."))

    values = data["values"]

    # Ignore newest candle because it may still be forming.
    completed = values[1:]

    closes = [float(x["close"]) for x in reversed(completed)]

    if len(closes) < 40:
        raise Exception("Not enough completed 5-minute candles.")

    return closes


def analyze(symbol):
    closes = get_data(symbol)

    price = closes[-1]

    ema9 = ema(closes, 9)
    ema21 = ema(closes, 21)

    ema12_series = ema_series(closes, 12)
    ema26_series = ema_series(closes, 26)

    macd_values = []

    start = max(0, len(ema26_series) - len(ema12_series))

    for i in range(len(ema26_series)):
        j = i + start
        if j < len(ema12_series):
            macd_values.append(
                ema12_series[j] - ema26_series[i]
            )

    if len(macd_values) < 10:
        raise Exception("Not enough MACD data.")

    macd = macd_values[-1]
    signal_series = ema_series(macd_values, 9)

    if not signal_series:
        raise Exception("Not enough MACD signal data.")

    macd_signal = signal_series[-1]

    rsi14 = rsi(closes, 14)

    if ema9 > ema21:
        trend = "UP"
    elif ema9 < ema21:
        trend = "DOWN"
    else:
        trend = "FLAT"

    if macd > macd_signal:
        macd_trend = "BULLISH"
    elif macd < macd_signal:
        macd_trend = "BEARISH"
    else:
        macd_trend = "FLAT"

    support = min(closes[-20:])
    resistance = max(closes[-20:])
    sr_range = resistance - support

    near_support = (
        sr_range > 0 and
        price <= support + sr_range * 0.20
    )

    near_resistance = (
        sr_range > 0 and
        price >= resistance - sr_range * 0.20
    )

    # Strong confirmation scoring
    bullish_score = 0
    bearish_score = 0

    if trend == "UP":
        bullish_score += 2
    elif trend == "DOWN":
        bearish_score += 2

    if macd_trend == "BULLISH":
        bullish_score += 2
    elif macd_trend == "BEARISH":
        bearish_score += 2

    if 50 <= rsi14 <= 68:
        bullish_score += 1
    elif 32 <= rsi14 <= 50:
        bearish_score += 1

    if trend == "UP" and price > ema9:
        bullish_score += 1
    elif trend == "DOWN" and price < ema9:
        bearish_score += 1

    confidence = max(bullish_score, bearish_score) * 100 / 6

    if bullish_score >= 5 and bullish_score > bearish_score:
        signal = "BUY"
    elif bearish_score >= 5 and bearish_score > bullish_score:
        signal = "SELL"
    else:
        signal = "WAIT"

    # Support/resistance safety filter
    if signal == "SELL" and near_support:
        signal = "WAIT"

    elif signal == "BUY" and near_resistance:
        signal = "WAIT"

    confidence = max(0, min(confidence, 100))

    return {
        "symbol": symbol,
        "price": round(price, 6),
        "rsi": round(rsi14, 2),
        "ema_trend": trend,
        "macd": round(macd, 8),
        "macd_signal": round(macd_signal, 8),
        "macd_trend": macd_trend,
        "support": round(support, 6),
        "resistance": round(resistance, 6),
        "confidence": confidence,
        "signal": signal
    }

class Handler(BaseHTTPRequestHandler):

    def do_GET(self):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)

        if parsed.path == "/api/signal":
            symbol = query.get("symbol", ["EUR/USD"])[0]

            try:
                if not forex_market_open():
                    result = {"symbol": symbol, "market_open": False, "signal": "MARKET_CLOSED", "message": "Forex market is closed. No trading signal."}
                else:
                    result = analyze(symbol)
                    send_telegram_signal(result)
                body = json.dumps(result).encode()

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

            except Exception as e:
                body = json.dumps({"error": str(e)}).encode()
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(body)

            return

        if self.path == "/" or self.path.startswith("/index.html"):
            try:
                with open("index.html", "rb") as f:
                    body = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except Exception as e:
                self.send_error(500, str(e))
            return

        self.send_error(404)

if __name__ == "__main__":
    print("Forex AI web backend started")
    HTTPServer(("0.0.0.0", int(os.environ.get("PORT", "8080"))), Handler).serve_forever()
