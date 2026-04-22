from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SongCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    artist: str = Field(min_length=1, max_length=255)
    album: str | None = Field(default=None, max_length=255)
    release_year: int | None = Field(default=None, ge=0, le=3000)
    duration_seconds: int | None = Field(default=None, ge=0)
    language: str | None = Field(default=None, max_length=80)
    notes: str | None = None
    time_period_id: int | None = None
    primary_geography_id: int | None = None


class SongUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    artist: str = Field(min_length=1, max_length=255)
    album: str | None = Field(default=None, max_length=255)
    release_year: int | None = Field(default=None, ge=0, le=3000)
    duration_seconds: int | None = Field(default=None, ge=0)
    language: str | None = Field(default=None, max_length=80)
    notes: str | None = None
    time_period_id: int | None = None
    primary_geography_id: int | None = None


class SongRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    artist: str
    album: str | None
    release_year: int | None
    duration_seconds: int | None
    language: str | None
    notes: str | None
    time_period_id: int | None
    primary_geography_id: int | None
    created_at: datetime
