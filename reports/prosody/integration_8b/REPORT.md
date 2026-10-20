# Hito 8B — Integración de Prosodia v1

Implementación: `f8bc5643dc5f228a672a0267b5927fabd2df2d88` sobre
`23ba91267d5f88314d555059a8c7d28865bb275a`, rama `investigate/phrase-prosody`.
Contrato y funcionamiento: [documentación de integración](../../../docs/phrase-prosody-integration.md).

## Resultado funcional

`POST /phrase-prosody-analysis` y `GET /phrase-prosody-protocol` integran el
extractor congelado mediante un adaptador separado. Solo aceptan la identidad
de la selección confirmada 7A y la configuración `filtered_800_03__0`.

La sección Prosodia aparece después de 7B.2, con curva discontinua de F0 sin
interpolación ni suavizado, huecos y bordes diferenciados, hover/tap de frames,
zoom, desplazamiento y reproducción limitada a 7A. Hz/ST usan la referencia
mediana nativa exportada; segundos/porcentaje modifican solo la visualización.
Cuatro métricas principales y detalles plegados evitan una tabla dominante.
Se muestran los códigos técnicos congelados y los motivos de `null`; cero
permanece válido. Los estados `partial`, `not_evaluable`, `failed` y `stale`
se distinguen de `completed`.

WAV, selección, intento, modalidad y versión/configuración/motor invalidan el
resultado; revisiones de recuentos, pausas y candidatos no alteran F0. La
exportación separa 7A, 7B.1, 7B.2 y Prosodia, conserva frames, métricas, huecos,
avisos, hashes, versiones, referencia ST, estado, motivos e historial inválido.

## Pruebas locales

Entorno: Python 3.12.14, Praat 6.4.27, NumPy 2.3.5, Playwright 1.51.1/Chromium.
Señales de prueba sintéticas/controladas. No se ha ejecutado de nuevo el banco
bloqueado ni desarrollo completo; las pruebas unitarias utilizan casos de desarrollo
para verificar el contrato, sin comparar configuraciones ni ajustar parámetros.

| Comando | Resultado | Evidencia comprimida |
| --- | --- | --- |
| `PRAAT_EXECUTABLE=/tmp/praat_barren python -m pytest -q tests/test_phrase_prosody.py tests/test_prosody_assessment.py tests/test_prosody_selection_policy.py tests/test_phrase_prosody_api.py` | 76 aprobados | `specific.log.gz` |
| `PRAAT_EXECUTABLE=/tmp/praat_barren python -m pytest -q` | 626 aprobados, 6 xfail esperados, 1 warning; 261,30 s | `python_full.log.gz` |
| `npm run test:ui` | 73 aprobados (14 nuevos) | `frontend_unit.log.gz` |
| `TEST_WAV=/tmp/vocal-6s.wav npm run test:browser` | 24 comprobaciones | `browser_vocal.log.gz` |
| `DDK_TEST_WAV=/tmp/ddk-clean.wav npm run test:ddk-browser` | 35 comprobaciones | `browser_ddk.log.gz` |
| `PHRASE_TEST_WAV=/tmp/phrase-8s.wav npm run test:phrase-browser` | 53 comprobaciones | `browser_7a.log.gz` |
| `PHRASE_TEST_WAV=/tmp/phrase-8s.wav npm run test:phrase-pauses-browser` | 60 comprobaciones | `browser_7b1.log.gz` |
| `CANDIDATE_TEST_WAV=/tmp/phrase-candidates.wav npm run test:phrase-candidates-browser` | 34 comprobaciones | `browser_7b2.log.gz` |
| `CANDIDATE_TEST_WAV=/tmp/phrase-candidates.wav npm run test:phrase-prosody-browser` | 55 comprobaciones | `browser_8b.log.gz` |

Total navegador: 261 comprobaciones. Todos los comandos de navegador usaron API
real y audio sintético. Algunos casos 8B inyectan respuestas controladas para
forzar cero, error de transporte y cambio de identidad; se distinguen del análisis
acústico real. API añade 21 pruebas; frontend 14. Capturas `desktop.png` y
`mobile.png` revisadas visualmente; viewport móvil de 390 px sin desbordamiento.

Los seis `xfail` estrictos ya existentes son limitaciones documentadas de pitch,
jitter y HNR; ninguno corresponde a Prosodia 8B. El warning es la deprecación de
`anyio.abc.BlockingPortal` en Starlette. No se han modificado para obtener verde.

## Integridad y alcance

`acoustic_integrity.json` registra SHA-256 y comparación byte a byte de 120
archivos previos (backend salvo el registro de ruta en app.py, configs, Praat,
research/prosody y reports/prosody) contra el commit base: todos idénticos.
`freeze.json` conserva SHA-256
`047fac7379b09dfae0f545569e21ec34463ab7227255507ceeba68f8c6b6a24c`.
Configuración acústica, reglas de soporte y discontinuidad, criterios de
aceptación, bancos y resultados 8A permanecen intactos. 7A, 7B.1, 7B.2, vocal y
DDK pasan sus regresiones sin cambiar sus algoritmos.

Durante la integración se resolvieron la retirada de resultados ante cambios de
fuente, el rechazo de respuestas tardías, la comprobación de identidad antes de
exportar y la conservación de identidad y `null + reason` en errores de transporte.
Ninguno requirió modificar el algoritmo acústico.

## Límites

La validez acústica sintética y la concordancia Praat proceden del Hito 8A
congelado. Esta fase prueba su integración técnica; la validación humana sigue
pendiente. No hay interpretación clínica ni curva suavizada. Sin persistencia
automática entre recargas; la exportación explícita conserva la auditoría.
Una identidad de servidor no verificable invalida el resultado antes de exportar.

## Docker y CI — aprobado

[Run 39442875677](https://github.com/andrepane/habla-motora/actions/runs/39442875677),
commit `f8bc5643dc5f228a672a0267b5927fabd2df2d88`: `completed / success`.
Docker se verificó en GitHub Actions al no estar disponible localmente.

- Construcción de imagen con pytest: 626 passed, 6 xfailed, 1 warning; 289,45 s.
- Repetición de pytest dentro del contenedor: 626 passed, 6 xfailed, 1 warning; 299,07 s.
- Praat 6.4.27, duración, caracterizaciones sintéticas de pitch/jitter/shimmer/HNR/DDK y endpoints HTTP: aprobados.
- Frontend: 73 pruebas unitarias aprobadas.
- Navegadores contra API Docker: vocal 24, DDK 35, 7A 53, 7B.1 60, 7B.2 34 y Prosodia 8B 55: 261 aprobadas.

Logs íntegros: `docker-ci.log.gz`; metadatos del run, pasos y artefactos:
`docker-ci.json`. Artefacto `milestone-5-docker-results`, ID `12277210058`,
SHA-256 `7a2e4ac1c028e93019aa6c6db1a7fca3bf7bcc3e1cbf1f5180f4fbe09020fe53`.
`verification.json` ofrece el resumen estructurado y `SHA256SUMS.json` identifica
los archivos de evidencia de esta entrega.

Hito 8B técnicamente cerrado para la integración solicitada, con validación
humana pendiente. La configuración acústica permanece idéntica a
`phrase_prosody_freeze_v2`; no se ha abierto PR.
