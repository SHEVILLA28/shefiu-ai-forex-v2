import pandas as pd

def get_support_resistance(data, window=20):
    """
    Find simple support and resistance levels.
    """

    support = data["Low"].rolling(window).min().iloc[-1]
    resistance = data["High"].rolling(window).max().iloc[-1]

    return {
        "support": support,
        "resistance": resistance
    }
