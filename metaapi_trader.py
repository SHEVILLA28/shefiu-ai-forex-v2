import os
import asyncio

from metaapi_cloud_sdk import MetaApi


# =========================================================
# METAAPI SETTINGS
# =========================================================

METAAPI_TOKEN = os.getenv("METAAPI_TOKEN")
METAAPI_ACCOUNT_ID = os.getenv("METAAPI_ACCOUNT_ID")


# =========================================================
# CONNECTION SETTINGS
# =========================================================

MAX_CONNECTION_ATTEMPTS = 5
RETRY_DELAY = 10


# =========================================================
# GET METAAPI CONNECTION
# =========================================================

async def get_connection():

    if not METAAPI_TOKEN:
        raise Exception("METAAPI_TOKEN is missing")

    if not METAAPI_ACCOUNT_ID:
        raise Exception("METAAPI_ACCOUNT_ID is missing")

    print("Connecting to MetaAPI...")

    api = MetaApi(METAAPI_TOKEN)

    account = await api.metatrader_account_api.get_account(
        METAAPI_ACCOUNT_ID
    )

    connection = account.get_rpc_connection()

    for attempt in range(
        1,
        MAX_CONNECTION_ATTEMPTS + 1
    ):

        try:

            print(
                f"MetaAPI connection attempt "
                f"{attempt}/{MAX_CONNECTION_ATTEMPTS}"
            )

            await connection.connect()

            print(
                "Waiting for MetaTrader synchronization..."
            )

            await connection.wait_synchronized()

            print(
                "MetaAPI connected and synchronized successfully!"
            )

            return connection

        except Exception as e:

            print(
                f"Connection attempt {attempt} failed: {e}"
            )

            if attempt < MAX_CONNECTION_ATTEMPTS:

                await asyncio.sleep(RETRY_DELAY)

            else:

                raise


# =========================================================
# PLACE BUY ORDER
# =========================================================

async def place_buy_order(symbol, volume):

    connection = await get_connection()

    print(
        f"Placing BUY: {symbol} | {volume}"
    )

    result = await connection.create_market_buy_order(
        symbol,
        volume
    )

    print(
        f"BUY order result: {result}"
    )

    return result


# =========================================================
# PLACE SELL ORDER
# =========================================================

async def place_sell_order(symbol, volume):

    connection = await get_connection()

    print(
        f"Placing SELL: {symbol} | {volume}"
    )

    result = await connection.create_market_sell_order(
        symbol,
        volume
    )

    print(
        f"SELL order result: {result}"
    )

    return result


# =========================================================
# GET OPEN POSITIONS
# =========================================================

async def get_open_positions():

    connection = await get_connection()

    positions = await connection.get_positions()

    return positions


# =========================================================
# CLOSE POSITION
# =========================================================

async def close_position(position_id):

    connection = await get_connection()

    print(
        f"Closing position: {position_id}"
    )

    result = await connection.close_position(
        position_id
    )

    print(
        f"Close result: {result}"
    )

    return result
