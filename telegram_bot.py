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
# =========================================================

def format_signal(result):


    # =====================================================
    # BASIC INFORMATION
    # =====================================================

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


    reason = result.get(
        "reason",
        "No reason available."
    )


    confidence = result.get(
        "confidence",
        0
    )


    # =====================================================
    # SIGNAL ICON
    # =====================================================

    if signal == "BUY":

        icon = "🟢"


    elif signal == "SELL":

        icon = "🔴"


    else:

        icon = "⚪"


    # =====================================================
    # START MESSAGE
    # =====================================================

    message = (

        "╔════════════════════╗\n"
        "🤖 SHEFIU AI FOREX VIP\n"
        "╚════════════════════╝\n\n"

        f"📊 PAIR: {pair}\n\n"

        f"{icon} SIGNAL: {signal}\n\n"

        f"⏱ TIMEFRAME: {timeframe}\n\n"

    )


    # =====================================================
    # ENTRY / TP / SL
    # =====================================================

    if signal in ["BUY", "SELL"]:

        message += (

            "💰 TRADE SETUP\n\n"

            f"🎯 Entry: "
            f"{result.get('entry', 'N/A')}\n"

            f"✅ Take Profit: "
            f"{result.get('take_profit', 'N/A')}\n"

            f"🛑 Stop Loss: "
            f"{result.get('stop_loss', 'N/A')}\n\n"

        )


    # =====================================================
    # SUPPORT AND RESISTANCE
    # =====================================================

    support = result.get(
        "support",
        "N/A"
    )


    resistance = result.get(
        "resistance",
        "N/A"
    )


    message += (

        "📊 MARKET LEVELS\n\n"

        f"🟢 Support: {support}\n"

        f"🔴 Resistance: {resistance}\n\n"

    )


    # =====================================================
    # CANDLESTICK ANALYSIS
    # =====================================================

    candlestick = result.get(
        "candlestick",
        "N/A"
    )


    candle_icon = "🕯"


    if candlestick in [

        "BULLISH ENGULFING",
        "HAMMER"

    ]:

        candle_status = "🟢 BULLISH CONFIRMATION"


    elif candlestick in [

        "BEARISH ENGULFING",
        "SHOOTING STAR"

    ]:

        candle_status = "🔴 BEARISH CONFIRMATION"


    elif candlestick == "NONE":

        candle_status = "⚪ NO STRONG PATTERN"


    else:

        candle_status = "ℹ️ WAITING"


    message += (

        "🕯 CANDLESTICK ANALYSIS\n\n"

        f"{candle_icon} Pattern: {candlestick}\n"

        f"{candle_status}\n\n"

    )


    # =====================================================
    # TREND / RSI / CONFIDENCE
    # =====================================================

    message += (

        "📈 MARKET ANALYSIS\n\n"

        f"📈 Trend: {trend}\n"

        f"📊 RSI: "
        f"{result.get('rsi', 'N/A')}\n"

        f"🔥 Confidence: "
        f"{confidence}%\n\n"

    )


    # =====================================================
    # ECONOMIC NEWS FILTER
    # =====================================================

    news_status = result.get(
        "news_status",
        None
    )


    news_reason = result.get(
        "news_message",
        None
    )


    if news_status in [

        "SAFE",
        "CLEAR",
        "NO_HIGH_IMPACT_NEWS"

    ]:


        message += (

            "📰 ECONOMIC NEWS FILTER\n\n"

            "🟢 Status: SAFE\n"

            "✅ No dangerous high-impact "
            "economic news detected.\n\n"

        )


    elif news_status in [

        "BLOCKED",
        "HIGH_IMPACT_NEWS"

    ]:


        message += (

            "📰 ECONOMIC NEWS FILTER\n\n"

            "🔴 Status: NEWS BLOCKED\n\n"

        )


        if news_reason:

            message += (

                f"⚠️ {news_reason}\n\n"

            )


    elif news_status:


        message += (

            "📰 ECONOMIC NEWS FILTER\n\n"

            f"ℹ️ Status: {news_status}\n\n"

        )


        if news_reason:

            message += (

                f"📝 {news_reason}\n\n"

            )


    else:


        message += (

            "📰 ECONOMIC NEWS FILTER\n\n"

            "ℹ️ Status: Checking...\n\n"

        )


    # =====================================================
    # ANALYSIS REASON
    # =====================================================

    message += (

        "📝 ANALYSIS\n\n"

        f"{reason}\n\n"

        "━━━━━━━━━━━━━━━━━━━━\n"

        "⚠️ Risk Warning\n"
        "No trading system guarantees profit.\n"

        "🤖 SHEFIU AI FOREX VIP"

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


                # =================================================
                # MANUAL FOREX PAIR REQUEST
                # =================================================

                if text in FOREX_PAIRS:


                    # =============================================
                    # CHECK CACHE FIRST
                    # =============================================

                    cached_result = get_cached_signal(
                        text
                    )


                    if cached_result:


                        send_message(

                            chat_id,

                            "📋 Showing recent analysis for "
                            f"{text}..."

                        )


                        send_message(

                            chat_id,

                            format_signal(
                                cached_result
                            )

                        )


                        continue


                    # =============================================
                    # CHECK COOLDOWN
                    # =============================================

                    allowed, remaining = (
                        can_make_manual_request(
                            chat_id
                        )
                    )


                    if not allowed:


                        send_message(

                            chat_id,

                            "⏳ Please wait "
                            f"{remaining} seconds before "
                            "requesting another analysis.\n\n"
                            "🤖 Automatic scanning is "
                            "still running."

                        )


                        continue


                    # =============================================
                    # ANALYZE PAIR
                    # =============================================

                    send_message(

                        chat_id,

                        f"🔍 Analyzing {text}...\n\n"
                        "🕯 Checking candlestick pattern...\n"
                        "📊 Checking market levels...\n"
                        "📈 Checking trend and momentum..."

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
                            "Please wait about one minute "
                            "and try again."

                        )


                # =================================================
                # START COMMAND
                # =================================================

                elif text == "/START":


                    pairs_text = "\n".join(
                        FOREX_PAIRS
                    )


                    welcome = (

                        "╔════════════════════╗\n"
                        "🤖 SHEFIU AI FOREX VIP\n"
                        "╚════════════════════╝\n\n"

                        "📊 PROFESSIONAL FOREX ANALYSIS\n\n"

                        "Send any pair below:\n\n"

                        f"{pairs_text}\n\n"

                        f"⏱ Timeframe: {TIMEFRAME}\n\n"

                        "🕯 Candlestick Analysis: ACTIVE\n"

                        "📊 Support & Resistance: ACTIVE\n"

                        "📈 EMA Trend Analysis: ACTIVE\n"

                        "📊 RSI Confirmation: ACTIVE\n"

                        "🛡 Economic News Filter: ACTIVE\n\n"

                        "━━━━━━━━━━━━━━━━━━━━\n\n"

                        "Example:\n"
                        "EUR/USD"

                    )


                    send_message(
                        chat_id,
                        welcome
                    )


                # =================================================
                # HELP COMMAND
                # =================================================

                elif text == "/HELP":


                    send_message(

                        chat_id,

                        "🤖 SHEFIU AI FOREX VIP HELP\n\n"

                        "Simply send a Forex pair.\n\n"

                        "Example:\n"
                        "EUR/USD\n"
                        "GBP/USD\n"
                        "XAU/USD\n\n"

                        "The bot will analyze:\n\n"

                        "🕯 Candlestick patterns\n"
                        "📈 Market trend\n"
                        "📊 RSI\n"
                        "🟢 Support\n"
                        "🔴 Resistance\n"
                        "📰 Economic news\n"
                        "🎯 Entry / TP / SL"

                    )


        except Exception as e:


            print(
                f"Telegram bot error: {e}"
            )


            time.sleep(5)
