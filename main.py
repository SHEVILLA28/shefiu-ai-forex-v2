import os
import time
import threading

from http.server import HTTPServer, BaseHTTPRequestHandler

import requests

from config import BOT_TOKEN, CHAT_ID
from telegram_bot import run_telegram_bot, format_signal
from signals import get_signal

=========================================================

SHEFIU AI FOREX V2

=========================================================

=========================================================

HEALTH SERVER FOR RENDER

=========================================================

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


def do_HEAD(self):

    self.send_response(200)

    self.send_header(
        "Content-type",
        "text/plain"
    )

    self.end_headers()


def log_message(self, format, *args):

    return

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

=========================================================

TELEGRAM MESSAGE

=========================================================

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
        f"Telegram status: {response.status_code}"
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

=========================================================

FOREX PAIRS

=========================================================

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

=========================================================

BOT SETTINGS

=========================================================

TIMEFRAME = "5M"

SCAN_INTERVAL = 300

=========================================================

SIGNAL MEMORY

PREVENTS REPEATED SIGNALS

=========================================================

LAST_SIGNAL = {}

=========================================================

AUTOMATIC FOREX SCANNER

=========================================================

def run_automatic_scanner():

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


                signal = result.get(
                    "signal",
                    "NO TRADE"
                )


                # =====================================
                # SEND ONLY BUY OR SELL
                # =====================================

                if signal in ["BUY", "SELL"]:


                    previous_signal = (
                        LAST_SIGNAL.get(pair)
                    )


                    # ===============================
                    # PREVENT DUPLICATE ALERT
                    # ===============================

                    if previous_signal == signal:

                        print(
                            f"Duplicate {signal} "
                            f"signal ignored for {pair}"
                        )


                    else:

                        message = format_signal(
                            result
                        )


                        success = (
                            send_telegram_message(
                                message
                            )
                        )


                        if success:

                            LAST_SIGNAL[pair] = (
                                signal
                            )


                            print(
                                f"{signal} signal sent "
                                f"for {pair}"
                            )


                else:

                    # Reset memory when market
                    # returns to NO TRADE

                    LAST_SIGNAL[pair] = None


                # =====================================
                # SMALL DELAY BETWEEN API REQUESTS
                # =====================================

                time.sleep(3)


            except Exception as e:

                print(
                    f"Scanner error for "
                    f"{pair}: {e}"
                )


                time.sleep(3)


        print(
            "Forex scan completed."
        )


    except Exception as e:

        print(
            f"Automatic scanner error: {e}"
        )


    # =============================================
    # WAIT BEFORE NEXT FULL MARKET SCAN
    # =============================================

    print(
        f"Waiting {SCAN_INTERVAL} seconds "
        "before next scan..."
    )


    time.sleep(
        SCAN_INTERVAL
    )

=========================================================

START BOT

=========================================================

if name == "main":

print(
    "Starting SHEFIU AI FOREX V2..."
)


# =====================================================
# START RENDER HEALTH SERVER
# =====================================================

health_thread = threading.Thread(
    target=run_health_server,
    daemon=True
)

health_thread.start()


# =====================================================
# START TELEGRAM MANUAL BOT
# =====================================================

telegram_thread = threading.Thread(
    target=run_telegram_bot,
    daemon=True
)

telegram_thread.start()

print(
    "Manual Telegram bot started."
)


# =====================================================
# START AUTOMATIC FOREX SCANNER
# =====================================================

scanner_thread = threading.Thread(
    target=run_automatic_scanner,
    daemon=True
)

scanner_thread.start()

print(
    "Automatic Forex scanner started."
)


# =====================================================
# KEEP RENDER SERVICE RUNNING
# =====================================================

while True:

    time.sleep(60)
