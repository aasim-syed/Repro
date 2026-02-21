# Contributing

Thanks for contributing to AgentReplay.

## Development setup
```bash
python -m venv .venv
# Windows PowerShell:
# .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pytest -q

Style

Run: ruff check .

Keep changes small and well-tested.

What to work on

Storage backends (JSONL, Postgres)

Export format improvements (.areplay v2)

Framework hooks (LangGraph, LangChain, custom agents)

Better diff output