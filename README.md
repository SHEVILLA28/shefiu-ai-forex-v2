# shefiu-ai-forex-v2

## Market session control update

The bot now uses one central Forex session controller based on the New York
5:00 PM weekly session boundary. This handles daylight-saving changes without
hard-coding a UTC hour. When AUTO is enabled, the scanner pauses while the
weekly market is closed and checks again automatically every minute. It resumes
after the session opens without requiring a manual Render restart.
