import os
import time
import threading
import requests

from http.server import HTTPServer, BaseHTTPRequestHandler

from config import BOT_TOKEN, CHAT_ID
from signals import get_signal


# =========================================================
# SHEFIU AI FOREX V2
# =========================================================


# =========================================================
# HEALTH SERVER FOR RENDER
# =========================================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        self.send_response(200)

        self.send_header(
            "Content-Type",
            "text/plain"
        )

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
# FOREX PAIRS
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
    "CHF/JPY",

    "AUD/JPY",
    "EUR/JPY",

    "GBP/JPY",
    "USD/SGD",
]


# =========================================================
# CURRENT TIMEFRAME
# =========================================================

CURRENT_TIMEFRAME = "5M"


# =========================================================
# API PROTECTION SETTINGS
# =========================================================

# Automatic scanning starts OFF.
# This prevents the bot from immediately using too many API requests.

AUTO_SCAN_ENABLED = False


# Wait 60 minutes between full automatic scans.

AUTO_SCAN_INTERVAL_SECONDS = 60 * 60


# Wait 15 seconds between pairs during automatic scanning.

AUTO_PAIR_DELAY_SECONDS = 15


# Prevent duplicate automatic signals.

AUTO_SIGNAL_COOLDOWN = 30 * 60


# Manual request cooldown.

MANUAL_REQUEST_COOLDOWN = 20


# =========================================================
# ANALYSIS PROTECTION
# =========================================================

# Only ONE market analysis can happen at a time.

ANALYSIS_LOCK = threading.Lock()


# Remember recent manual requests.

last_manual_request = {}


# Remember automatic signals.

last_auto_signal = {}


# Last automatic scan time.

last_auto_scan_time = 0


# =========================================================
# TELEGRAM
# =========================================================

TELEGRAM_URL = (
    f"https://api.telegram.org/bot{BOT_TOKEN}"
)


def telegram_request(method, data=None):

    try:

        response = requests.post(

            f"{TELEGRAM_URL}/{method}",

            json=data or {},

            timeout=40

        )

        return response.json()

    except Exception as e:

        print(
            "Telegram error:",
            e
        )

        return {

            "ok": False,

            "error": str(e)

        }


# =========================================================
# SEND MESSAGE
# =========================================================

def send_message(
    chat_id,
    text,
    reply_markup=None
):

    data = {

        "chat_id": chat_id,

        "text": text,

    }


    if reply_markup is not None:

        data[
            "reply_markup"
        ] = reply_markup


    return telegram_request(
        "sendMessage",
        data
    )


# =========================================================
# TELEGRAM MENU
# =========================================================

def send_menu(chat_id):

    if AUTO_SCAN_ENABLED:

        auto_status = (
            "🟢 AUTOMATIC SCANNING: ON"
        )

    else:

        auto_status = (
            "🔴 AUTOMATIC SCANNING: OFF"
        )


    keyboard = [

        [
            {"text": "EUR/USD"},
            {"text": "GBP/USD"},
        ],

        [
            {"text": "USD/JPY"},
            {"text": "USD/CHF"},
        ],

        [
            {"text": "AUD/USD"},
            {"text": "USD/CAD"},
        ],

        [
            {"text": "NZD/USD"},
            {"text": "XAU/USD"},
        ],

        [
            {"text": "EUR/GBP"},
            {"text": "CHF/JPY"},
        ],

        [
            {"text": "AUD/JPY"},
            {"text": "EUR/JPY"},
        ],

        [
            {"text": "GBP/JPY"},
            {"text": "USD/SGD"},
        ],

        [
            {"text": "📊 ALL PAIRS"},
        ],

        [
            {"text": "⏱️ 1 MIN"},
            {"text": "⏱️ 2 MIN"},
        ],

        [
            {"text": "⏱️ 3 MIN"},
            {"text": "⏱️ 5 MIN"},
        ],

        [
            {"text": "🟢 AUTO SCAN ON"},
            {"text": "🔴 AUTO SCAN OFF"},
        ],
    ]


    message = (

        "🤖 SHEFIU AI FOREX V2\n\n"

        "🟢 MANUAL TELEGRAM CONTROL: ON\n"

        f"{auto_status}\n\n"

        f"⏱️ CURRENT TIMEFRAME: "
        f"{CURRENT_TIMEFRAME}\n\n"

        "📊 Select a Forex pair below.\n\n"

        "🤖 Automatic scanning checks "
        "supported Forex pairs.\n\n"

        "⚠️ NO OTC MARKETS.\n\n"

        "⚠️ Please wait for an analysis "
        "to finish before requesting another pair.\n\n"

        "⚠️ Signals are not guaranteed profit."
    )


    send_message(

        chat_id,

        message,

        {

            "keyboard": keyboard,

            "resize_keyboard": True,

            "one_time_keyboard": False,

        }

    )


# =========================================================
# FORMAT SIGNAL
# =========================================================

def format_signal(
    signal,
    timeframe=None
):

    if not signal:

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

            f"📈 Trend: "
            f"{signal.get('trend', 'WAIT')}\n\n"

            f"📝 Reason: "
            f"{signal.get('reason', 'WAIT')}\n\n"

            "⚠️ Signal only. "
            "No guaranteed profit."

        )


    # =====================================================
    # SIGNAL ICON
    # =====================================================

    if signal_type == "BUY":

        signal_icon = "🟢"

    elif signal_type == "SELL":

        signal_icon = "🔴"

    else:

        signal_icon = "⚪"


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

        f"{signal_icon} SIGNAL: "
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
        f"{trend}\n\n"

        f"📊 RSI: "
        f"{signal.get('rsi', 'N/A')}\n"

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

    global CURRENT_TIMEFRAME


    timeframe = CURRENT_TIMEFRAME


    key = (
        pair,
        timeframe
    )


    now = time.time()


    previous_time = last_manual_request.get(
        key,
        0
    )


    # Prevent repeated requests too quickly.

    if now - previous_time < MANUAL_REQUEST_COOLDOWN:

        remaining = int(
            MANUAL_REQUEST_COOLDOWN
            -
            (now - previous_time)
        )


        send_message(

            chat_id,

            (

                f"⏳ Please wait about "
                f"{remaining} seconds before "
                f"checking {pair} again.\n\n"

                "This protects the market-data API."

            )

        )

        return


    # Do not queue many analyses.

    if not ANALYSIS_LOCK.acquire(
        blocking=False
    ):

        send_message(

            chat_id,

            (

                "⏳ Another Forex analysis is "
                "currently running.\n\n"

                "Please wait for it to finish "
                "before selecting another pair."

            )

        )

        return


    last_manual_request[key] = now


    try:

        send_message(

            chat_id,

            (

                f"🔎 Analyzing {pair}...\n\n"

                f"⏱️ Timeframe: "
                f"{timeframe}\n\n"

                "Please wait."

            )

        )


        signal = get_signal(
            pair,
            timeframe
        )


        message = format_signal(
            signal,
            timeframe
        )


        send_message(
            chat_id,
            message
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


        send_message(

            chat_id,

            (

                f"⚠️ Could not analyze "
                f"{pair}.\n\n"

                "Please wait a little and try again."

            )

        )


    finally:

        ANALYSIS_LOCK.release()


# =========================================================
# ANALYZE ALL PAIRS
# =========================================================

def analyze_all(chat_id):

    timeframe = CURRENT_TIMEFRAME


    send_message(

        chat_id,

        (

            "📊 SHEFIU AI FOREX V2\n\n"

            "🔎 Checking all Forex pairs.\n\n"

            "⚠️ This takes time because "
            "requests are slowed down to "
            "protect the market-data API.\n\n"

            f"⏱️ Timeframe: "
            f"{timeframe}"

        )

    )


    for pair in PAIRS:

        acquired = ANALYSIS_LOCK.acquire(
            timeout=60
        )


        if not acquired:

            continue


        try:

            signal = get_signal(
                pair,
                timeframe
            )


            message = format_signal(
                signal,
                timeframe
            )


            send_message(
                chat_id,
                message
            )


        except Exception as e:

            print(
                f"Error analyzing {pair}:",
                e
            )


        finally:

            ANALYSIS_LOCK.release()


        # Important API protection.

        time.sleep(
            AUTO_PAIR_DELAY_SECONDS
        )


    send_message(

        chat_id,

        "✅ Finished checking all pairs."

    )


# =========================================================
# DUPLICATE SIGNAL PROTECTION
# =========================================================

def should_send_auto_signal(
    pair,
    timeframe,
    signal
):

    signal_type = signal.get(
        "signal",
        "NO TRADE"
    )


    if signal_type not in (
        "BUY",
        "SELL"
    ):

        return False


    key = (
        pair,
        timeframe
    )


    now = time.time()


    previous = last_auto_signal.get(
        key
    )


    if previous is None:

        last_auto_signal[key] = {

            "signal": signal_type,

            "time": now

        }

        return True


    previous_signal = previous.get(
        "signal"
    )


    previous_time = previous.get(
        "time",
        0
    )


    # Send immediately if direction changes.

    if previous_signal != signal_type:

        last_auto_signal[key] = {

            "signal": signal_type,

            "time": now

        }

        return True


    # Same signal cooldown.

    if now - previous_time >= AUTO_SIGNAL_COOLDOWN:

        last_auto_signal[key] = {

            "signal": signal_type,

            "time": now

        }

        return True


    return False


# =========================================================
# AUTOMATIC SCANNER
# =========================================================

def automatic_scan_loop():

    global last_auto_scan_time


    print(
        "🟢 Automatic scanner system ready."
    )


    while True:

        try:

            # Scanner OFF.

            if not AUTO_SCAN_ENABLED:

                time.sleep(10)

                continue


            now = time.time()


            if last_auto_scan_time != 0:

                elapsed = (
                    now
                    -
                    last_auto_scan_time
                )


                if elapsed < AUTO_SCAN_INTERVAL_SECONDS:

                    time.sleep(10)

                    continue


            last_auto_scan_time = time.time()


            timeframe = CURRENT_TIMEFRAME


            print(

                f"🔎 Automatic scan started: "
                f"{timeframe}"

            )


            for pair in PAIRS:

                if not AUTO_SCAN_ENABLED:

                    break


                acquired = ANALYSIS_LOCK.acquire(
                    timeout=60
                )


                if not acquired:

                    continue


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


                    if signal_type not in (

                        "BUY",

                        "SELL"

                    ):

                        continue


                    if not should_send_auto_signal(

                        pair,

                        timeframe,

                        signal

                    ):

                        continue


                    auto_message = (

                        "🔔 AUTOMATIC FOREX SIGNAL\n\n"

                        +

                        format_signal(
                            signal,
                            timeframe
                        )

                    )


                    send_message(

                        CHAT_ID,

                        auto_message

                    )


                    print(

                        f"🚨 AUTO SIGNAL SENT: "
                        f"{pair} "
                        f"{signal_type}"

                    )


                except Exception as e:

                    print(

                        f"Automatic scan error "
                        f"for {pair}:",
                        e

                    )


                finally:

                    ANALYSIS_LOCK.release()


                # Slow down API requests.

                time.sleep(
                    AUTO_PAIR_DELAY_SECONDS
                )


            print(
                "✅ Automatic scan finished."
            )


        except Exception as e:

            print(
                "Automatic scanner error:",
                e
            )

            time.sleep(30)


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

    if text == "/start":

        send_menu(chat_id)

        return


    # =====================================================
    # MENU
    # =====================================================

    if text == "/menu":

        send_menu(chat_id)

        return


    # =====================================================
    # TIMEFRAME
    # =====================================================

    timeframe_buttons = {

        "⏱️ 1 MIN": "1M",

        "⏱️ 2 MIN": "2M",

        "⏱️ 3 MIN": "3M",

        "⏱️ 5 MIN": "5M",

    }


    if text in timeframe_buttons:

        CURRENT_TIMEFRAME = (
            timeframe_buttons[text]
        )


        last_auto_scan_time = 0


        send_message(

            chat_id,

            (

                f"⏱️ Timeframe changed to "
                f"{CURRENT_TIMEFRAME}.\n\n"

                "Manual and automatic analysis "
                "will use this timeframe."

            )

        )


        send_menu(chat_id)

        return


    # =====================================================
    # AUTO SCAN ON
    # =====================================================

    if text == "🟢 AUTO SCAN ON":

        AUTO_SCAN_ENABLED = True

        last_auto_scan_time = 0


        send_message(

            chat_id,

            (

                "🟢 AUTOMATIC SCANNING: ON\n\n"

                f"⏱️ Timeframe: "
                f"{CURRENT_TIMEFRAME}\n\n"

                "The bot will scan Forex pairs "
                "slowly to protect the "
                "market-data API."

            )

        )


        send_menu(chat_id)

        return


    # =====================================================
    # AUTO SCAN OFF
    # =====================================================

    if text == "🔴 AUTO SCAN OFF":

        AUTO_SCAN_ENABLED = False


        send_message(

            chat_id,

            (

                "🔴 AUTOMATIC SCANNING: OFF\n\n"

                "Manual Forex analysis "
                "is still available."

            )

        )


        send_menu(chat_id)

        return


    # =====================================================
    # ALL PAIRS
    # =====================================================

    if text == "📊 ALL PAIRS":

        threading.Thread(

            target=analyze_all,

            args=(chat_id,),

            daemon=True

        ).start()


        return


    # =====================================================
    # SINGLE PAIR
    # =====================================================

    if text in PAIRS:

        threading.Thread(

            target=analyze_pair,

            args=(chat_id, text),

            daemon=True

        ).start()


        return


    # =====================================================
    # UNKNOWN COMMAND
    # =====================================================

    send_message(

        chat_id,

        (

            "❓ I don't understand that command.\n\n"

            "Press /menu to open the "
            "Forex menu."

        )

    )


# =========================================================
# TELEGRAM LOOP
# =========================================================

def telegram_loop():

    print(
        "🟢 Telegram control system started."
    )


    offset = None


    while True:

        try:

            data = {

                "timeout": 25

            }


            if offset is not None:

                data["offset"] = offset


            result = telegram_request(

                "getUpdates",

                data

            )


            if result.get("ok"):

                updates = result.get(

                    "result",

                    []

                )


                for update in updates:

                    offset = (

                        update["update_id"]

                        + 1

                    )


                    handle_update(
                        update
                    )


            else:

                time.sleep(5)


        except Exception as e:

            print(
                "Telegram loop error:",
                e
            )

            time.sleep(10)


# =========================================================
# START BOT
# =========================================================

print()

print("=" * 50)

print("🤖 SHEFIU AI FOREX V2")

print("=" * 50)

print(
    "🟢 Manual Telegram control ready"
)

print(
    "🔴 Automatic scanning starts OFF"
)

print(
    f"📊 Markets: {len(PAIRS)} pairs"
)

print(
    f"⏱️ Timeframe: "
    f"{CURRENT_TIMEFRAME}"
)

print(
    "📱 Waiting for Telegram commands..."
)

print("=" * 50)


# Send menu when bot starts.

send_menu(CHAT_ID)


# Start Telegram control loop.

telegram_loop()
