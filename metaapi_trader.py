# =========================================================
# START BOT
# =========================================================

if __name__ == "__main__":

    print(
        "Starting SHEFIU AI FOREX V2..."
    )


    # Start Render health server

    health_thread = threading.Thread(
        target=run_health_server,
        daemon=True
    )

    health_thread.start()


    # Start Telegram manual bot

    telegram_thread = threading.Thread(
        target=run_telegram_bot,
        daemon=True
    )

    telegram_thread.start()


    print(
        "Manual Telegram bot started."
    )


    # =============================================
    # TEMPORARY METAAPI TEST TRADE
    # DEMO ACCOUNT ONLY
    # =============================================

    print(
        "Testing MetaAPI connection with EURUSD BUY..."
    )

    test_success = execute_trade(
        "BUY",
        "EUR/USD"
    )

    print(
        f"MetaAPI test result: {test_success}"
    )


    # Start automatic Forex scanner

    scanner_thread = threading.Thread(
        target=run_automatic_scanner,
        daemon=True
    )

    scanner_thread.start()


    print(
        "Automatic Forex scanner started."
    )


    # Keep Render service running

    while True:

        time.sleep(60)
