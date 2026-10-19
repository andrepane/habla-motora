# Banco experimental de candidatos a pausa

Sin WAV humanos. Sin conexión a /phrase. 7B.1 manual conserva en exclusiva la decisión y el resultado definitivo.

- `development-cases.jsonl.gz`: todas las evaluaciones de desarrollo, receta WAV, referencias construidas, candidatos completos, hashes y métricas.
- `development-summary.json.gz`: resumen completo por familia, condición, duración, frecuencia y formato.
- `frozen-gate.json`: criterios congelados DESPUÉS de desarrollo y ANTES de ejecutar bloqueado. Se guarda en un commit previo a los resultados bloqueados.
- Los archivos equivalentes `blocked-*` y el informe se añaden después de esa congelación.
- `development-20s-smoke.json`: comprobación técnica del formato máximo, bajo carga; no certifica percentiles de rendimiento.

Las referencias regionales son intervalos de construcción sintética. Las referencias `pause_proxy` aplican las reglas temporales al sintético; nunca equivalen a anotación clínica humana. Los candidatos sobre cierres o intervalos cortos útiles para revisar cuentan en la carga proxy: consulte ambos objetivos de evaluación. La carga absoluta cuenta TODOS los candidatos, incluidos bordes.

Los WAV no se duplican en git: cada receta reproduce sus bytes y verifica SHA-256. Para inspeccionar un caso y obtener todos los frames:

```
python -m research.pause_candidates.inspect_case --split development --case-id ID --variant multifeature --output /tmp/pause-case
```

Para descomprimir un resumen: `gzip -dc reports/pause_candidates/development-summary.json.gz > reports/pause_candidates/development-summary.json`. El hash del JSON descomprimido es el que vincula la congelación. Los JSONL incluyen latencia medida, por lo que su hash cambia en una nueva ejecución; se conservan los hashes de esta ejecución exacta. Configuración, señal y características se identifican por hashes propios.

No se elige un motor por tasa de aceptaciones ni por menor número de propuestas aislado. El criterio de carga por familia se obtiene entre métodos con mayor recall de desarrollo, evitando premiar omisiones. Esto sigue siendo un criterio comparativo de ingeniería, no un límite de carga clínicamente tolerable. No se ajusta el algoritmo después de consultar bloqueado.
