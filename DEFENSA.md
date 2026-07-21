# Defensa oral — preguntas probables y respuestas

Preparado para la defensa oral del TP. Cada respuesta referencia el documento donde está el
detalle completo, para poder profundizar en vivo si hace falta.

---

## Modelo general

**¿Por qué eligieron trabajar todo en minutos?**
El enunciado mezcla minutos (llegadas, atención) y horas (mantenimiento: 200±30 h, 2 h). Convertir
todo a una sola unidad desde el arranque evita bugs de "factor 60" y permite sumar/comparar
tiempos del reloj de simulación directamente. Detalle: `DISEÑO.md` §4, `DECISIONES.md` D1.

**¿Por qué el modelo tiene solo 3 tipos de evento programado (Llegada, Fin de atención, Fin de
mantenimiento) y no uno de "inicio de mantenimiento"?**
Porque el inicio de mantenimiento (correctivo o preventivo) es una decisión instantánea que se
toma *dentro* del procesamiento de otro evento — no requiere esperar un tiempo adicional, así que
programarlo como evento aparte sería redundante. Detalle: `DISEÑO.md` §5.3, `DECISIONES.md` D3.

**¿Qué es un "objeto temporal" y por qué el Cliente lo es?**
Un objeto temporal existe solo durante parte de la simulación (un Cliente vive desde que llega
hasta que termina de ser atendido) y se descarta después, sin dejar registro individual — solo
contadores agregados (clientes atendidos, suma de esperas). La Copiadora es un objeto permanente:
existe toda la corrida. Detalle: `DISEÑO.md` §3, `DECISIONES.md` D5.

---

## Números aleatorios

**¿Cómo generan los tiempos entre llegadas y de atención?**
Por el método de la transformada inversa: `T = -media * ln(1 - RND)`, con `RND` uniforme en
[0,1). Es la fórmula estándar de la cátedra; matemáticamente equivalente a `-media * ln(RND)`
porque `RND` y `1-RND` tienen la misma distribución. Está aislada en
`RandomGenerator.exponential()` para poder cambiarla en un solo lugar. Detalle: `SUPUESTOS.md` #3,
`src/copy_center/random_utils.py`.

**¿Qué generador de números aleatorios usan? ¿Es el que pide la cátedra?**
`random.Random(seed)` de Python (Mersenne Twister), con semilla configurable. Es un supuesto sin
confirmar: si la cátedra exige un generador congruencial propio, alcanza con reemplazar el método
`uniform01()` de `RandomGenerator` — el resto del modelo no cambia. Detalle: `SUPUESTOS.md` #7.

**¿Cómo garantizan que la simulación sea reproducible?**
Cada corrida usa una única instancia de `RandomGenerator` con una semilla fija (no se toca el
estado global de `random`). Correr dos veces con los mismos parámetros y la misma semilla da
resultados idénticos — verificado en varias etapas (`PROGRESO.md`, `VALIDACION.md` #15). Detalle:
`DECISIONES.md` D7, D10.

**¿Cómo se ve en el vector de estado el RND de cada variable?**
Cada fila (`StateRow`) guarda el `Draw` (RND crudo + valor sorteado) de la llegada, la atención y
el/los umbral(es) que intervinieron en ese evento puntual. Incluso el estado inicial (t=0, umbral
de las 3 copiadoras + primera llegada) queda registrado como fila `INICIO`. Detalle: `DISEÑO.md`
§9, `DECISIONES.md` D14.

---

## Mantenimiento

**¿Por qué no interrumpen la atención cuando el uso llega al umbral?**
Porque el enunciado no menciona una interrupción, y el motor solo tiene los 3 tipos de evento ya
mencionados — partir "fin de atención" en dos requeriría un evento adicional no contemplado. Por
eso `usage_remaining` puede quedar negativo momentáneamente: se termina el cliente en curso y
*recién entonces* la copiadora entra a mantenimiento. Es un supuesto sin confirmar. Detalle:
`SUPUESTOS.md` #2.

**¿Cómo deciden qué copiadora atiende a un cliente que llega, si hay varias libres?**
Se asigna la de **mayor** `usage_remaining` (la más lejana a fallar), para reservar "fresca" a la
que más se va a necesitar y minimizar la chance de que falle en medio de una atención larga con
gente esperando. Es coherente con la lógica preventiva del problema, pero es un supuesto (el
enunciado no lo especifica). Detalle: `SUPUESTOS.md` #5.

**¿Y para la regla preventiva, cómo eligen a cuál mandar a mantenimiento?**
La de **menor** `usage_remaining` entre las 3 (la más próxima a fallar) — lectura literal del
enunciado ("se debe realizar el mantenimiento sobre la que esté más próxima a fallar"). Detalle:
`DISEÑO.md` §8.2.

**¿Cuándo se evalúa la regla preventiva? ¿Se chequea todo el tiempo?**
No: se evalúa únicamente al final del procesamiento de un evento *Fin de atención* o *Fin de
mantenimiento* — son los únicos puntos donde una copiadora puede pasar a estar Libre y por lo
tanto donde "las 3 libres a la vez" puede volverse cierto por primera vez. Nunca se evalúa desde
una Llegada (solo puede reducir la cantidad de libres) ni contra el estado inicial en t=0 (las 3
arrancan libres por default, pero eso no es una transición). Detalle: `DISEÑO.md` §7.4.

**Encontramos que en sus pruebas el mantenimiento correctivo casi nunca se dispara. ¿Por qué?**
Es un hallazgo real, no un bug: sin umbral mínimo para la regla preventiva (lectura literal del
enunciado), las copiadoras son enviadas a mantenimiento preventivo mucho antes de acumular las
10.200-13.800 min de uso necesarias para un correctivo. En una prueba con carga moderada
(ρ≈0,83), la regla preventiva se disparó 353 veces contra **0** correctivos. Está documentado
como uno de los dos puntos más importantes para confirmar con la cátedra (junto con la tasa de
llegadas). Detalle: `SUPUESTOS.md` #4, `VALIDACION.md` §3.

---

## Estadísticas

**¿Qué es la cola máxima y cómo la calculan?**
Es un acumulador de tipo máximo: cada vez que la longitud de la cola común cambia (se encola o se
desencola un cliente), se actualiza `max_queue_length = max(max_queue_length, len(cola))`. Al ser
monótona creciente, el resultado final se lee directamente de la última fila del vector de
estado — verificado que nunca decrece en las ~50.000 filas de la corrida de validación. Detalle:
`DISEÑO.md` §10.1, `VALIDACION.md` #5-6.

**¿Qué diferencia hay entre una estadística síncrona y una asíncrona? Denme un ejemplo de cada
una del código.**
Síncrona: se acumula un `Δt` (tiempo transcurrido) ponderado por el estado vigente durante ese
intervalo — ejemplo: `% ocupación` de una copiadora, que suma el tiempo que estuvo en estado
Ocupada cada vez que cambia de estado (`Simulation._change_copier_state`). Asíncrona: se acumula
un valor puntual en el instante en que un proceso se completa — ejemplo: el tiempo de espera en
cola, que se suma una sola vez, cuando el cliente *empieza* a ser atendido (`_assign_client`), no
durante todo el tiempo que esperó. Detalle: `DISEÑO.md` §10.2, `DECISIONES.md` D15.

**¿Cómo verificaron que el % de ocupación/mantenimiento está bien calculado?**
Con un chequeo cruzado independiente: una subclase de prueba registra cada apertura/cierre de
intervalo de estado por fuera del código de producción, y al recalcular `busy_time`/
`maintenance_time` desde esos intervalos, coincidió exactamente (diferencia 0) con los
acumuladores reales sobre ~30.000 intervalos. También se verificó que
`ocupada% + mantenimiento% + libre% = 100%` para las 3 copiadoras. Detalle: `VALIDACION.md` §2
(chequeos 10-13).

---

## Validación y confiabilidad

**¿Cómo saben que el motor de eventos está bien implementado?**
Con validación incremental etapa por etapa (no solo al final): en cada etapa se corrieron
escenarios con distinta carga (saturado, moderado, estable) y se revisaron invariantes concretas
(p. ej. que ninguna copiadora en mantenimiento tenga un cliente asignado, que `usage_remaining <=
usage_threshold`, que la cantidad de eventos `Fin de mantenimiento` coincida exactamente con la
suma de correctivos + preventivos). Detalle: `PROGRESO.md` (bitácora completa) y `VALIDACION.md`.

**¿Tienen un caso de prueba fijo que dé siempre el mismo resultado?**
Sí: `seed=42`, `mean_interarrival_time=6`, `max_iterations=50000` da cola máxima = 35, 0
correctivos, 353 preventivos, siempre exactamente igual. Sirve como test de regresión: si un
cambio futuro altera estos números sin querer, es señal de que se rompió algo (probablemente el
orden o la cantidad de sorteos aleatorios). Detalle: `VALIDACION.md` §1.

---

## Supuestos y límites del modelo

**¿Cuáles son los supuestos más importantes que quedaron sin confirmar?**
Dos, ambos marcados ⚠️ en `SUPUESTOS.md`:
1. **#1 — Tasa de llegadas:** "4 clientes/minuto" tomado literalmente satura completamente el
   sistema (ρ≈20); podría ser una redacción confusa de "1 cada 4 minutos" (ρ≈1,25).
2. **#4 — Umbral mínimo de la regla preventiva:** sin umbral mínimo, el mecanismo preventivo
   domina por completo al correctivo (ver pregunta anterior sobre mantenimiento).

Ambos cambian drásticamente el valor final de "cola máxima", así que el resultado que se reporte
como entrega definitiva debe correrse después de resolverlos.

**Si tuvieran que agregar una cuarta copiadora, ¿cuánto código tendrían que tocar?**
Ninguno del motor: `n_copiers` es un parámetro de `SimulationConfig`, las copiadoras se crean en
un loop (`[self._new_copier(i) for i in range(config.n_copiers)]`), y toda la lógica de selección
(`_select_free_copier`, `_maybe_trigger_preventive_maintenance`) itera sobre `self.copiers` sin
asumir que son 3. Solo cambiaría el ancho de la tabla del vector de estado (columnas por
copiadora), que también se genera dinámicamente en `report.py`. Detalle: `DECISIONES.md` D9.

**¿Por qué la cola común no aparece detallada (cliente por cliente) en la tabla del vector de
estado?**
Porque a diferencia de las copiadoras (cantidad fija, 3), la cola no tiene tamaño acotado — en
escenarios saturados llegó a superar los 18.000 clientes en espera. Una columna por cliente sería
inviable. La longitud de la cola sí se muestra siempre; el detalle de clientes vivos de una fila
puntual está disponible aparte (`report.format_queue_detail`). Detalle: `DECISIONES.md` D12.
