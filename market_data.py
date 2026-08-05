import yfinance as yf
import pandas as pd


def get_market_data(symbol, interval="15m", period="5d"):
    """
    Download market data from Yahoo Finance.
    """

    try:
        data = yf.download(
            symbol,
            interval=interval,
            period=period,
            progress=False,
            auto_adjust=True,
        )

        if data.empty:
            return None

        return data

    except Exception as e:
        print(f"Error loading {symbol}: {e}")
        return None
