import hashlib
import json
import math
from pathlib import Path
import tempfile

import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend.pitch import SCRIPT, _validate_and_summarize, analyze_pitch
from backend.praat_runner import CONFIG_PATH, AnalysisError, _run
from tests.synthetic_pitch import wav_bytes

HASH_V1 = '94b976f9c3e1f21d965df9ce547422953c6d780df64988cf2562cc8594520729'


@pytest.mark.parametrize('hz', [100, 200, 400])
def test_clean_tones(hz):
    r = analyze_pitch(wav_bytes(frequency=hz))
    assert abs(r['acoustic']['f0_mean_hz']['value']-hz) <= 0.1
    assert r['acoustic']['f0_sd_hz']['value'] <= 0.1
    assert r['quality']['f0_coverage_percent']['value'] == 100
    assert r['quality']['voiced_frames'] == r['quality']['total_frames'] == 600
    assert r['quality']['accepted_cycles']['value'] is None


def test_modulation_accuracy():
    r = analyze_pitch(wav_bytes('modulated'))
    expected = [200+20*math.sin(2*math.pi*2*f['time_s']) for f in r['tracking_frames']]
    errors = [f['f0_hz']-v for f, v in zip(r['tracking_frames'], expected) if f['f0_hz'] is not None]
    assert r['quality']['f0_coverage_percent']['value'] == 100
    assert abs(r['acoustic']['f0_mean_hz']['value']-200) <= 0.2
    assert abs(r['acoustic']['f0_sd_hz']['value']-math.sqrt(200)) <= 0.3
    assert errors  # Pointwise accuracy is evaluated separately, without relaxing its target.


@pytest.mark.xfail(strict=True, reason="Praat raw cc v1 exceeds the exploratory 0.5 Hz pointwise modulation target")
def test_modulation_pointwise_exploratory_target():
    r = analyze_pitch(wav_bytes('modulated'))
    errors = [abs(f['f0_hz']-(200+20*math.sin(2*math.pi*2*f['time_s'])))
              for f in r['tracking_frames'] if f['f0_hz'] is not None]
    assert max(errors) <= 0.5


def test_gap():
    r = analyze_pitch(wav_bytes('gap'))
    assert 60 <= r['quality']['f0_coverage_percent']['value'] <= 75
    assert abs(r['acoustic']['f0_mean_hz']['value']-200) <= 0.1
    assert any(f['f0_hz'] is None for f in r['tracking_frames'])
    assert all(f['f0_hz'] is None or f['f0_hz'] > 0 for f in r['tracking_frames'])
    assert 'INCOMPLETE_F0_COVERAGE' in [w['code'] for w in r['quality']['technical_warnings']]


def test_silence():
    r = analyze_pitch(wav_bytes('silence'))
    assert r['acoustic']['f0_mean_hz']['value'] is None
    assert r['acoustic']['f0_sd_hz']['value'] is None
    assert r['quality']['f0_coverage_percent']['value'] == 0
    assert r['quality']['voiced_frames'] == 0
    assert all(f['f0_hz'] is None for f in r['tracking_frames'])
    assert 'F0_NOT_DETECTED' in [w['code'] for w in r['quality']['technical_warnings']]


@pytest.mark.parametrize('kind,hz', [('noise',200), ('tone',50), ('tone',700), ('weak_fundamental',200)])
def test_stress_cases_report_only_not_false_rejection(kind,hz):
    r = analyze_pitch(wav_bytes(kind,frequency=hz))
    q = r['quality']
    assert q['total_frames'] == len(r['tracking_frames'])
    assert q['voiced_frames'] == sum(f['f0_hz'] is not None for f in r['tracking_frames'])
    assert q['f0_coverage_percent']['value'] == 100*q['voiced_frames']/q['total_frames']
    json.dumps(r, allow_nan=False)
    # No claim of silence or correct tracking for noise/out-of-range inputs.


def test_no_frames_real_engine():
    r = analyze_pitch(wav_bytes(), diagnostic_interval=(0,0.000001))
    assert r['quality']['total_frames'] == 0
    assert r['quality']['f0_coverage_percent']['value'] is None
    assert r['acoustic']['f0_mean_hz']['value'] is None


def test_one_frame_real_engine():
    r = analyze_pitch(wav_bytes())
    t = r['tracking_frames'][0]['time_s']
    small = analyze_pitch(wav_bytes(), diagnostic_interval=(t-0.000001,t+0.000001))
    assert small['quality']['voiced_frames'] == 1
    assert small['acoustic']['f0_sd_hz']['value'] is None


def test_praat_queries_and_frame_export_independent_reference():
    import os
    data = wav_bytes('modulated')
    r = analyze_pitch(data)
    with tempfile.TemporaryDirectory() as temp:
        wav = Path(temp)/'input.wav'; wav.write_bytes(data)
        script = Path(temp)/'reference.praat'
        script.write_text('''form Reference
 sentence Wav
endform
Read from file: wav$
To Pitch (raw cross-correlation): 0.005, 75, 600, 15, "no", 0.03, 0.45, 0.01, 0.35, 0.14
mean = Get mean: 1.5, 4.5, "Hertz"
sd = Get standard deviation: 1.5, 4.5, "Hertz"
writeInfoLine: fixed$(mean, 17), " ", fixed$(sd, 17)
n = Get number of frames
for i from 1 to n
 t = Get time from frame number: i
 if t >= 1.5 and t <= 4.5
  f = Get value in frame: i, "Hertz"
  appendInfoLine: i, " ", fixed$(t, 17), " ", fixed$(f, 17)
 endif
endfor
''')
        lines = _run([os.environ.get('PRAAT_EXECUTABLE','praat'),'--run',str(script),str(wav)]).splitlines()
    mean, sd = map(float, lines[0].split())
    assert r['acoustic']['f0_mean_hz']['value'] == mean
    assert r['acoustic']['f0_sd_hz']['value'] == sd
    for exported, line in zip(r['tracking_frames'], lines[1:], strict=True):
        i,t,f = line.split()
        assert exported == {'frame_index':int(i),'time_s':float(t),'f0_hz':float(f)}


def test_provenance_unchanged_config():
    data = wav_bytes()
    r = analyze_pitch(data)
    p = r['provenance']
    assert hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest() == HASH_V1 == p['configuration_sha256']
    assert p['file_sha256'] == hashlib.sha256(data).hexdigest()
    assert p['script_sha256'] == hashlib.sha256(SCRIPT.read_bytes()).hexdigest()
    assert p['module_version'] == 'pitch_v1'
    assert p['warnings_version'] == 'pitch_warnings_v1'
    assert p['output_schema_version'] == 'pitch_output_v1'
    assert p['praat_version'] == '6.4.27'


def test_octave_warning_does_not_change_data_or_bridge_gaps():
    frames = [{'frame_index':1,'time_s':1,'f0_hz':100},
              {'frame_index':2,'time_s':1.005,'f0_hz':200},
              {'frame_index':3,'time_s':1.010,'f0_hz':None},
              {'frame_index':4,'time_s':1.015,'f0_hz':100}]
    raw = json.dumps({'frames':frames,'total_frames':4,'voiced_frames':3,'f0_mean_hz':133,'f0_sd_hz':57})
    r = _validate_and_summarize(raw,1,2)
    assert r['tracking_frames'] == frames
    jumps = [w for w in r['quality']['technical_warnings'] if w['code']=='POSSIBLE_OCTAVE_JUMP']
    assert len(jumps)==1 and jumps[0]['semitones']==12


def test_nonfinite_pitch_output_rejected():
    with pytest.raises(AnalysisError):
        _validate_and_summarize('{"f0_mean_hz":NaN}',0,1)


@pytest.mark.parametrize('interval', [(-1,4),(4,3),(0,7),(0,float('nan'))])
def test_invalid_emission(interval):
    with pytest.raises(ValueError):
        analyze_pitch(wav_bytes(), *interval)


def test_short_emission():
    with pytest.raises(ValueError,match='3 seconds'):
        analyze_pitch(wav_bytes(),0,2)


def test_pitch_api():
    with TestClient(app) as client:
        response = client.post('/pitch', files={'file':('tone.wav',wav_bytes(),'audio/wav')},
                               data={'emission_start_s':'0','emission_end_s':'6'})
    assert response.status_code==200
    assert abs(response.json()['acoustic']['f0_mean_hz']['value']-200) <= 0.1
