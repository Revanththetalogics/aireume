#!/usr/bin/env python3
"""
Block backend startup until Ollama is reachable, the configured model is pulled,
and a minimal generate call has completed (loads weights into RAM).

Disable with OLLAMA_STARTUP_REQUIRED=0 (local pytest, dev without GPU/model).
Automatically skipped when using Ollama Cloud (https://ollama.com).
"""
from __future__ import annotations

import json
import os
import sys
import time

import httpx


def _env_flag(name: str, default: str = "1") -> bool:
    v = os.getenv(name, default).strip().lower()
    return v not in ("0", "false", "no", "off")


def _is_ollama_cloud(base_url: str) -> bool:
    """Check if the base URL points to Ollama Cloud (ollama.com)."""
    return "ollama.com" in base_url.lower()


def _pick_model_name(tags: list, want: str):
    """Return a concrete tag name from /api/tags that matches want (substring)."""
    names = [m.get("name", "") for m in tags if m.get("name")]
    if not names or not want:
        return None
    for n in names:
        if n == want or want in n:
            return n
    return None


def main() -> int:
    if not _env_flag("OLLAMA_STARTUP_REQUIRED", "1"):
        print("[wait_for_ollama] OLLAMA_STARTUP_REQUIRED=0 — skipping Ollama gate.", flush=True)
        return 0

    base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")

    # Skip local health checks for Ollama Cloud — cloud doesn't need warmup or model pull
    if _is_ollama_cloud(base):
        print(f"[wait_for_ollama] Ollama Cloud detected ({base}) — skipping local Ollama gate.", flush=True)
        print("[wait_for_ollama] Cloud models do not require local warmup or model pulling.", flush=True)
        return 0
    want = (os.getenv("OLLAMA_MODEL") or "gemma4:31b-cloud").strip()
    poll_sec = float(os.getenv("OLLAMA_POLL_INTERVAL_SEC", "2"))
    deadline = time.monotonic() + float(os.getenv("OLLAMA_WAIT_TIMEOUT_SEC", "120"))
    warm_timeout = float(os.getenv("OLLAMA_WARMUP_TIMEOUT_SEC", "300"))

    print(f"[wait_for_ollama] Waiting for Ollama at {base} (model={want})…", flush=True)

    tags_body = None
    while time.monotonic() < deadline:
        try:
            r = httpx.get(f"{base}/api/tags", timeout=5.0)
            if r.status_code == 200:
                tags_body = r.json()
                break
        except Exception as e:
            print(f"[wait_for_ollama] … not ready ({str(e)[:60]})", flush=True)
        time.sleep(poll_sec)

    if not tags_body:
        print("[wait_for_ollama] FATAL: Ollama did not respond with /api/tags in time.", file=sys.stderr, flush=True)
        return 1

    models = tags_body.get("models") or []
    resolved = _pick_model_name(models, want)
    if not resolved:
        have = json.dumps([m.get("name") for m in models])
        print(
            f"[wait_for_ollama] FATAL: model '{want}' not pulled. Available: {have}",
            file=sys.stderr,
            flush=True,
        )
        return 1

    print(f"[wait_for_ollama] Model found: {resolved}. Warming (load into RAM)…", flush=True)
    try:
        r = httpx.post(
            f"{base}/api/generate",
            json={
                "model": resolved,
                "prompt": ".",
                "stream": False,
                "options": {"num_predict": 1},
            },
            timeout=warm_timeout,
        )
        r.raise_for_status()
    except Exception as e:
        print(f"[wait_for_ollama] FATAL: warm generate failed: {e}", file=sys.stderr, flush=True)
        return 1

    print("[wait_for_ollama] Ollama ready — model loaded.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
