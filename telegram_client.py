
from telethon import TelegramClient
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.errors import InviteRequestSentError

from config import TelegramConfig


class TelegramService:

    def __init__(self, config: TelegramConfig):
        self.config = config

        self.client = TelegramClient(
            config.session_name,
            config.api_id,
            config.api_hash,
        )

    async def connect(self):
        await self.client.start()

        me = await self.client.get_me()

        print("Successfully connected!")
        print(f"Name: {me.first_name}")
        print(f"Username: {me.username}")

    async def disconnect(self):
        await self.client.disconnect()

    async def send_join_request(self, invite_hash: str):

        try:
            result = await self.client(
                ImportChatInviteRequest(invite_hash)
            )

            print("Joined the channel directly.")

            return {
                "status": "active",
                "result": result,
            }

        except InviteRequestSentError:

            print("Join request sent successfully.")

            return {
                "status": "requested",
                "result": None,
            }

