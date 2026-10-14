# Primera interfaz de vocal sostenida — verificación

Fecha: 14/10/2026. Base: main e03d8474144723414462e51ee625814087a2d5d6.
Implementación y corrección de frontera: dcd9b7e44b32997590550364cf7062208ac42b36.
PR: https://github.com/andrepane/habla-motora/pull/1 (borrador, sin fusionar).

## Alcance

Interfaz en `/`, servida por FastAPI desde `frontend/`. Subida de WAV o
captura de /a/, reproducción, repetición y descarga de grabación; forma de
onda y selección manual; ventana central de 3 s; cinco medidas, coberturas,
avisos, curvas, copia de resumen, JSON completo y auditoría desplegable.

El navegador llama solo a POST `/vowel-analysis` para analizar. El backend
recibe el WAV una vez, conserva todos sus bytes y ejecuta `analyze_shimmer`
y `analyze_hnr` sin modificar sus algoritmos. Comprueba hash del WAV frente
a bytes recibidos, configuración/versiones y diccionario de intervalo.
Las salidas originales permanecen bajo `modules`, sin fusionar coberturas,
provenance ni sustituir estadísticas nativas por operaciones de frontend.

Un fallo de módulo devuelve HTTP 200 con `status=partial`, error explícito y
`result=null` para ese módulo. La salida del otro permanece completa.
Los valores no calculables son null, nunca ceros. Los ceros y HNR negativos
válidos se preservan. Errores de entrada: 422/413; ambos módulos fallidos o
incoherencia: 503, sin emitir un conjunto de medidas engañoso.

No añade pacientes, persistencia, diagnóstico, rangos clínicos, CPP/CPPS,
seguimiento ni otras tareas de habla. Los seis xfail históricos permanecen
intactos; no son pruebas aprobadas ni objetivos acústicos ya cumplidos.

## Verificación local

Python 3.12.14 y ejecutable oficial Praat 6.4.27 (January 27 2025).
Archivo de descarga verificado contra el mismo SHA-256 del Dockerfile:
6f60fba398f7490881a569b874a1c66ca026e1f748946d50a6017941c4137f7e.
Dependencias Python originales de requirements.lock, sin cambios.

- Suite completa: 230 passed, 6 xfailed, 1 warning in 189.50s (0:03:09).
- 30 pruebas nuevas de orquestación, HTTP, archivos estáticos y regresión
  del límite temporal: todas aprobadas en ejecución específica.
- 7 pruebas JavaScript: todas aprobadas. PCM16, tasas compatibles, signos,
  selección central, rechazo sin conversión, null/cero/negativos, restricciones
  de micrófono y presentación de magnitudes pequeñas sin falsos ceros.
- 24 comprobaciones Chromium/Playwright 1.51.1: todas aprobadas con API real.
  Incluyen WAV completo verificado por hash, tarjetas y curvas, copiar,
  descarga JSON, selección inferior a 3 s, invalidación inmediata y respuesta
  obsoleta, mocks de null/cero/HNR negativo/fallo parcial, rechazo de WAV
  inválido, micrófono sintético real de Chromium -> PCM16 -> backend, ajustes
  de captura consultados, descarga de grabación, adaptación a móvil y ausencia
  de errores JavaScript.
- Los mocks comprueban representación de estados, no exactitud acústica.
- Sin modificaciones en pitch/jitter/shimmer/hnr, scripts Praat, configuración
  experimental_v1 ni archivos de pruebas acústicas históricos (diff vacío).

## Regresión: fin del archivo con duración fraccionaria

La captura sintética expuso una incompatibilidad de fronteras sin afectar a
los algoritmos: 154368 muestras a 44100 Hz duran 3.500408163265306 s según el
recuento PCM. El script histórico de duración escribe fixed$(duration, 12),
que devuelve 3.500408163265 s. Pasar el primer número como final explícito
violaba la comprobación estricta del segundo por unos 3.06e-13 s.

El orquestador detecta una selección en el final PCM con precisión de 1e-12 s
(solo frontera del archivo, sin cambiar criterios de aceptación acústicos).
En ese caso pasa `emission_end_s=None` a ambos módulos, que usan su propia
duración nativa. No recorta, remuestrea, cambia scripts ni vuelve a calcular
métricas. Los finales interiores se transmiten sin cambios.
El JSON conserva `emission_end_s` solicitado, `effective_emission_end_s` y
`end_selection=native_file_end`. El intervalo de salida es el real de Praat.
La prueba específica utiliza exactamente esa duración no entera de muestras.

## Docker y Actions

Dockerfile y requirements.lock intactos. COPY . . incluye el frontend; no
necesita Node en producción. .dockerignore excluye node_modules.

El workflow conserva construcción con pytest, repetición dentro del
contenedor, informes sintéticos y todas las comprobaciones HTTP anteriores.
Añade activación por frontend/package y PR, Node 22, siete pruebas JS y las
comprobaciones Chromium contra el contenedor iniciado. Exporta también captura
visual. Se mantiene timeout de 30 minutos.

Comprobación Docker de la revisión final:
https://github.com/andrepane/habla-motora/actions/runs/38555759172
Success, job 115824364227. Construcción: 230 passed, 6 xfailed, 1 warning
in 325.70s; segunda suite: 230 passed, 6 xfailed, 1 warning in 326.19s.
Construcción, segunda suite dentro del contenedor,
informes sintéticos y todos los endpoints anteriores aprobados. Siete pruebas
JS y 24 comprobaciones Chromium contra el contenedor aprobadas, incluida
captura y análisis de micrófono sintético.
Artefacto: https://github.com/andrepane/habla-motora/actions/runs/38555759172/artifacts/11890950513
Digest del artefacto: sha256:77c0f7c57603cc31bb2b55e86fffe2e5fce62a8259a4dc097535c25556a98ebe.

No hay Docker en este entorno local: los resultados locales no se describen
como resultados de contenedor. La evidencia Docker se identifica separadamente.

## Uso local

```bash
git checkout feat/vowel-interface
docker build --platform linux/amd64 -t habla-motora:vowel .
docker run --rm -p 127.0.0.1:8000:8000 habla-motora:vowel
```

Abrir http://localhost:8000/. Sin servidor ni compilación frontend adicionales.
Alternativa: entorno Python y Praat originales del README; ejecutar
`uvicorn backend.app:app --host 127.0.0.1 --port 8000`.

## Límites de captura y presentación

La grabación necesita localhost/HTTPS y permiso de micrófono. Se solicitan
cancelación de eco, reducción de ruido y ganancia automática desactivadas;
se registran restricciones, ajustes consultados, tasa AudioContext y canales.
No se afirma que hardware, sistema o navegador carezcan de procesamiento.
Web Audio puede adaptar internamente la tasa de captura. No hay SPL calibrado.
Si llegan varios canales, se usa el primero y queda registrado. La salida es
PCM16 mono a 44100/48000 Hz. No hay conversiones silenciosas de subidas.

Los gráficos unen solo frames nativos consecutivos con valor definido y se
interrumpen ante valores null o saltos de índice; sin suavizado ni interpolación
para rellenar huecos. Las medidas conservan precisión original en JSON. La
pantalla muestra hasta tres decimales y usa notación científica para magnitudes
no nulas inferiores a 0,001. Cobertura alta y HNR alto no certifican voz válida.
Cambiar audio o límites borra los resultados inmediatamente y cancela la espera;
la tarea que ya comenzó en el backend puede finalizar.

La captura Chromium prueba el mecanismo de grabación, no micrófonos físicos,
compatibilidad Safari/Firefox, ruido real ni fiabilidad clínica en voz humana.
La interfaz solo evalúa los 3 s centrales: no detecta automáticamente la vocal
ni muestra tracking fuera de esa ventana.

Captura visual con tono sintético: [interfaz_vocal.png](interfaz_vocal.png).
