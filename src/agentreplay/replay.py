from __future__ import annotations

from typing import Dict, Any, Optional, List

from .store import Store
from .models import ReplayReport, Step


class ToolMocker:
    """
    During replay, tool outputs come from the recorded trace.
    This is the key determinism primitive for v0.1.
    """

    def __init__(self, tool_steps: List[Step]):
        self._by_index = {s.idx: s for s in tool_steps}
        self._cursor = 0
        self._tool_indices = [s.idx for s in tool_steps]

    def next_output(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        if self._cursor >= len(self._tool_indices):
            raise RuntimeError("Replay tool calls exceeded recorded tool calls")

        idx = self._tool_indices[self._cursor]
        step = self._by_index[idx]
        self._cursor += 1

        # Optional strict checks:
        if step.name != tool_name:
            raise RuntimeError(f"Tool name mismatch at replay cursor {self._cursor-1}: {step.name} != {tool_name}")

        # Could also compare inputs; for v0.1 keep lenient (diff layer will catch changes).
        return step.output


class Replayer:
    def __init__(self, store: Store):
        self.store = store

    def build_tool_mocker(self, run_id: str) -> ToolMocker:
        steps = self.store.list_steps(run_id)
        tool_steps = [s for s in steps if s.kind == "tool"]
        return ToolMocker(tool_steps)

    def replay(self, run_id: str) -> ReplayReport:
        # v0.1: replay is "validate trace consistency + tool mocking availability"
        steps = self.store.list_steps(run_id)
        notes: List[str] = []
        ok = True

        # Basic integrity checks
        last_idx = -1
        for s in steps:
            if s.idx != last_idx + 1:
                ok = False
                notes.append(f"Non-contiguous step idx at {s.idx} (prev={last_idx})")
            last_idx = s.idx

        # Ensure tool steps are mockable
        _ = self.build_tool_mocker(run_id)
        notes.append("Tool mocker prepared from recorded tool steps.")

        return ReplayReport(run_id=run_id, ok=ok, steps_replayed=len(steps), notes=notes)
