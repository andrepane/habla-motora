# 7B.2: ayuda experimental opcional en /phrase

La integración ejecuta exclusivamente `pause_detector_energy_v1`, por acción explícita del revisor. No cambia el algoritmo, sus parámetros, el banco bloqueado ni sus criterios. A+B y Praat siguen siendo investigación. No hay validación humana ni garantías de rendimiento en pacientes.

## Contrato y dependencias

`GET /phrase-candidate-protocol` identifica el motor congelado y su configuración. `POST /phrase-candidates` recibe el WAV íntegro, `context_json` de 7A y `expected_dependencies_json` (SHA-256 del WAV, contexto, configuración y motor). Revalida el WAV y la selección mediante 7A; no ejecuta reconocimiento ni genera resultados manuales. El contexto incluye frase, intento, modalidad, administración y selección. El hash del contexto identifica esos datos sin utilizar recuentos de contenido como evidencia acústica.

Estados de ejecución: `completed`, `not_evaluable`, `failed`, `stale`. Solo `completed` puede devolver una lista vacía; los otros estados mantienen candidatos `null`. Los errores de contrato siguen usando HTTP 422 y el límite de subida HTTP 413. La ejecución original del motor se conserva sin transformación, con configuración, hashes, evidencia acústica y trazabilidad de frames por hash. Los candidatos heredan las dependencias de su ejecución contenedora.

## Separación de responsabilidades

El exportado de cada intento añade `candidate_review_7b2`: ejecución y candidatos inmutables, decisiones individuales, vínculos hacia anotaciones manuales e historial. `pause_review_7b1` continúa separado. La copia crea una anotación `uncertain`, nunca `pause`, y retira la confirmación temporal mediante la invalidación ya existente de 7B.1. Los límites originales y los editados se registran en la decisión y vínculo. No se añade ningún campo al esquema manual cerrado de 7B.1.

Rechazar o regenerar no modifica anotaciones ni resultados manuales. Al regenerar se archivan ejecución, decisiones y vínculos; las anotaciones manuales permanecen. Los cambios en WAV o contexto 7A invalidan y archivan las propuestas. Los cambios manuales de 7B.1 no modifican la evidencia automática. Cada intento mantiene su propia instancia. Las respuestas tardías no pueden sustituir una ejecución vigente.

Solo la revisión manual global confirmada de `phrase_pause_review_v1` puede producir métricas definitivas. Revisar todas las propuestas no confirma la selección completa; una lista vacía no confirma ausencia de pausas. Se mantienen las reglas de intrapalabra, respiración, interferencias y umbral manual de 250 ms. El mínimo automático continúa siendo 80 ms.

## Límites de uso

El detector puede proponer cierres consonánticos, actividad débil e interrupciones breves, omitir regiones y requerir correcciones de límites. La capa discontinua en la onda corresponde a propuestas, no a pausas confirmadas. No hay aceptación global ni conversión directa a pausa. La edición por muestras se aplica solo a la copia; la propuesta original nunca cambia.

Las pruebas nuevas cubren API, estados, auditoría, copia `uncertain`, rechazo, regeneración, límites editados, independencia de intentos, exportación y móvil. El workflow Docker conserva las regresiones de vocal, DDK, 7A y 7B.1 y añade el navegador 7B.2. Las señales usadas son controladas/sintéticas, sin ajuste con WAV humanos ni reevaluación para optimizar el banco bloqueado.
