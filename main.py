import os
import time
import threading
import asyncio

from http.server import HTTPServer, BaseHTTPRequestHandler

import requests

from config import BOT_TOKEN, CHAT_ID

from telegram_bot import (
    format_signal,
    run_telegram_bot
)

from signals import get_signal

from bot_control import get_auto_settings

from market_data import resolve_mt5_symbol

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
# DEFAULT SETTINGS
# =========================================================

TIMEFRAME = os.getenv("DEFAULT_TIMEFRAME", "5M").upper()


# =========================================================
# SCAN SETTINGS
# =========================================================

SCAN_INTERVAL = max(60, int(os.getenv("SCAN_INTERVAL_SECONDS", "300")))


# =========================================================
# TRADE SETTINGS
# =========================================================

TRADE_VOLUME = float(os.getenv("TRADE_VOLUME", "0.02"))


# =========================================================
# MAXIMUM OPEN TRADES PROTECTION
# =========================================================

MAX_OPEN_TRADES = max(1, int(os.getenv("MAX_OPEN_TRADES", "2")))


# =========================================================
# TRADE COOLDOWN PROTECTION
# =========================================================

TRADE_COOLDOWN = max(0, int(os.getenv("TRADE_COOLDOWN_SECONDS", "1800")))


# =========================================================
# SIGNAL / TRADE MEMORY
# =========================================================

LAST_SIGNAL = {}

LAST_TRADE_TIME = {}


# =========================================================
# METAAPI SYMBOL CONVERSION
# =========================================================

def convert_to_mt5_symbol(pair):

    # Resolve the exact symbol exposed by the connected Exness MT5 account.
    # Do not guess a broker suffix such as "m".
    try:
        symbol = resolve_mt5_symbol(pair)
        print(f"MT5 symbol resolved: {pair} -> {symbol}")
        return symbol
    except Exception as e:
        print(f"MT5 symbol resolution failed for {pair}: {e}")
        return str(pair).upper().replace("/", "").replace(" ", "")


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


        # =============================================
        # MAXIMUM OPEN TRADES PROTECTION
        # =============================================

        if open_trade_count >= MAX_OPEN_TRADES:

            print(
                "Maximum open trade limit reached."
            )


            return (

                False,

                "MAX_TRADES_REACHED",

                open_trade_count

            )


        # =============================================
        # SAME SYMBOL PROTECTION
        # =============================================

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


        # =============================================
        # TRADE COOLDOWN PROTECTION
        # =============================================

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
# METAAPI TRADE RESULT VALIDATION
# =========================================================

def _trade_result_success(result):
    if not isinstance(result, dict):
        return False

    code = str(result.get("stringCode", "")).upper()

    if not code:
        return False

    success_codes = {
        "TRADE_RETCODE_DONE",
        "TRADE_RETCODE_DONE_PARTIAL",
        "DONE",
        "FILLED",
        "PLACED",
        "OK",
    }

    return code in success_codes


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


    # =============================================
    # VALID SIGNAL CHECK
    # =============================================

    if signal not in [

        "BUY",

        "SELL"

    ]:

        return (

            False,

            "INVALID_SIGNAL"

        )


    # =============================================
    # VALIDATE SL AND TP
    # =============================================

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

        return (False, "INVALID_SL_TP")

    try:
        entry = float(result.get("entry"))
    except Exception:
        return (False, "INVALID_ENTRY")

    if signal == "BUY" and not (stop_loss < entry < take_profit):
        print(f"Invalid BUY levels for {pair}: SL={stop_loss}, entry={entry}, TP={take_profit}")
        return (False, "INVALID_SL_TP_DIRECTION")

    if signal == "SELL" and not (take_profit < entry < stop_loss):
        print(f"Invalid SELL levels for {pair}: SL={stop_loss}, entry={entry}, TP={take_profit}")
        return (False, "INVALID_SL_TP_DIRECTION")

    # =============================================
    # CONVERT SYMBOL
    # =============================================

    symbol = convert_to_mt5_symbol(
        pair
    )


    print(
        f"Trade setup for {symbol} | "
        f"Signal: {signal} | "
        f"SL: {stop_loss} | "
        f"TP: {take_profit}"
    )


    # =============================================
    # CHECK TRADE PROTECTION
    # =============================================

    allowed, status, open_trade_count = (
        check_trade_permission(
            symbol
        )
    )


    if not allowed:

        print(
            f"Trade permission denied: "
            f"{status}"
        )


        return (

            False,

            status

        )


    try:

        # =========================================
        # BUY ORDER
        # =========================================

        if signal == "BUY":

            print(
                f"Placing BUY order "
                f"for {symbol}"
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

            if not _trade_result_success(result_order):
                return (False, "TRADE_REJECTED")


        # =========================================
        # SELL ORDER
        # =========================================

        elif signal == "SELL":

            print(
                f"Placing SELL order "
                f"for {symbol}"
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

            if not _trade_result_success(result_order):
                return (False, "TRADE_REJECTED")


        # =============================================
        # SAVE TRADE TIME
        # =============================================

        LAST_TRADE_TIME[symbol] = (
            time.time()
        )


        return (

            True,

            "TRADE_PLACED"

        )


    except Exception as e:

        print(
            f"Trade execution error "
            f"for {symbol}: {e}"
        )


        return (

            False,

            "TRADE_FAILED"

        )


# =========================================================
# WAIT FOR NEXT AUTO SCAN
# =========================================================

def wait_for_next_scan():

    elapsed = 0


    while elapsed < SCAN_INTERVAL:

        auto_settings = get_auto_settings()


        # Stop immediately if AUTO is OFF

        if not auto_settings.get(
            "enabled",
            False
        ):

            return


        time.sleep(5)

        elapsed += 5


# =========================================================
# AUTOMATIC FOREX SCANNER
# =========================================================

def run_automatic_scanner():

    print(
        "🤖 Automatic Forex scanner is ready."
    )


    while True:

        try:

            # =============================================
            # GET CURRENT AUTO SETTINGS
            # =============================================

            auto_settings = get_auto_settings()


            auto_enabled = auto_settings.get(
                "enabled",
                False
            )


            auto_timeframe = auto_settings.get(
                "timeframe",
                TIMEFRAME
            )


            selected_pairs = auto_settings.get(
                "pairs",
                []
            )


            # =============================================
            # AUTOMATIC MODE OFF
            # =============================================

            if not auto_enabled:

                time.sleep(5)

                continue


            # =============================================
            # NO PAIRS SELECTED
            # =============================================

            if not selected_pairs:

                print(
                    "⚠️ Automatic mode is ON "
                    "but no Forex pairs are selected."
                )

                time.sleep(5)

                continue


            # =============================================
            # AUTOMATIC MODE ON
            # =============================================

            print(
                "===================================="
            )

            print(
                "🤖 AUTOMATIC MODE: ON"
            )

            print(
                f"⏱ AUTO TIMEFRAME: "
                f"{auto_timeframe}"
            )

            print(
                f"📊 SELECTED PAIRS: "
                f"{selected_pairs}"
            )

            print(
                "Starting Forex market scan..."
            )

            print(
                "===================================="
            )


            # =============================================
            # SCAN ONLY SELECTED FOREX PAIRS
            # =============================================

            for pair in selected_pairs:

                try:

                    # =====================================
                    # CHECK AUTO STATUS AGAIN
                    # =====================================

                    auto_settings = get_auto_settings()


                    if not auto_settings.get(
                        "enabled",
                        False
                    ):

                        print(
                            "🔴 Automatic mode turned OFF."
                        )

                        break


                    # =====================================
                    # CHECK CURRENT SELECTED PAIRS
                    # =====================================

                    current_pairs = auto_settings.get(
                        "pairs",
                        []
                    )


                    if pair not in current_pairs:

                        print(
                            f"Skipping {pair} "
                            "because it was removed."
                        )

                        continue


                    # =====================================
                    # GET CURRENT TIMEFRAME
                    # =====================================

                    auto_timeframe = (
                        auto_settings.get(
                            "timeframe",
                            TIMEFRAME
                        )
                    )


                    print(
                        f"🔍 Analyzing {pair} | "
                        f"{auto_timeframe}"
                    )


                    # =====================================
                    # GET SIGNAL
                    # =====================================

                    result = get_signal(
                        pair,
                        auto_timeframe
                    )

                    signal = result.get(
                        "signal",
                        "NO TRADE"
                    )


                    print(
                        f"Result for {pair}: "
                        f"{signal} | "
                        f"Timeframe: "
                        f"{auto_timeframe} | "
                        f"Trend: "
                        f"{result.get('trend')} | "
                        f"RSI: "
                        f"{result.get('rsi')} | "
                        f"Confidence: "
                        f"{result.get('confidence')}%"
                    )


                    # =====================================
                    # UNIQUE SIGNAL KEY
                    # =====================================

                    signal_key = (
                        f"{pair}_{auto_timeframe}"
                    )


                    # =====================================
                    # BUY OR SELL SIGNAL
                    # =====================================

                    if signal in [

                        "BUY",

                        "SELL"

                    ]:


                        previous_signal = (
                            LAST_SIGNAL.get(
                                signal_key
                            )
                        )


                        # =================================
                        # DUPLICATE SIGNAL PROTECTION
                        # =================================

                        if previous_signal == signal:

                            print(
                                f"Duplicate {signal} "
                                f"signal ignored for "
                                f"{pair} | "
                                f"{auto_timeframe}"
                            )


                        else:

                            print(
                                f"🆕 NEW {signal} SIGNAL "
                                f"FOR {pair} | "
                                f"{auto_timeframe}"
                            )


                            # =============================
                            # EXECUTE TRADE
                            # =============================

                            trade_success, trade_status = (
                                execute_trade(
                                    result,
                                    pair
                                )
                            )


                            # =============================
                            # TRADE SUCCESS
                            # =============================

                            if trade_success:

                                LAST_SIGNAL[
                                    signal_key
                                ] = signal


                                print(
                                    f"✅ {signal} trade "
                                    f"placed successfully "
                                    f"for {pair}"
                                )


                                message = format_signal(
                                    result
                                )


                                message += (

                                    "\n\n"

                                    "🤖 AUTOMATIC TRADE "
                                    "PLACED SUCCESSFULLY\n\n"

                                    f"📊 MT5 Symbol: "
                                    f"{convert_to_mt5_symbol(pair)}\n"

                                    f"⏱ Timeframe: "
                                    f"{auto_timeframe}\n"

                                    f"📦 Lot Size: "
                                    f"{TRADE_VOLUME}\n\n"

                                    "🛡 Trade Protection: "
                                    "ACTIVE\n"

                                    "🛑 Stop Loss: "
                                    "ATTACHED\n"

                                    "✅ Take Profit: "
                                    "ATTACHED\n"

                                    f"🔒 Maximum Open Trades: "
                                    f"{MAX_OPEN_TRADES}"

                                )


                                send_telegram_message(
                                    message
                                )


                            # =============================
                            # TRADE FAILED
                            # =============================

                            else:

                                print(
                                    f"❌ Trade not placed "
                                    f"for {pair}: "
                                    f"{trade_status}"
                                )


                    # =====================================
                    # NO TRADE
                    # =====================================

                    else:

                        LAST_SIGNAL[
                            signal_key
                        ] = None


                    # =====================================
                    # API PROTECTION
                    # =====================================

                    time.sleep(3)


                except Exception as e:

                    print(
                        f"Scanner error for "
                        f"{pair}: {e}"
                    )

                    time.sleep(3)


            # =============================================
            # SCAN COMPLETED
            # =============================================

            print(
                "===================================="
            )

            print(
                "Forex scan completed."
            )

            print(
                "===================================="
            )


        except Exception as e:

            print(
                f"Automatic scanner error: {e}"
            )


        # =============================================
        # WAIT FOR NEXT SCAN
        # =============================================

        auto_settings = get_auto_settings()


        if auto_settings.get(
            "enabled",
            False
        ):

            print(
                f"Waiting {SCAN_INTERVAL} seconds "
                f"before next scan..."
            )


            wait_for_next_scan()


        else:

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
        "Manual Telegram System: READY"
    )

    print(
        f"Trade Volume: "
        f"{TRADE_VOLUME}"
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
        f"Scan Interval: "
        f"{SCAN_INTERVAL} seconds"
    )

    print(
        "===================================="
    )


    # =====================================================
    # START HEALTH SERVER
    # =====================================================

    health_thread = threading.Thread(

        target=run_health_server,

        daemon=True

    )


    health_thread.start()


    print(
        "✅ Health server started."
    )


    # =====================================================
    # START AUTOMATIC SCANNER
    # =====================================================

    scanner_thread = threading.Thread(

        target=run_automatic_scanner,

        daemon=True

    )


    scanner_thread.start()


    print(
        "✅ Automatic Forex scanner started."
    )


    # =====================================================
    # START TELEGRAM BOT
    # =====================================================

    telegram_thread = threading.Thread(

        target=run_telegram_bot,

        daemon=True

    )


    telegram_thread.start()


    print(
        "✅ Telegram control bot started."
    )


    # =====================================================
    # KEEP BOT RUNNING
    # =====================================================

    while True:

        time.sleep(60)
