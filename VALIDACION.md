# Validación

Casos de prueba, chequeos de sanidad y resultados esperados. Complementa la validación manual ya
registrada etapa por etapa en `PROGRESO.md`: acá se consolida el **caso de prueba reproducible**
exigido por el Definition of Done (§10 del prompt) y los chequeos de sanidad más importantes, con
sus resultados exactos.

---

## 1. Caso de prueba reproducible (semilla fija)

**Parámetros** (el resto queda en los defaults de `SimulationConfig`):

```python
from copy_center.config import SimulationConfig
from copy_center.simulation import Simulation

cfg = SimulationConfig(max_iterations=50_000, mean_interarrival_time=6.0, seed=42)
sim = Simulation(cfg)
sim.run()
```

Con `mean_interarrival_time=6` (ρ≈0,83, en vez del default literal de SUPUESTOS.md #1) para tener
un escenario cargado pero no degenerado — el default literal (λ=4/min) satura el sistema tan rápido
que 50.000 iteraciones no alcanzan ni a completar 1200 minutos simulados (ver §3 más abajo), lo que
lo hace poco útil como caso de regresión.

**Resultado esperado (exacto, con `seed=42`):**

| Métrica | Valor |
|---|---|
| Iteración final | 50.000 |
| Reloj final | 149134.3687 min |
| Cola máxima | **35** |
| Clientes atendidos | 24.821 |
| Mantenimientos correctivos | 0 |
| Mantenimientos preventivos | 353 |
| Espera promedio (de los 20.625 que esperaron) | 35.5293 min |
| Copiadora 0 — ocupada / mantenimiento / libre | 83,61% / 8,69% / 7,70% |
| Copiadora 1 — ocupada / mantenimiento / libre | 82,25% / 9,90% / 7,85% |
| Copiadora 2 — ocupada / mantenimiento / libre | 82,15% / 9,82% / 8,03% |

Cualquier corrida con los mismos parámetros y `seed=42` debe reproducir estos valores
exactamente (DECISIONES.md D7). Si algún refactor futuro cambia estos números sin que haya
cambiado el modelo a propósito, es señal de una regresión (alteró el orden/cantidad de sorteos de
`RandomGenerator`).

**Nota:** `correctivos=0` no es un error — es el hallazgo ya documentado en SUPUESTOS.md #4: sin
umbral mínimo, la regla preventiva se adelanta y el mantenimiento correctivo casi no llega a
dispararse en cargas moderadas/bajas.

---

## 2. Chequeos de sanidad (todos verificados sobre el caso de arriba)

| # | Chequeo | Resultado |
|---|---|---|
| 1 | `len(state_vector) == iteration + 1` (la fila extra es `INIT`) | OK (50.001 filas) |
| 2 | La fila `INIT` tiene exactamente 3 draws de umbral (uno por copiadora) y 1 de llegada | OK |
| 3 | Todo RND ∈ [0, 1) | OK |
| 4 | Todo umbral sorteado ∈ [10200, 13800] | OK |
| 5 | `max_queue_length` es monótona creciente fila a fila en todo el vector de estado | OK (verificado en las 50.001 filas) |
| 6 | `state_vector[-1].max_queue_length == sim.max_queue_length` (cola máxima se lee de la última fila) | OK |
| 7 | Cantidad de filas `SERVICE_END` == `clients_served` | OK (24.821 == 24.821) |
| 8 | Cantidad de filas `MAINTENANCE_END` == `correctivos + preventivos` | OK (353 == 0 + 353) |
| 9 | `INIT(1) + ARRIVAL + SERVICE_END + MAINTENANCE_END == iteración final + 1` | OK (1 + 24.826 + 24.821 + 353 = 50.001) |
| 10 | Para cada copiadora: `ocupada% + mantenimiento% + libre% = 100%` (con el clamp de `copier_stats`) | OK, diferencia < 1e-6 en las 3 |
| 11 | Para cada copiadora, **sin** clamp: `busy_time + maintenance_time <= total_time` | OK |
| 12 | `maintenance_time` de cada copiadora es múltiplo exacto de 120 min (duración fija) | OK (12960=108×120, 14760=123×120, 14640=122×120; 108+123+122=353 preventivos) |
| 13 | Recálculo **independiente** de `busy_time`/`maintenance_time` por intervalos (subclase de auditoría que registra cada apertura/cierre de intervalo) coincide exactamente con los acumuladores de producción | OK, diferencia = 0.00e+00 en las 3 copiadoras (29.729 intervalos) |
| 14 | `espera_promedio >= 0` | OK (35.53 min) |
| 15 | Reproducibilidad: dos corridas independientes con el mismo `seed` dan resultados idénticos | OK, verificado en Etapas 1, 3, 4 y 5 |
| 16 | `usage_remaining <= usage_threshold` para las 3 copiadoras en todo momento | OK (Etapa 3) |
| 17 | Ninguna copiadora en `MAINTENANCE` tiene `current_client` seteado | OK |
| 18 | Todo disparo preventivo ocurre con las 3 copiadoras realmente `FREE`, y se elige la de menor `usage_remaining` | OK, verificado con subclase de instrumentación (Etapa 4) |

El chequeo #13 es el más fuerte: no compara el resultado contra sí mismo, sino contra un cálculo
completamente independiente (una bitácora de intervalos abiertos/cerrados llevada por fuera de
`_change_copier_state`), así que descarta bugs de doble conteo o de intervalos no cerrados.

---

## 3. Escenarios exploratorios (evidencia para SUPUESTOS.md, no regresión formal)

Estos no son casos de regresión (no se congeló un resultado exacto) sino corridas usadas para
entender el comportamiento del modelo y respaldar los puntos ⚠️ de `SUPUESTOS.md`:

| Escenario | `mean_interarrival_time` | ρ aprox. | Resultado |
|---|---|---|---|
| Default literal del enunciado (SUPUESTOS #1) | 0.25 | ≈20 | Sistema totalmente saturado: con 5.000 iteraciones la cola ya alcanza ~4500 y el reloj apenas llega a ~1168 min. Con 20.000 iteraciones, 0 correctivos y 0 preventivos (no da tiempo a que se den las condiciones de ninguno de los dos mecanismos). |
| Interpretación alternativa (1 cliente cada 4 min) | 4.0 | ≈1.25 | También saturado pero mucho más gradual (cola máxima ≈525 en 5.000 iteraciones). |
| Baja carga | 30.0 | ≈0.17 | Cola máxima muy baja (≈4-6), pero **5201 preventivos vs. 0 correctivos** en 50.000 iteraciones — el hallazgo más fuerte para SUPUESTOS.md #4. |
| Estable | 20.0 | ≈0.25 | Cola máxima = 4, la mayoría de los clientes no espera. |

---

## 4. Qué falta validar

- [ ] Una vez confirmados con la cátedra los puntos de `SUPUESTOS.md` #1 y #4, congelar un caso de
  prueba reproducible con los parámetros **finales** (no los usados acá solo para poder validar el
  motor) y ese sí reportarlo como el resultado oficial del TP.
- [ ] Validar el comportamiento de `end_time` (parámetro X) una vez que se defina un valor concreto
  para la entrega (SUPUESTOS.md #9).
- [ ] Revisar manualmente `i`/`j` y el formato de salida (`report.render_full_report`) contra lo que
  pida la cátedra en la corrección, una vez que haya CLI/`README.md` (Etapa 7).

---

*Última actualización: 2026-07-17 — Etapa 6.*
