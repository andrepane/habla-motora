# habla-motora — hito 1

Nombre técnico provisional. Herramienta experimental de medición del habla motora
orientada a una futura presentación a COLOAN. Este hito contiene únicamente un
smoke test de infraestructura con Praat. Sin frontend ni interpretación clínica.

## Qué hace

Recibe un WAV PCM mono, 16/24/32-bit, 44.100/48.000 Hz, hasta 10 MiB. Ejecuta el
script fijo `praat/smoke_test.praat` y devuelve la duración del archivo completo.
No detecta el segmento de vocal ni implementa F0, jitter, shimmer, HNR o CPP/CPPS.

Cada resultado incluye versión exacta de Praat, versión del protocolo y
configuración, SHA-256 de los bytes exactos de configuración, del WAV y del script.
Cobertura de F0 y ciclos aceptados son obligatorios y permanecen `null` con motivo
`not_implemented`. Los fallos devuelven error, nunca medidas 0. No hay métricas
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
