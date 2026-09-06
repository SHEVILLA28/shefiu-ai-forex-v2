import os
import time
import threading
import asyncio

from http.server import HTTPServer, BaseHTTPRequestHandler

import requests

from config import BOT_TOKEN, CHAT_ID
from telegram_bot import format_signal, run_telegram_bot
from signals import get_signal

from metaapi_trader import (
    place_buy_order,
    place_sell_order,
    get_open_positions
)


# =========================================================
# SHEFIU AI FOREX V2
# AUTOMATIC + MANUAL + TELEGRAM + METAAPI TRADING
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
# AUTOMATIC SCANNER CONTROL
# =========================================================

AUTO_SCAN_ENABLED = False

AUTO_TIMEFRAME = "5M"

AUTO_SETTINGS_LOCK = threading.Lock()


# =========================================================
# SET AUTOMATIC SCANNER
# =========================================================

def set_auto_scan(
    enabled=None,
    timeframe=None
):

    global AUTO_SCAN_ENABLED
    global AUTO_TIMEFRAME


    with AUTO_SETTINGS_LOCK:

        if enabled is not None:

            AUTO_SCAN_ENABLED = bool(
                enabled
            )


        if timeframe is not None:

            valid_timeframes = [

                "1M",
                "2M",
                "3M",
                "5M"

            ]


            if timeframe in valid_timeframes:

                AUTO_TIMEFRAME = timeframe


        print(

            f"Automatic scanner settings | "
            f"Enabled: {AUTO_SCAN_ENABLED} | "
            f"Timeframe: {AUTO_TIMEFRAME}"

        )


# =========================================================
# GET AUTOMATIC SCANNER SETTINGS
# =========================================================

def get_auto_settings():

    with AUTO_SETTINGS_LOCK:

        return (

            AUTO_SCAN_ENABLED,
            AUTO_TIMEFRAME

        )


# =========================================================
# GET SCAN INTERVAL
# =========================================================

def get_scan_interval(timeframe):

    intervals = {

        "1M": 60,

        "2M": 120,

        "3M": 180,

        "5M": 300

    }


    return intervals.get(
        timeframe,
        300
    )


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
# TRADE SETTINGS
# =========================================================

TRADE_VOLUME = 0.02


# =========================================================
# MAXIMUM OPEN TRADES PROTECTION
# =========================================================

MAX_OPEN_TRADES = 2


# =========================================================
# TRADE COOLDOWN PROTECTION
# =========================================================

TRADE_COOLDOWN = 1800


# =========================================================
# SIGNAL / TRADE MEMORY
# =========================================================

LAST_SIGNAL = {}

LAST_TRADE_TIME = {}


# =========================================================
# CHECK IF A SYMBOL ALREADY HAS OPEN TRADE
# =========================================================

def symbol_has_open_position(
    positions,
    symbol
):

    for position in positions:

        position_symbol = position.get(
            "symbol",
            ""
        )


        if position_symbol.upper() == symbol.upper():

            return True


    return False


# =========================================================
# CHECK TRADE COOLDOWN
# =========================================================

def check_trade_cooldown(symbol):

    last_trade = LAST_TRADE_TIME.get(
        symbol,
        0
    )


    if last_trade == 0:

        return True, 0


    elapsed = time.time() - last_trade


    if elapsed >= TRADE_COOLDOWN:

        return True, 0


    remaining = int(
        TRADE_COOLDOWN - elapsed
    )


    return False, remaining


# =========================================================
# CHECK IF A NEW TRADE CAN BE OPENED
# =========================================================

def check_trade_permission(symbol):

    try:

        positions = asyncio.run(
            get_open_positions()
        )


        open_trade_count = len(
            positions
        )


        print(
            f"Currently open trades: "
            f"{open_trade_count}/{MAX_OPEN_TRADES}"
        )


        if open_trade_count >= MAX_OPEN_TRADES:

            print(
                "Maximum open trade limit reached."
            )


            return (
                False,
                "MAX_TRADES_REACHED",
                open_trade_count
            )


        if symbol_has_open_position(
            positions,
            symbol
        ):

            print(
                f"Trade BLOCKED: {symbol} "
                "already has an open position."
            )


            return (
                False,
                "SYMBOL_ALREADY_OPEN",
                open_trade_count
            )


        cooldown_allowed, remaining = (
            check_trade_cooldown(
                symbol
            )
        )


        if not cooldown_allowed:

            print(
                f"Trade BLOCKED for {symbol}: "
                f"cooldown active for "
                f"{remaining} more seconds."
            )


            return (
                False,
                "TRADE_COOLDOWN",
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


    if signal not in [

        "BUY",
        "SELL"

    ]:

        return (
            False,
            "INVALID_SIGNAL"
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
        check_trade_permission(
            symbol
        )
    )


    if not allowed:

        print(
            f"Trade permission denied: {status}"
        )


        return (
            False,
            status
        )


    try:

        if signal == "BUY":

            print(
                f"Placing BUY order for {symbol}"
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


        elif signal == "SELL":

            print(
                f"Placing SELL order for {symbol}"
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


        LAST_TRADE_TIME[symbol] = (
            time.time()
        )


        return (
            True,
            "TRADE_PLACED"
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
        "Automatic Forex scanner thread started."
    )


    while True:

        try:

            enabled, timeframe = (
                get_auto_settings()
            )


            # =============================================
            # AUTO SCAN OFF
            # =============================================

            if not enabled:

                print(
                    "Automatic scanner is OFF. "
                    "Waiting for AUTO SCAN ON..."
                )


                time.sleep(5)

                continue


            # =============================================
            # AUTO SCAN ON
            # =============================================

            print(
                "===================================="
            )

            print(
                "Starting automatic Forex scan..."
            )

            print(
                f"Selected timeframe: {timeframe}"
            )

            print(
                "===================================="
            )


            for pair in FOREX_PAIRS:

                # Check again in case AUTO OFF
                # was pressed during scanning

                enabled, current_timeframe = (
                    get_auto_settings()
                )


                if not enabled:

                    print(
                        "AUTO SCAN turned OFF."
                    )

                    break


                try:

                    print(
                        f"Analyzing {pair} | "
                        f"{current_timeframe}"
                    )


                    result = get_signal(

                        pair,
                        current_timeframe

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
                        f"Confidence: "
                        f"{result.get('confidence')}%"

                    )


                    # =====================================
                    # BUY OR SELL SIGNAL
                    # =====================================

                    if signal in [

                        "BUY",
                        "SELL"

                    ]:

                        signal_key = (
                            f"{pair}_{current_timeframe}"
                        )


                        previous_signal = (
                            LAST_SIGNAL.get(
                                signal_key
                            )
                        )


                        # Duplicate protection

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

                                LAST_SIGNAL[
                                    signal_key
                                ] = signal


                                message = format_signal(
                                    result
                                )


                                message += (

                                    "\n\n"

                                    "🤖 AUTOMATIC TRADE "
                                    "PLACED SUCCESSFULLY\n\n"

                                    f"📊 MT5 Symbol: "
                                    f"{convert_to_mt5_symbol(pair)}\n"

                                    f"📦 Lot Size: "
                                    f"{TRADE_VOLUME}\n"

                                    "🛡 Trade Protection: ACTIVE\n"

                                    "🛑 Stop Loss: ATTACHED\n"

                                    "✅ Take Profit: ATTACHED\n"

                                    f"🔒 Maximum Open Trades: "
                                    f"{MAX_OPEN_TRADES}"

                                )


                                send_telegram_message(
                                    message
                                )


                            else:

                                print(

                                    f"Trade not placed for "
                                    f"{pair}: "
                                    f"{trade_status}"

                                )


                    # =====================================
                    # NO TRADE
                    # =====================================

                    else:

                        signal_key = (
                            f"{pair}_{current_timeframe}"
                        )


                        LAST_SIGNAL[
                            signal_key
                        ] = None


                    # API protection

                    time.sleep(3)


                except Exception as e:

                    print(
                        f"Scanner error for "
                        f"{pair}: {e}"
                    )


                    time.sleep(3)


            # =============================================
            # WAIT FOR NEXT SCAN
            # =============================================

            enabled, timeframe = (
                get_auto_settings()
            )


            if enabled:

                scan_interval = (
                    get_scan_interval(
                        timeframe
                    )
                )


                print(
                    "===================================="
                )

                print(
                    "Forex scan completed."
                )

                print(
                    f"Waiting {scan_interval} seconds "
                    "before next scan..."
                )

                print(
                    "===================================="
                )


                # Check AUTO ON/OFF every 5 seconds
                # while waiting

                waited = 0


                while waited < scan_interval:

                    enabled, _ = (
                        get_auto_settings()
                    )


                    if not enabled:

                        print(
                            "AUTO SCAN turned OFF "
                            "while waiting."
                        )

                        break


                    time.sleep(5)

                    waited += 5


        except Exception as e:

            print(
                f"Automatic scanner error: {e}"
            )


            time.sleep(5)


# =========================================================
# START BOT
# =========================================================

if __name__ == "__main__":

    print(
        "===================================="
    )

    print(
        "Starting SHEFIU AI FOREX V2..."
    )

    print(
        "Automatic Trading System: READY"
    )

    print(
        "Automatic Scanner: OFF"
    )

    print(
        f"Trade Volume: {TRADE_VOLUME}"
    )

    print(
        f"Maximum Open Trades: "
        f"{MAX_OPEN_TRADES}"
    )

    print(
        f"Trade Cooldown: "
        f"{TRADE_COOLDOWN} seconds"
    )

    print(
        "===================================="
    )


    # =============================================
    # START HEALTH SERVER
    # =============================================

    health_thread = threading.Thread(

        target=run_health_server,

        daemon=True

    )


    health_thread.start()


    print(
        "Health server started."
    )


    # =============================================
    # START AUTOMATIC SCANNER
    # ONLY ONE THREAD
    # =============================================

    scanner_thread = threading.Thread(

        target=run_automatic_scanner,

        daemon=True

    )


    scanner_thread.start()


    print(
        "Automatic scanner thread started."
    )


    # =============================================
    # START TELEGRAM BOT
    # =============================================

    telegram_thread = threading.Thread(

        target=run_telegram_bot,

        daemon=True

    )


    telegram_thread.start()


    print(
        "Telegram bot started."
    )


    # =============================================
    # KEEP BOT RUNNING
    # =============================================

    while True:

        time.sleep(60)
