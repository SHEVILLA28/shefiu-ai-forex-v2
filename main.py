import time
import requests
from config import BOT_TOKEN, CHAT_ID
from signals import get_signal

PAIRS = [
    "EUR/USD",
    "GBP/USD",
    "USD/JPY",
    "USD/CHF",
    "AUD/USD",
    "XAU/USD",
]

last_signals = {}

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    try:
        requests.post(
            url,
            data={
                "chat_id": CHAT_ID,
                "text": message
            },
            timeout=15
        )
    except Exception as e:
        print("Telegram Error:", e)

print("🤖 SHEFIU AI FOREX V2 Started...")

while True:

    for pair in PAIRS:

        try:
            print(f"Checking {pair}...")

            signal = get_signal(pair)

            if signal is None:
                continue

            if signal["signal"] == "NO TRADE":
                print(f"{pair}: NO TRADE")
                continue

            if last_signals.get(pair) == signal["signal"]:
                print(f"{pair}: Duplicate signal skipped")
                continue

            signal_icon = "🟢" if signal["signal"] == "BUY" else "🔴"
            trend_icon = "📈" if signal["trend"] == "BUY" else "📉"

            msg = (
                f"🤖 SHEFIU AI FOREX V2\n\n"
                f"📈 Pair: {signal['pair']}\n\n"
                f"{signal_icon} Signal: {signal['signal']}\n\n"
                f"⏰ Pocket Option Expiry: 5 Minutes\n\n"
                f"🎯 Entry: {signal['entry']}\n"
                f"✅ Take Profit: {signal['take_profit']}\n"
                f"🛑 Stop Loss: {signal['stop_loss']}\n\n"
                f"{trend_icon} Trend: {signal['trend']}\n"
                f"🔥 Confidence: {signal['confidence']}%"
            )

            send_telegram(msg)

            last_signals[pair] = signal["signal"]

            print(f"Sent {pair} {signal['signal']}")

        except Exception as e:
            print(pair, e)

    print("Finished checking all pairs.")
    print("Waiting 5 minutes...")
    time.sleep(300)
