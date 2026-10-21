"""H10.3 is presentation-only; protect all clinical and orchestration code."""
import hashlib
import json
from pathlib import Path


def test_visual_phase_preserves_protected_sources():
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / 'tests/visual-protected-sources.json').read_text())
    for entry in manifest['files']:
        actual = hashlib.sha256((root / entry['path']).read_bytes()).hexdigest()
        assert actual == entry['sha256'], entry['path']
