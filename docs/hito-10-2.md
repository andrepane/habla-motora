# Hito 10.2 — Navegación y flujo progresivo

Base: `e1728236761302c1ff7085a3dacaf15f1feebb27`, rama
`feat/h10-evaluation-continuity`. Sin PR ni cambios en main.

## Recorrido

`/` y `/evaluation` presentan Nueva evaluación, Continuar e Importar.
`/vocal` conserva el análisis independiente; los enlaces antiguos a
`/?attempt_id=…` y `/?standalone=1` conservan Vocal.

La evaluación tiene tres tareas, intentos numerados/fechados, cinco dominios
cuantitativos y un solo siguiente paso recomendado. Todas las tareas siguen
siendo accesibles manualmente. Crear un intento no lo hace representativo.
La acción «Usar este intento en el Perfil» requiere completar Vocal o
confirmar la revisión DDK/contenido. Los selectores avanzados del Perfil
también impiden elegir intentos todavía no completados; los representantes
anteriores se conservan al quedar desactualizados.

Vocal presenta sus pasos originales y continuación a DDK. En DDK la revisión
manual precede al resultado automático, que permanece en un desplegable.
Habla conectada organiza los mismos controles mediante Grabación y selección,
Contenido, Pausas y Prosodia. Los pasos requieren las dependencias originales.
La forma de acontecimientos se serializa al contrato existente `type: note`.
Los candidatos son ayuda opcional dentro de Pausas y nunca confirman intervalos.
Prosodia conserva la selección exacta y el motor congelado.

La cabecera conserva evaluación, tarea, intento, guardado y enlaces al centro
de evaluación/Perfil. La selección de intento vinculada permanece bloqueada,
como en 10.1. Los UUID siguen en URL/exportación/auditoría, no en etiquetas.

## Consulta y continuación

Abrir un resultado conserva la consulta de solo lectura de 10.1. No escribe
fuentes, invalida resultados ni ejecuta análisis. Para Habla conectada se añade
«Continuar contenido, pausas o Prosodia»: recupera WAV y contexto verificados,
reconstruye las revisiones disponibles y bloquea la selección guardada y el
contenido ya confirmado. Si el contenido estaba pendiente permite revisarlo.
Restaurar resultados no registra nuevas fuentes. Una revisión/cálculo explícito
sí utiliza los controladores originales y sus invalidaciones existentes.
«Editar / Reanalizar» conserva la confirmación y advertencia de 10.1.

## Alcance técnico

`evaluation-flow.js` proyecta metadatos existentes para estados y siguiente
paso; no calcula tasas ni estadísticas. `clinical-task-flow.js` organiza DOM
existente sin sustituir los controladores. Los únicos cambios backend son rutas
HTML. No se modifican los motores, configuraciones, protocolos, store ni
proyector clínico. DDK v2 sigue desactivada. Inteligibilidad sigue no evaluada.

La navegación técnica «Mostrar todos los apartados» permite inspección avanzada
y ejecutar las regresiones detalladas anteriores. Es secundaria y no altera
las dependencias. El recorrido clínico nuevo prueba la presentación progresiva
por defecto, sin activar esa opción.

## Validación

- `npm run test:ui`: unidades existentes más política de recomendación.
- `PRAAT_EXECUTABLE=… python -m pytest -q`: suite completa.
- `tests/test_evaluation_ui.py`: rutas nuevas y compatibilidad de enlaces.
- `npm run test:journey-browser`: recorrido clínico real con WAV sintéticos,
  representante explícito, restauración de contenido pendiente, acontecimientos,
  Pausas sin candidatos, salida/reentrada a Prosodia sin duplicar selección,
  Perfil completo, consulta/cancelación, móvil e independiente.
- Regresiones de navegador: Vocal, DDK, Frase, Pausas, candidatos, Prosodia,
  Perfil y continuidad 10.1.
- Workflow `docker-smoke.yml`: construcción Docker, pytest dentro de imagen,
  caracterización sintética, HTTP y todas las pruebas frontend/navegador.
  Conserva capturas en `clinical-journey-evidence/`.

El informe de evidencia registra resultados, commit probado y ejecución CI.
No se vuelve a ejecutar el banco bloqueado de investigación.

## Límites deliberados

No es el acabado visual final. Conserva formularios clínicos y advertencias
metodológicas; varios detalles técnicos siguen siendo extensos. Almacenamiento
local, exportable: no hay sincronización, cuentas ni base clínica remota.
Los borradores siguen siendo temporales; los resultados registrados e historial
son inmutables. El máximo de dos intentos de Habla conectada permanece intacto.
