import os
import time
import requests
import pandas as pd
from datetime import datetime, timezone

from ta.trend import EMAIndicator, MACD
from ta.momentum import RSIIndicator


# =========================================================
# SETTINGS
# =========================================================

TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# Forex only — NO OTC, NO crypto
PAIRS = [
    "EUR/USD",
    "GBP/USD",
    "USD/JPY",
    "AUD/USD",
    "USD/CAD",
    "USD/CHF",
    "NZD/USD",
]

TIMEFRAME = "5min"

# Start with one pair to protect Twelve Data credits.
# Change to True later when everything works.
SCAN_ALL_PAIRS = False

# How often the bot checks
CHECK_EVERY_SECONDS = 300

last_sent = {}


# =========================================================
# CHECK SETTINGS
# =========================================================

def check_environment():
    missing = []

    if not TWELVE_DATA_API_KEY:
        missing.append("TWELVE_DATA_API_KEY")

    if not BOT_TOKEN:
        missing.append("BOT_TOKEN")

    if not CHAT_ID:
        missing.append("CHAT_ID")

    if missing:
        print("❌ Missing environment variables:")
        for item in missing:
            print("   -", item)
        return False

    return True


# =========================================================
# GET MARKET DATA
# =========================================================

def get_market_data(symbol):
    url = "https://api.twelvedata.com/time_series"

    params = {
        "symbol": symbol,
        "interval": TIMEFRAME,
        "outputsize": 200,
        "apikey": TWELVE_DATA_API_KEY,
    }

    try:
        response = requests.get(
            url,
            params=params,
            timeout=15
        )

        data = response.json()

    except Exception as e:
        print(f"❌ Connection error for {symbol}: {e}")
        return None

    if "values" not in data:
        print(f"❌ Twelve Data error for {symbol}:")
        print(data)
        return None

    df = pd.DataFrame(data["values"])

    if len(df) < 60:
        print(f"⚠️ Not enough candles for {symbol}")
        return None

    df = df.iloc[::-1].reset_index(drop=True)

    for column in ["open", "high", "low", "close"]:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    df = df.dropna()

    return df


# =========================================================
# INDICATORS
# =========================================================

def calculate_indicators(df):

    # EMA
    df["EMA20"] = EMAIndicator(
        close=df["close"],
        window=20
    ).ema_indicator()

    df["EMA50"] = EMAIndicator(
        close=df["close"],
        window=50
    ).ema_indicator()

    # RSI
    df["RSI"] = RSIIndicator(
        close=df["close"],
        window=14
    ).rsi()

    # MACD
    macd = MACD(
        close=df["close"],
        window_fast=12,
        window_slow=26,
        window_sign=9
    )

    df["MACD"] = macd.macd()
    df["MACD_SIGNAL"] = macd.macd_signal()
    df["MACD_HIST"] = macd.macd_diff()

    # Support / resistance
    support = df["low"].tail(20).min()
    resistance = df["high"].tail(20).max()

    return df, support, resistance


# =========================================================
# SIGNAL ANALYSIS
# =========================================================

def analyze_pair(symbol):

    df = get_market_data(symbol)

    if df is None:
        return None

    df, support, resistance = calculate_indicators(df)

    last = df.iloc[-1]

    price = float(last["close"])
    ema20 = float(last["EMA20"])
    ema50 = float(last["EMA50"])
    rsi = float(last["RSI"])
    macd = float(last["MACD"])
    macd_signal = float(last["MACD_SIGNAL"])

    signal = "NO TRADE"
    trend = "Sideways"
    confidence = 0

    # -----------------------------------------------------
    # BUY CONDITIONS
    # -----------------------------------------------------

    buy_conditions = [
        ema20 > ema50,
        price > ema50,
        50 <= rsi <= 68,
        macd > macd_signal,
    ]

    # -----------------------------------------------------
    # SELL CONDITIONS
    # -----------------------------------------------------

    sell_conditions = [
        ema20 < ema50,
        price < ema50,
        32 <= rsi <= 50,
        macd < macd_signal,
    ]

    buy_score = sum(buy_conditions)
    sell_score = sum(sell_conditions)

    # Require ALL conditions
    if buy_score == 4:

        signal = "🟢 BUY"
        trend = "Bullish"
        confidence = 90

        tp = price + 0.0020
        sl = price - 0.0010

    elif sell_score == 4:

        signal = "🔴 SELL"
        trend = "Bearish"
        confidence = 90

        tp = price - 0.0020
        sl = price + 0.0010

    else:

        tp = None
        sl = None

        if ema20 > ema50:
            trend = "Bullish"

        elif ema20 < ema50:
            trend = "Bearish"

    return {
        "pair": symbol,
        "signal": signal,
        "entry": price,
        "take_profit": tp,
        "stop_loss": sl,
        "support": float(support),
        "resistance": float(resistance),
        "trend": trend,
        "ema20": ema20,
        "ema50": ema50,
        "rsi": rsi,
        "macd": macd,
        "macd_signal": macd_signal,
        "confidence": confidence,
    }


# =========================================================
# TELEGRAM
# =========================================================

def send_telegram(message):

    url = (
        f"https://api.telegram.org/bot"
        f"{BOT_TOKEN}/sendMessage"
    )

    data = {
        "chat_id": CHAT_ID,
        "text": message,
    }

    try:

        response = requests.post(
            url,
            data=data,
            timeout=15
        )

        if response.ok:
            print("✅ Telegram signal sent")
        else:
            print("❌ Telegram error:")
            print(response.text)

    except Exception as e:
        print("❌ Telegram connection error:", e)


# =========================================================
# FORMAT SIGNAL
# =========================================================

def format_signal(result):

    return f"""
📊 FOREX AI SIGNAL

Pair: {result['pair']}
Timeframe: {TIMEFRAME}

Signal: {result['signal']}

Entry: {result['entry']:.5f}

TP: {result['take_profit']:.5f}
SL: {result['stop_loss']:.5f}

Support: {result['support']:.5f}
Resistance: {result['resistance']:.5f}

Trend: {result['trend']}

EMA20: {result['ema20']:.5f}
EMA50: {result['ema50']:.5f}

RSI: {result['rsi']:.2f}

MACD: {result['macd']:.5f}
MACD Signal: {result['macd_signal']:.5f}

Confidence: {result['confidence']}%

⚠️ Forex market only
⏱ 5-minute analysis
""".strip()


# =========================================================
# SCAN
# =========================================================

def scan_market():

    if SCAN_ALL_PAIRS:
        pairs = PAIRS
    else:
        pairs = ["EUR/USD"]

    print()
    print("=" * 50)
    print("🔎 FOREX AI SCAN")
    print(datetime.now(timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    ))
    print("=" * 50)

    for pair in pairs:

        print(f"Checking {pair}...")

        result = analyze_pair(pair)

        if result is None:
            continue

        print(
            f"{pair}: {result['signal']} | "
            f"Trend: {result['trend']} | "
            f"RSI: {result['rsi']:.2f}"
        )

        # Only send actual BUY/SELL signals
        if result["signal"] == "NO TRADE":
            print("⏳ No trade")
            continue

        # Prevent duplicate signal
        signal_key = (
            f"{result['signal']}_"
            f"{result['entry']:.5f}"
        )

        if last_sent.get(pair) == signal_key:
            print("⏭ Duplicate signal skipped")
            continue

        last_sent[pair] = signal_key

        message = format_signal(result)

        print(message)

        send_telegram(message)


# =========================================================
# MAIN
# =========================================================

def main():

    print("🚀 FOREX AI BOT STARTING...")
    print("Forex only — NO OTC")
    print("Timeframe:", TIMEFRAME)

    if not check_environment():
        return

    print("✅ Environment variables found")
    print("✅ Bot is ready")

    while True:

        try:

            scan_market()

            print()
            print(
                f"⏳ Waiting "
                f"{CHECK_EVERY_SECONDS // 60} minutes..."
            )

            time.sleep(CHECK_EVERY_SECONDS)

        except KeyboardInterrupt:

            print("🛑 Bot stopped")
            break

        except Exception as e:

            print("❌ Unexpected error:", e)
            print("⏳ Retrying in 60 seconds...")

            time.sleep(60)


if __name__ == "__main__":
    main()
