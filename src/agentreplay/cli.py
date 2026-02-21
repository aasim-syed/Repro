from __future__ import annotations

import typer
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


if __name__ == "__main__":
    app()
