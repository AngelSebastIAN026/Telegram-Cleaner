from datetime import datetime

from pydantic import BaseModel


class ChannelInfo(BaseModel):
    channel_id: int
    title: str
    username: str | None = None


class ChannelMembership(BaseModel):
    channel_id: int
    title: str
    username: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime