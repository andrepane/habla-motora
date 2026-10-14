# Hito 6A — protocolo aprobado antes de implementar

Base: main e31363b. Fecha: 14/10/2026. Cierre sujeto a revisión final de Andrea.
6B (habla humana) pendiente y no bloqueante. Sin reclutamiento ni corpus clínico.

## Captura y selección

Consigna: repetir pa-ta-ka rápido y claro, sin cambiar orden; práctica previa.
Objetivo 8 s de producción y 1 s de margen por extremo. Dos intentos independientes,
30 s de descanso; no elegir automáticamente el mejor. WAV mono PCM16/24/32,
44100/48000 Hz, máximo 15 s y 4.000.000 bytes (margen respecto a multipart Vercel).
Conservar bytes originales y ajustes consultados de captura. Sin normalización,
conversión, filtrado de audio ni calibración SPL. Selección manual de primera a
última sílaba completa; mantener errores, reinicios y pausas interiores. Se analiza
TODO el tramo; no se hereda la ventana central de 3 s de vocal sostenida.

## Detector y fronteras

RMS Hann de 20 ms, paso 5 ms, dB digitales, suelo -120 dB. Umbral
max(P10+6, P90-25), percentiles con interpolación lineal. Picos/mesetas separados
por valles de al menos 3 dB y 50 ms; conflicto: conservar el más alto, empate el
primero. Exportar rechazados y motivos. Meseta: centro temporal; contraste respecto
a mínimos a izquierda/derecha hasta un pico mayor o el borde del contorno.
Frames centrados dentro de la selección, ventanas tomadas del WAV completo;
ventanas que cruzan la selección se marcan como bordes incompletos y sus candidatos
no se aceptan automáticamente. Timestamp = centro de envolvente, NO inicio fonético.
Energía constante, silencio o sin candidatos: conteo candidato 0, tasas null.
No inventar picos ni forzar regularidad. No identidad fonética automática.
Agrupar candidatos completos de tres desde un anclaje explícito; sin anclaje,
agrupación not_requested, no tríadas ni tasas de tríadas. Resto visible.

## Matemática y revisión

Ns/T y Nc/T, T=fin-inicio incluye pausas. DT MUESTRAL (n-1); CV=100*DT/media,
intervalos en ms. Mínimo 3 intervalos para DT/CV; media temporal de intervalos
puede existir con 1. Sin eventos: tasas null, salvo ausencia revisada explícita.
Núcleos automáticos no son sílabas. Tríadas no son ciclos fonéticos.
Después de revisión completa: sílabas revisadas y ciclos revisados; ciclos solo
pa/ta/ka consecutivos, mismo segmento, no reutilizados. Reinicios cortan grupos y
series de intervalos; transiciones excluidas exportadas. Pausas no se excluyen
por su longitud. Unknown impide finalizar revisión. Eventos descartados no se
cuentan. Revisar puede añadir/eliminar/mover/etiquetar/reanclar mediante reinicio.
Original automático, operaciones ordenadas y resultado revisado siempre separados.
Todo recálculo ocurre en backend; revisión enviada con mismo WAV y hash esperado.

## Estados específicos DDK

Cada etapa tiene estado, salida y motivo; no se imita shimmer/hnr.
Detección completed/empty/failed. Empty conserva evidencia con tasas null; failed
retiene entrada y límites válidos, auditoría diagnóstica y etapas dependientes blocked.
Agrupación completed/not_requested/blocked; anclaje inválido es HTTP 422.
Cálculo completed/partial/blocked: partial significa algunas medidas null por
falta de acontecimientos/intervalos, nunca una cifra inventada. No borrar otras
medidas definidas. Revisión not_requested/draft/completed; draft NO se publica
como sílabas/ciclos revisados. Revisión completa puede recuperar medidas tras
detector vacío o fallido mediante acontecimientos manuales; original preservado.
Invalid review -> 422, sin reemplazar resultado original en navegador.
Estado global completed/partial: partial si detección failed/empty o cálculo parcial;
not_requested de agrupación/revisión no es fallo. Completed significa ejecución,
NO validación humana ni cierre del hito. Excepción inesperada -> 503, no captura
indiscriminada como estado parcial exitoso.

## Criterios congelados

Conteos matemáticos exactos; tasas/CV error absoluto <=1e-9 en sus unidades,
DT contra casos analíticos. Sintéticos LIMPIOS y separables: conteo exacto y error
máximo de centros <=10 ms; matriz 2/4/6/8/10/12 acontecimientos/s, 44100/48000,
PCM16/24/32, envolventes variables. Referencia conocida independiente del detector.
Caracterización: amplitud baja, transitorios, omisiones/duplicados, pausas
0.2/0.5/1 s, ruido con semillas, clipping, mesetas, fronteras. Publicar errores,
sin exigir recuperación en señal difícil ni relajar tolerancias después.
Edición: replay determinista, original intacto, integridad hash, rechazo de NaN,
fuera de intervalo, ids duplicados, tiempos coincidentes, límites y revisión incoherente.
Frontend/API/Vercel: captura/subida, selección, gráficos/tablas, parcial/empty/failed,
revisión, cancelación, invalidación y exportación; regresiones previas intactas.
Los seis xfail previos son incumplimientos; no modificar ni relajarlos.
6A no se cierra automáticamente por CI; Preview y evidencia a revisión del usuario.

## 6B pendiente

Anotación manual independiente y corpus futuro: referencias, tolerancias y
separación desarrollo/evaluación se aprobarán antes. No existe criterio humano
obligatorio en 6A ni inferencia clínica. Revisión manual de un archivo NO valida
el detector en habla humana. Texto visible: Validación técnica con señales
controladas. Validación en habla humana pendiente.
