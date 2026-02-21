from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Literal, List
from datetime import datetime

StepKind = Literal["llm", "tool", "span"]


@dataclass(frozen=True)
class Run:
    id: str
    name: str
    started_at: datetime
    ended_at: Optional[datetime]
    meta: Dict[str, Any]


@dataclass(frozen=True)
class Step:
    id: str
    run_id: str
    idx: int
    kind: StepKind
    name: str
    ts: datetime
    input: Dict[str, Any]
    output: Dict[str, Any]
    error: Optional[Dict[str, Any]]


@dataclass(frozen=True)
class ReplayReport:
    run_id: str
    ok: bool
    steps_replayed: int
    notes: List[str]
