import hashlib
import json
from pathlib import Path
import subprocess

import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend import praat_runner as runner

FIXTURE = Path(__file__).parent / 'fixtures/tone_2s.wav'


def test_real_praat_duration_and_provenance():
    data = FIXTURE.read_bytes()
    result = runner.analyze_wav(data)
    assert result['temporal']['file_duration_s'] == pytest.approx(2, abs=1/44100)
    p = result['provenance']
    assert p['praat_version'] == '6.4.27'
    assert p['protocol_version'] == 'v1'
    assert p['configuration_version'] == 'experimental_v1'
    assert p['file_sha256'] == hashlib.sha256(data).hexdigest()
    assert p['configuration_sha256'] == hashlib.sha256(runner.CONFIG_PATH.read_bytes()).hexdigest()
    assert result['quality']['f0_coverage']['value'] is None
    assert result['quality']['accepted_cycles']['value'] is None
    assert result['quality']['technical_warnings']
    assert 'acoustic' not in result
    json.dumps(result, allow_nan=False)


def test_real_api():
    with TestClient(app) as client:
        response = client.post('/smoke-test', files={'file': ('tone.wav', FIXTURE.read_bytes(), 'audio/wav')})
    assert response.status_code == 200
    assert response.json()['temporal']['file_duration_s'] == 2


def test_bad_wav():
    with TestClient(app) as client:
        response = client.post('/smoke-test', files={'file': ('bad.wav', b'not a wav', 'audio/wav')})
    assert response.status_code == 422


def test_missing_engine():
    with pytest.raises(runner.AnalysisError):
        runner.analyze_wav(FIXTURE.read_bytes(), '/nonexistent/praat')


def test_version_mismatch(monkeypatch):
    monkeypatch.setattr(runner, '_run', lambda args: 'Praat 0.0.0')
    with pytest.raises(runner.AnalysisError, match='Expected Praat'):
        runner.analyze_wav(FIXTURE.read_bytes())


def test_timeout_has_no_zero_result(monkeypatch):
    def timeout(*args, **kwargs):
        assert kwargs['shell'] is False
        assert kwargs['timeout'] == 15
        raise subprocess.TimeoutExpired(args[0], 15)
    monkeypatch.setattr(runner.subprocess, 'run', timeout)
    with pytest.raises(runner.AnalysisError):
        runner.analyze_wav(FIXTURE.read_bytes())


def test_nonfinite_output(monkeypatch):
    outputs = iter(['Praat 6.4.27', 'nan'])
    monkeypatch.setattr(runner, '_run', lambda args: next(outputs))
    with pytest.raises(runner.AnalysisError, match='disagrees'):
        runner.analyze_wav(FIXTURE.read_bytes())


def test_oversized_upload():
    with TestClient(app) as client:
        response = client.post('/smoke-test', files={'file': ('large.wav', b'x'*(runner.MAX_BYTES+1), 'audio/wav')})
    assert response.status_code == 413
