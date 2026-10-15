import copy
import hashlib
import io
import json
import wave
from fractions import Fraction

import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend import phrase

client = TestClient(app)


from tests.synthetic_phrase import wav


DATA = wav()


def context(**updates):
    c = dict(phrase_id='phrase_es_01_v1', modality='direct_reading_v1', attempt=1,
             selection={'start_sample': 0, 'end_sample_exclusive': 384000},
             selection_confirmed=True, recording_limit_reached=False, administration={})
    c.update(updates)
    return c


def review(data=DATA, c=None, **updates):
    c = c or context()
    r = dict(context_sha256=phrase.analyze_phrase(data, c)['provenance']['context_sha256'],
             confirmed=True, production='present', target_match='exact_once',
             word_count={'value': None, 'confirmed': False},
             syllable_count={'value': None, 'confirmed': False}, events=[], notes='')
    r.update(updates)
    return r


def analyze(r, c=None, data=DATA):
    return phrase.analyze_phrase(data, c or context(), r, hashlib.sha256(data).hexdigest())


def test_frozen_stimulus_counts_are_not_acoustic_inference():
    s = phrase.CONFIG['stimulus']
    assert s['text'] == 'La niña corta papel con tijeras y pega las tiras pequeñas sobre la mesa.'
    assert len(s['text'].split()) == len(s['syllabification']) == s['canonical_words'] == 14
    assert sum(len(w.split('-')) for w in s['syllabification']) == s['canonical_syllables'] == 25
    assert s['cross_word_synalepha'] is False
    # Digital silence still has no inferred production/content/counts.
    r = phrase.analyze_phrase(DATA, context())
    assert all(m['value'] is None for m in r['rates'].values())
    assert r['review'] is None and r['audit']['acoustic_content_inference'] is False


@pytest.mark.parametrize('rate', [44100, 48000])
@pytest.mark.parametrize('bits', [16, 24, 32])
@pytest.mark.parametrize('bounds', [(0, 1001), (101, 350001)])
def test_exact_sample_duration_and_fraction_oracle(rate, bits, bounds):
    data = wav(rate, bits)
    a, b = bounds
    c = context(selection={'start_sample': a, 'end_sample_exclusive': b})
    r = review(data, c)
    actual = analyze(r, c, data)
    duration = Fraction(b-a, rate)
    assert actual['selected_duration_s']['value'] == float(duration)
    assert abs(actual['rates']['reference_word_rate']['value'] - float(60*14/duration)) <= 1e-9
    assert abs(actual['rates']['reference_syllable_rate']['value'] - float(25/duration)) <= 1e-9
    assert actual['provenance']['file_sha256'] == hashlib.sha256(data).hexdigest()
    assert actual['input']['sample_count'] == rate*8


def test_reference_never_fills_reviewed_counts():
    r = analyze(review())
    assert r['rates']['reference_word_rate']['value'] == 105
    assert r['rates']['reference_syllable_rate']['value'] == 3.125
    assert r['rates']['reviewed_word_rate']['value'] is None
    assert r['rates']['reviewed_syllable_rate']['value'] is None
    assert r['review']['word_count']['value'] is None
    assert r['review']['syllable_count']['value'] is None
    assert r['stages']['calculation']['status'] == 'partial'


@pytest.mark.parametrize('kind,other,value', [('word','syllable',14), ('syllable','word',25)])
def test_independent_confirmations(kind, other, value):
    r = review(**{kind+'_count': {'value':value,'confirmed':True}})
    out = analyze(r)
    assert out['rates']['reviewed_'+kind+'_rate']['value'] is not None
    assert out['rates']['reviewed_'+other+'_rate']['value'] is None
    assert out['rates']['reviewed_'+other+'_rate']['reason'] == other+'_count_unconfirmed'


@pytest.mark.parametrize('event,words,syllables', [('omission',13,22), ('repetition',15,27),
    ('substitution',14,25), ('fragment',14,27), ('restart',20,35)])
def test_deviations_include_all_production_and_block_reference(event, words, syllables):
    r = review(target_match='different', word_count={'value':words,'confirmed':True},
               syllable_count={'value':syllables,'confirmed':True},
               events=[{'id':'e1','type':event,'note':'manual annotation'}])
    out = analyze(r)
    assert all(out['rates'][name]['reason']=='target_mismatch' for name in ('reference_word_rate','reference_syllable_rate'))
    assert out['rates']['reviewed_word_rate']['value'] == words*60/8
    assert out['rates']['reviewed_syllable_rate']['value'] == syllables/8
    assert out['selected_duration_s']['value'] == 8


def test_same_counts_different_sequence_does_not_enable_reference():
    r = review(target_match='different', word_count={'value':14,'confirmed':True},
               syllable_count={'value':25,'confirmed':True},
               notes='Same 14 words in a different order')
    out = analyze(r)
    assert out['rates']['reviewed_word_rate']['value'] == 105
    assert out['rates']['reviewed_syllable_rate']['value'] == 3.125
    assert out['rates']['reference_word_rate']['value'] is None
    assert out['rates']['reference_syllable_rate']['value'] is None


@pytest.mark.parametrize('change', ['audio','limits','phrase','modality','attempt','limit'])
def test_stale_review_rejected_after_identity_change(change):
    r = review(); c = context(); data = DATA
    if change == 'audio': data = wav(duration=8.01)
    elif change == 'limits': c['selection']['start_sample'] = 1
    elif change == 'phrase': c['phrase_id'] = 'not_this_phrase'
    elif change == 'modality':
        c['modality']='auditory_model_with_text_v1'
        c['administration']={'model_id':'fixed-model-v1','model_sha256':'a'*64,'model_presented_confirmed':True}
    elif change == 'attempt': c['attempt']=2
    else: c['recording_limit_reached']=True
    with pytest.raises(ValueError):analyze(r,c,data)


@pytest.mark.parametrize('match,reason', [('pending','pending_content_review'),('uncertain','target_match_uncertain'),('different','target_mismatch')])
def test_reference_null_reasons(match,reason):
    out = analyze(review(target_match=match))
    assert out['rates']['reference_word_rate']['reason'] == reason


def test_selection_review_and_calculation_stages_are_independent():
    c = context(selection=None, selection_confirmed=False)
    out = phrase.analyze_phrase(DATA,c)
    assert out['stages']=={'selection':{'status':'not_requested'},'review':{'status':'not_requested'},'calculation':{'status':'blocked'}}
    assert out['selected_duration_s']['value'] is None
    c = context(selection_confirmed=False)
    out = analyze(review(c=c),c)
    assert out['stages']['selection']['status']=='draft'
    assert out['rates']['reference_word_rate']['reason']=='selection_unconfirmed'
    out = analyze(review(confirmed=False,word_count={'value':14,'confirmed':True}))
    assert out['stages']['review']['status']=='draft'
    assert out['rates']['reviewed_word_rate']['value'] is None


def test_null_zero_and_absence_are_distinct():
    r = review(target_match='different',word_count={'value':0,'confirmed':True})
    out = analyze(r)
    assert out['rates']['reviewed_word_rate']['value'] == 0
    assert out['rates']['reviewed_syllable_rate']['value'] is None
    r.update(production='absent',syllable_count={'value':0,'confirmed':True})
    out = analyze(r)
    assert out['review']['word_count']['value']==0
    assert out['selected_duration_s']['value']==8
    assert out['production_duration_s']['value'] is None
    assert all(x['value'] is None and x['reason']=='no_production' for x in out['rates'].values())


def test_limit_truncation_cannot_be_complete_reference_but_reviewed_counts_survive():
    c=context(recording_limit_reached=True)
    out=analyze(review(c=c,word_count={'value':14,'confirmed':True}),c)
    assert out['rates']['reference_word_rate']['reason']=='recording_limit_reached'
    assert out['rates']['reviewed_word_rate']['value']==105


@pytest.mark.parametrize('mode', ['auditory_model_with_text_v1','auditory_model_only_v1'])
def test_models_are_separate_and_auditable(mode):
    c=context(modality=mode,administration={})
    with pytest.raises(ValueError):phrase.analyze_phrase(DATA,c)
    c['administration']={'model_id':'fixed-model-v1','model_sha256':'f'*64,'model_presented_confirmed':True}
    out=phrase.analyze_phrase(DATA,c)
    assert out['context']['modality']==mode
    assert out['context']['administration']['model_sha256']=='f'*64
    assert out['audit']['attempt_aggregation'].startswith('none')


@pytest.mark.parametrize('counts', [(-1,True),(True,True),(1.2,True),(float('nan'),True),(float('inf'),True),(None,True)])
def test_invalid_manual_counts_rejected(counts):
    with pytest.raises(ValueError):analyze(review(word_count={'value':counts[0],'confirmed':counts[1]}))


@pytest.mark.parametrize('selection', [{'start_sample':0,'end_sample_exclusive':0},
    {'start_sample':-1,'end_sample_exclusive':2}, {'start_sample':0,'end_sample_exclusive':384001},
    {'start_sample':True,'end_sample_exclusive':2}, {'start_sample':.5,'end_sample_exclusive':2}])
def test_invalid_selection_rejected(selection):
    with pytest.raises(ValueError):phrase.analyze_phrase(DATA,context(selection=selection))


@pytest.mark.parametrize('bad', [b'bad',DATA[:-2],wav(channels=2),wav(rate=16000),wav(duration=20.001)])
def test_invalid_wav(bad):
    with pytest.raises(ValueError):phrase.analyze_phrase(bad,context())


@pytest.mark.parametrize('bits',[16,24,32])
def test_20_second_file_accepted_without_15_second_ddk_limit(bits):
    data=wav(bits=bits,duration=20)
    out=phrase.analyze_phrase(data,context(selection={'start_sample':0,'end_sample_exclusive':960000}))
    assert out['selected_duration_s']['value']==20
    assert len(data)<=4000000


def test_original_inputs_immutable_and_deterministic():
    c=context();r=review();saved=copy.deepcopy((c,r));data_before=bytes(DATA)
    first=analyze(r,c);second=analyze(r,c)
    assert first==second and (c,r)==saved and DATA==data_before
    assert all(x['value'] is None and x['reason']=='not_implemented' for x in first['out_of_scope'].values())


def test_contradictory_exact_review_and_duplicate_events_rejected():
    with pytest.raises(ValueError):analyze(review(events=[{'id':'e1','type':'omission','note':'x'}]))
    with pytest.raises(ValueError):analyze(review(word_count={'value':13,'confirmed':True}))
    with pytest.raises(ValueError):analyze(review(target_match='different',events=[{'id':'e1','type':'restart','note':''}]*2))


def post(c=None,r=None,data=DATA,**fields):
    fields['context_json']=json.dumps(c or context())
    if r is not None:
        fields['review_json']=json.dumps(r)
        fields.setdefault('expected_file_sha256',hashlib.sha256(data).hexdigest())
    return client.post('/phrase-analysis',files={'file':('test.wav',data)},data=fields)


def test_http_real_flow_export_payload_and_independent_attempts():
    result=post();assert result.status_code==200
    assert result.json()['rates']['reference_word_rate']['value'] is None
    r=review(word_count={'value':14,'confirmed':True},syllable_count={'value':25,'confirmed':True})
    out=post(r=r);assert out.status_code==200
    assert out.json()['stages']['calculation']['status']=='completed'
    assert post(context(attempt=2),r).status_code==422
    assert post(r=r,expected_file_sha256='wrong').status_code==422
    for path in ['/phrase','/phrase-protocol','/static/phrase.js','/static/phrase.css','/static/phrase-recorder.js']:
        assert client.get(path).status_code==200


def test_http_validation_and_unexpected_failures(monkeypatch):
    assert post(data=b'x'*4000001).status_code==413
    assert post(data=b'bad').status_code==422
    assert client.post('/phrase-analysis',files={'file':('x.wav',DATA)},data={'context_json':'not json'}).status_code==422
    assert client.post('/phrase-analysis',files={'file':('x.wav',DATA)},data={'context_json':json.dumps(context()),'review_json':'null'}).status_code==422
    def fail(*args,**kw):raise RuntimeError('private details')
    monkeypatch.setattr('backend.phrase_routes.analyze_phrase',fail)
    out=post();assert out.status_code==503 and 'private details' not in out.text

@pytest.mark.parametrize('offset,value,size', [(4,100,4),(22,2,2),(28,1,4),(32,1,2),(34,12,2),(40,767999,4)])
def test_pcm_header_integrity(offset,value,size):
    damaged=bytearray(DATA);damaged[offset:offset+size]=value.to_bytes(size,'little')
    with pytest.raises(ValueError):phrase.read_wav(bytes(damaged))
