"""
Central Forex market session control.

Uses the New York 5:00 PM session boundary, so daylight-saving time is
handled automatically instead of hard-coding a UTC hour.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

NEW_YORK = ZoneInfo("America/New_York")


def is_forex_market_open(now=None):
    """Return True when the normal weekly Forex session is open."""
    if now is None:
        now = datetime.now(NEW_YORK)
    else:
        now = now.astimezone(NEW_YORK)

    weekday = now.weekday()  # Monday=0 ... Sunday=6
    session_hour = now.hour
    session_minute = now.minute

    # Saturday: closed all day.
    if weekday == 5:
        return False

    # Sunday: opens at 5:00 PM New York time.
    if weekday == 6:
        return (session_hour, session_minute) >= (17, 0)

    # Friday: closes at 5:00 PM New York time.
    if weekday == 4:
        return (session_hour, session_minute) < (17, 0)

    # Monday through Thursday.
    return True


def market_status_message():
    return (
        "Forex market is currently closed. Automatic scanning and new "
        "trade execution are paused until the normal Forex session reopens."
    )
