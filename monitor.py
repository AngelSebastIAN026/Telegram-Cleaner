from datetime import datetime
import re

from telethon.tl.functions.channels import LeaveChannelRequest
from telethon.tl.functions.messages import CheckChatInviteRequest

from models import ChannelMembership
from llm import GeminiLLM


class TelegramMonitor:

    def __init__(
        self,
        client,
        database,
        notifier,
        bot,
    ):

        self.client = client
        self.database = database
        self.notifier = notifier
        self.bot = bot

        
        self.agent = GeminiLLM(
            telegram_client=client,
            database=database,
        )

        self.pending_notifications = {}

        self.my_user_id = None

        self.baseline_channel_ids = set()

        self.printed_pending_invites = set()

        
        self.recently_processed_channel_ids = set()

    async def initialize(self):

        me = await self.client.get_me()

        self.my_user_id = me.id

        print(
            f"Telegram user ID: {self.my_user_id}"
        )

    async def initialize_baseline(self):

        print(
            "\nCreating initial channel baseline..."
        )

        dialogs = await self.client.get_dialogs()

        for dialog in dialogs:

            if not dialog.is_channel:
                continue

            channel = dialog.entity

            channel_id = channel.id
            title = dialog.title

            self.baseline_channel_ids.add(
                channel_id
            )

            username = getattr(
                channel,
                "username",
                None,
            )

            existing_channel = (
                self.database.get_channel(
                    channel_id
                )
            )

            if existing_channel is not None:
                continue

            now = datetime.now()

            membership = ChannelMembership(
                channel_id=channel_id,
                title=title,
                username=username,
                status="existing",
                created_at=now,
                updated_at=now,
            )

            self.database.add_channel(
                membership
            )

            print(
                f"Baseline: {title}"
            )

        print(
            "Initial baseline created."
        )

        pending_invites = (
            self.database.get_pending_invites()
        )

        for pending_invite in pending_invites:

            pending_title = pending_invite[2]

            if (
                pending_title
                not in self.printed_pending_invites
            ):

                print(
                    f"⏳ Pending join request: "
                    f"{pending_title}"
                )

                self.printed_pending_invites.add(
                    pending_title
                )

    

    async def check_for_new_channels(
        self,
        dialogs=None,
    ):

        if dialogs is None:

            dialogs = await self.client.get_dialogs()

        pending_invites = (
            self.database.get_pending_invites()
        )

        pending_titles = {
            invite[2]
            for invite in pending_invites
        }

        for dialog in dialogs:

            if not dialog.is_channel:
                continue

            channel = dialog.entity

            channel_id = channel.id
            title = dialog.title

            username = getattr(
                channel,
                "username",
                None,
            )

            

            if (
                channel_id
                in self.recently_processed_channel_ids
            ):
                continue

            

            if channel_id in self.baseline_channel_ids:
                continue

            

            if title in pending_titles:
                continue

            

            existing_channel = (
                self.database.get_channel(
                    channel_id
                )
            )

            if existing_channel is not None:
                continue

            
            if not username:
                continue

            now = datetime.now()

            joined_at = now.isoformat()

            

            self.database.add_public_channel(
                channel_id=channel_id,
                title=title,
                username=username,
                joined_at=joined_at,
                created_at=joined_at,
                updated_at=joined_at,
            )

            print(
                "\n========================================"
            )

            print(
                f"🟢 NEW PUBLIC CHANNEL JOINED: {title}"
            )

            print(
                f"Channel ID: {channel_id}"
            )

            print(
                f"Username: @{username}"
            )

            print(
                f"Joined at: {joined_at}"
            )

            print(
                "========================================"
            )

            
            try:

                await self.bot.notify_public_channel(
                    channel_id=channel_id,
                    title=title,
                    username=username,
                    joined_at=joined_at,
                )

                print(
                    f"Immediate notification sent: {title}"
                )

            except Exception as error:

                print(
                    f"❌ Could not send public channel "
                    f"notification: {error}"
                )

        

        await self.check_public_channels_after_8_days(
            dialogs=dialogs
        )

    

    
    async def check_public_channels_after_8_days(
        self,
        dialogs=None,
    ):
        if dialogs is None:
            dialogs = await self.client.get_dialogs()

        current_channel_ids = {
            dialog.entity.id
            for dialog in dialogs
            if dialog.is_channel
        }

        try:
            with self.database.connect() as connection:
                rows = connection.execute(
                    """
                    SELECT
                        channel_id,
                        title,
                        username,
                        joined_at,
                        reminder_sent
                    FROM channel_memberships
                    WHERE status = 'active'
                      AND username IS NOT NULL
                      AND joined_at IS NOT NULL
                    """
                ).fetchall()

        except Exception as error:
            print(f"Could not check 8-day reminders: {error}")
            return

        now = datetime.now()

        for row in rows:
            channel_id, title, username, joined_at_value, reminder_sent = row

            if reminder_sent:
                continue

            if channel_id not in current_channel_ids:
                continue

            try:
                joined_at = datetime.fromisoformat(joined_at_value)
            except (ValueError, TypeError):
                print(f"Invalid joined_at for {title}: {joined_at_value}")
                continue

            
            if joined_at.tzinfo is not None:
                from datetime import timezone
                current_time = datetime.now(timezone.utc)
                joined_at = joined_at.astimezone(timezone.utc)
            else:
                current_time = now

            days_joined = (
                current_time - joined_at
            ).total_seconds() / 86400

            if days_joined < 8:
                continue


            if getattr(self.bot, "owner_id", None) is None:
                continue

            try:
                await self.bot.notify_8_day_reminder(
                    channel_id=channel_id,
                    title=title,
                    username=username,
                    joined_at=joined_at_value,
                )

                self.database.mark_reminder_sent(channel_id)
                print(f"8-day reminder sent: {title}")

            except Exception as error:
                print(f"Could not send reminder for {title}: {error}")

    

    async def handle_pending_join_request(
        self,
        update,
    ):

        message = getattr(
            update,
            "message",
            None,
        )

        if message is None:
            return

        reply_markup = getattr(
            message,
            "reply_markup",
            None,
        )

        if reply_markup is None:
            return

        
        rows = getattr(reply_markup, "rows", None)
        if not rows:
            return

        for row in rows:

            for button in row.buttons:

                button_text = getattr(
                    button,
                    "text",
                    "",
                ) or ""

                button_type = getattr(
                    button,
                    "type",
                    None,
                )

                button_url = getattr(
                    button_type,
                    "url",
                    None,
                )

                if not button_url:
                    continue

                match = re.search(
                    r"(?:https?://)?t\.me/\+([A-Za-z0-9_-]+)",
                    button_url,
                )

                if not match:
                    continue

                invite_hash = match.group(1)

                existing_pending = (
                    self.database.get_pending_invite(
                        invite_hash
                    )
                )

                if existing_pending is not None:
                    return

                print(
                    "\n========================================"
                )

                print(
                    "🔗 PRIVATE INVITE LINK DETECTED"
                )

                print(
                    f"Button: {button_text}"
                )

                print(
                    f"Invite hash: {invite_hash}"
                )

                try:

                    invite = await self.client(
                        CheckChatInviteRequest(
                            invite_hash
                        )
                    )

                    invite_title = getattr(
                        invite,
                        "title",
                        "Unknown",
                    )

                    request_needed = getattr(
                        invite,
                        "request_needed",
                        False,
                    )

                    print(
                        f"Invite title: "
                        f"{invite_title}"
                    )

                    print(
                        f"Request needed: "
                        f"{request_needed}"
                    )

                    if request_needed:

                        print(
                            "🟡 This channel requires "
                            "admin approval."
                        )

                        print()
                        print(
                            "🤖 Sending event to "
                            "Gemini Agent..."
                        )

                        agent_result = (
                            await self.agent.ask_with_tool(
                                f"""
You are the Telegram Cleaner Agent.

A private Telegram channel invite has been detected.

Channel title:
{invite_title}

Invite hash:
{invite_hash}

Telegram reports that this invite requires administrator approval.

Your task is to decide the correct action.

Because this is a private invite requiring approval,
track it as a pending channel by calling the
store_pending_invite function.

Do not leave any channel at this stage.

Do not invent any information.

Use the function tool to store the pending invite.
"""
                            )
                        )

                        print()
                        print(
                            "🤖 Gemini Agent result:"
                        )

                        print(
                            agent_result
                        )

                        self.printed_pending_invites.add(
                            invite_title
                        )

                    else:

                        print(
                            "🟢 This invite does not "
                            "require admin approval."
                        )

                except Exception as error:

                    print(
                        f"❌ Could not inspect invite: "
                        f"{error}"
                    )

                print(
                    "========================================\n"
                )

                return

    

    async def check_pending_channels(
        self,
        dialogs=None,
    ):

        pending_invites = (
            self.database.get_pending_invites()
        )

        if not pending_invites:
            return

        if dialogs is None:

            dialogs = await self.client.get_dialogs()

        current_channels = []

        for dialog in dialogs:

            if not dialog.is_channel:
                continue

            current_channels.append(
                {
                    "id": dialog.entity.id,
                    "title": dialog.title,
                    "entity": dialog.entity,
                }
            )

        for pending_invite in pending_invites:

            invite_hash = pending_invite[1]
            pending_title = pending_invite[2]

            approved_channel = None

            for current_channel in current_channels:

                if (
                    current_channel["title"]
                    == pending_title
                ):

                    approved_channel = (
                        current_channel
                    )

                    break

            if approved_channel is None:
                continue

            await self.handle_approved_channel(
                invite_hash,
                approved_channel["entity"],
            )

    

    async def handle_approved_channel(
        self,
        invite_hash,
        channel,
    ):

        channel_id = channel.id

        channel_title = getattr(
            channel,
            "title",
            "Unknown",
        )

        username = getattr(
            channel,
            "username",
            None,
        )

        print(
            "\n========================================"
        )

        print(
            f"✅ JOIN REQUEST APPROVED: "
            f"{channel_title}"
        )

        print(
            f"Channel ID: {channel_id}"
        )

        print(
            "🤖 Sending approved channel "
            "to Gemini Agent..."
        )

        try:

            agent_result = (
                await self.agent.ask_with_tool(
                    f"""
You are the Telegram Cleaner Agent.

A previously tracked private Telegram channel
has now been approved and the user has joined it.

Channel title:
{channel_title}

Channel ID:
{channel_id}

Invite hash:
{invite_hash}

The channel was previously stored as a pending
invite because administrator approval was required.

Now that the join request has been approved,
decide the correct cleanup action.

This channel was intentionally tracked as a
temporary channel.

Call the leave_channel function to leave it.

Do not invent any information.

Use the provided channel ID, invite hash,
and channel title exactly as given.
"""
                )
            )

            print()
            print(
                "🤖 Gemini Agent result:"
            )

            print(
                agent_result
            )

            agent_left_channel = False

            tool_results = agent_result.get(
                "tool_results",
                [],
            )

            for tool_result in tool_results:

                if (
                    tool_result.get("tool_name")
                    == "leave_channel"
                ):

                    result = tool_result.get(
                        "result",
                        {},
                    )

                    if (
                        isinstance(result, dict)
                        and result.get("status")
                        == "left"
                    ):

                        agent_left_channel = True

                        break

            if agent_left_channel:

                now = datetime.now()

                existing_channel = (
                    self.database.get_channel(
                        channel_id
                    )
                )

                if existing_channel is None:

                    membership = ChannelMembership(
                        channel_id=channel_id,
                        title=channel_title,
                        username=username,
                        status="left",
                        created_at=now,
                        updated_at=now,
                    )

                    self.database.add_channel(
                        membership
                    )

                    print(
                        "Database: channel recorded "
                        "with status = left"
                    )

                else:

                    self.database.update_status(
                        channel_id=channel_id,
                        status="left",
                        updated_at=now.isoformat(),
                    )

                    print(
                        "Database: channel status "
                        "updated to left"
                    )

                self.recently_processed_channel_ids.add(
                    channel_id
                )

                print(
                    f"✅ Agent cleanup completed: "
                    f"{channel_title}"
                )

            print(
                "========================================\n"
            )

        except Exception as error:

            print(
                f"❌ Error while processing approved "
                f"channel {channel_title}: {error}"
            )

    

    async def handle_reply(
        self,
        event,
    ):

        if not event.out:
            return

        if not event.is_private:
            return

        if event.message.reply_to_msg_id is None:
            return

        reply_message_id = (
            event.message.reply_to_msg_id
        )

        if (
            reply_message_id
            not in self.pending_notifications
        ):
            return

        channel_id = (
            self.pending_notifications[
                reply_message_id
            ]
        )

        answer = (
            event.raw_text
            .strip()
            .lower()
        )

        if answer == "yes":

            print(
                f"\nUser chose to leave channel: "
                f"{channel_id}"
            )

            try:

                channel = (
                    await self.client.get_entity(
                        channel_id
                    )
                )

                await self.client(
                    LeaveChannelRequest(
                        channel
                    )
                )

                self.database.update_status(
                    channel_id=channel_id,
                    status="left",
                    updated_at=(
                        datetime.now()
                        .isoformat()
                    ),
                )

                await event.reply(
                    "🚪 You left the channel successfully."
                )

                print(
                    "Channel left successfully."
                )

                del self.pending_notifications[
                    reply_message_id
                ]

            except Exception as error:

                print(
                    f"Error while leaving channel: "
                    f"{error}"
                )

        elif answer == "no":

            print(
                f"\nUser chose to keep channel: "
                f"{channel_id}"
            )

            self.database.update_status(
                channel_id=channel_id,
                status="kept",
                updated_at=(
                    datetime.now()
                    .isoformat()
                ),
            )

            await event.reply(
                "✅ Channel kept. You are staying "
                "in this channel."
            )

            print(
                "Channel kept."
            )

            del self.pending_notifications[
                reply_message_id
            ]