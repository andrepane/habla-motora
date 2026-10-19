# Hito 7B.1 — pausas revisadas y velocidad articulatoria operacional

Base: main `58c2e6557725194512e2bbdce5de41eebdfeedcc`. Protocolo `phrase_pause_review_v1`, mínimo fijo/versionado 250 ms. Sin detector, ASR, inferencia fonética ni clasificación automática de respiraciones. 7B.2 queda separado. Validación humana pendiente; sin diagnóstico ni baremos.

## Dependencias e integración

Capa independiente sobre `/phrase`: mismo WAV íntegro, selección, intento, modalidad, modelo y revisión de contenido de 7A. No altera sus fórmulas, resultados ni endpoint; tampoco vocal sostenida o DDK. `POST /phrase-pause-analysis` recibe file, context_json, review_json, expected_file_sha256 y temporal_json. Recalcula 7A mediante su función original y contrasta file/context/review/config/engine SHA-256 con `source_dependencies`. No acepta numeradores ni duraciones calculados por el cliente. `GET /phrase-pause-protocol` expone la convención versionada.

Cambios en cualquier dependencia invalidan resultado y confirmación temporal; la interfaz archiva y vacía las anotaciones vinculadas al contexto anterior. Cambios en intervalos/estado/nota invalidan métricas y confirmación sin borrar el borrador. Reemplazar la respuesta 7A por una validación sin revisión también invalida 7B.1. AbortController + revisión rechazan respuestas tardías. Intentos independientes, sin agregación entre modalidades o grabaciones. Una revisión 7A puede estar completada aunque alguno de sus recuentos no esté confirmado; las dos tasas de 7B.1 mantienen esa independencia.

## Pausa operacional y anotación

Interrupción interna sin articulación verbal ni vocalización llena, confirmada por escucha contextual y onda ampliada, con duración >=250 ms. No es silencio acústico: puede contener respiración o ruido ambiente sin producción. Ausencia de F0/sonoridad/energía no demuestra pausa. Se resta toda su duración, no solo el exceso de 250 ms. Las interrupciones inferiores quedan en el tiempo operacional.

Anotaciones absolutas `[start_sample,end_sample_exclusive)`, enteros: selección `[a,b)` y evento `[p,q)` requieren `a < p < q < b`. Los intervalos que tocan extremos exigen revisar los límites 7A; no se recortan. La captura mantiene los originales de 7A (mono PCM16/24/32, 44.1/48 kHz, 20 s, 4.000.000 bytes). Un archivo truncado por límite conserva la advertencia y solo permite caracterizar el fragmento con recuentos manuales, sin presentarlo como objetivo completo.

Umbral: `ceil(Fs*250/1000)` muestras, 11.025 a 44.1 kHz y 12.000 a 48 kHz. Duraciones almacenadas por muestras; precisión de almacenamiento no equivale a exactitud humana.

Cada intervalo contiene id único, límites, classification, breath_present (yes/no/uncertain), within_word, nonarticulatory_confirmed y note. Clasificaciones:

- `pause`: interrupción confirmada >=250 ms.
- `below_threshold`: interrupción <250 ms, no se resta.
- `consonantal_closure`: oclusión, no se resta aunque sea larga.
- `uncertain`: no permite cierre global.
- `other_nonverbal`: interferencia no verbal; no permite cierre global.

Los intervalos nuevos empiezan como `uncertain`; no se infiere su clasificación. Una pausa intrapalabra solo se admite si el revisor declara `within_word=true` y confirma explícitamente una interrupción no articulatoria claramente separada del gesto consonántico y del resto de la producción (`nonarticulatory_confirmed=true`). Ante duda entre pausa/oclusión/transición, `uncertain`; nunca convertirla en pausa por duración.

Respiración: atributo del intervalo de pausa completo (silencio + sonido respiratorio), sin doble conteo. «Eh» y otras pausas llenas, fragmentos, repeticiones y reinicios permanecen en tiempo y recuentos revisados 7A. Silencios a ambos lados de «eh» se valoran por separado, sin unir atravesando la vocalización. Silencios iniciales/finales se excluyen mediante selección 7A, no se cuentan como pausas internas.

Sin solapamientos entre anotaciones; duplicados o etiquetas contradictorias requieren corrección explícita. Pausas contiguas requieren revisión y un único intervalo continuo. Pausas separadas por articulación real siguen separadas, sin fusión por proximidad. Nunca se calcula una unión silenciosa.

Conservadurismo explícito: esta versión no define una sustracción adicional para tos/risa/voz ajena. Un evento registrado como `other_nonverbal` deja el conjunto en draft/not_evaluable. Si impide decidir producción/pausa, todas las métricas globales quedan null, incluidas número, total, porcentaje, media y mediana. No se presenta el subtotal de intervalos ya revisados como resumen global. Esta regla es deliberadamente conservadora incluso para eventos claramente no verbales: resolverlos requeriría otro protocolo de denominador/numerador.

## Interfaz y confirmación

Panel 7B.1 por intento, sobre la misma onda 7A. Activar «Anotar intervalos» hace que el arrastre prepare límites sin cambiar selección, revisión ni métricas 7A. Se añaden/editan índices, clasificación, respiración y declaraciones intrapalabra. Bandas diferenciadas y etiquetas; ampliación de intervalo y escucha con 250 ms de contexto a cada lado, limitada al WAV. Zoom y escucha no cambian índices ni resultados. Se puede escuchar una región sin afirmar que es una pausa.

Confirmación global: «He revisado toda la selección, he anotado todas las pausas del protocolo y no quedan regiones inciertas ni interferencias sin resolver». Estados `not_started`, `draft`, `confirmed`, `not_evaluable`. API exige reviewed_all=true para confirmed y nota para not_evaluable. Interfaz inicia en borrador. confirmed no se admite con uncertain/other_nonverbal. Selección y producción presentes confirmadas en 7A son necesarias para publicar métricas. Lista vacía solo significa cero pausas después de revisar y confirmar todo.

## Fórmulas

N = b-a; ni = qi-pi para cada pausa aceptada. Suma primero muestras enteras.

- Duración seleccionada D = N/Fs, idéntica a 7A.
- `pause_duration_s` P = sum(ni)/Fs.
- `operational_speech_time_s` T = (N-sum(ni))/Fs.
- `pause_percent` = 100*sum(ni)/N.
- `pause_count` K = número de pausas aceptadas.
- `pause_mean_duration_s` = P/K si K>0.
- `pause_median_duration_s`: mediana de ni/Fs; par: media de los dos centrales.
- `reviewed_syllable_articulation_rate` (principal) = Ns/T, sílabas/s.
- `reviewed_word_articulation_rate` (complementaria) = 60*Nw/T, palabras/min.

Ns/Nw exclusivamente recuentos reales confirmados de 7A, nunca referencia canónica ni relleno automático. Desviaciones: recuentos reales incluidos en 7A; palabras completas repetidas/reiniciadas incluidas, fragmentos sin palabra completa pero con sílabas confirmadas, sustituciones reales, «eh» cero palabras léxicas/una sílaba si así se confirmó. No se resta su tiempo. No se publica una tasa «fluida» o «articulación pura».

T conserva oclusiones, interrupciones <250 ms, pausas llenas y disfluencias articuladas. No es tiempo de fonación ni movimiento articulatorio puro. El umbral y su trato de respiraciones cortas son convenciones pendientes de validación humana. En frase breve, cambios pequeños de límites pueden afectar mucho a la tasa. Lectura y seguimiento visual siguen siendo factores de confusión.

Ejemplo: D=8 s, pausas 0.5 y 1.5 s -> P=2, T=6, 25%, K=2, media/mediana=1 s. Con 14 palabras y 25 sílabas revisadas: 140 palabras/min y 25/6 sílabas/s.

## Null, cero y errores

Cualquier bloqueo global deja TODAS las métricas null: selection_unconfirmed, content_review_pending, no_production, pause_review_pending, pause_review_uncertain o pause_review_not_evaluable. Revisión incierta/interferencia nunca publica resumen global definitivo. Subtotales únicamente dentro de audit, rotulados como evidencia parcial. Cambios de dependencia se rechazan como stale_dependency y el cliente invalida antes de recalcular.

Con revisión confirmada sin pausas: P=0, K=0, %=0, T=D; media y mediana null/no_pauses. Recuento confirmado cero con presencia y T>0 produce tasa cero; no confirmado -> null/word_count_unconfirmed o syllable_count_unconfirmed independientemente. Ausencia de producción -> todo null/no_production, no «silencio=pausa». T<=0 -> tasas null/nonpositive_operational_speech_time, nunca infinito. Con intervalos internos válidos no solapados T es positivo por construcción.

422: índices, revisión, dependencias, solapamientos, contradicciones o JSON inválidos. 413: archivo >4.000.000 bytes. 503: error inesperado con mensaje genérico. Error no se convierte en cero ni se conserva como resultado actual. Estado temporal y cálculo separados; tasas incompletas no eliminan estadísticas válidas salvo bloqueo global. Media/mediana null/no_pauses no impiden completed cuando ambas tasas sí están disponibles.

## Auditoría, exportación y validación

Exportación completa 7A añade `pause_review_7b1` por intento: borrador actual, respuesta actual, historial de cambios/resultados invalidados/errores y revisiones. Respuesta incluye source_7a recalculado íntegro, hashes fuente/config/motor/revisión temporal, intervalos, muestras, fórmulas, unidades, numeradores y denominadores. WAV/activos originales intactos en el mismo paquete. Datos de sesión; exportar antes de cerrar. No se añade persistencia remota ni importación de pacientes. El paquete permite reproducir el cálculo por API; no existe importador UI nuevo. Hash identifica datos, no certifica acierto del revisor.

Cierre técnico: oráculo Fraction, seis formatos PCM/frecuencia, umbral ±1 muestra, suma/mediana/porcentajes, límites, solapamientos, estados, incertidumbre intrapalabra, interferencias globales, ausencia/cero/null/error, numeradores independientes, variantes y cambios fuente. Sintéticos verifican cálculo/flujo, no competencia perceptiva ni reconocimiento. Navegador real con API comprueba anotación/zoom/escucha/confirmación/exportación/invalidez/intentos/móvil y regresiones previas sin cambiar sus pruebas. Suite completa y Docker requeridos antes de PR.

Pendiente en humanos: concordancia intra/interrevisor en clases y límites, reproducibilidad de recuentos, sensibilidad al umbral, repetibilidad y utilidad en poblaciones de interés. 7B.2 podrá proponer candidatos solo tras protocolo y validación propios; no pertenece a este módulo.
