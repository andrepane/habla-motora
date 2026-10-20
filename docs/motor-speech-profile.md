# Hito 9 — Perfil integrado de habla motora v1

Base: main `85d6e81d83cf37c5cf802c795601e28ee8f09042`. Ruta `/profile`.
Implementación de las fases 9.1–9.3 y de exportación/comparabilidad de metadatos.
No altera motores, configuración, criterios ni bancos de hitos previos.

## Arquitectura

- `backend/motor_profile_routes.py`: sirve página e identidad en
  `GET /motor-profile-protocol`. Lee versiones y hashes; no ejecuta análisis.
- `frontend/motor-profile-store.js`: registro IndexedDB local,
  `evaluation -> task -> attempt -> source result`, artefactos por SHA-256,
  exportación/importación y verificación de integridad.
- `frontend/motor-profile.js`: proyector puro `motor_speech_profile_v1`, sin
  imports, acceso a red, audio, estadística ni motores. Copia campos permitidos,
  comprueba identidades, dependencias y versiones; produce estados y recuentos
  administrativos de completitud.
- `frontend/profile-bridge.js`: conecta resultados aceptados e invalidaciones de
  las tareas con una evaluación/intento identificados en la URL. Fuera de ese
  contexto las páginas siguen funcionando como antes.
- `frontend/motor-profile-ui.js`: cinco bloques, mini-curva, detalles y exportación.

No hay backend de pacientes, autenticación, multiusuario, permisos ni sincronización.
IndexedDB persiste entre navegación y recargas en el mismo navegador/origen.
No garantiza conservación si el usuario borra datos o el navegador los elimina:
el paquete exportado es la copia recuperable entre dispositivos/orígenes.

## Identidad y uso

1. Crear una evaluación local: UUID, timestamps, zona horaria, versión de batería,
   identificador opcional de caso y notas opcionales.
2. Crear intentos de vocal, DDK y frase. No se selecciona automáticamente ninguno.
3. Elegir explícitamente el representativo de cada tarea.
4. Abrir el intento desde el Perfil, realizar/subir la tarea y analizar/revisar.
   El puente guarda el resultado aceptado y los bytes del WAV original localmente.
5. Volver mediante el enlace del puente, que espera a que termine el registro.

Frase admite los dos intentos de 7A. Su elección vincula conjuntamente velocidad,
pausas y Prosodia; no existen selectores independientes que puedan mezclar esos
dominios. Un resultado dependiente debe tener el mismo WAV/contexto 7A y número
de intento. Pausas exige además la misma revisión de contenido. Cada resultado
dependiente conserva la referencia al resultado 7A original del que procede.

Las fuentes son inmutables y tienen UUID propio, payload JSON conservado por
hash y activos WAV/modelo por hash. Los sucesivos resultados cambian únicamente
las referencias actuales; los anteriores siguen en el catálogo/historial.
No se elige el más rápido, más reciente o mejor. Los límites/versiones originales
de vocal y DDK se conservan en sus unidades originales; no se reinterpretan.

El enlace «Ver tarea» mantiene evaluación/intento. Una tarea ya registrada ofrece
recuperar su WAV original para editar/reanalizar; esta acción invalida el resultado
vigente y exige volver a revisar. No restaura silenciosamente confirmaciones.
El resultado completo anterior y el WAV siguen consultables desde el Perfil.

Los timestamps de registro/importación son distintos de los de captura. Cuando
la fuente no exporta fecha de captura, se guarda null + `not_exported_by_source`.
La asociación a una sesión es explícita; no se deduce la fecha real de un WAV
importado ni se certifica por su nombre o fecha de archivo.

## Completitud, disponibilidad y evidencia

Se conservan cuatro planos separados: estado original de fuente/tarea, revisión,
estado del dominio, disponibilidad/evidencia de cada métrica. No hay condición de
completitud basada en conseguir todos los valores.

| Dominio | Cierre válido | Métricas principales |
| --- | --- | --- |
| Fonación | Submódulo de fonación ejecutado; HNR no es indispensable | F0 media, DT, HNR experimental |
| DDK | Revisión confirmada y resultado revisado | Sílabas/s, ciclos/s, CV si calculable |
| Velocidad | Selección confirmada y revisión de contenido cerrada | Sílabas revisadas/s, palabras revisadas/min, duración seleccionada |
| Pausas | Revisión global 7B.1 confirmada y producción presente confirmada | Tasa operacional silábica, porcentaje, recuento |
| Prosodia | Extracción terminada sobre selección 7A confirmada | Mediana Hz, rango robusto ST, pendiente ST/s |

Una DDK cerrada con solo dos intervalos puede estar completed con
`cv_percent=null/insufficient_intervals`. HNR ausente/fallido no impide completed
si la tarea de fonación sí terminó; se conserva la advertencia. Prosodia puede
estar completed como tarea aunque su resultado estadístico original sea partial
por soporte insuficiente. Una revisión temporal explícitamente no evaluable se
mantiene not_evaluable. Los motivos de cada métrica no se relajan ni sustituyen.

Estados de dominio: `not_started`, `partial`, `completed`, `not_evaluable`,
`stale`, `failed`. Estado global independiente: `empty`, `current`, `stale`,
`failed`. La integridad fallida no borra dominios independientes válidos.

La completitud cuenta cinco dominios cuantitativos, con estados no nulos
desglosados. Siempre añade «Inteligibilidad no evaluada». No es una puntuación
clínica ni significa que toda la evaluación del habla motora esté completa.
Inteligibilidad es una sección visible `not_evaluated`, solo con notas opcionales;
no existe ASR, escala, puntuación, normalidad, severidad, radar ni baremo.

## Fuentes y límites

- Vocal: `/vowel-analysis`; F0/jitter/shimmer proceden exclusivamente de
  `modules.shimmer.result`, HNR de `modules.hnr.result`. HNR, jitter y shimmer
  están rotulados experimentales. La ventana es central de 3 s; no se inventa
  duración fonada ni tiempo máximo de fonación. Se conservan los seis xfail
  históricos de pitch/jitter/HNR y la validación humana pendiente.
- DDK: únicamente `reviewed_result.metrics` confirmado para cifras revisadas.
  Candidatos automáticos quedan en el original, nunca como sustituto. V1 activa;
  v2 no activada. El CV no es una puntuación de coordinación/severidad.
- 7A: recuentos reales revisados y tasas de referencia separados. Selección sin
  confirmar no publica duración final aunque exista un valor de borrador.
- 7B.1: única fuente de medidas finales de pausas. Sin revisión global no se
  publican subtotales como cifras finales. Tiempo/tasa operacionales, no articulación pura.
- 7B.2: referencia de soporte experimental, nunca numerador/denominador final.
- Prosodia: `filtered_800_03__0`, freeze v2 idéntico; mismas reglas de soporte.
  Mediana, rango y pendiente son de habla conectada, no se mezclan con vocal.
  La cobertura es contexto técnico, no exactitud. La mini-curva usa frames
  originales, corta huecos y distingue bordes; no corrige ni suaviza.

Todas las cifras se copian exactamente del campo original: cero y HNR negativo
son válidos; null conserva el motivo. El proyector no calcula tasas, pendientes,
cuantiles, perturbaciones, F0 ni otra medida acústica. La geometría del SVG es
solo visualización de valores ya existentes. La evidencia es técnica/sintética;
ni completed ni la confirmación manual certifican validación clínica.

## Invalidación

- Cambiar WAV/selección vocal o DDK invalida su dominio; editar revisión DDK retira
  las cifras revisadas hasta confirmar/recalcular en su módulo original.
- Cambiar contexto 7A invalida frase, pausas, candidatos y Prosodia.
- Cambiar revisión/recuentos 7A invalida tasas y pausas; no cambia F0/candidatos.
- Editar 7B.1 afecta solo a pausas. Generar/rechazar candidatos no modifica F0.
- Cambiar versión/configuración/motor requerido produce stale, sin reanálisis.
- Archivo fuente/activo con hash incorrecto produce fallo de integridad.
- Se rechazan respuestas tardías y cambios concurrentes de intento durante el registro.

Se comprueba identidad al abrir/recuperar foco/visibilidad del Perfil y antes de
exportar. Si el servidor no es accesible no se declara vigente su identidad actual:
los resultados conservados permanecen auditables como stale. Los snapshots
exportados anteriores son históricos inmutables.

## Contratos

`motor_evaluation_v1`: metadatos, intentos, bindings explícitos, catálogo de
fuentes y eventos locales. `motor_speech_profile_v1`: identidad de evaluación,
bindings, catálogo sin payloads, cinco dominios, métricas, estados, completitud,
soporte experimental, notas e Inteligibilidad `not_evaluated`.

Cada métrica contiene `value`, `unit`, `reason`, `reason_origin`, `availability`,
`source_ref`, `source_pointer`, `definition_id`, `acquisition`, `experimental`,
`evidence` y metadatos de comparabilidad. Método/estado/numerador/denominador/base
se conservan si la fuente los exporta. Un motivo por ausencia de tarea o por stale
pertenece al perfil; un motivo matemático original pertenece a la fuente.

El catálogo conserva hashes, versiones, contexto/selección, identidad de intento,
referencia 7A padre, fechas, captura y referencias a artefactos. Los payloads
completos, frames, pulsos, intervalos, candidatos, WAV y modelos NO se embeben en
el resumen. Se recuperan en el registro local mediante su hash.

`motor_speech_bundle_v1` es el paquete JSON recuperable separado: incluye el
registro, resumen y artefactos por hash (base64) sin duplicar activos idénticos.
Importar verifica hashes, pertenencia de evaluación/intento, WAV y dependencias
7A; rechaza colisiones de evaluación. Ignora las cifras del resumen embebido y
reconstruye desde originales. No confundir integridad con autenticidad del autor
o acierto del revisor: no hay firma ni autenticación clínica.

## Comparabilidad futura

`compareMetadata` contrasta tarea, definición, unidad, protocolo/configuración/
motor, modalidad, estímulo/modelo y base de adquisición/recuento. Solo devuelve
`same_method_metadata` o `compatibility_not_established`, con motivos.
Incluso en el primer caso `clinical_comparability_established=false`. No calcula
delta, mejoría, porcentajes, severidad ni interpretación longitudinal. Las
condiciones de grabación permanecen en las fuentes; igualdad de metadatos no
certifica equivalencia acústica o clínica entre dos sesiones.

## Verificación y ejemplos

Pruebas específicas: `tests/test_motor_profile.py`, `tests/motor-profile.test.mjs`
y `tests/motor-profile-browser.mjs`. Este último realiza tareas con API real y
señales sintéticas, comprueba reconstrucción, manipulación de resumen/paquete,
estados, intentos, mini-curva, igualdad exacta y escritorio/móvil.
`python -m tests.profile_fixtures /tmp/profile-fixtures.json` genera las entradas
controladas sin ejecutar bancos de desarrollo/bloqueado ni usar WAV humanos.

Los ejemplos de `reports/motor_profile/` son sintéticos, no evaluaciones de
personas. El parcial muestra una tarea completada y cuatro sin iniciar. El
completo muestra cinco dominios completados, con CV DDK no calculable e
Inteligibilidad no evaluada. Los logs y CI de entrega documentan resultados exactos.

Fuera de este hito: PDF, diagnóstico, clasificación, puntuación global, baremos,
interpretación longitudinal, nueva inteligibilidad y cambios de motores.
