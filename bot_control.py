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
# VALID FOREX PAIRS
# =========================================================

VALID_PAIRS = [

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
        # ENABLE / DISABLE AUTOMATIC SCANNER
        # =============================================

        if enabled is not None:

            AUTO_SCAN_ENABLED = bool(
                enabled
            )


        # =============================================
        # SET TIMEFRAME
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
        # SET SELECTED PAIRS
        # =============================================

        if pairs is not None:

            valid_pairs = []


            for pair in pairs:

                pair = (
                    str(pair)
                    .strip()
                    .upper()
                )


                if pair in VALID_PAIRS:

                    valid_pairs.append(
                        pair
                    )


            AUTO_PAIRS = valid_pairs


        print(
            "===================================="
        )

        print(
            "🤖 AUTO SETTINGS UPDATED"
        )

        print(
            f"Enabled: "
            f"{AUTO_SCAN_ENABLED}"
        )

        print(
            f"Timeframe: "
            f"{AUTO_TIMEFRAME}"
        )

        print(
            f"Pairs: "
            f"{AUTO_PAIRS}"
        )

        print(
            "===================================="
        )


# =========================================================
# SET AUTOMATIC PAIRS
# =========================================================

def set_auto_pairs(pairs):

    set_auto_scan(
        pairs=pairs
    )


# =========================================================
# ADD ONE PAIR
# =========================================================

def add_auto_pair(pair):

    global AUTO_PAIRS


    pair = (
        str(pair)
        .strip()
        .upper()
    )


    if pair not in VALID_PAIRS:

        return False


    with AUTO_SETTINGS_LOCK:


        if pair not in AUTO_PAIRS:

            AUTO_PAIRS.append(
                pair
            )


        print(
            f"➕ Pair added: {pair}"
        )


        print(
            f"Selected pairs: "
            f"{AUTO_PAIRS}"
        )


    return True


# =========================================================
# REMOVE ONE PAIR
# =========================================================

def remove_auto_pair(pair):

    global AUTO_PAIRS


    pair = (
        str(pair)
        .strip()
        .upper()
    )


    with AUTO_SETTINGS_LOCK:


        if pair in AUTO_PAIRS:

            AUTO_PAIRS.remove(
                pair
            )


            print(
                f"➖ Pair removed: {pair}"
            )


            return True


    return False


# =========================================================
# CLEAR ALL PAIRS
# =========================================================

def clear_auto_pairs():

    global AUTO_PAIRS


    with AUTO_SETTINGS_LOCK:

        AUTO_PAIRS = []


        print(
            "🗑 All automatic pairs cleared."
        )


# =========================================================
# GET AUTO SETTINGS
# =========================================================

def get_auto_settings():

    with AUTO_SETTINGS_LOCK:

        return {

            "enabled":
                AUTO_SCAN_ENABLED,

            "timeframe":
                AUTO_TIMEFRAME,

            "pairs":
                AUTO_PAIRS.copy()

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
# GET SELECTED AUTO PAIRS
# =========================================================

def get_auto_pairs():

    with AUTO_SETTINGS_LOCK:

        return AUTO_PAIRS.copy()


# =========================================================
# CHECK IF PAIR IS SELECTED
# =========================================================

def is_pair_selected(pair):

    pair = (
        str(pair)
        .strip()
        .upper()
    )


    with AUTO_SETTINGS_LOCK:

        return pair in AUTO_PAIRS
