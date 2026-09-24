from datetime import datetime
import re

from telethon.tl.functions.channels import LeaveChannelRequest
from telethon.tl.functions.messages import CheckChatInviteRequest

from models import ChannelMembership


class TelegramMonitor:

    def __init__(self, client, database, notifier):

        self.client = client
        self.database = database
        self.notifier = notifier

        # notification message ID -> channel ID
        self.pending_notifications = {}

        # Telegram user ID
        self.my_user_id = None

        # Channels that existed when the program started
        self.baseline_channel_ids = set()

        # Pending invite titles already printed
        # during this program run.
        self.printed_pending_invites = set()

    # ========================================
    # INITIALIZE
    # ========================================

    async def initialize(self):

        me = await self.client.get_me()

        self.my_user_id = me.id

        print(
            f"Telegram user ID: {self.my_user_id}"
        )

    # ========================================
    # INITIAL BASELINE
    # ========================================

    async def initialize_baseline(self):

        print("\nCreating initial channel baseline...")

        dialogs = await self.client.get_dialogs()

        for dialog in dialogs:

            if not dialog.is_channel:
                continue

            channel = dialog.entity

            channel_id = channel.id
            title = dialog.title

            # Remember channels that existed
            # before the program started.
            self.baseline_channel_ids.add(
                channel_id
            )

            username = getattr(
                channel,
                "username",
                None
            )

            existing_channel = self.database.get_channel(
                channel_id
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

        print("Initial baseline created.")

        # ====================================
        # SHOW EXISTING PENDING REQUESTS ONCE
        # ====================================

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

    # ========================================
    # NORMAL NEW CHANNEL DETECTION
    # ========================================

    async def check_for_new_channels(
        self,
        dialogs=None
    ):

        # Reuse dialogs if main.py provides them.
        # Otherwise get them normally.
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
                None
            )

            # Ignore channels that existed
            # before the program started.
            if channel_id in self.baseline_channel_ids:
                continue

            # Ignore channels belonging to
            # the pending join-request flow.
            if title in pending_titles:
                continue

            existing_channel = self.database.get_channel(
                channel_id
            )

            if existing_channel is not None:
                continue

            # ====================================
            # NEW CHANNEL FOUND
            # ====================================

            now = datetime.now()

            membership = ChannelMembership(
                channel_id=channel_id,
                title=title,
                username=username,
                status="active",
                created_at=now,
                updated_at=now,
            )

            self.database.add_channel(
                membership
            )

            print(
                "\n========================================"
            )

            print(
                f"🚨 NEW CHANNEL DETECTED: {title}"
            )

            print(
                f"Channel ID: {channel_id}"
            )

            print(
                f"Username: @{username or 'None'}"
            )

            print(
                "========================================"
            )

            notification = (
                await self.notifier.notify_new_channel(
                    membership
                )
            )

            self.pending_notifications[
                notification.id
            ] = channel_id

            print(
                f"Notification sent for: {title}"
            )

    # ========================================
    # PRIVATE INVITE DETECTION
    # ========================================

    async def handle_pending_join_request(
        self,
        update
    ):

        message = getattr(
            update,
            "message",
            None
        )

        if message is None:
            return

        reply_markup = getattr(
            message,
            "reply_markup",
            None
        )

        if reply_markup is None:
            return

        for row in reply_markup.rows:

            for button in row.buttons:

                button_text = getattr(
                    button,
                    "text",
                    ""
                ) or ""

                button_type = getattr(
                    button,
                    "type",
                    None
                )

                button_url = getattr(
                    button_type,
                    "url",
                    None
                )

                if not button_url:
                    continue

                match = re.search(
                    r"(?:https?://)?t\.me/\+([A-Za-z0-9_-]+)",
                    button_url
                )

                if not match:
                    continue

                invite_hash = match.group(1)

                # ====================================
                # CHECK DATABASE FIRST
                # ====================================

                existing_pending = (
                    self.database.get_pending_invite(
                        invite_hash
                    )
                )

                # Already stored.
                # Do not call Telegram again.
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

                    # IMPORTANT:
                    # This is called ONLY ONCE for
                    # a newly detected invite.
                    invite = await self.client(
                        CheckChatInviteRequest(
                            invite_hash
                        )
                    )

                    invite_title = getattr(
                        invite,
                        "title",
                        "Unknown"
                    )

                    request_needed = getattr(
                        invite,
                        "request_needed",
                        False
                    )

                    print(
                        f"Invite title: {invite_title}"
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

                        now = datetime.now().isoformat()

                        self.database.add_pending_invite(
                            invite_hash=invite_hash,
                            title=invite_title,
                            created_at=now,
                            updated_at=now,
                        )

                        print(
                            f"⏳ Pending join request: "
                            f"{invite_title}"
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

    # ========================================
    # CHECK PENDING REQUESTS
    # ========================================

    async def check_pending_channels(
        self,
        dialogs=None
    ):

        pending_invites = (
            self.database.get_pending_invites()
        )

        if not pending_invites:
            return

        # Reuse dialogs if main.py provides them.
        # Otherwise get them normally.
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

                # Still waiting for approval.
                # Do not print anything.
                continue

            await self.handle_approved_channel(
                invite_hash,
                approved_channel["entity"]
            )

    # ========================================
    # HANDLE APPROVED REQUEST
    # ========================================

    async def handle_approved_channel(
        self,
        invite_hash,
        channel
    ):

        channel_id = channel.id

        channel_title = getattr(
            channel,
            "title",
            "Unknown"
        )

        username = getattr(
            channel,
            "username",
            None
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
            f"🚪 Automatically leaving: "
            f"{channel_title}"
        )

        try:

            await self.client(
                LeaveChannelRequest(
                    channel
                )
            )

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

            else:

                self.database.update_status(
                    channel_id=channel_id,
                    status="left",
                    updated_at=now.isoformat(),
                )

            self.database.update_pending_invite_status(
                invite_hash=invite_hash,
                status="left",
                updated_at=now.isoformat(),
            )

            print(
                f"✅ {channel_title} "
                f"left successfully."
            )

            print(
                "Database status: left"
            )

            print(
                "========================================\n"
            )

        except Exception as error:

            print(
                f"❌ Error while leaving "
                f"{channel_title}: {error}"
            )

    # ========================================
    # YES / NO REPLY
    # ========================================

    async def handle_reply(self, event):

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

        # ====================================
        # YES -> LEAVE
        # ====================================

        if answer == "yes":

            print(
                f"\nUser chose to leave channel: "
                f"{channel_id}"
            )

            try:

                channel = await self.client.get_entity(
                    channel_id
                )

                await self.client(
                    LeaveChannelRequest(channel)
                )

                self.database.update_status(
                    channel_id=channel_id,
                    status="left",
                    updated_at=datetime.now().isoformat(),
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

        # ====================================
        # NO -> KEEP
        # ====================================

        elif answer == "no":

            print(
                f"\nUser chose to keep channel: "
                f"{channel_id}"
            )

            self.database.update_status(
                channel_id=channel_id,
                status="kept",
                updated_at=datetime.now().isoformat(),
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
