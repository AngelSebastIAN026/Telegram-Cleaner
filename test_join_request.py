
import asyncio

from config import load_config
from telegram_client import TelegramService


async def test_join_request():

    config = load_config()

    telegram = TelegramService(config)

    await telegram.connect()

    print("\n========================================")
    print("       JOIN REQUEST TEST")
    print("========================================")

    invite_link = input(
        "\nEnter the Telegram invite link: "
    ).strip()

    if "t.me/+" in invite_link:

        invite_hash = invite_link.split(
            "t.me/+",
            1
        )[1]

    elif "t.me/joinchat/" in invite_link:

        invite_hash = invite_link.split(
            "t.me/joinchat/",
            1
        )[1]

    else:

        print("\nInvalid Telegram invite link.")

        await telegram.disconnect()
        return

    print("\nSending join request...")

    try:

        result = await telegram.send_join_request(
            invite_hash
        )

        print("\nTelegram response:")

        print(f"Status: {result['status']}")
        print(f"Result: {result['result']}")

    except Exception as error:

        print(
            f"\nError: {type(error).__name__}"
        )

        print(
            f"Details: {error}"
        )

    finally:

        await telegram.disconnect()


asyncio.run(test_join_request())

