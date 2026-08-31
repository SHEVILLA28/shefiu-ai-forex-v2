import os
import time
import threading
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler

from config import BOT_TOKEN, CHAT_ID
from signals import get_signal


# =========================================================
# HEALTH SERVER FOR RENDER
# =========================================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
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

    print(f"Health server running on port {port}")

    server.serve_forever()


threading.Thread(
    target=start_server,
    daemon=True
).start()


# =========================================================
# FOREX MARKETS
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
# TIMEFRAMES
# =========================================================

TIMEFRAME_MINUTES = {

    "1M": 1,
    "2M": 2,
    "3M": 3,
    "5M": 5,
}


CURRENT_TIMEFRAME = "5M"


# =========================================================
# AUTOMATIC SCANNER
# =========================================================

AUTO_SCAN_ENABLED = True

auto_lock = threading.Lock()

last_auto_scan_time = 0

# Stores the last BUY or SELL signal sent
last_auto_signal = {}

# Minimum time before repeating the SAME signal
AUTO_SIGNAL_COOLDOWN = 15 * 60


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

        result = response.json()

        return result

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
# SEND TELEGRAM MESSAGE
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

    if reply_markup:

        data["reply_markup"] = reply_markup

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

        f"{auto_status}\n"

        f"⏱️ CURRENT TIMEFRAME: "
        f"{CURRENT_TIMEFRAME}\n\n"

        "📊 Select a Forex pair below.\n\n"

        "🤖 Automatic scanning checks all "
        "supported Forex markets.\n\n"

        "⚠️ NO OTC MARKETS."
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
        signal.get("timeframe", "N/A")
    )


    # -----------------------------------------------------
    # NO TRADE
    # -----------------------------------------------------

    if signal_type == "NO TRADE":

        return (

            "🤖 SHEFIU AI FOREX V2\n\n"

            f"📊 Pair: {pair}\n\n"

            "⚪ SIGNAL: NO TRADE\n\n"

            f"⏱️ Timeframe: "
            f"{used_timeframe}\n\n"

            f"📝 Reason: "
            f"{signal.get('reason', 'WAIT')}\n\n"

            "⚠️ Signal only. No guaranteed profit."
        )


    # -----------------------------------------------------
    # BUY
    # -----------------------------------------------------

    if signal_type == "BUY":

        signal_icon = "🟢"

    # -----------------------------------------------------
    # SELL
    # -----------------------------------------------------

    else:

        signal_icon = "🔴"


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
        f"{trend}\n"

        f"🔥 Confidence: "
        f"{signal.get('confidence', 'N/A')}%\n\n"

        f"📝 Reason: "
        f"{signal.get('reason', 'N/A')}\n\n"

        "⚠️ Signal only. No guaranteed profit."
    )


# =========================================================
# ANALYZE ONE PAIR
# =========================================================

def analyze_pair(
    chat_id,
    pair
):

    timeframe = CURRENT_TIMEFRAME


    send_message(

        chat_id,

        (

            f"🔎 Analyzing {pair}...\n\n"

            f"⏱️ Timeframe: "
            f"{timeframe}\n\n"

            "Please wait."
        )
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

                f"Error: {e}"
            )
        )


# =========================================================
# ANALYZE ALL PAIRS
# =========================================================

def analyze_all(chat_id):

    timeframe = CURRENT_TIMEFRAME


    send_message(

        chat_id,

        (

            "📊 SHEFIU AI FOREX V2\n\n"

            "🔎 Checking all Forex pairs...\n\n"

            f"⏱️ Timeframe: "
            f"{timeframe}\n\n"

            "Please wait."
        )
    )


    for pair in PAIRS:

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


            time.sleep(1)


        except Exception as e:

            print(
                f"{pair} error:",
                e
            )


    send_message(

        chat_id,

        "✅ Finished checking all pairs."
    )


# =========================================================
# CHECK DUPLICATE AUTOMATIC SIGNAL
# =========================================================

def should_send_auto_signal(
    pair,
    timeframe,
    signal
):

    signal_type = signal.get(
        "signal"
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


    # First signal
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


    # Signal direction changed
    if previous_signal != signal_type:

        last_auto_signal[key] = {

            "signal": signal_type,

            "time": now
        }

        return True


    # Same signal still active.
    # Do not repeat immediately.

    if (
        now - previous_time
        >= AUTO_SIGNAL_COOLDOWN
    ):

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
        "🟢 Automatic scanner started."
    )


    while True:

        try:

            if not AUTO_SCAN_ENABLED:

                time.sleep(5)

                continue


            timeframe = CURRENT_TIMEFRAME

            minutes = TIMEFRAME_MINUTES.get(
                timeframe,
                5
            )


            with auto_lock:

                now = time.time()


                if last_auto_scan_time:

                    elapsed = (
                        now
                        -
                        last_auto_scan_time
                    )


                    required_time = (
                        minutes * 60
                    )


                    if elapsed < required_time:

                        time.sleep(5)

                        continue


                last_auto_scan_time = now


            print(

                f"🔎 Automatic scan started "
                f"for {timeframe}"
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


                    if signal_type not in (
                        "BUY",
                        "SELL"
                    ):

                        continue


                    # -----------------------------------------
                    # DUPLICATE PROTECTION
                    # -----------------------------------------

                    if not should_send_auto_signal(

                        pair,

                        timeframe,

                        signal

                    ):

                        print(

                            f"Duplicate prevented: "
                            f"{pair} "
                            f"{signal_type}"
                        )

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
                        f"{signal_type} "
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

                f"✅ Automatic scan finished: "
                f"{timeframe}"
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
    # TIMEFRAME BUTTONS
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

                "Automatic scanning will use "
                "this timeframe."
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

                "The bot will automatically "
                "scan all supported Forex pairs.\n\n"

                "Duplicate signals are protected."
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

                "Manual Forex analysis is "
                "still available."
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

            "❓ I don't understand "
            "that command.\n\n"

            "Press /menu to open "
            "the Forex menu."
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

                time.sleep(3)


        except Exception as e:

            print(
                "Telegram loop error:",
                e
            )

            time.sleep(5)


# =========================================================
# START BOT
# =========================================================

print()
print("=" * 50)
print("🤖 SHEFIU AI FOREX V2")
print("=" * 50)

print(
    "🟢 Automatic scanning: ON"
)

print(
    "🟢 Manual Telegram control: ON"
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


# Send menu when bot starts

send_menu(CHAT_ID)


# Start Telegram

telegram_loop()
