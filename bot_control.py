import threading


# =========================================================
# SHEFIU AI FOREX V2
# SHARED BOT CONTROL
# =========================================================


# =========================================================
# AUTOMATIC SCANNER SETTINGS
# =========================================================

AUTO_SCAN_ENABLED = False

AUTO_TIMEFRAME = "5M"


# =========================================================
# THREAD SAFETY LOCK
# =========================================================

AUTO_SETTINGS_LOCK = threading.Lock()


# =========================================================
# VALID TIMEFRAMES
# =========================================================

VALID_TIMEFRAMES = [

    "1M",
    "2M",
    "3M",
    "5M"

]


# =========================================================
# SET AUTO SCAN
# =========================================================

def set_auto_scan(
    enabled=None,
    timeframe=None
):

    global AUTO_SCAN_ENABLED
    global AUTO_TIMEFRAME


    with AUTO_SETTINGS_LOCK:

        if enabled is not None:

            AUTO_SCAN_ENABLED = bool(
                enabled
            )


        if timeframe is not None:

            timeframe = (
                str(timeframe)
                .strip()
                .upper()
            )


            if timeframe in VALID_TIMEFRAMES:

                AUTO_TIMEFRAME = timeframe


        print(

            f"🤖 AUTO SETTINGS | "
            f"Enabled: {AUTO_SCAN_ENABLED} | "
            f"Timeframe: {AUTO_TIMEFRAME}"

        )


# =========================================================
# GET AUTO SETTINGS
# =========================================================

def get_auto_settings():

    with AUTO_SETTINGS_LOCK:

        return {

            "enabled": AUTO_SCAN_ENABLED,

            "timeframe": AUTO_TIMEFRAME

        }


# =========================================================
# GET AUTO STATUS
# =========================================================

def is_auto_scan_enabled():

    with AUTO_SETTINGS_LOCK:

        return AUTO_SCAN_ENABLED


# =========================================================
# GET AUTO TIMEFRAME
# =========================================================

def get_auto_timeframe():

    with AUTO_SETTINGS_LOCK:

        return AUTO_TIMEFRAME
