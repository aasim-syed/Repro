# AgentReplay (v0.1)

A small OSS library to **record**, **replay**, and **diff** agent runs (LLM + tools).

## What "replay" means in v0.1
- Replays a run by **mocking tool outputs** from the recorded trace.
- Useful to reproduce failures, debug step-by-step, and detect regressions via diffs.

## Install
```bash

## Quickstart (Windows PowerShell)
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
python examples\plain_python_agent.py

agentreplay runs list --db agentreplay.db
agentreplay export <RUN_ID> -o repro.areplay --db agentreplay.db
agentreplay import repro.areplay --db agentreplay.db
agentreplay replay <RUN_ID> --strict --db agentreplay.db
