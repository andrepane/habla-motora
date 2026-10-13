# Verificación del hito 2: F0

Fecha: 13/10/2026. Ejecución real en Docker, GitHub Actions, Linux amd64,
Ubuntu 24.04, Python 3.12.14. Motor observado:
`Praat 6.4.27 (January 27 2025)`.

## Evidencia

- Commit de implementación probado: `3d32dce9b4ac1cd8d683f2469d254222f217ab8d`.
- [Ejecución completa](https://github.com/andrepane/habla-motora/actions/runs/38414844676): success.
- Job: `115356415150`.
- [Resultados JSON del contenedor y HTTP](https://github.com/andrepane/habla-motora/actions/runs/38414844676/artifacts/11823796472).
- Imagen: `habla-motora:smoke-v1`.
- ID: `sha256:a05dc7aea955e9ec10e5d4f846ad43f0a1b246315797dba69f5b9a33e6fe5db9`.
- Dockerfile, versión de motor y dependencias del hito 1 conservados.
  Se reconstruyó esa receta con los archivos del módulo F0; no se reutilizó
  la imagen antigua, que no contenía pitch_v1.

## Versiones y procedencia

Módulo `pitch_v1`, esquema `pitch_output_v1`, advertencias `pitch_warnings_v1`.
Configuración `experimental_v1` conservada byte a byte:
`94b976f9c3e1f21d965df9ce547422953c6d780df64988cf2562cc8594520729`.
El bloque scope es histórico y no controla la implementación.
Hash del script pitch:
`66ef64ac2a5e0be13df838f60f8457da9c2822c517606d05e7aa9ddc3625dd92`.

Cada caso conserva su hash WAV y las versiones/hashes de configuración y scripts.
Se añade el hash del script de duración como procedencia auxiliar.

## Método

Praat analiza el WAV completo con raw cross-correlation y los diez parámetros
explícitos de v1. Get mean y Get standard deviation, en Hertz, se consultan en
el intervalo. No se atribuye una fórmula estadística propia: se conserva la
semántica de bordes de Praat. Los frames exportados son los valores directos
del candidato seleccionado, sin interpolación de huecos ni corrección de octavas.

Cobertura: frames con F0 definida / frames cuyo centro pertenece al intervalo,
con límites inclusivos. No equivale a duración fonada ni demuestra exactitud.
Media/DT no calculables se exportan como null con motivo. Cobertura 0 % y DT
0 Hz pueden ser valores válidos. Ciclos glóticos: null/not_implemented.

Las entradas estándar seleccionan los tres segundos centrales de la emisión.
Si no se proporcionan límites se registra file_assumed_as_emission.
Los intervalos arbitrarios de diagnóstico son solo de Python y se identifican
expresamente como distintos del protocolo estándar.

## Señales y resultados exactos observados en Docker

Señales PCM16 mono, 6 s, 44.100 Hz. Ventana 1,5–4,5 s: 600 frames.
Amplitud 0,3. Ruido uniforme con semilla 20261013.
Modulación: f(t)=200+20*sin(2*pi*2*t), con fase integrada continuamente.
Tono–silencio–tono: 200 Hz, silencio digital entre 2,5 y 3,5 s.
Fundamental débil: amplitud 0,0001 a 200 Hz y 0,3 a 400 Hz.

| Caso | F0 media (Hz) | DT de F0 (Hz) | Frames definidos/totales | Cobertura (%) |
|---|---:|---:|---:|---:|
| tone_100 | 100.00000114928828 | 8.55092349e-8 | 600/600 | 100 |
| tone_200 | 199.99991673923483 | 0.00004271979354988 | 600/600 | 100 |
| tone_400 | 400.000413500297 | 0.00007910385848626 | 600/600 | 100 |
| modulated | 199.99945144383673 | 14.133393065730301 | 600/600 | 100 |
| tone_silence_tone | 199.99607741567297 | 0.07514557599236601 | 401/600 | 66.83333333333333 |
| silence | null | null | 0/600 | 0 |
| noise_seed_20261013 | null | null | 0/600 | 0 |
| below_range_50 | null | null | 0/600 | 0 |
| above_range_700 | 350.0000046783828 | 0.00000240046621022 | 600/600 | 100 |
| weak_fundamental_200 | 399.99673765490985 | 0.00006041685041197 | 600/600 | 100 |

En la modulación:
- Media teórica continua: 200 Hz.
- DT teórica continua: 14.142135623730951 Hz.
  Es orientación analítica, no sustituto de la consulta de Praat con sus bordes.
- Error máximo frente a la frecuencia instantánea en los centros:
  1.1007131971518902 Hz.
- RMSE por frame: 0.7491824416833277 Hz.

## Pruebas y API

- Construcción Docker: correcta, incluido pytest.
- Durante construcción: `30 passed, 1 xfailed, 1 warning in 6.66s`.
- Nueva suite completa dentro del contenedor:
  `30 passed, 1 xfailed, 1 warning in 6.64s`.
- 31 casos de prueba en total: 30 superados; uno NO superado y registrado como
  xfail estricto. No se contabiliza el xfail como éxito.
- Incluye las ocho regresiones del hito 1, tres tonos, modulación, huecos,
  silencio, caracterización de ruido/fuera de rango/fundamental débil,
  intervalos sin frames y con un frame, entradas inválidas, API,
  hashes/versiones y detector experimental de saltos.
- Un script de referencia separado, con parámetros explícitos idénticos,
  devuelve exactamente las mismas consultas estadísticas y frames para el
  tono modulado. Es verificación de integración con el mismo motor, no una
  validación independiente del algoritmo ni una prueba manual del escritorio.
- /health: HTTP 200; status alive.
- /smoke-test: HTTP 200; WAV del hito 1: 2.0 s.
- /pitch: HTTP 200; media 199.99991673923483 Hz; DT
  0.00004271979354988 Hz; cobertura 100 % para el tono de 200 Hz.
- Consulta de un único frame: DT null; intervalo sin frames:
  media, DT y cobertura null.

## Incumplimientos y limitaciones

- El objetivo exploratorio de error máximo por frame <=0,5 Hz en la modulación
  NO se cumple: 1,1007131971518902 Hz. Se conserva como xfail estricto, sin
  relajar el criterio ni modificar parámetros v1. La media y DT sí cumplen
  sus criterios propuestos (0,2 y 0,3 Hz de error, respectivamente).
- A 700 Hz, fuera del rango, Praat encuentra 350 Hz con cobertura 100 %.
- Con fundamental de 200 Hz muy débil, encuentra aproximadamente 400 Hz con
  cobertura 100 %. Un error de octava estable no dispara el aviso de saltos.
- Ruido: solo una realización uniforme; F0 no detectada en ella no demuestra
  ausencia de falsos positivos con otras señales.
- El aviso de 11–13 semitonos se ha probado con frames controlados: no se
  afirma sensibilidad validada para todos los errores del motor.
- No se distingue automáticamente silencio, falta de periodicidad o fallo
  del tracking. La salida dice F0 no detectada.
- Pruebas acústicas en PCM16/44.100 Hz y Linux amd64. No validado en voz real,
  micrófonos variados, ARM ni Docker Desktop de Windows.
- Permanece el aviso de deprecación Starlette/AnyIO y los avisos no bloqueantes
  de construcción/acciones documentados en el hito 1.
- No hay interpretación clínica ni implementación de jitter, shimmer, HNR
  o CPP/CPPS. No se ha iniciado el hito 3.
