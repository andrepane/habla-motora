# Verificación del hito 1

Comprobado el 13/10/2026 en Linux amd64, Python 3.12.14.
Motor real: Praat 6.4.27 (January 27 2025), distribución oficial barren.

- Smoke test real: 2.000000000000 s para un WAV de 88.200 muestras a 44.100 Hz.
- pytest: 8 passed, 1 warning (aviso de deprecación de Starlette/AnyIO).
- Incluye integración real con Praat y FastAPI; archivo inválido, límite de tamaño,
  ejecutable ausente, versión incorrecta, timeout y salida no finita.
- Cobertura de F0 y ciclos aceptados permanecen null; advertencias presentes.
- F0, jitter, shimmer y HNR no están implementados.

Limitaciones de esta verificación:
- Docker no está instalado en el entorno de trabajo: no se ha construido ni
  ejecutado la imagen. El Dockerfile incluye las pruebas en su construcción,
  pero su funcionamiento en Docker queda pendiente de confirmación.
- Repositorio público creado por el usuario: andrepane/habla-motora.
- No hay validación acústica ni clínica en este hito.
