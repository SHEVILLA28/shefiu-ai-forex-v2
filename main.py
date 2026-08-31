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
        f"🟢 Health server running on port {port}"
    )

    server.serve_forever()


threading.Thread(
    target=start_server,
    daemon=True
).start()


# =========================================================
# MARKETS - 14 PAIRS
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

TIMEFRAMES = {

    "1M": "1min",

    "2M": "2min",

    "3M": "3min",

    "5M": "5min",

}


TIMEFRAME_MINUTES = {

    "1M": 1,

    "2M": 2,

    "3M": 3,

    "5M": 5,

}


# =========================================================
# AUTOMATIC SCANNING SETTINGS
# =========================================================

AUTO_SCAN_ENABLED = True

CURRENT_TIMEFRAME = "5M"

auto_lock = threading.Lock()

last_auto_scan_time = 0

# Stores the last signal direction sent for each pair.
# This stops repeated BUY/SELL alerts.
last_auto_signal = {}

# Time when the last automatic alert was sent.
last_auto_alert_time = {}

# Extra protection against repeated signals.
AUTO_SIGNAL_COOLDOWN_SECONDS = 15 * 60


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

        if not result.get("ok"):

            print(
                "Telegram API error:",
                result
            )

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
# TELEGRAM MENU
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
            {"text": "CHF/JPY"}
        ],

        [
            {"text": "AUD/JPY"},
            {"text": "EUR/JPY"}
        ],

        [
            {"text": "GBP/JPY"},
            {"text": "USD/SGD"}
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

        "📊 MARKETS: 14 PAIRS\n\n"

        "Select a pair below for manual analysis.\n\n"

        "Automatic scanning checks all pairs "
        "and sends BUY/SELL signals only."
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
# SIGNAL MESSAGE
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

            f"{signal.get('reason', 'Conditions are not strong enough.')}"
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
        "UNKNOWN"
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


    telegram_request(

        "sendMessage",

        {

            "chat_id": chat_id,

            "text": (

                f"🔎 Analyzing {pair}...\n\n"

                f"⏱️ Timeframe: {timeframe}\n\n"

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

            f"✅ Analyzed {pair} "
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

                "🔎 Checking all 14 markets...\n\n"

                f"⏱️ Timeframe: {timeframe}\n\n"

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

                "✅ Finished checking all 14 pairs."

            )

        }

    )


# =========================================================
# AUTOMATIC SCANNER
# =========================================================

def automatic_scan_loop():

    global last_auto_scan_time


    print(
        "🟢 Automatic scanner thread started."
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


            with auto_lock:

                now = time.time()


                if (

                    last_auto_scan_time > 0

                    and

                    now - last_auto_scan_time
                    < minutes * 60

                ):

                    continue


                last_auto_scan_time = now


            print(

                f"🔎 Automatic scan started: "
                f"{timeframe}"

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


                    key = (

                        pair,

                        timeframe

                    )


                    # =========================================
                    # RESET WHEN THERE IS NO TRADE
                    # =========================================

                    if signal_type == "NO TRADE":

                        if key in last_auto_signal:

                            del last_auto_signal[key]

                        continue


                    # =========================================
                    # ONLY BUY OR SELL
                    # =========================================

                    if signal_type not in {

                        "BUY",

                        "SELL"

                    }:

                        continue


                    previous_signal = (

                        last_auto_signal.get(
                            key
                        )

                    )


                    current_time = time.time()


                    previous_alert_time = (

                        last_auto_alert_time.get(
                            key,
                            0
                        )

                    )


                    # =========================================
                    # STOP REPEATED SAME SIGNAL
                    #
                    # Example:
                    # XAU/USD BUY was already sent.
                    # Don't send XAU/USD BUY again immediately.
                    # =========================================

                    if previous_signal == signal_type:

                        if (

                            current_time
                            - previous_alert_time
                            < AUTO_SIGNAL_COOLDOWN_SECONDS

                        ):

                            print(

                                f"⏳ Duplicate signal skipped: "

                                f"{pair} "

                                f"{signal_type}"

                            )

                            continue


                    # =========================================
                    # SAVE SIGNAL
                    # =========================================

                    last_auto_signal[
                        key
                    ] = signal_type


                    last_auto_alert_time[
                        key
                    ] = current_time


                    # =========================================
                    # SEND AUTOMATIC SIGNAL
                    # =========================================

                    telegram_request(

                        "sendMessage",

                        {

                            "chat_id": CHAT_ID,

                            "text": (

                                "🔔 AUTOMATIC FOREX SIGNAL\n\n"

                                + format_signal(

                                    signal,

                                    timeframe

                                )

                            )

                        }

                    )


                    print(

                        f"🚨 Auto signal sent: "

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


            # Small sleep prevents CPU overload
            time.sleep(2)


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
# HANDLE TELEGRAM MESSAGE
# =========================================================

def handle_update(
    update
):

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

        f"📱 Telegram command received: "
        f"{text}"

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


        # Restart automatic timing
        last_auto_scan_time = 0


        # Clear old signal memory for new timeframe
        last_auto_signal.clear()

        last_auto_alert_time.clear()


        telegram_request(

            "sendMessage",

            {

                "chat_id": chat_id,

                "text": (

                    f"⏱️ Timeframe changed to "
                    f"{CURRENT_TIMEFRAME}.\n\n"

                    "🟢 Automatic scanner will now "
                    "use this timeframe."

                )

            }

        )


        send_menu(chat_id)

        return


    # =====================================================
    # AUTOMATIC SCANNER ON
    # =====================================================

    if text == "🟢 AUTO SCAN ON":

        AUTO_SCAN_ENABLED = True

        last_auto_scan_time = 0


        telegram_request(

            "sendMessage",

            {

                "chat_id": chat_id,

                "text": (

                    "🟢 AUTOMATIC SCANNING: ON\n\n"

                    f"⏱️ Timeframe: "
                    f"{CURRENT_TIMEFRAME}\n\n"

                    "The bot will scan all 14 pairs.\n"

                    "It sends BUY/SELL signals and "
                    "helps prevent repeated duplicate alerts."

                )

            }

        )


        send_menu(chat_id)

        return


    # =====================================================
    # AUTOMATIC SCANNER OFF
    # =====================================================

    if text == "🔴 AUTO SCAN OFF":

        AUTO_SCAN_ENABLED = False


        telegram_request(

            "sendMessage",

            {

                "chat_id": chat_id,

                "text": (

                    "🔴 AUTOMATIC SCANNING: OFF\n\n"

                    "🟢 Manual Telegram analysis "
                    "remains ON."

                )

            }

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

    telegram_request(

        "sendMessage",

        {

            "chat_id": chat_id,

            "text": (

                "❓ I don't understand that command.\n\n"

                "Press /menu to open the Forex menu."

            )

        }

    )


# =========================================================
# TELEGRAM LOOP
# =========================================================

def telegram_loop():

    print(
        "🟢 Telegram manual-control system started."
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


                    handle_update(update)


            else:

                time.sleep(5)


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
print("🟢 Automatic scanning: ON")
print("🟢 Manual Telegram control: ON")
print(f"📊 Markets: {len(PAIRS)} pairs")
print(f"⏱️ Timeframe: {CURRENT_TIMEFRAME}")
print("📱 Waiting for Telegram commands...")
print("=" * 50)
print()


# Send menu when the bot starts
send_menu(CHAT_ID)


# Start Telegram commands
telegram_loop()
