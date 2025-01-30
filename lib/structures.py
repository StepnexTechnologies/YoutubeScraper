from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from enum import Enum

from pydantic import BaseModel


@dataclass
class YtScraperConfig:
    log_directory: str = "logs"
    data_directory: str = "data"
    proxy: Optional[str] = None
    print_logs_to_console: bool = True


class BaseContent(BaseModel):
    views: int
    likes: int
    comments_count: int
    hashtags: Optional[List[str]]
    fetched_timestamp: str


class Link(BaseModel):
    title: str
    url: str


class AffiliatedChannel(BaseModel):
    name: str
    url: str
    code: str
    subscribers: int


class ChannelInfo(BaseModel):
    channel_code: str
    name: Optional[str]
    is_verified: Optional[bool]
    about: Optional[str]
    links: List[Link]
    display_picture_url: Optional[str]  # TODO: Not Implemented yet
    banner_url: Optional[str]  # TODO: Not Implemented yet
    affiliated_channels: Optional[List[AffiliatedChannel]]  # TODO: Not Implemented yet
    subscribers: Optional[int]
    videos_count: Optional[int]
    views_count: Optional[int]
    joined_date: Optional[str]
    location: Optional[str]  # TODO:Not Implemented yet


class Comment(BaseModel):
    comment: str
    commenter_channel_name: str
    commenter_display_picture_url: Optional[
        str
    ]  # TODO: Not implemented for shorts and videos, remove Optional once done
    likes: int
    date: str
    replies_count: int
    liked_by_creator: bool


class RelatedVideo(BaseModel):
    code: str
    url: str
    thumbnail_url: str
    title: str
    channel_name: str
    is_channel_verified: bool
    posted_date: str
    duration: int
    views: int


class TranscriptItem(BaseModel):
    timestamp: int
    text: str


class VideoInfo(BaseContent):
    code: str
    title: str
    description: str
    url: str
    thumbnail_url: Optional[str]
    transcript: Optional[List[TranscriptItem]]
    duration: float
    embed_code: str
    uploaded_date: str
    comments_turned_off: bool  # TODO: Not Implemented yet
    comments: List[Comment]
    related: Optional[List[RelatedVideo]]


class Short(BaseModel):
    code: str
    url: str
    views: int


class ShortMusic(BaseModel):
    name: str
    channel_name: str
    music_url: str
    channel_url: str
    used_in_shorts: List[Short]


class ShortEffect(BaseModel):
    name: str
    shorts_count: int


class ShortInfo(BaseContent):
    code: str
    url: str
    description: str
    secondary_description: Optional[str]  # TODO: Not Implemented yet
    music: Optional[ShortMusic]  # TODO: Not Implemented yet
    effect: Optional[ShortEffect]  # TODO: Not Implemented yet
    related_shorts: Optional[List[Short]]  # TODO: Not Implemented yet
    suggested_search_phrase: str  # TODO: Not Implemented yet
    link: Optional[Link]  # TODO: Not Implemented yet
    thumbnail_url: str
    posted_date: str
    pinned_comments: Optional[List[Comment]]
    comments: List[Comment]


class CommunityPostType(Enum):
    IMAGE = "Image"
    VIDEO = "Video"
    IMAGE_CAROUSEL = "Image Carousel"
    POLL = "Poll"
    OTHER = "Other"


class PollOption(BaseModel):
    description: str
    img_url: Optional[str]


class PollTypePost(BaseModel):
    votes_count: int
    options: List[PollOption]


class VideoTypePost(BaseModel):
    title: str
    url: str
    thumbnail_url: str
    channel_url: str
    channel_name: str
    is_channel_verified: bool
    code: str
    description: str
    views: int
    posted_date: str
    fetched_timestamp: str
    duration: int


class CommunityPost(BaseContent):
    code: str
    url: str
    description: Optional[str]
    post_type: CommunityPostType
    post_content: str | List[str] | PollTypePost | VideoTypePost | None
    comments: List[Comment]
    posted_date: str
