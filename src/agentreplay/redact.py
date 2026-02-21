from __future__ import annotations

from typing import Any, Dict, Callable
import re


DEFAULT_SECRET_KEYS = {"api_key", "apikey", "token", "secret", "password", "authorization"}


def redact_dict(d: Dict[str, Any], extra_keys: set[str] | None = None) -> Dict[str, Any]:
    keys = DEFAULT_SECRET_KEYS | (extra_keys or set())
    out: Dict[str, Any] = {}
    for k, v in (d or {}).items():
        if k.lower() in keys:
            out[k] = "***REDACTED***"
        else:
            out[k] = v
    return out


def redact_text(s: str) -> str:
    # minimal: redact bearer tokens
    s = re.sub(r"Bearer\s+[A-Za-z0-9\-\._~\+\/]+=*", "Bearer ***REDACTED***", s)
    return s


Redactor = Callable[[Dict[str, Any]], Dict[str, Any]]
