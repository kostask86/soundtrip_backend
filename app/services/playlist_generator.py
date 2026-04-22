from __future__ import annotations

import json
from pathlib import Path

import replicate
from fastapi import HTTPException, status

from app.core.config import settings
from app.schemas.playlist import PlaylistResponse

ONTOLOGY_PATH = Path(__file__).resolve().parents[2] / "scripts" / "ontology_data.json"
PROMPT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "scripts" / "playlist_prompt_config.json"


def _load_ontology_summary() -> dict:
    with ONTOLOGY_PATH.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    return {
        "styles": payload.get("styles", []),
        "emotion_values": payload.get("emotion_values", []),
        "time": payload.get("time", []),
        "geography": payload.get("geography", []),
        "influence_values": payload.get("influence_values", []),
        "example_song": payload.get("example_song", {}),
    }


def _build_prompt(user_prompt: str) -> str:
    ontology = _load_ontology_summary()
    with PROMPT_CONFIG_PATH.open("r", encoding="utf-8") as f:
        prompt_config = json.load(f)
    system_prompt = prompt_config.get("system_prompt", "")
    rules = prompt_config.get("rules", [])
    sections = prompt_config.get("sections", {})
    instructions = "\n".join([system_prompt, *rules]).strip()
    return (
        f"{instructions}\n"
        f"{sections.get('user_request', 'User request:')}\n{user_prompt}\n\n"
        f"{sections.get('ontology_json', 'Ontology JSON:')}\n"
        f"{json.dumps({k: v for k, v in ontology.items() if k != 'example_song'})}\n\n"
        f"{sections.get('example_song_structure', 'Example song structure:')}\n"
        f"{json.dumps(ontology['example_song'])}"
    )


def _extract_text_output(output: object) -> str:
    if isinstance(output, list):
        return "".join(str(chunk) for chunk in output)
    if isinstance(output, str):
        return output
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Replicate output was not text",
    )


def _parse_playlist_response(user_prompt: str, raw_text: str) -> PlaylistResponse:
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        start = raw_text.find("{")
        end = raw_text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="LLM did not return JSON")
        parsed = json.loads(raw_text[start : end + 1])

    if "songs" not in parsed:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="LLM JSON missing songs key")

    return PlaylistResponse(user_prompt=user_prompt, songs=parsed["songs"])


def generate_playlist(user_prompt: str) -> PlaylistResponse:
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

    llm_prompt = _build_prompt(user_prompt)
    # Use SDK default endpoint (no base_url override).
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
    return _parse_playlist_response(user_prompt=user_prompt, raw_text=raw_text)
