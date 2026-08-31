import os
import time
import requests
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from config import BOT_TOKEN, CHAT_ID
from signals import get_signal


# =========================================================
# HEALTH SERVER FOR RENDER
# =========================================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        self.send_response(200)

        self.end_headers()

        self.wfile.write(
            b"SHEFIU AI FOREX V2 is running"
        )

    def log_message(self, format, *args):

        pass


def start_server():

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


threading.Thread(
    target=start_server,
    daemon=True
).start()


# =========================================================
# MARKETS
# MUST MATCH signals.py
# =========================================================

PAIRS = [

    "EUR/USD",

    "GBP/USD",

    "USD/JPY",

    "USD/CHF",

    "AUD/USD",

    "USD/CAD",

    "NZD/USD",

    "XAU/USD",

    "EUR/GBP",

    "EUR/JPY",

    "CHF/JPY",

    "AUD/JPY",

    "GBP/JPY",

    "EUR/AUD",
]


# =========================================================
# TIMEFRAMES
# =========================================================

TIMEFRAME_MINUTES = {

    "1M": 1,

    "2M": 2,

    "3M": 3,

    "5M": 5,
}


# =========================================================
# BOT SETTINGS
# =========================================================

AUTO_SCAN_ENABLED = True

CURRENT_TIMEFRAME = "5M"


auto_lock = threading.Lock()


last_auto_scan_time = 0


# =========================================================
# DUPLICATE SIGNAL PROTECTION
#
# This stops XAU/USD or any other pair from repeatedly
# sending the same BUY/SELL signal.
# =========================================================

last_signal_type = {}

last_signal_time = {}


# =========================================================
# TELEGRAM
# =========================================================

TELEGRAM_URL = (
    f"https://api.telegram.org/bot{BOT_TOKEN}"
)


def telegram_request(
    method,
    data=None
):

    try:

        response = requests.post(

            f"{TELEGRAM_URL}/{method}",

            json=data or {},

            timeout=30
        )

        return response.json()

    except Exception as e:

        print(
            "Telegram request error:",
            e
        )

        return {

            "ok": False,

            "error": str(e)
        }


# =========================================================
# SEND TELEGRAM MENU
# =========================================================

def send_menu(chat_id):

    auto_status = (

        "🟢 AUTOMATIC SCANNING: ON"

        if AUTO_SCAN_ENABLED

        else

        "🔴 AUTOMATIC SCANNING: OFF"
    )


    keyboard = [

        [
            {"text": "EUR/USD"},
            {"text": "GBP/USD"}
        ],

        [
            {"text": "USD/JPY"},
            {"text": "USD/CHF"}
        ],

        [
            {"text": "AUD/USD"},
            {"text": "USD/CAD"}
        ],

        [
            {"text": "NZD/USD"},
            {"text": "XAU/USD"}
        ],

        [
            {"text": "EUR/GBP"},
            {"text": "EUR/JPY"}
        ],

        [
            {"text": "CHF/JPY"},
            {"text": "AUD/JPY"}
        ],

        [
            {"text": "GBP/JPY"},
            {"text": "EUR/AUD"}
        ],

        [
            {"text": "📊 ALL PAIRS"}
        ],

        [
            {"text": "⏱️ 1 MIN"},
            {"text": "⏱️ 2 MIN"}
        ],

        [
            {"text": "⏱️ 3 MIN"},
            {"text": "⏱️ 5 MIN"}
        ],

        [
            {"text": "🟢 AUTO SCAN ON"},
            {"text": "🔴 AUTO SCAN OFF"}
        ]
    ]


    message = (

        "🤖 SHEFIU AI FOREX V2\n\n"

        "🟢 MANUAL TELEGRAM CONTROL: ON\n"

        f"{auto_status}\n\n"

        f"⏱️ CURRENT TIMEFRAME: "
        f"{CURRENT_TIMEFRAME}\n\n"

        "📊 Markets: "
        f"{len(PAIRS)} pairs\n\n"

        "Select a pair below for analysis.\n\n"

        "🤖 Automatic scan sends BUY/SELL "
        "signals only."
    )


    telegram_request(

        "sendMessage",

        {

            "chat_id": chat_id,

            "text": message,

            "reply_markup": {

                "keyboard": keyboard,

                "resize_keyboard": True,

                "one_time_keyboard": False
            }
        }
    )


# =========================================================
# FORMAT SIGNAL
# =========================================================

def format_signal(
    signal,
    timeframe=None
):

    if signal is None:

        return (

            "⚠️ No signal data was returned."
        )


    pair = signal.get(
        "pair",
        "Unknown"
    )


    signal_type = signal.get(
        "signal",
        "NO TRADE"
    )


    used_timeframe = (

        timeframe

        or

        signal.get(
            "timeframe",
            "N/A"
        )
    )


    # =====================================================
    # NO TRADE
    # =====================================================

    if signal_type == "NO TRADE":

        return (

            "🤖 SHEFIU AI FOREX V2\n\n"

            f"📊 Pair: {pair}\n\n"

            "⚪ SIGNAL: NO TRADE\n\n"

            f"⏱️ Timeframe: "
            f"{used_timeframe}\n\n"

            f"Reason: "
            f"{signal.get('reason', 'WAIT')}"
        )


    # =====================================================
    # BUY / SELL ICON
    # =====================================================

    if signal_type == "BUY":

        icon = "🟢"

    elif signal_type == "SELL":

        icon = "🔴"

    else:

        icon = "⚪"


    trend = signal.get(
        "trend",
        "WAIT"
    )


    if trend == "BUY":

        trend_icon = "📈"

    elif trend == "SELL":

        trend_icon = "📉"

    else:

        trend_icon = "↔️"


    return (

        "🤖 SHEFIU AI FOREX V2\n\n"

        f"📊 Pair: {pair}\n\n"

        f"{icon} SIGNAL: "
        f"{signal_type}\n\n"

        f"⏱️ Timeframe: "
        f"{used_timeframe}\n\n"

        f"🎯 Entry: "
        f"{signal.get('entry', 'N/A')}\n"

        f"✅ Take Profit: "
        f"{signal.get('take_profit', 'N/A')}\n"

        f"🛑 Stop Loss: "
        f"{signal.get('stop_loss', 'N/A')}\n\n"

        f"{trend_icon} Trend: "
        f"{trend}\n"

        f"🔥 Confidence: "
        f"{signal.get('confidence', 'N/A')}%\n\n"

        f"📝 Reason: "
        f"{signal.get('reason', 'N/A')}\n\n"

        "⚠️ Signal only. "
        "No guaranteed profit."
    )


# =========================================================
# ANALYZE ONE PAIR
# =========================================================

def analyze_pair(
    chat_id,
    pair
):

    timeframe = CURRENT_TIMEFRAME


    telegram_request(

        "sendMessage",

        {

            "chat_id": chat_id,

            "text": (

                f"🔎 Analyzing {pair}...\n\n"

                f"⏱️ Timeframe: "
                f"{timeframe}\n\n"

                "Please wait."
            )
        }
    )


    try:

        signal = get_signal(

            pair,

            timeframe
        )


        message = format_signal(

            signal,

            timeframe
        )


        telegram_request(

            "sendMessage",

            {

                "chat_id": chat_id,

                "text": message
            }
        )


        print(

            f"Analyzed {pair} "
            f"on {timeframe}"
        )


    except Exception as e:

        print(

            f"Signal error for {pair}:",
            e
        )


        telegram_request(

            "sendMessage",

            {

                "chat_id": chat_id,

                "text": (

                    f"⚠️ Could not analyze "
                    f"{pair}.\n\n"

                    f"Error: {e}"
                )
            }
        )


# =========================================================
# ANALYZE ALL PAIRS
# =========================================================

def analyze_all(
    chat_id
):

    timeframe = CURRENT_TIMEFRAME


    telegram_request(

        "sendMessage",

        {

            "chat_id": chat_id,

            "text": (

                "📊 SHEFIU AI FOREX V2\n\n"

                "🔎 Checking all supported markets...\n\n"

                f"⏱️ Timeframe: "
                f"{timeframe}\n\n"

                "Please wait."
            )
        }
    )


    for pair in PAIRS:

        try:

            signal = get_signal(

                pair,

                timeframe
            )


            if signal is None:

                continue


            message = format_signal(

                signal,

                timeframe
            )


            telegram_request(

                "sendMessage",

                {

                    "chat_id": chat_id,

                    "text": message
                }
            )


            time.sleep(1)


        except Exception as e:

            print(

                f"{pair} error:",
                e
            )


    telegram_request(

        "sendMessage",

        {

            "chat_id": chat_id,

            "text": (

                "✅ Finished checking "
                "all markets."
            )
        }
    )


# =========================================================
# CHECK IF AUTOMATIC SIGNAL SHOULD BE SENT
# =========================================================

def should_send_auto_signal(
    pair,
    timeframe,
    signal_type
):

    key = (

        pair,

        timeframe
    )


    now = time.time()


    # Timeframe duration
    cooldown = (

        TIMEFRAME_MINUTES[timeframe]
        * 60
    )


    previous_type = last_signal_type.get(
        key
    )


    previous_time = last_signal_time.get(
        key,
        0
    )


    # =====================================================
    # SAME SIGNAL PROTECTION
    #
    # Example:
    #
    # XAU/USD BUY
    #
    # If another BUY comes immediately,
    # do not send it again.
    # =====================================================

    if previous_type == signal_type:

        if now - previous_time < cooldown:

            print(

                f"Duplicate signal blocked: "

                f"{pair} "

                f"{signal_type} "

                f"{timeframe}"
            )

            return False


    # Save latest signal

    last_signal_type[key] = signal_type

    last_signal_time[key] = now


    return True


# =========================================================
# AUTOMATIC SCANNER
# =========================================================

def automatic_scan_loop():

    global last_auto_scan_time


    print(
        "🟢 Automatic scanner started."
    )


    while True:

        try:

            if not AUTO_SCAN_ENABLED:

                time.sleep(5)

                continue


            timeframe = CURRENT_TIMEFRAME


            minutes = TIMEFRAME_MINUTES[
                timeframe
            ]


            now = time.time()


            # =================================================
            # WAIT UNTIL NEXT SCAN
            # =================================================

            if last_auto_scan_time:

                elapsed = (

                    now
                    -
                    last_auto_scan_time
                )


                required_wait = (
                    minutes * 60
                )


                if elapsed < required_wait:

                    time.sleep(5)

                    continue


            with auto_lock:

                last_auto_scan_time = (
                    time.time()
                )


            print(

                "\n"

                "🔎 ========================================\n"

                f"🔎 Automatic scan started: "
                f"{timeframe}\n"

                "🔎 ========================================\n"
            )


            for pair in PAIRS:

                if not AUTO_SCAN_ENABLED:

                    break


                try:

                    signal = get_signal(

                        pair,

                        timeframe
                    )


                    if not signal:

                        continue


                    signal_type = signal.get(
                        "signal",
                        "NO TRADE"
                    )


                    # Only automatic BUY or SELL

                    if signal_type not in [

                        "BUY",

                        "SELL"

                    ]:

                        print(

                            f"{pair}: NO TRADE"
                        )

                        continue


                    # =================================================
                    # STOP DUPLICATE SIGNALS
                    # =================================================

                    allowed = should_send_auto_signal(

                        pair,

                        timeframe,

                        signal_type
                    )


                    if not allowed:

                        continue


                    message = (

                        "🔔 AUTOMATIC FOREX SIGNAL\n\n"

                        +

                        format_signal(

                            signal,

                            timeframe
                        )
                    )


                    telegram_request(

                        "sendMessage",

                        {

                            "chat_id": CHAT_ID,

                            "text": message
                        }
                    )


                    print(

                        f"🚨 AUTO SIGNAL SENT: "

                        f"{pair} | "

                        f"{signal_type} | "

                        f"{timeframe}"
                    )


                    time.sleep(1)


                except Exception as e:

                    print(

                        f"Automatic scan error "
                        f"for {pair}:",

                        e
                    )


            print(

                "\n"

                f"✅ Automatic scan finished: "
                f"{timeframe}\n"
            )


        except Exception as e:

            print(

                "Automatic scanner error:",

                e
            )


            time.sleep(10)


# =========================================================
# START AUTOMATIC SCANNER
# =========================================================

threading.Thread(

    target=automatic_scan_loop,

    daemon=True

).start()


# =========================================================
# HANDLE TELEGRAM UPDATE
# =========================================================

def handle_update(update):

    global AUTO_SCAN_ENABLED

    global CURRENT_TIMEFRAME

    global last_auto_scan_time

    global last_signal_type

    global last_signal_time


    message = update.get(
        "message"
    )


    if not message:

        return


    chat = message.get(
        "chat",
        {}
    )


    chat_id = chat.get(
        "id"
    )


    text = message.get(
        "text",
        ""
    ).strip()


    if not chat_id:

        return


    print(

        f"Telegram command: {text}"
    )


    # =====================================================
    # START
    # =====================================================
