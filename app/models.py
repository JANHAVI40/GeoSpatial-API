from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class FileRecord:
    id: str
    filename: str
    feature_count: int = 0
    crs: str | None = None
    status: str = "PROCESSING"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error: str | None = None
    features: list[dict[str, Any]] = field(default_factory=list)
