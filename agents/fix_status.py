from pathlib import Path
from datetime import datetime
import os

HOME = Path.home()
AGENTOS = Path(os.getenv("AGENTOS_DIR", str(HOME / "AgenticOS"))).expanduser()
VAULT = Path(os.getenv("OBSIDIAN_VAULT", str(HOME / "vault"))).expanduser()
folders = {
    "Test Reports": VAULT / "Agentic OS" / "Test Reports",
    "Bug Reports": VAULT / "Agentic OS" / "Bug Reports",
    "Patch Plans": VAULT / "Agentic OS" / "Patch Plans",
    "Fix Cycles": VAULT / "Agentic OS" / "Fix Cycles",
    "Run Folders": AGENTOS / "iterative-fixes" / "runs",
}
print(f"AgenticOS Iterative Fix Status - {datetime.now().isoformat(timespec='seconds')}")
print(f"AgenticOS: {AGENTOS}")
print(f"Vault: {VAULT}\n")
for label, folder in folders.items():
    files = sorted(folder.glob("*")) if folder.exists() else []
    print(f"{label}: {len(files)} item(s)")
    for p in files[-5:]:
        print(f"  - {p}")
    print()
