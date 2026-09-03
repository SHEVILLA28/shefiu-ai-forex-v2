import os
import asyncio

from metaapi_cloud_sdk import MetaApi


# =========================================================
# METAAPI SETTINGS
# =========================================================

METAAPI_TOKEN = os.getenv("METAAPI_TOKEN")

METAAPI_ACCOUNT_ID = os.getenv(
    "METAAPI_ACCOUNT_ID"
)


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

        raise Exception(
            "METAAPI_TOKEN is missing"
        )


    if not METAAPI_ACCOUNT_ID:

        raise Exception(
            "METAAPI_ACCOUNT_ID is missing"
        )


    print(
        "Connecting to MetaAPI..."
    )


    api = MetaApi(
        METAAPI_TOKEN
    )


    account = await api.metatrader_account_api.get_account(
        METAAPI_ACCOUNT_ID
    )


    connection = account.get_rpc_connection()


    # =============================================
    # TRY CONNECTING SEVERAL TIMES
    # =============================================

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
                "Waiting for MetaTrader account "
                "synchronization..."
            )


            await connection.wait_synchronized()


            print(
                "MetaAPI connected and synchronized successfully!"
            )


            return connection


        except Exception as e:

            print(
                f"MetaAPI connection attempt "
                f"{attempt} failed: {e}"
            )


            if attempt < MAX_CONNECTION_ATTEMPTS:

                print(
                    f"Waiting {RETRY_DELAY} seconds "
                    "before trying again..."
                )


                await asyncio.sleep(
                    RETRY_DELAY
                )


            else:

                raise Exception(
                    "MetaAPI could not synchronize "
                    f"after {MAX_CONNECTION_ATTEMPTS} attempts. "
                    f"Last error: {e}"
                )


# =========================================================
# PLACE BUY ORDER
# =========================================================

async def place_buy_order(symbol, volume):

    print(
        f"Preparing BUY order: "
        f"{symbol} | Volume: {volume}"
    )


    connection = await get_connection()


    result = await connection.create_market_buy_order(
        symbol,
        volume
    )


    print(
        f"BUY order completed: {result}"
    )


    return result


# =========================================================
# PLACE SELL ORDER
# =========================================================

async def place_sell_order(symbol, volume):

    print(
        f"Preparing SELL order: "
        f"{symbol} | Volume: {volume}"
    )


    connection = await get_connection()


    result = await connection.create_market_sell_order(
        symbol,
        volume
    )


    print(
        f"SELL order completed: {result}"
    )


    return result
