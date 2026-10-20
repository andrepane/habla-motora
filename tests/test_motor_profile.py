import hashlib
from pathlib import Path
from fastapi.testclient import TestClient
from backend.app import app
from backend.motor_profile_routes import protocol, ROOT

client = TestClient(app)


def test_page_and_identity_are_metadata_only(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('Profile must not invoke acoustic analysis')
    from backend import vowel, ddk, phrase, phrase_pauses, phrase_prosody
    for module, name in [(vowel, 'analyze_vowel'), (ddk, 'analyze_ddk'),
                         (phrase, 'analyze_phrase'), (phrase_pauses, 'analyze_pauses'),
                         (phrase_prosody, 'analyze_prosody')]:
        monkeypatch.setattr(module, name, forbidden)
    assert client.get('/profile').status_code == 200
    r = client.get('/motor-profile-protocol')
    assert r.status_code == 200 and r.json()['acoustic_execution'] is False
    assert set(r.json()['sources']) == {'vowel', 'ddk', 'phrase', 'pauses', 'candidates', 'prosody'}


def test_identity_corresponds_to_unchanged_source_files():
    p = protocol()
    checks = p['sources']['ddk']['checks']
    assert checks[1]['value'] == hashlib.sha256((ROOT/'backend/ddk.py').read_bytes()).hexdigest()
    assert p['sources']['prosody']['checks'][-1]['value'] == 'filtered_800_03__0'
    assert hashlib.sha256((ROOT/'research/prosody/freeze.json').read_bytes()).hexdigest() == '047fac7379b09dfae0f545569e21ec34463ab7227255507ceeba68f8c6b6a24c'


def test_projector_has_no_acoustic_dependencies_or_network_execution():
    s = (ROOT/'frontend/motor-profile.js').read_text()
    assert 'import ' not in s
    assert 'fetch(' not in s and 'subprocess' not in s
    assert 'quantile(' not in s and 'log2(' not in s


def test_all_profile_modules_served_and_existing_routes_preserved():
    for path in ['motor-profile.js', 'motor-profile-store.js', 'motor-profile-ui.js', 'profile-bridge.js']:
        assert client.get('/static/'+path).status_code == 200
    for path in ['/', '/ddk', '/phrase', '/health', '/phrase-protocol', '/phrase-pause-protocol', '/phrase-candidate-protocol', '/phrase-prosody-protocol']:
        assert client.get(path).status_code == 200
