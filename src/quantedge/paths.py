"""Repository paths, resolved from this file so nothing depends on the working directory."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG_FILE = ROOT / "config.yaml"
DATA = ROOT / "data"
RAW = DATA / "raw"
ARTIFACTS = DATA / "artifacts"
MANIFEST = RAW / "manifest.json"
DECISIONS = ROOT / "doc" / "decisions"
