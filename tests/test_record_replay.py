from agentreplay import Recorder, SQLiteStore, Replayer

def test_record_and_replay(tmp_path):
    db = tmp_path / "t.db"
    store = SQLiteStore(str(db))
    rec = Recorder(store=store)

    with rec.run("test") as r:
        rec.llm("planner", input={"a": 1}, output={"b": 2})
        rec.tool("tool_x", input={"q": "hi"}, output={"ok": True})

    rep = Replayer(store)
    report = rep.replay(r.id)
    assert report.steps_replayed == 2
    assert report.ok is True
