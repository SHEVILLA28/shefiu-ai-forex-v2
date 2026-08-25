import os
# ==============================
# AI FOREX BOT CONFIGURATION
# ==============================

# Telegram Bot
BOT_TOKEN = os.environ.get("BOT_TOKEN")  
CHAT_ID = os.environ.get("CHAT_ID")

# Trading Settings
TIMEFRAME = "15m"

SYMBOLS = [
    "EURUSD",
    "GBPUSD",
    "USDJPY",
    "AUDUSD",
    "USDCAD",
    "USDCHF",
    "NZDUSD",
]

# Signal Settings
RSI_PERIOD = 14
EMA_FAST = 20
EMA_SLOW = 50
RISK_PERCENT = 2

# General Settings
DEBUG = True
