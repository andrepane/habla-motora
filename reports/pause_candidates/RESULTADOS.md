# Resultados 7B.2 — candidatos experimentales a pausa

**A es preferible en esta comparación técnica bloqueada.** No se adopta el nombre `pause_detector_v1`, no se conecta a `/phrase` y no se afirma validez humana ni ahorro de revisión. Los resultados definitivos siguen procediendo exclusivamente de 7B.1 manual confirmado.

## Proceso y congelación

- Base: `23697e7b4a00917e5547a27447fd95b46d8cf130`.
- Motores técnicos: commit `784dfa55ebac703aac88ea79a82a6a3245a78286`.
- Desarrollo completo y criterios guardados ANTES de ejecutar bloqueado: commit [`d111214907d1d143e84266442655877709375dbc`](https://github.com/andrepane/habla-motora/commit/d111214907d1d143e84266442655877709375dbc).
- SHA-256 del criterio congelado: `d39dffa0ad4173d5336f006e97b2d6564753b2f210542437effd774c3e1bb6a2`.
- No se ha cambiado código de detección, parámetros ni evaluación después de consultar bloqueado. No se ha utilizado ningún WAV humano.
- El límite absoluto por familia se deriva del menor P95 de carga entre métodos empatados en el mayor recall regional de desarrollo; en controles sin referencias se consideran los tres. Evita premiar a un comparador que omite regiones. Sigue sin demostrar carga tolerable para humanos.

## Banco

3.264 WAV de desarrollo + 3.264 bloqueados = **6.528 WAV**, cada uno procesado por A, A+B y Praat: **19.584 evaluaciones**. 27 familias, dos frecuencias de muestreo, tres PCM, ocho duraciones nominales y dos semillas/fases por condición. Semillas e identificadores disjuntos; mismo diseño de condiciones. No representa 6.528 hablantes ni observaciones humanas independientes.

Las frecuencias controladas incluyen 60, 100, 200, 350, 500, 600, 700 y 800 Hz; 800 Hz es control fuera del techo aproximado de retardos. La periodicidad es un coeficiente auxiliar, no una estimación de F0; los múltiplos de período impiden interpretarla como frecuencia fundamental.

Las rampas, amplitudes respiratorias, separaciones y eventos breves tienen valores balanceados por condición/duración, no un factorial completo de todas las combinaciones. Consulte manifiesto/recetas y protocolo para conocer esa limitación.

## Dos objetivos distintos

**Regional:** recuperar interrupciones construidas, incluidos cierres proxy y regiones de menos de 250 ms. **Proxy de pausa:** interrupciones sintéticas >=250 ms que no son cierres. Los candidatos útiles sobre intervalos cortos/cierres cuentan como falsos respecto al segundo objetivo, pero no demuestran un error de clasificación clínica: el detector no clasifica pausas.

TODAS las propuestas cuentan en la carga, incluidas las próximas a bordes y las solapadas. No se ocultan candidatos ni fallos. Un `not_evaluable` con referencia cuenta como omisión; sin referencias el recall es null. Silencio digital no se convierte automáticamente en pausa.

## Desarrollo (sin elegir ganador con este conjunto)

| Variante | TP regional | FP regional | Omisiones | Recall regional | Precisión regional | FP/min regional | FP/min proxy |
|---|---:|---:|---:|---:|---:|---:|---:|
| energy | 2712 | 120 | 264 | 91.13% | 95.76% | 0.551 | 5.901 |
| multifeature | 2712 | 120 | 264 | 91.13% | 95.76% | 0.551 | 5.901 |
| praat | 2052 | 87 | 924 | 68.95% | 95.93% | 0.400 | 3.667 |

## Bloqueado: recuperación y carga

| Variante | TP regional | FP regional | Omisiones | Recall regional | Precisión regional | Recall proxy | Precisión proxy | FP/min regional | FP/min proxy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| energy | 2712 | 126 | 264 | 91.13% | 95.56% | 90.85% | 54.55% | 0.579 | 5.928 |
| multifeature | 2712 | 126 | 264 | 91.13% | 95.56% | 90.85% | 54.55% | 0.579 | 5.928 |
| praat | 2052 | 84 | 924 | 68.95% | 96.07% | 78.87% | 62.92% | 0.386 | 3.640 |

Recall principal con IoU >=0,30, matching de máxima cardinalidad y después máximo IoU total; también se conserva la repetición con IoU >=0,50 en los archivos completos. El conjunto limpio tiene más casos por el cruce de frecuencias: por eso se informa también recall macro por familia.

| Variante | Recall macro por familia | IoU mediano | Error inicio abs. mediana / P95 ms | Error final abs. mediana / P95 ms | Fusiones | Fragmentaciones |
|---|---:|---:|---:|---:|---:|---:|
| energy | 88.07% | 0.960 | 6.250 / 11.270 | 4.750 / 11.250 | 24 | 6 |
| multifeature | 88.07% | 0.960 | 6.250 / 11.270 | 4.750 / 11.250 | 24 | 6 |
| praat | 62.50% | 0.884 | 18.750 / 21.247 | 12.750 / 16.250 | 0 | 0 |

Las 24 fusiones aparecen con actividad intermedia de 5 ms (12 en interrupciones nominales de 100 ms y 12 en las de 251 ms). Las 6 fragmentaciones aparecen en respiración simulada. No hay una regla de unión por proximidad ni borrado de actividad: la ventana y el umbral no siempre resuelven esa actividad breve. Es una limitación observada, no una garantía de separación.

Los errores de límites/IoU se calculan solo sobre emparejamientos; no ocultan las omisiones, que se informan por separado. Fusiones/fragmentaciones se detectan con el grafo de solapamientos, no solo el matching.

## Carga absoluta por familia (bloqueado)

| Familia | Recall regional A / A+B / Praat | FP/min proxy A | FP/min proxy A+B | FP/min proxy Praat | Tope congelado P95 por WAV |
|---|---|---:|---:|---:|---:|
| clean | 100.00% / 100.00% / 87.50% | 5.625 | 5.625 | 3.750 | 15.000 |
| noise_30 | 100.00% / 100.00% / 87.50% | 5.625 | 5.625 | 3.750 | 15.000 |
| noise_20 | 100.00% / 100.00% / 87.50% | 5.625 | 5.625 | 3.750 | 15.000 |
| noise_10 | 100.00% / 100.00% / 0.00% | 5.625 | 5.625 | 0.000 | 15.000 |
| noise_0 | 0.00% / 0.00% / 0.00% | 0.000 | 0.000 | 0.000 | 0.000 |
| breath | 50.00% / 50.00% / 0.00% | 8.438 | 8.438 | 0.000 | 30.000 |
| low_amplitude | 100.00% / 100.00% / 87.50% | 5.625 | 5.625 | 3.750 | 15.000 |
| fade | 100.00% / 100.00% / 100.00% | 5.625 | 5.625 | 5.625 | 15.000 |
| closure | 100.00% / 100.00% / 87.50% | 15.000 | 15.000 | 13.125 | 15.000 |
| weak_voice | 100.00% / 100.00% / 87.50% | 5.625 | 5.625 | 3.750 | 15.000 |
| two_close | 100.00% / 100.00% / 87.50% | 11.250 | 11.250 | 7.500 | 30.000 |
| brief_event | 87.50% / 87.50% / 62.50% | 22.500 | 22.500 | 15.000 | 30.000 |
| aperiodic | 100.00% / 100.00% / 87.50% | 5.625 | 5.625 | 3.750 | 15.000 |
| low_energy_present | null / null / null | 15.000 | 15.000 | 13.125 | 15.000 |
| no_pause | null / null / null | 0.000 | 0.000 | 0.000 | 0.000 |
| all_silence | null / null / null | 0.000 | 0.000 | 0.000 | 0.000 |
| background_only | null / null / null | 0.000 | 0.000 | 0.000 | 0.000 |
| clipped | 100.00% / 100.00% / 87.50% | 5.625 | 5.625 | 3.750 | 15.000 |
| stationary_broadband | null / null / null | 0.000 | 0.000 | 0.000 | 0.000 |
| colored_30 | 100.00% / 100.00% / 87.50% | 5.625 | 5.625 | 3.750 | 15.000 |
| colored_20 | 100.00% / 100.00% / 75.00% | 5.625 | 5.625 | 1.875 | 15.000 |
| colored_10 | 100.00% / 100.00% / 0.00% | 5.625 | 5.625 | 0.000 | 15.000 |
| colored_0 | 0.00% / 0.00% / 0.00% | 0.000 | 0.000 | 0.000 | 0.000 |
| variable_30 | 100.00% / 100.00% / 87.50% | 5.625 | 5.625 | 3.750 | 15.000 |
| variable_20 | 100.00% / 100.00% / 87.50% | 5.625 | 5.625 | 3.750 | 15.000 |
| variable_10 | 100.00% / 100.00% / 87.50% | 5.625 | 5.625 | 3.750 | 15.000 |
| variable_0 | 100.00% / 100.00% / 0.00% | 5.625 | 5.625 | 0.000 | 15.000 |

La columna de carga es el FP/min agregado de la familia; el criterio compara el P95 por WAV con el tope congelado. Media, mediana, P95 y máximo, FP/min regional y proxy, y todas las demás métricas por condición están en los CSV y resúmenes completos.

## Qué aporta y qué empeora B

- Candidatos adicionales con límites nuevos: **0**.
- TP regionales adicionales: **0**; cambio de FP proxy: **0**.
- Cambio de fusiones: **0**; cambio de fragmentaciones: **0**.
- Cambio del recall macro por familia: **0.000 puntos porcentuales**.
- Cambio de precisión proxy: **0.000 puntos porcentuales**.
- B añade características/avisos, pero su utilidad para el revisor no está medida. Que una regla exista y pase una prueba de activación controlada no significa que recupere más regiones en este banco.

En bloqueado, B no produce nuevos intervalos: la condición conjunta de periodicidad baja, planitud alta y flujo <=0,10 resulta restrictiva para estas señales. Esto no demuestra que toda información espectral sea inútil; demuestra ausencia de beneficio de ESTA vía B y ESTA configuración en ESTE banco. No se relajan umbrales después de ver bloqueado.

| Variante | Latencia mediana / P95 s bajo 8 workers | Estado |
|---|---:|---|
| energy | 0.055 / 0.229 | {'completed': 3168, 'failed': 0, 'not_evaluable': 96} |
| multifeature | 0.390 / 1.206 | {'completed': 3168, 'failed': 0, 'not_evaluable': 96} |
| praat | 0.242 / 0.846 | {'completed': 3264, 'failed': 0, 'not_evaluable': 0} |

Tiempos bajo carga concurrente, no benchmark aislado. El smoke de 20 s se conserva aparte; una observación no certifica P95 ni ahorro humano.

## Umbral manual 249 / 250 / 251 ms

| Duración nominal | Variante | Referencias regionales limpias | Candidatos | Recall regional | Mediana duración automática ms | Propuestas con duración automática >=250 ms |
|---|---|---:|---:|---:|---:|---:|
| 249 | energy | 96 | 96 | 100.00% | 240.000 | 0 |
| 249 | multifeature | 96 | 96 | 100.00% | 240.000 | 0 |
| 249 | praat | 96 | 96 | 100.00% | 220.000 | 0 |
| 250 | energy | 96 | 96 | 100.00% | 240.000 | 0 |
| 250 | multifeature | 96 | 96 | 100.00% | 240.000 | 0 |
| 250 | praat | 96 | 96 | 100.00% | 220.000 | 0 |
| 251 | energy | 96 | 96 | 100.00% | 240.000 | 0 |
| 251 | multifeature | 96 | 96 | 100.00% | 240.000 | 0 |
| 251 | praat | 96 | 96 | 100.00% | 220.000 | 0 |

Estos intervalos son propuestas, no pausas aceptadas. Las ventanas pueden acortar los límites, especialmente cerca de 250 ms; la clasificación exige revisar y corregir muestras en 7B.1. El detector no aplica el umbral manual para aceptar/rechazar. Las duraciones realizables por muestras constan en cada receta.

## Aplicación literal del criterio congelado

- **energy**: cumple los criterios técnicos del banco.
- **multifeature**: cumple los criterios técnicos del banco.
- **praat**: incumple: clean_start_median.

Condiciones adicionales para preferir B cuando ambas variantes son elegibles:
- `macro_recall_gain_ge2pp`: False.
- `precision_loss_le1pp`: True.
- `no_extra_fusions`: True.
- `incremental_burden_le2_each_family`: True.

**Decisión: A es preferible en esta comparación técnica bloqueada.** Las configuraciones siguen experimentales y separadas. La decisión no autoriza integración en interfaz ni adopción de un detector definitivo.

## Regresiones, límites y datos completos

No hay cambios en backend/ frontend/ ni en las configuraciones de vocal, DDK, 7A y 7B.1. Se añade NumPy para investigación offline. La primera ejecución local general concurrente se interrumpió tras seis marcas de error y no se usa como validación. La suite final aislada y CI se documentan en validation.json; no se atribuye una causa concreta a esos seis errores sin trazas completas.

Los cierres proxy se proponen como regiones candidatas; el motor no los distingue de pausas aceptables. La actividad periódica de amplitud muy reducida también puede producir falsos candidatos. Las advertencias/evidencias no sustituyen la clasificación manual.

Limitaciones: corpus construido y correlacionado; sin participantes; sin concordancia humana, precisión clínica ni tiempo ahorrado; ventanas y actividad breve pueden causar fusiones; ruido/respiración/voz débil siguen ambiguos; límites automáticos requieren revisión; periodicidad no es F0; P95 sintético no es tolerancia clínica. Reproducción por recetas con hashes: comprobarlos, no asumir identidad numérica entre cualquier plataforma.

## Validación final

| Comprobación | Resultado |
|---|---|
| Específicas del motor/evaluador | 40/40 |
| Suite local aislada | 537 passed, 6 xfailed, 1 warning; 740,82 s |
| Docker: construcción | 537 passed, 6 xfailed, 1 warning; 241,41 s |
| Docker: repetición en contenedor | 537 passed, 6 xfailed, 1 warning; 237,33 s |
| Unitarias frontend | 45/45 |
| Navegador vocal / DDK / 7A / 7B.1 | 24 / 35 / 53 / 60, todos aprobados |
| HTTP e informes sintéticos previos | Aprobados |

[CI completo sobre el código congelado](https://github.com/andrepane/habla-motora/actions/runs/39242058207), primer intento, success. El commit posterior solo añade documentación y datos. Los seis xfail son previos; la advertencia pytest es deprecación Starlette/AnyIO. El intento local concurrente interrumpido se conserva en validation-interrupted-local.txt; la repetición aislada y CI pasan.

Archivos completos:

- [Decisión y todos los criterios](decision.json) · [Congelación previa](frozen-gate.json).
- [Desarrollo por familia](development-per-family.csv) · [Bloqueado por familia](blocked-per-family.csv).
- [Desarrollo por condición](development-per-condition.csv.gz) · [Bloqueado por condición](blocked-per-condition.csv.gz).
- [Todas las evaluaciones de desarrollo](development-cases.jsonl.gz) · [Todas las evaluaciones bloqueadas](blocked-cases.jsonl.gz).
- [Resumen desarrollo](development-summary.json.gz) · [Resumen bloqueado](blocked-summary.json.gz).
- [B: diferencias por familia](B-delta-per-family.csv) · [B: diferencias por WAV](B-delta-per-case.csv.gz) · [Métricas bloqueadas por WAV](blocked-per-case.csv.gz).
- [Smoke de 20 s](development-20s-smoke.json) · [Validación final](validation.json) · [Reproducción y auditoría](README.md).

Cada registro conserva límites, duración, motivos, características, advertencias, hashes y receta. Los índices y digest de frames permiten regenerar la traza íntegra de un caso con inspect_case. No se almacenan gigabytes de WAV duplicados. No se ha abierto PR.
