# Hito 10.3 — Sistema visual

Base: main `6deed5e9025948935e353eff44ba3d97f633ac67`, PR #12 fusionada.
Rama nueva: `feat/h10-3-visual-system`. No se reutiliza la rama de continuidad.
Sin PR. Cambios de presentación; no se modifica la arquitectura de 10.1/10.2.

## Sistema

- Una sola base `design-system.css`: tipografía de sistema sin descargas,
  tinta oscura, fondo gris frío, superficie blanca, acento azul #245a85.
  Bordes discretos, radios 5–8 px, sin gradientes ni animaciones.
- Escala 36/21/16 px de títulos en escritorio y 27/19/16 px en móvil.
  Texto principal 16 px, ayudas y procedencia 12–14 px. Ancho máximo 1280 px.
- Botones primarios para análisis, confirmación, siguiente paso y exportación
  principal; secundarios para alternativas; terciarios para acciones menores.
  Los controles deshabilitados conservan contraste y semántica nativa.
- Estado completado en azul, pendiente neutro, actualización ámbar, error del
  sistema rojo. Son estados del trabajo, nunca normalidad/patología.
- Navegación activa con `aria-current`, foco visible y enlace de salto al contenido.
  Inputs de subida accesibles por teclado; tablas desplazables etiquetadas.

## Pantallas

Inicio mantiene sus tres acciones y acceso independiente; muestra las tres
 tareas y sus cinco dominios sin dashboard. Evaluación destaca el siguiente
paso y separa las tres tareas con divisores, intentos y acciones existentes.

Vocal y DDK aprovechan dos columnas para captura y selección en escritorio.
F0 tiene mayor peso; jitter/shimmer/HNR mantienen sus cifras y advertencias.
DDK prioriza revisión manual, con el análisis automático plegado como antes.

El stepper local de Habla conectada muestra actual, completado, disponible y
bloqueado con texto y número. Sus handlers, disponibilidad y dependencias son
exactamente los de 10.2. `visual-interface.js` solo lee estado ya publicado en
el DOM/auditoría y añade anotaciones de presentación.

Pausas conserva una sola onda y todos los controles originales; la onda y el
reproductor permanecen cerca de la edición en escritorio mediante sticky.
En móvil se priorizan ancho de campos, botones, intervalos y audio contextual;
las explicaciones de clasificación se pliegan, sin borrar texto. La definición
principal de pausa y las confirmaciones permanecen visibles. Los candidatos
siguen siendo ayuda opcional y no se ejecutan automáticamente.

Prosodia mantiene gráfico, huecos/bordes originales y controles táctiles.
No se alteran polilíneas, coordenadas, suavizado, interpolación ni cálculos.
Estadísticas secundarias, frames y parámetros siguen en detalles.

Perfil muestra dos columnas de dominios en escritorio y Prosodia a ancho
completo; móvil utiliza filas de métricas con etiqueta y valor. La gestión de
evaluaciones es secundaria cuando hay una activa, pero los mensajes de estado
permanecen siempre fuera del desplegable. No se ocultan avisos únicos; la
mención repetida de validación humana pasa a los detalles y sigue en cabecera.
Inteligibilidad permanece no evaluada y fuera del denominador.

## Integridad

`tests/visual-protected-sources.json` fija 171 archivos a su SHA-256 de main:
backend completo, configuraciones, Praat, investigación, informes de Prosodia
y todos los JS funcionales existentes. `test_visual_integrity.py` verifica
igualdad byte por byte. No se modifican proyector, registro, exportación,
consulta/edición, selección representativa, navegación ni invalidaciones.

## Verificación iterativa

Primero unidades y primeras capturas de Inicio/Evaluación; después captura,
selección y revisión; luego pasos locales/Perfil; por último cuatro anchos,
foco, teclado, accesibilidad automática y regresiones completas.

`npm run test:visual-browser` ejecuta el recorrido clínico real con WAV
sintéticos y 32 capturas (ocho pantallas × 1440/1024/390/320 px), comprueba
scroll horizontal de página, foco visible, apertura/cierre por teclado,
axe-core WCAG A/AA/2.1 AA y reflujo con zoom CSS 200 %. El zoom CSS complementa
las cuatro resoluciones; no se presenta como prueba del zoom nativo de todos
los navegadores. Las tablas extensas conservan scroll interno accesible.

El workflow Docker conserva todas las comprobaciones anteriores y añade las
visuales, guardando `visual-system-evidence/` con imágenes, accesibilidad y
reflujo. El informe de evidencia registra commit, resultados y CI.

## Límites

No es certificación WCAG ni validación clínica humana. Quedan pruebas manuales
con lectores de pantalla y dispositivos/navegadores reales adicionales.
Se conserva la densidad de los formularios de revisión donde es necesaria
para mantener todas las confirmaciones. No hay fuentes remotas, iconografía
decorativa, PDF, login, sincronización ni capacidades clínicas nuevas.
