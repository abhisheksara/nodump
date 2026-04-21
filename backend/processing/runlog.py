import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


class RunLogger:
    def __init__(self):
        self._entries: list[dict] = []

    def record(self, item: dict, action: str, **extra) -> None:
        self._entries.append({
            "ts": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "triage_label": item.get("triage_label"),
            "relevance_label": item.get("relevance_label"),
            "relevance_score": item.get("relevance_score"),
            "sub_domain": item.get("sub_domain"),
            **extra,
        })

    def save(self, runs_dir: str) -> Path:
        path = Path(runs_dir)
        path.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M")
        filepath = path / f"{ts}.jsonl"
        with filepath.open("w") as f:
            for entry in self._entries:
                f.write(json.dumps(entry, default=str) + "\n")
        logger.info("Run log: %s (%d entries)", filepath, len(self._entries))
        return filepath
