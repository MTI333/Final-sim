# Diseño — Simulación Centro de Copiado

Modelo completo del sistema: parámetros, objetos, estados, colas, eventos, fórmulas de variables
aleatorias, lógica de mantenimiento, columnas del vector de estado, estadísticas y arquitectura de
código propuesta. Este documento se escribe **antes** de codear (Etapa 0) y se actualiza si el
modelo cambia en etapas posteriores.

---

## 1. Resumen del problema

3 copiadoras atienden clientes que llegan según un proceso de Poisson. Si las 3 están ocupadas, el
cliente espera en una cola común FIFO. Cada copiadora requiere mantenimiento correctivo cada
~200±30 horas de **uso efectivo** (no de tiempo transcurrido). Si en algún momento las 3 quedan
libres a la vez, se aprovecha para mandar preventivamente a mantenimiento a la que esté más cerca
de necesitarlo. Objetivo: la **cola máxima** alcanzada durante la simulación.

Es un problema de simulación de eventos discretos puro (sin ecuaciones diferenciales): todo se
resuelve con el método de próximo evento (next-event time advance).

---

## 2. Unidades y parámetros

**Toda la simulación trabaja internamente en minutos.**

| Parámetro | Símbolo / nombre | Enunciado | Valor en minutos | Configurable |
|---|---|---|---|---|
| Media entre llegadas | `mean_interarrival_time` | 4 clientes/min ⚠️ (ver SUPUESTOS #1) | 0,25 | Sí |
| Media de atención | `mean_service_time` | 15 min | 15 | Sí |
| Umbral de mantenimiento (mín.) | `maintenance_threshold_min` | 200−30 = 170 h | 10200 | Sí |
| Umbral de mantenimiento (máx.) | `maintenance_threshold_max` | 200+30 = 230 h | 13800 | Sí |
| Duración del mantenimiento | `maintenance_duration` | 2 h | 120 | Sí |
| Cantidad de copiadoras | `n_copiers` | 3 | — | Sí |
| Tope de iteraciones | `max_iterations` | 100.000 | — | Sí |
| Tiempo límite de simulación | `end_time` (X) | no especificado | a definir | Sí |
| Fila inicial a mostrar | `j` | — | — | Sí |
| Cantidad de filas a mostrar | `i` | — | — | Sí |
| Semilla del generador aleatorio | `seed` | — | — | Sí |

Ningún valor va "quemado" en la lógica: todos viven en un único objeto/archivo de configuración
(ver §8 Arquitectura).

**Nota sobre "horas de uso":** es tiempo en que la copiadora estuvo efectivamente en estado
Ocupada (atendiendo), no tiempo transcurrido total. El contador de uso **no** avanza mientras la
copiadora está Libre o En mantenimiento.

---

## 3. Objetos y estados

### 3.1 Cliente (objeto temporal)

| Atributo | Descripción |
|---|---|
| `id` | identificador secuencial |
| `arrival_time` | instante de llegada (reloj de simulación) |
| `service_start_time` | instante en que empieza a ser atendido (None mientras espera) |

Estados: **Esperando** (en cola) → **Siendo atendido** → se destruye al finalizar la atención (no
se conserva historial individual; ver DECISIONES.md D5).

### 3.2 Copiadora (objeto permanente, × 3)

| Atributo | Descripción |
|---|---|
| `id` | 0, 1, 2 |
| `state` | `FREE` \| `BUSY` \| `MAINTENANCE` |
| `usage_threshold` | umbral sorteado ~ Uniforme[10200; 13800] (min de uso hasta el próximo correctivo) |
| `usage_remaining` | minutos de uso que le quedan antes de disparar mantenimiento correctivo |
| `current_client` | referencia al cliente en atención (o None) |
| `busy_until` / `maintenance_until` | instante programado de fin del evento actual |

Estados posibles: **Libre** · **Ocupada** · **En mantenimiento**.

---

## 4. Colas

- **Cola común (FIFO):** clientes esperando a que se libere alguna copiadora. Estructura tipo
  `deque`. No hay prioridades entre clientes (enunciado dice "fila común" sin distinción).

---

## 5. Eventos

Solo hay **eventos programados** de estos tipos (se guardan en una lista/heap de eventos futuros
ordenada por tiempo):

| Evento | Se programa cuando | Distribución |
|---|---|---|
| **Llegada de cliente** | al procesar cualquier llegada, se programa la siguiente | Exponencial(media=0,25 min) ⚠️ |
| **Fin de atención** (por copiadora) | al asignarle un cliente a una copiadora | Exponencial(media=15 min) |
| **Fin de mantenimiento** (por copiadora) | al entrar una copiadora a mantenimiento | Fija, 120 min |
| **Fin de simulación** | al arrancar la corrida | tiempo fijo = `end_time` (o corte por `max_iterations`) |

El **inicio** de un mantenimiento (correctivo o preventivo) **no es un evento programado
independiente**: se decide dentro del procesamiento de los eventos de arriba (ver §6).

---

## 6. Fórmulas de variables aleatorias

Todas parten de `RND ~ Uniforme(0,1)` (ver SUPUESTOS #7 sobre el generador a usar).

- **Tiempo entre llegadas:** `t = -mean_interarrival_time * ln(1 - RND)`
- **Tiempo de atención:** `t = -mean_service_time * ln(1 - RND)`
- **Umbral de mantenimiento correctivo:** `umbral = a + RND * (b - a)`, con `a=10200`, `b=13800`
  (Uniforme[a,b])
- **Duración de mantenimiento:** fija, `120` (no aleatoria, no consume RND)

Ambas fórmulas (exponencial y uniforme) se aíslan en funciones puras que devuelven **tanto el
valor sorteado como el RND crudo usado**, porque el vector de estado (§8 del prompt) exige mostrar
el RND de cada variable aleatoria.

---

## 7. Motor de eventos (lógica por tipo)

### 7.1 Llegada de cliente
1. Programar la próxima llegada: sortear RND → tiempo entre llegadas → `next_arrival = clock + t`.
2. Si hay alguna copiadora **Libre** → asignarla (criterio SUPUESTOS #5: mayor `usage_remaining`
   entre las libres); estado → Ocupada; sortear tiempo de atención; `busy_until = clock + t`.
   Si no hay ninguna libre → el cliente entra al final de la **cola común**.
3. Actualizar `max_queue_length = max(max_queue_length, len(queue))`.

### 7.2 Fin de atención (copiadora `c`)
1. El cliente atendido se retira (se destruye, no se conserva).
2. `c.usage_remaining -= duración_de_esa_atención`.
3. Si `c.usage_remaining <= 0` → la copiadora entra a **mantenimiento correctivo**: estado →
   En mantenimiento; `maintenance_until = clock + 120`; incrementar contador de correctivos.
   Si no:
   - Si hay clientes en la cola común → toma el siguiente (FIFO), sigue Ocupada, sortea nueva
     atención.
   - Si la cola está vacía → estado → Libre.
4. Evaluar la **regla preventiva** (§7.4) — puede disparar un mantenimiento sobre *otra*
   copiadora si las 3 quedaron libres tras este paso.
5. Actualizar `max_queue_length` (por si se desencoló un cliente).

### 7.3 Fin de mantenimiento (copiadora `c`)
1. Sortear nuevo `usage_threshold` ~ Uniforme[10200; 13800]; `usage_remaining = usage_threshold`.
2. Estado → Libre, o si hay clientes esperando en la cola común, toma al siguiente y pasa a
   Ocupada directamente (sortea atención).
3. Evaluar la regla preventiva.

### 7.4 Regla preventiva (evaluada al final de 7.2 y 7.3)
Si **las 3 copiadoras están en estado Libre simultáneamente** en ese instante, elegir la de
**menor `usage_remaining`** (más próxima a fallar; desempate por SUPUESTOS #6) y mandarla a
mantenimiento: estado → En mantenimiento; `maintenance_until = clock + 120`; incrementar contador
de preventivos.

---

## 8. Lógica de mantenimiento (núcleo del problema)

### 8.1 Correctivo (por uso)
Cada copiadora acumula uso **solo mientras atiende**. Arranca con `usage_remaining =
usage_threshold` (sorteado). Al terminar cada atención se descuenta la duración de esa atención.
Cuando llega a `<= 0`, entra a mantenimiento por 120 min; al salir, se sortea un nuevo umbral y se
reinicia `usage_remaining`.

### 8.2 Preventivo (regla especial)
Disparada exclusivamente por el evento "las 3 copiadoras Libres a la vez" (sin umbral mínimo, ver
SUPUESTOS #4). Elige la copiadora de menor `usage_remaining` de las 3.

### 8.3 Contadores
Se llevan **dos contadores separados**: `corrective_maintenance_count` y
`preventive_maintenance_count`. Requisito explícito del prompt (§6.2) para la defensa oral.

---

## 9. Vector de estado — columnas a mostrar

Por cada fila (= evento procesado):

- Iteración / número de evento.
- Reloj de simulación (instante del evento).
- Tipo de evento procesado.
- RND y valor sorteado de cada variable aleatoria que intervino en ese evento (llegada, atención,
  umbral — según corresponda).
- Estado de cada copiadora (Libre/Ocupada/Mantenimiento), su `usage_remaining` y su cliente actual
  si aplica.
- Longitud actual de la cola común.
- Columna acumulador `max_queue_length` (monótona creciente; en la **última fila** se lee el
  resultado final).
- Columnas de apoyo necesarias para las estadísticas de §10 (acumuladores síncronos/asíncronos).

En filas intermedias del rango `[j, j+i)` se muestran los objetos temporales vivos (clientes en
cola/en atención); en la **última fila** no hace falta mostrarlos (§8 del prompt).

---

## 10. Estadísticas

### 10.1 Requerida por el enunciado
- **Cola máxima:** acumulador tipo máximo. `max_queue_length = max(max_queue_length,
  len(queue))`, evaluado cada vez que la longitud de la cola cambia (al encolar en 7.1, al
  desencolar en 7.2/7.3). Se lee de la última fila del vector de estado.

### 10.2 De apoyo
- **% ocupación por copiadora** (síncrono): `tiempo_acumulado_Ocupada / tiempo_total_transcurrido`.
- **% tiempo en mantenimiento por copiadora** (síncrono):
  `tiempo_acumulado_Mantenimiento / tiempo_total_transcurrido`.
- **Tiempo promedio de espera en cola** (asíncrono): se acumula
  `service_start_time - arrival_time` en el momento en que el cliente **empieza** a ser atendido;
  se divide por la cantidad de clientes que efectivamente esperaron (espera > 0), no por el total
  de clientes atendidos.
- **Cantidad de clientes atendidos:** contador incrementado en cada Fin de atención.
- **Cantidad de mantenimientos correctivos / preventivos:** contadores separados (§8.3).

**Convenciones (heredadas del TP anterior de la cátedra):**
- *Síncrono:* se acumula `Δt = reloj(próximo evento) − reloj(evento actual)` multiplicado por el
  estado vigente durante ese intervalo.
- *Asíncrono:* se acumula un valor puntual en el instante en que el proceso se completa.
- Los promedios relacionados con la cola dividen por los clientes que **efectivamente esperaron**,
  no por el total.

---

## 11. Arquitectura de código propuesta (para Etapa 1)

- **`SimulationConfig`**: dataclass con todos los parámetros de §2. Único lugar donde viven los
  valores; nada de números "quemados" en la lógica.
- **`Simulation`**: reloj, heap/lista de eventos futuros ordenada por tiempo, lista de 3
  `Copier`, cola común (`deque` de `Client`), acumuladores estadísticos, vector de estado
  (lista de filas), bucle principal (`run()`), un método `process_event()` por tipo de evento.
- **`Copier`**: id, `state` (enum `FREE`/`BUSY`/`MAINTENANCE`), `usage_threshold`,
  `usage_remaining`, `current_client`.
- **`Client`**: id, `arrival_time`, `service_start_time`.
- **`Event`**: tipo (`ARRIVAL`/`SERVICE_END`/`MAINTENANCE_END`/`SIMULATION_END`), tiempo,
  referencia opcional a copiadora/cliente.
- Funciones puras de generación aleatoria aisladas: `rnd()`, `exponential(mean)`,
  `uniform(a, b)` — cada una devuelve `(valor, rnd_usado)`.

Identificadores de código en inglés, documentación en español (ver DECISIONES.md D8 para la tabla
de correspondencia de términos español↔inglés).

---

*Última actualización: 2026-07-17 — Etapa 0 (documentación base). Se revisa si el modelo cambia en
etapas posteriores.*
