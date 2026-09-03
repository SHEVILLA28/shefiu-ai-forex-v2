import os
import time
import threading
import asyncio

from http.server import HTTPServer, BaseHTTPRequestHandler

import requests

from config import BOT_TOKEN, CHAT_ID
from telegram_bot import run_telegram_bot, format_signal
from signals import get_signal

from metaapi_trader import (
    place_buy_order,
    place_sell_order
)


# =========================================================
# SHEFIU AI FOREX V2
# AUTOMATIC SIGNAL + TELEGRAM + METAAPI TRADING
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


# =========================================================
# FOREX PAIRS
# =========================================================

FOREX_PAIRS = [

    "EUR/USD",
    "GBP/USD"

]


# =========================================================
# METAAPI SYMBOL CONVERSION
# =========================================================

def convert_to_mt5_symbol(pair):

    return pair.replace(
        "/",
        ""
    )


# =========================================================
# BOT SETTINGS
# =========================================================

TIMEFRAME = "5M"


# Scan every 6 hours

SCAN_INTERVAL = 21600


# Trade volume

TRADE_VOLUME = 0.01


# =========================================================
# SIGNAL MEMORY
# PREVENTS DUPLICATE TRADES
# =========================================================

LAST_SIGNAL = {}


# =========================================================
# AUTOMATIC TRADE EXECUTION
# =========================================================

def execute_trade(signal, pair):

    symbol = convert_to_mt5_symbol(
        pair
    )


    try:

        if signal == "BUY":

            print(
                f"Placing BUY order for {symbol}"
            )


            result = asyncio.run(
                place_buy_order(
                    symbol,
                    TRADE_VOLUME
                )
            )


            print(
                f"BUY order result: {result}"
            )


            return True


        elif signal == "SELL":

            print(
                f"Placing SELL order for {symbol}"
            )


            result = asyncio.run(
                place_sell_order(
                    symbol,
                    TRADE_VOLUME
                )
            )


            print(
                f"SELL order result: {result}"
            )


            return True


        return False


    except Exception as e:

        print(
            f"Trade execution error for "
            f"{symbol}: {e}"
        )

        return False


# =========================================================
# AUTOMATIC FOREX SCANNER
# =========================================================

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


                    print(
                        f"Result for {pair}: "
                        f"{signal} | "
                        f"Trend: {result.get('trend')} | "
                        f"RSI: {result.get('rsi')} | "
                        f"Reason: {result.get('reason')}"
                    )


                    # =====================================
                    # BUY OR SELL SIGNAL
                    # =====================================

                    if signal in ["BUY", "SELL"]:

                        previous_signal = (
                            LAST_SIGNAL.get(pair)
                        )


                        # =================================
                        # PREVENT DUPLICATE TRADES
                        # =================================

                        if previous_signal == signal:

                            print(
                                f"Duplicate {signal} "
                                f"signal ignored for {pair}"
                            )


                        else:

                            print(
                                f"NEW {signal} SIGNAL "
                                f"FOR {pair}"
                            )


                            # =============================
                            # PLACE AUTOMATIC TRADE
                            # =============================

                            trade_success = execute_trade(
                                signal,
                                pair
                            )


                            if trade_success:

                                LAST_SIGNAL[pair] = signal


                                print(
                                    f"{signal} trade placed "
                                    f"successfully for {pair}"
                                )


                                # =========================
                                # SEND TELEGRAM MESSAGE
                                # =========================

                                message = format_signal(
                                    result
                                )


                                message += (
                                    "\n\n🤖 AUTOMATIC TRADE "
                                    "PLACED SUCCESSFULLY"
                                )


                                send_telegram_message(
                                    message
                                )


                            else:

                                print(
                                    f"Trade failed for {pair}"
                                )


                                message = (
                                    f"⚠️ SIGNAL DETECTED\n\n"
                                    f"Pair: {pair}\n"
                                    f"Signal: {signal}\n\n"
                                    f"Automatic trade failed."
                                )


                                send_telegram_message(
                                    message
                                )


                    else:

                        # Reset memory when there is no trade

                        LAST_SIGNAL[pair] = None


                    # Small delay between pairs

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


        print(
            f"Waiting {SCAN_INTERVAL} seconds "
            "before next scan..."
        )


        time.sleep(
            SCAN_INTERVAL
        )


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


    # Start Telegram manual bot

    telegram_thread = threading.Thread(
        target=run_telegram_bot,
        daemon=True
    )

    telegram_thread.start()


    print(
        "Manual Telegram bot started."
    )


    # Start automatic Forex scanner

    scanner_thread = threading.Thread(
        target=run_automatic_scanner,
        daemon=True
    )

    scanner_thread.start()


    print(
        "Automatic Forex scanner started."
    )


    # Keep Render service running

    while True:

        time.sleep(60)
