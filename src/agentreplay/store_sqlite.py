from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .models import Run, Step
from .store import Store


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _to_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _from_iso(s: str) -> datetime:
    # Python 3.9 compatible parse for isoformat with timezone
    return datetime.fromisoformat(s)


class SQLiteStore(Store):
    def __init__(self, path: str = "agentreplay.db") -> None:
        self.path = path

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def init(self) -> None:
        with self._conn() as c:
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                  id TEXT PRIMARY KEY,
                  name TEXT NOT NULL,
                  started_at TEXT NOT NULL,
                  ended_at TEXT NULL,
                  meta_json TEXT NOT NULL
                );
                """
            )
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS steps (
                  id TEXT PRIMARY KEY,
                  run_id TEXT NOT NULL,
                  idx INTEGER NOT NULL,
                  kind TEXT NOT NULL,
                  name TEXT NOT NULL,
                  ts TEXT NOT NULL,
                  input_json TEXT NOT NULL,
                  output_json TEXT NOT NULL,
                  error_json TEXT NULL,
                  FOREIGN KEY(run_id) REFERENCES runs(id)
                );
                """
            )
            c.execute("CREATE INDEX IF NOT EXISTS idx_steps_run ON steps(run_id, idx);")

    def create_run(self, name: str, started_at: datetime, meta: Dict[str, Any]) -> str:
        run_id = str(uuid.uuid4())
        with self._conn() as c:
            c.execute(
                "INSERT INTO runs(id, name, started_at, ended_at, meta_json) VALUES(?,?,?,?,?)",
                (run_id, name, _to_iso(started_at), None, json.dumps(meta or {})),
            )
        return run_id

    def end_run(self, run_id: str, ended_at: datetime) -> None:
        with self._conn() as c:
            c.execute("UPDATE runs SET ended_at=? WHERE id=?", (_to_iso(ended_at), run_id))

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
    ) -> str:
        step_id = str(uuid.uuid4())
        with self._conn() as c:
            c.execute(
                """
                INSERT INTO steps(
                  id, run_id, idx, kind, name, ts, input_json, output_json, error_json
                ) VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (
                    step_id,
                    run_id,
                    idx,
                    kind,
                    name,
                    _to_iso(ts),
                    json.dumps(input or {}),
                    json.dumps(output or {}),
                    None if error is None else json.dumps(error),
                ),
            )
        return step_id

    def get_run(self, run_id: str) -> Run:
        with self._conn() as c:
            row = c.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
            if not row:
                raise KeyError(f"Run not found: {run_id}")
            return Run(
                id=row["id"],
                name=row["name"],
                started_at=_from_iso(row["started_at"]),
                ended_at=_from_iso(row["ended_at"]) if row["ended_at"] else None,
                meta=json.loads(row["meta_json"] or "{}"),
            )

    def list_runs(self, limit: int = 50) -> List[Run]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM runs ORDER BY started_at DESC LIMIT ?", (int(limit),)
            ).fetchall()
            return [
                Run(
                    id=r["id"],
                    name=r["name"],
                    started_at=_from_iso(r["started_at"]),
                    ended_at=_from_iso(r["ended_at"]) if r["ended_at"] else None,
                    meta=json.loads(r["meta_json"] or "{}"),
                )
                for r in rows
            ]

    def list_steps(self, run_id: str) -> List[Step]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM steps WHERE run_id=? ORDER BY idx ASC", (run_id,)
            ).fetchall()
            return [
                Step(
                    id=r["id"],
                    run_id=r["run_id"],
                    idx=int(r["idx"]),
                    kind=r["kind"],
                    name=r["name"],
                    ts=_from_iso(r["ts"]),
                    input=json.loads(r["input_json"] or "{}"),
                    output=json.loads(r["output_json"] or "{}"),
                    error=json.loads(r["error_json"]) if r["error_json"] else None,
                )
                for r in rows
            ]
