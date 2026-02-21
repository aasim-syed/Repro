from __future__ import annotations

import typer
from typing import Optional

from .store_sqlite import SQLiteStore
from .replay import Replayer
from .diff import diff_runs
from .exporter import export_areplay, import_areplay

app = typer.Typer(no_args_is_help=True)


@app.command("runs")
def runs_cmd(
    action: str = typer.Argument(..., help="list"),
    db: str = typer.Option("agentreplay.db", "--db"),
    limit: int = typer.Option(20, "--limit"),
):
    store = SQLiteStore(db)
    store.init()
    if action != "list":
        raise typer.BadParameter("Only 'list' supported")
    runs = store.list_runs(limit=limit)
    for r in runs:
        typer.echo(f"{r.id}  {r.started_at.isoformat()}  {r.name}")


@app.command("replay")
def replay_cmd(
    run_id: str = typer.Argument(...),
    db: str = typer.Option("agentreplay.db", "--db"),
    strict: bool = typer.Option(False, "--strict", help="Fail if tool inputs differ from recorded trace"),
):
    store = SQLiteStore(db)
    store.init()
    rep = Replayer(store)
    report = rep.replay(run_id, strict=strict)
    typer.echo(f"ok={report.ok} steps={report.steps_replayed}")
    for n in report.notes:
        typer.echo(f"- {n}")


@app.command("diff")
def diff_cmd(
    run_a: str = typer.Argument(...),
    run_b: str = typer.Argument(...),
    db: str = typer.Option("agentreplay.db", "--db"),
):
    store = SQLiteStore(db)
    store.init()
    typer.echo(diff_runs(store, run_a, run_b))


@app.command("export")
def export_cmd(
    run_id: str = typer.Argument(...),
    out: str = typer.Option("run.areplay", "--out", "-o"),
    db: str = typer.Option("agentreplay.db", "--db"),
):
    store = SQLiteStore(db)
    store.init()
    path = export_areplay(store, run_id, out)
    typer.echo(f"Exported: {path}")


@app.command("import")
def import_cmd(
    path: str = typer.Argument(...),
    db: str = typer.Option("agentreplay.db", "--db"),
):
    store = SQLiteStore(db)
    store.init()
    new_id = import_areplay(store, path)
    typer.echo(f"Imported as run_id: {new_id}")


# ---------------- NEW: test command ----------------
@app.command("test")
def test_cmd(
    golden: str = typer.Argument(..., help=".areplay path OR run_id of golden in DB"),
    current_run_id: str = typer.Option(..., "--current-run-id", help="Run id of the current run to compare against"),
    db: str = typer.Option("agentreplay.db", "--db"),
    strict: bool = typer.Option(False, "--strict", help="Fail if tool inputs differ (future: deeper strict)"),
    expect: str = typer.Option("tools", "--expect", help="tools|actions|all"),
    mode: str = typer.Option("tool", "--mode", help="tool|full (v0.2.0 uses step-level diffs)"),
    json_out: bool = typer.Option(False, "--json", help="Emit machine-readable JSON only"),
    pretty: Optional[bool] = typer.Option(None, "--pretty/--no-pretty", help="Force pretty output on/off (default: auto)"),
    animations: str = typer.Option("auto", "--animations", help="auto|on|off (only affects pretty mode)"),
):
    from .tester import test_run
    from .render import render_json, render_plain, render_rich, should_pretty

    store = SQLiteStore(db)
    store.init()

    compare = expect  # naming: spec says --expect maps to compare selection
    res = test_run(
        store=store,
        golden=golden,
        current_run_id=current_run_id,
        strict=strict,
        compare=compare,  # tools|actions|all
        mode=mode,        # tool|full
    )

    if json_out:
        typer.echo(render_json(res))
        raise typer.Exit(code=0 if res.ok else 1)

    if should_pretty(pretty):
        typer.echo(render_rich(res, animations=animations))
    else:
        typer.echo(render_plain(res))

    raise typer.Exit(code=0 if res.ok else 1)


if __name__ == "__main__":
    app()