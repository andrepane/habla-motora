# Selección revisada v2: elegibilidad antes del coste

La congelación v1 (`89d2bb645fcb3d62e9a217e3ecf2357aed096016`) omitía el filtro de aceptación y eligió `current_cc__0`. Se sustituye explícitamente antes del bloqueado por un defecto de política de selección. No se han repetido WAV ni extracciones. No se han consultado resultados bloqueados ni WAV humanos.

La v1 se conserva byte a byte en `research/prosody/freeze_v1.json` y en su commit. `freeze_v2.json` contiene la decisión revisada y `freeze.json` es su copia activa. El informe y los resultados de desarrollo v1 permanecen intactos. El manifiesto histórico de hashes v1 debe verificarse resolviendo su antigua ruta `freeze.json` contra `freeze_v1.json`.

## Política

Cada candidata se evalúa con la función `assess` exactamente congelada, los mismos 14 criterios y los mismos umbrales. Solo las que cumplen todos los casos son elegibles. Después se reutilizan los costes persistidos y el desempate original: candidatas a ≤0,001 del menor coste elegible; menor mediana de error core, menor contexto y nombre de configuración. No se recalcula ni modifica el coste. El selector histórico se protege para impedir que vuelva a sobrescribir la congelación con una elección solo por coste.

## Las 14 configuraciones

| Configuración | Coste original | Elegible | Criterios fallidos (casos / total) |
|---|---:|---|---|
| current_cc__0 | 0.04628252 | No | C 12/168; O 1/72; M 13/168; P 13/168; Q10 13/168; Q90 13/168; R 12/168; S 12/168 |
| filtered_800_03__0 | 0.06994822 | Sí | Ninguno |
| filtered_800_09__0 | 0.07248308 | Sí | Ninguno |
| current_cc__250 | 0.11188638 | No | C 12/168; O 1/72; M 13/168; P 13/168; Q10 13/168; Q90 13/168; R 12/168; S 12/168 |
| wide_cc__250 | 0.11190180 | Sí | Ninguno |
| filtered_800_03__250 | 0.15026170 | Sí | Ninguno |
| filtered_800_09__250 | 0.15276170 | Sí | Ninguno |
| wide_ac__250 | 0.16697494 | Sí | Ninguno |
| wide_cc__0 | 0.22018083 | Sí | Ninguno |
| wide_ac__0 | 0.27787171 | Sí | Ninguno |
| filtered_1200_03__0 | 0.45319548 | Sí | Ninguno |
| filtered_1200_09__0 | 0.45577909 | Sí | Ninguno |
| filtered_1200_03__250 | 0.53091941 | Sí | Ninguno |
| filtered_1200_09__250 | 0.53346749 | Sí | Ninguno |

C: cobertura core ≥98%. O: cero frames con error de octava en constantes/duración. M: mediana core ≤20 cents. P: P95 core ≤50 cents. Q10/Q90: error ≤max(1 Hz, 2%). R: soporte de publicación y error del rango ≤0,2 ST. S: soporte de publicación y error de pendiente ≤max(0,05 ST/s, 5%). Los otros seis criterios (ruido, no periódicos y huecos) pasan en las 14 configuraciones.

Los JSON individuales conservan todos los criterios aprobados y fallidos. Cada fallo incluye identificador, valor observado y la receta completa (familia, frecuencia, muestreo y PCM). Los umbrales exactos están en `decision.json` y las dos congelaciones.

## Casos que excluyen a current_cc

Ambos contextos fallan los mismos ocho criterios. A 55 y 75 Hz faltan los 12 casos (dos frecuencias × dos muestreos × tres PCM): cobertura core 0%, F0/cuántiles indefinidos y soporte insuficiente de rango y pendiente. Un caso adicional de 600 Hz falla error core, cuantiles y octava.

- `current_cc__0`: `development-008-44100-16`, 600 Hz, 44100 Hz de muestreo, PCM 16 bits: 795 frames con error de octava.
- `current_cc__250`: `development-008-44100-16`, 600 Hz, 44100 Hz de muestreo, PCM 16 bits: 799 frames con error de octava.

## Decisión

**12 elegibles; ganadora: `filtered_800_03__0`, coste 0,06994822199289351.** Pasa los 14 criterios congelados en todos los casos aplicables (1392 comprobaciones por candidata). La segunda elegible tiene coste 0,07248307623877437, fuera del margen de empate de 0,001.

Autocorrelación filtrada: floor 50 Hz, top 800 Hz; paso 5 ms; 15 candidatos; very_accurate false; atenuación 0,03; silence 0,03; voicing 0,50; octave_cost 0,055; jump_cost 0,35; vu_cost 0,14. Son parámetros de un perfil ya existente, sin ajuste.

Se mantienen exactamente: tramo exacto sin contexto exterior; avisos con delta_t ≤10 ms; soporte distributed (≥50 frames, span ≥1 s y ≥70% de duración, cobertura ≥50%, ≥4 quintiles); todos los criterios y umbrales.

No existe una candidata que falle únicamente criterios secundarios/transicionales: las 12 que superan las comprobaciones congeladas en constantes principales y duración también superan la aceptación completa. Este subgrupo descriptivo no sustituye al filtro completo.

## Validación y trazabilidad

8 tests aprobados de política y evaluador: ausencia de alternativa si no hay elegibles, exclusión de la más barata que falla, conservación de desempates, archivo íntegro de v1, conservación de reglas, no creación de congelación sin ganadora y protección del selector anterior. No se han repetido tests acústicos ni regresiones ajenas a esta política.

Los hashes de motor, módulo, evaluador, manifiesto y resultados siguen iguales. Los hashes del nuevo selector y de la decisión están en v2; el manifiesto adicional cubre archivos nuevos y modificados. La comprobación de integridad confirma que las extracciones y el código acústico son idénticos al commit v1.

**Bloqueado no ejecutado. Esta congelación queda pendiente de revisión; no se abre PR.**
