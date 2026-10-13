# Protocolo experimental v1

Nombre técnico provisional: habla-motora. Sin denominación comercial.

Medida temporal prevista: duración del segmento seleccionado manualmente.
El smoke test implementado mide exclusivamente la duración del archivo completo;
no detecta la vocal ni selecciona el segmento.

Medidas acústicas del protocolo: F0 media (Hz), desviación típica de F0 (Hz), obtenida mediante
`Pitch: Get standard deviation` de Praat 6.4.27, jitter local (%), shimmer local (%) y HNR mediante
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
En el smoke test del hito 1 ambos son null con motivo not_implemented.
En pitch_v1 se informa cobertura de F0; los ciclos glóticos siguen sin implementar. No existen
umbrales de rechazo acústico todavía; sus definiciones operativas deberán fijarse
antes de implementar las métricas. Ausencias y errores nunca se convierten en 0.

Categorías: validada técnicamente (solo después de demostrar concordancia),
experimental (pendiente de verificación), interpretación clínica (logopeda).
Ninguna métrica está validada en este hito. El smoke test comprueba infraestructura,
no exactitud acústica, fiabilidad clínica, utilidad diagnóstica ni seguimiento.
No genera etiquetas de patología, disartria o Parkinson. No usa NeuroVoz.


## Estado de implementación separado de la configuración

El JSON experimental_v1 es inmutable y su bloque scope es información histórica.
El módulo pitch_v1 registra module_version, output_schema_version y warnings_version.
Las consultas estadísticas conservan exactamente la semántica de Praat; no se
atribuyen fórmulas propias ni se interpolan huecos de tracking_frames.
Jitter local se incorpora como módulo experimental jitter_v1. Shimmer local se incorpora
como módulo experimental shimmer_v1. HNR se incorpora como hnr_v1 experimental.
CPP/CPPS no se han implementado. El recuento opcional de pares de jitter
permanece null/not_implemented; se utilizan las consultas de Praat para valor
y períodos aceptados, sin sobreescribir un valor finito por pocos pulsos.


## Hito 4: shimmer local experimental (criterios congelados antes de las pruebas)

Sound completo -> Pitch raw cross-correlation -> Sound + Pitch -> PointProcess (cc).
Sound + PointProcess: Get shimmer (local), ventana central de 3 s, períodos
0.8/600 y 1.25/75 s, maximum period factor 1.3 y maximum amplitude factor 1.6.
El resultado nativo relativo se multiplica por 100 una vez. undefined -> null;
todo valor finito se conserva como experimental, sin inferencias de estabilidad vocal.
No se modifica experimental_v1 ni se normaliza, filtra o corrige el audio.

Praat 6.4.27 extrae un RMS con Hann centrado en cada pulso interior, con anchuras
izquierda y derecha de 0.2 veces cada período vecino. Ambos períodos deben
cumplir límites y razón <=1.3; RMS indefinido o no positivo se omite. Los pulsos
extremos de la selección no generan amplitudes. To AmplitudeTier (period) exporta
las mismas amplitudes; Down to TableOfReal solo se ejecuta si el tier no está vacío.
Para comparar amplitudes, Praat exige separación temporal dentro de los límites
y razón de amplitud <=1.6. En AmplitudeTier_getShimmer_local de esta versión,
el numerador es la diferencia absoluta media de los pares admitidos, mientras
el denominador incluye todos los puntos del tier excepto el último. No se
sustituye esta regla de borde por otra fórmula. La eliminación de puntos puede
hacer consecutivos puntos no adyacentes del proceso original.

Períodos aceptados (Get number of periods) no significa amplitudes ni pares
aceptados para shimmer. Se exportan pulsos, períodos y amplitudes nativas,
recuentos de amplitudes extraídas/no extraídas y de límites digitales del WAV.
shimmer_pairs_used permanece null/not_implemented. La comprobación sencilla de
razones superiores a 1.6 no se presenta como recuento de pares usados.

Versiones separadas: shimmer_v1, shimmer_output_v1, shimmer_warnings_v1.
Procedencia: versión Praat/protocolo/configuración, hash de configuración/WAV,
script principal y scripts auxiliares de duración, pitch y jitter. La ruta nativa
se repite para shimmer y se exige igualdad de pulsos y períodos con la auditoría
reutilizada; una discrepancia sería un error técnico de integridad.

Advertencias: se conservan F0, exclusiones de períodos, saturación y fiabilidad
de pulsos no verificada. Se añaden shimmer no calculable, amplitudes no extraídas,
razones superiores a 1.6 y RMS digital inferior a 10 pasos PCM en la ventana.
Este último es un aviso experimental de cuantificación, nunca un umbral clínico
ni un rechazo. La ausencia de muestras en los límites PCM no descarta saturación
previa del micrófono. Amplitudes en unidades digitales de Sound, sin calibración
para convertirlas en presión sonora física.

Validación separada: (1) amplitudes/tiempos conocidos con fórmula independiente y
casos analíticos; (2) consulta sobre AmplitudeTier conocido y Sound + PointProcess
impuesto, sin detector, incluyendo extracción independiente sobre muestras PCM;
(3) recorrido completo desde WAV. Usar otro script del mismo motor verifica
integración, no exactitud independiente. En WAV limpio se comprueba además
correspondencia de pulsos, sin aceptar una cifra acertada por coincidencia.

Todas las tolerancias son errores absolutos en PUNTOS PORCENTUALES. S_ref es el
valor de referencia expresado en porcentaje (por ejemplo, 5.0 para 5 %).
No se evalúan sobre razones sin multiplicar por 100.

- Fórmula matemática frente a AmplitudeTier: error_pp <= 0.00000001.
- Integración frente a consulta nativa separada:
  error_pp <= 0.000001 * max(1.0, abs(S_ref)).
- Extracción con pulsos impuestos sobre WAV limpio:
  error_pp <= max(0.01, 0.01 * abs(S_ref)).
- Recorrido completo limpio, alternante y aleatorio:
  error_pp <= max(0.05, 0.10 * abs(S_ref)).
- Ganancia constante sin clipping: cambio_pp <= 0.01 y sin pulsos perdidos/añadidos.
- Ruido 40/30 dB: criterio del recorrido completo limpio.
- Ruido 20/10 dB, amplitud muy baja, clipping y pulsos alterados: caracterización,
  sin exigir recuperación de la cifra original.

Ejemplos para S_ref=0, 1, 5 %: tolerancias de integración 0.000001, 0.000001,
0.000005 pp; extracción 0.01, 0.01, 0.05 pp; recorrido 0.05, 0.10, 0.50 pp.
Estas tolerancias no se relajan después de observar resultados. Los cuatro
xfail anteriores permanecen intactos.

Señales: seis segundos a 200 Hz, PCM16/44100, amplitudes alternantes nominales
0, 0.5, 1, 2 y 5 %, amplitudes aleatorias positivas (semilla 20261014), ganancias
0.1/2/0.001/0.0001, ruido gaussiano 40/30/20/10 dB (semilla 20261014), clipping,
pulsos perdidos/añadidos/desplazados, período anómalo y amplitud anómala.
Se prueban límites de períodos y razones 1.3/1.6 antes/en/después del límite.
Los casos en el límite se describen según los tiempos binary64 efectivos,
sin introducir tolerancias nuevas en los filtros del motor.
La referencia finita se calcula sobre la secuencia seleccionada y sobre las
muestras PCM reales; el nominal no sustituye la referencia. Alternar amplitudes
puede inducir periodicidad doble: cualquier error se caracteriza sin corregirlo.
No existe validación en voz humana ni interpretación clínica automatizada.

## Hito 5: HNR experimental — protocolo corregido y criterios previos

La medida oficial hnr_mean_db procede EXCLUSIVAMENTE de Harmonicity: Get mean,
con su semántica temporal nativa de Praat. No se describe ni se reimplementa
como una media aritmética simple de los frames exportados. La documentación
oficial la define como media temporal de la curva, ignorando indefinidos.
Los frames son auditoría. COBERTURA y mecanismo de MEDIA son distintos.
No se exige coincidencia con una media aritmética simple calculada en Python.

Sound completo -> To Harmonicity (cc): 0.01, 75, 0.1, 4.5 -> Get mean: inicio, fin.
Misma ventana central de 3 s; sin normalización ni filtros. No depende de Pitch
ni PointProcess y no hereda el techo de 600 Hz de F0. HNR en dB; cero y valores
negativos finitos pueden ser válidos. undefined -> null; todos los valores
finitos conservan estado experimental, sin interpretación clínica.

Auditoría de frames con centro inclusivamente dentro del intervalo:
frame_index, time_s, praat_raw_hnr_db, hnr_db, valid, reason y numerical_limit.
Get value in frame, sin interpolación. Praat 6.4.27 almacena -200 como marcador
non-sounding: se conserva como valor bruto para auditoría, pero hnr_db=null.
Los límites numéricos nativos +/-150 dB se conservan con advertencia: no son
precisión demostrada. Cobertura = 100 * frames válidos / frames interiores.
Sin frames: cobertura null; con frames pero ninguno válido: cobertura 0.
La media undefined devuelve null sin convertirla en cero ni sustituirla por
una estadística de frames. No hay umbral de rechazo por cobertura.

Versiones separadas: hnr_v1, hnr_output_v1, hnr_warnings_v1. experimental_v1
permanece byte a byte. Registro obligatorio de motor/protocolo/configuración,
hash WAV/configuración/script HNR y script auxiliar de duración. scope es histórico.
Advertencias: periodicidad no verificada, no calculable, cobertura incompleta,
frames excluidos por el motor, límites numéricos, posible clipping y RMS <10
pasos PCM (aviso de cuantificación, sin rechazo). No se infiere silencio de
un marcador no válido ni se clasifica ruido a partir de HNR. El umbral 0.1 es
relativo al máximo del archivo completo, incluso fuera del intervalo analizado.

Tolerancias fijadas ANTES de ejecutar las nuevas pruebas; diferencias absolutas
expresadas en dB, excepto la cobertura:

- Objetos controlados: error <=0.00000001 dB cuando se pueda establecer el
  resultado exactamente respetando la semántica nativa (curva constante y
  exclusiones con valor constante restante, o todos los valores no válidos).
  Objetos no constantes y bordes desplazados: caracterización de la consulta
  nativa; no se asigna una referencia por media aritmética simple de frames.
- Integración frente a script Praat separado, con la misma consulta Get mean:
  error de media y por frame <=0.000001 dB; mismos índices y estados válidos.
- Recuentos y cobertura: exactos según la definición operacional anterior.
  Se calcula el cociente de enteros, no se aproxima duración / paso temporal.
- Ganancia x0.1/x2 sobre tono+ruido a 20 dB: cambio <=0.1 dB y mismos estados
  de validez. Se escala conjuntamente tono y ruido, sin clipping.
- Tono limpio de período exacto en muestras: cobertura 100 %, media >=40 dB.
  Objetivo sintético de ingeniería, sin umbral clínico ni valor HNR ideal finito.
- Veinte realizaciones de ruido (semillas enteras 5000 a 5019), compartidas entre
  niveles: media entre realizaciones estrictamente creciente para SNR
  0 -> 10 -> 20 -> 30 -> 40 dB. Se publican dispersión y cobertura; no se
  descartan realizaciones para obtener la tendencia. Si falta una media,
  se registra como incumplimiento, no se elimina silenciosamente.
- Otras condiciones difíciles: caracterización, sin exigir HNR=SNR ni recuperar
  el HNR de una señal anterior al ruido, clipping o cuantificación.

Señales de 6 s y selección 1.5-4.5 s: tonos 100/200/400 Hz, tono+ruido gaussiano
40/30/20/10/0 dB, silencio, ruido solo, tono-silencio-tono, ganancias x0.1/x2,
x0.001/x0.0001, clipping, 50/74/76/700 Hz, armónicos enteros controlados,
fundamental débil y componente no armónica. PCM16/44100 y 48000 donde proceda;
48 kHz permite período exacto en muestras a 100/200/400 Hz.
Se prueba efecto del máximo global con y sin fragmento fuerte exterior.

Validación separada: (1) consulta sobre Harmonicity controlado creado mediante
Matrix, sin detector, con referencias inequívocas constantes; (2) otro script
Praat, integración; (3) WAV con componentes conocidas y correlación independiente
al período verdadero sin búsqueda del máximo. Esta última caracteriza el
estimador, no reimplementa Praat ni determina la medida oficial. Para señal
periódica estacionaria más ruido independiente, r(T0) se aproxima a Ps/(Ps+Pn),
pero ventanas finitas, selección de máximos, espectro, cuantificación y media
en dB impiden exigir igualdad exacta HNR=SNR. Un tono perfecto tiene relación
ideal infinita; se caracteriza el valor finito del motor sin forzarlo.

Los cuatro xfail históricos se conservan íntegros. Ningún criterio se relaja
tras los resultados. No hay validación en voz humana ni implementación CPP/CPPS.

La etiqueta congelada harmonicity.aggregation = mean_db_valid_frames se conserva
como descripción inicial; no autoriza a sustituir Get mean por una estadística propia.
