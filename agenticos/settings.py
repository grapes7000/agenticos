from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import tomllib
from typing import Any


def _expanded(value: str | Path) -> Path:
    return Path(os.path.expandvars(str(value))).expanduser().resolve()


def _default_config_path() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "agenticos" / "config.toml"


def _default_data_dir() -> Path:
    base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "agenticos"


@dataclass(frozen=True)
class Settings:
    root: Path
    vault: Path
    data_dir: Path
    database_path: Path
    ollama_url: str
    model: str
    dry_run: bool
    memory_database: Path
    memory_output_dir: Path
    allowed_scan_roots: tuple[Path, ...]
    blocked_terms: tuple[str, ...]
    config_path: Path


def load_settings(root: Path | None = None, config_path: Path | None = None) -> Settings:
    project_root = _expanded(root or os.environ.get("AGENTOS_HOME", Path(__file__).parents[1]))
    selected_config = _expanded(config_path or os.environ.get("AGENTOS_CONFIG", _default_config_path()))
    raw: dict[str, Any] = {}
    if selected_config.is_file():
        with selected_config.open("rb") as handle:
            raw = tomllib.load(handle)

    core = raw.get("agenticos", {})
    memory = raw.get("memory", {})
    scan = raw.get("scan", {})
    data_dir = _expanded(os.environ.get("AGENTOS_DATA_DIR", core.get("data_dir", _default_data_dir())))
    vault = _expanded(os.environ.get("AGENTOS_VAULT", core.get("vault", Path.home() / "vault")))
    memory_db = _expanded(
        os.environ.get(
            "AGENTOS_MEMORY_DB",
            memory.get("database", project_root / "chatgpt-memory" / "data" / "memory.sqlite3"),
        )
    )
    memory_output = _expanded(
        os.environ.get(
            "AGENTOS_MEMORY_OUTPUT",
            memory.get("output_dir", project_root / "chatgpt-memory" / "memory"),
        )
    )
    roots = scan.get("allowed_roots", ["~/Downloads", "~/Desktop", "~/Documents", "~/Projects"])
    blocked = scan.get(
        "blocked_terms",
        ["wallet", "seed", "mnemonic", "keystore", ".ssh", "password", "recovery", "secret"],
    )
    dry_value = os.environ.get("AGENTOS_DRY_RUN", str(core.get("dry_run", True))).lower()
    return Settings(
        root=project_root,
        vault=vault,
        data_dir=data_dir,
        database_path=data_dir / "agentos.sqlite3",
        ollama_url=os.environ.get("OLLAMA_HOST", core.get("ollama_url", "http://localhost:11434")).rstrip("/"),
        model=os.environ.get("AGENTOS_MODEL", core.get("model", "qwen2.5-coder:7b")),
        dry_run=dry_value not in {"0", "false", "no"},
        memory_database=memory_db,
        memory_output_dir=memory_output,
        allowed_scan_roots=tuple(_expanded(path) for path in roots),
        blocked_terms=tuple(str(term).lower() for term in blocked),
        config_path=selected_config,
    )
