# Verificación del hito 1 — Docker comprobado

Fecha: 13/10/2026. Ejecución real en GitHub Actions, Ubuntu 24.04, Linux amd64.
El entorno local no permite ejecutar Docker; se utilizó el runner de GitHub.
Estado final de la ejecución: success.

## Evidencia reproducible

- Commit probado: `97d8e8e96e169eb3ffa740b44a554977399661b7`.
- [Ejecución completa y registros](https://github.com/andrepane/habla-motora/actions/runs/38411194130).
- Job: `115343661032`.
- [JSON del smoke test y de ambos endpoints](https://github.com/andrepane/habla-motora/actions/runs/38411194130/artifacts/11822955319).
- Imagen construida: `habla-motora:smoke-v1`.
- ID de imagen observado: `sha256:767827c458dd81b91623faf48ece8ced21bee8b074a17a911b58a05988d6d0ce`.
- Base resuelta: `python:3.12.14-slim-bookworm@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e`.

## Resultados exactos

| Comprobación | Resultado |
|---|---|
| Construcción desde Dockerfile | Correcta; imagen exportada y código de salida 0 |
| pytest incluido en construcción | 8 passed, 1 warning in 0.47s |
| Praat ejecutado dentro del contenedor | Praat 6.4.27 (January 27 2025) |
| Smoke test dentro del contenedor | file_duration_s: 2.0; igualdad exacta con 2.0 comprobada |
| Nueva ejecución completa de pytest en contenedor | 8 passed, 1 warning in 0.45s |
| Arranque API | Uvicorn en 0.0.0.0:8000; Application startup complete |
| GET /health por HTTP desde el host al contenedor | HTTP 200; status: alive |
| POST /smoke-test con tone_2s.wav por HTTP | HTTP 200; file_duration_s: 2.0; Praat 6.4.27 |
| Cobertura F0 y ciclos aceptados | null, con reason: not_implemented |
| Advertencias técnicas del resultado | Presentes |

Respuesta de /health:

```json
{"status":"alive","note":"Does not establish Praat readiness"}
```

Archivo: `tests/fixtures/tone_2s.wav`, PCM16 mono, 44.100 Hz, 88.200 muestras.
Es un tono matemático, sin datos personales.

Procedencia observada tanto en CLI como en API:
- Protocolo: `v1`; configuración: `experimental_v1`.
- SHA-256 configuración: `94b976f9c3e1f21d965df9ce547422953c6d780df64988cf2562cc8594520729`.
- SHA-256 WAV: `666c692f98fe434bde26219f7ac62b7a69e835184f8ae40bf448f63168bfdd47`.
- SHA-256 script: `398b209f700ee812f9670f45f3c0c8a672c6926a2251be07ff10325f9bf4749f`.

## Corrección durante este hito

La primera ejecución Docker también pasó las 8 pruebas y ambos endpoints.
Produjo dos PytestCacheWarning por falta de permisos de escritura en /app para
el usuario sin privilegios. Se configuró la caché de pytest en
`/tmp/habla-motora-pytest-cache` y se repitieron construcción, smoke test,
suite completa y verificación HTTP. Esos avisos desaparecieron.

No fue necesario modificar el motor, el script ni la configuración experimental.
La verificación automática está en `.github/workflows/docker-smoke.yml`.

## Limitaciones y avisos restantes

- Verificado en Linux amd64; ARM y Docker Desktop en Windows no comprobados.
- Permanece un DeprecationWarning de Starlette/AnyIO; no afecta al resultado.
- Docker advierte sobre FROM --platform constante. Durante construcción pip
  informa de instalación como root; el proceso de ejecución usa el usuario app.
- Las acciones v4 producen avisos por transición Node 20 a Node 24.
- Una petición inicial puede fallar antes de que Uvicorn termine de arrancar:
  el workflow espera disponibilidad y verifica después HTTP 200 en ambos endpoints.
- La base y paquetes del sistema no están fijados íntegramente por digest/snapshot;
  no se promete reconstrucción bit a bit.
- /health solo informa de vida de la API; /smoke-test sí comprueba el motor real.
- Se mide la duración del archivo completo, no un segmento de vocal seleccionado.
- No hay validación acústica ni clínica. F0, jitter, shimmer, HNR y CPP/CPPS no
  están implementados. El hito 2 no se ha iniciado.
