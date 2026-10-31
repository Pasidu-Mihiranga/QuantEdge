"""Execute every notebook in notebooks/ top to bottom and save the outputs (gap G16).

    python scripts/run_notebooks.py            # all notebooks
    python scripts/run_notebooks.py 01 03      # only notebooks whose names start with these prefixes

Exits with status 1 if any cell raises, so a notebook that does not run end to end is caught.
Needs requirements-notebooks.txt.
"""

from __future__ import annotations

import sys
from pathlib import Path

import nbformat
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError

NOTEBOOKS = Path(__file__).resolve().parents[1] / "notebooks"


def main(prefixes: list[str]) -> int:
    paths = sorted(p for p in NOTEBOOKS.glob("*.ipynb") if not prefixes or p.name.startswith(tuple(prefixes)))
    failed = []
    for path in paths:
        nb = nbformat.read(path, as_version=4)
        try:
            NotebookClient(nb, timeout=900, kernel_name="python3",
                           resources={"metadata": {"path": str(NOTEBOOKS)}}).execute()
        except CellExecutionError as err:
            failed.append(path.name)
            print(f"FAILED  {path.name}\n{str(err).splitlines()[-1]}")
            continue
        nbformat.write(nb, path)
        print(f"ok      {path.name}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
