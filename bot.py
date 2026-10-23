import sqlite3

from datetime import datetime

from telethon import TelegramClient, events, Button

from telethon.tl.functions.channels import LeaveChannelRequest

from config import TelegramConfig

class TelegramBot:

    def __init__(

        self,

        config: TelegramConfig,

        database,

        user_client,

    ):

        self.config = config

        self.database = database

        # User's normal Telegram client.

        # This is needed because the bot itself cannot leave

        # channels that belong to the user's Telegram account.

        self.user_client = user_client

        # Telegram user ID who started the bot.

        self.owner_id = None

        self.client = TelegramClient(

            config.bot_session_name,

            config.api_id,

            config.api_hash,

        )

    async def connect(self):

        await self.client.start(

            bot_token=self.config.bot_token

        )

        me = await self.client.get_me()

        print("Telegram bot connected!")

        print(f"Bot name: {me.first_name}")

        print(f"Bot username: @{me.username}")

        self.client.add_event_handler(

            self.handle_start,

            events.NewMessage(

                incoming=True,

                pattern=r"^/start$",

            ),

        )

        self.client.add_event_handler(

            self.handle_callback,

            events.CallbackQuery(),

        )

    # -------------------------------------------------

    # MAIN MENU

    # -------------------------------------------------

    def menu_buttons(self):

        return [

            [

                Button.inline(

                    "🟡 Pending Channels",

                    b"pending"

                )

            ],

            [

                Button.inline(

                    "🟢 Active Channels",

                    b"active"

                )

            ],

            [

                Button.inline(

                    "⚪ Left Channels",

                    b"left"

                )

            ],

        ]

    async def handle_start(self, event):

        # Remember the Telegram user who owns the cleaner.

        self.owner_id = event.sender_id

        print(

            f"Bot user registered: {self.owner_id}"

        )

        await event.respond(

            "🤖 **Telegram Cleaner Agent**\n\n"

            "Choose an option:",

            buttons=self.menu_buttons(),

        )

    # -------------------------------------------------

    # PUBLIC CHANNEL NOTIFICATION

    # -------------------------------------------------

    async def notify_public_channel(

        self,

        channel_id: int,

        title: str,

        username: str | None,

        joined_at: str,

    ):

        # The bot needs to know which Telegram user

        # should receive the notification.

        if self.owner_id is None:

            print(

                "Bot notification skipped: "

                "user has not started the bot."

            )

            return

        if username:

            display_name = (

                f"{title} (@{username})"

            )

        else:

            display_name = title

        message = (

            "🟢 **New Public Channel Joined**\n\n"

            f"**Channel:** {display_name}\n"

            f"**Joined:** {joined_at}\n\n"

            "I will monitor this channel and check it "

            "after 8 days.\n\n"

            "You can leave it now if you want."

        )

        await self.client.send_message(

            self.owner_id,

            message,

            buttons=[

                [

                    Button.inline(

                        "🚪 Leave Now",

                        f"public_leave:{channel_id}".encode(),

                    )

                ]

            ],

        )

        print(

            f"Bot notification sent for public channel: "

            f"{title}"

        )

    # -------------------------------------------------

    # CALLBACK HANDLER

    # -------------------------------------------------

    async def notify_8_day_reminder(
        self,
        channel_id: int,
        title: str,
        username: str | None,
        joined_at: str,
    ):
        """Send the 8-day reminder with the existing Leave Now button."""
        if self.owner_id is None:
            print(
                "8-day reminder skipped: "
                "user has not started the bot."
            )
            return

        display_name = (
            f"{title} (@{username})"
            if username
            else title
        )

        message = (
            "⏰ **8-Day Channel Reminder**\n\n"
            f"**Channel:** {display_name}\n"
            f"**Joined:** {joined_at}\n\n"
            "You have been in this channel for at least "
            "8 days. Would you like to leave it?"
        )

        await self.client.send_message(
            self.owner_id,
            message,
            buttons=[
                [
                    Button.inline(
                        "🚪 Leave Now",
                        f"public_leave:{channel_id}".encode(),
                    )
                ]
            ],
        )

        print(
            f"8-day reminder sent for: {title}"
        )

    async def handle_callback(self, event):

        action = event.data.decode("utf-8")

        # -------------------------------------------------

        # PUBLIC CHANNEL - LEAVE NOW

        # -------------------------------------------------

        if action.startswith("public_leave:"):

            channel_id = int(

                action.split(":", 1)[1]

            )

            try:

                # Use the USER client, not the bot client.

                channel = (

                    await self.user_client.get_entity(

                        channel_id

                    )

                )

                title = getattr(

                    channel,

                    "title",

                    "Unknown",

                )

                # Leave the channel using the user's account.

                await self.user_client(

                    LeaveChannelRequest(

                        channel

                    )

                )

                # Update database immediately.

                self.database.update_status(

                    channel_id=channel_id,

                    status="left",

                    updated_at=(

                        datetime.now().isoformat()

                    ),

                )

                await event.edit(

                    "🚪 **Channel Left Successfully**\n\n"

                    f"Channel: **{title}**\n\n"

                    "You have left this public channel.\n"

                    "No 8-day reminder will be sent."

                )

                print(

                    f"User left public channel: {title}"

                )

            except Exception as error:

                print(

                    f"Error leaving public channel: "

                    f"{error}"

                )

                await event.answer(

                    "❌ Could not leave the channel.",

                    alert=True,

                )

            return

        # -------------------------------------------------

        # EXISTING DASHBOARD ACTIONS

        # -------------------------------------------------

        if action == "pending":

            await self.show_pending(event)

        elif action == "active":

            await self.show_active(event)

        elif action == "left":

            await self.show_left(event)

        elif action == "back":

            await self.show_menu(event)

        await event.answer()

    # -------------------------------------------------

    # DATABASE CONNECTION

    # -------------------------------------------------

    def get_connection(self):

        return sqlite3.connect(

            "channels.db"

        )

    # -------------------------------------------------

    # PENDING CHANNELS

    # -------------------------------------------------

    async def show_pending(self, event):

        connection = self.get_connection()

        try:

            cursor = connection.cursor()

            cursor.execute(

                """

                SELECT

                    title,

                    invite_hash,

                    status

                FROM pending_invites

                WHERE status = ?

                ORDER BY created_at DESC

                """,

                ("pending",),

            )

            rows = cursor.fetchall()

        finally:

            connection.close()

        if not rows:

            await event.edit(

                "🟡 **Pending Channels**\n\n"

                "No pending channels.",

                buttons=[

                    [

                        Button.inline(

                            "⬅️ Back",

                            b"back"

                        )

                    ]

                ],

            )

            return

        message = "🟡 **Pending Channels**\n\n"

        for index, row in enumerate(rows, start=1):

            title = row[0]

            invite_hash = row[1]

            message += (

                f"**{index}. {title}**\n"

                f"Invite hash: `{invite_hash}`\n"

                f"Status: 🟡 Pending\n\n"

            )

        await event.edit(

            message,

            buttons=[

                [

                    Button.inline(

                        "⬅️ Back",

                        b"back"

                    )

                ]

            ],

        )

    # -------------------------------------------------

    # ACTIVE CHANNELS

    # -------------------------------------------------

    async def show_active(self, event):

        connection = self.get_connection()

        try:

            cursor = connection.cursor()

            cursor.execute(

                """

                SELECT

                    title,

                    username,

                    status

                FROM channel_memberships

                WHERE status = ?

                ORDER BY updated_at DESC

                """,

                ("active",),

            )

            rows = cursor.fetchall()

        finally:

            connection.close()

        if not rows:

            await event.edit(

                "🟢 **Active Channels**\n\n"

                "No active channels.",

                buttons=[

                    [

                        Button.inline(

                            "⬅️ Back",

                            b"back"

                        )

                    ]

                ],

            )

            return

        message = "🟢 **Active Channels**\n\n"

        for index, row in enumerate(rows, start=1):

            title = row[0]

            username = row[1]

            if username:

                display_name = (

                    f"{title} (@{username})"

                )

            else:

                display_name = title

            message += (

                f"**{index}. {display_name}**\n"

                f"Status: 🟢 Active\n\n"

            )

        await event.edit(

            message,

            buttons=[

                [

                    Button.inline(

                        "⬅️ Back",

                        b"back"

                    )

                ]

            ],

        )

    # -------------------------------------------------

    # LEFT CHANNELS

    # -------------------------------------------------

    async def show_left(self, event):

        connection = self.get_connection()

        try:

            cursor = connection.cursor()

            cursor.execute(

                """

                SELECT

                    title,

                    username,

                    status

                FROM channel_memberships

                WHERE status = ?

                ORDER BY updated_at DESC

                """,

                ("left",),

            )

            rows = cursor.fetchall()

        finally:

            connection.close()

        if not rows:

            await event.edit(

                "⚪ **Left Channels**\n\n"

                "No channels have been left yet.",

                buttons=[

                    [

                        Button.inline(

                            "⬅️ Back",

                            b"back"

                        )

                    ]

                ],

            )

            return

        message = "⚪ **Left Channels**\n\n"

        for index, row in enumerate(rows, start=1):

            title = row[0]

            username = row[1]

            if username:

                display_name = (

                    f"{title} (@{username})"

                )

            else:

                display_name = title

            message += (

                f"**{index}. {display_name}**\n"

                f"Status: ⚪ Left\n\n"

            )

        await event.edit(

            message,

            buttons=[

                [

                    Button.inline(

                        "⬅️ Back",

                        b"back"

                    )

                ]

            ],

        )

    # -------------------------------------------------

    # BACK TO MENU

    # -------------------------------------------------

    async def show_menu(self, event):

        await event.edit(

            "🤖 **Telegram Cleaner Agent**\n\n"

            "Choose an option:",

            buttons=self.menu_buttons(),

        )

    # -------------------------------------------------

    # DISCONNECT

    # -------------------------------------------------

    async def disconnect(self):

        await self.client.disconnect()