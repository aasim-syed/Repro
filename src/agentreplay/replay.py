from __future__ import annotations

import json
from typing import Dict, Any, List

from .store import Store
from .models import ReplayReport, Step


def _stable(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False)


class ToolMocker:
    def __init__(self, tool_steps: List[Step], strict: bool = False):
        self.strict = strict
        self._tool_steps = tool_steps
        self._cursor = 0

    def next_output(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        if self._cursor >= len(self._tool_steps):
            raise RuntimeError("Replay tool calls exceeded recorded tool calls")

        step = self._tool_steps[self._cursor]
        self._cursor += 1

        if step.name != tool_name:
            raise RuntimeError(
                f"Tool name mismatch at tool-step #{self._cursor-1}: recorded={step.name} current={tool_name}"
            )

        if self.strict:
            if _stable(step.input) != _stable(tool_input):
                raise RuntimeError(
                    f"Tool input mismatch at tool-step #{self._cursor-1} for {tool_name}\n"
                    f"recorded={_stable(step.input)}\ncurrent ={_stable(tool_input)}"
                )

        return step.output


class Replayer:
    def __init__(self, store: Store):
        self.store = store

    def build_tool_mocker(self, run_id: str, strict: bool = False) -> ToolMocker:
        steps = self.store.list_steps(run_id)
        tool_steps = [s for s in steps if s.kind == "tool"]
        return ToolMocker(tool_steps, strict=strict)

    def replay(self, run_id: str, strict: bool = False) -> ReplayReport:
        steps = self.store.list_steps(run_id)
        notes: List[str] = []
        ok = True

        # integrity check
        last_idx = -1
        for s in steps:
            if s.idx != last_idx + 1:
                ok = False
                notes.append(f"Non-contiguous step idx at {s.idx} (prev={last_idx})")
            last_idx = s.idx

        _ = self.build_tool_mocker(run_id, strict=strict)
        notes.append(f"Tool mocker prepared (strict={strict}).")

        return ReplayReport(run_id=run_id, ok=ok, steps_replayed=len(steps), notes=notes)
