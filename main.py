import asyncio

from telethon import events

from config import load_config
from database import Database
from telegram_client import TelegramService
from notifier import TelegramNotifier
from monitor import TelegramMonitor


async def main():

    # ========================================
    # LOAD CONFIGURATION
    # ========================================

    config = load_config()

    # ========================================
    # CONNECT TO TELEGRAM
    # ========================================

    telegram = TelegramService(config)

    await telegram.connect()

    # ========================================
    # INITIALIZE DATABASE
    # ========================================

    database = Database()

    database.initialize()

    # ========================================
    # CREATE NOTIFIER
    # ========================================

    notifier = TelegramNotifier(
        telegram.client,
        database,
    )

    # ========================================
    # CREATE MONITOR
    # ========================================

    monitor = TelegramMonitor(
        telegram.client,
        database,
        notifier,
    )

    # ========================================
    # INITIALIZE TELEGRAM USER
    # ========================================

    await monitor.initialize()

    # ========================================
    # LISTEN FOR YES / NO REPLIES
    # ========================================

    telegram.client.add_event_handler(
        monitor.handle_reply,
        events.NewMessage,
    )

    # ========================================
    # LISTEN FOR PRIVATE INVITE LINKS
    # ========================================

    telegram.client.add_event_handler(
        monitor.handle_pending_join_request,
        events.Raw,
    )

    # ========================================
    # CREATE INITIAL BASELINE
    # ========================================

    await monitor.initialize_baseline()

    # ========================================
    # START MESSAGE
    # ========================================

    print(
        "\n========================================"
    )

    print(
        "       TELEGRAM CHANNEL CLEANER"
    )

    print(
        "========================================"
    )

    print(
        "Monitoring for new channels..."
    )

    print(
        "Monitoring join requests..."
    )

    print(
        "Pending requests will be left automatically"
    )

    print(
        "after approval."
    )

    print(
        "Reply YES or NO to normal channel notifications."
    )

    print(
        "Press Ctrl+C to stop."
    )

    # ========================================
    # MAIN MONITORING LOOP
    # ========================================

    try:

        while True:

            # Get Telegram dialogs ONLY ONCE.
            #
            # The same result is passed to both
            # pending-request checking and normal
            # channel checking.
            dialogs = await telegram.client.get_dialogs()

            # ====================================
            # CHECK PENDING JOIN REQUESTS
            # ====================================

            await monitor.check_pending_channels(
                dialogs
            )

            # ====================================
            # CHECK NORMAL NEW CHANNELS
            # ====================================

            await monitor.check_for_new_channels(
                dialogs
            )

            # Wait before checking again.
            await asyncio.sleep(5)

    except KeyboardInterrupt:

        print(
            "\nStopping Telegram Channel Cleaner..."
        )

    finally:

        await telegram.disconnect()

        print(
            "Disconnected from Telegram."
        )


# ============================================
# RUN PROGRAM
# ============================================

asyncio.run(main())

