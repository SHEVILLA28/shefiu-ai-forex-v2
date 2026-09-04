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
    get_open_positions
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

    symbol = pair.replace(
        "/",
        ""
    )

    return symbol + "m"


# =========================================================
# BOT SETTINGS
# =========================================================

TIMEFRAME = "5M"


# =========================================================
# SCAN SETTINGS
# =========================================================

# Scan every 6 hours

SCAN_INTERVAL = 21600


# =========================================================
# TRADE VOLUME
# =========================================================

TRADE_VOLUME = 0.02


# =========================================================
# MAXIMUM OPEN TRADES PROTECTION
# =========================================================

MAX_OPEN_TRADES = 2


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


        return (
            True,
            "TRADE_ALLOWED",
            open_trade_count
        )


    except Exception as e:

        print(
            f"Error checking open trades: {e}"
        )


        return (
            False,
            "POSITION_CHECK_FAILED",
            0
        )


# =========================================================
# AUTOMATIC TRADE EXECUTION
# WITH STOP LOSS AND TAKE PROFIT
# =========================================================

def execute_trade(result, pair):


    signal = result.get(
        "signal",
        "NO TRADE"
    )


    stop_loss = result.get(
        "stop_loss"
    )


    take_profit = result.get(
        "take_profit"
    )


    try:

        stop_loss = float(
            stop_loss
        )


        take_profit = float(
            take_profit
        )


    except Exception as e:

        print(
            f"Invalid Stop Loss or Take Profit "
            f"for {pair}: {e}"
        )


        return (
            False,
            "INVALID_SL_TP"
        )


    symbol = convert_to_mt5_symbol(
        pair
    )


    print(
        f"Trade setup for {symbol} | "
        f"Signal: {signal} | "
        f"SL: {stop_loss} | "
        f"TP: {take_profit}"
    )


    allowed, status, open_trade_count = (
        check_trade_permission()
    )


    if not allowed:


        if status == "MAX_TRADES_REACHED":

            print(
                f"Trade BLOCKED for {symbol}: "
                f"maximum {MAX_OPEN_TRADES} "
                f"open trades reached."
            )


            return (
                False,
                "MAX_TRADES_REACHED"
            )


        elif status == "POSITION_CHECK_FAILED":

            print(
                f"Trade BLOCKED for {symbol}: "
                "unable to safely check "
                "open positions."
            )


            return (
                False,
                "POSITION_CHECK_FAILED"
            )


    try:

        if signal == "BUY":

            print(
                f"Placing BUY order for {symbol}"
            )


            print(
                f"BUY Stop Loss: {stop_loss}"
            )


            print(
                f"BUY Take Profit: {take_profit}"
            )


            result_order = asyncio.run(
                place_buy_order(
                    symbol,
                    TRADE_VOLUME,
                    stop_loss,
                    take_profit
                )
            )


            print(
                f"BUY order result: "
                f"{result_order}"
            )


            return (
                True,
                "TRADE_PLACED"
            )


        elif signal == "SELL":

            print(
                f"Placing SELL order for {symbol}"
            )


            print(
                f"SELL Stop Loss: {stop_loss}"
            )


            print(
                f"SELL Take Profit: {take_profit}"
            )


            result_order = asyncio.run(
                place_sell_order(
                    symbol,
                    TRADE_VOLUME,
                    stop_loss,
                    take_profit
                )
            )


            print(
                f"SELL order result: "
                f"{result_order}"
            )


            return (
                True,
                "TRADE_PLACED"
            )


        return (
            False,
            "INVALID_SIGNAL"
        )


    except Exception as e:

        print(
            f"Trade execution error for "
            f"{symbol}: {e}"
        )


        return (
            False,
            "TRADE_FAILED"
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
                        f"Trend: "
                        f"{result.get('trend')} | "
                        f"RSI: "
                        f"{result.get('rsi')} | "
                        f"Reason: "
                        f"{result.get('reason')}"
                    )


                    if signal in ["BUY", "SELL"]:


                        previous_signal = (
                            LAST_SIGNAL.get(
                                pair
                            )
                        )


                        if previous_signal == signal:

                            print(
                                f"Duplicate {signal} "
                                f"signal ignored for "
                                f"{pair}"
                            )


                        else:

                            print(
                                f"NEW {signal} SIGNAL "
                                f"FOR {pair}"
                            )


                            trade_success, trade_status = (
                                execute_trade(
                                    result,
                                    pair
                                )
                            )


                            if trade_success:

                                LAST_SIGNAL[pair] = signal


                                print(
                                    f"{signal} trade "
                                    f"placed successfully "
                                    f"for {pair}"
                                )


                                message = format_signal(
                                    result
                                )


                                message += (
                                    "\n\n🤖 AUTOMATIC TRADE "
                                    "PLACED SUCCESSFULLY\n\n"
                                    "📊 Lot Size: 0.02\n"
                                    "🛑 Stop Loss attached\n"
                                    "✅ Take Profit attached"
                                )


                                send_telegram_message(
                                    message
                                )


                            elif (
                                trade_status
                                == "MAX_TRADES_REACHED"
                            ):

                                print(
                                    f"Trade blocked for "
                                    f"{pair}: maximum "
                                    f"trade limit reached."
                                )


                            elif (
                                trade_status
                                == "POSITION_CHECK_FAILED"
                            ):

                                print(
                                    f"Trade blocked for "
                                    f"{pair}: unable to "
                                    f"check open positions."
                                )


                            elif (
                                trade_status
                                == "INVALID_SL_TP"
                            ):

                                print(
                                    f"Trade blocked for "
                                    f"{pair}: invalid "
                                    f"Stop Loss or Take Profit."
                                )


                            else:

                                print(
                                    f"Trade FAILED "
                                    f"for {pair}"
                                )


                    else:

                        LAST_SIGNAL[pair] = None


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
            f"Waiting {SCAN_INTERVAL} "
            f"seconds before next scan..."
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


    health_thread = threading.Thread(
        target=run_health_server,
        daemon=True
    )

    health_thread.start()

    print(
        "Health server started."
    )


    telegram_thread = threading.Thread(
        target=run_telegram_bot,
        daemon=True
    )

    telegram_thread.start()

    print(
        "Manual Telegram bot started."
    )


    scanner_thread = threading.Thread(
        target=run_automatic_scanner,
        daemon=True
    )

    scanner_thread.start()

    print(
        "Automatic Forex scanner started."
    )


    while True:

        time.sleep(60)
