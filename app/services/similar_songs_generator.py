"""Build prompts and call Replicate for similar-song playlists anchored by city, country, and radius."""

from __future__ import annotations

import json
from pathlib import Path

import replicate
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.tables import Emotion, EmotionCategory, Song, SongEmotion, SongStyle, Style, TimePeriod
from app.schemas.playlist import PlaylistResponse
from app.services.playlist_generator import (
    _extract_text_output,
    _load_ontology_summary,
    _parse_playlist_response,
)

SIMILAR_PROMPT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "scripts" / "similar_songs_prompt_config.json"


def geography_scope_hint(radius_km: int) -> str:
    if radius_km <= 30:
        return (
            "Strongly prefer the anchor city; include only other cities or districts that clearly lie within the radius."
        )
    if radius_km <= 150:
        return (
            "Prefer the anchor city and its metro area; include other nearby cities in the same country when they fall within the radius."
        )
    if radius_km <= 800:
        return (
            "Include any cities within the radius in the same country and neighboring regions; the anchor city need not dominate the list."
        )
    return (
        "Include any cities and countries whose major population centers fall within the radius; cross-border matches are expected when the radius is large enough."
    )


def load_anchor_context(db: Session, song_id: int) -> dict:
    """Load anchor song row plus styles, emotions, and time period from relational tables."""
    song = db.get(Song, song_id)
    if song is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Song not found")
    city = (song.city or "").strip()
    if not city:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Song has no city; cannot anchor similar-by-city.",
        )

    style_parts: list[str] = []
    for row in db.execute(
        select(SongStyle, Style).join(Style, SongStyle.style_id == Style.id).where(SongStyle.song_id == song_id)
    ).all():
        ss, st = row[0], row[1]
        style_parts.append(f"{st.key} ({st.label}) role={ss.role or 'n/a'} confidence={ss.confidence}")

    emotion_parts: list[str] = []
    for row in db.execute(
        select(SongEmotion, Emotion, EmotionCategory)
        .join(Emotion, SongEmotion.emotion_id == Emotion.id)
        .join(EmotionCategory, Emotion.category_id == EmotionCategory.id)
        .where(SongEmotion.song_id == song_id)
    ).all():
        se, em, cat = row[0], row[1], row[2]
        emotion_parts.append(
            f"{em.key} ({em.label}) parent={cat.key} ({cat.label}) confidence={se.confidence}"
        )

    time_id = ""
    time_label = ""
    if song.time_period_id is not None:
        tp = db.get(TimePeriod, song.time_period_id)
        if tp is not None:
            time_id = tp.key
            time_label = tp.label

    return {
        "title": song.title,
        "artist": song.artist,
        "city": city,
        "country": (song.country or "").strip() or "unknown",
        "styles_text": "; ".join(style_parts) if style_parts else "(none linked — infer closest ontology styles)",
        "emotions_text": "; ".join(emotion_parts) if emotion_parts else "(none linked — infer closest ontology emotions)",
        "time_id": time_id or "(none linked — infer closest era from artist)",
        "time_label": time_label or "(none)",
    }


def build_similar_songs_llm_prompt(anchor: dict, count: int, radius_km: int) -> str:
    with SIMILAR_PROMPT_CONFIG_PATH.open("r", encoding="utf-8") as f:
        prompt_config = json.load(f)
    ontology = _load_ontology_summary()
    system_prompt = prompt_config.get("system_prompt", "")
    rules = list(prompt_config.get("rules", []))
    radius_template_vars = {
        "radius_km": radius_km,
        "anchor_city": anchor["city"],
        "anchor_country": anchor["country"],
        "radius_scope_hint": geography_scope_hint(radius_km),
    }
    for rule in prompt_config.get("radius_rules", []):
        rules.append(rule.format(**radius_template_vars))
    sections = prompt_config.get("sections", {})
    instructions = "\n".join([system_prompt, *rules]).strip()

    task_body = (
        f"Suggest exactly {count} songs that feel similar to the anchor, with artists or acts plausibly based "
        f"within {radius_km} km of {anchor['city']}, {anchor['country']}, matching the anchor's styles, emotions, "
        f"and era as described below.\n"
        f"Anchor track: \"{anchor['title']}\" by {anchor['artist']}.\n"
        f"Anchor location: {anchor['city']}, {anchor['country']} (search radius: {radius_km} km).\n"
        f"Styles (from database): {anchor['styles_text']}\n"
        f"Emotions (from database): {anchor['emotions_text']}\n"
        f"Era: {anchor['time_label']} (time id: {anchor['time_id']})."
    )

    anchor_block = (
        f"title={anchor['title']}\nartist={anchor['artist']}\ncity={anchor['city']}\ncountry={anchor['country']}\n"
        f"radius_km={radius_km}\n"
        f"styles={anchor['styles_text']}\nemotions={anchor['emotions_text']}\n"
        f"era_label={anchor['time_label']}\nera_id={anchor['time_id']}"
    )

    return (
        f"{instructions}\n"
        f"{sections.get('task', 'Task:')}\n{task_body}\n\n"
        f"{sections.get('anchor', 'Anchor:')}\n{anchor_block}\n\n"
        f"{sections.get('ontology_json', 'Ontology JSON:')}\n"
        f"{json.dumps({k: v for k, v in ontology.items() if k != 'example_song'})}\n\n"
        f"{sections.get('example_song_structure', 'Example song structure:')}\n"
        f"{json.dumps(ontology['example_song'])}"
    )


def short_user_prompt_summary(anchor: dict, count: int, radius_km: int) -> str:
    ctry = anchor["country"] if anchor["country"] != "unknown" else ""
    place = f"{anchor['city']}, {ctry}".strip().rstrip(",") if ctry else anchor["city"]
    return (
        f"{count} songs similar to \"{anchor['title']}\" by {anchor['artist']} "
        f"within {radius_km} km of {place}"
    )


def generate_similar_songs(
    db: Session, song_id: int, count: int, radius_km: int
) -> tuple[PlaylistResponse, str]:
    """Load anchor, build prompt, run Replicate, parse playlist JSON."""
    if not settings.replicate_api_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="REPLICATE_API_TOKEN is not configured",
        )
    if not settings.replicate_model:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="REPLICATE_MODEL is not configured",
        )

    anchor = load_anchor_context(db, song_id)
    llm_prompt = build_similar_songs_llm_prompt(anchor, count, radius_km)
    user_summary = short_user_prompt_summary(anchor, count, radius_km)

    client = replicate.Client(api_token=settings.replicate_api_token)
    try:
        output = client.run(
            settings.replicate_model,
            input={"prompt": llm_prompt},
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Replicate API error: {exc}",
        ) from None

    raw_text = _extract_text_output(output)
    return _parse_playlist_response(user_prompt=user_summary, raw_text=raw_text), llm_prompt
