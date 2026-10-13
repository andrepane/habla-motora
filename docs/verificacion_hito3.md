# Hito 3: jitter local experimental — verificación en Docker

Fecha: 13/10/2026. Entorno: GitHub Actions, Ubuntu 24.04, Linux amd64.
Python 3.12.14; motor observado: `Praat 6.4.27 (January 27 2025)`.

## Evidencia de ejecución

- Commit de implementación probado: `3e0a5664c4d3b1a83049121d725fe830bd2f4c41`.
- [Ejecución y registros](https://github.com/andrepane/habla-motora/actions/runs/38418337524): success.
- Job `115368651179`.
- [JSON de señales y API](https://github.com/andrepane/habla-motora/actions/runs/38418337524/artifacts/11826075140).
- Misma receta Dockerfile y dependencias de los hitos anteriores, reconstruida
  con el módulo nuevo. Imagen `habla-motora:smoke-v1`.
- ID de imagen: `sha256:ecf2c51146a33db4f515a31cd5d359e083782a961a84c0199dfbaa0e7410e446`.
- Construcción: `76 passed, 4 xfailed, 1 warning in 45.51s`.
- Suite nuevamente dentro del contenedor:
  `76 passed, 4 xfailed, 1 warning in 44.91s`.
- Total: 80 casos; 76 superados y cuatro incumplimientos registrados como xfail.
- /health, /smoke-test, /pitch y /jitter: HTTP 200.
- /smoke-test mantiene 2.0 s; /jitter devuelve 0.499833315122997 % para el caso
  alternante nominal 0.5 %, con procedencia y estado experimental.

## Configuración y método

experimental_v1 conservada byte a byte:
`94b976f9c3e1f21d965df9ce547422953c6d780df64988cf2562cc8594520729`.
scope sigue siendo información histórica, no estado de implementación.
Versiones separadas: jitter_v1, jitter_output_v1, jitter_warnings_v1.
Hash del script jitter:
`9340ddd8f25dd9bcfdfe044d2b0256386db38d599d82ee22e36b9f5df7ef9cb4`.
Se conservan hash WAV, configuración, script principal y scripts auxiliares
pitch/duración. Las advertencias heredadas de F0 conservan pitch_warnings_v1.

Recorrido exacto:
Sound completo -> Pitch raw cross-correlation con todos los parámetros v1 ->
selección Sound + Pitch -> To PointProcess (cc) -> Get jitter (local).
Límites de período: 0.8/600 y 1.25/75 s. Factor máximo: 1.3.
Se consulta la ventana central de 3 s; porcentaje = proporción de Praat * 100.

Un valor finito se conserva sin reglas paralelas por pocos pulsos.
undefined -> null/praat_undefined. Cero puede ser válido.
Solo se rechazan salidas corruptas/no finitas, orden inválido de pulsos,
incoherencias de recuentos o integridad numérica, no por interpretación clínica.

Todos los valores llevan experimental_pulse_reliability_unverified y una
advertencia de fiabilidad de pulsos no verificada. Se heredan avisos F0, se
avisa de períodos excluidos, undefined y muestras en rail digital del WAV
completo. El rail digital identifica posible saturación, no su origen.

## Recuentos y exportación

- Se exportan todos los pulsos del Sound, incluidos los exteriores a la ventana
  para conservar contexto.
- Se exportan períodos candidatos completos entre pulsos consecutivos interiores.
- Pulsos interiores: recuento directo por límites inclusivos.
- Períodos candidatos: máximo(0, pulsos interiores - 1).
- Períodos aceptados: exclusivamente Get number of periods con los mismos
  límites y parámetros; no equivale a cierres glóticos fisiológicos confirmados.
- accepted_cycles se identifica explícitamente con esa consulta de Praat.
- Pares utilizados: null/not_implemented. No se usa una consulta directa para
  ellos y reconstruir ese contador en producción añadiría lógica innecesaria.
  Por ello no se afirma cuántas comparaciones se excluyeron: el aviso cuantifica
  exclusiones de períodos, no las de pares.
- No se interpolan huecos ni se corrigen octavas.

## Referencias independientes y tolerancias

La fórmula de referencia solo existe en tests sobre tiempos fuente conocidos.
Se comprueba con seis conjuntos pequeños resueltos analíticamente, incluyendo
jitter cero, dos períodos diferentes, períodos excluidos y resultados undefined.
También se comprueban niveles alternantes, tres anomalías y secuencias aleatorias.

Tres recorridos separados:
1. Otro script sobre el mismo WAV/motor: integración, no exactitud independiente.
2. Tiempos conocidos -> fórmula matemática independiente y consulta Praat sobre
   PointProcess suministrado: cálculo/exclusiones sin detector acústico.
3. WAV -> pulsos encontrados -> comparación con tiempos conocidos: detección.

La máxima diferencia matemática/Praat sin detector en los cinco niveles
alternantes fue 1.8981934782609104e-12 puntos porcentuales, inferior a 1e-8.
No se usan valores del detector como referencia de verdad.

Criterios conservados:
- Integración: 1e-6*max(1,abs(referencia)) pp.
- Cálculo sobre tiempos conocidos: 1e-8 pp.
- Jitter cero en WAV: <=0.05 %.
- WAV limpio: error <=max(0.05 pp,10 % del valor de referencia).
- Ganancia constante sin saturación: cambio <=0.01 pp, sin pérdida/adición de
  pulsos según el emparejamiento sintético establecido.
No se relaja ningún criterio para conseguir que pase.

## Construcción de las señales

PCM16 mono/44.100 Hz, 6 s, ventana 1.5–4.5 s.
Pulsos gaussianos idénticos, sigma 0.2 ms, amplitud 0.3, tiempos fuente
posiblemente fraccionales respecto a la muestra.
Períodos alternantes T0*(1±epsilon), T0=1/200 s; epsilon=porcentaje_nominal/200.
El jitter de referencia se calcula sobre los tiempos completos de la ventana,
por eso puede diferir ligeramente del nominal por bordes y aritmética de tiempos.

También hay secuencias aleatorias de semilla 731, perturbación anómala de un
período x1.5, pulso eliminado o añadido, ganancia, amplitud baja, ruido
gaussiano semilla 20261013 y saturación. El SNR se calcula con RMS antes
de ganancia. El ruido y los casos difíciles son caracterización, no aceptación
universal de esas condiciones de grabación.

## Resultados exactos en Docker

Error expresado en puntos porcentuales (pp), no error relativo.

| Caso | Jitter obtenido (%) | Referencia fuente (%) | Error absoluto (pp) | Pulsos interiores | Períodos candidatos | Aceptados por Praat |
|---|---:|---:|---:|---:|---:|---:|
| jitter_0 | 0 | 1.9130434782609104e-12 | 1.9130434782609104e-12 | 600 | 599 | 599 |
| jitter_0.5 | 0.499833315122997 | 0.49999999999953404 | 0.00016668487653703767 | 600 | 599 | 599 |
| jitter_1 | 1.000079042026331 | 0.9999916528226959 | 0.00008738920363515756 | 600 | 599 | 599 |
| jitter_2 | 7e-15 | 2.00003338954104 | 2.000033389541033 | 300 | 299 | 299 |
| jitter_5 | 7e-15 | 5.000208689841687 | 5.0002086898416795 | 300 | 299 | 299 |
| long_period | 0.573757203827363 | 0.9999916248591373 | 0.42623442103177434 | 599 | 598 | 597 |
| lost_pulse | 1.000079069994705 | 0.9999916248591944 | 0.00008744513551073307 | 599 | 598 | 597 |
| added_pulse | 1.010119896128623 | 0.9999832637013676 | 0.010136632427255488 | 600 | 599 | 599 |
| gain_0.1 | 1.001991804565318 | 0.9999916528226959 | 0.002000151742622136 | 600 | 599 | 599 |
| gain_2 | 1.0001884590662549 | 0.9999916528226959 | 0.00019680624355900012 | 600 | 599 | 599 |
| amplitude_0.001 | 3.7e-14 | 0.9999916528226959 | 0.9999916528226589 | 300 | 299 | 299 |
| amplitude_0.0001 | 3.7e-14 | 0.9999916528226959 | 0.9999916528226589 | 300 | 299 | 299 |
| saturation_gain_5 | 1.00226786758155 | 0.9999916528226959 | 0.0022762147588540893 | 600 | 599 | 599 |
| random_jitter_1 | 1.001341126753404 | 1.0013396859316115 | 0.000001440821792542124 | 600 | 599 | 599 |
| random_jitter_2 | 2.001972715709418 | 2.001955294316504 | 0.000017421392913608003 | 600 | 599 | 599 |
| random_jitter_5 | 4.453493464066814 | 4.9949737457527705 | 0.5414802816859563 | 552 | 551 | 551 |
| noise_40dB | 1.000326176196051 | 0.9999916528226959 | 0.00033452337335504456 | 600 | 599 | 599 |
| noise_30dB | 1.000793103552457 | 0.9999916528226959 | 0.0008014507297612328 | 600 | 599 | 599 |
| noise_20dB | 0.9994767513450161 | 0.9999916528226959 | 0.0005149014776797411 | 600 | 599 | 599 |
| noise_10dB | 1.037777349685459 | 0.9999916528226959 | 0.03778569686276312 | 601 | 600 | 600 |
| silence | null | — | — | 0 | 0 | 0 |
| noise_only | null | — | — | 0 | 0 | 0 |
| pitch_error_700 | 5.862515e-8 | — | — | 1050 | 1049 | 1049 |
| weak_fundamental_200 | 0.012710051004735 | — | — | 1200 | 1199 | 1199 |

El JSON del artefacto incluye las versiones/hashes por caso, advertencias,
F0, cobertura y auditoría del emparejamiento de pulsos.

## Cuatro incumplimientos conservados

- xfail anterior de modulación F0: intacto, no relajado.
- Jitter alternante 2 %: estima 7e-15 %, error 2.000033389541033 pp;
  detecta 300 pulsos en lugar de aproximadamente 600.
- Jitter alternante 5 %: estima 7e-15 %, error 5.0002086898416795 pp;
  detecta 300 pulsos.
- Aleatorio nominal 5 %: referencia 4.9949737457527705 %, resultado
  4.453493464066814 %, error 0.5414802816859563 pp, superior a la tolerancia
  0.49949737457527705 pp; detecta 552 pulsos.
Estos tres xfail de jitter son estrictos y limitados a AssertionError.

Una secuencia perfectamente alternante puede tener periodicidad acústica cada
dos pulsos fuente. Su frecuencia acústica no es inequívocamente la tasa de esos
pulsos: aun así, el recorrido no recupera el jitter de los ciclos fuente y falla
el objetivo aprobado. El caso aleatorio evita esa repetición exacta y también
muestra limitaciones a perturbación alta.

## Robustez y problemas observados

- Período anómalo: resultado 0.573757203827363 %, frente a referencia filtrada
  0.9999916248591373 %. 599 pulsos, 598 candidatos, 597 aceptados. Hay
  alteración importante del tracking; el valor finito no se sobreescribe.
- Pulso perdido: 599 pulsos y 597 períodos aceptados; se conserva un jitter
  cercano al basal tras las exclusiones. No significa ausencia de la anomalía.
- Pulso añadido: 600 detectados, 599 aceptados; el detector no recupera el pulso
  fuente adicional en este caso. El recuento aceptado no prueba integridad.
- Ganancias x0.1 y x2 cumplen el criterio de cambio <=0.01 pp; emparejamiento
  sin pérdidas/adiciones en los márgenes de evaluación.
- Amplitudes x0.001 y x0.0001 producen jitter 3.7e-14 % en una fuente cercana
  al 1 %: F0 aproximadamente 100 Hz, 300 pulsos y 299 períodos aceptados.
  No se confunde ese valor con una medición fisiológica fiable.
- Saturación x5: 18,321 muestras del WAV en rail digital; advertencia emitida.
  El error pequeño de este único caso no demuestra inmunidad a saturación.
- Ruido a 40,30,20,10 dB: errores 0.00033452337335504456,
  0.0008014507297612328, 0.0005149014776797411 y 0.03778569686276312 pp.
  El caso 10 dB cuenta 601 pulsos en la ventana; el emparejamiento se evalúa
  con margen, de modo que no deben confundirse recuentos y correspondencias.
- Silencio digital y ruido solo: ningún pulso, jitter null. No demuestra que
  todo ruido vaya a devolver null.
- Tono de 700 Hz: pitch 350 Hz y jitter muy pequeño; fundamental débil de
  200 Hz: pitch aproximadamente 400 Hz y jitter 0.012710051004735 %.
  El error de pitch estable puede pasar desapercibido a las alertas de saltos.

## Limitaciones

La asociación de pulsos usa una puerta fija de un cuarto del período nominal
y permite un desplazamiento global; no utiliza deformación temporal. En casos
alterados los conteos de no emparejados son dependientes de esa regla, no una
identificación fisiológica definitiva. No hay confianza por pulso independiente
exportada por PointProcess ni certificado de fiabilidad derivado de coverage.

Resultados limitados a estas formas sintéticas, PCM16/44.100 Hz y Linux amd64.
No validado en voz humana, micrófonos variados, ARM ni Windows.
Permanece una advertencia de deprecación Starlette/AnyIO y los avisos de
construcción documentados en los hitos anteriores.

No se han implementado shimmer, HNR ni CPP/CPPS. No se ha iniciado el hito 4.
