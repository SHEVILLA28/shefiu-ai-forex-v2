import os
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

import requests

from config import BOT_TOKEN, CHAT_ID
from signals import get_signal


# =========================================================
# SHEFIU AI FOREX V2
# =========================================================


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

    if not BOT_TOKEN or not CHAT_ID:

        print(
            "Telegram BOT_TOKEN or CHAT_ID is missing."
        )

        return False


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
            f"Telegram status: "
            f"{response.status_code}"
        )


        if not response.ok:

            print(
                "Telegram response:",
                response.text
            )


        return response.ok


    except Exception as e:

        print(
            f"Telegram error: {e}"
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
# BOT SETTINGS
# =========================================================

TIMEFRAME = "5M"

SCAN_INTERVAL = 300


# =========================================================
# DUPLICATE SIGNAL PROTECTION
# =========================================================

LAST_SIGNALS = {}


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
            f"{result.get('entry', 'N/A')}\n"

            f"✅ Take Profit: "
            f"{result.get('take_profit', 'N/A')}\n"

            f"🛑 Stop Loss: "
            f"{result.get('stop_loss', 'N/A')}\n\n"

        )


    message += (

        f"📈 Trend: {trend}\n\n"

        f"📊 RSI: "
        f"{result.get('rsi', 'N/A')}\n"

        f"🔥 Confidence: "
        f"{result.get('confidence', 0)}%\n\n"

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
                "========================================"
            )

            print(
                "Starting Forex market scan..."
            )

            print(
                "========================================"
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


                    signal = result.get(
                        "signal",
                        "NO TRADE"
                    )


                    # =====================================
                    # SEND ONLY NEW SIGNALS
                    # =====================================

                    if signal in ["BUY", "SELL"]:


                        previous_signal = LAST_SIGNALS.get(
                            pair
                        )


                        if previous_signal != signal:


                            message = format_signal(
                                result
                            )


                            full_message = (

                                "🔔 AUTOMATIC FOREX SIGNAL\n\n"

                                + message

                            )


                            sent = send_telegram_message(
                                full_message
                            )


                            if sent:

                                LAST_SIGNALS[pair] = signal


                                print(

                                    f"NEW signal sent for "

                                    f"{pair}: {signal}"

                                )


                            else:

                                print(

                                    f"Failed to send signal "

                                    f"for {pair}"

                                )


                        else:

                            print(

                                f"Duplicate signal ignored for "

                                f"{pair}: {signal}"

                            )


                    # =====================================
                    # RESET WHEN NO TRADE
                    # =====================================

                    else:


                        if LAST_SIGNALS.get(pair) is not None:


                            print(

                                f"Signal reset for {pair}. "

                                "Waiting for a new setup."

                            )


                        LAST_SIGNALS[pair] = None


                        print(

                            f"No trade for {pair}"

                        )


                    # Small delay between API requests

                    time.sleep(2)


                except Exception as e:

                    print(

                        f"Error analyzing "

                        f"{pair}: {e}"

                    )


            print(
                "========================================"
            )

            print(
                "Scan completed."
            )

            print(
                f"Waiting {SCAN_INTERVAL} seconds..."
            )

            print(
                "========================================"
            )


            time.sleep(
                SCAN_INTERVAL
            )


        except Exception as e:

            print(
                f"Scanner error: {e}"
            )

            print(
                "Waiting 60 seconds before retry..."
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


    # Start automatic Forex scanner

    automatic_scanner()
