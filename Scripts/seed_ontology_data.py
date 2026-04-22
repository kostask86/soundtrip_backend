"""Seed ontology reference tables from Scripts/ontology_data.json.

Seeds:
- styles
- geographies
- time periods
- emotion categories + emotions
- influence categories + influences

Does not seed example songs.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import delete, select
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import Session

from app.core.database import engine
from app.models.tables import (
    Emotion,
    EmotionCategory,
    Geography,
    Influence,
    InfluenceCategory,
    Style,
    TimePeriod,
)


def _load_info_payload() -> dict:
    with (ROOT_DIR / "Scripts" / "ontology_data.json").open("r", encoding="utf-8") as f:
        return json.load(f)


def _upsert_by_key(session: Session, model: type, key: str, values: dict):
    row = session.scalar(select(model).where(model.key == key))
    if row is None:
        row = model(key=key, **values)
        session.add(row)
    else:
        for field, value in values.items():
            setattr(row, field, value)
    session.flush()
    return row


def seed_ontology_data(bind: Engine | Connection) -> None:
    payload = _load_info_payload()
    session = Session(bind=bind)
    try:
        for item in payload.get("time", []):
            _upsert_by_key(
                session,
                TimePeriod,
                item["id"],
                {"label": item["label"], "description": item.get("description")},
            )

        for item in payload.get("geography", []):
            _upsert_by_key(
                session,
                Geography,
                item["id"],
                {"label": item["label"], "description": item.get("description")},
            )

        emotion_categories: dict[str, EmotionCategory] = {}
        for category in payload.get("emotion_values", []):
            category_row = _upsert_by_key(
                session,
                EmotionCategory,
                category["id"],
                {"label": category["label"]},
            )
            emotion_categories[category["id"]] = category_row
            for child in category.get("children", []):
                _upsert_by_key(
                    session,
                    Emotion,
                    child["id"],
                    {"label": child["label"], "category_id": category_row.id},
                )

        influence_categories: dict[str, InfluenceCategory] = {}
        for category in payload.get("influence_values", []):
            category_row = _upsert_by_key(
                session,
                InfluenceCategory,
                category["id"],
                {"label": category["label"]},
            )
            influence_categories[category["id"]] = category_row
            for child in category.get("children", []):
                _upsert_by_key(
                    session,
                    Influence,
                    child["id"],
                    {"label": child["label"], "category_id": category_row.id},
                )

        created_styles: dict[str, Style] = {}
        for parent in payload.get("styles", []):
            parent_row = _upsert_by_key(
                session,
                Style,
                parent["id"],
                {
                    "label": parent["label"],
                    "level": parent.get("level", 1),
                    "parent_id": None,
                },
            )
            created_styles[parent["id"]] = parent_row

        for parent in payload.get("styles", []):
            parent_row = created_styles[parent["id"]]
            for child in parent.get("children", []):
                existing = session.scalar(select(Style).where(Style.key == child["id"]))
                if existing is None:
                    existing = Style(
                        key=child["id"],
                        label=child["label"],
                        level=child.get("level", 2),
                        parent_id=parent_row.id,
                    )
                    session.add(existing)
                    session.flush()
                else:
                    existing.label = child["label"]
                    existing.level = child.get("level", existing.level)
                    if existing.parent_id is None:
                        existing.parent_id = parent_row.id

        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def clear_ontology_data(bind: Engine | Connection) -> None:
    session = Session(bind=bind)
    try:
        session.execute(delete(Influence))
        session.execute(delete(InfluenceCategory))
        session.execute(delete(Emotion))
        session.execute(delete(EmotionCategory))
        session.execute(delete(Style))
        session.execute(delete(Geography))
        session.execute(delete(TimePeriod))
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def main() -> None:
    seed_ontology_data(bind=engine)
    print("Ontology data seeded from Scripts/ontology_data.json (example_song ignored).")


if __name__ == "__main__":
    main()
