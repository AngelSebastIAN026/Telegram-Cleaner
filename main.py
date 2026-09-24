import asyncio

from telethon import events

from config import load_config
from database import Database
from telegram_client import TelegramService
from notifier import TelegramNotifier
from monitor import TelegramMonitor


async def main():


    config = load_config()


    telegram = TelegramService(config)

    await telegram.connect()

    database = Database()

    database.initialize()


    notifier = TelegramNotifier(
        telegram.client,
        database,
    )


    monitor = TelegramMonitor(
        telegram.client,
        database,
        notifier,
    )


    await monitor.initialize()

    
    telegram.client.add_event_handler(
        monitor.handle_reply,
        events.NewMessage,
    )

    

    telegram.client.add_event_handler(
        monitor.handle_pending_join_request,
        events.Raw,
    )

    

    await monitor.initialize_baseline()

    

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

    

    try:

        while True:

            
            dialogs = await telegram.client.get_dialogs()

            

            await monitor.check_pending_channels(
                dialogs
            )

            

            await monitor.check_for_new_channels(
                dialogs
            )

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



asyncio.run(main())

