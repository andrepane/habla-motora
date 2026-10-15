# Hito 7A — frase estandarizada: duración y velocidad global

Base de implementación: main `cda158ac1f4683553519ca2370dcf91b0a0fbdd1`.
Protocolo aprobado por Andrea el 15/10/2026. Validación técnica; validación humana pendiente. Sin diagnóstico, baremos, ASR, alineación forzada, reconocimiento fonético, detector de sílabas ni detección de pausas. Vocal sostenida y DDK v1/v2 permanecen intactos.

## Estímulo congelado

`phrase_es_01_v1`: **La niña corta papel con tijeras y pega las tiras pequeñas sobre la mesa.**

14 palabras; 25 sílabas canónicas, sin sinalefas:

La / ni-ña / cor-ta / pa-pel / con / ti-je-ras / y / pe-ga / las / ti-ras / pe-que-ñas / so-bre / la / me-sa.

1+2+2+2+1+3+1+2+1+2+3+2+1+2=25.

Estos recuentos pertenecen al estímulo versionado, no son detecciones acústicas. No se describe como frase clínicamente validada ni fonéticamente equilibrada.

## Administración y dos intentos

Principal: `direct_reading_v1`, para personas con lectura funcional. Consigna: **«Lee esta frase en voz alta una vez, a tu ritmo habitual, intentando decirla completa y con claridad»**. Frase visible durante toda la producción, sin resaltado, barrido o marcas de ritmo. No se reproduce modelo auditivo en esta condición. La lectura/decodificación y el seguimiento visual son factores de confusión explícitos; su efecto queda pendiente de validación humana.

Un ensayo de familiarización y dos intentos independientes; descanso recomendado de 20 s, sin seleccionar el más rápido ni agregar resultados. Cada intento conserva su archivo, selección, revisión, modalidad e identidad. Se permite reemplazar explícitamente una grabación conservando activos originales e historial en la exportación.

Variantes separadas: `auditory_model_with_text_v1` y `auditory_model_only_v1`. No se mezclan entre sí ni con lectura directa. No se proporciona ni sintetiza un modelo de fábrica: para registrar la variante se aporta un WAV explícito, identificado por SHA-256, y se reproduce completo. El texto se oculta en la variante sin texto. Comparaciones entre modelos distintos tampoco son equivalentes: el hash/identificador se conservan. El backend recibe la declaración del modelo administrado; su presentación es una declaración de administración, no una detección acústica. La exportación integra los bytes del modelo aportado. No se afirma validación ni estandarización humana de un modelo aportado.

Grabación AudioWorklet PCM16, primer canal, 44.100/48.000 Hz; restricciones solicitadas y ajustes consultables registrados, junto con fechas de captura. La señal visual aparece tras un segundo de audio capturado; no se calcula tiempo de reacción. Conservar margen posterior al terminar y delimitar manualmente. La codificación cuantifica a PCM16; no normaliza. El navegador/sistema puede introducir procesamiento o adaptación interna de frecuencia: los ajustes no certifican captura bit a bit.

Subida: WAV PCM mono 16/24/32, 44.100/48.000 Hz; máximo 20 s y 4.000.000 bytes. Validador independiente, sin alterar el límite de 15 s de DDK. Integridad de RIFF/fmt/datos, alineación, frecuencia/byte rate, frames y truncado. No se recorta, convierte ni filtra el WAV recibido. Se conserva byte a byte y se exporta completo. Grabación limitada exactamente a 20 s; el corte por límite se registra y bloquea tasas de referencia. No se exige terminar rápido ni en una respiración.

## Selección y revisión

Interfaz `/phrase`, metadatos `/phrase-protocol`, endpoint independiente `POST /phrase-analysis`.

Selección manual de toda la producción, primera a última emisión; incluye errores, pausas, fragmentos y reinicios interiores. No hay ventana central de 3 s ni selección por F0. Arrastre de onda, índices enteros o cursor del reproductor. Autoridad: intervalo `[start_sample,end_sample_exclusive)`, con 0 ≤ inicio < fin ≤ número de muestras. Los límites deben confirmarse; la selección completa por defecto no equivale a selección confirmada.

Coincidencia manual: `pending`, `exact_once`, `different`, `uncertain`. `exact_once` exige la secuencia textual completa una vez, sin omisiones, añadidos, sustituciones, fragmentos extra ni reinicios; no exige imitar el acento ni constituye un análisis fonético. Mismos recuentos con secuencia distinta no habilitan tasas de referencia. La interfaz no transcribe ni reconoce el contenido.

Producción: `pending`, `present`, `absent`. Dos recuentos separados, con valor explícito y confirmación independiente. Confirmar palabras no confirma sílabas; los recuentos no se rellenan desde el objetivo. Eventos manuales: omission, repetition, substitution, fragment, restart, addition, filled_pause, uncertain; identificadores únicos, notas/transcripción manual opcionales.

Palabras revisadas = tokens ortográficos léxicos completos realmente producidos, incluyendo repeticiones; «del» es una palabra, los fragmentos no son fracciones de palabra. Sílabas revisadas = sílabas manualmente identificables, incluidas las de fragmentos, repeticiones y pausas llenas cuando se confirma su carácter silábico. «pa-pa-papel»: una palabra completa, cuatro sílabas. «Eh»: cero palabras léxicas y una sílaba si así se confirma; tos/risa no reciben sílabas automáticamente. No se aplica un silabificador al texto para fingir recuentos producidos.

## Matemática y estados

D=(fin−inicio)/Fs, sin redondear, incluye toda pausa interior.

| Campo | Numerador | Fórmula |
|---|---|---|
| reference_word_rate | 14 palabras del estímulo | 60×14/D |
| reference_syllable_rate | 25 sílabas canónicas del estímulo | 25/D |
| reviewed_word_rate | Palabras manualmente confirmadas | 60×Np/D |
| reviewed_syllable_rate | Sílabas manualmente confirmadas | Ns/D |

Referencia: solo con selección confirmada, producción presente y coincidencia `exact_once` confirmada, sin corte por límite. Las sílabas de referencia son canónicas, no núcleos acústicamente verificados. Las tasas revisadas son independientes de la coincidencia; cada recuento necesita confirmación propia. Una revisión en borrador no publica tasas definitivas. Duración del tramo disponible aunque el contenido esté pendiente; duración de producción solo tras confirmar presencia y selección.

Cada tasa conserva value, reason, unit, numerator, count_basis y denominator_s. Motivos null: pending_content_review, target_mismatch, target_match_uncertain, word_count_unconfirmed, syllable_count_unconfirmed, no_production, selection_unconfirmed, recording_limit_reached. Una selección inválida o duración cero se rechaza (422), en lugar de inventar una tasa cero/invalid_duration dentro de una ejecución válida.

Cero es un valor explícitamente confirmado y distinto de null. Una tasa revisada cero puede resultar de un recuento confirmado cero sobre un intervalo válido con producción presente. Si se confirma ausencia, pueden registrarse recuentos cero, pero duración de producción y tasas quedan null/no_production; la duración de observación sigue disponible. Energía baja, ruido o silencio digital jamás confirman por sí mismos presencia o ausencia.

Selección: not_requested/draft/completed. Revisión: not_requested/draft/completed; completed significa declaraciones enviadas y confirmadas, no que todos los recuentos sean conocidos. Cálculo: blocked/partial/completed; cuatro tasas definidas para completed. Global: completed o partial, sin significado clínico. Un campo no disponible no borra los restantes. Pausas, tiempo sin pausas y velocidad articulatoria: null/not_implemented, reservados para 7B.

422 = archivo, índices, contexto o revisión inválidos; 413 = más de 4.000.000 bytes; 503 = fallo inesperado, sin filtrar detalles internos ni devolver medidas falsas.

## Integridad y exportación

SHA-256 del WAV, configuración, motor, contexto y revisión. El contexto vincula bytes WAV, selección, frase, modalidad, intento, administración y corte por límite. Para revisar se exige reenviar el mismo WAV con hash esperado y el token de contexto actual. Cambiar cualquiera invalida la revisión previa; no se reutilizan confirmaciones.

Cambios en revisión invalidan tasas mostradas, conservando únicamente la identidad del contexto cuando corresponda; cambiar un recuento exige reconfirmarlo. AbortController y número de revisión rechazan respuestas tardías. Dos intentos no comparten resultados. No hay persistencia de servidor ni mezcla automática de modalidades.

Exportación JSON integra WAV originales en base64, modelos aportados, activos anteriores, metadatos de captura, borrador actual, respuestas completas, cambios ordenados y resultados invalidados marcados como históricos. Descarga independiente del WAV original idéntico byte a byte. La conservación es de sesión/exportación; no se crea una base de pacientes ni almacenamiento remoto. Cerrar la página sin exportar pierde la sesión.

## Cierre

Fórmulas contrastadas con Fraction, tolerancia absoluta ≤1e-9; duración exacta por índices. Matriz de frecuencias/PCM, límites, formato, hash, independencia de recuentos, discrepancias de secuencia con idéntico recuento, omisión/repetición/sustitución/fragmento/reinicio, null/cero/fallo, revisión desactualizada y original intacto. Pruebas unitarias de cancelación/captura/invalidez y flujo real navegador→API→resultado→exportación, con micrófono sintético y dos intentos.

Suite general, Docker, HTTP y navegador previos sin relajar las seis xfail conocidas. CI añade el navegador de frase y su captura a los artefactos. El cierre técnico no certifica comprensión, memoria, lectura, precisión de límites humanos ni concordancia de recuentos: queda pendiente validación en participantes. Revisión final de Andrea antes de PR/cierre del hito.
