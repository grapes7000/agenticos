from __future__ import annotations

from datetime import datetime
import html
from pathlib import Path

from .settings import Settings
from .workflows import StatusReport


def render_dashboard(settings: Settings, report: StatusReport, output: Path | None = None) -> Path:
    target = output or settings.data_dir / "dashboard" / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    cards = "".join(
        f"<article class='card {html.escape(check.status)}'><h2>{html.escape(check.name)}</h2>"
        f"<strong>{html.escape(check.status.upper())}</strong><p>{html.escape(check.detail)}</p></article>"
        for check in report.checks
    )
    suggestions = "".join(f"<li>{html.escape(item)}</li>" for item in report.suggestions) or "<li>None</li>"
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>AgenticOS</title><style>
:root {{ color-scheme: dark; --bg:#101015; --panel:#1b1b24; --text:#f4f1ff; --muted:#bcb5cc;
--accent:#d48cff; --ok:#73e2a7; --warn:#ffd166; --bad:#ff6b8a; }}
* {{ box-sizing:border-box }} body {{ margin:0; font:16px/1.5 system-ui,sans-serif; background:var(--bg); color:var(--text) }}
main {{ width:min(1100px,92vw); margin:3rem auto }} h1 {{ font-size:clamp(2rem,6vw,4rem); margin-bottom:.2rem }}
.subtitle {{ color:var(--muted); margin-top:0 }} .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:1rem }}
.card {{ background:var(--panel); border:1px solid #343345; border-radius:16px; padding:1.1rem }}
.card strong {{ color:var(--accent) }} .card.ok strong {{ color:var(--ok) }} .card.warning strong,.card.optional strong {{ color:var(--warn) }}
.card.critical strong,.card.offline strong {{ color:var(--bad) }} code {{ color:var(--accent) }}
</style></head><body><main><h1>AgenticOS</h1><p class="subtitle">{html.escape(report.headline)}</p>
<section class="grid">{cards}</section><h2>Suggested next actions</h2><ul>{suggestions}</ul>
<p class="subtitle">Generated {html.escape(datetime.now().astimezone().isoformat(timespec='seconds'))}</p>
</main></body></html>"""
    target.write_text(document, encoding="utf-8")
    return target
