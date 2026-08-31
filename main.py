import os
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

import requests

from config import BOT_TOKEN, CHAT_ID
from signals import get_signal


# =========================================================
# HEALTH SERVER FOR RENDER
# =========================================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        self.send_response(200)

        self.send_header(
            "Content-type",
            "text/plain"
        )

        self.end_headers()

        self.wfile.write(
            b"Forex AI Bot is running"
        )


def run_health_server():

    port = int(
        os.environ.get(
            "PORT",
            10000
        )
    )

    server = HTTPServer(
        ("0.0.0.0", port),
        HealthHandler
    )

    print(
        f"Health server running on port {port}"
    )

    server.serve_forever()


# =========================================================
# TELEGRAM MESSAGE
# =========================================================

def send_telegram_message(message):

    url = (
        f"https://api.telegram.org/bot"
        f"{BOT_TOKEN}/sendMessage"
    )

    data = {
        "chat_id": CHAT_ID,
        "text": message
    }

    try:

        response = requests.post(
            url,
            data=data,
            timeout=30
        )

        print(
            "Telegram status:",
            response.status_code
        )

        return response.ok

    except Exception as e:

        print(
            "Telegram error:",
            e
        )

        return False


# =========================================================
# FOREX PAIRS
# =========================================================

FOREX_PAIRS = [

    "EUR/USD",
    "GBP/USD",
    "USD/JPY",
    "USD/CHF",
    "AUD/USD",
    "USD/CAD",
    "NZD/USD",
    "XAU/USD",
    "EUR/GBP",
    "CHF/JPY",
    "AUD/JPY",
    "EUR/JPY",
    "GBP/JPY",
    "USD/SGD"

]


# =========================================================
# SETTINGS
# =========================================================

TIMEFRAME = "5M"

SCAN_INTERVAL = 300


# =========================================================
# FORMAT SIGNAL
# =========================================================

def format_signal(result):

    signal = result.get(
        "signal",
        "NO TRADE"
    )

    pair = result.get(
        "pair",
        "Unknown"
    )

    timeframe = result.get(
        "timeframe",
        TIMEFRAME
    )

    trend = result.get(
        "trend",
        "WAIT"
    )

    reason = result.get(
        "reason",
        "No reason available."
    )


    if signal == "BUY":

        signal_icon = "🟢"

    elif signal == "SELL":

        signal_icon = "🔴"

    else:

        signal_icon = "⚪"


    message = (
        "🤖 SHEFIU AI FOREX V2\n\n"

        f"📊 Pair: {pair}\n\n"

        f"{signal_icon} SIGNAL: {signal}\n\n"

        f"⏱ Timeframe: {timeframe}\n\n"

    )


    if signal in ["BUY", "SELL"]:

        message += (

            f"🎯 Entry: "
            f"{result.get('entry')}\n"

            f"✅ Take Profit: "
            f"{result.get('take_profit')}\n"

            f"🛑 Stop Loss: "
            f"{result.get('stop_loss')}\n\n"

        )


    message += (

        f"📈 Trend: {trend}\n\n"

        f"📊 RSI: "
        f"{result.get('rsi')}\n"

        f"🔥 Confidence: "
        f"{result.get('confidence')}%\n\n"

        f"📝 Reason: {reason}\n\n"

        "⚠️ Signal only. No guaranteed profit."

    )

    return message


# =========================================================
# AUTOMATIC FOREX SCANNER
# =========================================================

def automatic_scanner():

    print(
        "Automatic Forex scanner started."
    )


    while True:

        try:

            print(
                "Starting Forex market scan..."
            )


            for pair in FOREX_PAIRS:

                try:

                    print(
                        f"Analyzing {pair}..."
                    )


                    result = get_signal(

                        pair,

                        TIMEFRAME

                    )


                    if result.get(
                        "signal"
                    ) in ["BUY", "SELL"]:

                        message = format_signal(
                            result
                        )


                        send_telegram_message(
                            "🔔 AUTOMATIC FOREX SIGNAL\n\n"
                            + message
                        )


                        print(
                            f"Signal sent for {pair}"
                        )


                    else:

                        print(
                            f"No trade for {pair}"
                        )


                    time.sleep(2)


                except Exception as e:

                    print(
                        f"Error analyzing "
                        f"{pair}: {e}"
                    )


            print(
                "Scan completed. Waiting 5 minutes..."
            )


            time.sleep(
                SCAN_INTERVAL
            )


        except Exception as e:

            print(
                "Scanner error:",
                e
            )

            time.sleep(60)


# =========================================================
# START BOT
# =========================================================

if __name__ == "__main__":

    print(
        "Starting SHEFIU AI FOREX V2..."
    )


    # Start Render health server
    health_thread = threading.Thread(

        target=run_health_server,

        daemon=True

    )

    health_thread.start()


    # Start automatic scanner
    automatic_scanner()
