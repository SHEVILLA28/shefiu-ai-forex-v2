import time
import requests

from config import BOT_TOKEN, CHAT_ID
from signals import get_signal


# ==========================================
# FOREX PAIRS
# ==========================================

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


# ==========================================
# SEND TELEGRAM MESSAGE
# ==========================================

def send_message(chat_id, text):

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

        return response.ok

    except Exception as e:

        print(f"Telegram error: {e}")

        return False


# ==========================================
# FORMAT SIGNAL
# ==========================================

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

    reason = result.get(
        "reason",
        "No reason available."
    )


    if signal == "BUY":

        icon = "🟢"

    elif signal == "SELL":

        icon = "🔴"

    else:

        icon = "⚪"


    message = (

        "🤖 SHEFIU AI FOREX V2\n\n"

        f"📊 Pair: {pair}\n\n"

        f"{icon} SIGNAL: {signal}\n\n"

        f"⏱ Timeframe: {timeframe}\n\n"

    )


    if signal in ["BUY", "SELL"]:

        message += (

            f"🎯 Entry: "
            f"{result.get('entry', 'N/A')}\n"

            f"✅ Take Profit: "
            f"{result.get('take_profit', 'N/A')}\n"

            f"🛑 Stop Loss: "
            f"{result.get('stop_loss', 'N/A')}\n\n"

        )


    message += (

        f"📈 Trend: {trend}\n\n"

        f"📊 RSI: "
        f"{result.get('rsi', 'N/A')}\n"

        f"🔥 Confidence: "
        f"{result.get('confidence', 0)}%\n\n"

        f"📝 Reason: {reason}\n\n"

        "⚠️ Signal only. No guaranteed profit."

    )

    return message


# ==========================================
# TELEGRAM MANUAL BOT
# ==========================================

def run_telegram_bot():

    print(
        "Manual Telegram bot started."
    )

    offset = None


    while True:

        try:

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
                    "Telegram getUpdates error"
                )

                time.sleep(5)

                continue


            for update in data.get("result", []):

                offset = update["update_id"] + 1


                message = update.get("message")


                if not message:

                    continue


                chat_id = message["chat"]["id"]


                text = message.get(
                    "text",
                    ""
                ).strip()


                # ==========================
                # MANUAL FOREX PAIR REQUEST
                # ==========================

                if text in FOREX_PAIRS:

                    send_message(

                        chat_id,

                        f"🔍 Analyzing {text}..."

                    )


                    try:

                        result = get_signal(

                            text,

                            TIMEFRAME

                        )


                        signal_message = format_signal(
                            result
                        )


                        send_message(

                            chat_id,

                            signal_message

                        )


                    except Exception as e:

                        print(
                            f"Manual analysis error: {e}"
                        )


                        send_message(

                            chat_id,

                            "❌ Error analyzing this pair. "
                            "Please try again."

                        )


                # ==========================
                # START COMMAND
                # ==========================

                elif text == "/start":

                    pairs_text = "\n".join(
                        FOREX_PAIRS
                    )


                    welcome = (

                        "🤖 SHEFIU AI FOREX V2\n\n"

                        "Send me any Forex pair below "
                        "for manual analysis:\n\n"

                        f"{pairs_text}\n\n"

                        f"⏱ Timeframe: {TIMEFRAME}"

                    )


                    send_message(

                        chat_id,

                        welcome

                    )


        except Exception as e:

            print(
                f"Telegram bot error: {e}"
            )

            time.sleep(5)
