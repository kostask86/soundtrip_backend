from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Style(Base):
    __tablename__ = "styles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("styles.id"), nullable=True)

    parent: Mapped["Style | None"] = relationship("Style", remote_side=[id], backref="children")


class EmotionCategory(Base):
    __tablename__ = "emotion_categories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(255), nullable=False)


class Emotion(Base):
    __tablename__ = "emotions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("emotion_categories.id"), nullable=False)
    key: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(255), nullable=False)

    category: Mapped["EmotionCategory"] = relationship("EmotionCategory")


class TimePeriod(Base):
    __tablename__ = "time_periods"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class Geography(Base):
    __tablename__ = "geographies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class InfluenceCategory(Base):
    __tablename__ = "influence_categories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(255), nullable=False)


class Influence(Base):
    __tablename__ = "influences"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("influence_categories.id"), nullable=False)
    key: Mapped[str] = mapped_column(String(160), unique=True, nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(255), nullable=False)

    category: Mapped["InfluenceCategory"] = relationship("InfluenceCategory")


class Song(Base):
    __tablename__ = "songs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    artist: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    album: Mapped[str | None] = mapped_column(String(255), nullable=True)
    release_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    language: Mapped[str | None] = mapped_column(String(80), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    time_period_id: Mapped[int | None] = mapped_column(ForeignKey("time_periods.id"), nullable=True)
    primary_geography_id: Mapped[int | None] = mapped_column(ForeignKey("geographies.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SongStyle(Base):
    __tablename__ = "song_styles"
    __table_args__ = (UniqueConstraint("song_id", "style_id", name="uq_song_style"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    song_id: Mapped[int] = mapped_column(ForeignKey("songs.id"), nullable=False, index=True)
    style_id: Mapped[int] = mapped_column(ForeignKey("styles.id"), nullable=False, index=True)
    role: Mapped[str | None] = mapped_column(String(32), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)


class SongEmotion(Base):
    __tablename__ = "song_emotions"
    __table_args__ = (UniqueConstraint("song_id", "emotion_id", name="uq_song_emotion"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    song_id: Mapped[int] = mapped_column(ForeignKey("songs.id"), nullable=False, index=True)
    emotion_id: Mapped[int] = mapped_column(ForeignKey("emotions.id"), nullable=False, index=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)


class SongInfluence(Base):
    __tablename__ = "song_influences"
    __table_args__ = (UniqueConstraint("song_id", "influence_id", name="uq_song_influence"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    song_id: Mapped[int] = mapped_column(ForeignKey("songs.id"), nullable=False, index=True)
    influence_id: Mapped[int] = mapped_column(ForeignKey("influences.id"), nullable=False, index=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)


class SongSecondaryGeography(Base):
    __tablename__ = "song_secondary_geographies"
    __table_args__ = (UniqueConstraint("song_id", "geography_id", name="uq_song_secondary_geography"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    song_id: Mapped[int] = mapped_column(ForeignKey("songs.id"), nullable=False, index=True)
    geography_id: Mapped[int] = mapped_column(ForeignKey("geographies.id"), nullable=False, index=True)
