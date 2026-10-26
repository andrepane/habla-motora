"""Keep the H10.3 baseline; allow only the five authorized H10.4A adapters."""
import hashlib
import json
from pathlib import Path


def test_visual_phase_preserves_protected_sources():
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / 'tests/visual-protected-sources.json').read_text())
    adapters = json.loads((root / 'tests/continuity-adapter-sources.json').read_text())
    allowed = {entry['path']: entry for entry in adapters['files']}
    assert set(allowed) == {'frontend/app.js', 'frontend/ddk.js', 'frontend/phrase.js', 'frontend/profile-bridge.js', 'frontend/saved-task-view.js'}
    presentation = json.loads((root / 'tests/usability-presentation-sources.json').read_text())
    display = {e['path']: e for e in presentation['files']}
    assert set(display) == {'frontend/saved-task-view.js', 'frontend/motor-profile-ui.js', 'frontend/evaluation-ui.js'}
    for entry in manifest['files']:
        expected = entry['sha256']
        if entry['path'] in allowed:
            assert allowed[entry['path']]['baseline_sha256'] == expected
            expected = allowed[entry['path']]['sha256']
        if entry['path'] in display:
            assert display[entry['path']]['baseline_sha256'] == expected
            expected = display[entry['path']]['sha256']
        actual = hashlib.sha256((root / entry['path']).read_bytes()).hexdigest()
        assert actual == expected, entry['path']
