from __future__ import annotations

import typer
from typing import Optional
from .store_sqlite import SQLiteStore
from .replay import Replayer
from .diff import diff_runs

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
        raise typer.BadParameter("Only 'list' supported in v0.1")
    runs = store.list_runs(limit=limit)
    for r in runs:
        typer.echo(f"{r.id}  {r.started_at.isoformat()}  {r.name}")


@app.command("replay")
def replay_cmd(
    run_id: str = typer.Argument(...),
    db: str = typer.Option("agentreplay.db", "--db"),
):
    store = SQLiteStore(db)
    store.init()
    rep = Replayer(store)
    report = rep.replay(run_id)
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


if __name__ == "__main__":
    app()
