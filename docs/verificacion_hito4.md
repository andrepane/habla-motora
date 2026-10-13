# Hito 4: shimmer local experimental

Pendiente de completar con resultados exactos de Docker; las observaciones locales
no sustituyen esa verificación. Se usa el mismo Dockerfile y dependencias fijadas
para Praat 6.4.27. No se modifica experimental_v1 ni los cuatro xfail anteriores.

Las tolerancias completas y congeladas están en docs/protocolo_v1.md:
error absoluto en puntos porcentuales, con referencia en porcentaje.
- Integración: error_pp <= 0.000001 * max(1.0, abs(S_ref)).
- Extracción con pulsos impuestos limpia: error_pp <= max(0.01, 0.01 * abs(S_ref)).
- Recorrido completo limpio alternante/aleatorio: error_pp <= max(0.05, 0.10 * abs(S_ref)).
No se relajan después de observar resultados.

Se verifican por separado fórmula matemática, AmplitudeTier conocido,
Sound + PointProcess impuesto y recorrido completo. La referencia independiente
sobre PCM no usa amplitudes extraídas por Praat como verdad.

Todo valor finito se conserva como experimental con fiabilidad de pulsos no
verificada; undefined -> null. Se exportan amplitudes RMS Hann mediante
To AmplitudeTier (period). Pares utilizados: null/not_implemented.
Los períodos aceptados no representan ciclos/amplitudes aceptados para shimmer.
No existe validación en voz humana ni interpretación clínica automatizada.
