# Hito 10.4A — Continuidad crítica

Base: main b26eb545bdae7e0b2c60dd9bb1b621de0aeaee6f (PR #13, H10.3).
Rama: feat/h10-4a-critical-continuity. No incluye los P2 de la auditoría.

## Cambios autorizados

- La salida de una tarea independiente con audio/entrada temporal o captura
  activa solicita confirmación. Recarga/cierre usan beforeunload; enlaces internos
  permiten cancelar o salir expresamente. No hay nuevo almacenamiento ni autosave.
  Las descargas no disparan el aviso y no se consideran una prueba fiable de que
  el archivo se haya conservado: la protección permanece mientras haya contenido.
- exactAudioBuffer adapta ArrayBuffer/vistas recuperadas, respetando byteOffset y
  byteLength. No decodifica, altera, remuestrea ni vuelve a analizar el WAV.
- Continuar y Editar esperan al controlador preparado. Un fallo del protocolo se
  explica y permite reintentar mediante recarga segura de la consulta. Los enlaces
  y la consulta guardada no se bloquean durante esta preparación.
- DDK pendiente restaura WAV, selección, candidatos, operaciones y acontecimientos
  guardados. render(false) reutiliza el render existente sin registrar otra fuente.
  La consulta confirmada muestra acontecimientos, etiquetas, reinicios, exclusiones
  y ciclos procedentes del resultado original. Editar/Reanalizar sigue separado.

La reanudación no ejecuta el detector. Confirmar/calcular posteriormente conserva
el endpoint y comportamiento existentes, por acción expresa del usuario. Los
cambios de revisión aún no guardados siguen siendo borradores temporales: esta
fase no añade persistencia de borradores; cancelar la salida los conserva en la pestaña.

## Integridad

Sin cambios en backend, motores, configuraciones, Praat, investigación/bancos,
Prosodia congelada, proyector, registro/persistencia, formatos de exportación,
reglas de invalidación o elección representativa. El manifiesto H10.3 permanece
intacto; continuity-adapter-sources.json identifica exactamente los cinco
adaptadores frontend autorizados ahora, con sus hashes anterior y nuevo. La
prueba de integridad sigue verificando todos los demás archivos sin excepción.

## Verificación

critical-continuity-browser.mjs prueba 1440/390/320: grabación, recarga, cancelación,
salida, descarga, cierre de pestaña y ausencia de nueva base de datos independiente;
DDK automático y borrador con decisiones guardadas, lectura confirmada sin
escrituras; importación/exportación real, bytes/hash idénticos, ninguna nueva
fuente/invalidation al continuar; carga lenta y fallo recuperable del protocolo.
recovered-audio.test.mjs añade el caso de una vista con offset no nulo.
La CI existente ejecuta Python/Docker/HTTP, frontend, todas las regresiones de
navegador y la matriz visual; añade las pruebas críticas específicas.

Limitaciones: los diálogos nativos y su texto los controla el navegador. El cierre
forzado del proceso/OS no garantiza eventos beforeunload. Las pruebas móviles
usan viewports Chromium y micrófono sintético; no sustituyen dispositivos físicos.

Verificación local completada: 639 passed / 6 xfailed existentes (Python),
107 pruebas frontend, 102 comprobaciones específicas 10.4A, 386 comprobaciones
funcionales de navegador y 32 combinaciones visuales sin overflow ni violaciones
automáticas axe A/AA/2.1 AA. Las 39 del recorrido se repiten en la matriz visual.
