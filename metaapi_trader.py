import os
import asyncio

from metaapi_cloud_sdk import MetaApi


# =========================================================
# METAAPI CONFIGURATION
# =========================================================

METAAPI_TOKEN = os.getenv("METAAPI_TOKEN")

METAAPI_ACCOUNT_ID = os.getenv("METAAPI_ACCOUNT_ID")


# =========================================================
# CONNECT TO METAAPI
# =========================================================

async def get_connection():

    if not METAAPI_TOKEN:

        raise Exception(
            "METAAPI_TOKEN is missing."
        )

    if not METAAPI_ACCOUNT_ID:

        raise Exception(
            "METAAPI_ACCOUNT_ID is missing."
        )


    api = MetaApi(
        METAAPI_TOKEN
    )


    account = await api.metatrader_account_api.get_account(
        METAAPI_ACCOUNT_ID
    )


    connection = account.get_rpc_connection()


    await connection.connect()


    await connection.wait_synchronized()


    print(
        "MetaTrader 5 connected successfully."
    )


    return connection


# =========================================================
# PLACE BUY ORDER
# =========================================================

async def place_buy_order(

    symbol,
    volume=0.01,
    stop_loss=None,
    take_profit=None

):

    connection = await get_connection()


    result = await connection.create_market_buy_order(

        symbol,

        volume,

        stop_loss,

        take_profit

    )


    print(
        f"BUY order placed: {symbol}"
    )


    return result


# =========================================================
# PLACE SELL ORDER
# =========================================================

async def place_sell_order(

    symbol,
    volume=0.01,
    stop_loss=None,
    take_profit=None

):

    connection = await get_connection()


    result = await connection.create_market_sell_order(

        symbol,

        volume,

        stop_loss,

        take_profit

    )


    print(
        f"SELL order placed: {symbol}"
    )


    return result


# =========================================================
# SIMPLE TEST
# =========================================================

if __name__ == "__main__":

    print(
        "MetaApi trader module ready."
    )
