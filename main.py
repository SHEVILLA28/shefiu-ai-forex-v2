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

    symbol = pair.replace(
        "/",
        ""
    )

    return symbol + "m"


# =========================================================
# BOT SETTINGS
# =========================================================

TIMEFRAME = "5M"


# Scan every 6 hours

SCAN_INTERVAL = 21600


# Trade volume

TRADE_VOLUME = 0.01


# Maximum number of bot trades

MAX_OPEN_TRADES = 5


# Total profit target in USD

PROFIT_TARGET = 5.00


# Maximum total loss in USD

MAX_LOSS = -2.00


# Check profit/loss every 5 seconds

POSITION_CHECK_INTERVAL = 5


# =========================================================
# SIGNAL MEMORY
# =========================================================

LAST_SIGNAL = {}


# =========================================================
# BOT POSITION MEMORY
#
# Only positions detected after the bot places a trade
# are added to this session list.
# =========================================================

BOT_POSITION_IDS = set()

POSITION_LOCK = threading.Lock()

CLOSING_TRADES = False


# =========================================================
# GET POSITION ID
# =========================================================

def get_position_id(position):

    return position.get(
        "id"
    )


# =========================================================
# GET POSITION PROFIT
# =========================================================

def get_position_profit(position):

    try:

        return float(
            position.get(
                "profit",
                0
            )
        )

    except Exception:

        return 0.0


# =========================================================
# GET OPEN BOT POSITIONS
# =========================================================

def get_bot_positions():

    global BOT_POSITION_IDS

    positions = asyncio.run(
        get_open_positions()
    )


    open_positions = []


    current_ids = set()


    for position in positions:

        position_id = get_position_id(
            position
        )


        if position_id:

            current_ids.add(
                position_id
            )


            with POSITION_LOCK:

                if position_id in BOT_POSITION_IDS:

                    open_positions.append(
                        position
                    )


    # Remove positions that are no longer open

    with POSITION_LOCK:

        BOT_POSITION_IDS = (
            BOT_POSITION_IDS
            .intersection(current_ids)
        )


    return open_positions


# =========================================================
# COUNT BOT OPEN TRADES
# =========================================================

def get_bot_open_trade_count():

    positions = get_bot_positions()

    return len(positions)


# =========================================================
# TOTAL BOT PROFIT / LOSS
# =========================================================

def get_bot_total_profit():

    positions = get_bot_positions()

    total_profit = 0.0


    for position in positions:

        total_profit += get_position_profit(
            position
        )


    return total_profit, positions


# =========================================================
# AUTOMATIC TRADE EXECUTION
# =========================================================

def execute_trade(signal, pair):

    global CLOSING_TRADES


    if CLOSING_TRADES:

        print(
            "Trade closing is in progress. "
            "New trade ignored."
        )

        return False


    # Check maximum open trades

    try:

        open_trade_count = (
            get_bot_open_trade_count()
        )


        print(
            f"Bot open trades: "
            f"{open_trade_count}/"
            f"{MAX_OPEN_TRADES}"
        )


        if open_trade_count >= MAX_OPEN_TRADES:

            print(
                "Maximum open trades reached. "
                "No new trade will be placed."
            )

            return False


    except Exception as e:

        print(
            f"Could not check open trades: {e}"
        )

        return False


    symbol = convert_to_mt5_symbol(
        pair
    )


    try:

        # =============================================
        # GET POSITIONS BEFORE OPENING TRADE
        # =============================================

        positions_before = asyncio.run(
            get_open_positions()
        )


        ids_before = set()


        for position in positions_before:

            position_id = get_position_id(
                position
            )


            if position_id:

                ids_before.add(
                    position_id
                )


        # =============================================
        # PLACE BUY
        # =============================================

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


        # =============================================
        # PLACE SELL
        # =============================================

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


        else:

            return False


        # =============================================
        # WAIT FOR MT5 POSITION TO APPEAR
        # =============================================

        time.sleep(3)


        positions_after = asyncio.run(
            get_open_positions()
        )


        new_positions = []


        for position in positions_after:

            position_id = get_position_id(
                position
            )


            position_symbol = position.get(
                "symbol",
                ""
            )


            if (
                position_id
                and position_id not in ids_before
                and position_symbol == symbol
            ):

                new_positions.append(
                    position_id
                )


        # =============================================
        # SAVE BOT POSITION IDs
        # =============================================

        with POSITION_LOCK:

            for position_id in new_positions:

                BOT_POSITION_IDS.add(
                    position_id
                )


        if new_positions:

            print(
                f"Bot positions tracked: "
                f"{new_positions}"
            )

        else:

            print(
                "Trade request completed, but a new "
                "position ID was not detected yet."
            )


        return True


    except Exception as e:

        print(
            f"Trade execution error for "
            f"{symbol}: {e}"
        )

        return False


# =========================================================
# CLOSE BOT POSITIONS
# =========================================================

def close_bot_positions(reason, total_profit):

    global BOT_POSITION_IDS
    global CLOSING_TRADES


    if CLOSING_TRADES:

        return


    CLOSING_TRADES = True


    try:

        positions = get_bot_positions()


        if not positions:

            print(
                "No tracked bot positions to close."
            )

            return


        print(
            f"Closing {len(positions)} bot positions..."
        )


        closed_count = 0


        for position in positions:

            position_id = get_position_id(
                position
            )


            symbol = position.get(
                "symbol",
                "Unknown"
            )


            if not position_id:

                continue


            try:

                print(
                    f"Closing {symbol} "
                    f"| Position ID: {position_id}"
                )


                asyncio.run(
                    close_position(
                        position_id
                    )
                )


                closed_count += 1


                with POSITION_LOCK:

                    BOT_POSITION_IDS.discard(
                        position_id
                    )


                time.sleep(1)


            except Exception as e:

                print(
                    f"Error closing "
                    f"{symbol}: {e}"
                )


        message = (

            f"🤖 SHEFIU AI FOREX V2\n\n"

            f"🔴 AUTOMATIC TRADE CLOSE\n\n"

            f"Reason: {reason}\n"

            f"💰 Total Profit/Loss: "
            f"${total_profit:.2f}\n"

            f"📊 Positions closed: "
            f"{closed_count}"
        )


        send_telegram_message(
            message
        )


        print(
            f"Trade closing completed. "
            f"Closed: {closed_count}"
        )


    except Exception as e:

        print(
            f"Automatic closing error: {e}"
        )


    finally:

        CLOSING_TRADES = False


# =========================================================
# PROFIT / LOSS MONITOR
# =========================================================

def run_profit_monitor():

    print(
        "Profit and loss monitor started."
    )


    while True:

        try:

            if not CLOSING_TRADES:

                total_profit, positions = (
                    get_bot_total_profit()
                )


                position_count = len(
                    positions
                )


                if position_count > 0:

                    print(
                        f"Bot positions: "
                        f"{position_count} | "
                        f"Total P/L: "
                        f"${total_profit:.2f}"
                    )


                    # =====================================
                    # PROFIT TARGET
                    # =====================================

                    if total_profit >= PROFIT_TARGET:

                        print(
                            "PROFIT TARGET REACHED!"
                        )


                        close_bot_positions(
                            "Profit target reached",
                            total_profit
                        )


                    # =====================================
                    # MAXIMUM LOSS
                    # =====================================

                    elif total_profit <= MAX_LOSS:

                        print(
                            "MAXIMUM LOSS REACHED!"
                        )


                        close_bot_positions(
                            "Maximum loss reached",
                            total_profit
                        )


        except Exception as e:

            print(
                f"Profit monitor error: {e}"
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

                    # Don't open trades while closing

                    if CLOSING_TRADES:

                        print(
                            "Waiting for positions "
                            "to finish closing..."
                        )

                        break


                    # Check maximum trades

                    open_trade_count = (
                        get_bot_open_trade_count()
                    )


                    if open_trade_count >= MAX_OPEN_TRADES:

                        print(
                            f"Maximum {MAX_OPEN_TRADES} "
                            "bot trades reached."
                        )

                        break


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


                                message = format_signal(
                                    result
                                )


                                message += (

                                    "\n\n🤖 AUTOMATIC TRADE "
                                    "PLACED SUCCESSFULLY\n"

                                    f"📊 Maximum Trades: "
                                    f"{MAX_OPEN_TRADES}\n"

                                    f"💰 Profit Target: "
                                    f"${PROFIT_TARGET:.2f}\n"

                                    f"🔴 Maximum Loss: "
                                    f"${MAX_LOSS:.2f}"
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

                                    "Automatic trade was not placed
