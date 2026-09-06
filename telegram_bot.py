import time
import requests

from config import BOT_TOKEN
from signals import get_signal


# =========================================================
# SHEFIU AI FOREX V2
# PROFESSIONAL VIP TELEGRAM BOT
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
# DEFAULT TIMEFRAME
# =========================================================

TIMEFRAME = "5M"


# =========================================================
# SELECTED TIMEFRAME FOR EACH TELEGRAM USER
# =========================================================

USER_TIMEFRAMES = {}


# =========================================================
# MANUAL REQUEST PROTECTION
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

def send_message(chat_id, text):

    if not BOT_TOKEN:

        print("BOT_TOKEN is missing.")

        return False


    url = (
        f"https://api.telegram.org/bot"
        f"{BOT_TOKEN}/sendMessage"
    )


    data = {

        "chat_id": chat_id,

        "text": text

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
                f"Telegram response: "
                f"{response.text}"
            )


        return response.ok


    except Exception as e:

        print(
            f"Telegram error: {e}"
        )

        return False


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
    # BUY / SELL MESSAGE
    # =====================================================

    if signal in ["BUY", "SELL"]:


        signal_icon = "🟢" if signal == "BUY" else "🔴"


        message = (

            "🤖 SHEFIU AI FOREX VIP\n\n"

            f"{signal_icon} 📊 {pair} — {signal}\n"

            f"⏱ Timeframe: {timeframe}\n\n"

            f"🎯 Entry: {entry}\n"

            f"✅ TP: {take_profit}\n"

            f"🛑 SL: {stop_loss}\n\n"

            f"📈 Trend: {trend}\n"

            f"📊 RSI: {rsi}\n"

            f"🔥 Confidence: {confidence}%\n\n"

            f"📰 News: {news_text}\n"

            f"🕯 Pattern: {candlestick}"

        )


    # =====================================================
    # NO TRADE MESSAGE
    # =====================================================

    else:


        reason = result.get(

            "reason",

            "Waiting for a stronger setup."

        )


        message = (

            "🤖 SHEFIU AI FOREX VIP\n\n"

            f"📊 {pair}\n"

            f"⚪ Signal: NO TRADE\n"

            f"⏱ Timeframe: {timeframe}\n\n"

            f"📈 Trend: {trend}\n"

            f"📊 RSI: {rsi}\n"

            f"🕯 Pattern: {candlestick}\n"

            f"📰 News: {news_text}\n\n"

            f"📝 {reason}"

        )


    return message


# =========================================================
# CHECK MANUAL COOLDOWN
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

            MANUAL_REQUEST_COOLDOWN - elapsed

        ) + 1


        return False, remaining


    LAST_MANUAL_REQUEST[chat_id] = now


    return True, 0


# =========================================================
# GET CACHED SIGNAL
# =========================================================

def get_cached_signal(pair, timeframe):


    cache_key = f"{pair}_{timeframe}"


    cached = SIGNAL_CACHE.get(cache_key)


    if not cached:

        return None


    result = cached.get("result")

    saved_time = cached.get("time", 0)


    if time.time() - saved_time < CACHE_DURATION:

        return result


    # Remove expired cache

    SIGNAL_CACHE.pop(
        cache_key,
        None
    )


    return None


# =========================================================
# SAVE SIGNAL TO CACHE
# =========================================================

def save_signal_to_cache(
    pair,
    timeframe,
    result
):


    cache_key = f"{pair}_{timeframe}"


    SIGNAL_CACHE[cache_key] = {

        "result": result,

        "time": time.time()

    }


# =========================================================
# GET SELECTED TIMEFRAME
# =========================================================

def get_selected_timeframe(chat_id):


    return USER_TIMEFRAMES.get(

        chat_id,

        TIMEFRAME

    )


# =========================================================
# PROCESS TIMEFRAME SELECTION
# =========================================================

def process_timeframe_selection(
    chat_id,
    text
):


    timeframe_options = {


        "1": "1M",

        "1M": "1M",

        "1 MIN": "1M",

        "1 MINUTE": "1M",

        "🕐 1 MIN": "1M",


        "2": "2M",

        "2M": "2M",

        "2 MIN": "2M",

        "2 MINUTE": "2M",

        "🕐 2 MIN": "2M",


        "3": "3M",

        "3M": "3M",

        "3 MIN": "3M",

        "3 MINUTE": "3M",

        "🕐 3 MIN": "3M",


        "5": "5M",

        "5M": "5M",

        "5 MIN": "5M",

        "5 MINUTE": "5M",

        "🕐 5 MIN": "5M"

    }


    selected = timeframe_options.get(text)


    if not selected:

        return False


    USER_TIMEFRAMES[chat_id] = selected


    send_message(

        chat_id,

        f"✅ Timeframe changed successfully to {selected}\n\n"
        "Now send a Forex pair.\n\n"
        "Example:\n"
        "EUR/USD"

    )


    return True


# =========================================================
# SEND WELCOME MESSAGE
# =========================================================

def send_welcome_message(chat_id):


    pairs_text = "\n".join(
        FOREX_PAIRS
    )


    selected_timeframe = (
        get_selected_timeframe(
            chat_id
        )
    )


    welcome = (

        "🤖 SHEFIU AI FOREX VIP\n\n"

        "📊 AVAILABLE FOREX MARKETS:\n\n"

        f"{pairs_text}\n\n"

        f"⏱ Current Timeframe: "
        f"{selected_timeframe}\n\n"

        "━━━━━━━━━━━━━━━━━━\n"

        "🕐 CHOOSE TIMEFRAME:\n\n"

        "1 MIN\n"
        "2 MIN\n"
        "3 MIN\n"
        "5 MIN\n\n"

        "━━━━━━━━━━━━━━━━━━\n"

        "Then send a Forex pair.\n\n"

        "Example:\n"
        "EUR/USD"

    )


    send_message(
        chat_id,
        welcome
    )


# =========================================================
# TELEGRAM MANUAL BOT
# =========================================================

def run_telegram_bot():


    print(
        "Manual Telegram bot started."
    )


    offset = None


    while True:


        try:


            # =============================================
            # CHECK BOT TOKEN
            # =============================================

            if not BOT_TOKEN:


                print(
                    "BOT_TOKEN is missing."
                )


                time.sleep(10)


                continue


            # =============================================
            # TELEGRAM GET UPDATES
            # =============================================

            url = (

                f"https://api.telegram.org/bot"
                f"{BOT_TOKEN}/getUpdates"

            )


            params = {

                "timeout": 30,

                "allowed_updates": [
                    "message"
                ]

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


            if not data.get("ok"):


                print(

                    "Telegram getUpdates error:",

                    data

                )


                time.sleep(5)


                continue


            # =============================================
            # PROCESS UPDATES
            # =============================================

            for update in data.get(
                "result",
                []
            ):


                update_id = update.get(
                    "update_id"
                )


                if update_id is not None:


                    offset = update_id + 1


                telegram_message = update.get(
                    "message"
                )


                if not telegram_message:


                    continue


                chat = telegram_message.get(
                    "chat"
                )


                if not chat:


                    continue


                chat_id = chat.get(
                    "id"
                )


                if chat_id is None:


                    continue


                raw_text = telegram_message.get(
                    "text",
                    ""
                )


                if not raw_text:


                    continue


                text = raw_text.strip().upper()


                print(
                    f"Telegram message received: "
                    f"{text}"
                )


                # =========================================
                # START COMMAND
                # =========================================

                if text == "/START":


                    send_welcome_message(
                        chat_id
                    )


                    continue


                # =========================================
                # HELP COMMAND
                # =========================================

                if text == "/HELP":


                    selected_timeframe = (
                        get_selected_timeframe(
                            chat_id
                        )
                    )


                    help_message = (

                        "🤖 SHEFIU AI FOREX VIP\n\n"

                        f"⏱ Current Timeframe: "
                        f"{selected_timeframe}\n\n"

                        "Choose timeframe by sending:\n\n"

                        "🕐 1 MIN\n"
                        "🕐 2 MIN\n"
                        "🕐 3 MIN\n"
                        "🕐 5 MIN\n\n"

                        "Then send a Forex pair:\n\n"

                        "EUR/USD\n"
                        "GBP/USD\n"
                        "XAU/USD\n"
                        "GBP/JPY\n\n"

                        "Commands:\n"
                        "/START\n"
                        "/HELP\n"
                        "/TIMEFRAME\n"
                        "/STATUS"

                    )


                    send_message(
                        chat_id,
                        help_message
                    )


                    continue


                # =========================================
                # TIMEFRAME COMMAND
                # =========================================

                if text == "/TIMEFRAME":


                    selected_timeframe = (
                        get_selected_timeframe(
                            chat_id
                        )
                    )


                    send_message(

                        chat_id,

                        "🤖 SHEFIU AI FOREX VIP\n\n"

                        f"⏱ Current Timeframe: "
                        f"{selected_timeframe}\n\n"

                        "Choose a new timeframe:\n\n"

                        "🕐 1 MIN\n"
                        "🕐 2 MIN\n"
                        "🕐 3 MIN\n"
                        "🕐 5 MIN"

                    )


                    continue


                # =========================================
                # STATUS COMMAND
                # =========================================

                if text == "/STATUS":


                    selected_timeframe = (
                        get_selected_timeframe(
                            chat_id
                        )
                    )


                    send_message(

                        chat_id,

                        "🤖 SHEFIU AI FOREX VIP\n\n"

                        "🟢 Bot Status: ONLINE\n"

                        f"⏱ Selected Timeframe: "
                        f"{selected_timeframe}\n\n"

                        "📊 Forex Scanner: ACTIVE"

                    )


                    continue


                # =========================================
                # TIMEFRAME SELECTION
                # =========================================

                timeframe_changed = (
                    process_timeframe_selection(
                        chat_id,
                        text
                    )
                )


                if timeframe_changed:


                    continue


                # =========================================
                # FOREX PAIR REQUEST
                # =========================================

                if text in FOREX_PAIRS:


                    selected_timeframe = (

                        get_selected_timeframe(
                            chat_id
                        )

                    )


                    # =====================================
                    # CHECK CACHE
                    # =====================================

                    cached_result = (

                        get_cached_signal(
                            text,
                            selected_timeframe
                        )

                    )


                    if cached_result:


                        send_message(

                            chat_id,

                            f"📋 Recent {selected_timeframe} "
                            f"analysis for {text}"

                        )


                        send_message(

                            chat_id,

                            format_signal(
                                cached_result
                            )

                        )


                        continue


                    # =====================================
                    # COOLDOWN CHECK
                    # =====================================

                    allowed, remaining = (

                        can_make_manual_request(
                            chat_id
                        )

                    )


                    if not allowed:


                        send_message(

                            chat_id,

                            f"⏳ Please wait "
                            f"{remaining} seconds before "
                            f"requesting another new analysis."

                        )


                        continue


                    # =====================================
                    # ANALYZING MESSAGE
                    # =====================================

                    send_message(

                        chat_id,

                        f"🔍 Analyzing {text}\n\n"
                        f"⏱ Timeframe: "
                        f"{selected_timeframe}\n\n"
                        "Please wait..."

                    )


                    try:


                        # =================================
                        # GET SIGNAL
                        # =================================

                        result = get_signal(

                            text,

                            selected_timeframe

                        )


                        # =================================
                        # SAVE CACHE
                        # =================================

                        save_signal_to_cache(

                            text,

                            selected_timeframe,

                            result

                        )


                        # =================================
                        # SEND RESULT
                        # =================================

                        send_message(

                            chat_id,

                            format_signal(
                                result
                            )

                        )


                    except Exception as e:


                        print(

                            f"Manual analysis error: {e}"

                        )


                        send_message(

                            chat_id,

                            "❌ Error analyzing this pair.\n\n"
                            "Please try again later."

                        )


                    continue


                # =========================================
                # UNKNOWN MESSAGE
                # =========================================

                send_message(

                    chat_id,

                    "⚠️ Please send a valid command, "
                    "timeframe, or Forex pair.\n\n"

                    "Example:\n"
                    "EUR/USD\n\n"

                    "Send /HELP for instructions."

                )


        except requests.RequestException as e:


            print(
                f"Telegram connection error: {e}"
            )


            time.sleep(5)


        except Exception as e:


            print(
                f"Telegram bot error: {e}"
            )


            time.sleep(5)
