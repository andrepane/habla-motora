# Congelación de Prosodia 8A — desarrollo

Evaluación reiniciada desde `2d80492bad73899eb2153031bc4fac98c9263b7e`, sin reconstruir la implementación. La sesión anterior no se considera evidencia experimental. Solo se han usado controles acústicos sintéticos.

**El conjunto bloqueado no se ha ejecutado ni se ha generado su audio. Esta congelación se entrega para revisión.**

## Integridad y cambios

450 WAV (75 recetas × 2 frecuencias de muestreo × 3 anchos PCM), 14 combinaciones y 6.300 extracciones completas. 1.050 verificaciones de concordancia nativa aprobadas. Las 14 trazas NPZ conservan 450 casos cada una. Los centros se han verificado dentro de `[a,b)`; los conteos coinciden con los resultados. Véase `development/integrity.json`.

El módulo, banco, motor, perfiles, selector y tests originales permanecen byte a byte como en el commit inicial. Única corrección del código existente: `assess.py` evalúa la publicación del rango con la regla elegida en la congelación, en vez de la primera regla candidata que usaba el resumen del runner. Dos tests cubren la discrepancia en ambos sentidos. No se han cambiado los candidatos, el ranking ni los umbrales.

## Configuración elegida

```json
{
  "acceptance": {
    "clean_core_defined_percent": 98.0,
    "clean_core_median_cents": 20.0,
    "clean_core_p95_cents": 50.0,
    "constant_octave_error_frames": 0,
    "gap_boundary_window_factor": 3.0,
    "long_gap_recall": 0.95,
    "noise20_coverage_loss_pp": 10.0,
    "noise20_median_cents": 50.0,
    "quantile_max_hz_floor": 1.0,
    "quantile_relative_tolerance": 0.02,
    "robust_range_st": 0.2,
    "silence_false_defined_percent": 2.0,
    "slope_relative_tolerance": 0.05,
    "slope_st_s_floor": 0.05
  },
  "assessment_sha256": "6863b6184071aa87767666bd05448f13ae05ddafc97fa5e176253a4271df968e",
  "code_sha256": "5d3878cf5ed100276acc0c7798a702666049e49ed6d2b33fe8043c15f6539701",
  "context_s": 0.0,
  "development_manifest_sha256": "681e27cc49b5a7caef28814b669d38a7583aa9f02279f48deac8b3c466721115",
  "development_results_sha256": "40eac33f2991629b3b9ab4df578b8c15de1437057c8a359dec3b54bfa916dd27",
  "jump_limit_s": 0.01,
  "module_sha256": "4ae1b67439ea76934f7c740da1732ddf3d8ac4ded6a8652de5c34baafd99a8c8",
  "profile": {
    "attenuation": 0.03,
    "candidates": 15,
    "floor_hz": 75.0,
    "hop_s": 0.005,
    "id": "current_cc",
    "jump_cost": 0.35,
    "method": "raw cross-correlation",
    "octave_cost": 0.01,
    "silence": 0.03,
    "top_hz": 600.0,
    "very_accurate": false,
    "voicing": 0.45,
    "vu_cost": 0.14
  },
  "range_rule": {
    "id": "distributed",
    "minimum_bins": 4,
    "minimum_coverage": 0.5,
    "minimum_n": 50,
    "minimum_span_fraction": 0.7,
    "minimum_span_s": 1.0
  },
  "schema_version": "phrase_prosody_freeze_v1",
  "selected_configuration_id": "current_cc__0",
  "selection_policy": "predeclared_macro_family_cost_then_core_cents_within_0.001",
  "validation": "technical_only_human_validity_pending"
}
```

## Comparación completa

Selección por el coste macro por familia persistido: omisiones + 5×errores >600 cents + 5×falsos definidos. Se excluyen del coste frecuencias nominales fuera de 55–600 Hz y ruido con SNR ≤10 dB. Empates a ≤0,001 del mínimo: mediana del error core, contexto y nombre de configuración. La mediana core para ese desempate se calcula sobre todas las filas disponibles, tal como implementa el selector original. No se añadió un filtro de elegibilidad por resultados de graves/agudos. El coste no representa validez clínica.

| Configuración | Contexto ms | Coste | Mediana errores core (cents) | Elegida |
|---|---:|---:|---:|---|
| current_cc__0 | 0 | 0.04628252 | 0.00481456 | sí |
| filtered_800_03__0 | 0 | 0.06994822 | 0.00454045 |  |
| filtered_800_09__0 | 0 | 0.07248308 | 0.00450887 |  |
| current_cc__250 | 250 | 0.11188638 | 0.00481491 |  |
| wide_cc__250 | 250 | 0.11190180 | 0.00487068 |  |
| filtered_800_03__250 | 250 | 0.15026170 | 0.0050783 |  |
| filtered_800_09__250 | 250 | 0.15276170 | 0.0047819 |  |
| wide_ac__250 | 250 | 0.16697494 | 0.0046069 |  |
| wide_cc__0 | 0 | 0.22018083 | 0.00487068 |  |
| wide_ac__0 | 0 | 0.27787171 | 0.0046001 |  |
| filtered_1200_03__0 | 0 | 0.45319548 | 0.00469302 |  |
| filtered_1200_09__0 | 0 | 0.45577909 | 0.00469302 |  |
| filtered_1200_03__250 | 250 | 0.53091941 | 0.00523298 |  |
| filtered_1200_09__250 | 250 | 0.53346749 | 0.00523298 |  |

Los costes de cada familia por alternativa están en `development/selection.json`; todas las estadísticas y condiciones están en `development/results.jsonl.gz` y `development/summary.json`.

## Soporte del rango y discontinuidades

| Regla | Publicaciones falsas | Publicaciones esperadas obtenidas |
|---|---:|---:|
| distributed | 0 | 402 |
| temporal | 0 | 402 |
| frames_only | 18 | 402 |

El soporte combina número de frames, extensión temporal absoluta y relativa, cobertura y quintiles ocupados. No convierte el número de frames solapados en tamaño muestral independiente. P10/P90 y rango publicado quedan en null con motivo cuando no se cumple la regla. Los cuantiles nativos brutos siguen disponibles como auditoría.

| Límite delta_t ms | Avisos en controles positivos | Avisos falsos tras hueco largo |
|---:|---:|---:|
| 10 | 4 | 0 |
| 20 | 4 | 0 |
| 50 | 4 | 4 |

Transiciones >6 ST conservan dirección, delta_t y hueco. El límite elegido regula únicamente los avisos; 11–13 ST se etiqueta como posible salto de octava, sin corregir valores. Los controles temporales, positivos a 5/10 ms y negativos desde 25 ms de delta_t, se conservan en `temporal_policy.json`.

## Resultados de la configuración elegida por familia

Medianas y máximos son distribuciones entre casos, no frames independientes. Errores en valor absoluto. Los errores del rango y pendiente son valores brutos de cálculo; su publicación está condicionada al soporte. Los valores nativos y cada condición individual permanecen en el JSONL.

| Familia | Casos | Mediana error F0 cents | Máximo P95 core cents | Frames octava | Cobertura mediana % | Máximo error P10 Hz | Máximo error P90 Hz | Máximo error rango ST | Máximo error pendiente ST/s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| alternating | 6 | 0.00310909 | 0.00488469 | 0 | 51.0692 | 0.000564302 | 0.000564302 | 2.17868e-05 | 0.000216197 |
| aperiodic | 6 | null | null | 0 | 0 | null | null | null | null |
| aperiodic_gaps | 6 | 0.00310909 | 0.00488469 | 0 | 87.4214 | 0.000564302 | 0.000564302 | 2.17761e-05 | 4.26755e-05 |
| clipping | 6 | 0.00186592 | 0.00336514 | 0 | 100 | 0.000388756 | 0.000388756 | 5.77453e-06 | 4.27611e-07 |
| constant | 66 | 0.00174009 | 1200 | 10335 | 100 | 475 | 475 | 3.36471e-05 | 2.59449e-07 |
| dominant_second | 6 | 0.00192931 | 0.00384253 | 0 | 100 | 0.000443907 | 0.000443907 | 1.43826e-06 | 7.03695e-08 |
| dominant_third | 6 | 3.01122e-05 | 5.3652e-05 | 0 | 100 | 6.19796e-06 | 3.83056e-06 | 5.63688e-07 | 2.44063e-09 |
| duration | 24 | 0.00279478 | 0.00488469 | 0 | 100 | 0.000564302 | 0.000564302 | 2.17761e-05 | 6.43303e-08 |
| edge_fall | 6 | 0.00310909 | 0.00488469 | 0 | 100 | 0.000564302 | 0.000564302 | 2.17761e-05 | 0.00740182 |
| edge_rise | 6 | 0.00402894 | 0.00584769 | 0 | 100 | 0.000713046 | 0.000879938 | 1.86753e-05 | 0.00944253 |
| exterior_different | 6 | 0.00279478 | 0.00488469 | 0 | 100 | 0.000564302 | 0.000564302 | 2.17761e-05 | 4.42912e-08 |
| exterior_loud | 6 | 0.00457518 | 0.00606815 | 0 | 100 | 0.000701019 | 0.00062287 | 0.000114598 | 1.15752e-06 |
| fade | 6 | 0.00278366 | 0.010138 | 0 | 97.4843 | 0.000747798 | 0.000731445 | 0.000128046 | 3.26492e-05 |
| gap | 108 | 0.00310909 | 0.00488469 | 0 | 95.7233 | 0.000564302 | 0.000564302 | 2.17761e-05 | 0.00041511 |
| linear_hz | 12 | 0.723142 | 0.810307 | 0 | 100 | 0.0743105 | 0.093553 | 0.000971174 | 0.000283789 |
| linear_st | 24 | 0.633501 | 0.953461 | 0 | 100 | 0.072488 | 0.131337 | 0.00192592 | 0.000587175 |
| middle_only | 6 | 0.00310909 | 0.00488469 | 0 | 40.3774 | 0.000564302 | 0.000564302 | 2.17868e-05 | 0.00139556 |
| missing_fundamental | 6 | 9.84438e-05 | 0.000145823 | 0 | 100 | 1.68461e-05 | 1.68461e-05 | 5.83005e-07 | 7.16436e-08 |
| noise | 48 | 4.40402 | 66.6398 | 0 | 100 | 10.7777 | 11.843 | 0.869414 | 0.0241556 |
| severe_clipping | 6 | 0.0106594 | 0.0152507 | 0 | 100 | 0.00176183 | 0.00172389 | 0.00030173 | 1.53882e-07 |
| silence | 6 | null | null | 0 | 0 | null | null | null | null |
| single_island | 6 | 0.00310909 | 0.00488469 | 0 | 10.1887 | 0.000564302 | 0.000564302 | 2.17868e-05 | 0.0219131 |
| sinusoidal | 24 | 2.74868 | 12.3581 | 0 | 100 | 0.0522102 | 0.017759 | 0.00635558 | 0.00604344 |
| split_ends | 6 | 0.00310909 | 0.00488469 | 0 | 19.6226 | 0.000564302 | 0.000564302 | 2.14474e-05 | 0.00038511 |
| step | 36 | 0.0041892 | 0.00794894 | 30 | 100 | 0.000564302 | 0.0018366 | 8.42237e-05 | 0.0279342 |
| weak | 6 | 0.00483403 | 0.0114734 | 0 | 100 | 0.00132546 | 0.000883369 | 0.0001912 | 3.17001e-06 |

## Constantes graves y agudas

| F0 nominal Hz | Alcance principal | Mediana error cents | Máximo P95 cents | Octavas (frames) | Cobertura mínima % |
|---:|---|---:|---:|---:|---:|
| 45 | caracterización | null | null | 0 | 0 |
| 55 | sí | null | null | 0 | 0 |
| 75 | sí | null | null | 0 | 0 |
| 100 | sí | 1.50049e-05 | 2.50125e-05 | 0 | 100 |
| 150 | sí | 5.66052e-06 | 2.19653e-05 | 0 | 100 |
| 200 | sí | 0.00279478 | 0.00488469 | 0 | 100 |
| 300 | sí | 0.0113713 | 0.0114614 | 0 | 100 |
| 450 | sí | 0.00170994 | 0.00186112 | 0 | 100 |
| 600 | sí | 5.35903e-05 | 1200 | 795 | 100 |
| 750 | caracterización | 1200 | 1200 | 4770 | 100 |
| 950 | caracterización | 1200 | 1200 | 4770 | 100 |

## Criterios de aceptación congelados y resultado en desarrollo

Los umbrales proceden del plan previo y del selector persistido. Se conservan los fallos; no se han relajado para obtener aprobación.

| Criterio | Aprobados / evaluados |
|---|---:|
| clean_core_defined_percent | 156 / 168 |
| constant_octave_error | 71 / 72 |
| core_median_abs_cents | 155 / 168 |
| core_p95_abs_cents | 155 / 168 |
| gap_end_abs_error_s | 36 / 36 |
| gap_start_abs_error_s | 36 / 36 |
| long_gap_recall | 36 / 36 |
| noise20_coverage_loss_pp | 12 / 12 |
| noise20_median_cents | 12 / 12 |
| nonperiodic_false_defined_percent | 12 / 12 |
| p10_error | 155 / 168 |
| p90_error | 155 / 168 |
| robust_range_error | 156 / 168 |
| slope_error | 156 / 168 |

Aceptación global en desarrollo: **NO aprobada**. Cada fallo y su caso están identificados en `development/acceptance.json`. Elegir la mejor alternativa del coste no implica superar todos los criterios.

Los criterios son: core mediana ≤20 cents, P95 ≤50 cents, cobertura core ≥98%; cero octavas en constantes/duración; error de P10/P90 ≤max(1 Hz, 2%); error de rango ≤0,2 ST; pendiente ≤max(0,05 ST/s, 5%); falsos definidos no periódicos ≤2%; ruido a 20 dB: mediana ≤50 cents y pérdida de cobertura ≤10 puntos; huecos ≥500 ms: recuperación ≥95% y error mediano de bordes ≤3/floor segundos. Los fallos de publicación por soporte insuficiente cuentan como fallos en el criterio correspondiente.

## Verificación y límites

45 tests originales de prosodia aprobados, 2 de prosodia excluidos para no invocar ni consultar el bloqueado; 2 nuevos tests del evaluador aprobados. Regresiones: 595 aprobadas, 6 xfail, 2 excluidas y un aviso de deprecación. La regresión general empezó antes de añadir los dos nuevos tests, que se ejecutaron aparte. Logs en `development/`.

El entorno usa Python 3.12.14, NumPy 2.3.5 y Praat 6.4.27; el archivo de Praat coincide con `6f60fba398f7490881a569b874a1c66ca026e1f748946d50a6017941c4137f7e`, fijado en Dockerfile. La identidad binaria y tiempo de ejecución están en `manifest.json`. No se ha ejecutado Docker.

No hay interpretación clínica, validación humana ni prueba de población. La curva conserva huecos sin interpolación o suavizado. La selección exacta puede perder disponibilidad de centros en los bordes; las medidas de disponibilidad nominal inicial/final se conservan por caso, además de la cobertura sobre frames existentes. Con duración de 20 s el contexto se limita al WAV disponible. No se han tocado 7A/7B, vocal, DDK ni interfaz. No se ha abierto PR.
