from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, Optional

from .tester import TestResult


def _is_ci() -> bool:
    # Common CI signals
    return (
        os.getenv("CI", "").lower() in {"1", "true", "yes"}
        or os.getenv("GITHUB_ACTIONS", "").lower() in {"1", "true", "yes"}
        or os.getenv("BUILD_BUILDID") is not None  # Azure DevOps
    )


def _is_tty() -> bool:
    try:
        return sys.stdout.isatty()
    except Exception:
        return False


def should_pretty(pretty_flag: Optional[bool]) -> bool:
    # pretty_flag: True/False/None (auto)
    if pretty_flag is True:
        return True
    if pretty_flag is False:
        return False
    # auto:
    if _is_ci():
        return False
    return _is_tty()


def render_json(res: TestResult) -> str:
    payload: Dict[str, Any] = {
        "ok": res.ok,
        "summary": res.summary,
        "details": res.details,
        "first_divergence": None,
    }
    if res.first_divergence:
        d = res.first_divergence
        payload["first_divergence"] = {
            "step_idx": d.step_idx,
            "kind": d.kind,
            "name": d.name,
            "field_path": d.field_path,
            "reason": d.reason,
            "expected": d.expected,
            "actual": d.actual,
        }
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)


def render_plain(res: TestResult) -> str:
    lines = [res.summary]
    if res.first_divergence:
        d = res.first_divergence
        lines.append(f"step_idx: {d.step_idx}")
        lines.append(f"kind/name: {d.kind}:{d.name}")
        lines.append(f"field: {d.field_path}")
        lines.append(f"reason: {d.reason}")
        lines.append(f"expected: {json.dumps(d.expected, ensure_ascii=False)[:800]}")
        lines.append(f"actual:   {json.dumps(d.actual, ensure_ascii=False)[:800]}")
    return "\n".join(lines)


def render_rich(res: TestResult, *, animations: str = "auto") -> str:
    """
    Returns a string; caller prints it.
    Rich is imported only here so core usage doesn't require it.
    """
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.json import JSON
    from rich.text import Text

    console = Console(record=True)

    title = "PASS" if res.ok else "FAIL"
    style = "bold green" if res.ok else "bold red"

    # summary panel
    console.print(Panel(Text(res.summary, style=style), title=title, border_style=style))

    # details table
    t = Table(show_header=False, box=None)
    for k in ["compare", "mode", "strict", "steps_compared", "current_run_id"]:
        if k in res.details:
            t.add_row(k, str(res.details[k]))
    console.print(t)

    if res.first_divergence:
        d = res.first_divergence
        console.print(
            Panel(
                f"[bold]step_idx[/bold]: {d.step_idx}\n"
                f"[bold]kind/name[/bold]: {d.kind}:{d.name}\n"
                f"[bold]field[/bold]: {d.field_path}\n"
                f"[bold]reason[/bold]: {d.reason}",
                title="First divergence",
                border_style="red",
            )
        )
        console.print(Panel(JSON.from_data(d.expected), title="Expected", border_style="yellow"))
        console.print(Panel(JSON.from_data(d.actual), title="Actual", border_style="cyan"))

    return console.export_text()