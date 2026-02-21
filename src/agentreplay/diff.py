from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple, Optional
from .store import Store
from .models import Step


def _stable(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False)


def _first_divergence(a_steps: List[Step], b_steps: List[Step]) -> Optional[Tuple[int, Step, Step, str]]:
    n = min(len(a_steps), len(b_steps))
    for i in range(n):
        a = a_steps[i]
        b = b_steps[i]
        if (a.kind, a.name) != (b.kind, b.name):
            return (i, a, b, "kind/name changed")
        if _stable(a.input) != _stable(b.input):
            return (i, a, b, "input changed")
        if _stable(a.output) != _stable(b.output):
            return (i, a, b, "output changed")
        if _stable(a.error) != _stable(b.error):
            return (i, a, b, "error changed")
    if len(a_steps) != len(b_steps):
        # Divergence at length boundary
        i = n
        dummy = a_steps[-1] if a_steps else b_steps[-1]
        return (i, dummy, dummy, f"length changed: {len(a_steps)} != {len(b_steps)}")
    return None


def diff_runs(store: Store, run_a: str, run_b: str) -> str:
    a_steps = store.list_steps(run_a)
    b_steps = store.list_steps(run_b)

    div = _first_divergence(a_steps, b_steps)
    if div is None:
        return "No divergence. Runs are identical at step granularity."

    i, a, b, reason = div
    lines = []
    lines.append(f"DIVERGENCE at step index {i}: {reason}")
    lines.append(f"  A: kind={a.kind} name={a.name} idx={a.idx}")
    lines.append(f"  B: kind={b.kind} name={b.name} idx={b.idx}")

    # Show small payload snippets
    lines.append("  A.input:  " + _stable(a.input)[:400])
    lines.append("  B.input:  " + _stable(b.input)[:400])
    lines.append("  A.output: " + _stable(a.output)[:400])
    lines.append("  B.output: " + _stable(b.output)[:400])
    return "\n".join(lines)
