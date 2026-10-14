# Hito 6A — implementación técnica; cierre pendiente de revisión final

Fecha: 14/10/2026. Base: main e31363bbd2e8fbc1aad1033ec71309f37420a3ca.
Rama: feat/ddk-technical-6a. 6B permanece pendiente y no bloqueante.
Sin reclutamiento, voz humana, pacientes ni datasets clínicos.

## Arquitectura

`backend/ddk.py`: lectura PCM, envolvente RMS Hann, detección de máximos/mesetas,
contraste y separación, agrupación candidata, cálculo matemático y replay de
revisión. Solo stdlib; sin modelos, identidad fonética automática ni llamadas a
módulos de vocal sostenida. Configuración propia `ddk_experimental_v1.json`.
SHA-256 configuración: 89fd9ac962b05b2180c3f5325f9abc7175aac0378b184394a2c8d23b322b5a5a.
SHA-256 motor comprobado: 210a6be83b8a4479d774a89833e23bf25cd99201883f17d26fe8bf3eb7e1e1df.

FastAPI sirve `/ddk` y `POST /ddk-analysis`. Cada petición conserva WAV completo,
con intervalo explícito redondeado hacia arriba a índices de muestras y límites
efectivos exportados. Selección de todo el tramo, sin ventana central de 3 s.
La revisión reenvía el mismo WAV, hash esperado y operaciones, recalcula el
original determinista y aplica la revisión en backend. No confía en medidas
aportadas por el cliente. Audio temporal en memoria; sin persistencia de sesiones.

La interfaz reutiliza parseWav/encodeWav y el PCM AudioWorklet existente. El
controlador DDK añade límite de 15 s y cancelación segura de preparación. No se
cambian el controlador ni algoritmos de la pantalla de vocal sostenida.
Añade enlace de navegación, no una reconstrucción del frontend anterior.

## Estados y resultados parciales específicos

- `detection`: completed / empty / failed. Empty conserva contorno y decisiones;
  conteo candidato 0, tasas null/no_evidence. Failed reserva errores esperados
  DetectionError, con cifras dependientes null y etapas automáticas bloqueadas.
- `grouping`: completed / not_requested / blocked. Sin anclaje explícito no se
  agrupa. Tríadas candidatas, nunca reconocimiento pa/ta/ka.
- `calculation`: completed / partial / blocked. Partial representa medidas
  matemáticamente indefinidas, p. ej. menos de tres intervalos para DT/CV;
  conserva otras cifras definidas. No equivale a detector fonéticamente válido.
- `review`: not_requested / draft / completed. Draft tiene acontecimientos,
  pero NO métricas revisadas. Completed exige todas las etiquetas comprobadas;
  una lista vacía requiere confirmación explícita de ausencia.
- Revisión completa expone también `reviewed_result.calculation_status`: puede
  ser partial si faltan intervalos aunque la revisión esté completa.
- Una revisión manual puede recuperar acontecimientos tras detector empty/failed.
  Estado y original fallidos se conservan: no se sobreescribe el resultado
  automático para simular éxito. Estado global describe el recorrido automático.
- HTTP 422 entrada/revisión inválida, 413 tamaño excesivo, 503 excepción
  inesperada. No se captura cualquier excepción como falso éxito parcial.

`automatic_original`, `manual_modifications` y `reviewed_result` separados.
Exportación añade captura y `pending_review` si hay cambios no recalculados.
Identificadores únicos incluso tras eliminar; tiempos finitos, distintos y dentro
 del intervalo. Operaciones ordenadas add/delete/move/label/restart. Reinicios
rompen agrupaciones/intervalos y transiciones excluidas se exportan. Pausas largas
no se eliminan. No se ajustan omisiones ni se completa una tríada inventando picos.

## Interfaz comprobada

Captura/subida -> selección manual -> candidatos -> anclaje opcional -> revisión.
Contorno de energía y umbral, candidatos aceptados/rechazados, escucha de entorno,
tabla exacta, edición de tiempos y etiquetas, reinicios, adición/eliminación,
agrupaciones, intervalos utilizados/excluidos, resumen y JSON. Cambiar audio o
límites invalida resultados y aborta la espera; el backend puede terminar la tarea.
Cambiar edición/confirmación invalida inmediatamente medidas revisadas. Cambiar
anclaje requiere recalcular y avisa que descarta la revisión previa. Descartar
revisión es explícito. Original automático siempre separado de las modificaciones.

La etiqueta visible automática es núcleos candidatos / tríadas candidatas / tasa
automática estimada. Solo tras confirmación manual: sílabas/ciclos revisados.
Colores señalan decisiones técnicas, no normalidad. Adaptación a 390 px comprobada.
Capturas sintéticas se generan en los artefactos de Actions; no son pacientes.

## Resultados locales exactos

Python 3.12.14, dependencias originales requirements.lock; Praat oficial 6.4.27,
archivo descargado verificado contra SHA-256 original del Dockerfile.
Node 24.19.0, Playwright 1.51.1, Chromium 134.0.6998.35 (build 1161).

- Suite final completa: **310 passed, 6 xfailed, 1 warning in 198.25s (0:03:18)**.
- Suite DDK específica: **80 passed, 1 warning in 10.72s**.
- JavaScript final: **19 passed, 0 failed**, duración 98.807901 ms.
- Chromium DDK: **35 comprobaciones aprobadas**, API real, WAV sintético,
  captura de micrófono sintético, revisión, integridad original, exportación,
  errores, estados empty/failed e invalidación, móvil; cero pageerrors.
- Chromium vocal sostenida: **24 comprobaciones anteriores aprobadas**,
  incluido análisis real Praat y micrófono sintético.
- Comprobación HTTP adicional: **17 comprobaciones aprobadas en localhost**,
  incluyendo revisión manual, hash, siete grupos, 422/413 y silencio con tasa null.
- Advertencia conservada: deprecación BlockingPortal de Starlette/AnyIO.
- No hay Docker local; los resultados anteriores NO son resultados de contenedor.

36 combinaciones limpias: 6 ritmos (2,4,6,8,10,12/s) x 2 tasas x 3 profundidades.
Todas cumplen conteo exacto y error máximo <=10 ms. Pruebas matemáticas usan
referencia con Fraction/varianza independiente: tolerancia 1e-9, DT muestral.
Preservación: diff vacío en módulos pitch/jitter/shimmer/hnr/praat_runner, scripts
Praat, experimental_v1, dependencias, Dockerfiles y TODAS las pruebas históricas.

## Caracterización, sin ocultar pérdidas

Informe reproducible completo: `ddk_synthetic_report.json` (semilla 606).
La envolvente no es voz humana. Ruido: amplitud gaussiana del generador, NO SNR
medido/calibrado. Caso débil PCM16 (.00001) queda cuantificado a cero: no evidencia.

| Caso | Referencia | Candidatos | Falsos positivos | Perdidos |
|---|---:|---:|---:|---:|
| Limpio | 21 | 21 | 0 | 0 |
| Débil PCM16 | 21 nominales | 0 | 0 | 21 nominales |
| Transitorios | 21 | 21 | 0 | 0 |
| Ruido sigma .003 | 21 | 21 | 0 | 0 |
| Ruido sigma .03 | 21 | 21 | 0 | 0 |
| Ruido sigma .15 | 21 | 0 | 0 | 21 |
| Clipping | 21 | 21 | 0 | 0 |
| Omisión | 20 | 20 | 0 | 0 |
| Acontecimiento extra a 55 ms | 22 | 22 | 0 | 0 |
| Pausa .2 / .5 / 1 s (cada caso) | 21 | 21 | 0 | 0 |
| Silencio | 0 | 0 | 0 | 0 |
| Solo ruido sigma .03 | 0 | 0 | 0 | 0 |

Error máximo de centros emparejados en estos casos: 1.6666666666669272 ms.
En casos sin evidencia, tasa null; no sustituir por cero ni por la cifra nominal.
El conteo correcto con clipping NO valida señal ni precisión articulatoria.
La rejilla de 5 ms introduce variación temporal: ritmo sintético uniforme de 6/s
puede mostrar CV ~1.47 %, sin corregirlo silenciosamente hacia cero. La DT/CV
son exactas respecto a los tiempos detectados, no respecto a una articulación.

## Criterios de cierre y pendientes

Matemática, matriz sintética limpia, estados null/fallo, replay, auditoría y
frontend/API locales comprobados. No se ha relajado un umbral para pasar pruebas.
Caracterización documenta pérdidas fuera de señales limpias/separables.
Seis xfail históricos siguen siendo incumplimientos de hitos anteriores, intactos.

**Pendiente en esta revisión:** ejecución Docker/Actions de la rama; Preview en
Vercel y verificación real remota. La API Vercel devuelve 403 para el equipo;
no se dispone de CLI autenticada como alternativa. Estado y logs no se inventan.
Se actualizará la evidencia con los resultados remotos observables.

**6A NO declarado cerrado.** Cierre y fusión requieren revisión final de Andrea.
**6B pendiente**, sin criterio de reclutamiento humano obligatorio en 6A.
