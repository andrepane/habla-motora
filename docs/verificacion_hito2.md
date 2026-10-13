# Verificación del hito 2: F0

Módulo pitch_v1, esquema pitch_output_v1, advertencias pitch_warnings_v1.
Configuración experimental_v1 conservada byte a byte; scope solo histórico.

Se utiliza Praat 6.4.27, To Pitch (raw cross-correlation), sobre todo el WAV.
Las consultas Get mean y Get standard deviation, en Hertz, se realizan en la
ventana central de 3 s de la emisión seleccionada. No son estadísticas propias
calculadas en Python. Se conserva el tratamiento de bordes de las consultas.
Se exportan únicamente los frames con centros dentro del intervalo inclusivo.
F0 undefined se exporta como null, nunca cero. No se rellenan huecos ni se
corrigen octavas. La cobertura es un recuento discreto, no duración fonada.

Pruebas: señales PCM16 mono de 6 s a 44.100 Hz, amplitud 0,3; ruido uniforme
con semilla 20261013. Se analiza 1,5–4,5 s, con 600 frames disponibles.
Modulación f(t)=200+20*sin(2*pi*2*t) Hz, con fase integrada continuamente.
Tono–silencio–tono: tono de 200 Hz salvo silencio entre 2,5 y 3,5 s.

El objetivo exploratorio de error máximo por frame <=0,5 Hz en la modulación
no se cumple; se conserva como xfail estricta. No es una validación positiva.
Los casos de ruido, fuera de rango y fundamental débil son caracterización:
que su prueba pase no significa que el tracking detecte la frecuencia correcta.

Pendiente en este commit: resultados finales dentro del Docker verificado.
