import os
import asyncio
from datetime import datetime, timezone

import pandas as pd
from metaapi_cloud_sdk import MetaApi


# =========================================================
# SHEFIU AI FOREX V2
# MT5 / METAAPI MARKET DATA ENGINE
# =========================================================

METAAPI_TOKEN = os.getenv("METAAPI_TOKEN")
METAAPI_ACCOUNT_ID = os.getenv("METAAPI_ACCOUNT_ID")

MIN_CANDLES = 100
DEFAULT_HISTORY = 300
SYMBOL_CACHE_TTL = 900

TIMEFRAME_MAP = {
    "1M": "1m",
    "5M": "5m",
    "15M": "15m",
    "30M": "30m",
    "1H": "1h",
}

RESAMPLED_TIMEFRAMES = {
    "2M": "2min",
    "3M": "3min",
}

_SYMBOL_CACHE = {
    "loaded_at": 0.0,
    "symbols": [],
}


# =========================================================
# NORMALIZE PAIR
# =========================================================

def normalize_pair(pair):
    return str(pair or "").upper().replace("/", "").replace(" ", "")


# =========================================================
# METAAPI CONNECTION
# =========================================================

async def _get_account():
    if not METAAPI_TOKEN:
        raise RuntimeError("METAAPI_TOKEN is missing in Render.")

    if not METAAPI_ACCOUNT_ID:
        raise RuntimeError("METAAPI_ACCOUNT_ID is missing in Render.")

    api = MetaApi(METAAPI_TOKEN)
    account = await api.metatrader_account_api.get_account(
        METAAPI_ACCOUNT_ID
    )

    return api, account


async def _get_rpc_connection():
    api, account = await _get_account()

    connection = account.get_rpc_connection()
    await connection.connect()
    await connection.wait_synchronized()

    return api, account, connection


# =========================================================
# SYMBOL DISCOVERY
# =========================================================

async def _get_symbols_async():
    now = asyncio.get_running_loop().time()

    if (
        _SYMBOL_CACHE["symbols"]
        and now - _SYMBOL_CACHE["loaded_at"] < SYMBOL_CACHE_TTL
    ):
        return _SYMBOL_CACHE["symbols"]

    api, account, connection = await _get_rpc_connection()

    try:
        symbols = await connection.get_symbols()
        symbols = [str(symbol) for symbol in symbols]

        _SYMBOL_CACHE["symbols"] = symbols
        _SYMBOL_CACHE["loaded_at"] = now

        print(
            f"MetaAPI symbols loaded: {len(symbols)}"
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


async def _resolve_symbol_async(pair):
    base = normalize_pair(pair)
    symbols = await _get_symbols_async()

    # Exact match first.
    for symbol in symbols:
        if symbol.upper() == base:
            return symbol

    # Common broker suffix/prefix variations.
    candidates = []
    for symbol in symbols:
        normalized = normalize_pair(symbol)
        if normalized.startswith(base):
            candidates.append(symbol)

    if candidates:
        # Prefer the shortest matching broker symbol, e.g. EURUSDm
        # over a longer synthetic symbol.
        candidates.sort(key=lambda value: (len(value), value))
        return candidates[0]

    # Gold/XAUUSD broker naming can vary considerably.
    if base == "XAUUSD":
        gold_candidates = []
        for symbol in symbols:
            upper = symbol.upper()
            if "XAUUSD" in upper or upper.startswith("GOLD"):
                gold_candidates.append(symbol)

        if gold_candidates:
            gold_candidates.sort(key=lambda value: (len(value), value))
            return gold_candidates[0]

    raise RuntimeError(
        f"MetaAPI could not find broker symbol for {pair}. "
        "Use the MetaAPI symbol list to verify the broker name."
    )


def resolve_symbol(pair):
    return asyncio.run(_resolve_symbol_async(pair))


# =========================================================
# FETCH HISTORICAL CANDLES
# =========================================================

async def _fetch_candles_async(pair, timeframe, limit):
    api, account, connection = await _get_rpc_connection()

    try:
        symbol = await _resolve_symbol_async(pair)

        print(
            f"MetaAPI market data: {pair} -> {symbol} | {timeframe}"
        )

        # MetaAPI historical candles are requested before the current time.
        candles = await account.get_historical_candles(
            symbol=symbol,
            timeframe=timeframe,
            start_time=datetime.now(timezone.utc),
            limit=limit,
        )

        return candles, symbol
    finally:
        try:
            await connection.close()
        except Exception:
            pass
        try:
            await api.close()
        except Exception:
            pass


def _candles_to_dataframe(candles):
    if not candles:
        return None, "MetaAPI returned no candles."

    rows = []

    for candle in candles:
        if not isinstance(candle, dict):
            continue

        rows.append(
            {
                "datetime": candle.get("time")
                or candle.get("brokerTime"),
                "open": candle.get("open"),
                "high": candle.get("high"),
                "low": candle.get("low"),
                "close": candle.get("close"),
                "volume": candle.get("tickVolume")
                or candle.get("volume"),
            }
        )

    df = pd.DataFrame(rows)

    if df.empty:
        return None, "MetaAPI candle data could not be converted to a dataframe."

    df["datetime"] = pd.to_datetime(
        df["datetime"],
        errors="coerce",
        utc=True,
    )

    for column in ["open", "high", "low", "close"]:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    df = df.dropna(
        subset=[
            "datetime",
            "open",
            "high",
            "low",
            "close",
        ]
    )

    df = (
        df.sort_values("datetime")
        .drop_duplicates(subset=["datetime"])
        .reset_index(drop=True)
    )

    return df, None


# =========================================================
# RESAMPLE 1-MINUTE DATA FOR 2M / 3M
# =========================================================

def _resample(df, timeframe):
    rule = RESAMPLED_TIMEFRAMES[timeframe]

    data = df.copy().set_index("datetime")

    result = (
        data.resample(rule)
        .agg(
            {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
            }
        )
        .dropna(subset=["open", "high", "low", "close"])
        .reset_index()
    )

    return result


# =========================================================
# PUBLIC MARKET DATA FUNCTION
# =========================================================

def get_market_data(pair, timeframe="5M"):
    timeframe = str(timeframe or "5M").upper()

    if timeframe in RESAMPLED_TIMEFRAMES:
        source_timeframe = "1m"
        limit = 350
    else:
        source_timeframe = TIMEFRAME_MAP.get(timeframe)
        limit = DEFAULT_HISTORY

    if source_timeframe is None:
        return None, f"Unsupported MT5 timeframe: {timeframe}"

    try:
        candles, symbol = asyncio.run(
            _fetch_candles_async(
                pair,
                source_timeframe,
                limit,
            )
        )

        df, error_message = _candles_to_dataframe(candles)

        if df is None:
            return None, error_message

        if timeframe in RESAMPLED_TIMEFRAMES:
            df = _resample(df, timeframe)

        print(
            f"MT5 candles received: {pair} | {symbol} | "
            f"{timeframe} | {len(df)} candles"
        )

        if len(df) < MIN_CANDLES:
            return None, (
                f"Not enough MT5 candles for {pair} {timeframe}. "
                f"Received {len(df)}, need {MIN_CANDLES}."
            )

        return df, None

    except Exception as e:
        message = str(e)

        # MetaAPI currently documents historical candle RPC support as G1-only.
        if "historical" in message.lower() or "not supported" in message.lower():
            message = (
                "MetaAPI historical candles are unavailable for this account/API "
                "configuration. The scanner will not use another market-data provider. "
                f"MetaAPI error: {message}"
            )

        print(
            f"MT5 market-data error for {pair} {timeframe}: {message}"
        )

        return None, message


# =========================================================
# CURRENT PRICE
# =========================================================

async def _get_price_async(pair):
    api, account, connection = await _get_rpc_connection()

    try:
        symbol = await _resolve_symbol_async(pair)
        price = await connection.get_symbol_price(symbol=symbol)
        return price, symbol
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
    return asyncio.run(_get_price_async(pair))


# =========================================================
# MT5 SYMBOL HELPER FOR TRADE EXECUTION
# =========================================================

resolve_mt5_symbol = resolve_symbol
