"""phrase_prosody_v1: offline technical API, deliberately no HTTP route or UI."""
import copy
import io
import json
import os
from pathlib import Path
import subprocess
import wave
import numpy as np
from backend.phrase import analyze_phrase,canonical,digest
from research.prosody.engine import extract_many,summarize,executable_identity,HERE

MODULE_VERSION='phrase_prosody_v1'

def empty_metrics(reason):
    names=['f0_mean_hz','f0_median_hz','f0_sd_hz','f0_sd_st','p10_hz','p90_hz','f0_min_hz','f0_max_hz','raw_range_hz','robust_range_hz','robust_range_st','slope_st_s','coverage_percent','selection_duration_s']
    return {k:dict(value=None,reason=reason) for k in names}



def source_dependencies(data,context,configuration):
    source=analyze_phrase(data,context)
    engine_hash=digest(Path(__file__).read_bytes()+b''.join((HERE/p).read_bytes() for p in ['engine.py','extract.praat','statistics.praat']))
    return source,dict(file_sha256=source['provenance']['file_sha256'],context_sha256=source['provenance']['context_sha256'],
                       selection_sha256=digest(canonical(source['context']['selection'])),config_sha256=digest(canonical(configuration)),engine_sha256=engine_hash)


def analyze_prosody(data,context,*,expected_dependencies=None,configuration=None,executable=None):
    if configuration is None:configuration=json.loads((HERE/'freeze.json').read_text())
    source,deps=source_dependencies(data,context,configuration)
    result=dict(schema_version='phrase_prosody_output_v1',protocol_version=MODULE_VERSION,dependencies=deps,context=source['context'],configuration=configuration,
                status='not_evaluable',reason=None,metrics=empty_metrics('not_evaluated'),frames=None,warnings=[])
    if expected_dependencies is not None and expected_dependencies!=deps:return {**result,'status':'stale','reason':'dependency_mismatch','metrics':empty_metrics('dependency_mismatch')}
    if not context.get('selection_confirmed') or context.get('selection') is None:return {**result,'reason':'selection_unconfirmed','metrics':empty_metrics('selection_unconfirmed')}
    selection=context['selection'];rate=source['input']['sample_rate_hz'];p=configuration['profile']
    if (selection['end_sample_exclusive']-selection['start_sample'])/rate<3/p['floor_hz']:
        return {**result,'reason':'insufficient_analysis_duration','metrics':empty_metrics('insufficient_analysis_duration')}
    executable=executable or os.environ.get('PRAAT_EXECUTABLE','praat')
    try:
        runtime=executable_identity(executable)
        record=next(iter(extract_many(data,selection,[p],[configuration['context_s']],executable).values()))
        summary=summarize(record,selection,rate,configuration['range_rule'],configuration['jump_limit_s'])
        # Digital rail evidence, not an assertion of analogue clipping.
        with wave.open(io.BytesIO(data),'rb') as w:raw=w.readframes(w.getnframes());bits=w.getsampwidth()*8
        if bits==24:
            v=np.frombuffer(raw,dtype=np.uint8).reshape(-1,3).astype(np.int64);samples=v[:,0]+(v[:,1]<<8)+(v[:,2]<<16);samples=np.where(samples>=2**23,samples-2**24,samples)
        else:samples=np.frombuffer(raw,dtype='<i2' if bits==16 else '<i4')
        x=samples[selection['start_sample']:selection['end_sample_exclusive']];rail=int(np.sum((x==-(2**(bits-1)))|(x==2**(bits-1)-1)))
        if rail:summary['warnings'].append(dict(code='POSSIBLE_DIGITAL_CLIPPING',rail_samples=rail))
        run_id=digest(canonical(dict(dependencies=deps,runtime=runtime)))
        return {**result,**summary,'frames':record['frames'],'native_audit':record['native'],'runtime':runtime,'run_id':run_id,
                'grid':record['grid'],'acoustic_interval':record['acoustic_interval'],'original_pitch_sha256':record['original_pitch_sha256'],'restricted_pitch_sha256':record['restricted_pitch_sha256'],
                'validation':'technical_only_human_validity_pending'}
    except (OSError,ValueError,subprocess.SubprocessError):
        return {**result,'status':'failed','reason':'pitch_execution_failed','metrics':empty_metrics('pitch_execution_failed')}


class ProsodyHistory:
    """Dependency-bound snapshots; prior runs never overwritten or silently reused."""
    def __init__(self):self.current=None;self.history=[]
    def accept(self,result):
        if self.current is not None:self.history.append(copy.deepcopy(self.current))
        self.current=copy.deepcopy(result)
    def invalidate(self,dependencies):
        if self.current is not None and dependencies!=self.current['dependencies']:
            self.history.append(copy.deepcopy(self.current));self.current={**copy.deepcopy(self.current),'status':'stale','reason':'dependency_changed','metrics':empty_metrics('dependency_changed'),'frames':None}
