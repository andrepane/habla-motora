
## Resultado final y cierre

**Hito 8A cerrado técnicamente en el alcance sintético declarado.** Bloqueado aprobado: 14 criterios, 1.392/1.392 comprobaciones; cero fallos de ejecución o de integridad. No se ha ajustado ni vuelto a ejecutar el banco bloqueado.

Pruebas específicas: 55 aprobadas. Suite local: 605 aprobadas, 6 xfail conocidos y un aviso de deprecación. Frontend: 59/59. Navegador con API real y audio sintético: vocal 24, DDK 35, frase 53, pausas revisadas 60 y candidatos 34 comprobaciones.

Docker: imagen construida correctamente; suite durante la construcción y repetición en contenedor con 605 aprobadas y 6 xfail en ambas. También pasan los informes sintéticos existentes de pitch/jitter/shimmer/HNR/DDK, los endpoints HTTP y las regresiones de navegador del workflow. Evidencia: [GitHub Actions 39435802049](https://github.com/andrepane/habla-motora/actions/runs/39435802049), commit probado `a3d6188f8cd2acc36c5265f82516867d60faa5f4`. La entrega posterior solo añade informes y logs, sin cambiar código congelado ni tests.

Los seis xfail son anteriores a 8A: modulación de pitch raw cc; jitter alternante (dos casos), jitter aleatorio 5%; HNR de 100 Hz a 44,1/48 kHz (dos casos). Sus objetivos no se han relajado.

Limitaciones que permanecen: 60 frames con error de octava en transitorios de escalones de 12 ST (3–4 frames por caso, dentro de la guarda predeclarada), 4.734 en el control de 985,15 Hz fuera de alcance; ausencia de F0 en 46,665 Hz fuera de alcance; huecos de 20 ms no recuperados; cobertura nominal del primer/último tramo de 100 ms de 75% en controles estables por el recorte exacto. No se han corregido ni ocultado. La cobertura sobre frames existentes es una magnitud distinta.

La validez humana, la generalización a habla y las interpretaciones clínicas siguen pendientes. No se ha implementado la interfaz final de prosodia ni abierto PR.
