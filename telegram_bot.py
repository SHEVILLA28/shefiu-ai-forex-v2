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


TIMEFRAME = "5M"


# =========================================================
# MANUAL REQUEST PROTECTION
# =========================================================

MANUAL_REQUEST_COOLDOWN = 60

LAST_MANUAL_REQUEST = {}

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
# SHORT PROFESSIONAL FORMAT
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
    # SIGNAL ICON
    # =====================================================

    if signal == "BUY":

        signal_icon = "🟢"


    elif signal == "SELL":

        signal_icon = "🔴"


    else:

        signal_icon = "⚪"


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
    # SHORT BUY / SELL MESSAGE
    # =====================================================

    if signal in ["BUY", "SELL"]:

        message = (

            "🤖 SHEFIU AI FOREX VIP\n\n"

            f"📊 {pair} — {signal}\n"

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
    # SHORT NO TRADE MESSAGE
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

def get_cached_signal(pair):

    cached = SIGNAL_CACHE.get(pair)


    if not cached:

        return None


    result = cached["result"]

    saved_time = cached["time"]


    if time.time() - saved_time < CACHE_DURATION:

        return result


    return None


# =========================================================
# SAVE SIGNAL TO CACHE
# =========================================================

def save_signal_to_cache(pair, result):

    SIGNAL_CACHE[pair] = {

        "result": result,

        "time": time.time()

    }


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


            if not BOT_TOKEN:

                print(
                    "BOT_TOKEN is missing."
                )

                time.sleep(10)

                continue


            url = (
                f"https://api.telegram.org/bot"
                f"{BOT_TOKEN}/getUpdates"
            )


            params = {
                "timeout": 30
            }


            if offset is not None:

                params["offset"] = offset


            response = requests.get(
                url,
                params=params,
                timeout=40
            )


            data = response.json()


            if not data.get("ok"):


                print(
                    "Telegram getUpdates error:",
                    data
                )


                time.sleep(5)

                continue


            for update in data.get(
                "result",
                []
            ):


                offset = (
                    update["update_id"] + 1
                )


                telegram_message = update.get(
                    "message"
                )


                if not telegram_message:

                    continue


                chat_id = telegram_message[
                    "chat"
                ]["id"]


                text = telegram_message.get(
                    "text",
                    ""
                ).strip().upper()


                # =============================================
                # MANUAL FOREX PAIR REQUEST
                # =============================================

                if text in FOREX_PAIRS:


                    cached_result = get_cached_signal(
                        text
                    )


                    if cached_result:


                        send_message(

                            chat_id,

                            f"📋 Recent analysis for {text}"

                        )


                        send_message(

                            chat_id,

                            format_signal(
                                cached_result
                            )

                        )


                        continue


                    allowed, remaining = (
                        can_make_manual_request(
                            chat_id
                        )
                    )


                    if not allowed:


                        send_message(

                            chat_id,

                            f"⏳ Please wait "
                            f"{remaining} seconds."

                        )


                        continue


                    send_message(

                        chat_id,

                        f"🔍 Analyzing {text}..."

                    )


                    try:


                        result = get_signal(
                            text,
                            TIMEFRAME
                        )


                        save_signal_to_cache(
                            text,
                            result
                        )


                        send_message(

                            chat_id,

                            format_signal(result)

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


                # =============================================
                # START COMMAND
                # =============================================

                elif text == "/START":


                    pairs_text = "\n".join(
                        FOREX_PAIRS
                    )


                    welcome = (

                        "🤖 SHEFIU AI FOREX VIP\n\n"

                        "📊 Send any Forex pair below:\n\n"

                        f"{pairs_text}\n\n"

                        f"⏱ Timeframe: {TIMEFRAME}\n\n"

                        "Example:\n"
                        "EUR/USD"

                    )


                    send_message(
                        chat_id,
                        welcome
                    )


                # =============================================
                # HELP COMMAND
                # =============================================

                elif text == "/HELP":


                    send_message(

                        chat_id,

                        "🤖 SHEFIU AI FOREX VIP\n\n"

                        "Send a Forex pair to analyze.\n\n"

                        "Example:\n"
                        "EUR/USD\n"
                        "GBP/USD\n"
                        "XAU/USD\n\n"

                        "The bot checks:\n"

                        "📈 Trend\n"
                        "📊 RSI\n"
                        "🕯 Candlestick\n"
                        "📰 Economic News\n"
                        "🎯 Entry / TP / SL"

                    )


        except Exception as e:


            print(
                f"Telegram bot error: {e}"
            )


            time.sleep(5)
