from __future__ import annotations
import json
import os
import urllib.request
from typing import Optional

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
DEFAULT_MODEL = os.getenv("AGENTOS_DEFAULT_MODEL", "qwen2.5-coder:7b")

def ollama_available(timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(f"{OLLAMA_HOST}/api/tags", timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False

def generate(prompt: str, model: Optional[str] = None, system: Optional[str] = None, timeout: int = 120) -> str:
    if not ollama_available():
        raise RuntimeError("Ollama is not reachable. Start it with: ollama serve")
    payload = {
        "model": model or DEFAULT_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.25, "top_p": 0.9},
    }
    if system:
        payload["system"] = system
    req = urllib.request.Request(
        f"{OLLAMA_HOST}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode("utf-8"))
        return data.get("response", "").strip()
