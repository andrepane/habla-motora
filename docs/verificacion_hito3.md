# Hito 3: jitter local experimental

Pendiente de completar con resultados exactos de Docker.

Se conservan Sound completo, pitch raw cross-correlation v1, Sound & Pitch:
To PointProcess (cc), Get jitter (local), límites 0.8/600 y 1.25/75 s y factor
1.3. Ventana central de 3 s; porcentaje = proporción de Praat * 100.

Valores finitos se conservan; undefined -> null. Solo se rechazan salidas
corruptas/no finitas, orden de pulsos inválido o recuentos incoherentes.
Jitter tiene siempre estado experimental_pulse_reliability_unverified.
Se exportan pulsos con contexto y períodos candidatos, no una etiqueta
individual de aceptación inventada. Get number of periods da el recuento
aceptado. Pares utilizados: null/not_implemented: no hay consulta directa
utilizada y reconstruirla en producción añadiría lógica sustancial innecesaria.

La fórmula independiente solo existe en pruebas sobre tiempos conocidos.
Sus reglas se verifican con casos pequeños resueltos analíticamente y con
PointProcess conocido sin detector. La comparación WAV contra otro script del
mismo motor solo demuestra integración.

Tolerancias congeladas: integración 1e-6*max(1,abs(referencia)) puntos porcentuales;
matemática 1e-8 pp; jitter cero <=0.05%; limpio max(0.05 pp,10% referencia);
ganancia constante sin saturación cambio <=0.01 pp y sin pulsos perdidos/añadidos.
No se relajan por los incumplimientos; se registran xfail estrictos.

Señales: pulsos gaussianos idénticos, sigma 0.2 ms, amplitud 0.3,
PCM16/44.100 Hz, 6 s, análisis 1.5–4.5 s. Períodos alternantes y aleatorios
con tiempos fuente conocidos. SNR calculado sobre RMS antes de ganancia;
ruido gaussiano de semilla fija. Muestras en rail digital: aviso de posible
saturación, no diagnóstico de origen. Emparejamiento de pulsos con contexto,
puerta fija de un cuarto del período nominal y un desplazamiento global;
no hay deformación temporal para ocultar pérdidas. Emparejamiento es auditoría
sintética, no garantía de correspondencia fisiológica en voz humana.

Una señal alternante puede tener periodicidad acústica cada dos pulsos fuente;
no debe suponerse que la F0 acústica es inequívocamente la tasa de pulsos.
