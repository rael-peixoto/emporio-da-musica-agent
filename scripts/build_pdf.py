"""Build the submission PDF from the README, the decision log and the example conversations.

Usage:
    python scripts/build_pdf.py [--with-access-code] [--chrome PATH]

--with-access-code adds a private "Reviewer access" page with the proxy URL and the access code
read from EMPORIO_ACCESS_CODE (.env). The code is never printed. The PDF goes to dist/ and is
never committed.
"""

from __future__ import annotations

import argparse
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import markdown
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from emporio.config import DEFAULT_PROXY_URL  # noqa: E402

REPO_URL = "https://github.com/rael-peixoto/emporio-da-musica-agent"
PDF_NAME = "Rael Marchant Peixoto - AI Engineer – Full-Stack para Aplicações com IA Generativa.pdf"
CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "google-chrome", "chromium", "chromium-browser",
]
CSS = """
body { font-family: "Segoe UI", Arial, sans-serif; font-size: 10.5pt; line-height: 1.45;
       color: #1a1a1a; max-width: 100%; }
h1 { font-size: 20pt; border-bottom: 2px solid #333; padding-bottom: 4px; }
h2 { font-size: 15pt; border-bottom: 1px solid #ccc; padding-bottom: 2px; margin-top: 1.4em; }
h3 { font-size: 12pt; }
table { border-collapse: collapse; margin: 0.6em 0; width: 100%; font-size: 9.5pt; }
th, td { border: 1px solid #bbb; padding: 4px 6px; vertical-align: top; }
th { background: #f0f0f0; }
code { font-family: Consolas, monospace; font-size: 9pt; background: #f4f4f4; padding: 0 2px; }
pre { background: #f4f4f4; padding: 8px; white-space: pre-wrap; word-break: break-word; }
pre code { background: none; }
a { color: #0645ad; text-decoration: none; }
details summary { font-size: 9pt; color: #555; }
img { max-width: 100%; border: 1px solid #ccc; margin: 6px 0; }
.part { page-break-before: always; }
.access { border: 2px solid #c00; padding: 12px; background: #fff6f6; }
"""


def find_chrome(explicit: str | None) -> str:
    for candidate in ([explicit] if explicit else CHROME_CANDIDATES):
        path = shutil.which(candidate) or (candidate if Path(candidate).exists() else None)
        if path:
            return path
    sys.exit("Chrome or Edge not found; pass --chrome PATH")


LIST_ITEM = re.compile(r"^\s*(?:[-*]|\d+\.)\s")


def separate_lists(text: str) -> str:
    """GitHub renders a list right after a text line; python-markdown needs a blank line first."""
    out, in_code = [], False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_code = not in_code
        previous = out[-1] if out else ""
        if (not in_code and LIST_ITEM.match(line) and previous.strip()
                and not LIST_ITEM.match(previous) and not previous.startswith((" ", "\t"))):
            out.append("")
        out.append(line)
    return "\n".join(out)


def to_html(md_path: Path) -> str:
    text = separate_lists(md_path.read_text(encoding="utf-8"))

    def absolute(match: re.Match) -> str:  # repo-relative links -> GitHub, so they work in a PDF
        label, target = match.group(1), match.group(2)
        if target.startswith(("http", "#", "mailto:")):
            return match.group(0)
        resolved = (md_path.parent / target.split("#")[0]).resolve().relative_to(ROOT).as_posix()
        anchor = "#" + target.split("#", 1)[1] if "#" in target else ""
        return f"[{label}]({REPO_URL}/blob/main/{resolved}{anchor})"

    def local_image(match: re.Match) -> str:  # images must render inside the PDF, not link out
        return f"![{match.group(1)}]({(md_path.parent / match.group(2)).resolve().as_uri()})"

    text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", local_image, text)
    text = re.sub(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)", absolute, text)
    return markdown.markdown(text, extensions=["tables", "fenced_code", "toc", "md_in_html"])


def access_page() -> str:
    load_dotenv(ROOT / ".env")
    code = os.getenv("EMPORIO_ACCESS_CODE", "").strip()
    url = (os.getenv("PROXY_URL", "").strip() or DEFAULT_PROXY_URL)
    if not code or not url:
        sys.exit("EMPORIO_ACCESS_CODE (and a proxy URL) must be set in .env for --with-access-code")
    return f"""
<div class="access">
<h2>Reviewer access (private — not published in the repository)</h2>
<p>To try the agent without your own API key, run these commands in a terminal (Command Prompt
or PowerShell), in a folder of your choice:</p>
<pre><code>git clone {REPO_URL}.git
cd emporio-da-musica-agent
python -m venv .venv
.venv\\Scripts\\python -m pip install -r requirements.txt
.venv\\Scripts\\python -m emporio.setup --access-code {html.escape(code)}
.venv\\Scripts\\python -m emporio.web</code></pre>
<p>The last command opens the WhatsApp-style chat in your browser; <code>python -m emporio</code>
gives the terminal chat. (macOS/Linux: use <code>.venv/bin/python</code>.)</p>
<p>Model calls go through the author's proxy at <code>{html.escape(url)}</code>, which keeps the
API key server-side and enforces usage limits. The first message may take up to a minute if
the free server is asleep. The code stops working when the key expires on 2026-11-20.</p>
</div>"""


def main() -> int:
    parser = argparse.ArgumentParser(prog="python scripts/build_pdf.py")
    parser.add_argument("--with-access-code", action="store_true")
    parser.add_argument("--chrome")
    args = parser.parse_args()

    parts = [to_html(ROOT / "README.md")]
    if args.with_access_code:
        parts.insert(0, access_page())
    parts.append(to_html(ROOT / "docs" / "decision-log.md"))
    for example in sorted((ROOT / "examples").glob("*.md")):
        parts.append(f"<p><em>Example conversation: {example.name}</em></p>" + to_html(example))
    body = "\n".join(f'<section class="{"part" if i else ""}">{p}</section>'
                     for i, p in enumerate(parts))
    page = (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f"<style>{CSS}</style></head><body>{body}</body></html>")

    out_dir = ROOT / "dist"
    out_dir.mkdir(exist_ok=True)
    pdf = out_dir / PDF_NAME
    with tempfile.TemporaryDirectory() as tmp:
        html_file = Path(tmp) / "submission.html"
        html_file.write_text(page, encoding="utf-8")
        subprocess.run(
            [find_chrome(args.chrome), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
             f"--print-to-pdf={pdf}", html_file.as_uri()],
            check=True, capture_output=True,
        )
    size_mb = pdf.stat().st_size / 1_000_000
    print(f"Wrote {pdf.relative_to(ROOT)} ({size_mb:.2f} MB)"
          + (" — includes the PRIVATE access code page" if args.with_access_code else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
