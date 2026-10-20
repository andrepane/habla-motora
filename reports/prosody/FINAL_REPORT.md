# Hito 8A — Prosodia v1: evaluación técnica final

Configuración `filtered_800_03__0`, congelación `phrase_prosody_freeze_v2`, commit `9c67d04888ae0837297d6896ca4376e126cfc935`. No se ha reseleccionado ni ajustado ningún parámetro después del bloqueado. Las congelaciones v1/v2 y la corrección de elegibilidad permanecen auditables.

## Qué se ha validado

Verdad sintética: trayectorias de F0, periodicidad y huecos definidos por recetas deterministas, no habla humana. Desarrollo: 450 WAV × 14 alternativas, ya persistidos; esta comparación usa únicamente la alternativa congelada. Bloqueado: una primera ejecución completa, 450 WAV × una alternativa, sin iteración. Cambia fase, semilla, frecuencia base ×1,037 y pendiente log-lineal ×0,93. Comparte familias con desarrollo; no representa una población independiente.

Concordancia Praat: 75/75 comprobaciones en el bloqueado y 75/75 para esta alternativa en desarrollo (1.050/1.050 para las 14 alternativas originales). Un segundo script/proceso consulta estadísticas nativas sobre un Pitch reconstruido a partir de centros seleccionados. Tolerancia ≤1e-9. Es concordancia de integración, no un estimador acústico independiente. Los tests adicionales de concordancia cubren ambos muestreos y los tres PCM.

**Validación humana y validez clínica: pendientes.** No se han usado WAV humanos ni emitido interpretaciones clínicas.

## Aceptación congelada

| Criterio | Desarrollo aprobados/total | Bloqueado aprobados/total |
|---|---:|---:|
| clean_core_defined_percent | 168/168 | 168/168 |
| constant_octave_error | 72/72 | 72/72 |
| core_median_abs_cents | 168/168 | 168/168 |
| core_p95_abs_cents | 168/168 | 168/168 |
| gap_end_abs_error_s | 36/36 | 36/36 |
| gap_start_abs_error_s | 36/36 | 36/36 |
| long_gap_recall | 36/36 | 36/36 |
| noise20_coverage_loss_pp | 12/12 | 12/12 |
| noise20_median_cents | 12/12 | 12/12 |
| nonperiodic_false_defined_percent | 12/12 | 12/12 |
| p10_error | 168/168 | 168/168 |
| p90_error | 168/168 | 168/168 |
| robust_range_error | 168/168 | 168/168 |
| slope_error | 168/168 | 168/168 |

Aceptación global bloqueada: **True**. Los fallos, si existen, se conservan sin retocar criterios. La aceptación solo cubre las condiciones predeclaradas; la caracterización incluye condiciones adicionales que pueden fallar sin alterar esta decisión.

## Error y cobertura en controles principales limpios

168 casos por split. Cents de la tabla: todos los frames definidos con verdad periódica, incluidos transitorios. El P95 core máximo es el peor P95 por caso tras la guarda predeclarada de transiciones. La cobertura se calcula sobre centros existentes, no sobre toda la duración del audio.

| Split | Mediana cents agrupada | P95 cents agrupado | Máximo P95 core cents | Octavas frames | Cobertura agrupada % | Máximo error P10 Hz | Máximo error P90 Hz | Máximo error rango ST | Máximo error pendiente ST/s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| development | 0.00350151 | 0.220736 | 0.510065 | 60 | 100 | 0.0415154 | 0.0756933 | 0.00970747 | 0.0425178 |
| blocked | 0.00183682 | 0.159334 | 0.506939 | 60 | 100 | 0.042661 | 0.0780578 | 0.00963757 | 0.0424621 |

No se interpreta el número de frames solapados ni los formatos repetidos como muestras independientes. Los cuantiles Hz proceden de Praat; el rango robusto ST es 12·log2(P90/P10); la pendiente es OLS sobre tiempos reales de frames definidos. Los cuantiles/rango publicados exigen soporte distributed, y la pendiente su soporte temporal congelado. Valores nativos brutos y errores permanecen en la auditoría incluso si la publicación es null.

## Bloqueado por familia

| Familia | Casos | Mediana cents agrupada | P95 cents agrupado | Octavas frames | Cobertura mediana % | Máx error P10 Hz | Máx error P90 Hz | Máx error rango ST | Máx error pendiente ST/s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| alternating | 6 | 0.00167729 | 4.01737 | 0 | 53.4854 | 0.0544809 | 0.00605174 | 0.0049803 | 0.000192212 |
| aperiodic | 6 | null | null | 0 | 0 | null | null | null | null |
| aperiodic_gaps | 6 | 0.00145119 | 0.00250283 | 0 | 87.706 | 0.000311981 | 0.000182313 | 1.16435e-05 | 0.000110488 |
| clipping | 6 | 0.00135744 | 0.00246516 | 0 | 100 | 0.000295474 | 0.000182487 | 9.52633e-06 | 1.31287e-09 |
| constant | 66 | 0.00135695 | 1200 | 4734 | 100 | 492.575 | 492.575 | 0.00718612 | 7.43767e-07 |
| dominant_second | 6 | 0.000661041 | 0.000804845 | 0 | 100 | 0.000102158 | 9.09132e-05 | 3.08085e-06 | 1.02553e-08 |
| dominant_third | 6 | 0.000274087 | 0.000455093 | 0 | 100 | 4.41565e-05 | 6.41878e-05 | 2.80831e-06 | 7.36611e-09 |
| duration | 24 | 0.00140048 | 0.00248958 | 0 | 100 | 0.000309172 | 0.00018329 | 1.13273e-05 | 1.35154e-07 |
| edge_fall | 6 | 0.00148521 | 0.00253104 | 0 | 100 | 0.000319781 | 0.000183151 | 1.21515e-05 | 0.000468059 |
| edge_rise | 6 | 0.00344449 | 0.00364422 | 0 | 100 | 0.000611974 | 0.000615376 | 4.14668e-06 | 0.000674837 |
| exterior_different | 6 | 0.00140217 | 0.00248962 | 0 | 100 | 0.000308243 | 0.000182917 | 1.11863e-05 | 9.90807e-09 |
| exterior_loud | 6 | 0.0015617 | 0.00521492 | 0 | 100 | 0.000680789 | 0.000652184 | 8.5152e-05 | 2.50972e-07 |
| fade | 6 | 0.00146631 | 0.002728 | 0 | 97.5919 | 0.000310632 | 0.000247651 | 1.8699e-05 | 5.42363e-06 |
| gap | 108 | 0.00145333 | 0.00250213 | 0 | 96.0076 | 0.000317689 | 0.000183025 | 1.23631e-05 | 0.000996667 |
| linear_hz | 12 | 0.00208511 | 0.00612839 | 0 | 100 | 0.000314152 | 0.000377199 | 3.01973e-05 | 4.20531e-06 |
| linear_st | 24 | 0.00178693 | 0.00592221 | 0 | 100 | 0.000333261 | 0.00066926 | 4.73342e-05 | 3.38781e-06 |
| middle_only | 6 | 0.0015054 | 0.00250566 | 0 | 40.9379 | 0.000311241 | 0.000183678 | 1.11672e-05 | 0.00181717 |
| missing_fundamental | 6 | 0.00051041 | 0.000696304 | 0 | 100 | 9.29227e-05 | 8.41496e-05 | 4.6703e-06 | 5.57479e-09 |
| noise | 48 | 0.281848 | 5.14265 | 0 | 100 | 0.885011 | 1.14203 | 0.14988 | 0.00294956 |
| severe_clipping | 6 | 0.00109729 | 0.00515205 | 0 | 100 | 0.000617264 | 0.000177879 | 6.47917e-05 | 6.63169e-08 |
| silence | 6 | null | null | 0 | 0 | null | null | null | null |
| single_island | 6 | 0.00156196 | 3.75775 | 0 | 10.5196 | 0.289309 | 0.000184066 | 0.0241564 | 0.00886724 |
| sinusoidal | 24 | 0.0541487 | 0.483703 | 0 | 100 | 0.042661 | 0.0780578 | 0.00963757 | 0.00044449 |
| split_ends | 6 | 0.00151683 | 0.220447 | 0 | 19.3916 | 0.000307969 | 0.000186707 | 1.39768e-05 | 0.00133866 |
| step | 36 | 0.00204809 | 0.00351627 | 60 | 100 | 0.000306785 | 0.000612435 | 5.98188e-05 | 0.0424621 |
| weak | 6 | 0.00172936 | 0.00920894 | 0 | 100 | 0.00113721 | 0.00116431 | 0.000192115 | 1.62311e-07 |

Las familias constant/noise incluyen condiciones fuera de aceptación: 45/750/950 Hz nominales, ruido intenso y armónicos ambiguos son caracterización. No se ocultan ni se mezclan con los controles principales.

## Graves/agudos: constantes bloqueadas

| F0 nominal Hz | F0 sintética Hz | Mediana cents | P95 cents | Octavas frames | Cobertura mínima % | P10 nativo mediano Hz | P90 nativo mediano Hz |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 45 | 46.665 | null | null | 0 | 0 | null | null |
| 55 | 57.035 | 0.250533 | 0.405017 | 0 | 100 | 57.0221 | 57.0448 |
| 75 | 77.775 | 0.0374686 | 0.0656803 | 0 | 100 | 77.7736 | 77.7779 |
| 100 | 103.7 | 0.00157964 | 0.00230414 | 0 | 100 | 103.7 | 103.7 |
| 150 | 155.55 | 0.000431679 | 0.000815556 | 0 | 100 | 155.55 | 155.55 |
| 200 | 207.4 | 0.00140217 | 0.00248962 | 0 | 100 | 207.4 | 207.4 |
| 300 | 311.1 | 0.00338133 | 0.00371785 | 0 | 100 | 311.1 | 311.1 |
| 450 | 466.65 | 2.97085e-05 | 0.000124302 | 0 | 100 | 466.65 | 466.65 |
| 600 | 622.2 | 0.000743796 | 0.000902769 | 0 | 100 | 622.2 | 622.2 |
| 750 | 777.75 | 0.000832696 | 0.00123162 | 0 | 100 | 777.75 | 777.75 |
| 950 | 985.15 | 1200 | 1200 | 4734 | 100 | 492.575 | 492.575 |

## Muestreo y PCM: controles principales bloqueados

| Formato | Mediana cents | P95 cents | Máximo P95 core cents | Octavas frames | Cobertura % | Máx error P10 Hz | Máx error P90 Hz | Máx error rango ST | Máx error pendiente ST/s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 44100-PCM16 | 0.00210336 | 0.159863 | 0.499615 | 10 | 100 | 0.042661 | 0.0780578 | 0.00963757 | 0.0424451 |
| 44100-PCM24 | 0.00213337 | 0.159873 | 0.499688 | 10 | 100 | 0.0426594 | 0.0780558 | 0.00963727 | 0.0424451 |
| 44100-PCM32 | 0.00213419 | 0.159874 | 0.499688 | 10 | 100 | 0.0426594 | 0.0780558 | 0.00963727 | 0.0424451 |
| 48000-PCM16 | 0.00127299 | 0.158548 | 0.506939 | 10 | 100 | 0.0420418 | 0.0772728 | 0.00951857 | 0.0424621 |
| 48000-PCM24 | 0.00127897 | 0.158599 | 0.506702 | 10 | 100 | 0.0420384 | 0.0773038 | 0.00952004 | 0.0424621 |
| 48000-PCM32 | 0.00127902 | 0.1586 | 0.506701 | 10 | 100 | 0.0420384 | 0.0773038 | 0.00952004 | 0.0424621 |

Los JSON de comparación conservan también el desglose por formato en desarrollo. Los resultados por caso identifican cualquier diferencia entre 44,1/48 kHz y PCM16/24/32.

## Huecos bloqueados

| Hueco sintético s | Casos | Referencias por caso | Coincidencias mediana | Error mediano inicio s | Error mediano final s | IoU mediano |
|---:|---:|---:|---:|---:|---:|---:|
| 0.02s | 18 | 1 | 0 | null | null | 0 |
| 0.05s | 18 | 1 | 1 | 0.01 | 0.015 | 0.6 |
| 0.1s | 18 | 1 | 1 | 0.005 | 0.01 | 0.8 |
| 0.25s | 18 | 1 | 1 | 0.005 | 0.01 | 0.92 |
| 0.5s | 18 | 1 | 1 | 0.005 | 0.01 | 0.96 |
| 1s | 18 | 1 | 1 | 0.005 | 0.01 | 0.98 |

La aceptación de recuperación/bordes solo se aplica a huecos ≥500 ms. Los huecos menores se caracterizan sin extrapolar validez de detección de pausas lingüísticas.

## Ruido bloqueado

| Condición nominal | Mediana cents | P95 cents | Cobertura mínima % |
|---|---:|---:|---:|
| 0dB-100Hz | 3.62785 | 10.8923 | 100 |
| 0dB-450Hz | 1.77846 | 5.33136 | 100 |
| 10dB-100Hz | 1.18992 | 3.37151 | 100 |
| 10dB-450Hz | 0.298025 | 0.912066 | 100 |
| 20dB-100Hz | 0.362832 | 1.07997 | 100 |
| 20dB-450Hz | 0.085167 | 0.246357 | 100 |
| 30dB-100Hz | 0.12035 | 0.346073 | 100 |
| 30dB-450Hz | 0.0277968 | 0.0801152 | 100 |

Solo SNR=20 dB tiene los criterios congelados de mediana ≤50 cents y pérdida de cobertura ≤10 puntos. El resto se conserva como caracterización.

## Bordes y disponibilidad temporal

| Familia bloqueada | Mediana error inicial cents | Mediana error final cents | Cobertura inicial sobre rejilla nominal % | Cobertura final sobre rejilla nominal % |
|---|---:|---:|---:|---:|
| constant | 0.00162253 | 0.00159076 | 75 | 75 |
| edge_rise | 0.190422 | 0.00345059 | 75 | 75 |
| edge_fall | 0.0014276 | 0.72916 | 75 | 75 |
| exterior_loud | 0.00179052 | 0.00200591 | 75 | 75 |
| exterior_different | 0.00142775 | 0.00146493 | 75 | 75 |

Los primeros/últimos 100 ms y los primeros/últimos cinco frames definidos se conservan por caso. Con tramo exacto faltan centros cerca de los extremos por la ventana acústica, aunque la cobertura sobre frames existentes sea 100%. No se publican frames exteriores ni se interpola para rellenar extremos o huecos. En 20 s el WAV carece de contexto exterior, también documentado en desarrollo.

## Discontinuidades, clipping y publicación

- development: 18 transiciones >6 ST; 18 a delta_t ≤10 ms; 0 a intervalos mayores. Avisos: `{"LOW_F0_COVERAGE": 36, "POSSIBLE_OCTAVE_JUMP": 18, "UNDEFINED_F0_REGIONS": 144, "UPPER_FILTERED_BAND": 66}`. Rango publicable 414/450; pendiente publicable 414/450.
- blocked: 18 transiciones >6 ST; 18 a delta_t ≤10 ms; 0 a intervalos mayores. Avisos: `{"F0_NEAR_SEARCH_LIMIT": 6, "LOW_F0_COVERAGE": 36, "POSSIBLE_OCTAVE_JUMP": 18, "UNDEFINED_F0_REGIONS": 144, "UPPER_FILTERED_BAND": 66}`. Rango publicable 414/450; pendiente publicable 414/450.

Un salto de octava de la verdad sintética y un error de octava del estimador son conceptos diferentes. Los avisos son evidencia temporal, nunca corrección automática ni interpretación clínica. La regla temporal se eligió solo en desarrollo; la prueba de política inyectada permanece en `development/temporal_policy.json`.

Clipping y severe_clipping se conservan como familias separadas con su número de muestras recortadas en la verdad sintética. El runner de banco no añade el aviso digital del contrato de API; los tests del módulo verifican ese aviso. Un buen resultado de F0 en estas señales no implica que una grabación humana recortada sea válida para análisis clínico.

## Pruebas y cierre técnico

La evidencia de tests locales, navegador y Docker se completa en `validation/` y `validation/summary.json`. El cierre requiere aceptación, integridad, suite y regresiones; no sustituye la validación humana. No se ha implementado interfaz de prosodia ni abierto PR.

## Artefactos

`blocked/manifest.json`, `cases.json`, `results.jsonl.gz`, `summary.json`, `acceptance.json`, `traces-filtered_800_03__0.npz`, `integrity.json` y `development_comparison.json`. Los hashes de archivos, las pruebas y el estado final quedan en el manifiesto de entrega. Las medias/DT/cuantiles nativos no se sustituyen por promedios simples de los frames.

## Resultado final y cierre

**Hito 8A cerrado técnicamente en el alcance sintético declarado.** Bloqueado aprobado: 14 criterios, 1.392/1.392 comprobaciones; cero fallos de ejecución o de integridad. No se ha ajustado ni vuelto a ejecutar el banco bloqueado.

Pruebas específicas: 55 aprobadas. Suite local: 605 aprobadas, 6 xfail conocidos y un aviso de deprecación. Frontend: 59/59. Navegador con API real y audio sintético: vocal 24, DDK 35, frase 53, pausas revisadas 60 y candidatos 34 comprobaciones.

Docker: imagen construida correctamente; suite durante la construcción y repetición en contenedor con 605 aprobadas y 6 xfail en ambas. También pasan los informes sintéticos existentes de pitch/jitter/shimmer/HNR/DDK, los endpoints HTTP y las regresiones de navegador del workflow. Evidencia: [GitHub Actions 39435802049](https://github.com/andrepane/habla-motora/actions/runs/39435802049), commit probado `a3d6188f8cd2acc36c5265f82516867d60faa5f4`. La entrega posterior solo añade informes y logs, sin cambiar código congelado ni tests.

Los seis xfail son anteriores a 8A: modulación de pitch raw cc; jitter alternante (dos casos), jitter aleatorio 5%; HNR de 100 Hz a 44,1/48 kHz (dos casos). Sus objetivos no se han relajado.

Limitaciones que permanecen: 60 frames con error de octava en transitorios de escalones de 12 ST (3–4 frames por caso, dentro de la guarda predeclarada), 4.734 en el control de 985,15 Hz fuera de alcance; ausencia de F0 en 46,665 Hz fuera de alcance; huecos de 20 ms no recuperados; cobertura nominal del primer/último tramo de 100 ms de 75% en controles estables por el recorte exacto. No se han corregido ni ocultado. La cobertura sobre frames existentes es una magnitud distinta.

La validez humana, la generalización a habla y las interpretaciones clínicas siguen pendientes. No se ha implementado la interfaz final de prosodia ni abierto PR.
