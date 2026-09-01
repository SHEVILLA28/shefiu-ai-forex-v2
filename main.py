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

TIMEFRAME = "5M"

# Scan every 5 minutes
SCAN_INTERVAL = 300

# Stores the last signal sent for each pair
LAST_SIGNALS = {}


# =========================================================
# HEALTH SERVER FOR RENDER
# =========================================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()

        self.wfile.write(
            b"Forex AI Bot is running"
        )

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()

    def log_message(self, format, *args):
        print(
            "[HEALTH] " + (format % args),
            flush=True
        )


def run_health_server():

    port = int(
        os.environ.get("PORT", 10000)
    )

    server = HTTPServer(
        ("0.0.0.0", port),
        HealthHandler
    )

    print(
        f"Health server running on port {port}",
        flush=True
    )

    server.serve_forever()


# =========================================================
# TELEGRAM MESSAGE
# =========================================================

def send_telegram_message(message):

    if not BOT_TOKEN:
        print(
            "ERROR: BOT_TOKEN is missing.",
            flush=True
        )
        return False

    if not CHAT_ID:
        print(
            "ERROR: CHAT_ID is missing.",
            flush=True
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
            f"Telegram status: {response.status_code}",
            flush=True
        )

        if not response.ok:

            print(
                f"Telegram error response: {response.text}",
                flush=True
            )

            return False

        return True

    except Exception as e:

        print(
            f"Telegram connection error: {e}",
            flush=True
        )

        return False


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
        "========================================",
        flush=True
    )

    print(
        "AUTOMATIC FOREX SCANNER STARTED",
        flush=True
    )

    print(
        "========================================",
        flush=True
    )


    # Send startup confirmation
    startup_message = (
        "🟢 SHEFIU AI FOREX V2 IS ONLINE\n\n"
        f"⏱ Timeframe: {TIMEFRAME}\n"
        f"📊 Monitoring {len(FOREX_PAIRS)} Forex pairs\n\n"
        "🤖 Automatic scanner has started."
    )

    startup_sent = send_telegram_message(
        startup_message
    )

    if startup_sent:

        print(
            "Startup message sent to Telegram successfully.",
            flush=True
        )

    else:

        print(
            "WARNING: Startup message was NOT sent to Telegram.",
            flush=True
        )


    while True:

        try:

            print(
                "\n========================================",
                flush=True
            )

            print(
                "Starting Forex market scan...",
                flush=True
            )

            print(
                "========================================",
                flush=True
            )


            for pair in FOREX_PAIRS:

                try:

                    print(
                        f"Analyzing {pair}...",
                        flush=True
                    )


                    result = get_signal(
                        pair,
                        TIMEFRAME
                    )


                    if not isinstance(result, dict):

                        print(
                            f"Invalid result received for {pair}",
                            flush=True
                        )

                        time.sleep(2)
                        continue


                    signal = result.get(
                        "signal",
                        "NO TRADE"
                    )


                    print(
                        f"{pair} result: {signal}",
                        flush=True
                    )


                    # =====================================
                    # SEND BUY OR SELL SIGNAL
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


                            print(
                                f"New {signal} signal found for {pair}",
                                flush=True
                            )


                            sent = send_telegram_message(
                                full_message
                            )


                            if sent:

                                LAST_SIGNALS[pair] = signal

                                print(
                                    f"SUCCESS: Signal sent for "
                                    f"{pair}: {signal}",
                                    flush=True
                                )

                            else:

                                print(
                                    f"FAILED: Could not send "
                                    f"signal for {pair}",
                                    flush=True
                                )


                        else:

                            print(
                                f"Duplicate signal ignored for "
                                f"{pair}: {signal}",
                                flush=True
                            )


                    # =====================================
                    # NO TRADE
                    # =====================================

                    else:

                        print(
                            f"No trade setup for {pair}",
                            flush=True
                        )


                    # Wait between API requests
                    time.sleep(2)


                except Exception as e:

                    print(
                        f"ERROR analyzing {pair}: {e}",
                        flush=True
                    )

                    time.sleep(2)


            print(
                "\n========================================",
                flush=True
            )

            print(
                "Scan completed.",
                flush=True
            )

            print(
                f"Waiting {SCAN_INTERVAL} seconds "
                "before next scan...",
                flush=True
            )

            print(
                "========================================",
                flush=True
            )


            time.sleep(SCAN_INTERVAL)


        except Exception as e:

            print(
                f"SCANNER ERROR: {e}",
                flush=True
            )

            print(
                "Waiting 60 seconds before retry...",
                flush=True
            )

            time.sleep(60)


# =========================================================
# START BOT
# =========================================================

if __name__ == "__main__":

    print(
        "Starting SHEFIU AI FOREX V2...",
        flush=True
    )


    # Start Forex scanner in background
    scanner_thread = threading.Thread(
        target=automatic_scanner,
        daemon=True
    )

    scanner_thread.start()


    # Run Render health server in main thread
    run_health_server()
