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
    place_sell_order,
    get_open_positions,
    close_position
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
    "GBP/USD",
    "AUD/USD",
    "NZD/USD",

    "USD/JPY",
    "USD/CHF",
    "USD/CAD",

    "EUR/GBP",
    "EUR/JPY",
    "EUR/CHF",

    "GBP/JPY",
    "GBP/CHF",

    "AUD/JPY",
    "NZD/JPY"

]


# =========================================================
# METAAPI SYMBOL CONVERSION
# =========================================================

def convert_to_mt5_symbol(pair):

    symbol = pair.replace("/", "")

    return symbol + "m"


# =========================================================
# BOT SETTINGS
# =========================================================

TIMEFRAME = "5M"


# Scan every 6 hours

SCAN_INTERVAL = 21600


# Trade volume

TRADE_VOLUME = 0.01


# =========================================================
# MAXIMUM OPEN TRADES PROTECTION
# =========================================================

MAX_OPEN_TRADES = 2


# =========================================================
# AUTOMATIC PROFIT / LOSS SETTINGS
# =========================================================

# Close all positions when total profit reaches $5

TOTAL_PROFIT_TARGET = 5.00


# Close all positions when total loss reaches -$2

TOTAL_LOSS_LIMIT = -2.00


# Check positions every 5 seconds

POSITION_CHECK_INTERVAL = 5


# =========================================================
# SIGNAL MEMORY
# PREVENT DUPLICATE TRADES
# =========================================================

LAST_SIGNAL = {}


# =========================================================
# CHECK IF A NEW TRADE CAN BE OPENED
# =========================================================

def check_trade_permission():

    try:

        positions = asyncio.run(
            get_open_positions()
        )

        open_trade_count = len(positions)


        print(
            f"Currently open trades: "
            f"{open_trade_count}/{MAX_OPEN_TRADES}"
        )


        # =============================================
        # MAXIMUM TRADE LIMIT REACHED
        # =============================================

        if open_trade_count >= MAX_OPEN_TRADES:

            print(
                "Maximum open trade limit reached. "
                "No new trade will be opened."
            )

            return (
                False,
                "MAX_TRADES_REACHED",
                open_trade_count
            )


        # =============================================
        # TRADE CAN BE OPENED
        # =============================================

        return (
            True,
            "TRADE_ALLOWED",
            open_trade_count
        )


    except Exception as e:

        print(
            f"Error checking open trades: {e}"
        )


        # Safety:
        # Do not trade if position checking fails.

        return (
