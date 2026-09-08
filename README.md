# SHEFIU AI FOREX V2 - FIXED

## Start command
`python main.py`

## Required Render environment variables
- `BOT_TOKEN`
- `CHAT_ID`
- `TWELVE_DATA_API_KEY`
- `METAAPI_TOKEN`
- `METAAPI_ACCOUNT_ID`

Optional controls are in `.env.example`.

## Important
- The bot scans selected pairs in small rotating batches to reduce Twelve Data request bursts.
- The bot pauses all Twelve Data requests for a longer cooldown after a provider rate-limit response instead of continuing to hammer the API.
- The scanner derives the 15-minute confirmation from 5-minute candles when possible, reducing API calls.
- Automatic trading has maximum-open-trades, same-symbol, cooldown, and SL/TP direction checks.
- Test the corrected deployment on a demo account before enabling real-money trading.

This software can generate or execute trades but cannot guarantee profitable results.
