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

                print(
                    f"Waiting {RETRY_DELAY} seconds..."
                )

                await asyncio.sleep(RETRY_DELAY)

            else:

                raise Exception(
                    f"Could not connect to MetaAPI: {e}"
                )


# =========================================================
# PLACE BUY ORDER
# =========================================================

async def place_buy_order(symbol, volume):

    connection = await get_connection()

    print(
        f"Placing BUY: {symbol} | Volume: {volume}"
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
        f"Placing SELL: {symbol} | Volume: {volume}"
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

    print(
        f"Open positions found: {len(positions)}"
    )

    return positions


# =========================================================
# GET TOTAL PROFIT / LOSS
# =========================================================

async def get_total_profit():

    positions = await get_open_positions()

    total_profit = 0.0

    for position in positions:

        profit = position.get(
            "profit",
            0
        )

        total_profit += float(profit)

    print(
        f"Total open profit/loss: ${total_profit:.2f}"
    )

    return total_profit


# =========================================================
# CLOSE ONE POSITION
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


# =========================================================
# CLOSE ALL OPEN POSITIONS
# =========================================================

async def close_all_positions():

    positions = await get_open_positions()

    if not positions:

        print(
            "No open positions to close."
        )

        return 0


    closed_count = 0


    for position in positions:

        try:

            position_id = position.get("id")

            symbol = position.get(
                "symbol",
                "Unknown"
            )

            if position_id:

                print(
                    f"Closing {symbol} "
                    f"| Position ID: {position_id}"
                )

                await close_position(
                    position_id
                )

                closed_count += 1

                await asyncio.sleep(1)


        except Exception as e:

            print(
                f"Error closing position: {e}"
            )


    print(
        f"Closed positions: {closed_count}"
    )

    return closed_count
