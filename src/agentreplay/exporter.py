from __future__ import annotations

import json
import zipfile
from datetime import datetime
from typing import Any, Dict, List

from .store import Store
from .models import Run, Step


FORMAT_VERSION = "0.2"


def _json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")


def export_areplay(store: Store, run_id: str, out_path: str) -> str:
    run: Run = store.get_run(run_id)
    steps: List[Step] = store.list_steps(run_id)

    manifest: Dict[str, Any] = {
        "format": "agentreplay.areplay",
        "version": FORMAT_VERSION,
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "run_id": run_id,
    }

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

    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", _json_bytes(manifest))
        z.writestr("run.json", _json_bytes(run_obj))
        z.writestr("steps.json", _json_bytes(steps_obj))

    return out_path


def import_areplay(store: Store, in_path: str) -> str:
    """
    Imports a .areplay artifact into the store as a NEW run_id.
    Returns the new run_id.
    """
    with zipfile.ZipFile(in_path, "r") as z:
        manifest = json.loads(z.read("manifest.json").decode("utf-8"))
        run_obj = json.loads(z.read("run.json").decode("utf-8"))
        steps_obj = json.loads(z.read("steps.json").decode("utf-8"))

    name = run_obj.get("name", "imported_run")
    started_at = datetime.fromisoformat(run_obj["started_at"])
    meta = run_obj.get("meta", {})
    meta = {**meta, "imported_from": in_path, "areplay_version": manifest.get("version")}

    new_run_id = store.create_run(name=name, started_at=started_at, meta=meta)

    # end_run if ended_at exists
    ended_at = run_obj.get("ended_at")
    if ended_at:
        store.end_run(new_run_id, datetime.fromisoformat(ended_at))

    # Insert steps in order; preserve idx/kind/name/payloads
    for s in sorted(steps_obj, key=lambda x: int(x["idx"])):
        store.add_step(
            run_id=new_run_id,
            idx=int(s["idx"]),
            kind=s["kind"],
            name=s["name"],
            ts=datetime.fromisoformat(s["ts"]),
            input=s.get("input") or {},
            output=s.get("output") or {},
            error=s.get("error"),
        )

    return new_run_id
