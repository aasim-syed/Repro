from __future__ import annotations

import random
from agentreplay import Recorder, SQLiteStore, diff_runs


def fake_llm(prompt: str) -> str:
    # simulate mild nondeterminism
    if "plan" in prompt:
        return random.choice(["use_tool:A", "use_tool:B"])
    return "ok"


def tool_a(x: int) -> int:
    return x + 1


def tool_b(x: int) -> int:
    return x + 2


def run_once(db_path: str, seed: int) -> str:
    random.seed(seed)
    store = SQLiteStore(db_path)
    rec = Recorder(store=store, project="example", redaction=True)

    with rec.run("toy_agent", meta={"seed": seed}) as r:
        plan = fake_llm("plan: increment number")
        rec.llm("planner", input={"prompt": "plan"}, output={"text": plan})

        x = 10
        if plan == "use_tool:A":
            out = tool_a(x)
            rec.tool("tool_a", input={"x": x}, output={"y": out})
        else:
            out = tool_b(x)
            rec.tool("tool_b", input={"x": x}, output={"y": out})

        answer = fake_llm("final answer")
        rec.llm("finalizer", input={"prompt": "final"}, output={"text": answer, "result": out})

    print("Run ID:", r.id)
    return r.id


if __name__ == "__main__":
    db = "agentreplay.db"
    run1 = run_once(db, seed=1)
    run2 = run_once(db, seed=2)

    store = SQLiteStore(db)
    print("\n--- DIFF ---")
    print(diff_runs(store, run1, run2))

    print("\nTry:")
    print(f"  agentreplay runs list --db {db}")
    print(f"  agentreplay replay {run1} --db {db}")
    print(f"  agentreplay diff {run1} {run2} --db {db}")
