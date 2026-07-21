# Progreso — Simulación Centro de Copiado

Bitácora de checkpoint entre sesiones. **Leer al empezar cada sesión nueva**; actualizar al
terminar cada etapa (plan completo en `PROMPT_Agente_TP_CentroCopiado.md` §9).

---

## Estado actual

**Etapa actual:** Etapa 7 — Cierre ✅ completada. **Las 8 etapas del plan (§9 del prompt) están
completas.**
**Próximo paso real:** `SUPUESTOS.md` #1 y #4 ya no están pendientes de la cátedra — decisión
final (2026-07-21) tomada por el usuario: apegarse a la lectura literal del enunciado en ambos
aunque el resultado sea inestable (#1) o deje vestigial el correctivo (#4). Falta correr el
resultado final de "cola máxima" con esos defaults para la entrega.
**Código Python:** motor de eventos completo + vector de estado + estadísticas + CLI
(`python -m copy_center`). Los 7 archivos `.md` exigidos por §1 del prompt están completos:
`DISEÑO.md`, `DECISIONES.md` (16 decisiones), `SUPUESTOS.md` (9 supuestos, 2 marcados ⚠️),
`PROGRESO.md` (este archivo), `README.md`, `VALIDACION.md`, `DEFENSA.md`.
**Extra (no entregable):** `src/copy_center/webapp.py` — interfaz web local
(`python -m copy_center.webapp`), ver sesión de abajo.

---

## Sesión 2026-07-17

### Hecho
- Leído el prompt completo (`PROMPT_Agente_TP_CentroCopiado.md`).
- Creados los 4 documentos de la Etapa 0:
  - **`SUPUESTOS.md`** — 9 supuestos registrados: los 5 del prompt §3 (unidad de llegadas ⚠️
    crítico, interrupción por mantenimiento, fórmula de la exponencial, umbral de la regla
    preventiva, selección de copiadora) + 4 adicionales detectados durante el diseño (desempate
    por uso_restante igual, generador de RND a usar, estado inicial del sistema, valor del
    parámetro X de fin de simulación). Cada uno con default adoptado y marca `# TODO: confirmar
    con cátedra` donde corresponde.
  - **`DISEÑO.md`** — modelo completo: tabla de parámetros/unidades, objetos (Cliente,
    Copiadora) con sus atributos, cola común, los 4 tipos de evento, fórmulas de las 3 variables
    aleatorias (llegada, atención, umbral), pseudocódigo del motor de eventos por tipo, lógica de
    mantenimiento correctivo/preventivo, columnas del vector de estado, fórmulas exactas de las
    estadísticas (cola máxima + 5 de apoyo) y arquitectura de clases propuesta para la Etapa 1.
  - **`DECISIONES.md`** — 9 decisiones de arquitectura/modelado con justificación y alternativas
    descartadas, incluyendo la convención de idioma (código en inglés, docs en español) con tabla
    de correspondencia de términos español↔inglés.
  - **`PROGRESO.md`** (este archivo).

### Pendiente / próximos pasos
- [ ] Confirmar con la cátedra los puntos de `SUPUESTOS.md`, en especial **#1** (tasa de llegadas
  4/min vs. 1 cada 4 min) — es el más crítico porque cambia por completo el comportamiento del
  sistema y por lo tanto el resultado de "cola máxima".
- [ ] **Etapa 1:** crear el esqueleto Python — `SimulationConfig`, clase `Simulation`, clase
  `Copier`, clase `Client`, clase/tipo `Event`, funciones `rnd()` / `exponential()` / `uniform()`
  aisladas y testeables.
- [ ] Definir un valor de prueba concreto para el parámetro `end_time` (X) cuando se llegue a
  `VALIDACION.md`.

### Notas para retomar
- No se crearon todavía `README.md`, `VALIDACION.md` ni `DEFENSA.md` — corresponden a las etapas
  5-7 del plan, no a la 0.
- No hay repositorio git inicializado en esta carpeta.
- Todo el modelo (colas, eventos, fórmulas) está cerrado en `DISEÑO.md`; antes de tocar código en
  la Etapa 1 conviene releer `DISEÑO.md` §11 (arquitectura propuesta) y `DECISIONES.md` D8 (tabla
  de nombres español↔inglés) para no tener que rehacer las clases luego.

---

## Sesión 2026-07-17 (cont.) — Etapa 1

### Hecho
- Creado el paquete `src/copy_center/` con la arquitectura definida en `DISEÑO.md` §11:
  - **`config.py`** — `SimulationConfig` (dataclass) con todos los parámetros de §2 de
    `DISEÑO.md` en minutos, más validaciones básicas en `__post_init__` (medias positivas,
    umbrales coherentes, etc.).
  - **`random_utils.py`** — `RandomGenerator`, clase que envuelve `random.Random(seed)` propio
    (no usa el módulo `random` global) con métodos `uniform01()`, `exponential(mean)` y
    `uniform(low, high)`; estos dos últimos devuelven un `Draw(value, rnd)` para poder mostrar el
    RND crudo en el vector de estado más adelante (§8 del prompt). Implementa el default de
    `SUPUESTOS.md` #3 (`T = -media * ln(1 - RND)`).
  - **`entities.py`** — `CopierState` (enum FREE/BUSY/MAINTENANCE), `Client` (objeto temporal,
    con propiedad `waited`), `Copier` (objeto permanente, con `consume_usage()` y
    `needs_corrective_maintenance()`).
  - **`events.py`** — `EventType` (ARRIVAL/SERVICE_END/MAINTENANCE_END/SIMULATION_END) y
    `Event` (dataclass); confirma D3 (sin evento propio de inicio de mantenimiento).
  - **`simulation.py`** — esqueleto de `Simulation`: arma las 3 copiadoras con umbral sorteado
    independientemente (estado inicial de `SUPUESTOS.md` #8), cola vacía, programa la primera
    llegada y (si `end_time` está seteado) el evento de fin de simulación. `run()` lanza
    `NotImplementedError` a propósito — el motor de eventos es la Etapa 2.
- Agregadas dos decisiones de implementación a `DECISIONES.md` (D10: `RandomGenerator` como clase
  en vez de funciones sueltas sobre el módulo `random` global; D11: desempate de eventos
  simultáneos en el heap por orden de programación).
- **Smoke test manual** (`PYTHONPATH=src python3 -c "..."`, no quedó como archivo de test
  permanente — eso corresponde a `VALIDACION.md` en la Etapa 6): instancié `Simulation` con la
  config default y verifiqué que las 3 copiadoras arrancan Libres con `usage_threshold` dentro de
  `[10200, 13800]` y `usage_remaining == usage_threshold`; la cola arranca vacía; se programa
  exactamente 1 evento inicial (`ARRIVAL`); dos corridas con la misma semilla producen los mismos
  umbrales sorteados (reproducibilidad, D7); `run()` falla explícitamente con
  `NotImplementedError`. Todo OK.

### Pendiente / próximos pasos
- [ ] Confirmar con la cátedra los puntos de `SUPUESTOS.md` (sigue pendiente, no bloqueante para
  seguir codeando con los defaults).
- [ ] **Etapa 2:** implementar `Simulation.run()` / `process_event()` para Llegada y Fin de
  atención (DISEÑO.md §7.1, §7.2), sin mantenimiento todavía. Validar que corre sin errores y que
  la cola máxima observada tiene sentido con los parámetros default.
- [ ] Definir un valor de prueba concreto para `end_time` (X) cuando se llegue a `VALIDACION.md`.

### Notas para retomar
- El paquete vive en `src/copy_center/`; para importarlo hace falta `PYTHONPATH=src` (no hay
  todavía `pyproject.toml`/instalación editable — se puede agregar en la Etapa 7 si hace falta un
  entry point más prolijo para el `README.md`).
- `Simulation.run()` está deliberadamente sin implementar; no es un bug, es el corte de la Etapa 1.

---

## Sesión 2026-07-17 (cont.) — Etapa 2

### Hecho
- Implementado el motor de eventos en `simulation.py` (DISEÑO.md §7.1, §7.2), sin ninguna lógica
  de mantenimiento todavía:
  - `_process_arrival`: reprograma la próxima llegada, crea el `Client`, asigna copiadora libre
    (`_select_free_copier`: mayor `usage_remaining`, desempate por menor id — SUPUESTOS.md #5/#6)
    o encola en `self.queue` si las 3 están ocupadas.
  - `_process_service_end`: libera al cliente atendido, toma el siguiente de la cola si hay
    (mismo copiadora, sortea nueva atención) o pasa la copiadora a Libre si la cola está vacía.
    **No toca `usage_remaining` ni dispara mantenimiento** — eso es Etapa 3/4 explícitamente.
  - `_update_max_queue_length`: único punto que actualiza `max_queue_length`, llamado en cada
    mutación de `self.queue` (encolar y desencolar), tal como pide DISEÑO.md §10.1.
  - `_process_event` despacha por tipo; `run()` corre hasta `max_iterations` o hasta procesar
    `SIMULATION_END`.
  - De paso, ya que la información estaba a mano en `_assign_client`, se completó también el
    acumulador de apoyo `total_wait_time` / `clients_that_waited` (espera asíncrona, DISEÑO.md
    §10.2) — no estaba estrictamente pedido hasta la Etapa 6, pero salió gratis al implementar la
    asignación y evita tener que volver a tocar ese método más adelante.
  - Se fusionó `_schedule_first_arrival` en `_schedule_next_arrival` (era código duplicado; la
    primera llegada y las siguientes se sortean exactamente igual).
- **Validación manual** (no quedó como test permanente, eso es `VALIDACION.md` en la Etapa 6) con
  tres escenarios de 5000 iteraciones cada uno:
  - Default literal del enunciado (`mean_interarrival_time=0.25`, SUPUESTOS #1): sistema
    totalmente saturado, cola máxima = 4503 en apenas 5000 iteraciones, las 3 copiadoras 100%
    ocupadas — confirma numéricamente que este supuesto es sospechoso y hay que confirmarlo con
    la cátedra antes de reportar el resultado final.
  - Interpretación alternativa (`mean_interarrival_time=4`): también saturado pero mucho más
    gradual (cola máxima = 525 en el mismo número de iteraciones).
  - Escenario claramente estable (`mean_interarrival_time=20`, ρ≈0,25): cola máxima = 4, la
    mayoría de los clientes no espera, copiadoras terminan libres — comportamiento esperado.
  - Reproducibilidad: dos corridas independientes con `seed=777` dieron exactamente el mismo
    `max_queue_length` y `clients_served`.
  - Confirmado que ninguna corrida disparó `NotImplementedError` de mantenimiento (esperable: sin
    Etapa 3/4 nunca se programa un `MAINTENANCE_END`).

### Pendiente / próximos pasos
- [ ] **Etapa 3:** en `_process_service_end`, restar la duración de la atención de
  `copier.usage_remaining`; si llega a `<= 0`, pasar la copiadora a `MAINTENANCE`, programar
  `MAINTENANCE_END` a `clock + maintenance_duration`, e incrementar
  `corrective_maintenance_count`. Implementar `_process_maintenance_end` (sortear nuevo umbral,
  volver a Libre o tomar cliente de la cola).
- [ ] Confirmar con la cátedra los puntos de `SUPUESTOS.md` (sigue pendiente).
- [ ] Definir un valor de prueba concreto para `end_time` (X) para `VALIDACION.md`.

### Notas para retomar
- El escenario default (`mean_interarrival_time=0.25`) es útil para *estresar* el motor durante
  desarrollo, pero **no** es necesariamente el que hay que reportar como resultado final del TP —
  depende de la confirmación de SUPUESTOS.md #1.
- Con parámetros saturados, la cola crece indefinidamente: para probar cosas rápido a mano
  conviene usar `max_iterations` chico (unos pocos miles) o un `mean_interarrival_time` más alto.

---

## Sesión 2026-07-17 (cont.) — Etapa 3

### Hecho
- Implementado el mantenimiento correctivo (DISEÑO.md §7.2 pasos 2-3, §7.3, §8.1):
  - `_process_service_end` ahora calcula la duración real de la atención que acaba de terminar
    (`self.clock - finished_client.service_start_time`), se la resta a `copier.usage_remaining`
    vía `Copier.consume_usage()`, y si `Copier.needs_corrective_maintenance()` es `True` manda la
    copiadora a mantenimiento en vez de tomar el siguiente cliente de la cola o pasar a Libre.
    `usage_remaining` puede quedar negativo — es el comportamiento esperado de SUPUESTOS.md #2 (no
    se interrumpe la atención en curso).
  - Nuevo helper `_start_maintenance(copier, corrective)`: pasa la copiadora a `MAINTENANCE`,
    programa `MAINTENANCE_END` a `clock + maintenance_duration`, e incrementa el contador
    correspondiente (`corrective_maintenance_count` o `preventive_maintenance_count` — este
    segundo se deja listo para la Etapa 4).
  - `_process_maintenance_end` implementado: sortea un nuevo `usage_threshold` ~
    Uniforme[min, max], resetea `usage_remaining`, y si hay clientes esperando en la cola común
    toma al siguiente (pasa directo a Ocupada); si no, queda Libre.
- **Validación manual** (dos corridas, no quedaron como test permanente):
  1. Escenario realista (`mean_interarrival_time=6`, ρ≈0,83, 50.000 iteraciones): 30
     mantenimientos correctivos, 0 preventivos (esperado, todavía no existe la regla), invariantes
     de estado verificadas en las 3 copiadoras (`usage_remaining <= usage_threshold`, ninguna
     `MAINTENANCE` con `current_client` seteado), reproducibilidad confirmada con semilla fija.
  2. Escenario dirigido (`maintenance_threshold_min = maintenance_threshold_max = 25`, para poder
     verificar la mecánica a mano): confirma que el correctivo se dispara apenas se acumulan ~25
     min de uso, que el umbral se resortea correctamente al valor fijo esperado (25.0), y que
     `usage_remaining` queda negativo en las copiadoras que terminaron en mantenimiento (coherente
     con SUPUESTOS.md #2).

### Pendiente / próximos pasos
- [ ] **Etapa 4:** implementar la regla preventiva — al final de `_process_service_end` y
  `_process_maintenance_end` (donde dice "Regla preventiva: Etapa 4"), chequear si las 3
  copiadoras quedaron `FREE` simultáneamente y, si es así, mandar a mantenimiento a la de menor
  `usage_remaining` vía `_start_maintenance(copier, corrective=False)` (el helper ya soporta el
  caso preventivo, solo falta el chequeo y la selección).
- [ ] Confirmar con la cátedra los puntos de `SUPUESTOS.md` (sigue pendiente).

### Notas para retomar
- El helper `_start_maintenance` ya recibe un flag `corrective: bool` y ya sabe incrementar el
  contador correcto — la Etapa 4 solo necesita agregar el *chequeo* de "3 libres a la vez" y
  llamarlo con `corrective=False`, no hay que tocar la firma.
- Ambos puntos donde va la regla preventiva ya están marcados con el comentario `# Regla
  preventiva ("las 3 libres a la vez"): Etapa 4` en `simulation.py`.

---

## Sesión 2026-07-17 (cont.) — Etapa 4

### Hecho
- Implementada la regla de mantenimiento preventivo (DISEÑO.md §7.4, §8.2):
  - Nuevo método `_maybe_trigger_preventive_maintenance()`: si las 3 copiadoras están `FREE`
    simultáneamente, elige la de menor `usage_remaining` (desempate por menor id, SUPUESTOS.md
    #4/#6) y la manda a mantenimiento vía `_start_maintenance(copier, corrective=False)` (el
    helper ya soportaba este caso desde la Etapa 3).
  - Se llama al final de `_process_service_end` y `_process_maintenance_end` — **nunca** desde
    `_process_arrival`, porque una llegada solo puede reducir la cantidad de copiadoras libres,
    nunca dejar a las 3 libres a la vez (documentado en el docstring del método).
  - Confirmado (ver SUPUESTOS.md §7.4 en DISEÑO.md, ya decidido en Etapa 0): la regla **no** se
    evalúa contra el estado inicial en `t=0` (las 3 copiadoras arrancan libres por default, pero
    eso no es una "transición" — solo se chequea tras Fin de atención / Fin de mantenimiento).
- **Validación manual** con una subclase de instrumentación temporal (no quedó en el código de
  producción) que interceptaba `_start_maintenance` para afirmar, en cada disparo preventivo, que
  las 3 copiadoras estaban realmente libres en ese instante y que se eligió la de menor
  `usage_remaining`:
  - Escenario de baja carga (`mean_interarrival_time=30`): 5201 preventivos, 0 correctivos, todas
    las aserciones de instrumentación pasaron, reproducibilidad confirmada con semilla fija.
  - Escenario saturado (default literal, `mean_interarrival_time=0.25`): 0 preventivos y 0
    correctivos en 20.000 iteraciones — esperable, el sistema casi nunca tiene las 3 libres a la
    vez cuando está saturado.
  - **Hallazgo importante:** en el escenario moderado ya usado en la Etapa 3
    (`mean_interarrival_time=6`, semilla 42, 50.000 iteraciones), al activar la regla preventiva
    los correctivos bajaron de 30 (Etapa 3, sin preventiva) a **0**, con 353 preventivos. Sin
    umbral mínimo, la regla preventiva "se adelanta" y elimina virtualmente la posibilidad de que
    ocurra un correctivo. Quedó documentado como hallazgo empírico en `SUPUESTOS.md` #4 (ahora
    marcado ⚠️, junto con el #1, como uno de los dos puntos más importantes para confirmar con la
    cátedra).

### Pendiente / próximos pasos
- [ ] **Etapa 5:** vector de estado — registrar una fila por evento procesado (con RND de cada
  variable aleatoria involucrada, estado de las 3 copiadoras, longitud de cola, acumuladores),
  mostrar `i` filas desde `j`, mostrar la última fila sin objetos temporales (§8 del prompt).
- [ ] Confirmar con la cátedra los puntos de `SUPUESTOS.md`, en especial **#1** (tasa de llegadas)
  y **#4** (umbral mínimo de la regla preventiva) — este último con evidencia empírica concreta
  ahora disponible.

### Notas para retomar
- El motor de eventos (Etapas 2-4) está funcionalmente completo y validado a mano en varios
  escenarios (saturado, moderado, de baja carga), pero **todavía no hay ningún output legible**:
  solo se puede inspeccionar `Simulation` por atributos después de `run()`. La Etapa 5 es la que
  arma el vector de estado y la presentación pedida por la cátedra.
- Antes de fijar los parámetros default para el `README.md`/entrega final, conviene resolver
  SUPUESTOS.md #1 y #4 — ambos cambian drásticamente el comportamiento del sistema y por lo tanto
  el valor final de "cola máxima".

---

## Sesión 2026-07-17 (cont.) — Etapa 5

### Hecho
- Nuevo módulo **`state_vector.py`**: `StateRow` (una fila = una iteración), `CopierSnapshot`,
  `ClientSnapshot`. `StateRow` guarda, entre otras cosas, los `Draw` (valor + RND) de llegada,
  atención y umbral(es) usados en ese evento — reutiliza `Draw` de `random_utils.py` en vez de
  duplicar la estructura.
- Nuevo módulo **`report.py`**, desacoplado de `Simulation` (D13): `format_header`, `format_row`,
  `format_queue_detail`, `render_full_report(state_vector, n_copiers, j, i)`. Traduce los nombres
  internos de evento/estado (ingles, D8) a español para mostrar (`_EVENT_LABELS_ES`,
  `_STATE_LABELS_ES`).
- `simulation.py`:
  - `_draw_exponential(kind, mean)` / `_draw_uniform_threshold(copier_id)`: wrappean las llamadas
    al `RandomGenerator` y además registran el `Draw` en `self._current_draws` /
    `self._current_umbral_draws` para la fila en curso. Reemplazan las llamadas directas a
    `self.rng.*` en `_new_copier`, `_schedule_next_arrival`, `_assign_client` y
    `_process_maintenance_end` — **sin cambiar el orden ni la cantidad de sorteos**, así que la
    secuencia de números aleatorios (y por lo tanto los resultados) no cambia.
  - `_record_state_row(event_type)`: arma una `StateRow` con el estado completo del sistema
    (copiadoras, cola, acumuladores) + los draws de la iteración en curso, la agrega a
    `self.state_vector`, y resetea los draws para la próxima.
  - Se agrega una fila `"INIT"` al final de `__init__` (D14) para que los 3 umbrales iniciales y
    la primera llegada también queden auditables.
  - `run()` llama a `_record_state_row(event.type.name)` después de procesar cada evento.
- **Validación manual** (no quedó como test permanente):
  - Chequeo de no-regresión: repetí el escenario moderado de la Etapa 4
    (`mean_interarrival_time=6`, semilla 42, 50.000 iteraciones) y confirmé que da exactamente los
    mismos resultados (correctivos=0, preventivos=353, cola_máxima=35) — el registro del vector de
    estado no alteró la secuencia de RND.
  - `len(state_vector) == iteration + 1` (la fila extra es `INIT`).
  - Fila `INIT`: 3 draws de umbral (uno por copiadora, cada uno con RND en [0,1) y valor en
    [10200, 13800]) + 1 draw de llegada.
  - `render_full_report` probado con `j`/`i` normales y con `j` cerca del final (ventana más chica
    que `i` porque no hay más filas) — no rompe, la última fila oculta correctamente los ids de
    cliente (`Cop_Cliente = "-"`) pero conserva `Cola` (longitud) visible.
  - Confirmé que `state_vector[-1].max_queue_length == sim.max_queue_length` (la cola máxima se
    lee de la última fila, como pide DISEÑO.md §10.1).
  - De paso, un ejemplo con pocos iteraciones mostró en vivo el efecto ya documentado en
    SUPUESTOS.md #4: la copiadora 2 entra en mantenimiento preventivo en la iteración 2, apenas
    las 3 quedan libres por primera vez, mucho antes de acumular uso real.

### Pendiente / próximos pasos
- [ ] **Etapa 6:** estadísticas de apoyo síncronas (% ocupación, % tiempo en mantenimiento por
  copiadora) — requieren acumular `Δt = tiempo del próximo evento − tiempo del evento actual`
  ponderado por el estado vigente; no alcanza con los contadores puntuales que ya existen.
  Terminar de calcular tiempo promedio de espera (`total_wait_time / clients_that_waited`, ya
  acumulado desde la Etapa 2) y armar `VALIDACION.md` con casos de prueba y sanity checks.
- [ ] Confirmar con la cátedra `SUPUESTOS.md` #1 y #4 (sigue pendiente).

### Notas para retomar
- `report.py` es standalone: recibe `state_vector` + `n_copiers` + `j`/`i`, no necesita el objeto
  `Simulation`. Para usarlo desde afuera: `render_full_report(sim.state_vector, sim.config.n_copiers,
  sim.config.report_from_iteration, sim.config.report_row_count)`.
- Guardar el vector de estado completo en memoria (una `StateRow` por iteración, hasta 100.000)
  es la elección simple y suficiente para este TP; si en algún momento pesara demasiado, la
  alternativa sería volcar a CSV/streaming en vez de acumular en una lista — no hizo falta todavía.

---

## Sesión 2026-07-17 (cont.) — Etapa 6

### Hecho
- **`entities.py`:** `Copier` suma `state_since`, `busy_time`, `maintenance_time` (el tiempo libre
  se deriva, no se acumula aparte — DECISIONES.md D15).
- **`simulation.py`:**
  - Nuevo `_change_copier_state(copier, new_state)`: único punto de mutación de `copier.state`;
    acumula `Δt` en `busy_time`/`maintenance_time` del estado que se abandona antes de cambiarlo.
    Reemplazó las 4 asignaciones directas de `copier.state = ...` que había en el motor
    (`_start_maintenance`, `_assign_client`, y las ramas `else` de `_process_service_end` /
    `_process_maintenance_end`).
  - `_finalize_copier_time_accounting()`: cierra el último intervalo abierto de cada copiadora al
    terminar `run()` (si no, el tramo final entre el último cambio de estado y el corte de la
    simulación quedaba sin contar).
  - `summary() -> SimulationSummary`: arma el resumen final (cola máxima, clientes atendidos,
    espera promedio, contadores de mantenimiento, % ocupación/mantenimiento/libre por copiadora).
- Nuevo módulo **`statistics.py`**: `CopierStats`, `SimulationSummary`, `copier_stats()` (calcula
  los 3 porcentajes con clamp para evitar libre% negativo por error de redondeo de punto flotante).
- **`report.py`:** nuevo `format_summary(summary)` — texto legible con el resumen completo.
- **`VALIDACION.md`** (nuevo): caso de prueba reproducible oficial (`seed=42,
  mean_interarrival_time=6.0, max_iterations=50000`) con resultado exacto documentado, 18 chequeos
  de sanidad con su resultado, y una tabla de escenarios exploratorios que respaldan
  SUPUESTOS.md #1 y #4.
- **Validación** (resumen; detalle completo en `VALIDACION.md`):
  - Sin regresión: el caso del seed=42 sigue dando correctivos=0, preventivos=353, cola_máxima=35.
  - Invariante `ocupada% + mantenimiento% + libre% = 100%` verificado en las 3 copiadoras.
  - Invariante más fuerte, sin el clamp: `busy_time + maintenance_time <= total_time`.
  - **Chequeo cruzado independiente:** armé una subclase de `Simulation` que registra cada
    apertura/cierre de intervalo por fuera de `_change_copier_state` (sin reusar su lógica) y
    recalculé `busy_time`/`maintenance_time` desde cero — coincidió exactamente (diferencia
    0.00e+00) con los acumuladores de producción sobre 29.729 intervalos. Este fue el chequeo más
    convincente: descarta bugs de doble conteo o de intervalos que quedan sin cerrar.
  - `maintenance_time` de cada copiadora resultó ser múltiplo exacto de 120 (duración fija), y la
    suma de esos múltiplos coincide con el contador de preventivos — otra confirmación cruzada.
  - `max_queue_length` monótona creciente verificada en las 50.001 filas del vector de estado.
  - Conteo de filas por tipo de evento (`INIT`+`ARRIVAL`+`SERVICE_END`+`MAINTENANCE_END`)
    consistente con los acumuladores (`clients_served`, `corrective_+preventive_count`).

### Pendiente / próximos pasos
- [ ] **Etapa 7 (cierre):** `README.md` (cómo instalar/correr, parámetros, ejemplos — hoy no hay
  ninguna forma de correr esto sin abrir un intérprete de Python y llamar a `Simulation`
  directamente); `DEFENSA.md` (preguntas probables + respuestas); repasar `DECISIONES.md` completo.
- [ ] Confirmar con la cátedra `SUPUESTOS.md` #1 y #4 (sigue pendiente — es lo único que falta
  para poder correr el caso oficial final, no uno de prueba).
- [ ] Una vez confirmados los supuestos, congelar en `VALIDACION.md` el resultado con los
  parámetros definitivos de entrega (distinto del caso de prueba de esta etapa, que usó
  `mean_interarrival_time=6` solo para tener un escenario cargado pero no degenerado).

### Notas para retomar
- El motor (Etapas 2-4), el vector de estado (Etapa 5) y las estadísticas (Etapa 6) están
  funcionalmente completos y validados. Lo que falta es enteramente de "cierre de entrega": una
  forma cómoda de ejecutar (`README.md`/CLI) y la documentación de defensa oral.
- `Simulation.summary()` puede llamarse en cualquier momento, pero los % por copiadora solo están
  cerrados una vez que `run()` terminó (llama a `_finalize_copier_time_accounting()` al final).
  Si se llamara a mitad de una corrida, el último intervalo abierto no estaría contabilizado.

---

## Sesión 2026-07-17 (cont.) — Etapa 7 (cierre)

### Hecho
- Nuevo módulo **`cli.py`**: `argparse` con un flag por cada campo de `SimulationConfig` (mismos
  defaults), corre la simulación e imprime `render_full_report(...)` + `format_summary(...)`.
  `--report-from`/`--report-rows` mapean a `report_from_iteration`/`report_row_count` (los demás
  flags usan la conversión automática de guiones a guiones bajos de `argparse`).
- **`__main__.py`**: permite `python -m copy_center` además de `python -m copy_center.cli`.
- **`README.md`** (nuevo): requisitos, cómo correr, tabla de los 11 parámetros con su default y
  significado, ejemplo de salida, estructura del proyecto, índice de la documentación del TP, y
  una sección final que repite (a propósito, para que no se pierda) la advertencia sobre
  SUPUESTOS.md #1 y #4 antes de reportar un resultado como entrega definitiva.
- **`DEFENSA.md`** (nuevo): ~18 preguntas probables organizadas en 5 bloques (modelo general,
  números aleatorios, mantenimiento, estadísticas, validación/supuestos), cada respuesta con
  referencia al documento donde está el detalle para poder profundizar en vivo.
- **`DECISIONES.md`:** agregada D16 (por qué no hay `pyproject.toml`/instalación editable — se
  corre con `PYTHONPATH=src`), y repaso completo del archivo (D1-D16) para confirmar que no hay
  contradicciones ni decisiones desactualizadas.
- **Validación del cierre:**
  - CLI probado con una corrida chica (30 iteraciones) y con el tope de **100.000 iteraciones**
    (`--max-iterations 100000`): corrió en ~2,9 s sin errores — confirma el ítem del Definition of
    Done "corre hasta 100.000 iteraciones... sin errores".
  - `--help` probado: describe los 11 parámetros con su default.
  - Corte por `--end-time` (parámetro X) probado explícitamente: con `end_time=500.0` la corrida
    cortó antes de las 100.000 iteraciones y `sim.clock == 500.0` exacto.
  - Confirmado que los 7 archivos `.md` de `§1` del prompt existen y tienen contenido.
  - Limpiado `__pycache__` del árbol de `src/`.

### Definition of Done (§10 del prompt) — repaso final
- [x] Calcula la cola máxima correctamente (VALIDACION.md).
- [x] Corre hasta 100.000 iteraciones o hasta X sin errores (probado en esta etapa, ambos casos).
- [x] Consistencia de unidades verificada (todo en minutos, DISEÑO.md §4).
- [x] Mantenimiento correctivo y preventivo funcionando, con contadores separados (Etapas 3-4).
- [x] `i`, `j`, última fila, RND por variable y objetos temporales visibles (Etapa 5, `report.py`).
- [x] Todos los parámetros configurables (`SimulationConfig` + CLI).
- [x] Documentación `.md` completa y actualizada (los 7 archivos de §1).
- [x] Caso de prueba reproducible (semilla fija) documentado en `VALIDACION.md`.

**Las 8 etapas del plan y los 8 ítems del Definition of Done están completos.** Lo único que
queda — y no es una tarea de código — es la confirmación de la cátedra sobre SUPUESTOS.md #1 y #4
antes de fijar el resultado final de "cola máxima" a entregar.

### Pendiente / próximos pasos
- [ ] Llevar `SUPUESTOS.md` #1 y #4 a la cátedra (o al enunciado/consultas del curso).
- [ ] Una vez resueltos, correr el caso final con los parámetros definitivos y actualizar
  `VALIDACION.md` con ese resultado como "el" resultado de entrega (distinto del caso de prueba
  usado para validar el motor, que a propósito evitó los valores degenerados de SUPUESTOS #1).
- [ ] Repasar `DEFENSA.md` en voz alta antes de la defensa oral.

### Notas para retomar
- Si se retoma este proyecto en otra sesión: leer primero este archivo (`PROGRESO.md`) completo,
  después `SUPUESTOS.md` (para ver si los ⚠️ #1/#4 ya se confirmaron) y recién ahí tocar código.
- Todo el código vive en `src/copy_center/`; se corre con `PYTHONPATH=src python3 -m copy_center`.
  No hay tests automatizados formales (pytest) — toda la validación quedó documentada como
  corridas manuales reproducibles en `PROGRESO.md`/`VALIDACION.md`. Si se agrega una suite de
  tests más adelante, los casos de `VALIDACION.md` §1-2 son el punto de partida natural.

---

## Sesión 2026-07-17 (cont.) — webapp: gráfico de cola + resaltado de pico

### Contexto: recuperación tras apagón
La PC se apagó a mitad de sesión. Al retomar: **todo el código estaba intacto** (nada
truncado/corrupto — `py_compile` limpio en los 12 archivos, CLI y webapp corren igual que antes).
Lo único que se había perdido era la *anotación*: `src/copy_center/webapp.py` (interfaz web local,
379 líneas) y el cambio en `report.py` que expone `event_label`/`state_label` como funciones
públicas para que la webapp las reuse, se habían escrito **después** de la última entrada de esta
bitácora (que decía "las 8 etapas están completas") y por lo tanto no habían quedado registrados acá.
Repuesto arriba en "Estado actual" y en esta entrada para que no vuelva a pasar.

### Hecho
- **Gráfico "Cola en el tiempo"** (`render_queue_chart` en `webapp.py`): SVG en escalera (step
  chart) armado a mano, sin librerías (mismo criterio stdlib-only que el resto de la webapp,
  DECISIONES.md D16) — `queue_length` es constante entre eventos, así que un step chart es la
  forma correcta (no una línea interpolada, que mentiría sobre los valores intermedios).
  - Ejes con ticks "lindos" (múltiplos 1/2/2.5/5·10ⁿ), grilla hairline, wash de área al 10% de
    opacidad bajo la línea.
  - **Submuestreo para corridas grandes** (`_downsample_for_chart`, tope 400 puntos por defecto):
    con `max_iterations` por defecto en 100.000 el vector de estado puede tener 100k filas: cada
    bucket conserva su primer punto y su pico, así el trazo nunca esconde la cola máxima aunque se
    recorte resolución. El pie del gráfico avisa cuándo está submuestreado.
  - **Marcador en el punto de cola máxima** (círculo + label "Cola máx: N" + `<title>` nativo),
    calculado siempre sobre el vector completo (no sobre los puntos submuestreados), para que el
    valor mostrado sea exacto.
  - **Hover con crosshair + tooltip** (vanilla JS, sin dependencias — primer JS del proyecto):
    sigue el mouse, busca el punto más cercano por tiempo (búsqueda binaria) y muestra
    cola/tiempo/iteración. Los datos van en un `<script type="application/json">` (no inline en el
    HTML) y el tooltip se arma con `textContent`, nunca `innerHTML`, para no confiar en los datos
    como si fueran HTML seguro.
- **Resaltado de la fila de cola máxima** en la tabla (`render_table`): fondo + barra lateral de
  acento + badge "◆ máx" en la celda de Cola, en la fila exacta donde se alcanzó por primera vez el
  máximo. Si `max_queue_length == 0` (nunca se formó cola) no se resalta nada — no tendría sentido
  marcar una fila arbitraria entre puras filas en cero.
- **Card "Cola máxima" clickeable**: ahora es un link que salta directamente a la página de tabla
  que contiene esa fila (centrada en la ventana, no como primera fila cortada), reutilizando el
  mismo mecanismo de query string que ya usaba la paginación.
- **Validación:**
  - `py_compile` limpio en todo `src/`.
  - Script de humo (`smoke_test_webapp.py`, en el scratchpad de la sesión, no en el repo): corrida
    chica, corrida con cola en cero, y corrida grande (20.000 iteraciones) — en los tres casos se
    siguió el link "Cola máxima" como lo haría un click real y se confirmó que la página de destino
    muestra la fila resaltada.
  - Servidor real levantado (`python -m copy_center.webapp`) y consultado por HTTP (no solo
    en memoria): `200 OK`, el bloque `<svg>` devuelto es XML bien formado.
  - **Hallazgo colateral (no arreglado, fuera de alcance):** con `mean_interarrival_time=0.25`
    (el default, el mismo que `SUPUESTOS.md` #1 marca como crítico/degenerado a confirmar con la
    cátedra) la cola crece sin límite; `Simulation` reconstruye `clients_in_queue` completo en
    *cada* fila del vector de estado (`simulation.py`, snapshot por iteración), lo que da O(n²) en
    ese escenario degenerado y una corrida de 20.000 iteraciones no terminaba en 120 s. No es un
    problema de la webapp ni de esta sesión — ya estaba así en el motor — y solo se manifiesta en
    el caso patológico que la cátedra todavía tiene que resolver. Si `SUPUESTOS.md` #1 se confirma
    con la tasa alta, conviene revisar esto antes de correr el caso final de entrega.
  - No se probó visualmente en un navegador real (sin herramienta de screenshot/browser
    disponible en esta sesión) — la validación fue estructural (XML bien formado, HTTP 200,
    elementos esperados presentes) y funcional (flujo click→resaltado con datos simulados reales).

### Pendiente / próximos pasos
- Confirmar visualmente en un navegador (pendiente por falta de herramienta en esta sesión).
- Sigue pendiente lo de siempre: `SUPUESTOS.md` #1 y #4 con la cátedra.
- Si se retoma el hallazgo colateral de arriba: candidato a arreglo sería no armar
  `clients_in_queue` en cada fila, o cachear las snapshots — pero es una decisión de diseño del
  motor (afecta D12), no algo para tocar sin pensarlo.

---

*Agregar nuevas entradas de sesión abajo de esta línea, sin borrar el historial anterior.*

---

## Sesión 2026-07-18 — webapp: server real levantado, fix de la landing page

### Contexto
El pendiente de la sesión anterior era "confirmar visualmente en un navegador" (no se
había podido antes por falta de herramienta). Esta sesión sí corre en la máquina del
usuario, así que se levantó `copy_center.webapp` como servidor real en background
(`PYTHONPATH=src python3 -m copy_center.webapp --port 8877`) en vez de mostrar solo un
snapshot estático.

### Hecho
- **Hallazgo confirmado en producción (ya no solo teórico):** el primer intento de levantar
  el server y pedir `GET /` sin query string colgó el proceso — subió a >2.7 GB de RAM y
  no respondió en 2 min. Es el mismo hallazgo colateral anotado en la sesión anterior
  (O(n²) de `Simulation` + `mean_interarrival_time=0.25` degenerado de SUPUESTOS.md #1),
  pero acá se manifestó de entrada porque `_config_from_query({})` arma la config con
  **todos** los defaults de `SimulationConfig`, incluido `max_iterations=100_000`. Se mató
  el proceso (`kill -9`).
- **Fix acotado a la webapp** (`_LANDING_MAX_ITERATIONS = 200` en `webapp.py`): cuando
  `GET /` llega sin query string, se usa ese tope solo para la carga inicial en vez de los
  100.000 default. El formulario sigue permitiendo pedir cualquier valor a mano (incluido
  el default real) — la decisión de a qué costo es responsabilidad del usuario en ese caso,
  no algo que la landing page deba forzar. **No se tocó** `SimulationConfig` ni
  `simulation.py` (el motor, y por lo tanto D12, sigue igual — arreglar el O(n²) de fondo
  sigue pendiente y fuera de alcance como ya se había decidido).
- Server reiniciado con el fix: `GET /` responde `200` en <1 s, con el gráfico de cola, la
  fila de cola máxima resaltada y el `<title>` con el resumen — confirmado por `curl`, no
  solo en memoria.
- Server dejado corriendo en background en `http://127.0.0.1:8877/` para que el usuario lo
  recorra interactivamente (form, paginación y todo — a diferencia del snapshot estático,
  acá sí responden).

### Pendiente / próximos pasos
- Sigue pendiente lo de siempre: `SUPUESTOS.md` #1 y #4 con la cátedra.
- El O(n²) de fondo en `simulation.py` sigue sin arreglar — el fix de esta sesión solo evita
  que la landing page lo dispare por accidente; si se pide un run manual con
  `max_iterations` alto y la tasa degenerada, el problema reaparece tal cual estaba.

---

## Sesión 2026-07-21 — SUPUESTOS #1 y #4: decisión final, ya no se espera a la cátedra

### Contexto
El usuario pidió explicación detallada de #1 y #4, y después de entenderlos decidió: en vez de
seguir esperando respuesta de la cátedra, apegarse lo más posible al enunciado tal como está
escrito, aceptando que el resultado sea inestable (#1) o deje vestigial el correctivo (#4) en
vez de reinterpretar el texto para forzar un comportamiento "más razonable".

### Hecho
- **No hizo falta tocar el motor:** tanto `mean_interarrival_time=0.25` (#1) como la ausencia de
  umbral mínimo en `_maybe_trigger_preventive_maintenance` (#4, `simulation.py:149-159`) ya eran
  el default en el código — coincidían con la lectura literal. Confirmado leyendo
  `random_utils.py:40-43` (fórmula `T = -media * ln(1 - RND)`, también ya la default de #3) y
  `simulation.py`.
- **Se cerraron ambos supuestos en `SUPUESTOS.md`:** #1 y #4 pasan de "TODO: confirmar con
  cátedra" a "Decisión final (2026-07-21)", con la justificación de por qué se prioriza el apego
  literal sobre la estabilidad del resultado. El hallazgo empírico de #4 (correctivo vestigial)
  queda documentado como contexto para la defensa oral, no como pregunta abierta.
- Removido el comentario `# TODO: confirmar con cátedra` en `config.py:20` (único lugar del
  código con ese marcador para #1; #4 no tenía uno propio).
- Actualizado "Estado actual" arriba: ya no queda ninguno de los dos como pendiente de cátedra.

### Pendiente / próximos pasos
- Correr el resultado final de "cola máxima" con estos defaults para la entrega.
- El O(n²) de fondo en `simulation.py` sigue sin arreglar y ahora es más relevante: con #1
  decidido en firme (tasa degenerada, no una hipótesis a descartar), cualquier corrida final con
  `max_iterations` alto en el escenario real **va a disparar el problema de rendimiento**, no
  solo en un caso hipotético. Conviene revisarlo antes de generar el resultado de entrega.
