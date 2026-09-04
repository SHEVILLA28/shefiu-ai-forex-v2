import requests
from datetime import datetime, timedelta, timezone


# =========================================================
# XOOMAR ECONOMIC NEWS FILTER
# =========================================================

NEWS_URL = "https://xoomar.com/api/markets/calendar"


# =========================================================
# GET CURRENCIES FROM FOREX PAIR
# =========================================================

def get_pair_currencies(pair):

    pair = pair.upper().replace("/", "").replace(" ", "")

    if len(pair) != 6:
        return None, None

    return pair[:3], pair[3:]


# =========================================================
# GET ECONOMIC NEWS
# =========================================================

def get_economic_news():

    try:

        response = requests.get(
            NEWS_URL,
            timeout=15
        )

        response.raise_for_status()

        response_data = response.json()


        # Xoomar API returns data inside "data"

        if isinstance(response_data, dict):

            return response_data.get(
                "data",
                []
            )


        return response_data


    except Exception as e:

        print(
            f"News filter error: {e}"
        )

        return []


# =========================================================
# CHECK FOR HIGH IMPACT NEWS
# =========================================================

def has_high_impact_news(pair):

    base_currency, quote_currency = (
        get_pair_currencies(pair)
    )


    if not base_currency:

        return False


    news_events = get_economic_news()


    now = datetime.now(timezone.utc)

    news_window_before = (
        now - timedelta(minutes=30)
    )

    news_window_after = (
        now + timedelta(minutes=30)
    )


    for event in news_events:

        try:

            importance = str(
                event.get(
                    "importance",
                    ""
                )
            ).lower()


            currency = str(
                event.get(
                    "currency",
                    event.get(
                        "country",
                        ""
                    )
                )
            ).upper()


            # Only high-impact events

            if importance not in [
                "high",
                "3",
                "high impact"
            ]:

                continue


            # Check if news affects this Forex pair

            if (
                currency != base_currency
                and currency != quote_currency
            ):

                continue


            event_time_string = event.get(
                "date"
            ) or event.get(
                "datetime"
            ) or event.get(
                "time"
            )


            if not event_time_string:

                continue


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


            except Exception:

                continue


            if (
                news_window_before
                <= event_time
                <= news_window_after
            ):

                print(
                    f"HIGH IMPACT NEWS WARNING: "
                    f"{pair} affected by {currency}"
                )

                return True


        except Exception as e:

            print(
                f"News event processing error: {e}"
            )

            continue


    return False
