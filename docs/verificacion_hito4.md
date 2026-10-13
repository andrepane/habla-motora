# Hito 4: shimmer local experimental — verificación en Docker

Fecha: 13/10/2026. GitHub Actions, Ubuntu 24.04, Linux amd64.
Python 3.12.14. Motor observado: `Praat 6.4.27 (January 27 2025)`.

## Evidencia

- Commit de implementación probado: `c782968a6e3f8db9c7c02fde4219330700c70de1`.
- [Ejecución y registros](https://github.com/andrepane/habla-motora/actions/runs/38422677944): success.
- Job `115383845613`.
- [JSON de señales y API](https://github.com/andrepane/habla-motora/actions/runs/38422677944/artifacts/11827262143).
- Misma receta Dockerfile y dependencias que en los hitos anteriores, reconstruida
  con shimmer y nuevas pruebas. No se cambia experimental_v1 ni sus bytes.
- Imagen `habla-motora:smoke-v1`: `sha256:b8ee01a64b410e514bae3f1a1859ba4a2a3f0ea26260b1b1c6cbaa2d689efb6e`.
- Pytest durante la construcción: `148 passed, 4 xfailed, 1 warning in 99.98s (0:01:39)`.
- Suite completa nuevamente dentro del contenedor: `148 passed, 4 xfailed, 1 warning in 99.84s (0:01:39)`.
- Total 152 casos: 148 passed, cuatro xfail anteriores conservados; 72 pruebas
  nuevas de shimmer. Cero nuevos xfail y cero fallos inesperados.
- /health, /smoke-test, /pitch, /jitter y /shimmer: HTTP 200.
- /smoke-test mantiene exactamente 2.0 s; /shimmer nominal 0.5 % devuelve
  0.500758145420238 %, con versiones, hashes, auditoría y advertencias.

Docker se ejecuta en GitHub Actions porque este entorno local no tiene Docker.
La prueba local no se presenta como evidencia de contenedor.

## Configuración, alcance y procedencia

Hash SHA-256 de experimental_v1, intacto:
`94b976f9c3e1f21d965df9ce547422953c6d780df64988cf2562cc8594520729`.
Versiones: shimmer_v1, shimmer_output_v1, shimmer_warnings_v1.
Hash del script shimmer: `cbbdcf9f02ff73c6cdb4c64e9df609a7166e336c9371e1c176d75f367284a0b2`.
Cada resultado conserva además versión de Praat/protocolo/configuración, hash WAV,
y hashes de scripts auxiliares de duración, pitch y jitter. scope del JSON es histórico.
No se modifican scripts ni pruebas F0/jitter, los cuatro xfail, Dockerfile o dependencias.

Sound completo -> Pitch raw cross-correlation con parámetros v1 -> Sound + Pitch
-> PointProcess (cc) -> Sound + PointProcess: Get shimmer (local).
Ventana central de 3 s; períodos 0.8/600 y 1.25/75 s; factores 1.3 y 1.6.
Proporción nativa multiplicada por 100 una sola vez. No hay normalización,
filtrado, relleno de huecos, corrección de octavas ni selección del mejor resultado.

Todos los valores finitos se conservan como experimental_pulse_reliability_unverified;
undefined -> null/praat_undefined. Solo se rechazan fallos de ejecución o integridad
numérica, incoherencias de recuentos/orden y discrepancias entre auditorías nativas,
sin una regla clínica paralela. Un cero real puede conservarse como cero.
HNR y CPP/CPPS no se implementan; no se inicia el hito 5.

## Amplitudes y auditoría

La extracción se hace con To AmplitudeTier (period), utilizando el propio motor.
En Praat 6.4.27 la amplitud es RMS con Hann alrededor del pulso, anchuras
0.2*T_izquierdo y 0.2*T_derecho, no máximo ni pico a pico. Ambos períodos deben
cumplir los límites y razón <=1.3; la amplitud debe ser definida y positiva.
Los dos pulsos extremos no generan amplitudes. Se exportan tiempos y valores
mediante Down to TableOfReal; no se intenta convertir un tier vacío a tabla.
No hay calibración del micrófono: las unidades de Sound no se interpretan como SPL.

En AmplitudeTier_getShimmer_local, los pares consecutivos del tier deben tener
separación dentro de los límites y razón de amplitud <=1.6. El denominador
incluye todos los puntos del tier excepto el último, según este código versionado.
No se reemplaza esa regla por una media propia. Los puntos eliminados pueden
hacer consecutivos puntos que no eran adyacentes en el proceso original.
Referencia del motor: [AmplitudeTier.cpp v6.4.27](https://github.com/praat/praat/blob/v6.4.27/fon/AmplitudeTier.cpp).

Se reutilizan tracking_frames, tracking_pulses, tracking_periods, cobertura F0
y Get number of periods. Este último cuenta períodos admitidos temporalmente:
NO es un recuento de amplitudes ni de pares aceptados para shimmer.
shimmer_pairs_used permanece null/not_implemented. El examen sencillo de razones
>1.6 solo es una advertencia opcional; no reconstruye el algoritmo de pares.

Las cinco señales alternantes limpias tienen 601 pulsos, 600 períodos candidatos,
600 períodos aceptados y 599 amplitudes extraídas en la ventana inclusiva.
No hay amplitudes interiores excluidas; dos pulsos de borde carecen de amplitud.
La producción verifica que la repetición del recorrido nativo de shimmer conserve
los mismos pulsos y períodos de la auditoría reutilizada de jitter.

## Referencias independientes y tolerancias congeladas

Tres niveles separados:
1. Fórmula independiente sobre tiempos/amplitudes conocidos, con ocho ejemplos
   analíticos que incluyen exclusiones y undefined. Consulta de AmplitudeTier
   conocido: no necesita Sound, Pitch ni detector acústico.
2. Sound sintético + PointProcess impuesto. La extracción Hann RMS se comprueba
   independientemente sobre muestras PCM decodificadas. Incluye pulsos correctos
   y erróneos, sin depender del detector de Praat.
3. WAV completo -> detección de Pitch/pulsos -> shimmer. Se compara con amplitudes
   fuente conocidas y se exige correspondencia de pulsos en las pruebas limpias.
Otro script del mismo motor prueba integración; no se presenta como exactitud independiente.

Error = abs(S_obtenido - S_ref), ambos en porcentaje: unidad puntos porcentuales (pp).
Las fórmulas completas se fijaron antes de programar y no se modificaron:

- Matemática: error_pp <= 0.00000001.
- Integración: error_pp <= 0.000001 * max(1.0, abs(S_ref)).
- Extracción limpia con pulsos impuestos: error_pp <= max(0.01, 0.01 * abs(S_ref)).
- Recorrido completo limpio, alternante/aleatorio: error_pp <= max(0.05, 0.10 * abs(S_ref)).
- Ganancia constante sin clipping: cambio_pp <= 0.01 y sin pulsos perdidos/añadidos
  según la correspondencia sintética del hito 3.
- Ruido 40/30 dB: criterio del recorrido limpio.
- Ruido 20/10 dB, amplitud baja, clipping y errores de pulsos: caracterización,
  sin exigir recuperación de la amplitud original.

Los cinco niveles alternantes y tres aleatorios superan los criterios limpios.
Máximo error entre fórmula fuente y AmplitudeTier conocido: 1.0658141036401503e-14 pp.
Máximo error entre extracción independiente de PCM y Sound + PointProcess impuesto
para los casos de caracterización: 2.708944180085382e-13 pp.
En los cinco niveles alternantes, consulta sobre tier extraído y consulta directa
Sound + PointProcess concuerdan dentro de la tolerancia de integración.

## Señales

Pulsos gaussianos de forma constante, sigma 0.2 ms, amplitud base 0.3, a 200 Hz.
Seis segundos, PCM16 mono/44100 Hz; muestras generadas en centros (i+0.5)/fs.
Selección 1.5–4.5 s. Amplitudes alternantes A0*(1 +/- nominal/200).
Las referencias se calculan para la secuencia finita seleccionada, conservando
la semántica del denominador. Series aleatorias positivas y ruido gaussiano
con semilla 20261014. El nominal no sustituye la referencia matemática real.
SNR calculado sobre RMS del archivo antes de ganancia.

## Resultados exactos dentro del contenedor

| Caso | Shimmer obtenido (%) | Referencia fuente (%) | Error (pp) | Pulsos interiores | Períodos aceptados | Amplitudes extraídas | Interiores no extraídas |
|---|---:|---:|---:|---:|---:|---:|---:|
| shimmer_0 | 0.002965485410149 | 0 | 0.002965485410149 | 601 | 600 | 599 | 0 |
| shimmer_0.5 | 0.500758145420238 | 0.5 | 0.0007581454202379989 | 601 | 600 | 599 | 0 |
| shimmer_1 | 1.000824228373228 | 1 | 0.000824228373228042 | 601 | 600 | 599 | 0 |
| shimmer_2 | 2.000301140533101 | 2 | 0.00030114053310104083 | 601 | 600 | 599 | 0 |
| shimmer_5 | 4.9991950924499 | 5 | 0.000804907550100431 | 601 | 600 | 599 | 0 |
| random_1 | 1.005400083888125 | 1.005326997685911 | 7.308620221402329e-05 | 601 | 600 | 599 | 0 |
| random_2 | 2.010875384473584 | 2.0109234219444585 | 4.8037470874451316e-05 | 601 | 600 | 599 | 0 |
| random_5 | 5.0293303402954415 | 5.029330337682051 | 2.6133903929803637e-09 | 601 | 600 | 599 | 0 |
| gain_0.1 | 0.9939112585247789 | 1 | 0.006088741475221093 | 601 | 600 | 599 | 0 |
| gain_2 | 1.0005750513942089 | 1 | 0.0005750513942088809 | 601 | 600 | 599 | 0 |
| low_amplitude_0.001 | 1.299999983491074 | 1 | 0.29999998349107404 | 600 | 599 | 598 | 0 |
| low_amplitude_0.0001 | 4.47e-12 | 1 | 0.99999999999553 | 300 | 299 | 298 | 0 |
| clipping_gain_5 | 0.354800392777561 | 1 | 0.6451996072224391 | 600 | 599 | 598 | 0 |
| noise_40dB | 0.9970471213739609 | 1 | 0.0029528786260391016 | 600 | 599 | 598 | 0 |
| noise_30dB | 0.990773278109375 | 1 | 0.009226721890625011 | 599 | 598 | 597 | 0 |
| noise_20dB | 1.131515404127765 | 1 | 0.13151540412776508 | 599 | 598 | 597 | 0 |
| noise_10dB | 2.781040062367859 | 1 | 1.7810400623678588 | 600 | 599 | 598 | 0 |
| lost_pulse | 1.000820031889581 | 1.0000084034319616 | 0.0008116284576193955 | 599 | 597 | 595 | 2 |
| added_pulse | 0.998495006763237 | 0.998324958123953 | 0.00017004863928393732 | 601 | 600 | 599 | 0 |
| shifted_pulse | 1.000824228373236 | 1.0000084034319616 | 0.0008158249412744123 | 599 | 597 | 595 | 2 |
| long_period | 1.000807915135286 | 0.9999915967092714 | 0.000816318426014595 | 599 | 597 | 308 | 289 |
| amplitude_spike | 0.99916172834366 | 0.9983388842978655 | 0.0008228440457944686 | 601 | 600 | 599 | 0 |
| silence | null | null | null | 0 | 0 | 0 | 0 |
| noise_only | null | null | null | 0 | 0 | 0 | 0 |
| pitch_error_700 | 2.60225008e-07 | null | null | 1050 | 1049 | 1048 | 0 |
| weak_fundamental_200 | 0.048587386215778 | null | null | 1200 | 1199 | 1198 | 0 |

El artefacto JSON incluye las consultas sin detector, referencia PCM independiente,
F0, cobertura, hashes, advertencias, cuantificación, rails y correspondencia de pulsos.
El nivel fuente cero produce 0.002965485410149 % en el WAV;
la extracción independiente sobre PCM reproduce ese pequeño residuo. No se fuerza a cero.

## Robustez y exclusiones observadas

- Ganancia x0.1 y x2: ambas cumplen cambio <=0.01 pp, sin pérdidas/adiciones
  en la correspondencia sintética. El resultado depende de cuantificación PCM.
- Amplitud x0.001: 1.299999983491074 %, RMS 2.6324333259210007 pasos PCM.
  Amplitud x0.0001: 4.47e-12 %, RMS 0.3049106779729928 pasos PCM;
  F0 99.99906535848625 Hz, 300 pulsos y 298 amplitudes. Esta cifra casi cero
  no recupera el shimmer de la fuente del 1 %. Ambos casos generan LOW_DIGITAL_AMPLITUDE
  y conservan el valor experimental, sin rechazo ni corrección automática.
- Clipping x5: 0.354800392777561 %, frente a referencia fuente 1 %.
  18306 muestras en rail en el archivo;
  9300 en la ventana. Advertencia de posible saturación. La extracción con pulsos
  impuestos da 0.35474371556400897 %, mostrando alteración de amplitudes aun sin detector.
- Ruido 40/30 dB cumple el objetivo fijado. A 20/10 dB el error frente a fuente
  es 0.13151540412776508/1.7810400623678588 pp, fuera del objetivo limpio;
  esos casos eran de caracterización, no nuevos xfail ni pruebas de exactitud aprobadas.
- Pulso perdido y desplazado en la señal: 595 amplitudes, dos interiores no extraídas;
  la cifra cercana al 1 % no significa que la anomalía se detecte clínicamente.
- Período anómalo: 308 amplitudes de 597 pulsos interiores candidatos para amplitud;
  289 no extraídas y shimmer 1.000807915135286 %. La cifra cercana a la fuente
  coexiste con tracking alterado y numerosas exclusiones. Avisos de períodos y
  amplitudes excluidas más fiabilidad no verificada.
- Pulso añadido a la señal: el detector no recupera todos los pulsos fuente;
  se obtiene 0.998495006763237 %, distinto de 1.088012162166951 % con pulsos impuestos.
- Pico de amplitud x2: dos razones exportadas superiores a 1.6; aviso emitido.
  Se conservan 599 amplitudes, pero se filtran comparaciones en el numerador.
  El valor bajo no demuestra ausencia de esa amplitud anómala.
- Silencio digital y ruido solo de esta prueba: null y cero amplitudes.
  No se generaliza a cualquier ruido ni se infiere automáticamente silencio.
- Tono 700 Hz seguido a 350 Hz y fuente débil 200 Hz seguida a 400 Hz dan shimmer
  bajo, con advertencia de fiabilidad no verificada. Un error de octava estable
  puede pasar desapercibido a los avisos de salto entre frames.

## Pulsos impuestos erróneos sobre el mismo WAV

Aquí se modifica únicamente PointProcess; el WAV original del 1 % permanece intacto.

| Error impuesto | Shimmer (%) | Pulsos | Períodos aceptados | Amplitudes |
|---|---:|---:|---:|---:|
| lost_pulse | 1.000832645663652 | 600 | 598 | 596 |
| added_pulse | 1.000824228373244 | 602 | 601 | 597 |
| shifted_pulse | 1.000832645663652 | 601 | 598 | 596 |

La extracción independiente sobre PCM concuerda. El shimmer puede permanecer
cercano al 1 % porque se excluyen zonas afectadas, sin probar integridad de pulsos.

## Límites de factores y períodos

Se prueban casos antes/en/después de 1.3 y 1.6, así como límites de períodos.
En los límites se respetan tiempos binary64 efectivos: no se añade un epsilon
para cambiar la aceptación del motor. Restar tiempos puede desplazar un cociente
nominalmente igual al límite al lado excluido. Se documentan los resultados exactos.

| Caso | Amplitudes nativas | Shimmer nativo (%) | Shimmer PCM independiente (%) |
|---|---:|---:|---:|
| period_factor_1.2999990000000001 | 3 | 4.145753677524712 | 4.145753677523282 |
| period_factor_1.3 | 1 | null | null |
| period_factor_1.300001 | 1 | null | null |
| amplitude_factor_1.5999990000000002 | — | 59.99990000000002 | null |
| amplitude_factor_1.6 | — | 60.00000000000001 | null |
| amplitude_factor_1.600001 | — | null | null |
| period_0.0013333233333333336 | 0 | null | null |
| period_0.0013333333333333335 | 0 | null | null |
| period_0.0013333433333333334 | 3 | 0.995767794363981 | 0.9957677943639187 |
| period_0.016666656666666665 | 3 | 0.995500346107675 | 0.9955003461078796 |
| period_0.016666666666666666 | 2 | 0.990765775946764 | 0.9907657759477987 |
| period_0.016666676666666668 | 0 | null | null |

Las consultas sobre AmplitudeTier con razón 1.6 aceptan el par (60 %);
con 1.600001 devuelven undefined/null. Estos porcentajes prueban la fórmula,
no representan umbrales clínicos ni grabaciones de voz.

## Errores de implementación corregidos y límites restantes

Las primeras pruebas detectaron que Down to TableOfReal falla si AmplitudeTier
está vacío. Se corrigió la exportación consultando el recuento antes de convertir,
sin cambiar el shimmer nativo ni convertir undefined en cero. También se corrigió
una llamada de prueba que usaba un argumento inexistente al generar un WAV corto.
Ningún fallo se ocultó como nuevo xfail y no se relajaron tolerancias.

Los cuatro xfail históricos permanecen byte a byte: modulación F0, jitter
alternante 2/5 % y jitter aleatorio 5 %. CI success no significa que esos objetivos
se cumplan. Una advertencia de deprecación Starlette/AnyIO permanece.
Los avisos de construcción/base Docker documentados antes siguen vigentes.

Validación limitada a estas señales sintéticas PCM16/44100 y Linux amd64.
La aceptación de WAV PCM24/32 o 48000 no equivale a validación acústica de todos
esos formatos; solo la inspección de cuantificación se prueba para 16/24/32 bits.
No validado en voz humana, micrófonos diferentes, ARM ni Windows. No se detecta
con fiabilidad la ganancia automática, compresión o saturación previa del micrófono.
Las exclusiones y la extracción RMS pueden ocultar o alterar variaciones de amplitud.
La auditoría sintética de correspondencia no certifica cierres glóticos fisiológicos.

Conclusión: cálculo matemático y extracción PCM verificados; recorrido acústico
caracterizado con estas señales. Fiabilidad de pulsos y condiciones de amplitud
limitan la interpretación. No se infiere estabilidad vocal ni patología.
