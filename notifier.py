class TelegramNotifier:

    def __init__(self, client, database):
        self.client = client
        self.database = database

    async def notify_new_channel(self, channel):

        message = (
            "🔔 New Telegram Channel Detected\n\n"
            f"Channel: {channel.title}\n"
            f"Username: @{channel.username or 'None'}\n\n"
            "Do you want to leave this channel?\n\n"
            "Reply YES to leave.\n"
            "Reply NO to keep the channel."
        )

        sent_message = await self.client.send_message(
            "me",
            message,
        )

        return sent_message