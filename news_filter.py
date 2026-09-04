import requests
from datetime import datetime, timedelta, timezone


# =========================================================
# SHEFIU AI FOREX V2 - ECONOMIC NEWS FILTER
# =========================================================

NEWS_URL = "https://xoomar.com/api/markets/calendar"


# =========================================================
# GET CURRENCIES FROM FOREX PAIR
# =========================================================

def get_pair_currencies(pair):

    pair = pair.upper().replace("/", "").replace(" ", "")

    if len(pair) != 6:
        return None, None

    base_currency = pair[:3]
    quote_currency = pair[3:]

    return base_currency, quote_currency


# =========================================================
# GET ECONOMIC NEWS
# =========================================================

def get_economic_news():

    try:

        print("Checking economic news...")

        response = requests.get(
            NEWS_URL,
            timeout=15
        )

        response.raise_for_status()

        response_data = response.json()


        # =============================================
        # API RETURNS DATA INSIDE "data"
        # =============================================

        if isinstance(response_data, dict):

            news_data = response_data.get(
                "data",
                []
            )

            if isinstance(news_data, list):

                print(
                    f"Economic news events received: "
                    f"{len(news_data)}"
                )

                return news_data


        # =============================================
        # API RETURNS LIST DIRECTLY
        # =============================================

        if isinstance(response_data, list):

            print(
                f"Economic news events received: "
                f"{len(response_data)}"
            )

            return response_data


        print(
            "Economic news API returned an "
            "unexpected format."
        )

        return []


    except Exception as e:

        print(
            f"News filter error: {e}"
        )

        return []


# =========================================================
# PARSE EVENT TIME
# =========================================================

def parse_event_time(event):

    event_time_string = (

        event.get("date")

        or event.get("datetime")

        or event.get("time")

    )


    if not event_time_string:

        return None


    try:

        event_time = datetime.fromisoformat(
            str(event_time_string).replace(
                "Z",
                "+00:00"
            )
        )


        if event_time.tzinfo is None:

            event_time = event_time.replace(
                tzinfo=timezone.utc
            )


        return event_time.astimezone(
            timezone.utc
        )


    except Exception:

        return None


# =========================================================
# CHECK NEWS STATUS
# =========================================================

def get_news_status(pair):


    # =============================================
    # GET PAIR CURRENCIES
    # =============================================

    base_currency, quote_currency = (
        get_pair_currencies(pair)
    )


    if not base_currency:

        return {
            "blocked": False,
            "status": "UNKNOWN",
            "message": (
                "Unable to identify currencies "
                "for this Forex pair."
            ),
            "currency": None,
            "event": None
        }


    # =============================================
    # GET NEWS EVENTS
    # =============================================

    news_events = get_economic_news()


    if not news_events:

        return {
            "blocked": False,
            "status": "CLEAR",
            "message": (
                "No high-impact economic news "
                "detected for this pair."
            ),
            "currency": None,
            "event": None
        }


    # =============================================
    # CURRENT UTC TIME
    # =============================================

    now = datetime.now(
        timezone.utc
    )


    # =============================================
    # NEWS PROTECTION WINDOW
    #
    # 30 MINUTES BEFORE
    # 30 MINUTES AFTER
    # =============================================

    news_window_before = (
        now - timedelta(minutes=30)
    )


    news_window_after = (
        now + timedelta(minutes=30)
    )


    # =============================================
    # CHECK EVERY NEWS EVENT
    # =============================================

    for event in news_events:

        try:

            if not isinstance(event, dict):

                continue


            # =========================================
            # GET IMPORTANCE
            # =========================================

            importance = str(
                event.get(
                    "importance",
                    event.get(
                        "impact",
                        ""
                    )
                )
            ).lower()


            # =========================================
            # ONLY HIGH IMPACT NEWS
            # =========================================

            high_impact_values = [

                "high",

                "high impact",

                "3",

                "3.0"

            ]


            if importance not in high_impact_values:

                continue


            # =========================================
            # GET CURRENCY
            # =========================================

            currency = str(
                event.get(
                    "currency",
                    ""
                )
            ).upper().strip()


            # =========================================
            # CHECK IF EVENT AFFECTS PAIR
            # =========================================

            if currency not in [

                base_currency,

                quote_currency

            ]:

                continue


            # =========================================
            # GET EVENT TIME
            # =========================================

            event_time = parse_event_time(
                event
            )


            if event_time is None:

                continue


            # =========================================
            # CHECK TIME WINDOW
            # =========================================

            if (

                news_window_before

                <= event_time

                <= news_window_after

            ):


                event_name = (

                    event.get("title")

                    or event.get("event")

                    or event.get("name")

                    or "High-impact economic news"

                )


                print(

                    f"HIGH IMPACT NEWS WARNING: "

                    f"{pair} affected by "

                    f"{currency} | "

                    f"{event_name}"

                )


                return {

                    "blocked": True,

                    "status": "BLOCKED",

                    "message": (

                        f"High-impact {currency} news "

                        f"detected: {event_name}. "

                        f"Trading temporarily paused."

                    ),

                    "currency": currency,

                    "event": event_name

                }


        except Exception as e:

            print(
                f"News event processing error: {e}"
            )

            continue


    # =============================================
    # NO DANGEROUS NEWS FOUND
    # =============================================

    return {

        "blocked": False,

        "status": "CLEAR",

        "message": (

            "No high-impact economic news "

            "detected for this Forex pair."

        ),

        "currency": None,

        "event": None

    }


# =========================================================
# COMPATIBILITY FUNCTION
# =========================================================

def has_high_impact_news(pair):

    news_status = get_news_status(pair)

    return news_status.get(
        "blocked",
        False
            )
