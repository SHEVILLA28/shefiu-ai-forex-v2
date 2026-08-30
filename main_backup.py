import os
import time
import requests
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from config import BOT_TOKEN, CHAT_ID
from signals import get_signal


# =========================================================
# HEALTH SERVER FOR RENDER
# =========================================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"SHFIU AI FOREX V2 is running")

    def log_message(self, format, *args):
        pass


def start_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()


threading.Thread(
    target=start_server,
    daemon=True
).start()


# =========================================================
# FOREX PAIRS
# =========================================================

PAIRS = [
    "EUR/USD",
    "GBP/USD",
    "USD/JPY",
    "USD/CHF",
    "AUD/USD",
    "USDCAD",
    "NZD/USD",
    "XAUUSD",
]


# =========================================================
# TELEGRAM
# =========================================================

TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


def telegram_request(method, data=None):

    try:
        response = requests.post(
            f"{TELEGRAM_URL}/{method}",
            json=data or {},
            timeout=25
        )

        return response.json()

    except Exception as e:

        print("Telegram request error:", e)

        return {
            "ok": False,
            "error": str(e)
        }


# =========================================================
# TELEGRAM MENU
# =========================================================

def send_menu(chat_id):

    keyboard = [
        [
            {"text": "EUR/USD"},
            {"text": "GBP/USD"}
        ],
        [
            {"text": "USD/JPY"},
            {"text": "USD/CHF"}
        ],
        [
            {"text": "AUD/USD"},
            {"text": "USDCAD"}
        ],
        [
            {"text": "NZD/USD"},
            {"text": "XAUUSD"}
        ],
        [
            {"text": "📊 ALL PAIRS"}
        ]
    ]

    message = (
        "🤖 SHEFIU AI FOREX V2\n\n"
        "🟢 MANUAL TELEGRAM CONTROL: ON\n"
        "🔴 AUTOMATIC SCANNING: OFF\n\n"
        "Select a pair below.\n"
        "The bot will analyze the selected market."
    )

    telegram_request(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": message,
            "reply_markup": {
                "keyboard": keyboard,
                "resize_keyboard": True,
                "one_time_keyboard": False
            }
        }
    )


# =========================================================
# SIGNAL MESSAGE
# =========================================================

def format_signal(signal):

    if signal is None:
        return "⚠️ No signal data was returned."


    if signal.get("signal") == "NO TRADE":

        return (
            f"🤖 SHEFIU AI FOREX V2\n\n"
            f"📊 Pair: {signal.get('pair', 'Unknown')}\n\n"
            f"⚪ SIGNAL: NO TRADE\n\n"
            f"Market conditions are not strong enough."
        )


    signal_type = signal.get("signal", "UNKNOWN")

    if signal_type == "BUY":
        icon = "🟢"
    else:
        icon = "🔴"


    trend = signal.get("trend", "UNKNOWN")

    if trend == "BUY":
        trend_icon = "📈"
    else:
        trend_icon = "📉"


    return (
        "🤖 SHEFIU AI FOREX V2\n\n"
        f"📊 Pair: {signal.get('pair', 'Unknown')}\n\n"
        f"{icon} Signal: {signal_type}\n\n"
        "⏰ Timeframe: 5 Minutes\n\n"
        f"🎯 Entry: {signal.get('entry', 'N/A')}\n"
        f"✅ Take Profit: {signal.get('take_profit', 'N/A')}\n"
        f"🛑 Stop Loss: {signal.get('stop_loss', 'N/A')}\n\n"
        f"{trend_icon} Trend: {trend}\n"
        f"🔥 Confidence: {signal.get('confidence', 'N/A')}%\n\n"
        "⚠️ Signal only. No guaranteed profit."
    )


# =========================================================
# ANALYZE ONE PAIR
# =========================================================

def analyze_pair(chat_id, pair):

    telegram_request(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": (
                f"🔎 Analyzing {pair}...\n\n"
                "Please wait."
            )
        }
    )


    try:

        signal = get_signal(pair)

        message = format_signal(signal)

        telegram_request(
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": message
            }
        )

        print(f"Analyzed {pair}")

    except Exception as e:

        print(f"Signal error for {pair}:", e)

        telegram_request(
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": (
                    f"⚠️ Could not analyze {pair}.\n\n"
                    f"Error: {e}"
                )
            }
        )


# =========================================================
# ANALYZE ALL PAIRS
# =========================================================

def analyze_all(chat_id):

    telegram_request(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": (
                "📊 SHEFIU AI FOREX V2\n\n"
                "🔎 Checking all supported markets...\n\n"
                "Please wait."
            )
        }
    )


    for pair in PAIRS:

        try:

            signal = get_signal(pair)

            if signal is None:
                continue

            message = format_signal(signal)

            telegram_request(
                "sendMessage",
                {
                    "chat_id": chat_id,
                    "text": message
                }
            )

            time.sleep(1)

        except Exception as e:

            print(f"{pair} error:", e)


# =========================================================
# HANDLE TELEGRAM MESSAGE
# =========================================================

def handle_update(update):

    message = update.get("message")

    if not message:
        return


    chat = message.get("chat", {})
    chat_id = chat.get("id")

    text = message.get("text", "")

    if not chat_id:
        return


    print(
        f"Telegram command received: {text}"
    )


    # START
    if text == "/start":

        send_menu(chat_id)
        return


    # MENU
    if text == "/menu":

        send_menu(chat_id)
        return


    # ALL PAIRS
    if text == "📊 ALL PAIRS":

        analyze_all(chat_id)
        return


    # SINGLE PAIR
    if text in PAIRS:

        analyze_pair(
            chat_id,
            text
        )

        return


    # UNKNOWN COMMAND
    telegram_request(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": (
                "❓ I don't understand that command.\n\n"
                "Press /menu to open the Forex menu."
            )
        }
    )


# =========================================================
# TELEGRAM LOOP
# =========================================================

def telegram_loop():

    print(
        "🟢 Telegram manual-control system started."
    )

    offset = None


    while True:

        try:

            data = {
                "timeout": 25
            }


            if offset is not None:

                data["offset"] = offset


            result = telegram_request(
                "getUpdates",
                data
            )


            if result.get("ok"):

                updates = result.get(
                    "result",
                    []
                )


                for update in updates:

                    offset = (
                        update["update_id"] + 1
                    )

                    handle_update(update)


        except Exception as e:

            print(
                "Telegram loop error:",
                e
            )

            time.sleep(5)


# =========================================================
# START
# =========================================================

print(
    "🤖 SHEFIU AI FOREX V2"
)

print(
    "🔴 Automatic scanning: OFF"
)

print(
    "🟢 Manual Telegram control: ON"
)

print(
    "📱 Waiting for Telegram button commands..."
)


send_menu(CHAT_ID)


telegram_loop()
