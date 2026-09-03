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
# FOREX PAIRS - 14 PAIRS
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

# Close all open positions when total profit reaches $5

TOTAL_PROFIT_TARGET = 5.00


# Close all open positions when total loss reaches -$2

TOTAL_LOSS_LIMIT = -2.00


# Check positions every 5 seconds

POSITION_CHECK_INTERVAL = 5


# =========================================================
# SIGNAL MEMORY
# PREVENT DUPLICATE TRADES
# =========================================================

LAST_SIGNAL = {}


# =========================================================
# CHECK NUMBER OF OPEN TRADES
# =========================================================

def can_open_new_trade():

    try:

        positions = asyncio.run(
            get_open_positions()
        )

        open_trade_count = len(positions)

        print(
            f"Currently open trades: "
            f"{open_trade_count}/{MAX_OPEN_TRADES}"
        )


        if open_trade_count >= MAX_OPEN_TRADES:

            print(
                "Maximum open trade limit reached. "
                "No new trade will be opened."
            )

            return False


        return True


    except Exception as e:

        print(
            f"Error checking open trades: {e}"
        )

        # Safety protection:
        # Do not open a trade if position checking fails.

        return False


# =========================================================
# AUTOMATIC TRADE EXECUTION
# =========================================================

def execute_trade(signal, pair):

    symbol = convert_to_mt5_symbol(pair)


    # =============================================
    # CHECK MAXIMUM OPEN TRADES FIRST
    # =============================================

    if not can_open_new_trade():

        print(
            f"Trade blocked for {symbol}: "
            "maximum open trade limit reached."
        )

        return False


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
# AUTOMATIC POSITION MONITOR
# =========================================================

def run_position_monitor():

    print(
        "Automatic profit/loss monitor started."
    )


    while True:

        try:

            positions = asyncio.run(
                get_open_positions()
            )


            if not positions:

                print(
                    "Position monitor: No open positions."
                )


            else:

                total_profit = 0.0


                for position in positions:

                    profit = float(
                        position.get(
                            "profit",
                            0
                        )
                    )

                    total_profit += profit


                print(
                    f"Total open trade profit/loss: "
                    f"${total_profit:.2f}"
                )


                # =====================================
                # PROFIT TARGET REACHED
                # =====================================

                if total_profit >= TOTAL_PROFIT_TARGET:

                    print(
                        f"PROFIT TARGET REACHED: "
                        f"${total_profit:.2f}"
                    )

                    print(
                        "Closing all open positions..."
                    )


                    for position in positions:

                        position_id = position.get("id")


                        if position_id:

                            try:

                                asyncio.run(
                                    close_position(position_id)
                                )

                            except Exception as e:

                                print(
                                    f"Error closing position "
                                    f"{position_id}: {e}"
                                )


                    send_telegram_message(
                        f"🟢 PROFIT TARGET REACHED\n\n"
                        f"Total Profit: ${total_profit:.2f}\n\n"
                        f"Closing all open trades."
                    )


                # =====================================
                # LOSS LIMIT REACHED
                # =====================================

                elif total_profit <= TOTAL_LOSS_LIMIT:

                    print(
                        f"LOSS LIMIT REACHED: "
                        f"${total_profit:.2f}"
                    )

                    print(
                        "Closing all open positions..."
                    )


                    for position in positions:

                        position_id = position.get("id")


                        if position_id:

                            try:

                                asyncio.run(
                                    close_position(position_id)
                                )

                            except Exception as e:

                                print(
                                    f"Error closing position "
                                    f"{position_id}: {e}"
                                )


                    send_telegram_message(
                        f"🔴 LOSS LIMIT REACHED\n\n"
                        f"Total Loss: ${total_profit:.2f}\n\n"
                        f"Closing all open trades."
                    )


        except Exception as e:

            print(
                f"Position monitor error: {e}"
            )


        time.sleep(
            POSITION_CHECK_INTERVAL
        )


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

                        previous_signal = LAST_SIGNAL.get(pair)


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
                                f"
