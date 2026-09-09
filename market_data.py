import os
import asyncio
from datetime import datetime, timezone
from urllib.parse import quote

import requests
import pandas as pd
from metaapi_cloud_sdk import MetaApi


# =========================================================
# SHEFIU AI FOREX V2
# MT5 / METAAPI MARKET DATA ENGINE
#
# IMPORTANT:
# - Market data comes ONLY from MetaAPI / MT5.
# - No Twelve Data.
# - No alternative market-data provider.
# - Uses MetaAPI historical market-data REST API for candles.
# =========================================================


METAAPI_TOKEN = os.getenv("METAAPI_TOKEN")
METAAPI_ACCOUNT_ID = os.getenv("METAAPI_ACCOUNT_ID")


# =========================================================
# SETTINGS
# =========================================================

MIN_CANDLES = 100
DEFAULT_HISTORY = 300
SYMBOL_CACHE_TTL = 900

# Historical market-data requests can sometimes take longer
# while the MT5 terminal downloads broker history.
REQUEST_TIMEOUT = 180


# =========================================================
# MT5 TIMEFRAMES
#
# MetaAPI historical market-data API supports these MT5
# timeframes directly.
# =========================================================

TIMEFRAME_MAP = {
    "1M": "1m",
    "2M": "2m",
    "3M": "3m",
    "5M": "5m",
    "15M": "15m",
    "30M": "30m",
    "1H": "1h",
}


# =========================================================
# SYMBOL CACHE
# =========================================================

_SYMBOL_CACHE = {
    "loaded_at": 0.0,
    "symbols": [],
}


# =========================================================
# NORMALIZE PAIR
# =========================================================

def normalize_pair(pair):
    return (
        str(pair or "")
        .upper()
        .replace("/", "")
        .replace(" ", "")
    )


# =========================================================
# CHECK CONFIGURATION
# =========================================================

def _check_config():
    if not METAAPI_TOKEN:
        raise RuntimeError(
            "METAAPI_TOKEN is missing in Render."
        )

    if not METAAPI_ACCOUNT_ID:
        raise RuntimeError(
            "METAAPI_ACCOUNT_ID is missing in Render."
        )


# =========================================================
# GET METAAPI ACCOUNT
# =========================================================

async def _get_account():
    _check_config()

    api = MetaApi(METAAPI_TOKEN)

    try:
        account = await api.metatrader_account_api.get_account(
            METAAPI_ACCOUNT_ID
        )

        return api, account

    except Exception:
        try:
            await api.close()
        except Exception:
            pass

        raise


# =========================================================
# GET RPC CONNECTION
#
# Used only for:
# - symbol discovery
# - current price
#
# Historical candles are NOT requested through RPC.
# =========================================================

async def _get_rpc_connection():
    api, account = await _get_account()

    try:
        connection = account.get_rpc_connection()

        await connection.connect()

        await connection.wait_synchronized()

        return api, account, connection

    except Exception:
        try:
            await api.close()
        except Exception:
            pass

        raise


# =========================================================
# SYMBOL DISCOVERY
# =========================================================

async def _get_symbols_async():

    now = asyncio.get_running_loop().time()

    # Use cached symbols when available.
    if (
        _SYMBOL_CACHE["symbols"]
        and now - _SYMBOL_CACHE["loaded_at"] < SYMBOL_CACHE_TTL
    ):
        return _SYMBOL_CACHE["symbols"]

    api, account, connection = await _get_rpc_connection()

    try:

        symbols = await connection.get_symbols()

        symbols = [
            str(symbol)
            for symbol in symbols
        ]

        if not symbols:
            raise RuntimeError(
                "MetaAPI returned an empty symbol list."
            )

        _SYMBOL_CACHE["symbols"] = symbols

        _SYMBOL_CACHE["loaded_at"] = now

        print(
            f"MetaAPI symbols loaded: "
            f"{len(symbols)}"
        )

        return symbols

    finally:

        try:
            await connection.close()
        except Exception:
            pass

        try:
            await api.close()
        except Exception:
            pass


# =========================================================
# RESOLVE BROKER SYMBOL
# =========================================================

async def _resolve_symbol_async(pair):

    base = normalize_pair(pair)

    if not base:
        raise RuntimeError(
            "Empty Forex pair supplied."
        )

    symbols = await _get_symbols_async()

    # -----------------------------------------------------
    # 1. Exact match
    # -----------------------------------------------------

    for symbol in symbols:

        if symbol.upper() == base:
            return symbol

    # -----------------------------------------------------
    # 2. Broker suffix / prefix variations
    #
    # Examples:
    # EURUSD
    # EURUSDm
    # EURUSD.a
    # EURUSDpro
    # -----------------------------------------------------

    candidates = []

    for symbol in symbols:

        normalized = normalize_pair(symbol)

        if normalized.startswith(base):
            candidates.append(symbol)

    if candidates:

        candidates.sort(
            key=lambda value: (
                len(value),
                value
            )
        )

        return candidates[0]

    # -----------------------------------------------------
    # 3. Gold / XAUUSD variations
    # -----------------------------------------------------

    if base == "XAUUSD":

        gold_candidates = []

        for symbol in symbols:

            upper = symbol.upper()

            if (
                "XAUUSD" in upper
                or upper.startswith("GOLD")
            ):
                gold_candidates.append(symbol)

        if gold_candidates:

            gold_candidates.sort(
                key=lambda value: (
                    len(value),
                    value
                )
            )

            return gold_candidates[0]

    # -----------------------------------------------------
    # 4. Nothing found
    # -----------------------------------------------------

    raise RuntimeError(
        f"MetaAPI could not find broker symbol "
        f"for {pair}. "
        f"Use the MetaAPI symbol list to verify "
        f"the broker symbol."
    )


# =========================================================
# PUBLIC SYMBOL RESOLVER
# =========================================================

def resolve_symbol(pair):

    return asyncio.run(
        _resolve_symbol_async(pair)
    )


# =========================================================
# GET METAAPI MARKET-DATA HOST
#
# Historical market data uses a separate hostname.
# The account's MetaAPI region determines the hostname.
#
# Example:
# mt-market-data-client-api-v1.new-york.agiliumtrade.ai
# =========================================================

async def _get_market_data_host():

    api, account = await _get_account()

    try:

        region = getattr(
            account,
            "region",
            None
        )

        if not region:

            raise RuntimeError(
                "MetaAPI account region could not be determined."
            )

        region = str(region).strip()

        if not region:

            raise RuntimeError(
                "MetaAPI account region is empty."
            )

        host = (
            "mt-market-data-client-api-v1."
            f"{region}."
            "agiliumtrade.ai"
        )

        return host

    finally:

        try:
            await api.close()
        except Exception:
            pass


# =========================================================
# FETCH HISTORICAL CANDLES
#
# IMPORTANT:
# We use MetaAPI's historical market-data REST API here.
#
# This is the correct route for MT5 historical candles.
# =========================================================

async def _fetch_candles_async(
    pair,
    timeframe,
    limit
):

    symbol = await _resolve_symbol_async(pair)

    host = await _get_market_data_host()

    encoded_symbol = quote(
        symbol,
        safe=""
    )

    encoded_timeframe = quote(
        timeframe,
        safe=""
    )

    url = (
        f"https://{host}"
        f"/users/current/accounts/"
        f"{METAAPI_ACCOUNT_ID}"
        f"/historical-market-data/"
        f"symbols/{encoded_symbol}"
        f"/timeframes/{encoded_timeframe}"
        f"/candles"
    )

    params = {
        "startTime": datetime.now(
            timezone.utc
        ).isoformat(
            timespec="milliseconds"
        ).replace(
            "+00:00",
            "Z"
        ),
        "limit": min(
            int(limit),
            1000
        ),
    }

    headers = {
        "auth-token": METAAPI_TOKEN,
        "Accept": "application/json",
    }

    print(
        "MetaAPI historical market data:"
    )

    print(
        f"Pair: {pair}"
    )

    print(
        f"Broker symbol: {symbol}"
    )

    print(
        f"Timeframe: {timeframe}"
    )

    print(
        f"History limit: {params['limit']}"
    )

    print(
        f"MetaAPI region: {host}"
    )

    # -----------------------------------------------------
    # requests is blocking, so run it in a worker thread.
    # -----------------------------------------------------

    def request_data():

        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=REQUEST_TIMEOUT,
        )

        return response

    response = await asyncio.to_thread(
        request_data
    )

    # -----------------------------------------------------
    # HTTP errors
    # -----------------------------------------------------

    if response.status_code != 200:

        body = response.text[:1000]

        raise RuntimeError(
            "MetaAPI historical candle request failed. "
            f"HTTP {response.status_code}: {body}"
        )

    # -----------------------------------------------------
    # Decode JSON
    # -----------------------------------------------------

    try:

        candles = response.json()

    except Exception as e:

        raise RuntimeError(
            "MetaAPI returned invalid JSON "
            f"for historical candles: {e}"
        )

    if not isinstance(
        candles,
        list
    ):

        raise RuntimeError(
            "MetaAPI historical candle response "
            "was not a list."
        )

    return candles, symbol


# =========================================================
# CONVERT CANDLES TO DATAFRAME
# =========================================================

def _candles_to_dataframe(candles):

    if not candles:

        return (
            None,
            "MetaAPI returned no candles."
        )

    rows = []

    for candle in candles:

        if not isinstance(
            candle,
            dict
        ):
            continue

        rows.append(
            {
                "datetime": (
                    candle.get("time")
                    or candle.get("brokerTime")
                ),

                "open": candle.get(
                    "open"
                ),

                "high": candle.get(
                    "high"
                ),

                "low": candle.get(
                    "low"
                ),

                "close": candle.get(
                    "close"
                ),

                "volume": (
                    candle.get(
                        "tickVolume"
                    )
                    if candle.get(
                        "tickVolume"
                    ) is not None
                    else candle.get(
                        "volume"
                    )
                ),
            }
        )

    df = pd.DataFrame(rows)

    if df.empty:

        return (
            None,
            "MetaAPI candle data could "
            "not be converted to a dataframe."
        )

    # -----------------------------------------------------
    # Datetime
    # -----------------------------------------------------

    df["datetime"] = pd.to_datetime(
        df["datetime"],
        errors="coerce",
        utc=True,
    )

    # -----------------------------------------------------
    # Numeric columns
    # -----------------------------------------------------

    for column in [
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    # -----------------------------------------------------
    # Remove invalid candles
    # -----------------------------------------------------

    df = df.dropna(
        subset=[
            "datetime",
            "open",
            "high",
            "low",
            "close",
        ]
    )

    # -----------------------------------------------------
    # Sort oldest -> newest
    # -----------------------------------------------------

    df = (
        df
        .sort_values("datetime")
        .drop_duplicates(
            subset=["datetime"]
        )
        .reset_index(
            drop=True
        )
    )

    return df, None


# =========================================================
# PUBLIC MARKET DATA FUNCTION
# =========================================================

def get_market_data(
    pair,
    timeframe="5M"
):

    timeframe = str(
        timeframe or "5M"
    ).upper()

    # -----------------------------------------------------
    # Check timeframe
    # -----------------------------------------------------

    source_timeframe = TIMEFRAME_MAP.get(
        timeframe
    )

    if source_timeframe is None:

        return (
            None,
            f"Unsupported MT5 timeframe: "
            f"{timeframe}"
        )

    # -----------------------------------------------------
    # History amount
    # -----------------------------------------------------

    limit = DEFAULT_HISTORY

    # 2M / 3M no longer need resampling.
    # MetaAPI MT5 historical market-data API
    # supports these timeframes directly.
    if timeframe in (
        "2M",
        "3M"
    ):

        limit = DEFAULT_HISTORY

    try:

        candles, symbol = asyncio.run(
            _fetch_candles_async(
                pair,
                source_timeframe,
                limit,
            )
        )

        # -------------------------------------------------
        # Convert to dataframe
        # -------------------------------------------------

        df, error_message = (
            _candles_to_dataframe(
                candles
            )
        )

        if df is None:

            return (
                None,
                error_message
            )

        # -------------------------------------------------
        # Verify enough candles
        # -------------------------------------------------

        print(
            f"MT5 candles received: "
            f"{pair} | "
            f"{symbol} | "
            f"{timeframe} | "
            f"{len(df)} candles"
        )

        if len(df) < MIN_CANDLES:

            return (
                None,
                (
                    f"Not enough MT5 candles "
                    f"for {pair} {timeframe}. "
                    f"Received {len(df)}, "
                    f"need {MIN_CANDLES}."
                )
            )

        return (
            df,
            None
        )

    except Exception as e:

        message = str(e)

        print(
            f"MT5 market-data error for "
            f"{pair} {timeframe}: "
            f"{message}"
        )

        return (
            None,
            message
        )


# =========================================================
# CURRENT PRICE
# =========================================================

async def _get_price_async(pair):

    api, account, connection = (
        await _get_rpc_connection()
    )

    try:

        symbol = await _resolve_symbol_async(
            pair
        )

        price = await connection.get_symbol_price(
            symbol=symbol
        )

        return (
            price,
            symbol
        )

    finally:

        try:
            await connection.close()
        except Exception:
            pass

        try:
            await api.close()
        except Exception:
            pass


def get_current_price(pair):

    return asyncio.run(
        _get_price_async(pair)
    )


# =========================================================
# MT5 SYMBOL HELPER
#
# Used by main.py for actual trade execution.
# =========================================================

resolve_mt5_symbol = resolve_symbol
