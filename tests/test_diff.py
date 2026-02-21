from agentreplay import Recorder, SQLiteStore, diff_runs

def test_diff_detects_change(tmp_path):
    db = tmp_path / "t.db"
    store = SQLiteStore(str(db))

    rec = Recorder(store=store)
    with rec.run("a") as ra:
        rec.tool("t", input={"x": 1}, output={"y": 2})

    rec2 = Recorder(store=store)
    with rec2.run("b") as rb:
        rec2.tool("t", input={"x": 1}, output={"y": 3})

    out = diff_runs(store, ra.id, rb.id)
    assert "DIVERGENCE" in out
    assert "output changed" in out
