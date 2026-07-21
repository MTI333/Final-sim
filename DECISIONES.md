# Decisiones de diseño e implementación

Cada entrada: **Decisión** → **Justificación** → **Alternativas descartadas**. Es la base para la
defensa oral: cualquier "¿por qué hicieron esto así?" debería tener su respuesta acá. Las
ambigüedades de interpretación del enunciado (con su default y su "confirmar con cátedra") viven
en `SUPUESTOS.md`; este archivo se enfoca en decisiones de modelado/arquitectura una vez adoptado
un supuesto, más las decisiones que no dependen de ninguna ambigüedad.

---

### D1. Trabajar todo internamente en minutos
**Justificación:** el enunciado mezcla minutos (llegadas, atención) y horas (mantenimiento).
Convertir todo a una única unidad desde el inicio evita bugs de "factor 60" y permite sumar/comparar
tiempos del reloj de simulación sin conversiones puntuales dispersas por el código.
**Alternativa descartada:** manejar horas para mantenimiento y minutos para el resto, convirtiendo
en cada fórmula puntual — más propenso a error y mucho más difícil de auditar en la defensa oral.

### D2. Motor de eventos discretos por lista de eventos futuros ordenada por tiempo (next-event time advance)
**Justificación:** es el paradigma estándar de simulación de eventos discretos, y es el que exige
el formato de "vector de estado" de la cátedra (una fila por evento procesado, no por tick de
tiempo fijo).
**Alternativa descartada:** simulación por pasos de tiempo fijo (time-stepped) — desperdicia
cómputo en instantes sin nada que hacer y no coincide con el estilo de vector de estado pedido.

### D3. Sin evento independiente de "inicio de mantenimiento"
**Justificación:** el inicio de mantenimiento (correctivo o preventivo) se decide dentro del
procesamiento de los eventos Llegada / Fin de atención / Fin de mantenimiento, tal como indica el
prompt (§5.3). Agregar un cuarto tipo de evento programado sería redundante: la decisión es
instantánea, no requiere esperar un tiempo adicional.
**Ver también:** SUPUESTOS.md #2 (no interrumpe atención en curso).

### D4. Selección de copiadora (para clientes y para mantenimiento preventivo) con contadores separados
**Decisión:** criterio de "mayor uso_restante" para asignar cliente, "menor uso_restante" para
elegir a quién mandar a mantenimiento preventivo; contadores `corrective_maintenance_count` y
`preventive_maintenance_count` independientes.
**Justificación:** coherencia interna del modelo preventivo (ver SUPUESTOS.md #5) y requisito
explícito del prompt (§6.2: "registrar un contador separado de mantenimientos correctivos vs
preventivos").

### D5. Cliente como objeto temporal, destruido al finalizar su atención
**Decisión:** no se conserva historial individual de clientes atendidos, solo contadores y
acumuladores agregados (cantidad atendida, suma de esperas, etc.).
**Justificación:** el prompt aclara en §8 que en la última fila del vector de estado "no hace
falta mostrar objetos temporales" — ni el enunciado ni el formato de cátedra piden trazabilidad
individual por cliente, solo estadísticas agregadas (cola máxima, espera promedio, cantidad
atendida).
**Alternativa descartada:** guardar una lista histórica completa de todos los clientes con sus
tiempos — útil para debugging manual, pero es over-engineering frente a lo que pide la consigna.
Si hace falta para `VALIDACION.md`, se puede loguear opcionalmente detrás de un flag de debug, sin
que forme parte del modelo central.

### D6. Cola común como FIFO simple (`deque`), sin prioridades
**Justificación:** el enunciado dice explícitamente "fila común" sin ninguna mención de prioridad
entre clientes.

### D7. Semilla aleatoria configurable, fija por default, para reproducibilidad
**Justificación:** requisito explícito del Definition of Done (§10 del prompt: "caso de prueba
reproducible (semilla fija)"), y necesario para poder auditar en la defensa oral los RND que
aparecen en el vector de estado (correr dos veces con la misma semilla debe dar exactamente el
mismo resultado).

### D8. Idioma: identificadores de código en inglés, documentación y comentarios de dominio en español
**Justificación:** preferencia general del usuario (inglés para código, español para
conversación/documentación). Como el enunciado y la defensa oral son en español, se mantiene una
tabla de correspondencia explícita para que el código sea auditable término a término contra el
enunciado durante la defensa.

| Español (enunciado) | Identificador en código |
|---|---|
| Copiadora | `Copier` |
| Cliente | `Client` |
| Cola común | `queue` (FIFO / `deque`) |
| Mantenimiento correctivo | `corrective maintenance` |
| Mantenimiento preventivo | `preventive maintenance` |
| Cola máxima | `max_queue_length` |
| Uso restante | `usage_remaining` |
| Umbral (de mantenimiento) | `usage_threshold` |
| Simulación | `Simulation` |
| Reloj de simulación | `clock` |

### D9. Todos los parámetros del enunciado configurables en un único lugar
**Decisión:** un solo objeto de configuración (`SimulationConfig`) concentra medias, umbrales,
duración de mantenimiento, X, i, j y semilla. Ningún valor "quemado" dentro de la lógica de
eventos.
**Justificación:** requisito explícito de §1 y §8 del prompt ("todos los parámetros modificables",
"no números quemados").

### D10. `RandomGenerator` como clase (con estado) en vez de funciones sueltas
**Decisión:** `DISEÑO.md` §11 proponía funciones puras `rnd()` / `exponential()` / `uniform()`;
al implementarlas (Etapa 1) se agruparon en una clase `RandomGenerator` que envuelve una instancia
propia de `random.Random(seed)`.
**Justificación:** una función suelta `rnd()` necesitaría apoyarse en el módulo global `random`
(estado compartido, no seedeable de forma aislada) o recibir el generador como parámetro en cada
llamada. Encapsularlo en una clase que la `Simulation` instancia una sola vez con su propia semilla
mantiene la reproducibilidad (D7) sin tocar estado global, y sigue siendo un solo punto de contacto
reemplazable si la cátedra pide un generador congruencial propio (SUPUESTOS.md #7).
**Alternativa descartada:** funciones module-level sobre `random` global — más simple de leer pero
sin aislamiento entre corridas paralelas/tests y con estado global implícito.

### D11. Desempate de eventos simultáneos en el heap por orden de programación
**Decisión:** el heap de eventos guarda tuplas `(time, seq, event)`, con `seq` un contador
monótono creciente asignado al programar cada evento.
**Justificación:** dos eventos pueden caer exactamente en el mismo `time` (p. ej. floats
idénticos por casualidad, o eventos fijos como fin de mantenimiento). `heapq` necesita un criterio
de desempate total; usar el orden de programación es determinístico y reproducible con semilla
fija (D7), y evita tener que definir comparación (`__lt__`) entre objetos `Event`.

### D12. La cola común no se enumera en la tabla del vector de estado
**Decisión:** la tabla principal (`report.format_row`/`format_header`) solo muestra la
**longitud** de la cola (`Cola`), no cada cliente en espera individualmente. El detalle de
clientes vivos en la cola (id, hora de llegada) queda disponible por separado, fila por fila, vía
`report.format_queue_detail(row)`.
**Justificación:** a diferencia de las copiadoras (cantidad fija, 3), la cola común no tiene
tamaño acotado — en los escenarios saturados probados en la Etapa 2/3 llegó a superar los 18.000
clientes en espera. Una tabla con una columna por cliente en cola sería inviable. `StateRow` sigue
guardando la lista completa (`clients_in_queue`), así que "se pueden ver los atributos de los
objetos presentes" (§8 del prompt) sigue siendo cierto — solo que no forman parte de las columnas
fijas de la tabla principal.

### D13. Separación entre motor (`simulation.py`) y presentación (`report.py`)
**Decisión:** `Simulation` arma `StateRow` (datos), pero no sabe formatear ni traducir nada a
español; `report.py` no depende de `Simulation`, solo de `StateRow`.
**Justificación:** permite testear la presentación (tablas, traducciones, recorte de objetos
temporales en la última fila) de forma aislada del motor de eventos, y mantiene la convención de
idioma (DECISIONES.md D8: identificadores internos —`EventType`, `CopierState`— en inglés; la
traducción a español para mostrar en pantalla vive solo en `report.py`, vía los diccionarios
`_EVENT_LABELS_ES` / `_STATE_LABELS_ES`).

### D14. Fila "INIT" para el estado en t=0
**Decisión:** `Simulation` registra una `StateRow` con `event_type="INIT"` al final de `__init__`,
antes de que ocurra ningún evento — captura los 3 sorteos de umbral inicial (SUPUESTOS.md #8) y el
sorteo de la primera llegada, para que también sean auditables en el vector de estado.
**Justificación:** el prompt exige mostrar el RND de cada variable aleatoria (§8); los umbrales
iniciales de las 3 copiadoras y la primera llegada son sorteos reales que de otro modo quedarían
invisibles (ocurren antes de la primera iteración `1`). `report.py` traduce `"INIT"` a `"INICIO"`
al mostrarlo (D13).

### D15. Estadísticas síncronas por acumulación de Δt en cada cambio de estado, no por barrido posterior
**Decisión:** cada `Copier` guarda `state_since`, `busy_time` y `maintenance_time`. Un único punto
de mutación, `Simulation._change_copier_state(copier, new_state)`, calcula
`Δt = clock - state_since` y se lo suma al acumulador del estado que se abandona, antes de
cambiar `state`/`state_since`. Todas las asignaciones directas de `copier.state` en el motor
(`_start_maintenance`, `_assign_client`, ramas `else` de `_process_service_end` y
`_process_maintenance_end`) se reemplazaron por llamadas a este método. Al cortar `run()` se llama
`_finalize_copier_time_accounting()`, que cierra el último intervalo abierto de cada copiadora
transicionándola "a sí misma" (`_change_copier_state(c, c.state)`), para no perder el tramo final
sin un evento que lo cierre.
**Justificación:** es el mismo patrón que ya usa `max_queue_length` (un único punto de mutación
para una invariante estadística) y evita tener que reconstruir los intervalos recorriendo
`state_vector` después — el costo de acumular es O(1) por cambio de estado, contra tener que
iterar hasta 100.000 filas al final. El tiempo libre (`free_pct`) se deriva
(`1 - ocupada% - mantenimiento%`) en vez de acumularse aparte, para no arrastrar tres contadores
cuando dos alcanzan.
**Validado (VALIDACION.md §2, chequeo #13):** con una subclase de auditoría que registra cada
apertura/cierre de intervalo por fuera de `_change_copier_state`, el recálculo independiente de
`busy_time`/`maintenance_time` coincidió exactamente (diferencia 0.00e+00) con los acumuladores de
producción sobre 29.729 intervalos.

### D16. Sin empaquetado formal (`pyproject.toml`/`pip install`) — se corre con `PYTHONPATH=src`
**Decisión:** el proyecto se ejecuta como `PYTHONPATH=src python3 -m copy_center [flags]`, sin
`pyproject.toml`, `setup.py` ni instalación editable.
**Justificación:** es un entregable académico de un solo uso (correrlo para la defensa y para
generar el resultado final), no una librería pensada para reusarse o distribuirse en otros
proyectos. Agregar configuración de empaquetado sería complejidad sin beneficio real para ese caso
de uso, y el proyecto ya no tiene dependencias externas que justifiquen un entorno virtual
gestionado. Ver `README.md` para el comando exacto.
**Alternativa descartada:** `pyproject.toml` + `pip install -e .` con un entry point — más "prolijo"
pero agrega una capa de configuración de packaging que nadie más va a reusar.

---

*Última actualización: 2026-07-17 — Etapa 7 (cierre).*
