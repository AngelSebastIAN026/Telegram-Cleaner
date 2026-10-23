import asyncio

from telethon import events

from config import load_config
from database import Database
from telegram_client import TelegramService
from notifier import TelegramNotifier
from monitor import TelegramMonitor
from bot import TelegramBot


async def main():

    
    config = load_config()

    
    database = Database()
    database.initialize()

    
    telegram = TelegramService(config)
    await telegram.connect()

    

    notifier = TelegramNotifier(
        telegram.client,
        database,
    )

    

    telegram_bot = TelegramBot(
        config=config,
        database=database,
        user_client=telegram.client,
    )

    await telegram_bot.connect()

    

    monitor = TelegramMonitor(
        telegram.client,
        database,
        notifier,
        telegram_bot,
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

    

    print()
    print("==========================================")
    print("Telegram Cleaner Agent is running")
    print("==========================================")
    print()

    print("Cleaner monitor: ACTIVE")
    print("Dashboard bot: ACTIVE")
    print()

    print("Available bot options:")
    print("  🟡 Pending Channels")
    print("  🟢 Active Channels")
    print("  ⚪ Left Channels")
    print()

    

    try:

        while True:

            dialogs = await telegram.client.get_dialogs()

            
            await monitor.check_pending_channels(
                dialogs
            )

            
            await monitor.check_for_new_channels(
                dialogs
            )

            # Check every 5 seconds
            await asyncio.sleep(5)

    except KeyboardInterrupt:

        print()
        print("Stopping application...")

    finally:

        await telegram_bot.disconnect()
        await telegram.disconnect()


if __name__ == "__main__":
    asyncio.run(main())