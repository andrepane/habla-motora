# Protocolo experimental v1

Nombre técnico provisional: habla-motora. Sin denominación comercial.

Medida temporal prevista: duración del segmento seleccionado manualmente.
El smoke test implementado mide exclusivamente la duración del archivo completo;
no detecta la vocal ni selecciona el segmento.

Medidas acústicas previstas, NO implementadas: F0 media (Hz), desviación típica
muestral de F0 (Hz), jitter local (%), shimmer local (%) y HNR mediante
Harmonicity (cc) (dB). CPP/CPPS queda fuera.

Selección prevista: /a/ cómoda de 5–8 s; ventana central de 3 s sin buscar el
mejor resultado. Análisis sobre el audio completo, consultas dentro de la ventana.
No hay normalización, eliminación de ruido ni conversión automática de canales.

Todos los parámetros están en configs/experimental_v1.json. Es una configuración
experimental: no expresa normalidad clínica. Una vez registrada una prueba, no
se modifica v1: se añade v2 y se conserva v1 con sus resultados y hashes.
El hash se calcula sobre los bytes exactos del JSON (también cambia al reformatear).
La versión de Praat y la huella del script forman parte de cada resultado.

Cobertura de F0, ciclos aceptados y advertencias técnicas son obligatorios.
Actualmente los dos primeros son null con motivo not_implemented. No existen
umbrales de rechazo acústico todavía; sus definiciones operativas deberán fijarse
antes de implementar las métricas. Ausencias y errores nunca se convierten en 0.

Categorías: validada técnicamente (solo después de demostrar concordancia),
experimental (pendiente de verificación), interpretación clínica (logopeda).
Ninguna métrica está validada en este hito. El smoke test comprueba infraestructura,
no exactitud acústica, fiabilidad clínica, utilidad diagnóstica ni seguimiento.
No genera etiquetas de patología, disartria o Parkinson. No usa NeuroVoz.
