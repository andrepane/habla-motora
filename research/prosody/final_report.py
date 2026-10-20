"""Post-freeze descriptive reporting only; never extracts audio or selects a profile.

All acceptance decisions come from the unchanged frozen assessor. Supplemental
pooled cents errors compare saved traces with the declared synthetic trajectory.
"""
import gzip
import json
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np
from backend.phrase import canonical, digest
from reports.prosody.assess import CLEAN
from .bank import trajectory
from .run import code_hash

ROOT = Path('reports/prosody')


def read_rows(split, ident):
    with gzip.open(ROOT/split/'results.jsonl.gz', 'rt') as f:
        return [r for line in f if (r := json.loads(line))['configuration_id'] == ident]


def describe(values):
    x = np.asarray([float(v) for v in values if v is not None], dtype=float)
    if not len(x):
        return dict(n=0, median=None, p95=None, minimum=None, maximum=None)
    return dict(n=len(x), median=float(np.median(x)), p95=float(np.percentile(x, 95)),
                minimum=float(np.min(x)), maximum=float(np.max(x)))


def primary(row):
    c = row['case']
    return c['family'] in CLEAN and 55 <= c['frequency'] <= 600


def make_report():
    freeze_raw = Path('research/prosody/freeze.json').read_bytes()
    freeze = json.loads(freeze_raw)
    assert freeze['code_sha256'] == code_hash()
    assert freeze['assessment_sha256'] == digest((ROOT/'assess.py').read_bytes())
    assert freeze['module_sha256'] == digest(Path('backend/phrase_prosody.py').read_bytes())
    assert freeze['development_results_sha256'] == digest((ROOT/'development/results.jsonl.gz').read_bytes())
    proof = json.loads((ROOT/'blocked/integrity.json').read_text())
    assert proof['all_frozen_hashes_match'] and proof['first_run_complete']
    assert proof['blocked_results_sha256'] == digest((ROOT/'blocked/results.jsonl.gz').read_bytes())
    assert proof['freeze_file_sha256'] == digest(freeze_raw)
    ident = freeze['selected_configuration_id']
    samples = {s: read_rows(s, ident) for s in ('development', 'blocked')}
    assert all(len(rs) == 450 for rs in samples.values())
    errors = {}
    for split, rows in samples.items():
        traces = np.load(ROOT/split/f'traces-{ident}.npz')
        for row in rows:
            c = row['case']; saved = traces[c['case_id']]
            t = saved[:, 0] - row['selection']['start_sample']/c['rate']
            reference, periodic = trajectory(c, t)
            defined = np.isfinite(saved[:, 1]); both = periodic & defined
            # Supplemental description only; no acceptance threshold is applied here.
            errors[c['case_id']] = np.abs(1200*np.log2(saved[both, 1]/reference[both]))

    def summarize(rows):
        fields = rows[0]['metrics'].keys()
        pooled = np.concatenate([errors[r['case']['case_id']] for r in rows])
        total = sum(r['summary']['counts']['total'] for r in rows)
        defined = sum(r['summary']['counts']['defined'] for r in rows)
        rules = [r['support_comparison'][freeze['range_rule']['id']] for r in rows]
        warnings = Counter(w['code'] for r in rows for w in r['summary']['warnings'])
        transitions = [t for r in rows for t in r['summary']['transitions']]
        return dict(cases=len(rows), metrics={key: describe(r['metrics'][key] for r in rows) for key in fields},
                    native={key: describe(r['native'][key] for r in rows) for key in rows[0]['native']},
                    pooled_absolute_cents=describe(pooled), existing_frames=total, defined_frames=defined,
                    pooled_frame_coverage_percent=100*defined/total if total else None,
                    octave_error_frames=sum(r['metrics']['octave_error_frames'] for r in rows),
                    gross_error_frames=sum(r['metrics']['gross_error_frames'] for r in rows),
                    range_published_cases=sum(s['eligible'] and r['native']['p10_hz'] is not None and r['native']['p90_hz'] is not None for s,r in zip(rules,rows)),
                    slope_published_cases=sum(r['metrics']['slope_published'] for r in rows),
                    warnings=dict(warnings), transitions_over_6st=len(transitions),
                    short_transitions=sum(t['delta_t_s'] <= freeze['jump_limit_s']+1e-12 for t in transitions),
                    transitions_after_longer_interval=sum(t['delta_t_s'] > freeze['jump_limit_s']+1e-12 for t in transitions),
                    trace_files=[f"{r['case']['case_id']}" for r in rows])

    comparison = dict(configuration=ident, frozen_commit=proof['freeze_commit'],
                      freeze_sha256=digest(freeze_raw), human_validation='pending',
                      pooled_error_definition='Absolute cents on saved defined frames with synthetic periodic truth; whole-track, no transition guard. Repeated formats and overlapping frames are not independent observations.',
                      case_statistic_definition='Median/P95/min/max of per-case metrics are descriptive between-case distributions, never pooled-frame quantiles.',
                      splits={})
    for split, rows in samples.items():
        families = defaultdict(list); formats = defaultdict(list); constants = defaultdict(list)
        noises = defaultdict(list); gaps = defaultdict(list)
        for r in rows:
            c = r['case']; families[c['family']].append(r)
            if primary(r): formats[f"{c['rate']}-PCM{c['bits']}"].append(r)
            if c['family'] == 'constant': constants[f"{c['frequency']:g}"].append(r)
            if c['family'] == 'noise': noises[f"{c['snr_db']:g}dB-{c['frequency']:g}Hz"].append(r)
            if c['family'] == 'gap': gaps[f"{c['gap']:g}s"].append(r)
        comparison['splits'][split] = dict(
            manifest=json.loads((ROOT/split/'manifest.json').read_text()),
            all_conditions=summarize(rows), primary_clean=summarize([r for r in rows if primary(r)]),
            by_family={k:summarize(v) for k,v in sorted(families.items())},
            primary_by_format={k:summarize(v) for k,v in sorted(formats.items())},
            constants={k:summarize(v) for k,v in sorted(constants.items(), key=lambda kv:float(kv[0]))},
            noise={k:summarize(v) for k,v in sorted(noises.items())},
            gaps={k:summarize(v) for k,v in sorted(gaps.items())})
    development_acceptance = json.loads((ROOT/'eligibility_v2'/f'{ident}.json').read_text())
    blocked_acceptance = json.loads((ROOT/'blocked/acceptance.json').read_text())
    comparison['acceptance'] = dict(development=development_acceptance, blocked=blocked_acceptance)
    (ROOT/'blocked/development_comparison.json').write_bytes(canonical(comparison)+b'\n')
    render_markdown(comparison, freeze)
    return comparison


def render_markdown(data, freeze):
    def fmt(v): return 'null' if v is None else f'{v:.6g}'
    def metric(g,k,stat='median'): return fmt(g['metrics'][k][stat])
    lines = ['# Hito 8A — Prosodia v1: evaluación técnica final', '',
             f"Configuración `{data['configuration']}`, congelación `phrase_prosody_freeze_v2`, commit `{data['frozen_commit']}`. "
             'No se ha reseleccionado ni ajustado ningún parámetro después del bloqueado. Las congelaciones v1/v2 y la corrección de elegibilidad permanecen auditables.', '',
             '## Qué se ha validado', '',
             'Verdad sintética: trayectorias de F0, periodicidad y huecos definidos por recetas deterministas, no habla humana. '
             'Desarrollo: 450 WAV × 14 alternativas, ya persistidos; esta comparación usa únicamente la alternativa congelada. '
             'Bloqueado: una primera ejecución completa, 450 WAV × una alternativa, sin iteración. Cambia fase, semilla, '
             'frecuencia base ×1,037 y pendiente log-lineal ×0,93. Comparte familias con desarrollo; no representa una población independiente.', '',
             'Concordancia Praat: 75/75 comprobaciones en el bloqueado y 75/75 para esta alternativa en desarrollo '
             '(1.050/1.050 para las 14 alternativas originales). Un segundo script/proceso consulta estadísticas nativas '
             'sobre un Pitch reconstruido a partir de centros seleccionados. Tolerancia ≤1e-9. Es concordancia de integración, '
             'no un estimador acústico independiente. Los tests adicionales de concordancia cubren ambos muestreos y los tres PCM.', '',
             '**Validación humana y validez clínica: pendientes.** No se han usado WAV humanos ni emitido interpretaciones clínicas.', '',
             '## Aceptación congelada', '', '| Criterio | Desarrollo aprobados/total | Bloqueado aprobados/total |', '|---|---:|---:|']
    for name,b in data['acceptance']['blocked']['criteria'].items():
        d=data['acceptance']['development']['criteria'][name]
        lines.append(f"| {name} | {d['passed']}/{d['total']} | {b['passed']}/{b['total']} |")
    lines += ['', f"Aceptación global bloqueada: **{data['acceptance']['blocked']['all_passed']}**. "
              'Los fallos, si existen, se conservan sin retocar criterios. La aceptación solo cubre las condiciones predeclaradas; '
              'la caracterización incluye condiciones adicionales que pueden fallar sin alterar esta decisión.', '',
              '## Error y cobertura en controles principales limpios', '',
              '168 casos por split. Cents de la tabla: todos los frames definidos con verdad periódica, incluidos transitorios. '
              'El P95 core máximo es el peor P95 por caso tras la guarda predeclarada de transiciones. '
              'La cobertura se calcula sobre centros existentes, no sobre toda la duración del audio.', '',
              '| Split | Mediana cents agrupada | P95 cents agrupado | Máximo P95 core cents | Octavas frames | Cobertura agrupada % | Máximo error P10 Hz | Máximo error P90 Hz | Máximo error rango ST | Máximo error pendiente ST/s |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    def main_row(name,g):
        return f"| {name} | {fmt(g['pooled_absolute_cents']['median'])} | {fmt(g['pooled_absolute_cents']['p95'])} | {metric(g,'core_p95_abs_cents','maximum')} | {g['octave_error_frames']} | {fmt(g['pooled_frame_coverage_percent'])} | {metric(g,'p10_abs_error_hz','maximum')} | {metric(g,'p90_abs_error_hz','maximum')} | {metric(g,'robust_range_abs_error_st','maximum')} | {metric(g,'slope_abs_error_st_s','maximum')} |"
    for split in ('development','blocked'):lines.append(main_row(split,data['splits'][split]['primary_clean']))
    lines += ['', 'No se interpreta el número de frames solapados ni los formatos repetidos como muestras independientes. '
              'Los cuantiles Hz proceden de Praat; el rango robusto ST es 12·log2(P90/P10); la pendiente es OLS sobre tiempos reales de frames definidos. '
              'Los cuantiles/rango publicados exigen soporte distributed, y la pendiente su soporte temporal congelado. '
              'Valores nativos brutos y errores permanecen en la auditoría incluso si la publicación es null.', '',
              '## Bloqueado por familia', '',
              '| Familia | Casos | Mediana cents agrupada | P95 cents agrupado | Octavas frames | Cobertura mediana % | Máx error P10 Hz | Máx error P90 Hz | Máx error rango ST | Máx error pendiente ST/s |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for name,g in data['splits']['blocked']['by_family'].items():
        lines.append(f"| {name} | {g['cases']} | {fmt(g['pooled_absolute_cents']['median'])} | {fmt(g['pooled_absolute_cents']['p95'])} | {g['octave_error_frames']} | {metric(g,'coverage_percent')} | {metric(g,'p10_abs_error_hz','maximum')} | {metric(g,'p90_abs_error_hz','maximum')} | {metric(g,'robust_range_abs_error_st','maximum')} | {metric(g,'slope_abs_error_st_s','maximum')} |")
    lines += ['', 'Las familias constant/noise incluyen condiciones fuera de aceptación: 45/750/950 Hz nominales, '
              'ruido intenso y armónicos ambiguos son caracterización. No se ocultan ni se mezclan con los controles principales.', '',
              '## Graves/agudos: constantes bloqueadas', '',
              '| F0 nominal Hz | F0 sintética Hz | Mediana cents | P95 cents | Octavas frames | Cobertura mínima % | P10 nativo mediano Hz | P90 nativo mediano Hz |',
              '|---:|---:|---:|---:|---:|---:|---:|---:|']
    for nominal,g in data['splits']['blocked']['constants'].items():
        lines.append(f"| {nominal} | {float(nominal)*1.037:.6g} | {fmt(g['pooled_absolute_cents']['median'])} | {fmt(g['pooled_absolute_cents']['p95'])} | {g['octave_error_frames']} | {metric(g,'coverage_percent','minimum')} | {fmt(g['native']['p10_hz']['median'])} | {fmt(g['native']['p90_hz']['median'])} |")
    lines += ['', '## Muestreo y PCM: controles principales bloqueados', '',
              '| Formato | Mediana cents | P95 cents | Máximo P95 core cents | Octavas frames | Cobertura % | Máx error P10 Hz | Máx error P90 Hz | Máx error rango ST | Máx error pendiente ST/s |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for name,g in data['splits']['blocked']['primary_by_format'].items():lines.append(main_row(name,g))
    lines += ['', 'Los JSON de comparación conservan también el desglose por formato en desarrollo. '
              'Los resultados por caso identifican cualquier diferencia entre 44,1/48 kHz y PCM16/24/32.', '',
              '## Huecos bloqueados', '',
              '| Hueco sintético s | Casos | Referencias por caso | Coincidencias mediana | Error mediano inicio s | Error mediano final s | IoU mediano |',
              '|---:|---:|---:|---:|---:|---:|---:|']
    for name,g in data['splits']['blocked']['gaps'].items():
        lines.append(f"| {name} | {g['cases']} | {metric(g,'gap_reference_count')} | {metric(g,'gap_matched_count')} | {metric(g,'gap_start_abs_error_s')} | {metric(g,'gap_end_abs_error_s')} | {metric(g,'gap_mask_iou')} |")
    lines += ['', 'La aceptación de recuperación/bordes solo se aplica a huecos ≥500 ms. '
              'Los huecos menores se caracterizan sin extrapolar validez de detección de pausas lingüísticas.', '',
              '## Ruido bloqueado', '',
              '| Condición nominal | Mediana cents | P95 cents | Cobertura mínima % |', '|---|---:|---:|---:|']
    for name,g in data['splits']['blocked']['noise'].items():
        lines.append(f"| {name} | {fmt(g['pooled_absolute_cents']['median'])} | {fmt(g['pooled_absolute_cents']['p95'])} | {metric(g,'coverage_percent','minimum')} |")
    lines += ['', 'Solo SNR=20 dB tiene los criterios congelados de mediana ≤50 cents y pérdida de cobertura ≤10 puntos. '
              'El resto se conserva como caracterización.', '',
              '## Bordes y disponibilidad temporal', '',
              '| Familia bloqueada | Mediana error inicial cents | Mediana error final cents | Cobertura inicial sobre rejilla nominal % | Cobertura final sobre rejilla nominal % |',
              '|---|---:|---:|---:|---:|']
    for name in ['constant','edge_rise','edge_fall','exterior_loud','exterior_different']:
        g=data['splits']['blocked']['by_family'][name]
        lines.append(f"| {name} | {metric(g,'initial_edge_median_abs_cents')} | {metric(g,'final_edge_median_abs_cents')} | {metric(g,'initial_edge_defined_of_nominal_percent')} | {metric(g,'final_edge_defined_of_nominal_percent')} |")
    lines += ['', 'Los primeros/últimos 100 ms y los primeros/últimos cinco frames definidos se conservan por caso. '
              'Con tramo exacto faltan centros cerca de los extremos por la ventana acústica, aunque la cobertura sobre frames existentes sea 100%. '
              'No se publican frames exteriores ni se interpola para rellenar extremos o huecos. '
              'En 20 s el WAV carece de contexto exterior, también documentado en desarrollo.', '',
              '## Discontinuidades, clipping y publicación', '']
    for split in ('development','blocked'):
        g=data['splits'][split]['all_conditions']
        lines.append(f"- {split}: {g['transitions_over_6st']} transiciones >6 ST; {g['short_transitions']} a delta_t ≤10 ms; "
                     f"{g['transitions_after_longer_interval']} a intervalos mayores. Avisos: `{json.dumps(g['warnings'],sort_keys=True)}`. "
                     f"Rango publicable {g['range_published_cases']}/450; pendiente publicable {g['slope_published_cases']}/450.")
    lines += ['', 'Un salto de octava de la verdad sintética y un error de octava del estimador son conceptos diferentes. '
              'Los avisos son evidencia temporal, nunca corrección automática ni interpretación clínica. '
              'La regla temporal se eligió solo en desarrollo; la prueba de política inyectada permanece en `development/temporal_policy.json`.', '',
              'Clipping y severe_clipping se conservan como familias separadas con su número de muestras recortadas en la verdad sintética. '
              'El runner de banco no añade el aviso digital del contrato de API; los tests del módulo verifican ese aviso. '
              'Un buen resultado de F0 en estas señales no implica que una grabación humana recortada sea válida para análisis clínico.', '',
              '## Pruebas y cierre técnico', '',
              'La evidencia de tests locales, navegador y Docker se completa en `validation/` y `validation/summary.json`. '
              'El cierre requiere aceptación, integridad, suite y regresiones; no sustituye la validación humana. '
              'No se ha implementado interfaz de prosodia ni abierto PR.', '',
              '## Artefactos', '',
              '`blocked/manifest.json`, `cases.json`, `results.jsonl.gz`, `summary.json`, `acceptance.json`, '
              '`traces-filtered_800_03__0.npz`, `integrity.json` y `development_comparison.json`. '
              'Los hashes de archivos, las pruebas y el estado final quedan en el manifiesto de entrega. '
              'Las medias/DT/cuantiles nativos no se sustituyen por promedios simples de los frames.', '']
    (ROOT/'FINAL_REPORT.md').write_text('\n'.join(lines))


if __name__ == '__main__':
    result = make_report()
    print(json.dumps({s:result['splits'][s]['primary_clean'] for s in result['splits']}, indent=2))
