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

AUTO_PAIRS = []


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
    timeframe=None,
    pairs=None
):

    global AUTO_SCAN_ENABLED
    global AUTO_TIMEFRAME
    global AUTO_PAIRS


    with AUTO_SETTINGS_LOCK:


        # =============================================
        # ENABLE / DISABLE
        # =============================================

        if enabled is not None:

            AUTO_SCAN_ENABLED = bool(enabled)


        # =============================================
        # TIMEFRAME
        # =============================================

        if timeframe is not None:

            timeframe = (
                str(timeframe)
                .strip()
                .upper()
            )


            if timeframe in VALID_TIMEFRAMES:

                AUTO_TIMEFRAME = timeframe


        # =============================================
        # PAIRS
        # =============================================

        if pairs is not None:

            clean_pairs = []


            for pair in pairs:

                pair = str(pair).strip().upper()


                if pair and pair not in clean_pairs:

                    clean_pairs.append(pair)


            AUTO_PAIRS = clean_pairs


        print(

            "\n"
            "====================================\n"
            "🤖 AUTO SETTINGS UPDATED\n"
            f"Enabled: {AUTO_SCAN_ENABLED}\n"
            f"Timeframe: {AUTO_TIMEFRAME}\n"
            f"Pairs: {AUTO_PAIRS}\n"
            "====================================\n"

        )


# =========================================================
# GET AUTO SETTINGS
# =========================================================

def get_auto_settings():

    with AUTO_SETTINGS_LOCK:

        return {

            "enabled": AUTO_SCAN_ENABLED,

            "timeframe": AUTO_TIMEFRAME,

            "pairs": AUTO_PAIRS.copy()

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


# =========================================================
# GET AUTO PAIRS
# =========================================================

def get_auto_pairs():

    with AUTO_SETTINGS_LOCK:

        return AUTO_PAIRS.copy()


# =========================================================
# ADD AUTO PAIR
# =========================================================

def add_auto_pair(pair):

    global AUTO_PAIRS


    pair = str(pair).strip().upper()


    with AUTO_SETTINGS_LOCK:

        if pair not in AUTO_PAIRS:

            AUTO_PAIRS.append(pair)


        print(
            f"➕ Auto pair added: {pair}"
        )


# =========================================================
# REMOVE AUTO PAIR
# =========================================================

def remove_auto_pair(pair):

    global AUTO_PAIRS


    pair = str(pair).strip().upper()


    with AUTO_SETTINGS_LOCK:

        if pair in AUTO_PAIRS:

            AUTO_PAIRS.remove(pair)


        print(
            f"➖ Auto pair removed: {pair}"
        )


# =========================================================
# CLEAR AUTO PAIRS
# =========================================================

def clear_auto_pairs():

    global AUTO_PAIRS


    with AUTO_SETTINGS_LOCK:

        AUTO_PAIRS = []


        print(
            "🗑 All automatic pairs cleared."
        )
