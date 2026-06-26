#!/usr/bin/env python3
import sys, re, datetime
from urllib.parse import urlparse
from agentos_common import write_note, md_frontmatter, ollama_generate, slugify, log_event

try:
    import requests
    from bs4 import BeautifulSoup
except Exception as e:
    requests = BeautifulSoup = None
    IMPORT_ERR = e
else:
    IMPORT_ERR = None


def fetch_text(url):
    if requests is None:
        raise RuntimeError(f"requests/bs4 unavailable: {IMPORT_ERR}")
    r = requests.get(url, timeout=20, headers={"User-Agent":"AgenticOSLayer1/0.1"})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    title = soup.title.string.strip() if soup.title and soup.title.string else url
    text = re.sub(r"\n{3,}", "\n\n", soup.get_text("\n"))
    text = re.sub(r"[ \t]{2,}", " ", text)
    return title, text[:30000]


def main():
    if len(sys.argv) < 2:
        print("Usage: agentos research <url>")
        sys.exit(1)
    url = sys.argv[1]
    title, text = fetch_text(url)
    prompt = f"""
Create an Obsidian research note from this webpage text.
Include:
- 5 bullet summary
- Why it matters for Brooke's Agentic OS / Linux automation projects
- Useful commands/tools mentioned if any
- Questions to research next
- Source URL
Do not copy long passages verbatim.

URL: {url}
TITLE: {title}
TEXT:
{text}
""".strip()
    summary = ollama_generate(prompt, timeout=180)
    date = datetime.date.today().isoformat()
    body = md_frontmatter(title, ["research", "agentic-os"])
    body += f"# {title}\n\nSource: {url}\n\n{summary}\n"
    note = write_note(f"Agentic OS/04 Research/{date}-{slugify(title)}.md", body)
    log_event("research", title, str(note), {"url": url})
    print(f"Saved research note: {note}")

if __name__ == "__main__":
    main()
