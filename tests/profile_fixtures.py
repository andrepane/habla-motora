"""Synthetic integration fixtures, never a development/blocked bank evaluation."""
import base64
import hashlib
import json
import sys
from pathlib import Path
from backend.vowel import analyze_vowel
from backend.ddk import analyze_ddk
from backend.phrase import analyze_phrase
from backend.phrase_pauses import analyze_pauses, source_dependencies as pause_dependencies
from backend.phrase_prosody import source_dependencies
from backend.phrase_prosody_routes import execute, configuration
from backend.phrase_candidate_routes import propose, protocol as candidate_protocol
from backend.motor_profile_routes import protocol
from tests.synthetic_pitch import wav_bytes
from tests.synthetic_ddk import signal
from tests.test_phrase import context, review
from tests.test_phrase_candidates_api import activity


def fixtures():
    vowel = wav_bytes()
    ddk = signal(centers=[.25, .5, .75], duration=1)[0]
    phrase = activity()
    original = analyze_ddk(ddk)
    ops = [dict(action='label', id=e['id'], label=['pa', 'ta', 'ka'][i % 3])
           for i, e in enumerate(original['automatic_original']['detection']['events'])]
    reviewed = analyze_ddk(ddk, review=dict(operations=ops, confirmed=True),
                           expected_hash=hashlib.sha256(ddk).hexdigest())
    c = context()
    r = review(phrase, c, word_count=dict(value=14, confirmed=True),
               syllable_count=dict(value=25, confirmed=True))
    seven = analyze_phrase(phrase, c, r, hashlib.sha256(phrase).hexdigest())
    temporal = dict(protocol_version='phrase_pause_review_v1', source_dependencies=pause_dependencies(seven),
                    status='confirmed', reviewed_all=True, note='Synthetic contract fixture, not a clinical observation.',
                    intervals=[dict(id=f'p{i}', start_sample=a*48000, end_sample_exclusive=b*48000,
                                    classification='pause', breath_present='no', within_word=False,
                                    nonarticulatory_confirmed=False, note='Synthetic gap')
                               for i, (a, b) in enumerate([(2, 3), (5, 6)])])
    pauses = analyze_pauses(phrase, c, r, hashlib.sha256(phrase).hexdigest(), temporal)
    cp = candidate_protocol()
    candidates = propose(phrase, c, dict(file_sha256=seven['provenance']['file_sha256'],
                                         context_sha256=seven['provenance']['context_sha256'],
                                         config_sha256=cp['config_sha256'], engine_sha256=cp['engine_sha256']))
    _, deps = source_dependencies(phrase, c, configuration())
    prosody = execute(phrase, c, deps)
    return dict(protocol=protocol(), payloads=dict(vowel=analyze_vowel(vowel, 0, 6), ddk=reviewed,
                ddk_automatic=original, phrase=seven, pauses=pauses, candidates=candidates, prosody=prosody),
                wavs={k:base64.b64encode(v).decode() for k,v in dict(vowel=vowel,ddk=ddk,phrase=phrase).items()})


if __name__ == '__main__':
    Path(sys.argv[1]).write_text(json.dumps(fixtures(), allow_nan=False))
