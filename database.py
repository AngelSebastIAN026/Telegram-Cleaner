import sqlite3
import os

from datetime import datetime

from models import ChannelMembership



class Database:

    def __init__(self, database_path: str = "channels.db"):

        self.database_path = database_path

        print(
            "Database file:",
            os.path.abspath(self.database_path)
        )

    def connect(self):

        return sqlite3.connect(
            self.database_path
        )

    def initialize(self):

        with self.connect() as connection:

            

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS channel_memberships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id INTEGER NOT NULL UNIQUE,
                    title TEXT NOT NULL,
                    username TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    joined_at TEXT,
                    reminder_sent INTEGER NOT NULL DEFAULT 0
                )
                """
            )

            

            try:

                connection.execute(
                    """
                    ALTER TABLE channel_memberships
                    ADD COLUMN joined_at TEXT
                    """
                )

            except sqlite3.OperationalError:

                
                pass

            try:

                connection.execute(
                    """
                    ALTER TABLE channel_memberships
                    ADD COLUMN reminder_sent INTEGER
                    NOT NULL DEFAULT 0
                    """
                )

            except sqlite3.OperationalError:

                
                pass

            

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS pending_invites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    invite_hash TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

            

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS movie_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    movie_name TEXT NOT NULL,
                    requester_id INTEGER,
                    status TEXT NOT NULL,
                    result TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    completed_at TEXT
                )
                """
            )

            

            try:

                connection.execute(
                    """
                    ALTER TABLE movie_tasks
                    ADD COLUMN requester_id INTEGER
                    """
                )

            except sqlite3.OperationalError:

                
                pass

            
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS task_channels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    channel_id INTEGER,
                    channel_title TEXT NOT NULL,
                    invite_hash TEXT,
                    access_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    temporary INTEGER NOT NULL DEFAULT 1,
                    joined_at TEXT,
                    left_at TEXT,
                    FOREIGN KEY (task_id)
                        REFERENCES movie_tasks(id)
                )
                """
            )

            connection.commit()

    

    def add_channel(
        self,
        channel: ChannelMembership
    ):

        with self.connect() as connection:

            connection.execute(
                """
                INSERT INTO channel_memberships
                (
                    channel_id,
                    title,
                    username,
                    status,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    channel.channel_id,
                    channel.title,
                    channel.username,
                    channel.status,
                    channel.created_at.isoformat(),
                    channel.updated_at.isoformat(),
                ),
            )

            connection.commit()

    def update_status(
        self,
        channel_id: int,
        status: str,
        updated_at: str,
    ):

        with self.connect() as connection:

            connection.execute(
                """
                UPDATE channel_memberships
                SET status = ?, updated_at = ?
                WHERE channel_id = ?
                """,
                (
                    status,
                    updated_at,
                    channel_id,
                ),
            )

            connection.commit()

    def get_channel(
        self,
        channel_id: int
    ):

        with self.connect() as connection:

            cursor = connection.execute(
                """
                SELECT
                    id,
                    channel_id,
                    title,
                    username,
                    status,
                    created_at,
                    updated_at
                FROM channel_memberships
                WHERE channel_id = ?
                """,
                (channel_id,),
            )

            return cursor.fetchone()

    
    def add_public_channel(
        self,
        channel_id: int,
        title: str,
        username: str | None,
        joined_at: str,
        created_at: str,
        updated_at: str,
    ):

        with self.connect() as connection:

            connection.execute(
                """
                INSERT OR IGNORE INTO channel_memberships
                (
                    channel_id,
                    title,
                    username,
                    status,
                    created_at,
                    updated_at,
                    joined_at,
                    reminder_sent
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    channel_id,
                    title,
                    username,
                    "active",
                    created_at,
                    updated_at,
                    joined_at,
                    0,
                ),
            )

            connection.commit()

            print(
                f"Database: public channel saved -> {title}"
            )

    def mark_reminder_sent(
        self,
        channel_id: int,
    ):

        with self.connect() as connection:

            connection.execute(
                """
                UPDATE channel_memberships
                SET reminder_sent = 1
                WHERE channel_id = ?
                """,
                (channel_id,),
            )

            connection.commit()

    

    def add_pending_invite(
        self,
        invite_hash: str,
        title: str,
        created_at: str,
        updated_at: str,
    ):

        with self.connect() as connection:

            connection.execute(
                """
                INSERT OR IGNORE INTO pending_invites
                (
                    invite_hash,
                    title,
                    status,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    invite_hash,
                    title,
                    "pending",
                    created_at,
                    updated_at,
                ),
            )

            connection.commit()

            print(
                f"Database: pending invite saved -> {title}"
            )

    def get_pending_invites(self):

        with self.connect() as connection:

            cursor = connection.execute(
                """
                SELECT
                    id,
                    invite_hash,
                    title,
                    status,
                    created_at,
                    updated_at
                FROM pending_invites
                WHERE status = ?
                """,
                ("pending",),
            )

            return cursor.fetchall()

    def get_pending_invite(
        self,
        invite_hash: str,
    ):

        with self.connect() as connection:

            cursor = connection.execute(
                """
                SELECT
                    id,
                    invite_hash,
                    title,
                    status,
                    created_at,
                    updated_at
                FROM pending_invites
                WHERE invite_hash = ?
                """,
                (invite_hash,),
            )

            return cursor.fetchone()

    def update_pending_invite_status(
        self,
        invite_hash: str,
        status: str,
        updated_at: str,
    ):

        with self.connect() as connection:

            connection.execute(
                """
                UPDATE pending_invites
                SET status = ?, updated_at = ?
                WHERE invite_hash = ?
                """,
                (
                    status,
                    updated_at,
                    invite_hash,
                ),
            )

            connection.commit()

            print(
                f"Database: pending invite updated -> "
                f"{status}"
            )

    

    