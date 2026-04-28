from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SongCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    artist: str = Field(min_length=1, max_length=255)
    album: str | None = Field(default=None, max_length=255)
    mb_recording_mbid: str | None = Field(default=None, max_length=64)
    mb_release_mbid: str | None = Field(default=None, max_length=64)
    mb_release_group_mbid: str | None = Field(default=None, max_length=64)
    album_cover_url: str | None = None
    release_year: int | None = Field(default=None, ge=0, le=3000)
    duration_seconds: int | None = Field(default=None, ge=0)
    language: str | None = Field(default=None, max_length=80)
    lyrics_text: str | None = None
    lyrics_language: str | None = Field(default=None, max_length=80)
    notes: str | None = None
    time_period_id: int | None = None
    primary_geography_id: int | None = None


class SongUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    artist: str = Field(min_length=1, max_length=255)
    album: str | None = Field(default=None, max_length=255)
    mb_recording_mbid: str | None = Field(default=None, max_length=64)
    mb_release_mbid: str | None = Field(default=None, max_length=64)
    mb_release_group_mbid: str | None = Field(default=None, max_length=64)
    album_cover_url: str | None = None
    release_year: int | None = Field(default=None, ge=0, le=3000)
    duration_seconds: int | None = Field(default=None, ge=0)
    language: str | None = Field(default=None, max_length=80)
    lyrics_text: str | None = None
    lyrics_language: str | None = Field(default=None, max_length=80)
    notes: str | None = None
    time_period_id: int | None = None
    primary_geography_id: int | None = None


class SongRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    artist: str
    album: str | None
    mb_recording_mbid: str | None
    mb_release_mbid: str | None
    mb_release_group_mbid: str | None
    album_cover_url: str | None
    release_year: int | None
    duration_seconds: int | None
    language: str | None
    lyrics_text: str | None
    lyrics_language: str | None
    notes: str | None
    time_period_id: int | None
    primary_geography_id: int | None
    created_at: datetime


class SongMetadataCandidate(BaseModel):
    recording_mbid: str
    recording_title: str
    artist_name: str
    score: int
    release_mbid: str | None = None
    release_title: str | None = None
    release_date: str | None = None
    release_group_mbid: str | None = None
    release_group_title: str | None = None
    cover_url_preview: str | None = None


class SongMetadataSearchResponse(BaseModel):
    song_id: int
    query: str
    candidates: list[SongMetadataCandidate]


class SongMetadataApplyRequest(BaseModel):
    auto: bool = True
    overwrite: bool = True
    recording_mbid: str | None = None
    release_mbid: str | None = None
    release_group_mbid: str | None = None
    min_score: int = Field(default=60, ge=0, le=100)
