# Prompt para el agente — Aplicativo de Simulación: "Centro de Copiado"

## 0. Rol y objetivo

Sos un agente de desarrollo. Tu tarea es **construir desde cero, en Python**, un aplicativo de
**simulación de eventos discretos** para el problema del "Centro de Copiado" descripto abajo.
El objetivo del TP es **determinar la cola máxima** que se forma, pero el aplicativo debe cumplir
además el formato general de la cátedra (ver §8).

Este trabajo va a ser **defendido oralmente**, por lo que **cada decisión debe quedar
documentada y justificada**. La documentación es tan importante como el código.

---

## 1. ⚠️ REGLAS DE TRABAJO Y DOCUMENTACIÓN (leer primero)

Para no perder contexto entre etapas/sesiones y para poder defender el trabajo, **debés crear y
mantener actualizados** los siguientes archivos `.md` en el repositorio. **No avances a la
siguiente etapa sin actualizar la documentación de la etapa anterior.**

| Archivo | Contenido | Cuándo se actualiza |
|---|---|---|
| `DISEÑO.md` | Modelo completo: objetos, estados, colas, eventos, lógica de mantenimiento, fórmulas. | Al definir el modelo, antes de codear. |
| `DECISIONES.md` | Cada decisión de modelado con su **justificación** (por qué se eligió, alternativas descartadas). Es la base de la defensa. | Cada vez que tomes una decisión. |
| `SUPUESTOS.md` | Supuestos adoptados y **puntos a confirmar con la cátedra** (ver §3). | Al inicio y cuando surja una duda. |
| `PROGRESO.md` | **Bitácora / checkpoint de contexto:** qué se hizo, qué falta, estado actual, próximos pasos. | Al final de **cada etapa** del §9. |
| `README.md` | Cómo instalar y correr, descripción de parámetros, ejemplos. | Al tener la app funcionando. |
| `VALIDACION.md` | Casos de prueba, chequeos de sanidad y resultados esperados. | Al validar. |
| `DEFENSA.md` | Preguntas probables de la defensa con sus respuestas. | Al final. |

**Reglas adicionales:**
- Empezá **leyendo y escribiendo `PROGRESO.md`** al inicio de cada sesión para recuperar contexto.
- Ante cualquier ambigüedad, **NO adivines**: registrala en `SUPUESTOS.md`, adoptá un default
  razonable, dejá un comentario `# TODO: confirmar con cátedra` en el código y seguí.
- Código claro y modular (una clase `Simulacion`, objetos `Copiadora`, un bucle de eventos).
- Todos los parámetros del enunciado deben ser **variables configurables**, no números "quemados".

---

## 2. Enunciado del problema (literal)

> Se poseen 3 máquinas en un centro de copiado. Los clientes llegan de acuerdo con una
> distribución Poisson con media de 4 clientes/minuto. El tiempo que lleva atender a cada cliente
> sigue una distribución exponencial con media de 15 minutos. Cuando un cliente llega y todas las
> copiadoras están ocupadas tiene que esperar en una fila común. Cada 200 horas de uso más menos
> 30 horas, la copiadora necesita una reparación/mantenimiento de 2 horas. En el caso de que las 3
> copiadoras estén libres en un momento dado, se debe realizar el mantenimiento sobre la que esté
> más próxima a fallar (para evitar que luego falle cuando haya clientes). **Determinar la cola
> máxima que se forma en el centro de copiado.**

**Nota:** este problema **NO** tiene ecuaciones diferenciales → **no se usa Runge-Kutta**.

---

## 3. ⚠️ Interpretación y puntos a CONFIRMAR con la cátedra

Registrar estos ítems en `SUPUESTOS.md`. Defaults adoptados:

1. **Unidad de las llegadas (crítico).** "Poisson con media de 4 clientes/minuto" se interpreta
   como tasa λ = 4 por minuto ⇒ **tiempo entre llegadas Exponencial de media 1/4 = 0,25 min**.
   ⚠️ Es una tasa muy alta frente a la capacidad de servicio; **confirmar** si no se quiso decir
   "media de 4 minutos entre clientes" (Exp media 4). Dejar la media como parámetro para poder
   cambiarla en un solo lugar.
2. **Interrupción por mantenimiento.** Default: cuando una copiadora alcanza su umbral de uso, **termina
   de atender al cliente en curso y recién entonces entra a mantenimiento** (no se interrumpe la
   copia). Confirmar si la cátedra quiere que interrumpa.
3. **Fórmula de la exponencial.** Default `T = -media * ln(1 - RND)`. Algunas cátedras usan
   `-media * ln(RND)`. Aislarla en una función.
4. **Regla preventiva.** Default (literal): **siempre que las 3 copiadoras queden libres**, se envía
   a mantenimiento a la más próxima a fallar. Confirmar si debe existir un umbral mínimo de uso
   para dispararla.
5. **Selección de copiadora para un cliente.** Cuando hay varias libres, default: asignar la de
   **mayor uso restante** (la más lejana a fallar), coherente con la intención preventiva. Es un
   supuesto; confirmar.

---

## 4. Consistencia de unidades (IMPORTANTE)

Mezcla de minutos y horas. **Trabajar internamente todo en MINUTOS.**

| Magnitud | Enunciado | En minutos |
|---|---|---|
| Media entre llegadas | 0,25 min (λ=4/min) ⚠️ | 0,25 |
| Media de atención | 15 min | 15 |
| Umbral de mantenimiento | 200 ± 30 h de uso → Uniforme[170; 230] h | Uniforme[10200; 13800] |
| Duración del mantenimiento | 2 h | 120 |

⚠️ "Horas de **uso**" = tiempo en que la copiadora estuvo **efectivamente atendiendo** (estado
Ocupada), **no** el tiempo total transcurrido. Solo se acumula uso mientras atiende.

---

## 5. Modelo de simulación

### 5.1 Objetos y estados

| Objeto | Tipo | Estados |
|---|---|---|
| **Cliente** | Temporal | Esperando atención (en cola) · Siendo atendido |
| **Copiadora** (×3) | Permanente | Libre · Ocupada · En mantenimiento |

Cada **Copiadora** debe guardar además: `uso_restante_hasta_mantenimiento` (min), `umbral_actual`
(min, sorteado), y referencia al cliente en atención / hora de fin.

### 5.2 Colas
- **Cola común** (FIFO): clientes esperando una copiadora libre.

### 5.3 Eventos (solo tipos Llegada y Fin)
- **Llegada de cliente** (Exp media 0,25 min ⚠️).
- **Fin de atención** (Exp media 15 min) — por copiadora.
- **Fin de mantenimiento** (120 min fijos) — por copiadora.
- **Fin de simulación** (evento temporal: tiempo X o 100.000 iteraciones).

El inicio de mantenimiento **no es un evento programado independiente**: se dispara dentro del
procesamiento de otros eventos (ver §6).

### 5.4 Motor de eventos

**Llegada de cliente**
1. Programar la próxima llegada (sortear RND → tiempo entre llegadas → `reloj + t`).
2. Si hay copiadora **Libre** → asignarla (§3.5); estado → Ocupada; sortear tiempo de atención;
   `fin_atencion = reloj + t`. Si no hay libre → el cliente entra a la **cola común**.
3. Actualizar **cola máxima** (§7).

**Fin de atención (copiadora c)**
1. El cliente atendido se retira (se destruye).
2. Acumular uso: `c.uso_restante -= duracion_de_la_atencion`.
3. Si `c.uso_restante <= 0` → la copiadora entra a **mantenimiento** (estado → En mantenimiento;
   `fin_mantenimiento = reloj + 120`). Si no:
   - Si hay clientes en cola → toma el siguiente (FIFO), estado sigue Ocupada, sortea atención.
   - Si la cola está vacía → estado → Libre.
4. Evaluar la **regla preventiva** (§6.2).
5. Actualizar cola máxima.

**Fin de mantenimiento (copiadora c)**
1. `c.umbral_actual = ` nuevo Uniforme[10200; 13800]; `c.uso_restante = c.umbral_actual`.
2. Estado → Libre (o toma cliente de la cola si hubiera).
3. Evaluar la regla preventiva.

---

## 6. Lógica de mantenimiento (el núcleo del problema)

### 6.1 Mantenimiento correctivo (por uso)
Cada copiadora acumula **uso** solo mientras atiende. Se lleva un contador
`uso_restante_hasta_mantenimiento`, inicializado con un Uniforme[10200; 13800] min. Al terminar
cada atención se le resta la duración de esa atención. Cuando llega a `<= 0`, la copiadora entra a
mantenimiento por 120 min; al salir, se sortea un **nuevo umbral** y se reinicia el uso restante.

### 6.2 Mantenimiento preventivo (regla especial)
Cuando, tras procesar un evento, **las 3 copiadoras quedan Libres** al mismo tiempo, se elige la de
**menor `uso_restante`** (la más próxima a fallar) y se la envía a mantenimiento (estado → En
mantenimiento; `fin_mantenimiento = reloj + 120`). Documentar en `DECISIONES.md` el criterio de
desempate y el default de §3.4.

⚠️ Registrar un **contador separado** de mantenimientos **correctivos** vs **preventivos** (sirve
para la defensa y como estadística de apoyo).

---

## 7. Estadística requerida + estadísticas de apoyo

### Requerida por el enunciado
- **Cola máxima:** máximo valor que alcanza la longitud de la cola común durante la simulación.
  Es un acumulador de tipo **máximo**: cada vez que cambia la longitud de la cola, hacer
  `cola_maxima = max(cola_maxima, longitud_actual)`. En el vector de estado, esta columna se lee
  de la **última fila** (es monótona creciente).

### De apoyo (recomendadas para enriquecer y validar; confirmar si la cátedra pide más)
- % de ocupación de cada copiadora (síncrono).
- % de tiempo de cada copiadora en mantenimiento (síncrono o asíncrono por episodio).
- Tiempo promedio de espera en cola (asíncrono; dividir por los clientes que esperaron).
- Cantidad de clientes atendidos.
- Cantidad de mantenimientos correctivos y preventivos.

**Convenciones (heredadas del TP anterior, mantener):** síncrono = suma `Δt = reloj(próximo
evento) − reloj(actual)` según el estado de la fila actual; asíncrono = suma al completarse el
proceso; promedios de cola dividen por los que **efectivamente esperaron**.

---

## 8. Requisitos de la consigna (formato de la cátedra)

- [ ] Simula hasta **100.000 iteraciones** del vector de estado **o** hasta el **tiempo X**, lo que
  ocurra primero.
- [ ] Muestra **`i` iteraciones a partir de la iteración `j`** (i y j por parámetro).
- [ ] Muestra la **última fila** (instante X); en esa fila no hace falta mostrar objetos temporales.
- [ ] **Todos** los parámetros modificables (medias, umbral 200/±30, duración mantenimiento, X, i, j).
- [ ] Vector de estado con el **detalle del sistema** + columnas para calcular las métricas.
- [ ] Para **cada variable aleatoria** se muestra el **RND** usado (llegada, atención, umbral).
- [ ] En cualquier fila del intervalo se pueden ver los **atributos de los objetos presentes**
  (copiadoras y clientes vivos).

---

## 9. Plan de trabajo sugerido (etapas)

1. **Etapa 0 — Documentación base:** crear `SUPUESTOS.md`, `DISEÑO.md`, `DECISIONES.md`,
   `PROGRESO.md`. Volcar §3, §5, §6.
2. **Etapa 1 — Esqueleto:** clase `Simulacion`, objetos `Copiadora`, parámetros configurables,
   generadores de aleatorios (Exp, Uniforme) aislados. Actualizar `PROGRESO.md`.
3. **Etapa 2 — Motor de eventos:** llegadas, fin de atención, cola común, asignación. Sin
   mantenimiento todavía. Validar que corre y que la cola máxima tiene sentido.
4. **Etapa 3 — Mantenimiento correctivo:** contador de uso y disparo por umbral.
5. **Etapa 4 — Mantenimiento preventivo:** regla de las 3 libres + contadores separados.
6. **Etapa 5 — Vector de estado y visualización:** filas i desde j, última fila, RND por variable,
   objetos temporales.
7. **Etapa 6 — Estadísticas:** cola máxima + apoyo. Chequeos de sanidad en `VALIDACION.md`.
8. **Etapa 7 — Cierre:** `README.md`, `DEFENSA.md`, repaso de `DECISIONES.md`.

Actualizar `PROGRESO.md` **al terminar cada etapa**.

---

## 10. Criterios de aceptación (Definition of Done)

- [ ] Calcula la **cola máxima** correctamente.
- [ ] Corre hasta 100.000 iteraciones o hasta X sin errores.
- [ ] Consistencia de unidades verificada (todo en minutos).
- [ ] Mantenimiento correctivo y preventivo funcionando, con contadores separados.
- [ ] `i, j`, última fila, RND por variable y objetos temporales visibles.
- [ ] Todos los parámetros configurables.
- [ ] **Documentación `.md` completa y actualizada** (los 7 archivos del §1).
- [ ] Caso de prueba reproducible (semilla fija) documentado en `VALIDACION.md`.

---

> **Recordatorio final:** la calidad de la **documentación** (`DECISIONES.md`, `DISEÑO.md`,
> `DEFENSA.md`) es parte del entregable, porque este TP se defiende oralmente. Documentá el
> *porqué* de cada decisión, no solo el *qué*.
