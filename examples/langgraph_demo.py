"""
Optional demo:
pip install langgraph langchain-core

This shows how to record tool calls / LLM calls via a simple wrapper pattern.
"""

from __future__ import annotations

from agentreplay import Recorder, SQLiteStore

# NOTE: This file is meant as a template; keep it import-safe for users without langgraph.


def record_tool(rec: Recorder, tool_name: str, fn):
    def wrapped(*args, **kwargs):
        inp = {"args": list(args), "kwargs": kwargs}
        try:
            out = fn(*args, **kwargs)
            rec.tool(tool_name, input=inp, output={"result": out})
            return out
        except Exception as e:
            rec.tool(tool_name, input=inp, output={}, error={"type": type(e).__name__, "msg": str(e)})
            raise

    return wrapped


if __name__ == "__main__":
    store = SQLiteStore("agentreplay.db")
    rec = Recorder(store=store, project="langgraph-demo")

    with rec.run("langgraph_like_flow") as r:
        # Replace these with actual LangGraph nodes/tools in your real integration.
        def tool_add(x, y): return x + y
        safe_add = record_tool(rec, "add", tool_add)

        rec.llm("planner", input={"messages": ["add 2 and 3"]}, output={"text": "call add(2,3)"})
        res = safe_add(2, 3)
        rec.llm("finalizer", input={"res": res}, output={"text": f"answer={res}"})

    print("Recorded run:", r.id)
