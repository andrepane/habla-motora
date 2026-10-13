# Hito 5: HNR experimental — verificación dentro de Docker

Fecha: 13/10/2026. GitHub Actions, Ubuntu 24.04, Linux amd64.
Python 3.12.14. Motor observado: Praat 6.4.27 (January 27 2025).

## Evidencia

- Commit de implementación probado: `dbd47a6e7559886580f751f4c8f1cc4a7c7fc115`.
- [Ejecución y registros](https://github.com/andrepane/habla-motora/actions/runs/38431180676): success.
- Job `115413442787`.
- [Artefacto JSON de pruebas y API](https://github.com/andrepane/habla-motora/actions/runs/38431180676/artifacts/11830899173).
- Misma receta Dockerfile y dependencias verificadas anteriormente, reconstruida
  con el código de HNR. Imagen habla-motora:smoke-v1.
- ID de imagen: `sha256:e8d7efe3085833a826ef0b0022cb21934bbad979d2ef7445d3ff30b3b18f2c85`.
- Pytest durante la construcción: `200 passed, 6 xfailed, 1 warning in 323.02s (0:05:23)`.
- Suite nuevamente dentro del contenedor: `200 passed, 6 xfailed, 1 warning in 322.50s (0:05:22)`.
- Total 206 casos: 200 passed, seis xfail. De las 54 pruebas nuevas de HNR,
  52 pasan y dos registran objetivos experimentales incumplidos.
- Los cuatro xfail históricos permanecen byte a byte.
- /health, /smoke-test, /pitch, /jitter, /shimmer y /hnr: HTTP 200.
- /smoke-test mantiene exactamente 2.0 s. /hnr devuelve
  20.14544355206075 dB para tono+ruido a 20 dB, semilla 5000.

El [primer intento](https://github.com/andrepane/habla-motora/actions/runs/38428854469)
alcanzó el límite global de 15 minutos durante el informe de HNR. La construcción
había obtenido `200 passed, 6 xfailed, 1 warning in 323.36s` y la segunda suite
`200 passed, 6 xfailed, 1 warning in 324.45s`; las comprobaciones HTTP quedaron
pendientes. Se corrigió únicamente timeout-minutes de 15 a 30 en el workflow,
sin cambiar código de análisis, señales, configuración ni criterios. Se repitió
el flujo completo para cerrar informe, API y artefactos.

Docker se ejecutó en GitHub Actions porque el entorno local no tiene Docker.
No se presentan las observaciones preliminares locales como evidencia de contenedor.

## Corrección obligatoria de semántica

hnr_mean_db procede EXCLUSIVAMENTE de Harmonicity: Get mean. Se conserva su
semántica temporal nativa, tal como define la documentación oficial. Los frames
exportados son auditoría: NO se calcula ni se exige una media aritmética simple
de esos valores para validar, sustituir o corregir la consulta oficial.
Cobertura y mecanismo de cálculo de la media son dos cosas distintas.

La comparación de integración se hace mediante otro script Praat que ejecuta
la misma consulta Get mean. Los objetos controlados se usan con referencias
inequívocas constantes; los objetos no constantes son caracterización de la
consulta nativa, sin inventar una agregación alternativa.
La etiqueta congelada mean_db_valid_frames se conserva como descripción inicial,
no como autorización para sustituir la consulta por una estadística propia.

Referencia: [Harmonicity: Get mean](https://praat.org/manual/Harmonicity__Get_mean___.html).

## Configuración y procedencia

experimental_v1 intacta; SHA-256:
`94b976f9c3e1f21d965df9ce547422953c6d780df64988cf2562cc8594520729`.
Versiones separadas: hnr_v1, hnr_output_v1, hnr_warnings_v1.
Script HNR: `f5ce3b522e31b47f16a802af70307ef13e17e7d7efcdf997139701e0008c17b1`.
Cada resultado registra motor exacto, versión protocolo/configuración, hash de
configuración/WAV/script HNR y script auxiliar de duración. scope es histórico.
Dockerfile, dependencias, módulos y pruebas históricos permanecen intactos.

Sound completo -> To Harmonicity (cc): 0.01, 75, 0.1, 4.5 -> Get mean: inicio, fin.
Ventana central de tres segundos; aquí 1.5-4.5 s. Sin normalización o filtrado
en el backend. No ejecuta Pitch ni PointProcess; no aplica el techo de 600 Hz
de F0. Los avisos de amplitud reutilizan funciones de inspección PCM sin ejecutar
los módulos de pitch, jitter o shimmer.

HNR en dB, a partir del estimador de periodicidad nativo. El motor transforma
la fuerza r mediante 10*log10(r/(1-r)) y tiene límites numéricos +/-150 dB.
Estos límites no prueban exactitud acústica a esos niveles. Get mean undefined
-> null/praat_undefined; valores finitos negativos y cero se conservan.
No se implementa CPP/CPPS ni se inicia el siguiente hito.

## Auditoría y cobertura

Get number of frames, Get time from frame number, Get value in frame, sin
interpolación. Por frame: frame_index, time_s, praat_raw_hnr_db, hnr_db, valid,
reason y numerical_limit. Se registra además rejilla global (número de frames,
paso y primer centro), recuentos y cobertura. El objeto no exporta un certificado
independiente de periodicidad ni el período elegido por frame en esta auditoría.

- -200 es marcador non-sounding de Praat 6.4.27, NO una medición de -200 dB.
  Se conserva únicamente en el campo bruto, con hnr_db=null y motivo explícito.
- undefined de un frame -> null; no se reemplaza por cero.
- Cobertura = 100 * frames válidos / frames cuyo centro cae inclusivamente
  dentro del intervalo. Se conserva el número real de frames, no duración/0.01.
- Sin frames: cobertura null. Con frames pero ninguno válido: cobertura 0 %.
- Media oficial: exclusivamente Get mean, sin inferirla a partir de cobertura.
- Cobertura no certifica voz, ausencia de ruido ni tracking correcto.
- f0_coverage y accepted_cycles permanecen null/not_computed_in_hnr_module:
  no se calculan para filtrar HNR ni se confunden con su cobertura.

Las señales de 6 s de estas pruebas tienen 301 centros HNR en [1.5,4.5],
incluidos los extremos de la rejilla. Cobertura 100 % equivale aquí a 301/301,
no a un denominador teórico de 300.

## Tolerancias previas, conservadas

Todas las diferencias de HNR se expresan en dB:
- Objetos con referencia temporal exacta constante: error <=0.00000001 dB.
  Se incluyen valores negativos, cero, límites numéricos, intervalos desplazados,
  exclusiones con resto constante y todos los frames marcados como no válidos.
- Integración frente al script separado con Get mean: error de media y por
  frame <=0.000001 dB, mismos índices y estados de validez.
- Recuentos/cobertura: exactos según la definición operacional; no se aproxima
  el denominador ni se exige igualdad con el mecanismo de la media nativa.
- Ganancia x0.1/x2 sobre tono+ruido 20 dB: cambio <=0.1 dB, mismos estados válidos.
- Tono limpio de período exacto: cobertura 100 % y media >=40 dB.
- Ruido: media entre 20 realizaciones estrictamente creciente para SNR
  0 -> 10 -> 20 -> 30 -> 40 dB. Semillas 5000 a 5019, ninguna descartada.
- Condiciones difíciles: caracterización; no se exige HNR=SNR.

No se modifica ningún criterio después de observar resultados.

## Señales y referencia independiente

Archivos de seis segundos, PCM16 mono; generación habitual a 48000 Hz y
comprobaciones de tono también a 44100 Hz. Fase en centros de muestras.
Cuando fs/f es entero se repite un bloque exacto de muestras periódicas;
la cuantificación también se repite, sin ruido aleatorio de cuantificación.
Amplitud inicial de seno 0.2. Ruido gaussiano con semilla fija y RMS conocido.
El generador escala conjuntamente componentes para asegurar margen de amplitud
antes de aplicar las ganancias explícitas; este factor queda registrado y no
altera el SNR. El backend no normaliza los WAV recibidos.

Se registran SNR nominal, SNR generado a partir de las potencias independientes
y SNR de residual PCM frente a la componente periódica cuantificada. Este
residual no es una verdad de HNR: puede ser periódico, como la cuantificación.

La referencia independiente usa Pearson a un retardo conocido de 240 muestras
(200 Hz a 48000), segmentos de 60 ms, sin búsqueda de máximos ni resultados
Praat como entrada. Su rejilla propia es distinta de la auditoría nativa;
caracteriza un estimador al período verdadero, no replica el algoritmo Praat.
Bajo hipótesis estacionarias y ruido independiente, r(T0) aproxima Ps/(Ps+Pn).
Ventanas finitas, búsqueda de máximos, interpolación, espectro y cuantificación
impiden exigir equivalencia exacta entre SNR y HNR.

## Resultados exactos de condiciones individuales

| Caso | HNR medio nativo (dB) | Cobertura (%) | Válidos | Excluidos |
|---|---:|---:|---:|---:|
| clean_100Hz_48000 | 33.739301862443725 | 100 | 301 | 0 |
| clean_200Hz_48000 | 45.394110605899954 | 100 | 301 | 0 |
| clean_400Hz_48000 | 59.042268248064744 | 100 | 301 | 0 |
| clean_100Hz_44100 | 33.248476204039925 | 100 | 301 | 0 |
| clean_200Hz_44100 | 40.466951924781526 | 100 | 301 | 0 |
| clean_400Hz_44100 | 45.39295446580539 | 100 | 301 | 0 |
| silence | null | 0 | 0 | 301 |
| noise_only | -9.283131586198612 | 100 | 301 | 0 |
| tone_silence_tone | 44.23799574548981 | 67.10963455149502 | 202 | 99 |
| gain_0.1 | 20.14515861313347 | 100 | 301 | 0 |
| gain_2 | 20.1454460549853 | 100 | 301 | 0 |
| gain_baseline_20dB | 20.14544355206075 | 100 | 301 | 0 |
| low_amplitude_0.001 | 54.92186020085814 | 100 | 301 | 0 |
| low_amplitude_0.0001 | 68.94795961607069 | 100 | 301 | 0 |
| clipping_gain_10 | 48.11510757708116 | 100 | 301 | 0 |
| weak_center_without_loud_context | 45.41578917279338 | 100 | 301 | 0 |
| weak_center_with_loud_context | null | 0 | 0 | 301 |
| harmonics | 48.56111962803428 | 100 | 301 | 0 |
| weak_fundamental | 48.81668503774521 | 100 | 301 | 0 |
| inharmonic_317Hz | 11.345960839511875 | 100 | 301 | 0 |
| frequency_50Hz | null | 0 | 0 | 301 |
| frequency_74Hz | null | 0 | 0 | 301 |
| frequency_76Hz | 17.56837233523638 | 100 | 301 | 0 |
| frequency_700Hz | 48.778100288061026 | 100 | 301 | 0 |

## Tono + ruido: 20 realizaciones por nivel

Las medias y DT siguientes se calculan ENTRE realizaciones, cada una con su
propio Get mean nativo. No son una agregación alternativa de frames del archivo.

| SNR nominal (dB) | Media HNR (dB) | DT entre realizaciones (dB) | Mínimo HNR | Máximo HNR | Cobertura mínima/máxima (%) | Referencia de retardo conocido, semilla 5000 (dB) |
|---|---:|---:|---:|---:|---:|---:|
| 0 | 0.9899652077856427 | 0.037174350919041574 | 0.9304410660244613 | 1.0572320417391385 | 100/100 | -0.02039023683796522 |
| 10 | 10.38835575896874 | 0.02515238736420064 | 10.347848256869625 | 10.447708888499966 | 100/100 | 9.983356467758316 |
| 20 | 20.15992090616159 | 0.013230009773728308 | 20.13282739832085 | 20.179625983724133 | 100/100 | 19.981128996070147 |
| 30 | 31.7182950012029 | 0.02017687708435573 | 31.675928065076896 | 31.74934420678648 | 100/100 | 29.980081299005295 |
| 40 | 41.47615731377019 | 0.026440636043500085 | 41.429509456902046 | 41.53395545040967 | 100/100 | 39.97951576821109 |

Se cumple la tendencia creciente con todas las realizaciones. No se interpreta
la diferencia frente al SNR nominal como fallo de integración ni se calibra
una corrección para forzar HNR=SNR. La referencia independiente permite mostrar
la diferencia de estimadores, no validar clínicamente el HNR del motor.

Resultados por semilla, sin selección posterior:

| Semilla | HNR SNR 0 | HNR SNR 10 | HNR SNR 20 | HNR SNR 30 | HNR SNR 40 |
|---|---:|---:|---:|---:|---:|
| 5000 | 0.9577943424453726 | 10.383308685843353 | 20.14544355206075 | 31.700997202714348 | 41.442256290936534 |
| 5001 | 0.9515518642976827 | 10.385099415871181 | 20.13282739832085 | 31.678796141306687 | 41.429509456902046 |
| 5002 | 0.9674905619194928 | 10.372649843338506 | 20.160202464524975 | 31.72478340804993 | 41.46915977841929 |
| 5003 | 1.0478915847138597 | 10.41999413524612 | 20.17262738979139 | 31.73492151522941 | 41.47225919741268 |
| 5004 | 1.0081843640010566 | 10.40634979108892 | 20.14505804281281 | 31.702404688044272 | 41.448935340515405 |
| 5005 | 0.9967607602225345 | 10.403588191142799 | 20.156531937436622 | 31.718753702464056 | 41.48669759929439 |
| 5006 | 0.9706605213026696 | 10.374152143239328 | 20.17771256654257 | 31.74934420678648 | 41.53395545040967 |
| 5007 | 1.0572320417391385 | 10.447708888499966 | 20.17476933284901 | 31.73929466551946 | 41.49773379366896 |
| 5008 | 0.9304410660244613 | 10.351920875761325 | 20.15383687320699 | 31.721377831046016 | 41.45058390416489 |
| 5009 | 1.0362720143271489 | 10.40804311698356 | 20.141994290945053 | 31.675928065076896 | 41.47556531390089 |
| 5010 | 1.0433349585607143 | 10.414813030595715 | 20.14908783935073 | 31.7000116353214 | 41.45121705592669 |
| 5011 | 0.9505752292692484 | 10.363472507756864 | 20.165013898536305 | 31.712141172146012 | 41.50280406847071 |
| 5012 | 0.9366026413492645 | 10.363862870988891 | 20.164700794232527 | 31.727027871738226 | 41.48299637374398 |
| 5013 | 1.0104731500412079 | 10.396565723955696 | 20.1673426926561 | 31.72019320086624 | 41.49141640415424 |
| 5014 | 0.9784215766084455 | 10.38100655097833 | 20.14870518571454 | 31.701088496018343 | 41.49867430080144 |
| 5015 | 1.0073971878438766 | 10.41042720971979 | 20.179625983724133 | 31.741039917669415 | 41.51518992778747 |
| 5016 | 0.9750752739907599 | 10.347848256869625 | 20.16287601799027 | 31.72522729764864 | 41.46629947771171 |
| 5017 | 0.9723008474789986 | 10.368459575570588 | 20.161242343635312 | 31.722778528367417 | 41.48100210904501 |
| 5018 | 0.9947242703596277 | 10.375634515004043 | 20.178541958727685 | 31.745146759636462 | 41.47917481236586 |
| 5019 | 1.0061198992172926 | 10.392209850920176 | 20.160277560173213 | 31.724643718408306 | 41.44771561977189 |

## Consulta sobre objetos controlados

Curvas constantes -150,-10,0,10,150 dB y límites de intervalo desplazados
superan error <=1e-8 dB. Curva completamente -200 devuelve undefined/null;
resto constante con marcadores excluidos conserva la constante. Se verifica la
semántica sin depender del detector y sin comparar con una media de frames.

| Valores impuestos (dB) | Inicio | Fin | Get mean nativo (dB) | Alcance |
|---|---:|---:|---:|---|
| [10, 10, 10, 10, 10] | 1.5 | 4.5 | 10 | constant-curve exact reference |
| [10, 10, 10, 10, 10] | 2.001 | 2.029 | 10 | constant-curve exact reference |
| [10, 10, 10, 10, 10] | 2.005 | 2.035 | 10 | constant-curve exact reference |
| [-200, -200, -200, -200, -200] | 1.5 | 4.5 | null | constant-curve exact reference |
| [-200, -200, -200, -200, -200] | 2.001 | 2.029 | null | constant-curve exact reference |
| [-200, -200, -200, -200, -200] | 2.005 | 2.035 | null | constant-curve exact reference |
| [10, -200, 10, -200, 10] | 1.5 | 4.5 | 10 | constant-curve exact reference |
| [10, -200, 10, -200, 10] | 2.001 | 2.029 | 10 | constant-curve exact reference |
| [10, -200, 10, -200, 10] | 2.005 | 2.035 | 10 | constant-curve exact reference |
| [0, 0, 0, 0, 0] | 1.5 | 4.5 | 0 | constant-curve exact reference |
| [0, 0, 0, 0, 0] | 2.001 | 2.029 | 0 | constant-curve exact reference |
| [0, 0, 0, 0, 0] | 2.005 | 2.035 | 0 | constant-curve exact reference |
| [-10, -10, -10, -10, -10] | 1.5 | 4.5 | -10 | constant-curve exact reference |
| [-10, -10, -10, -10, -10] | 2.001 | 2.029 | -10 | constant-curve exact reference |
| [-10, -10, -10, -10, -10] | 2.005 | 2.035 | -10 | constant-curve exact reference |
| [10, 20, 30, 40, 50] | 1.5 | 4.5 | 30 | native characterization; no frame arithmetic reference |
| [10, 20, 30, 40, 50] | 2.001 | 2.029 | 25 | native characterization; no frame arithmetic reference |
| [10, 20, 30, 40, 50] | 2.005 | 2.035 | 30 | native characterization; no frame arithmetic reference |

Los objetos no constantes se documentan sin asignar una fórmula de agregación
propia. La implementación incluye una prueba de integridad que confirma que un
valor nativo no se reemplaza aunque difiera de la media aritmética de los frames.

## Ganancia, clipping y amplitud baja

- Ganancia x0.1: cambio 0.0002849389272796543 dB.
- Ganancia x2: cambio 2.502924548508645e-06 dB.
  Ambas cumplen <=0.1 dB, mismos frames válidos.
- Amplitud x0.001: RMS 4.631414470763764
  pasos PCM; HNR 54.92186020085814 dB.
- Amplitud x0.0001: RMS 0.6708203932499369
  pasos PCM; HNR 68.94795961607069 dB.
  Ambos generan LOW_DIGITAL_AMPLITUDE. El HNR aumenta pese a la cuantificación
  extrema: esta repetición sintética no demuestra fidelidad a una voz grabada.
- Clipping x10: 192000 muestras en rail en el archivo,
  96000 en la ventana;
  HNR 48.11510757708116 dB y advertencia de saturación.
  HNR alto coexiste con distorsión deliberada, sin invalidación automática.

## Silencio, ruido, contexto global, frecuencias y armónicos

- Silencio digital: null y 0/301 válidos; no se devuelve -200 como medición.
- Ruido solo: valor finito negativo y 100 % de cobertura en esta realización.
  Cobertura no significa presencia de voz ni ausencia de ruido.
- Tono-silencio-tono: 202/301 válidos, 99 excluidos. Los bordes de análisis y
  soporte temporal del estimador impiden identificar esta cifra con una duración
  física exacta de silencio o con la segmentación de voz.
- Segmento central débil sin contexto fuerte: cobertura 100 %.
  Con fragmento fuerte externo a la ventana: cobertura 0 %, media null. El Sound
  completo y el umbral relativo al máximo global producen esta dependencia.
- 50/74 Hz: null en estas señales; 76 Hz: valor bajo respecto a otros tonos.
  El mínimo 75 Hz afecta al análisis. No se generaliza un null universal por frecuencia.
- 700 Hz: resultado finito; no se aplica el techo 600 Hz de F0.
- Armónicos enteros y fundamental débil conservan valores altos. Los armónicos
  periódicos no se tratan como ruido añadido.
- Componente de 317 Hz junto a 200 Hz: HNR inferior. Es no armónica respecto a
  200 Hz; no equivale a ruido aleatorio. Matemáticamente la combinación tiene
  periodicidad más larga (1 s), fuera de la búsqueda de esta configuración.

## Dos nuevos incumplimientos, sin relajación

1. Tono limpio 100 Hz/48000: 33.739301862443725 dB,
   cobertura 100 %, no cumple >=40 dB.
2. Tono limpio 100 Hz/44100: 33.248476204039925 dB,
   cobertura 100 %, no cumple >=40 dB.

Se conservan como xfail estrictos, limitados a AssertionError y a esos dos casos.
El código devuelve el valor nativo experimental; no lo corrige ni modifica v1.
La causa exacta de la diferencia respecto al objetivo no se establece con estas
pruebas; se observa dependencia del valor nativo con frecuencia y muestreo.
Una integración correcta no demuestra exactitud independiente absoluta del estimador.
Los cuatro xfail anteriores (modulación F0 y tres casos de jitter) permanecen
intactos. Success de CI no significa que los seis objetivos incumplidos se cumplan.

## Limitaciones

Estas pruebas no demuestran validación en voz humana, comparación de micrófonos,
utilidad clínica ni capacidad diagnóstica. Predomina PCM16/48000, con tonos
PCM16/44100. Aceptar otros formatos no prueba exactitud acústica en ellos.
No se certifica ARM/Windows ni se detectan con fiabilidad compresión, AGC,
saturación previa del micrófono o condiciones de grabación de un paciente.
HNR alto no certifica estabilidad vocal, y cobertura alta no certifica voz.
La media temporal oficial puede describir solo la parte admisible de un archivo,
y el máximo exterior al intervalo puede cambiar qué frames resultan admisibles.
Una advertencia de deprecación Starlette/AnyIO permanece; los límites de
reproducibilidad de la base Docker documentados anteriormente siguen vigentes.

Conclusión: integración nativa y auditoría verificadas, estimador caracterizado
con señales controladas. Dos objetivos de tono limpio incumplidos y conservados;
no existe validación clínica ni en voz humana. CPP/CPPS no implementados.
