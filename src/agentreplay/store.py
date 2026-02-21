from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime
from .models import Run, Step


class Store(ABC):
    @abstractmethod
    def init(self) -> None: ...

    @abstractmethod
    def create_run(self, name: str, started_at: datetime, meta: Dict[str, Any]) -> str: ...

    @abstractmethod
    def end_run(self, run_id: str, ended_at: datetime) -> None: ...

    @abstractmethod
    def add_step(
        self,
        run_id: str,
        idx: int,
        kind: str,
        name: str,
        ts: datetime,
        input: Dict[str, Any],
        output: Dict[str, Any],
        error: Optional[Dict[str, Any]],
    ) -> str: ...

    @abstractmethod
    def get_run(self, run_id: str) -> Run: ...

    @abstractmethod
    def list_runs(self, limit: int = 50) -> List[Run]: ...

    @abstractmethod
    def list_steps(self, run_id: str) -> List[Step]: ...
