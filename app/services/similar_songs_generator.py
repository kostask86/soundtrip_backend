"""Build prompts and call Replicate for similar-song playlists anchored by city, country, radius, and time."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import replicate
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.tables import Emotion, EmotionCategory, Song, SongEmotion, SongStyle, Style, TimePeriod
from app.schemas.playlist import PlaylistResponse, Timespan
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
    has_linked_era = False
    if song.time_period_id is not None:
        tp = db.get(TimePeriod, song.time_period_id)
        if tp is not None:
            time_id = tp.key
            time_label = tp.label
            has_linked_era = True

    return {
        "title": song.title,
        "artist": song.artist,
        "city": city,
        "country": (song.country or "").strip() or "unknown",
        "release_year": song.release_year,
        "has_linked_era": has_linked_era,
        "styles_text": "; ".join(style_parts) if style_parts else "(none linked — infer closest ontology styles)",
        "emotions_text": "; ".join(emotion_parts) if emotion_parts else "(none linked — infer closest ontology emotions)",
        "time_id": time_id or "(none linked — infer closest era from artist)",
        "time_label": time_label or "(none)",
    }


def resolve_time_constraint(anchor: dict, timespan: Timespan | None) -> dict[str, Any]:
    if timespan is not None:
        return {
            "mode": "range",
            "start_year": timespan.start_year,
            "end_year": timespan.end_year,
            "summary": f"{timespan.start_year}–{timespan.end_year}",
        }
    if anchor["has_linked_era"]:
        return {
            "mode": "era",
            "time_id": anchor["time_id"],
            "time_label": anchor["time_label"],
            "summary": f"era {anchor['time_label']}",
        }
    if anchor["release_year"] is not None:
        return {
            "mode": "release_year",
            "release_year": anchor["release_year"],
            "summary": str(anchor["release_year"]),
        }
    return {"mode": "none", "summary": ""}


def _append_time_rules(rules: list[str], prompt_config: dict, time_constraint: dict[str, Any]) -> None:
    mode = time_constraint["mode"]
    if mode == "range":
        template_rules = prompt_config.get("timespan_rules", [])
        vars_ = {
            "start_year": time_constraint["start_year"],
            "end_year": time_constraint["end_year"],
        }
    elif mode == "era":
        template_rules = prompt_config.get("era_rules", [])
        vars_ = {"time_id": time_constraint["time_id"], "time_label": time_constraint["time_label"]}
    elif mode == "release_year":
        template_rules = prompt_config.get("release_year_rules", [])
        vars_ = {"release_year": time_constraint["release_year"]}
    else:
        template_rules = prompt_config.get("no_time_rules", [])
        vars_ = {}
    for rule in template_rules:
        rules.append(rule.format(**vars_) if vars_ else rule)


def _build_time_constraint_block(time_constraint: dict[str, Any]) -> str:
    mode = time_constraint["mode"]
    if mode == "range":
        return (
            f"Only include songs with release_year from {time_constraint['start_year']} "
            f"through {time_constraint['end_year']} inclusive. "
            "Do not use the anchor song's linked era for filtering."
        )
    if mode == "era":
        return (
            f"Match songs to anchor era {time_constraint['time_label']} "
            f"(ontology time id: {time_constraint['time_id']})."
        )
    if mode == "release_year":
        return f"Only include songs with release_year equal to {time_constraint['release_year']}."
    return "No fixed year range; infer closest valid ontology era per artist when needed."


def _geography_task_line(anchor: dict, radius_km: int | None) -> str:
    place = f"{anchor['city']}, {anchor['country']}"
    if radius_km is not None:
        return (
            f"with artists or acts plausibly based within {radius_km} km of {place}"
        )
    return f"with artists or acts strongly associated with {place} (same city and country as the anchor)"


def build_similar_songs_llm_prompt(
    anchor: dict,
    count: int,
    radius_km: int | None,
    timespan: Timespan | None,
) -> str:
    with SIMILAR_PROMPT_CONFIG_PATH.open("r", encoding="utf-8") as f:
        prompt_config = json.load(f)
    ontology = _load_ontology_summary()
    time_constraint = resolve_time_constraint(anchor, timespan)

    system_prompt = prompt_config.get("system_prompt", "")
    rules = list(prompt_config.get("rules", []))

    geo_vars = {"anchor_city": anchor["city"], "anchor_country": anchor["country"]}
    if radius_km is not None:
        radius_vars = {
            **geo_vars,
            "radius_km": radius_km,
            "radius_scope_hint": geography_scope_hint(radius_km),
        }
        for rule in prompt_config.get("radius_rules", []):
            rules.append(rule.format(**radius_vars))
    else:
        for rule in prompt_config.get("city_country_rules", []):
            rules.append(rule.format(**geo_vars))

    _append_time_rules(rules, prompt_config, time_constraint)

    sections = prompt_config.get("sections", {})
    instructions = "\n".join([system_prompt, *rules]).strip()

    match_clause = "matching the anchor's styles and emotions"
    if time_constraint["mode"] != "range":
        match_clause += " and time constraint below"

    location_line = (
        f"Anchor location: {anchor['city']}, {anchor['country']} (search radius: {radius_km} km).\n"
        if radius_km is not None
        else f"Anchor location: {anchor['city']}, {anchor['country']} (same city and country).\n"
    )

    task_body = (
        f"Suggest exactly {count} songs that feel similar to the anchor, {_geography_task_line(anchor, radius_km)}, "
        f"{match_clause}.\n"
        f"Anchor track: \"{anchor['title']}\" by {anchor['artist']}.\n"
        f"{location_line}"
        f"Styles (from database): {anchor['styles_text']}\n"
        f"Emotions (from database): {anchor['emotions_text']}"
    )
    if time_constraint["mode"] == "era":
        task_body += f"\nEra (from database): {anchor['time_label']} (time id: {anchor['time_id']})."

    anchor_lines = [
        f"title={anchor['title']}",
        f"artist={anchor['artist']}",
        f"city={anchor['city']}",
        f"country={anchor['country']}",
        f"styles={anchor['styles_text']}",
        f"emotions={anchor['emotions_text']}",
    ]
    if radius_km is not None:
        anchor_lines.append(f"radius_km={radius_km}")
    if time_constraint["mode"] == "era":
        anchor_lines.append(f"era_label={anchor['time_label']}")
        anchor_lines.append(f"era_id={anchor['time_id']}")
    elif time_constraint["mode"] == "release_year":
        anchor_lines.append(f"release_year={anchor['release_year']}")
    elif time_constraint["mode"] == "range":
        anchor_lines.append("anchor_era=ignored (see time constraint)")

    anchor_block = "\n".join(anchor_lines)
    time_block = _build_time_constraint_block(time_constraint)

    return (
        f"{instructions}\n"
        f"{sections.get('task', 'Task:')}\n{task_body}\n\n"
        f"{sections.get('time_constraint', 'Time constraint:')}\n{time_block}\n\n"
        f"{sections.get('anchor', 'Anchor:')}\n{anchor_block}\n\n"
        f"{sections.get('ontology_json', 'Ontology JSON:')}\n"
        f"{json.dumps({k: v for k, v in ontology.items() if k != 'example_song'})}\n\n"
        f"{sections.get('example_song_structure', 'Example song structure:')}\n"
        f"{json.dumps(ontology['example_song'])}"
    )


def short_user_prompt_summary(
    anchor: dict,
    count: int,
    radius_km: int | None,
    timespan: Timespan | None,
) -> str:
    ctry = anchor["country"] if anchor["country"] != "unknown" else ""
    place = f"{anchor['city']}, {ctry}".strip().rstrip(",") if ctry else anchor["city"]
    time_constraint = resolve_time_constraint(anchor, timespan)

    if radius_km is not None:
        base = (
            f"{count} songs similar to \"{anchor['title']}\" by {anchor['artist']} "
            f"within {radius_km} km of {place}"
        )
    else:
        base = f"{count} songs similar to \"{anchor['title']}\" by {anchor['artist']} in {place}"

    if time_constraint["summary"]:
        return f"{base}, {time_constraint['summary']}"
    return base


def generate_similar_songs(
    db: Session,
    song_id: int,
    count: int,
    radius_km: int | None = None,
    timespan: Timespan | None = None,
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
    llm_prompt = build_similar_songs_llm_prompt(anchor, count, radius_km, timespan)
    user_summary = short_user_prompt_summary(anchor, count, radius_km, timespan)

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
