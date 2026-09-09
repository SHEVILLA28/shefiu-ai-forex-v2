import time
import json
import requests

from config import BOT_TOKEN
from signals import get_signal

from bot_control import (

    set_auto_scan,

    get_auto_settings,

    add_auto_pair,

    remove_auto_pair,

    clear_auto_pairs

)


# =========================================================
# SHEFIU AI FOREX V2
# TELEGRAM CONTROL SYSTEM
# =========================================================


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
# TIMEFRAMES
# =========================================================

VALID_TIMEFRAMES = [

    "1M",
    "2M",
    "3M",
    "5M",
    "15M"

]


# =========================================================
# DEFAULT TIMEFRAME
# =========================================================

TIMEFRAME = "5M"


# =========================================================
# USER SETTINGS
# =========================================================

USER_TIMEFRAMES = {}

USER_MODES = {}


# =========================================================
# MANUAL REQUEST COOLDOWN
# =========================================================

MANUAL_REQUEST_COOLDOWN = 60

LAST_MANUAL_REQUEST = {}


# =========================================================
# SIGNAL CACHE
# =========================================================

SIGNAL_CACHE = {}

CACHE_DURATION = 60


# =========================================================
# SEND TELEGRAM MESSAGE
# =========================================================

def send_message(
    chat_id,
    text,
    reply_markup=None
):

    if not BOT_TOKEN:

        print(
            "❌ BOT_TOKEN is missing."
        )

        return False


    url = (
        f"https://api.telegram.org/bot"
        f"{BOT_TOKEN}/sendMessage"
    )


    data = {

        "chat_id": chat_id,

        "text": text

    }


    if reply_markup is not None:

        data["reply_markup"] = json.dumps(
            reply_markup
        )


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
                f"Telegram response: "
                f"{response.text}"
            )


        return response.ok


    except Exception as e:

        print(
            f"❌ Telegram error: {e}"
        )

        return False


# =========================================================
# MAIN MENU BUTTONS
# =========================================================

def get_main_menu():

    return {

        "keyboard": [

            [

                "🤖 AUTOMATIC",

                "👤 MANUAL"

            ],

            [

                "📊 PAIRS",

                "🕐 TIMEFRAME"

            ],

            [

                "▶️ START AUTO",

                "⛔ STOP AUTO"

            ],

            [

                "📋 STATUS",

                "❓ HELP"

            ]

        ],

        "resize_keyboard": True

    }


# =========================================================
# FOREX PAIRS KEYBOARD
# =========================================================

def get_pairs_keyboard():

    return {

        "keyboard": [

            [

                "EUR/USD",

                "GBP/USD"

            ],

            [

                "USD/JPY",

                "USD/CHF"

            ],

            [

                "AUD/USD",

                "USD/CAD"

            ],

            [

                "NZD/USD",

                "XAU/USD"

            ],

            [

                "EUR/GBP",

                "CHF/JPY"

            ],

            [

                "AUD/JPY",

                "EUR/JPY"

            ],

            [

                "GBP/JPY",

                "USD/SGD"

            ],

            [

                "🗑 CLEAR PAIRS",

                "🏠 MENU"

            ]

        ],

        "resize_keyboard": True

    }


# =========================================================
# TIMEFRAME KEYBOARD
# =========================================================

def get_timeframe_keyboard():

    return {

        "keyboard": [

            [

                "🕐 1M",

                "🕐 2M"

            ],

            [

                "🕐 3M",

                "🕐 5M"

            ],

            [

                "🕐 15M"

            ],

            [

                "🏠 MENU"

            ]

        ],

        "resize_keyboard": True

    }


# =========================================================
# GET USER MODE
# =========================================================

def get_user_mode(chat_id):

    return USER_MODES.get(
        chat_id,
        "MANUAL"
    )


# =========================================================
# SET USER MODE
# =========================================================

def set_user_mode(
    chat_id,
    mode
):

    USER_MODES[chat_id] = mode


# =========================================================
# GET USER TIMEFRAME
# =========================================================

def get_selected_timeframe(chat_id):

    return USER_TIMEFRAMES.get(

        chat_id,

        TIMEFRAME

    )


# =========================================================
# SET TIMEFRAME
# FIXED VERSION
# =========================================================

def set_selected_timeframe(
    chat_id,
    timeframe
):

    timeframe = (

        str(timeframe)

        .replace("🕐", "")

        .strip()

        .upper()

    )


    if timeframe not in VALID_TIMEFRAMES:

        return False


    # =============================================
    # SAVE USER TIMEFRAME ONLY
    #
    # This does NOT automatically change the
    # running Automatic Scanner timeframe.
    # =============================================

    USER_TIMEFRAMES[chat_id] = timeframe


    return True


# =========================================================
# FORMAT SIGNAL
# =========================================================

def format_signal(result):

    signal = result.get(
        "signal",
        "NO TRADE"
    )


    pair = result.get(
        "pair",
        "Unknown"
    )


    timeframe = result.get(
        "timeframe",
        TIMEFRAME
    )


    trend = result.get(
        "trend",
        "WAIT"
    )


    confidence = result.get(
        "confidence",
        0
    )


    rsi = result.get(
        "rsi",
        "N/A"
    )


    candlestick = result.get(
        "candlestick",
        "N/A"
    )


    news_status = result.get(
        "news_status",
        "UNKNOWN"
    )


    entry = result.get(
        "entry",
        "N/A"
    )


    take_profit = result.get(
        "take_profit",
        "N/A"
    )


    stop_loss = result.get(
        "stop_loss",
        "N/A"
    )


    # =====================================================
    # NEWS STATUS
    # =====================================================

    if news_status in [

        "SAFE",
        "CLEAR",
        "NO_HIGH_IMPACT_NEWS"

    ]:

        news_text = "SAFE ✅"


    elif news_status in [

        "BLOCKED",
        "HIGH_IMPACT_NEWS"

    ]:

        news_text = "BLOCKED 🔴"


    else:

        news_text = str(news_status)


    # =====================================================
    # BUY / SELL
    # =====================================================

    if signal in ["BUY", "SELL"]:


        signal_icon = (

            "🟢"

            if signal == "BUY"

            else "🔴"

        )


        return (

            "🤖 SHEFIU AI FOREX VIP\n\n"

            f"{signal_icon} 📊 {pair} — "
            f"{signal}\n\n"

            f"⏱ Timeframe: {timeframe}\n\n"

            f"🎯 Entry: {entry}\n"

            f"✅ TP: {take_profit}\n"

            f"🛑 SL: {stop_loss}\n\n"

            f"📈 Trend: {trend}\n"

            f"📊 RSI: {rsi}\n"

            f"🔥 Confidence: "
            f"{confidence}%\n\n"

            f"📰 News: {news_text}\n"

            f"🕯 Pattern: {candlestick}"

        )


    # =====================================================
    # NO TRADE
    # =====================================================

    reason = result.get(

        "reason",

        "Waiting for a stronger setup."

    )


    return (

        "🤖 SHEFIU AI FOREX VIP\n\n"

        f"📊 {pair}\n"

        "⚪ Signal: NO TRADE\n\n"

        f"⏱ Timeframe: {timeframe}\n\n"

        f"📈 Trend: {trend}\n"

        f"📊 RSI: {rsi}\n"

        f"🕯 Pattern: {candlestick}\n"

        f"📰 News: {news_text}\n\n"

        f"📝 {reason}"

    )


# =========================================================
# MANUAL COOLDOWN
# =========================================================

def can_make_manual_request(chat_id):

    now = time.time()


    last_request = LAST_MANUAL_REQUEST.get(

        chat_id,

        0

    )


    elapsed = now - last_request


    if elapsed < MANUAL_REQUEST_COOLDOWN:


        remaining = int(

            MANUAL_REQUEST_COOLDOWN
            - elapsed

        ) + 1


        return False, remaining


    LAST_MANUAL_REQUEST[chat_id] = now


    return True, 0


# =========================================================
# SIGNAL CACHE
# =========================================================

def get_cached_signal(
    pair,
    timeframe
):

    key = (
        f"{pair}_{timeframe}"
    )


    cached = SIGNAL_CACHE.get(key)


    if not cached:

        return None


    if (

        time.time()
        - cached["time"]

        < CACHE_DURATION

    ):

        return cached["result"]


    SIGNAL_CACHE.pop(
        key,
        None
    )


    return None


def save_signal_to_cache(
    pair,
    timeframe,
    result
):

    key = (
        f"{pair}_{timeframe}"
    )


    SIGNAL_CACHE[key] = {

        "result": result,

        "time": time.time()

    }


# =========================================================
# WELCOME MESSAGE
# =========================================================

def send_welcome_message(chat_id):

    timeframe = get_selected_timeframe(
        chat_id
    )


    send_message(

        chat_id,

        "🤖 SHEFIU AI FOREX VIP\n\n"

        "Welcome to your Forex AI Bot! 🚀\n\n"

        f"⏱ Current Timeframe: "
        f"{timeframe}\n\n"

        "Choose how you want the bot to work:\n\n"

        "👤 MANUAL\n"
        "Analyze any pair yourself.\n\n"

        "🤖 AUTOMATIC\n"
        "Select multiple pairs and the bot "
        "will scan them automatically.\n\n"

        "👇 Use the buttons below.",

        get_main_menu()

    )


# =========================================================
# STATUS
# =========================================================

def send_status(chat_id):

    mode = get_user_mode(chat_id)


    timeframe = get_selected_timeframe(
        chat_id
    )


    settings = get_auto_settings()


    auto_status = (

        "🟢 RUNNING"

        if settings["enabled"]

        else "🔴 STOPPED"

    )


    pairs = settings["pairs"]


    if pairs:

        pairs_text = "\n".join(pairs)


    else:

        pairs_text = "No pairs selected"


    message = (

        "🤖 SHEFIU AI FOREX VIP\n\n"

        f"👤 Current Mode: {mode}\n\n"

        f"⏱ Your Selected Timeframe: "
        f"{timeframe}\n\n"

        f"🤖 Automatic Scanner: "
        f"{auto_status}\n\n"

        f"⏱ Auto Scanner Timeframe: "
        f"{settings['timeframe']}\n\n"

        "📊 Automatic Pairs:\n\n"

        f"{pairs_text}"

    )


    send_message(

        chat_id,

        message,

        get_main_menu()

    )


# =========================================================
# HELP
# =========================================================

def send_help_message(chat_id):

    message = (

        "🤖 SHEFIU AI FOREX HELP\n\n"

        "👤 MANUAL MODE\n"
        "1️⃣ Press MANUAL\n"
        "2️⃣ Choose TIMEFRAME\n"
        "3️⃣ Press a Forex pair\n\n"

        "🤖 AUTOMATIC MODE\n"
        "1️⃣ Press AUTOMATIC\n"
        "2️⃣ Choose PAIRS\n"
        "3️⃣ Select Forex pairs\n"
        "4️⃣ Choose TIMEFRAME\n"
        "5️⃣ Press START AUTO\n\n"

        "⛔ STOP AUTO\n"
        "Stops the Automatic Scanner.\n\n"

        "📋 STATUS\n"
        "Shows your current settings.\n\n"

        "⚠️ Changing your selected timeframe "
        "does not change a scanner that is "
        "already running."

    )


    send_message(

        chat_id,

        message,

        get_main_menu()

    )


# =========================================================
# PROCESS PAIR
# =========================================================

def process_pair_request(
    chat_id,
    pair
):

    mode = get_user_mode(chat_id)


    # =====================================================
    # AUTOMATIC MODE
    # =====================================================

    if mode == "AUTOMATIC":


        settings = get_auto_settings()


        current_pairs = settings["pairs"]


        if pair in current_pairs:


            remove_auto_pair(pair)


            selected_pairs = get_auto_settings()[
                "pairs"
            ]


            pairs_text = (

                "\n".join(selected_pairs)

                if selected_pairs

                else "No pairs selected"

            )


            send_message(

                chat_id,

                f"➖ {pair} removed from "
                "Automatic Scanner.\n\n"

                f"📊 Selected pairs:\n\n"
                f"{pairs_text}",

                get_pairs_keyboard()

            )


        else:


            add_auto_pair(pair)


            send_message(

                chat_id,

                f"✅ {pair} added to "
                "Automatic Scanner.\n\n"

                "You can select more pairs.\n\n"

                "When finished:\n"
                "🕐 Choose TIMEFRAME\n"
                "▶️ Press START AUTO",

                get_pairs_keyboard()

            )


        return


    # =====================================================
    # MANUAL MODE
    # =====================================================

    timeframe = get_selected_timeframe(
        chat_id
    )


    cached = get_cached_signal(

        pair,

        timeframe

    )


    if cached:


        send_message(

            chat_id,

            f"📋 Recent analysis for "
            f"{pair}\n\n"

            f"⏱ {timeframe}",

            get_main_menu()

        )


        send_message(

            chat_id,

            format_signal(cached)

        )


        return


    allowed, remaining = (
        can_make_manual_request(
            chat_id
        )
    )


    if not allowed:


        send_message(

            chat_id,

            f"⏳ Please wait "
            f"{remaining} seconds.",

            get_main_menu()

        )


        return


    send_message(

        chat_id,

        f"🔍 Analyzing {pair}\n\n"

        f"⏱ Timeframe: {timeframe}\n\n"

        "Please wait..."

    )


    try:


        result = get_signal(

            pair,

            timeframe

        )


        save_signal_to_cache(

            pair,

            timeframe,

            result

        )


        send_message(

            chat_id,

            format_signal(result),

            get_main_menu()

        )


    except Exception as e:


        print(
            f"Manual analysis error: {e}"
        )


        send_message(

            chat_id,

            "❌ Error analyzing this pair.",

            get_main_menu()

        )


# =========================================================
# RUN TELEGRAM BOT
# =========================================================

def run_telegram_bot():

    print(
        "✅ Telegram Control Bot Started."
    )


    offset = None


    while True:


        try:


            if not BOT_TOKEN:


                print(
                    "❌ BOT_TOKEN is missing."
                )


                time.sleep(10)


                continue


            # =================================================
            # GET TELEGRAM UPDATES
            # =================================================

            url = (

                f"https://api.telegram.org/bot"
                f"{BOT_TOKEN}/getUpdates"

            )


            params = {

                "timeout": 30,

                "allowed_updates": json.dumps(
                    ["message"]
                )

            }


            if offset is not None:

                params["offset"] = offset


            response = requests.get(

                url,

                params=params,

                timeout=40

            )


            response.raise_for_status()


            data = response.json()


            # =================================================
            # PROCESS UPDATES
            # =================================================

            for update in data.get(
                "result",
                []
            ):


                update_id = update.get(
                    "update_id"
                )


                if update_id is not None:

                    offset = update_id + 1


                message = update.get(
                    "message"
                )


                if not message:

                    continue


                chat_id = (

                    message

                    .get("chat", {})

                    .get("id")

                )


                if chat_id is None:

                    continue


                raw_text = message.get(
                    "text",
                    ""
                )


                if not raw_text:

                    continue


                text = raw_text.strip()


                upper_text = text.upper()


                command = upper_text.split("@")[0]


                print(

                    f"📩 Telegram: "
                    f"{upper_text}"

                )


                # =============================================
                # START / MENU
                # =============================================

                if command in [

                    "/START",

                    "🏠 MENU"

                ]:


                    send_welcome_message(
                        chat_id
                    )


                    continue


                # =============================================
                # HELP
                # =============================================

                if command in [

                    "/HELP",

                    "❓ HELP"

                ]:


                    send_help_message(
                        chat_id
                    )


                    continue


                # =============================================
                # AUTOMATIC MODE
                # =============================================

                if upper_text == "🤖 AUTOMATIC":


                    set_user_mode(

                        chat_id,

                        "AUTOMATIC"

                    )


                    send_message(

                        chat_id,

                        "🤖 AUTOMATIC MODE SELECTED\n\n"

                        "1️⃣ Press 📊 PAIRS\n"
                        "2️⃣ Select Forex pairs\n"
                        "3️⃣ Choose 🕐 TIMEFRAME\n"
                        "4️⃣ Press ▶️ START AUTO",

                        get_main_menu()

                    )


                    continue


                # =============================================
                # MANUAL MODE
                # =============================================

                if upper_text == "👤 MANUAL":


                    set_user_mode(

                        chat_id,

                        "MANUAL"

                    )


                    send_message(

                        chat_id,

                        "👤 MANUAL MODE SELECTED\n\n"

                        "Choose a timeframe and "
                        "press any Forex pair.\n\n"

                        "The Automatic Scanner "
                        "settings will not be changed.",

                        get_main_menu()

                    )


                    continue


                # =============================================
                # PAIRS
                # =============================================

                if upper_text == "📊 PAIRS":


                    mode = get_user_mode(
                        chat_id
                    )


                    send_message(

                        chat_id,

                        f"📊 SELECT FOREX PAIRS\n\n"

                        f"Current Mode: {mode}\n\n"

                        "Press a pair below.",

                        get_pairs_keyboard()

                    )


                    continue


                # =============================================
                # CLEAR PAIRS
                # =============================================

                if upper_text == "🗑 CLEAR PAIRS":


                    clear_auto_pairs()


                    send_message(

                        chat_id,

                        "🗑 All Automatic pairs "
                        "have been cleared.",

                        get_pairs_keyboard()

                    )


                    continue


                # =============================================
                # TIMEFRAME
                # =============================================

                if upper_text == "🕐 TIMEFRAME":


                    send_message(

                        chat_id,

                        "🕐 CHOOSE TIMEFRAME\n\n"

                        "Press your preferred "
                        "timeframe:",

                        get_timeframe_keyboard()

                    )


                    continue


                # =============================================
                # TIMEFRAME BUTTON
                # =============================================

                if upper_text in [

                    "🕐 1M",

                    "🕐 2M",

                    "🕐 3M",

                    "🕐 5M",

                    "🕐 15M"

                ]:


                    timeframe = (

                        upper_text

                        .replace("🕐", "")

                        .strip()

                    )


                    set_selected_timeframe(

                        chat_id,

                        timeframe

                    )


                    mode = get_user_mode(
                        chat_id
                    )


                    send_message(

                        chat_id,

                        f"✅ Timeframe selected: "
                        f"{timeframe}\n\n"

                        f"Current Mode: {mode}\n\n"

                        "Your selection has been "
                        "saved.\n\n"

                        "For Automatic mode, press "
                        "▶️ START AUTO to apply it.",

                        get_main_menu()

                    )


                    continue


                # =============================================
                # START AUTOMATIC
                # =============================================

                if upper_text == "▶️ START AUTO":


                    settings = get_auto_settings()


                    pairs = settings["pairs"]


                    if not pairs:


                        send_message(

                            chat_id,

                            "⚠️ Please select at least "
                            "one Forex pair first.\n\n"

                            "Press 📊 PAIRS",

                            get_main_menu()

                        )


                        continue


                    timeframe = get_selected_timeframe(
                        chat_id
                    )


                    set_auto_scan(

                        enabled=True,

                        timeframe=timeframe,

                        pairs=pairs

                    )


                    pairs_text = "\n".join(
                        pairs
                    )


                    send_message(

                        chat_id,

                        "🚀 AUTOMATIC SCANNER STARTED\n\n"

                        f"⏱ Timeframe: "
                        f"{timeframe}\n\n"

                        "📊 Scanning:\n\n"

                        f"{pairs_text}\n\n"

                        "🤖 The bot will continue "
                        "scanning automatically until "
                        "you press STOP AUTO.",

                        get_main_menu()

                    )


                    continue


                # =============================================
                # STOP AUTOMATIC
                # =============================================

                if upper_text == "⛔ STOP AUTO":


                    settings = get_auto_settings()


                    set_auto_scan(

                        enabled=False,

                        timeframe=settings["timeframe"],

                        pairs=settings["pairs"]

                    )


                    send_message(

                        chat_id,

                        "⛔ AUTOMATIC SCANNER STOPPED\n\n"

                        "👤 Manual mode can still "
                        "be used.",

                        get_main_menu()

                    )


                    continue


                # =============================================
                # STATUS
                # =============================================

                if command == "/STATUS" or (
                    upper_text == "📋 STATUS"
                ):


                    send_status(chat_id)


                    continue


                # =============================================
                # FOREX PAIR
                # =============================================

                if upper_text in FOREX_PAIRS:


                    process_pair_request(

                        chat_id,

                        upper_text

                    )


                    continue


                # =============================================
                # UNKNOWN COMMAND
                # =============================================

                send_message(

                    chat_id,

                    "⚠️ Please use the buttons "
                    "below.",

                    get_main_menu()

                )


        except requests.RequestException as e:


            print(
                f"❌ Telegram connection error: "
                f"{e}"
            )


            time.sleep(5)


        except Exception as e:


            print(
                f"❌ Telegram bot error: {e}"
            )


            time.sleep(5)
