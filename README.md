# Centro de Copiado — Simulación de eventos discretos

TP de Simulación: 3 copiadoras, clientes que llegan según Poisson, atención exponencial, cola
común, mantenimiento correctivo por uso y mantenimiento preventivo cuando las 3 copiadoras quedan
libres a la vez. Objetivo: determinar la **cola máxima**. Ver `DISEÑO.md` para el modelo completo.

## Requisitos

- Python 3.10+ (probado con 3.12).
- Sin dependencias externas — solo librería estándar.

## Cómo correr

Desde la raíz del proyecto:

```bash
PYTHONPATH=src python3 -m copy_center --seed 42 --mean-interarrival-time 6.0 \
  --max-iterations 50000 --report-from 0 --report-rows 20
```

(`python -m copy_center.cli ...` funciona igual). Sin argumentos usa los defaults de
`SimulationConfig` (ver tabla abajo):

```bash
PYTHONPATH=src python3 -m copy_center
```

Para ver todos los parámetros disponibles:

```bash
PYTHONPATH=src python3 -m copy_center --help
```

## Parámetros

| Flag | Default | Significado |
|---|---|---|
| `--n-copiers` | 3 | Cantidad de copiadoras |
| `--mean-interarrival-time` | 0.25 | Media del tiempo entre llegadas (min). ⚠️ Ver `SUPUESTOS.md` #1 |
| `--mean-service-time` | 15.0 | Media del tiempo de atención (min) |
| `--maintenance-threshold-min` | 10200 | Umbral de mantenimiento correctivo, extremo inferior (min de uso; 170 h) |
| `--maintenance-threshold-max` | 13800 | Umbral de mantenimiento correctivo, extremo superior (min de uso; 230 h) |
| `--maintenance-duration` | 120 | Duración fija del mantenimiento (min; 2 h) |
| `--max-iterations` | 100000 | Tope de iteraciones |
| `--end-time` | sin límite | Tiempo límite X (min). El corte real es `min(max_iterations, X)` |
| `--report-from` | 0 | Iteración `j` desde la que se muestran filas |
| `--report-rows` | 50 | Cantidad de filas `i` a mostrar desde `j` |
| `--seed` | 12345 | Semilla del generador aleatorio (reproducibilidad) |

Todos los valores del enunciado son parámetros — nada está "quemado" en la lógica (ver
`DECISIONES.md` D9).

## Salida

El programa imprime:

1. El **vector de estado**: `i` filas a partir de la iteración `j`, una fila por evento
   procesado. Cada fila muestra el reloj, el tipo de evento, el RND y el valor sorteado de cada
   variable aleatoria involucrada (llegada / atención / umbral), el estado de cada copiadora
   (Libre / Ocupada / Manten, uso restante, cliente en atención) y los acumuladores (cola actual,
   cola máxima, clientes atendidos, mantenimientos correctivos/preventivos).
2. La **última fila** (el instante final de la corrida), sin mostrar los ids de cliente en
   atención (objetos temporales — DISEÑO.md §9).
3. Un **resumen final**: cola máxima, clientes atendidos, espera promedio, contadores de
   mantenimiento y % de tiempo ocupada / en mantenimiento / libre de cada copiadora.

Ejemplo (extracto, con `--seed 42 --mean-interarrival-time 6 --max-iterations 30 --report-rows 3`):

```
Vector de estado — filas 0 a 2 de 30 (iteración final=30, reloj final=79.87 min)
Iter | Reloj | Evento | RND_lleg | T_lleg | ... | Cop0_Estado | Cop0_UsoRest | Cop0_Cliente | ...
0 | 0.00 | INICIO | 0.2484 | 1.43 | ... | LIBRE | 11654.3 | - | ...
1 | 1.43 | LLEGADA | 0.7599 | 7.13 | ... | OCUPADA | 11654.3 | 0 | ...
2 | 4.32 | FIN_ATENCION | - | - | ... | LIBRE | 11651.4 | - | ...

...

Resumen de la corrida
  Tiempo total simulado: 79.87 min
  Cola máxima: 6
  Clientes atendidos: 11
  ...
```

La cola común **no** se enumera cliente por cliente en la tabla (no tiene tamaño acotado — llegó a
superar 18.000 clientes en escenarios de prueba saturados); solo se muestra su longitud. El
detalle de los clientes vivos en la cola de una fila puntual está disponible programáticamente vía
`report.format_queue_detail(row)` (DECISIONES.md D12).

## Estructura del proyecto

```
src/copy_center/
  config.py         SimulationConfig: todos los parámetros (DISEÑO.md §2)
  random_utils.py    Generador de aleatorios: exponencial, uniforme (SUPUESTOS.md #3, #7)
  entities.py        Client, Copier, CopierState
  events.py          Event, EventType
  state_vector.py    StateRow, CopierSnapshot, ClientSnapshot (una fila = una iteración)
  statistics.py       SimulationSummary, CopierStats (resumen final)
  simulation.py       Simulation: el motor de eventos completo (DISEÑO.md §7)
  report.py          Presentación en texto del vector de estado y del resumen (español)
  cli.py             Interfaz de línea de comandos
  __main__.py        Permite `python -m copy_center`
```

## Documentación del TP

Este trabajo se defiende oralmente — la documentación es tan importante como el código:

| Archivo | Contenido |
|---|---|
| `DISEÑO.md` | Modelo completo: objetos, estados, eventos, fórmulas |
| `DECISIONES.md` | Cada decisión de diseño con su justificación y alternativas descartadas |
| `SUPUESTOS.md` | Ambigüedades del enunciado, defaults adoptados, puntos a confirmar con la cátedra |
| `PROGRESO.md` | Bitácora de todas las sesiones de trabajo, etapa por etapa |
| `VALIDACION.md` | Caso de prueba reproducible + chequeos de sanidad |
| `DEFENSA.md` | Preguntas probables de la defensa oral, con sus respuestas |

## ⚠️ Antes de reportar un resultado final

Dos supuestos en `SUPUESTOS.md` cambian drásticamente el comportamiento del sistema y siguen
**sin confirmar con la cátedra**:

- **#1 — Tasa de llegadas:** el enunciado dice "4 clientes/minuto" tomado literalmente (λ=4/min)
  satura el sistema por completo (ρ≈20). Puede ser una redacción confusa de "1 cada 4 minutos".
- **#4 — Umbral mínimo de la regla preventiva:** sin umbral mínimo, la regla preventiva se
  adelanta y el mantenimiento correctivo casi no llega a dispararse (evidencia empírica en
  `SUPUESTOS.md` #4 y `VALIDACION.md`).

El resultado de "cola máxima" que se reporte como entrega final debe correrse **después** de
resolver estos dos puntos.
