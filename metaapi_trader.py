import os

from metaapi_cloud_sdk import MetaApi


METAAPI_TOKEN = os.getenv("METAAPI_TOKEN")
METAAPI_ACCOUNT_ID = os.getenv("METAAPI_ACCOUNT_ID")


async def get_connection():

    if not METAAPI_TOKEN:
        raise Exception("METAAPI_TOKEN is missing")

    if not METAAPI_ACCOUNT_ID:
        raise Exception("METAAPI_ACCOUNT_ID is missing")

    api = MetaApi(METAAPI_TOKEN)

    account = await api.metatrader_account_api.get_account(
        METAAPI_ACCOUNT_ID
    )

    connection = account.get_rpc_connection()

    await connection.connect()

    await connection.wait_synchronized()

    return connection


async def place_buy_order(symbol, volume):

    connection = await get_connection()

    result = await connection.create_market_buy_order(
        symbol,
        volume
    )

    return result


async def place_sell_order(symbol, volume):

    connection = await get_connection()

    result = await connection.create_market_sell_order(
        symbol,
        volume
    )

    return result
