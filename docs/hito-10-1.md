# Hito 10.1 — Continuidad de evaluación y navegación

Base main: f6936dfa6d4e44e373d9eda9f092f6c758b47f2d.
Rama: feat/h10-evaluation-continuity. Sin rediseño visual general.

## P0.1

evaluation-navigation.js conserva evaluation_id en todos los enlaces globales.
Resuelve por tarea el último intento abierto explícitamente en esta pestaña
(sessionStorage separado por evaluación), o su representativo si no hay uno activo
válido. No altera bindings ni elige automáticamente un representativo. Cuando no
hay intento, abre Perfil con manage_task y expone su creación explícita.
La URL y el registro verifican pertenencia a evaluación/tarea. Un contexto inválido
bloquea el editor; no cae en análisis independiente. Sin evaluation_id los módulos
continúan siendo independientes.

## P0.2

En evaluación los dos selectores internos de Frase quedan bloqueados. La URL
identifica un único intento; los handlers comprueban el ordinal incluso si se
fuerza un clic. Para cambiar se abre otro intento desde Perfil. El registro
comprueba evaluation_id, attempt_id, ordinal y dependencias. El modo independiente
conserva sus dos pestañas.

## P0.3

Con una fuente existente se abre consulta sin cargar el WAV en el editor ni llamar
a motores. Muestra métricas originales, estado, intento, relación con representativo,
WAV reproducible y selección/revisión/procedencia en detalles. Los valores históricos
desactualizados se identifican como originales no vigentes para el Perfil. Se
verifican artefactos antes de habilitar edición. Consultar no escribe resultados.

Editar / Reanalizar requiere confirmación. Avisa de recuperación del WAV y nueva
confirmación de selección/revisiones; en Frase explica las invalidaciones de Pausas,
candidatos y Prosodia. Cancelar no modifica nada. Aceptar inicia el editor con el
original y conserva las reglas existentes de invalidación al cargar/modificar.
No se restauran confirmaciones como si la nueva edición ya estuviera revisada.
Los resultados anteriores permanecen inmutables. La edición conserva modalidad,
marca de límite y modelo auditivo original de Frase; exige volver a reproducir
el modelo, sin restaurar automáticamente su confirmación de presentación.

## P0.4

Identidad/intento permanecen visibles independientemente del mensaje de guardado.
Se distinguen guardando, guardado, revisión pendiente y cambios sin confirmar.
Los borradores son temporales en la pestaña: no se promete persistencia de cambios
no calculados. Los enlaces esperan la cola de registro y piden confirmación si se
perdería un borrador. beforeunload advierte ante recarga/cierre/navegación con cambios
o guardado pendiente. El navegador controla ese diálogo y puede suprimirlo; un
cierre forzoso no permite garantizar guardados pendientes. Al volver mediante
BFCache se recarga el contexto para no reutilizar un editor obsoleto.
Una dependencia invalidada sigue desactualizada aunque se abandone el borrador.

## Verificación local

- Python completa: 630 passed, 6 xfailed, 1 aviso de deprecación; 244.03 s.
- npm run test:ui: 100 pruebas aprobadas, 3 nuevas de navegación.
- npm run test:continuity-browser: 36 comprobaciones aprobadas.
- Regresiones navegador: Vocal 24, DDK 35, Frase 53, Pausas 60, candidatos 34,
  Prosodia 55, Perfil 46: 307 comprobaciones aprobadas. Total navegador: 343.
- Consulta sin POST ni cambios en JSON exacto de evaluación; edición cancelada;
  invalidaciones explícitas conservando fuentes; registro exacto del intento 2;
  Pausas/Prosodia del mismo intento y F0 sin cambios por revisión de contenido;
  salida/recarga canceladas, atrás/adelante, modo independiente y móvil.
- Sin cambios de backend, configs, Praat, research, bancos ni proyector.

Logs completos en reports/hito10_1/. Audio sintético, sin validación clínica ni
nueva ejecución de bancos desarrollo/bloqueado. El harness permite Chromium
alternativo con BROWSER_EXECUTABLE; CI mantiene el Chromium de Playwright.
Docker no está disponible localmente. El workflow existente conserva construcción,
pytest dentro del contenedor y endpoints HTTP e incorpora la nueva prueba.
Verificación remota completada: commit de implementación
20f516fd516676b604ab938cf742ad6ab15dd79f, workflow 39593716565, todos los pasos
aprobados. Docker: 630 passed + 6 xfailed en construcción y en la segunda pasada;
100 unitarias frontend y 343 comprobaciones de navegador, incluidas 36 nuevas.
Endpoints HTTP, caracterizaciones existentes y carga de artefactos aprobados.
URL: https://github.com/andrepane/habla-motora/actions/runs/39593716565
Resumen verificable en reports/hito10_1/ci.json. Este cierre documental no cambia
el código validado ni requiere volver a ejecutar los motores.
