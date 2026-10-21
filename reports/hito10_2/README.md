# Evidencia Hito 10.2

Código: `b817d424ad47e06171014812a3d8c422f1226148`.
Base H10.1: `e1728236761302c1ff7085a3dacaf15f1feebb27`.
Rama: `feat/h10-evaluation-continuity`. Sin PR ni cambios en main.

## Resultado local

| Verificación | Resultado |
|---|---:|
| Python completo (`python -m pytest -q`) | 638 passed, 6 xfailed |
| Frontend (`npm run test:ui`) | 102 passed |
| Vocal (`npm run test:browser`) | 24 comprobaciones |
| DDK (`npm run test:ddk-browser`) | 35 |
| Habla conectada (`npm run test:phrase-browser`) | 53 |
| Pausas (`npm run test:phrase-pauses-browser`) | 60 |
| Candidatos (`npm run test:phrase-candidates-browser`) | 34 |
| Prosodia (`npm run test:phrase-prosody-browser`) | 55 |
| Perfil (`npm run test:motor-profile-browser`) | 50 |
| Continuidad 10.1 (`npm run test:continuity-browser`) | 36 |
| Recorrido 10.2 (`npm run test:journey-browser`) | 39 |
| Total navegador | 386 |

Todos los procesos de navegador salieron con código 0. Los xfail de Python
son los existentes; aparece un aviso de deprecación de Starlette/AnyIO en el
entorno local. Las rutas HTML añaden ocho casos parametrizados al total.
Los logs de Python/frontend/navegador están en este directorio.

Praat local: binario oficial 6.4.27. Navegador local: Chromium 153 a través
de Playwright 1.51.1 con `BROWSER_EXECUTABLE`, `FONTCONFIG_PATH=/etc/fonts`.
Los tests usan WAV sintéticos de los helpers existentes, nunca grabaciones
humanas. Esta evidencia funcional no constituye validación clínica humana.

## Recorrido nuevo

Inicio → Nueva evaluación → Vocal → elegir explícitamente intento → DDK →
revisión manual confirmada → elegir intento → Habla conectada → selección →
Contenido → Pausas revisadas → Prosodia → elegir intento → Perfil 5/5.

El recorrido prueba las dependencias y el contexto, formularios posteriores
ocultos, candidatos opcionales sin ejecución automática, detalle automático
DDK cerrado, retorno desde contenido pendiente y desde pausas confirmadas,
igualdad de fuentes e invalidaciones tras restaurar, acontecimientos
estructurados conservando el contrato, consulta sin escritura, edición
cancelada, continuación prohibida con selección desactualizada, móvil y
modo independiente y ausencia confirmada con Pausas explícitamente no evaluables. El resto de regresiones conserva edición, exportación,
audio, auditoría, invalidación y exactitud de los resultados originales.

Las regresiones detalladas anteriores abren explícitamente la vista técnica
completa; el recorrido nuevo prueba la presentación progresiva por defecto.

## Integridad

`protected-files.json` registra 62 archivos idénticos byte por byte respecto
a H10.1: motores backend (excepto app.py, que cambia solo rutas HTML),
configuraciones, Praat, investigación y lógica frontend protegida. Incluye
proyector/registro y estado de Prosodia sin cambios. `validation-trees.json` verifica también igualdad de los árboles Git completos de investigación, informes de Prosodia, configuraciones, Praat y fixtures.

SHA-256 de `research/prosody/freeze.json`:
`047fac7379b09dfae0f545569e21ec34463ab7227255507ceeba68f8c6b6a24c`.
Configuración: `phrase_prosody_freeze_v2` / `filtered_800_03__0`.
DDK v1 activa, v2 desactivada. No se ejecutó el banco bloqueado de investigación.

Las adiciones de restauración son presentación/rehidratación; no recalculan
métricas ni registran fuentes al consultar. Solo las acciones explícitas de
análisis/revisión llaman a los controladores existentes. Originales,
confirmaciones, null + reason y reglas de invalidación se conservan.

## Docker y HTTP

La ejecución CI del commit de código es:
https://github.com/andrepane/habla-motora/actions/runs/39613088828

Estado final: **completed / success**. Los 22 pasos concluyeron correctamente.

Se construyó la imagen, se repitió Python dentro del contenedor (638 passed, 6 xfailed en ambas ejecuciones), se verificó Praat 6.4.27, caracterización sintética, endpoints HTTP y las 102 pruebas frontend y 386 comprobaciones de navegador.

[Artefacto con capturas y resultados](https://github.com/andrepane/habla-motora/actions/runs/39613088828/artifacts/12353050745). `ci-summary.json` conserva estado, commit, pasos y digest del artefacto; `ci-tests.txt` conserva los resúmenes extraídos del log original. Docker se verificó en GitHub Actions, no en el entorno local.

## Capturas

`npm run test:journey-browser` produce:

1. `01-inicio.png`
2. `02-vocal.png`
3. `03-ddk.png`
4. `04-pausas.png`
5. `05-prosodia.png`
6. `06-perfil.png`
7. `07-movil.png`

`screenshots-local.json` registra hashes de la ejecución local final.
CI regenera capturas equivalentes dentro de `clinical-journey-evidence/` en
su artefacto `milestone-5-docker-results`; los píxeles varían por navegador,
fecha y locale. Se conserva además la evidencia de los módulos existentes.

## Límites

El acabado visual general queda pendiente. Se mantienen formularios y detalles
clínicos existentes y sus advertencias metodológicas. La evaluación se guarda
localmente; se exporta el paquete para copia recuperable. Los borradores son
temporales. Se conserva el máximo existente de dos intentos de Habla conectada.
Inteligibilidad no evaluada queda fuera del denominador de cinco dominios.
