from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Iterator

from .store import Store
from .redact import redact_dict


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class RunHandle:
    id: str
    name: str
    meta: Dict[str, Any]


class Recorder:
    """
    Framework-agnostic recorder.
    You call recorder.llm(...) / recorder.tool(...) around your agent execution.
    """

    def __init__(self, store: Store, project: str = "default", redaction: bool = True):
        self.store = store
        self.project = project
        self.redaction = redaction
        self._active_run: Optional[RunHandle] = None
        self._idx: int = 0
        self.store.init()

    @contextmanager
    def run(self, name: str, meta: Optional[Dict[str, Any]] = None) -> Iterator[RunHandle]:
        if self._active_run is not None:
            raise RuntimeError("Nested runs not supported in v0.1")
        meta = meta or {}
        meta = {"project": self.project, **meta}

        run_id = self.store.create_run(name=name, started_at=_utcnow(), meta=meta)
        self._active_run = RunHandle(id=run_id, name=name, meta=meta)
        self._idx = 0
        try:
            yield self._active_run
        finally:
            self.store.end_run(run_id, ended_at=_utcnow())
            self._active_run = None
            self._idx = 0

    def _ensure_run(self) -> RunHandle:
        if self._active_run is None:
            raise RuntimeError("No active run. Use `with recorder.run(...):`")
        return self._active_run

    def span(self, name: str, input: Optional[Dict[str, Any]] = None, output: Optional[Dict[str, Any]] = None):
        self._record(kind="span", name=name, input=input or {}, output=output or {}, error=None)

    def llm(self, name: str, input: Dict[str, Any], output: Dict[str, Any], error: Optional[Dict[str, Any]] = None):
        self._record(kind="llm", name=name, input=input, output=output, error=error)

    def tool(self, name: str, input: Dict[str, Any], output: Dict[str, Any], error: Optional[Dict[str, Any]] = None):
        self._record(kind="tool", name=name, input=input, output=output, error=error)

    def _record(self, kind: str, name: str, input: Dict[str, Any], output: Dict[str, Any], error: Optional[Dict[str, Any]]):
        run = self._ensure_run()

        if self.redaction:
            input = redact_dict(input)
            output = redact_dict(output)
            if error is not None:
                error = redact_dict(error)

        idx = self._idx
        self._idx += 1

        self.store.add_step(
            run_id=run.id,
            idx=idx,
            kind=kind,
            name=name,
            ts=_utcnow(),
            input=input,
            output=output,
            error=error,
        )
