# Hito 8B — Prosodia v1 en /phrase

Integración de `phrase_prosody_v1` a partir del Hito 8A cerrado en
`23ba91267d5f88314d555059a8c7d28865bb275a`. No se repite el bloqueado, no se
recalcula la selección de configuración ni se usan WAV humanos para esta integración.

## Contrato HTTP

`GET /phrase-prosody-protocol` publica identidad, configuración y versiones.
`POST /phrase-prosody-analysis` acepta multipart:

| Campo | Contenido |
| --- | --- |
| `file` | WAV completo, hasta 4.000.000 bytes |
| `context_json` | El contexto validado de 7A, sin reconstruirlo: `phrase_id`, `attempt`, `modality`, `selection_confirmed`, `selection` con `start_sample` y `end_sample_exclusive`, `administration` y `recording_limit_reached` |
| `expected_dependencies_json` | Cinco SHA-256: `file_sha256`, `context_sha256`, `selection_sha256`, `config_sha256`, `engine_sha256` |

Los límites de muestras están en `context_json.selection`, la única selección.
Los hashes de archivo/contexto proceden de 7A; selección se codifica como JSON
canónico de los dos enteros. Configuración/motor proceden del protocolo.
El servidor vuelve a calcular las dependencias con el módulo congelado: una
discrepancia produce `stale`, métricas nulas con razón y ninguna curva.
Una selección sin confirmar no se evalúa. Ningún campo permite elegir parámetros.

La respuesta conserva íntegramente métricas `value/reason`, frames auditables con
tiempo absoluto/relativo, Hz y ST, gaps, counts, warnings, cobertura, native_audit,
reference_st, configuración, dependencias, runtime (Praat real y hash binario),
protocolo y run_id. El adaptador añade identidad verificable y
`phrase_prosody_integration_v1`. En errores previos al motor no se atribuye una
versión de Praat ejecutada. HTTP 422 indica petición inválida; 413, tamaño;
503, imposibilidad de verificar identidad o completar el transporte. La interfaz
conserva identidad y contexto de una petición fallida sin inventar resultados.

## Invariantes acústicos

La configuración es exclusivamente `phrase_prosody_freeze_v2`,
`filtered_800_03__0`. El adaptador verifica cada vez los bytes de freeze,
código agregado, módulo y evaluador antes de invocar el extractor existente.
No se modifica el extractor, los perfiles, los bancos ni los umbrales.

| Invariante | Valor |
| --- | --- |
| SHA-256 freeze.json | `047fac7379b09dfae0f545569e21ec34463ab7227255507ceeba68f8c6b6a24c` |
| SHA-256 código agregado congelado | `5d3878cf5ed100276acc0c7798a702666049e49ed6d2b33fe8043c15f6539701` |
| SHA-256 módulo acústico | `4ae1b67439ea76934f7c740da1732ddf3d8ac4ded6a8652de5c34baafd99a8c8` |
| Contexto exterior | 0 s |
| Discontinuidad | Regla congelada, delta_t <= 10 ms |
| Soporte P10–P90 | `distributed`, sin cambios |
| Semitonos | Referencia: mediana nativa de F0 de esa selección; se muestran los f0_st exportados por el motor |
| Praat requerido | 6.4.27, comprobado por el motor existente |

## Dependencias y estados

Cada intento mantiene su resultado e historial. Cambiar WAV, selección,
confirmación, intento, modalidad o contexto/versionado de frase invalida Prosodia.
La identidad del servidor se comprueba al analizar, recuperar foco/visibilidad y
antes de exportar. Cambiar configuración/motor/versiones exige un nuevo análisis;
no hay ajuste automático. Se abortan peticiones anteriores y se rechazan
respuestas tardías por revisión y fuente.

Editar recuentos de revisión 7A, pausas 7B.1 o candidatos 7B.2 no cambia la curva.
No forman parte de sus dependencias ni disparan una extracción. La selección
confirmada validada se conserva aunque la revisión de tasas esté pendiente.

Estados del motor: `completed`, `partial`, `not_evaluable`, `failed`, `stale`.
La interfaz añade `idle` y `processing`. En `partial` muestra los valores válidos
y las razones de las métricas nulas. En `stale` retira la curva y los valores
actuales, conservando las respuestas previas como historial explícitamente inválido.
Nunca se convierte `null` en cero; cero es un valor válido.

## Interfaz y exportación

Prosodia ocupa una sección propia después de candidatos 7B.2. La curva tiene
prioridad sobre cuatro métricas principales: mediana, rango robusto, tendencia
global OLS y cobertura. Las restantes métricas aprobadas, duración exacta 7A,
conteos y auditoría están en «Detalles técnicos».

El SVG usa puntos y segmentos rectos únicamente entre frames válidos consecutivos.
Los indefinidos cortan los segmentos; no hay interpolación, suavizado, corrección
de F0 ni segunda selección. Se distinguen huecos y bordes sin análisis.
Hover/tap muestra el frame real, su tiempo y valor; no interpola valores.
Hz/ST y segundos/0–100 % son transformaciones de visualización. Zoom, rueda,
desplazamiento y reset modifican solo la vista. La reproducción reutiliza el audio
original, limitada a 7A o a ±250 ms del cursor dentro de 7A.

Se muestran los códigos técnicos del extractor y las razones de soporte
insuficiente, sin crear nuevos umbrales ni avisos clínicos. Se incluye la nota:
«Medidas descriptivas de F0 sobre habla conectada. No constituyen una interpretación
clínica automática.»

La exportación `phrase_battery_export_v1` conserva sus campos previos y añade por
intento `phrase_7a` y `prosody_8a_8b`; mantiene separados `pause_review_7b1` y
`candidate_review_7b2`. Prosodia contiene estado, razón, `results_current`,
`current_response` completo, historial y metadatos de vista (unidades, eje, viewport,
interpolation=false, smoothing=false). La referencia ST, null+reason, frames,
huecos, avisos, hashes y versiones permanecen en la respuesta exportada.

## Verificación

Pruebas nuevas: `tests/test_phrase_prosody_api.py`,
`tests/phrase-prosody.test.mjs`, `tests/phrase-prosody-browser.mjs`.
Cubren selección e identidad, intentos/modalidades, respuestas tardías, estados,
soporte, null/cero, topología de huecos/bordes, unidades/referencia, normalización,
zoom/cursor/audio, independencia de pausas/candidatos, exportación y móvil.
El workflow Docker existente incorpora el navegador 8B sin retirar sus regresiones.
La evidencia final se conserva en `reports/prosody/integration_8b/`.

Limitaciones: verificación acústica sintética heredada del 8A, validación humana
pendiente; sin interpretación clínica. La disponibilidad del protocolo es necesaria
para confirmar vigencia antes de exportar. La integración no añade persistencia
automática entre recargas: se conserva la exportación explícita existente.
