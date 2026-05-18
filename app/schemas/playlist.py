from datetime import datetime


from typing_extensions import Self


from pydantic import BaseModel, Field, model_validator

PlaylistTypeLiteral = Literal["main", "secondary"]


class PlaylistRequest(BaseModel):
    prompt: str = Field(min_length=5, max_length=2000)


class Timespan(BaseModel):
    start_year: int = Field(ge=1800, le=3000)
    end_year: int = Field(ge=1800, le=3000)

    @model_validator(mode="after")
    def end_not_before_start(self) -> Self:
        if self.end_year < self.start_year:
            raise ValueError("end_year must be >= start_year")
        return self


class SimilarSongsRequest(BaseModel):
    song_id: int = Field(ge=1)
    count: int = Field(ge=1, le=50, description="Number of similar songs to generate")
    linked_playlist_id: int = Field(ge=1, description="Main playlist id this similar playlist derives from")
    radius_km: int | None = Field(
        default=None,
        ge=1,
        le=20_000,
        description="Max distance from anchor city in km; omit to match anchor city and country only",
    )
    timespan: Timespan | None = Field(
        default=None,
        description="Release year range for similar songs; overrides anchor era when set",
    )


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
    city: str | None = None
    country: str | None = None
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
    type: PlaylistTypeLiteral
    linked_playlist_id: int | None
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
