"""RegWatch: PFAS regulatory/industry digest feed (spec §8).

Snapshot mode only — the bundled JSON is the whole deliverable for Day 3.
Live RSS fetch is an explicit Day 5 stretch goal in the spec and is not
implemented here; do not let its absence block anything else.
"""

from __future__ import annotations

import json
import logging

import pandas as pd

from app.config import settings
from app.models import FeedResponse, RegWatchItem

logger = logging.getLogger("reportforge.regwatch")


def load_snapshot_feed() -> FeedResponse:
    if not settings.regwatch_snapshot_path.exists():
        logger.error("RegWatch snapshot not found at %s", settings.regwatch_snapshot_path)
        raise FileNotFoundError(f"RegWatch snapshot not found at {settings.regwatch_snapshot_path}")

    raw_items = json.loads(settings.regwatch_snapshot_path.read_text())
    items = [RegWatchItem.model_validate(item) for item in raw_items]
    items.sort(key=lambda item: item.published_at, reverse=True)

    return FeedResponse(source="snapshot", generated_at=pd.Timestamp.now("UTC").to_pydatetime(), items=items)
