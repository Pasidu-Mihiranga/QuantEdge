"""Provenance manifest for the raw data snapshot (Step 02).

Each file in `data/raw/` gets one entry recording where it came from, when, and its SHA-256,
so anyone can verify that the numbers were produced from exactly this snapshot.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from quantedge.paths import MANIFEST, RAW


class ManifestError(RuntimeError):
    """Raised when a snapshot file is missing or does not match its recorded hash."""


@dataclass(frozen=True)
class ManifestEntry:
    file: str
    source: str
    url_or_call: str
    downloaded_utc: str
    rows: int
    first_date: str
    last_date: str
    sha256: str
    library_versions: dict[str, str]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_manifest(entries: list[ManifestEntry], path: Path = MANIFEST) -> None:
    payload = {"files": [asdict(e) for e in sorted(entries, key=lambda e: e.file)]}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def read_manifest(path: Path = MANIFEST) -> list[ManifestEntry]:
    if not path.exists():
        raise ManifestError(f"No manifest at {path}. Run `python -m quantedge.data.download --refresh`.")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [ManifestEntry(**e) for e in payload["files"]]


def verify_manifest(path: Path = MANIFEST, raw_dir: Path = RAW) -> list[ManifestEntry]:
    """Recompute every hash; raise `ManifestError` on any missing file or mismatch."""
    entries = read_manifest(path)
    problems = []
    for e in entries:
        f = raw_dir / e.file
        if not f.exists():
            problems.append(f"missing: {e.file}")
        elif sha256_file(f) != e.sha256:
            problems.append(f"hash mismatch: {e.file}")
    if problems:
        raise ManifestError("Snapshot does not match manifest: " + "; ".join(problems))
    return entries
