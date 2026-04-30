from datetime import datetime

from pydantic import BaseModel, Field


class PlaylistRequest(BaseModel):
    prompt: str = Field(min_length=5, max_length=2000)


class PlaylistStyle(BaseModel):
    id: str
    label: str
    level: int
    role: str
    confidence: float


class PlaylistEmotion(BaseModel):
    parent_id: str
    parent_label: str
    id: str
    label: str
    confidence: float


class PlaylistTime(BaseModel):
    id: str
    label: str


class PlaylistGeographyItem(BaseModel):
    id: str
    label: str


class PlaylistGeography(BaseModel):
    primary: PlaylistGeographyItem
    secondary: list[PlaylistGeographyItem]


class PlaylistInfluence(BaseModel):
    parent_id: str
    parent_label: str
    id: str
    label: str
    confidence: float


class PlaylistSong(BaseModel):
    song_id: int | None = None
    position: int | None = None
    title: str
    artist: str
    album: str | None = None
    album_cover_url: str | None = None
    release_year: int | None = None
    duration_seconds: int | None = None
    language: str | None = None
    lyrics_text: str | None = None
    notes: str | None = None
    time_period_id: int | None = None
    primary_geography_id: int | None = None
    created_at: datetime | None = None
    styles: list[PlaylistStyle]
    emotions: list[PlaylistEmotion]
    time: PlaylistTime
    geography: PlaylistGeography
    influences: list[PlaylistInfluence]


class PlaylistResponse(BaseModel):
    user_prompt: str
    songs: list[PlaylistSong]


class PlaylistCreate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    user_prompt: str = Field(min_length=5, max_length=2000)
    llm_prompt: str | None = None
    songs: list[PlaylistSong]


class PlaylistUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    user_prompt: str = Field(min_length=5, max_length=2000)
    llm_prompt: str | None = None
    songs: list[PlaylistSong]


class PlaylistStoredRead(BaseModel):
    id: int
    title: str | None
    user_prompt: str
    llm_prompt: str | None
    songs: list[PlaylistSong]
    created_at: datetime
    updated_at: datetime


class PlaylistGenerationJobResponse(BaseModel):
    job_id: str
    status: str


class PlaylistJobStatusResponse(BaseModel):
    job_id: str
    status: str
    playlist_id: int | None = None
    playlist: PlaylistStoredRead | None = None
    error: str | None = None
