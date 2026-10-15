# habla-motora — evaluación experimental de vocal sostenida

Nombre técnico provisional. Herramienta experimental de medición del habla motora
orientada a una futura presentación a COLOAN. El proyecto contiene los hitos acústicos 1–5 cerrados y una primera interfaz web
para vocal sostenida. Sin interpretación clínica.

## Qué hace

Recibe un WAV PCM mono, 16/24/32-bit, 44.100/48.000 Hz, hasta 10 MiB. Ejecuta el
script fijo `praat/smoke_test.praat` y devuelve la duración del archivo completo.
El smoke test no detecta el segmento de vocal ni calcula F0. El endpoint /pitch
calcula F0 media, DT y cobertura. El endpoint /jitter añade jitter local experimental. El endpoint /shimmer añade shimmer local experimental. El endpoint /hnr mide HNR mediante Harmonicity (cc). CPP/CPPS no están implementados.

Cada resultado incluye versión exacta de Praat, versión del protocolo y
configuración, SHA-256 de los bytes exactos de configuración, del WAV y del script.
En el smoke test, cobertura de F0 y ciclos aceptados permanecen `null` con motivo
`not_implemented`; en /pitch se calcula cobertura y los ciclos siguen `null`. Los fallos devuelven error, nunca medidas 0. No hay métricas
acústicas validadas ni etiquetas diagnósticas.

## Ejecutar con Docker (Linux amd64)

Desde la raíz del proyecto, con Docker instalado:

```bash
docker build --platform linux/amd64 -t habla-motora:smoke-v1 .
docker run --rm habla-motora:smoke-v1 python -m backend.praat_runner tests/fixtures/tone_2s.wav
docker run --rm habla-motora:smoke-v1 python -m pytest -q
```

La imagen fija Python 3.12.14, Praat 6.4.27 y las dependencias Python mediante
`requirements.lock`. Descarga el ejecutable oficial estático, sin interfaz gráfica,
y verifica SHA-256 del archivo descargado. Ejecuta pytest durante la construcción
y usa un usuario sin privilegios. La imagen base y los paquetes del sistema no
están congelados por digest/snapshot: no se promete reconstrucción bit a bit.
En ARM es necesaria la emulación amd64 de Docker.

## API mínima

```bash
docker run --rm -p 127.0.0.1:8000:8000 habla-motora:smoke-v1
```

En otra terminal:

```bash
curl -f http://127.0.0.1:8000/health
curl -f -F 'file=@tests/fixtures/tone_2s.wav' http://127.0.0.1:8000/smoke-test
```

`/health` comprueba que la API vive, no que Praat esté operativo. La documentación
técnica de la API está en http://127.0.0.1:8000/docs. Es un servicio local de pruebas,
sin autenticación ni preparación para despliegue público.

## Ejecutar sin Docker

Python 3.12 y el ejecutable oficial de Praat 6.4.27:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.lock
python -m pip install --no-deps --no-build-isolation -e .
export PRAAT_EXECUTABLE=/ruta/absoluta/a/praat
python -m backend.praat_runner tests/fixtures/tone_2s.wav
python -m pytest -q
uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

En PowerShell: `.venv\Scripts\Activate.ps1` y
`$env:PRAAT_EXECUTABLE = 'C:\ruta\Praat.exe'`.

## Resultado esperado

La señal incluida es un tono matemático de 200 Hz, PCM16 mono, 88.200 muestras
(2 segundos a 44.100 Hz), sin voces ni datos personales.

```json
{"temporal": {"file_duration_s": 2.0}}
```

La respuesta real añade procedencia y advertencias. Consulte
`docs/verificacion_hito1.md` para las comprobaciones realizadas y sus límites.

## Ejecución y configuración

Python usa `subprocess.run` con una lista de argumentos, `shell=False`, timeout
de 15 segundos, script fijo y un archivo temporal con nombre controlado. El nombre
del archivo subido no se introduce en scripts ni comandos. El WAV temporal se
elimina al terminar. Los audios no se conservan en el backend.

La configuración `configs/experimental_v1.json` contiene los parámetros aprobados
para las futuras métricas, pero el smoke test solo utiliza la versión del motor.
No se atribuye ejecución a parámetros que todavía no se usan. Para modificar una
configuración con pruebas registradas, crear v2 y conservar v1 y sus resultados.

## Estructura

- `backend/`: FastAPI y ejecución de Praat; CLI para el smoke test.
- `praat/`: script de duración reutilizable en Praat de escritorio.
- `configs/`: protocolo experimental explícito.
- `tests/`: pruebas reales de motor/API y pruebas de errores.
- `tests/fixtures/`: único WAV sintético permitido en Git.
- `docs/`: alcance del protocolo y evidencia de comprobaciones.

## Qué no demuestra

La ejecución correcta y la duración de un WAV conocido no validan medidas
acústicas, segmentación, diagnóstico, utilidad clínica, comparación de micrófonos
ni seguimiento longitudinal. Las interpretaciones clínicas corresponden al
logopeda. No se utilizan NeuroVoz ni datasets restringidos.

Referencias: [Praat](https://www.praat.org/),
[versión oficial 6.4.27](https://github.com/praat/praat.github.io/releases/tag/v6.4.27).


## Hito 2: F0 experimental

`praat/pitch_v1.praat` analiza el WAV completo con raw cross-correlation y todos
los parámetros explícitos de experimental_v1. El JSON y su hash permanecen
intactos; su bloque scope es histórico, no estado del programa.

```bash
docker run --rm habla-motora:smoke-v1 python -m tests.report_pitch
docker run --rm habla-motora:smoke-v1 python -m pytest -q
```

CLI: `python -m backend.pitch archivo.wav --emission-start 0 --emission-end 6`.
API: POST `/pitch`, multipart WAV y límites `emission_start_s`, `emission_end_s`.
Si se omiten, se asume el archivo como emisión completa. La ventana es los tres
segundos centrales; emisiones de menos de tres segundos producen HTTP 422.
Los intervalos de diagnóstico explícitos solo están disponibles en Python y
siempre se identifican como pruebas ajenas a la selección estándar.

Salida: media y DT mediante consultas propias de Praat en Hertz, cobertura por
centros de frames, valores por frame, motivos de null y advertencias técnicas.
La cobertura no demuestra tracking correcto ni permite identificar silencio.
No hay corrección de octavas, interpolación de huecos ni rechazo por cobertura.
Una DT exactamente cero puede ser válida. Los ciclos glóticos siguen null.
Se conservan /health y /smoke-test como comprobaciones del hito 1.

El objetivo exploratorio de error máximo por frame <=0,5 Hz en la modulación
no se cumple con v1: se mantiene como prueba xfail estricta, no se relaja.
No implica validación clínica; véase docs/verificacion_hito2.md.


## Hito 3: jitter local experimental

`praat/jitter_v1.praat`: Sound completo + Pitch raw cc -> PointProcess (cc).
Get jitter (local), límites 0.8/600 y 1.25/75 s, factor máximo 1.3, porcentaje.
Cada valor finito de Praat se conserva con fiabilidad de pulsos no verificada;
undefined se convierte en null, nunca en cero. Se exportan pulsos completos y
períodos candidatos de la ventana central. Get number of periods determina
períodos aceptados. Pares utilizados: null/not_implemented; no se reimplementa
ese contador en producción. Los recuentos no certifican cierres glóticos reales.

```bash
docker run --rm habla-motora:smoke-v1 python -m tests.report_jitter
```

CLI: `python -m backend.jitter archivo.wav --emission-start 0 --emission-end 6`.
API: POST `/jitter`, mismos campos multipart que /pitch.
Versiones: jitter_v1, jitter_output_v1, jitter_warnings_v1. Configuración v1 intacta.
La prueba matemática usa tiempos conocidos sin detector; la comparación del
WAV con otro script Praat comprueba integración. No son la misma validación.
Se conservan los objetivos incumplidos como xfail estrictos, sin relajarlos.
Resultados y límites en docs/verificacion_hito3.md. No hay diagnóstico ni
validación en voces humanas.


## Hito 4: shimmer local experimental

CLI: `python -m backend.shimmer archivo.wav --emission-start 0 --emission-end 6`.
API: POST `/shimmer`, mismos campos multipart y selección central de 3 s que /jitter.
Reutiliza la auditoría y resultados de F0/jitter y añade únicamente shimmer local.
Sound + PointProcess: Get shimmer (local), períodos congelados, factores 1.3 y 1.6.
Exporta amplitudes mediante To AmplitudeTier (period), RMS Hann de Praat;
no son picos, SPL calibrado ni amplitudes clínicas. Pares usados: null/not_implemented.
Cada valor finito conserva estado experimental; undefined -> null. Un shimmer bajo
no demuestra tracking correcto ni estabilidad vocal.

```bash
docker run --rm habla-motora:smoke-v1 python -m tests.report_shimmer
docker run --rm habla-motora:smoke-v1 python -m pytest -q
```

Los tres niveles de validación y tolerancias completas, en puntos porcentuales,
están en docs/protocolo_v1.md. Los resultados exactos de Docker están en
docs/verificacion_hito4.md. Configuración v1 y cuatro xfail anteriores intactos.
Al cierre del hito 4 aún no se implementaba HNR; véase el hito 5 a continuación.
CPP/CPPS siguen fuera del alcance.


## Hito 5: HNR experimental

CLI: `python -m backend.hnr archivo.wav --emission-start 0 --emission-end 6`.
API: POST `/hnr`, mismos campos multipart para seleccionar la emisión y usar
su ventana central de 3 s. Ruta independiente: Sound completo -> Harmonicity (cc)
con 0.01 s, 75 Hz, silence threshold 0.1, periods per window 4.5. No ejecuta
Pitch/PointProcess y no adopta el techo de 600 Hz del módulo F0.

hnr_mean_db procede exclusivamente de Harmonicity: Get mean, conservando la
semántica temporal nativa. Los frames exportados son auditoría; no se calcula
una media aritmética simple para reemplazar o validar la consulta oficial.
La cobertura cuenta separadamente frames válidos con centro en el intervalo.
-200 es marcador nativo no válido: hnr_db=null, con valor bruto en auditoría.
undefined -> null; valores finitos negativos o cero se conservan. No hay
clasificación de silencio, ruido, patología ni fiabilidad de voz humana.
Versiones hnr_v1, hnr_output_v1, hnr_warnings_v1 y hashes completos.

```bash
docker run --rm habla-motora:smoke-v1 python -m tests.report_hnr
docker run --rm habla-motora:smoke-v1 python -m pytest -q
```

Protocolo corregido y tolerancias previas en docs/protocolo_v1.md; resultados
exactos, nuevos incumplimientos si aparecen y límites en docs/verificacion_hito5.md.
No se modifica experimental_v1 ni se relajan los cuatro xfail anteriores.
Un HNR alto puede coexistir con clipping o tracking incorrecto; no demuestra
voz estable ni validez clínica. CPP/CPPS siguen fuera del proyecto implementado.


## Primera interfaz web: vocal sostenida

Ejecutar el contenedor como se indica arriba y abrir **http://localhost:8000/**.
La página se sirve junto con la API, sin servidor frontend adicional, CDN ni
compilación. Dockerfile y dependencias acústicas permanecen intactos.

Flujo: subir WAV compatible o grabar /a/ -> escuchar -> marcar la emisión
mediante los límites de la forma de onda o los campos numéricos -> analizar.
La emisión debe durar al menos 3 s. Se resaltan sus 3 segundos centrales.
Se envía el WAV completo, sin recortar, filtrar ni normalizar. Cambiar el audio
o los límites invalida los resultados y aborta la espera de la solicitud anterior
(el trabajo ya iniciado en el backend puede terminar).

POST `/vowel-analysis`: una subida multipart `file`, `emission_start_s` y
`emission_end_s`. Orquesta `analyze_shimmer` y `analyze_hnr` sin modificar sus
algoritmos. `/shimmer` ya incluye duración, F0, jitter y shimmer. El frontend
no llama a los endpoints individuales. Si el final coincide con el límite del WAV (precisión de 12 decimales del
script histórico de duración), los módulos resuelven el final con su duración
nativa, usando `emission_end_s=None`. El JSON registra límite solicitado,
límite efectivo y `end_selection`; evita errores por redondeo sin alterar
ningún algoritmo. Se conservan sus respuestas completas
bajo `modules.shimmer.result` y `modules.hnr.result`, con procedencia separada.

- `status=completed`: ambos módulos completados y coherentes.
- `status=partial`: un módulo fallido, identificado con error y `result=null`;
  el otro resultado se conserva. HTTP 200 con estado parcial explícito.
- HTTP 422: WAV o selección incompatibles. HTTP 413: más de 10 MiB.
- HTTP 503: ambos módulos fallidos o incoherencia de hash/configuración/intervalo.
- `integrity.cross_module_verified=false` en resultados parciales: no afirma
  comparar contra un módulo fallido. El hash de cada resultado se comprueba
  frente a los bytes recibidos, incluso si solo hay uno disponible.

Las tarjetas muestran F0 media y DT, jitter local, shimmer local y HNR medio.
Coberturas separadas, avisos, curvas nativas sin suavizado ni relleno de huecos,
resumen copiable y JSON completo con auditoría. `null` se muestra como
«No calculable» y su motivo; cero y HNR negativo se conservan. La presentación
usa hasta tres decimales y notación científica para magnitudes no nulas <0,001,
para no mostrarlas como ceros; el JSON conserva la precisión original.
HNR medio sigue siendo exclusivamente `Harmonicity: Get mean`.

### Grabación

Requiere localhost o HTTPS, permiso de micrófono y Web Audio/AudioWorklet.
Solicita `echoCancellation=false`, `noiseSuppression=false`, `autoGainControl=false`
y un canal. Registra restricciones solicitadas, `getSettings()`,
`getConstraints()`, frecuencia de AudioContext y canales observados.
No garantiza ausencia de procesamiento del sistema, navegador o micrófono.

Codifica muestras capturadas en WAV mono PCM16 a la frecuencia de AudioContext
(44.100 o 48.000 Hz). Si llegan varios canales, usa el primero y lo registra.
No remuestrea archivos subidos ni convierte formatos incompatibles.
Web Audio puede adaptar internamente la captura a la frecuencia de AudioContext;
se conservan los ajustes consultables y esto no certifica captura bit a bit.
No hay calibración SPL. La cuantificación PCM16 y la limitación a [-1,1] son
parte de la codificación de captura, no una normalización acústica.

### Pruebas de interfaz

```bash
npm ci
npm run test:ui
npx playwright install --with-deps chromium
python -c 'from tests.synthetic_pitch import wav_bytes; from pathlib import Path; Path("/tmp/vocal-6s.wav").write_bytes(wav_bytes())'
# Con la API ejecutándose en otra terminal:
npm run test:browser
```

Variables opcionales: `BASE_URL`, `TEST_WAV`, `SCREENSHOT`.
La prueba de micrófono usa un dispositivo sintético de Chromium, sin voz real.
Actions conserva todas las comprobaciones previas y añade estas pruebas al
contenedor real ya iniciado. Se activa también en PR y cambios del frontend.
No incorpora pacientes, historial, rangos clínicos, diagnóstico ni nuevas tareas.


## Hito 6A: motor técnico DDK (pendiente de revisión final)

Abrir `/ddk` en el mismo servidor. Captura/subida, selección de TODO el tramo,
detección de núcleos candidatos, anclaje opcional para tríadas candidatas, tasas
automáticas estimadas, auditoría y revisión manual. No reconoce fonemas.
Solo después de confirmar todas las etiquetas manuales se muestran sílabas/ciclos
revisados. La revisión no valida el detector en habla humana: 6B sigue pendiente.

`POST /ddk-analysis`: WAV multipart, emission_start_s/emission_end_s; anchor_id
opcional. Para revisión, mismo WAV, expected_file_sha256 y review_json con
operaciones ordenadas, confirmed y confirm_absence. Original automático,
modificaciones y revisión separados. Estados específicos: detección
completed/empty/failed; agrupación completed/not_requested/blocked; cálculo
completed/partial/blocked; revisión not_requested/draft/completed. Una cifra null
lleva motivo. El estado completed no cierra el hito ni demuestra validez clínica.

Límite DDK 4.000.000 bytes y 15 s, margen respecto al multipart Vercel. El límite
histórico de vocal (10 MiB) no cambia: sigue siendo superior al límite documentado
de payload de Vercel (4.5 MB). No se atribuye ese tamaño a la plataforma.

Configuración independiente `configs/ddk_experimental_v1.json`; stdlib Python,
sin modificar dependencias, algoritmos, scripts Praat ni pruebas previas.
Protocolo: `docs/protocolo_ddk_6a.md`; evidencia: `docs/verificacion_ddk_6a.md`.

```bash
python -m pytest tests/test_ddk.py -q
python -m tests.report_ddk
npm run test:ui
python -c 'from tests.synthetic_ddk import signal; from pathlib import Path; Path("/tmp/ddk-clean.wav").write_bytes(signal()[0])'
# Con la API iniciada:
npm run test:ddk-browser
```

DDK_TEST_WAV, DDK_SCREENSHOT y BASE_URL configuran pruebas de navegador.
No se incorporan personas, grabaciones humanas ni datasets clínicos.

## Hito 7A: frase estandarizada

Abrir `/phrase`. Lectura directa (`direct_reading_v1`) como condición principal para lectores funcionales. Frase fija: «La niña corta papel con tijeras y pega las tiras pequeñas sobre la mesa.»; 14 palabras / 25 sílabas canónicas de referencia, sin sinalefas. No son detecciones acústicas. Sin diagnóstico ni validación humana.

Dos intentos independientes, subida WAV o grabación, selección manual por índices de muestra, revisión manual y cuatro tasas separadas. Sin ASR, pausas automáticas, alineación, reconocimiento fonético ni detector silábico. Exporta JSON con WAV originales integrados, revisiones y estados; exportar antes de cerrar la página. No agrega intentos/modalidades. Las variantes auditivas requieren un WAV de modelo explícito identificado por hash.

`GET /phrase-protocol`; `POST /phrase-analysis`: multipart `file`, `context_json`, `review_json` opcional y `expected_file_sha256` obligatorio al revisar. Límite independiente 20 s / 4.000.000 bytes. Revisión ligada al hash del contexto. Protocolo completo y semántica de null/cero/error en `docs/protocolo_frase_7a_v1.md`.

```bash
python -m pytest tests/test_phrase.py -q
npm run test:ui
python -c 'from pathlib import Path; from tests.synthetic_phrase import wav; Path("/tmp/phrase-8s.wav").write_bytes(wav())'
# Con la API en ejecución:
npm run test:phrase-browser
```

La condición principal evita el modelo auditivo inmediato, pero lectura y seguimiento visual siguen siendo factores de confusión pendientes de validación humana. La frase no se presenta como clínicamente validada ni fonéticamente equilibrada. Hito 7B (pausas y velocidad articulatoria) fuera del alcance.
