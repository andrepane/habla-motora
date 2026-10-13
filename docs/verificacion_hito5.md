# Hito 5: HNR experimental

Pendiente de completar con resultados exactos dentro de Docker. Los resultados
locales son preliminares y no sustituyen la ejecución dentro del contenedor.
Se usa la misma receta Dockerfile y Praat 6.4.27, sin modificar experimental_v1.

hnr_mean_db procede exclusivamente de Harmonicity: Get mean. Su semántica
nativa se conserva: no se valida ni reemplaza por una media aritmética simple
de frames. La cobertura se define separadamente mediante recuentos de frames
válidos con centro dentro del intervalo. Se elimina la comparación con la media
aritmética de los frames. undefined -> null; -200 es marcador excluido, conservado
solo en el valor bruto de auditoría. Cero y negativos finitos son resultados válidos.

Las tolerancias previas completas están en docs/protocolo_v1.md. Se mantiene
el objetivo de tono limpio exacto: cobertura 100 % y media >=40 dB. La prueba
local encontró dos incumplimientos a 100 Hz, 48000 y 44100 Hz de muestreo:
33.739301862443725 y 33.248476204039925 dB respectivamente. Se registran como
xfail estrictos, no se cambia el criterio ni se modifica la configuración.
Los cuatro xfail históricos permanecen intactos.

No se implementa CPP/CPPS ni se atribuye validación clínica o en voz humana.
