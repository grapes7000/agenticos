from pathlib import Path
import sqlite3
import sys

DB = Path("data/db/agent_os.sqlite")
SENSITIVE_NAMES = [
    "seed", "private", "wallet", "keystore", "password", "recovery",
    "mnemonic", "ssh", "id_rsa", "secret", "passphrase", "2fa", "backup-code"
]

CATEGORIES = {
    "Images": [".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".avif", ".heic"],
    "Videos": [".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"],
    "Audio": [".mp3", ".wav", ".flac", ".m4a", ".ogg"],
    "Documents": [".pdf", ".docx", ".odt", ".txt", ".md", ".rtf"],
    "Spreadsheets": [".csv", ".xlsx", ".ods"],
    "Archives": [".zip", ".tar", ".gz", ".7z", ".rar", ".xz", ".bz2"],
    "Code": [".py", ".js", ".ts", ".html", ".css", ".json", ".sh", ".rs", ".go", ".toml", ".yaml", ".yml"],
    "Apps": [".appimage", ".deb", ".rpm", ".flatpakref"],
}

def category_for(path: Path) -> str:
    suffix = path.suffix.lower()
    for category, suffixes in CATEGORIES.items():
        if suffix in suffixes:
            return category
    return "Other"

def is_sensitive(path: Path) -> int:
    text = str(path).lower()
    return int(any(word in text for word in SENSITIVE_NAMES))

def scan(folder: Path):
    if not folder.exists():
        raise SystemExit(f"Folder not found: {folder}")
    DB.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    skipped = 0
    with sqlite3.connect(DB) as con:
        for p in folder.rglob("*"):
            if not p.is_file():
                continue
            try:
                st = p.stat()
            except OSError:
                skipped += 1
                continue
            con.execute(
                """
                INSERT INTO files(path, name, suffix, size_bytes, mtime, category, sensitive)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    name=excluded.name,
                    suffix=excluded.suffix,
                    size_bytes=excluded.size_bytes,
                    mtime=excluded.mtime,
                    category=excluded.category,
                    sensitive=excluded.sensitive,
                    indexed_at=CURRENT_TIMESTAMP
                """,
                (str(p), p.name, p.suffix.lower(), st.st_size, st.st_mtime, category_for(p), is_sensitive(p)),
            )
            count += 1
    print(f"Scanned {count} files from {folder}; skipped {skipped}")

if __name__ == "__main__":
    folder = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else Path.home() / "Downloads"
    scan(folder)
