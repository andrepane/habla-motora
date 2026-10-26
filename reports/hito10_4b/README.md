# H10.4B — Pulido P2

Base: `79105ab82bce99aa7a85234ec2ca5b05e31f4c3a`, merge PR #14 (10.4A).
Rama nueva: `feat/h10-4b-usability-polish`. Sin PR.

La regresión nueva verifica también que consultar Vocal/DDK conserva las acciones fuera del editor oculto. Se corrigió una carrera de presentación al trasladar el CTA antes de terminar la reconstrucción asíncrona de la consulta; no cambia fuentes ni estados.

## Alcance

- P2.1: se trasladan los nodos originales de acciones, sin duplicar botones/handlers. Vocal: después de resultados/avisos. DDK: después de métricas revisadas. Pausas: continuación junto a confirmación. Jitter/shimmer, gráficos DDK y tasas de referencia permanecen en detalles. Los intervalos de Pausas se pliegan solo tras obtener una revisión confirmada; conservan todos sus controles. Un borrador posterior permite seguir editándolos. Cabecera móvil más compacta.
- P2.2: controles de tiempo en segundos delegan en los controles originales de muestras y sus handlers. Sin edición, no se reasigna ningún índice. Al editar se aplica la misma cuantización a la muestra más próxima que en la onda, con final excluido. Los índices originales y su equivalencia exacta están en detalles. Razones conocidas y unidades `count` se traducen únicamente para mostrar; JSON/orígenes/exports conservan los códigos. Razones desconocidas mantienen el código.
- P2.3: se oculta el desplegable de opciones de borrador cuando el resultado temporal es confirmado; no se cambia su valor. Se distingue resultado confirmado, borrador posterior y no evaluable leyendo el resultado/historial existente. Confirmar una casilla sin resultado calculado no se presenta como resultado confirmado.
- P2.4: indicación de desplazamiento cuando existe overflow, columna de acontecimiento fija, región desplazable enfocada por teclado y orden de controles intacto. Ninguna columna se elimina.
- P2.5: resumen y copia completa recuperable se etiquetan y explican por separado. La importación sigue utilizando el mismo validador. Solo tras su rechazo, si el archivo tiene el schema del resumen, se explica qué copia se necesita y dónde obtenerla. Otros errores se conservan.

## Verificación local

- Python completa: **639 passed, 6 xfailed**, 406,51 s. Un warning previo Starlette/AnyIO.
- Frontend: **111/111** (cuatro pruebas nuevas de presentación).
- Regresiones navegador: Vocal 24, DDK 35, Frase 53, Pausas 60, candidatos 34, Prosodia 55, Perfil 50, continuidad 36, recorrido clínico 39; 10.4A 102.
- P2: 98 comprobaciones en el recorrido real con API y audio sintético; controles exactos, accesibilidad de detalles, proximidad/ausencia de duplicados, tabla con teclado/columna fija, estados y rechazo orientativo de resumen sin escrituras.
- Visual: ocho pantallas × 1440/1024/390/320, sin overflow de página; cero violaciones automáticas axe AA. Ocho comprobaciones de reflow al 200 %. Los casos incompletos de axe requieren revisión humana; esto no es certificación WCAG.
- Comparación reproducida sobre una copia temporal de main y esta rama, con los mismos WAV sintéticos. `positions.json` registra posiciones absolutas, no tiempos de interacción. A 320 px: Vocal 3173→2572, DDK 4539→3607, Pausas 4943→2761 px. Las posiciones dependen del contenido; la garantía probada es proximidad a cierre y acceso a todos los datos.

Reproducción: `npm run test:ui`; `USABILITY_AUDIT=1 npm run test:visual-browser`, con `PROFILE_FIXTURES` generado mediante `python -m tests.profile_fixtures`. El workflow Docker ejecuta esta matriz, todas las regresiones, 10.4A, HTTP y las suites completas.

## Integridad y límites

No se modifican backend, Praat, detectores, parámetros, fórmulas, protocolos, proyector, registro/persistencia, importador/exportador, reglas de invalidación, representatividad ni bancos. Se conservan los manifiestos históricos H10.3 y 10.4A. `usability-presentation-sources.json` encadena únicamente tres excepciones de mensajes/renderizado (UI de evaluación, UI del Perfil y consulta guardada); todos los demás hashes protegidos siguen exigiéndose.

No se afirma que la sesión clínica esté validada con usuarios humanos. La tabla DDK sigue siendo horizontal en móvil, ahora orientada y operable. El editor de intervalos abierto conserva su extensión para no quitar salvaguardas necesarias. Las capturas completas, finales de paso, tabla desplazada, borrador posterior, exportación y error de resumen se producen en el artefacto `visual-system-evidence` del CI; baseline comparativo y capturas locales acompañan la entrega. No se implementan P3 ni nuevas capacidades.

La conclusión sobre CI se registra después de su ejecución terminal sobre el commit de código. Las escrituras de atributos visuales se realizan solo si cambia su valor, para mantener estable el observador de presentación.

## Capturas conservadas

Las imágenes JPEG son vistas de las capturas PNG originales; el manifiesto conserva ambos hashes y distingue las pruebas de presentación con datos simulados. Se usa exclusivamente audio sintético.

| Recorrido | Móvil | Escritorio |
|---|---|---|
| Final de Vocal | [320 px](evidence/step-end-03-vocal-320.jpg) | [1440 px](evidence/step-end-03-vocal-1440.jpg) |
| Final de DDK | [320 px](evidence/step-end-04-ddk-320.jpg) | [1440 px](evidence/step-end-04-ddk-1440.jpg) |
| Editor de pausas antes de confirmar | [320 px](evidence/pauses-editing-320.jpg) · [390 px](evidence/pauses-editing-390.jpg) | [1440 px](evidence/pauses-editing-1440.jpg) |
| Pausas confirmadas | [320 px](evidence/pauses-confirmed-320.jpg) | [1440 px](evidence/06-pausas-1440.jpg) |
| DDK con tabla desplazada | [320 px](evidence/ddk-horizontal-320.jpg) | Todas las columnas disponibles en la regresión de escritorio |
| Perfil y exportación | [320 px](evidence/08-perfil-320.jpg) | [1440 px](evidence/08-perfil-1440.jpg) |
| Importación de resumen rechazada | [320 px](evidence/summary-import-error-320.jpg) | [1440 px](evidence/summary-import-error-1440.jpg) |

Comparables anteriores sobre main: [Vocal](evidence/before-03-vocal-320.jpg), [DDK](evidence/before-04-ddk-320.jpg), [Pausas](evidence/before-06-pausas-320.jpg).

## CI final confirmado

Código validado: `9ed03cdd46ea796d67461359072d1490e04d2e3a`.
[Workflow 39812293062](https://github.com/andrepane/habla-motora/actions/runs/39812293062): **completed / success**.

Docker construye y ejecuta la suite Python completa dos veces: 639 passed / 6 xfailed en cada ejecución (339,42 y 342,05 s). Frontend 111/111; todas las regresiones de navegador, recorrido clínico, continuidad, 10.4A, módulos e importación/exportación pasan. Pasan las caracterizaciones sintéticas y verificaciones HTTP existentes.

El ZIP del artefacto `milestone-5-docker-results` se ha descargado y verificado: SHA-256 `3c1b24b411895047f16af22c1572ded0d746b0c3511c41e6aeae5e1e6224b503`. Incluye 48 PNG; sus JSON confirman 98/98 comprobaciones P2, 32 casos visuales/axe sin overflow ni violaciones automáticas y 8 reflows. Los JSON `ci-*.json` provienen directamente de ese ZIP, no de la ejecución local. `validation.json` conserva el vínculo al código exacto, los pasos, los recuentos y el digest; `ci-log-extract.txt` contiene el extracto verificable de los logs.

El commit posterior de evidencia solo contiene archivos bajo `reports/hito10_4b/`; conserva idéntico el código validado. No se abre PR.
