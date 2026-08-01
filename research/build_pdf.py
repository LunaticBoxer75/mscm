#!/usr/bin/env python3
"""Convert the Convoy/Seattle research markdown to a print-ready PDF via styled HTML + headless Chrome.

Reuses the career-plan binder styling for a consistent look.
"""
import subprocess, tempfile, os, pathlib, re, markdown

ROOT = pathlib.Path(__file__).parent
OUT = ROOT / "pdf"
OUT.mkdir(parents=True, exist_ok=True)
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

CSS = """
@page { size: Letter; margin: 0.6in 0.65in; }
* { box-sizing: border-box; }
body { font-family: -apple-system, "Helvetica Neue", Arial, sans-serif; font-size: 10.5pt;
       line-height: 1.45; color: #1a1a1a; max-width: 100%; }
h1 { font-size: 19pt; margin: 0 0 6pt; color: #0b3d5c; border-bottom: 3px solid #0b3d5c; padding-bottom: 5pt; }
h2 { font-size: 14pt; margin: 16pt 0 5pt; color: #0b3d5c; border-top: 1px solid #dde3e8; padding-top: 10pt; }
h3 { font-size: 12pt; margin: 12pt 0 4pt; color: #14507a; }
h4 { font-size: 11pt; margin: 9pt 0 3pt; color: #333; }
p { margin: 4pt 0; }
a { color: #14507a; text-decoration: none; }
ul, ol { margin: 4pt 0; padding-left: 20pt; }
li { margin: 2pt 0; }
code { background: #eef2f5; padding: 1px 4px; border-radius: 3px; font-size: 9pt; }
pre { background: #f5f7f9; border: 1px solid #dde3e8; border-radius: 5px; padding: 8pt 10pt;
      font-size: 8.5pt; line-height: 1.4; white-space: pre-wrap; page-break-inside: avoid; }
pre code { background: none; padding: 0; }
blockquote { border-left: 4px solid #4a90c2; background: #f0f6fb; margin: 6pt 0; padding: 5pt 12pt;
             border-radius: 0 4px 4px 0; page-break-inside: avoid; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0; font-size: 9pt; page-break-inside: avoid; }
th, td { border: 1px solid #cdd6de; padding: 4pt 7pt; text-align: left; vertical-align: top; }
th { background: #0b3d5c; color: #fff; font-weight: 600; }
tr:nth-child(even) td { background: #f4f7fa; }
hr { border: none; border-top: 1px solid #dde3e8; margin: 12pt 0; }
.page-break { page-break-before: always; }
strong { color: #111; }
"""

MD_EXT = ["tables", "fenced_code", "sane_lists"]


def md_to_html_body(md_text: str) -> str:
    return markdown.markdown(md_text, extensions=MD_EXT)


def wrap(title: str, body_html: str) -> str:
    return (f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>{title}</title>"
            f"<style>{CSS}</style></head><body>{body_html}</body></html>")


def render_pdf(html: str, out_pdf: pathlib.Path):
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(html); tmp = f.name
    subprocess.run([CHROME, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                    "--run-all-compositor-stages-before-draw", "--virtual-time-budget=8000",
                    f"--print-to-pdf={out_pdf}", f"file://{tmp}"],
                   check=True, capture_output=True)
    os.unlink(tmp)


# (source markdown, output PDF filename, HTML <title>)
DOCS = [
    ("convoy-seattle-freight-logistics.md", "Convoy-Seattle-Freight-Logistics.pdf",
     "Convoy & the Seattle Freight & Logistics Market"),
    ("uber-eats-india.md", "Uber-Eats-India.pdf",
     "Uber Eats India — A Strategic Teardown"),
    ("convoy-market-reentry.md", "Convoy-Market-Reentry-Analysis.pdf",
     "US Freight Brokerage — Market Re-Entry Analysis"),
]

for md_name, pdf_name, title in DOCS:
    src = ROOT / md_name
    if not src.exists():
        print(f"  … skip (missing): {md_name}")
        continue
    body = md_to_html_body(src.read_text(encoding="utf-8"))
    out = OUT / pdf_name
    render_pdf(wrap(title, body), out)
    print(f"  ✓ {out.relative_to(ROOT)}")
