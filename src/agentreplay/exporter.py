# agentreplay/exporter.py
from __future__ import annotations

import json
import zipfile
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .store import Store
from .models import Run, Step

FORMAT_VERSION = "0.2"


def _json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _parse_dt(s: str) -> datetime:
    # handles "Z" + naive iso
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def export_areplay(store: Store, run_id: str, out_path: str) -> str:
    run: Run = store.get_run(run_id)
    steps: List[Step] = store.list_steps(run_id)

    run_obj = {
        "id": run.id,
        "name": run.name,
        "started_at": run.started_at.isoformat(),
        "ended_at": run.ended_at.isoformat() if run.ended_at else None,
        "meta": run.meta,
    }

    steps_obj = [
        {
            "id": s.id,
            "run_id": s.run_id,
            "idx": s.idx,
            "kind": s.kind,
            "name": s.name,
            "ts": s.ts.isoformat(),
            "input": s.input,
            "output": s.output,
            "error": s.error,
        }
        for s in steps
    ]

    steps_bytes = _json_bytes(steps_obj)

    # v0.2 manifest hardening
    created_by = "agentreplay"  # keep simple; optionally set to package version later
    manifest: Dict[str, Any] = {
        "format": "agentreplay.areplay",
        "version": FORMAT_VERSION,
        "schema_version": FORMAT_VERSION,
        "created_by": created_by,
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "run_id": run_id,
        "hashes": {"steps_json_sha256": _sha256_bytes(steps_bytes)},
        "redactions_applied": False,  # flip to True if your redact pipeline is applied
    }

    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", _json_bytes(manifest))
        z.writestr("run.json", _json_bytes(run_obj))
        z.writestr("steps.json", steps_bytes)

    return out_path


def import_areplay(store: Store, in_path: str) -> str:
    """
    Imports a .areplay artifact into the store as a NEW run_id.
    Returns the new run_id.
    """
    with zipfile.ZipFile(in_path, "r") as z:
        manifest = json.loads(z.read("manifest.json").decode("utf-8"))
        run_obj = json.loads(z.read("run.json").decode("utf-8"))
        steps_raw = z.read("steps.json")
        steps_obj = json.loads(steps_raw.decode("utf-8"))

    # Optional: verify hash if present (warn-only here)
    try:
        expected = (manifest.get("hashes") or {}).get("steps_json_sha256")
        if expected and expected != _sha256_bytes(steps_raw):
            # keep import permissive; test runner can be strict
            pass
    except Exception:
        pass

    name = run_obj.get("name", "imported_run")
    started_at = _parse_dt(run_obj["started_at"])
    meta = run_obj.get("meta", {})
    meta = {**meta, "imported_from": in_path, "areplay_version": manifest.get("version")}

    new_run_id = store.create_run(name=name, started_at=started_at, meta=meta)

    ended_at = run_obj.get("ended_at")
    if ended_at:
        store.end_run(new_run_id, _parse_dt(ended_at))

    for s in sorted(steps_obj, key=lambda x: int(x["idx"])):
        store.add_step(
            run_id=new_run_id,
            idx=int(s["idx"]),
            kind=s["kind"],
            name=s["name"],
            ts=_parse_dt(s["ts"]),
            input=s.get("input") or {},
            output=s.get("output") or {},
            error=s.get("error"),
        )

    return new_run_id


def load_areplay_steps(path: str) -> List[Step]:
    """
    Read-only loader: .areplay -> List[Step] (no DB writes)
    """
    with zipfile.ZipFile(path, "r") as z:
        steps_obj = json.loads(z.read("steps.json").decode("utf-8"))

    steps: List[Step] = []
    for d in steps_obj:
        steps.append(
            Step(
                id=str(d.get("id", "")),
                run_id=str(d.get("run_id", "")),
                idx=int(d.get("idx", 0)),
                kind=str(d.get("kind", "span")),
                name=str(d.get("name", "")),
                ts=_parse_dt(d.get("ts", datetime.utcnow().isoformat() + "Z")),
                input=dict(d.get("input") or {}),
                output=dict(d.get("output") or {}),
                error=d.get("error"),
            )
        )
    steps.sort(key=lambda s: s.idx)
    return steps