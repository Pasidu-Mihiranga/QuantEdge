"""Print the report, memo and tear sheet to PDF with headless Chrome (needs Google Chrome or Chromium).

    python scripts/build_pdfs.py
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from quantedge.config import load_config
from quantedge.paths import ARTIFACTS, ROOT
from quantedge.reports import final, report

REPORTS = ROOT / "reports"
PDFS = {"report.html": "QuantEdge_Technical_Report.pdf", "memo.html": "Investment_Committee_Memo.pdf",
        "tearsheet.html": "Executive_Tear_Sheet.pdf"}


def chrome() -> str:
    mac = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    found = next((c for c in (os.environ.get("CHROME"), shutil.which("google-chrome"), shutil.which("chromium"), mac)
                  if c and Path(c).exists()), None)
    if found is None:
        raise SystemExit("Chrome not found: set CHROME to its path")
    return found


def pages(pdf: Path) -> int:
    return len(re.findall(rb"/Type\s*/Page\b(?!s)", pdf.read_bytes()))


def main() -> None:
    n = json.loads((ARTIFACTS / "decision_numbers.json").read_text(encoding="utf-8"))
    (REPORTS / "memo.html").write_text(final.memo_page(n), encoding="utf-8")
    (REPORTS / "tearsheet.html").write_text(final.tear_sheet(n), encoding="utf-8")
    (REPORTS / "report.html").write_text(report.render(load_config()), encoding="utf-8")
    for source, name in PDFS.items():
        out = REPORTS / name
        subprocess.run([chrome(), "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={out}",
                        (REPORTS / source).as_uri()], check=True, capture_output=True, timeout=120)
        print(f"{name}: {pages(out)} pages, {out.stat().st_size / 1e3:.0f} KB")


if __name__ == "__main__":
    main()
