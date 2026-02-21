from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Optional, Literal, List, Tuple

from .store import Store
from .models import Step
from .diff import _first_divergence  # uses your existing engine
from .exporter import load_areplay_steps


CompareKind = Literal["tools", "actions", "all"]
ModeKind = Literal["tool", "full"]  # for future expansion


@dataclass(frozen=True)
class Divergence:
    step_idx: int
    kind: str
    name: str
    field_path: str
    reason: str
    expected: Any
    actual: Any


@dataclass(frozen=True)
class TestResult:
    ok: bool
    first_divergence: Optional[Divergence]
    summary: str
    details: Dict[str, Any]


def _stable(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False)


def _filter_steps(steps: List[Step], compare: CompareKind) -> List[Step]:
    if compare == "all":
        return steps
    if compare == "tools":
        return [s for s in steps if s.kind == "tool"]
    if compare == "actions":
        # minimal v0.2.0: treat "planner actions" as LLM steps
        # We compare llm input/output at step granularity for now.
        return [s for s in steps if s.kind == "llm"]
    # fallback
    return steps


def _div_tuple_to_struct(div: Tuple[int, Step, Step, str]) -> Divergence:
    i, a, b, reason = div

    # minimal field_path mapping based on your diff reasons
    # (you can upgrade later to true JSON-path diff)
    if "kind/name" in reason:
        path = "kind/name"
        expected = {"kind": a.kind, "name": a.name}
        actual = {"kind": b.kind, "name": b.name}
    elif "input" in reason:
        path = "input"
        expected = a.input
        actual = b.input
    elif "output" in reason:
        path = "output"
        expected = a.output
        actual = b.output
    elif "error" in reason:
        path = "error"
        expected = a.error
        actual = b.error
    elif "length" in reason:
        path = "steps.length"
        expected = None
        actual = None
    else:
        path = "unknown"
        expected = None
        actual = None

    return Divergence(
        step_idx=i,
        kind=a.kind,
        name=a.name,
        field_path=path,
        reason=reason,
        expected=expected,
        actual=actual,
    )


def test_run(
    *,
    store: Store,
    golden: str,  # .areplay path OR run_id
    current_run_id: str,
    strict: bool = False,
    compare: CompareKind = "tools",
    mode: ModeKind = "tool",
) -> TestResult:
    """
    v0.2.0 semantics:
    - compare: tools|actions|all -> filters step stream then uses your existing divergence logic
    - strict: placeholder for future (your replay has strict; for testing we keep the flag)
    - mode: placeholder (tool/full), currently step-level diffs only
    """

    # Load golden steps
    if golden.endswith(".areplay"):
        golden_steps = load_areplay_steps(golden)
        golden_ref = {"type": "file", "value": golden}
    else:
        golden_steps = store.list_steps(golden)
        golden_ref = {"type": "run_id", "value": golden}

    # Load current steps
    current_steps = store.list_steps(current_run_id)

    # Filter streams by compare mode
    g2 = _filter_steps(golden_steps, compare)
    c2 = _filter_steps(current_steps, compare)

    div = _first_divergence(g2, c2)
    if div is None:
        return TestResult(
            ok=True,
            first_divergence=None,
            summary="PASS: no divergence",
            details={
                "golden": golden_ref,
                "current_run_id": current_run_id,
                "compare": compare,
                "strict": strict,
                "mode": mode,
                "steps_compared": len(g2),
            },
        )

    d = _div_tuple_to_struct(div)
    return TestResult(
        ok=False,
        first_divergence=d,
        summary=f"FAIL: divergence at step {d.step_idx} ({d.kind}:{d.name}) - {d.reason}",
        details={
            "golden": golden_ref,
            "current_run_id": current_run_id,
            "compare": compare,
            "strict": strict,
            "mode": mode,
            "steps_compared": len(g2),
            "expected_snippet": _stable(d.expected)[:600] if d.expected is not None else None,
            "actual_snippet": _stable(d.actual)[:600] if d.actual is not None else None,
        },
    )