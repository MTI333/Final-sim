"""Presentación del vector de estado y de las estadísticas finales. Ver
DISEÑO.md §9, §10 y §8 del prompt.

No depende de `Simulation`: recibe la lista de `StateRow` / el
`SimulationSummary` ya armados, así se puede testear la presentación por
separado del motor de eventos (DECISIONES.md D13: separación
motor/presentación). Traduce al español para mostrar (nombres de
evento/estado internos quedan en inglés en el código, DECISIONES.md D8).
"""

from __future__ import annotations

from copy_center.state_vector import StateRow
from copy_center.statistics import SimulationSummary

_EVENT_LABELS_ES = {
    "INIT": "INICIO",
    "ARRIVAL": "LLEGADA",
    "SERVICE_END": "FIN_ATENCION",
    "MAINTENANCE_END": "FIN_MANTENIMIENTO",
}

_STATE_LABELS_ES = {
    "FREE": "LIBRE",
    "BUSY": "OCUPADA",
    "MAINTENANCE": "MANTEN",
}


def event_label(event_type: str) -> str:
    """Traducción del `event_type` interno (inglés) al español para mostrar.
    Pública porque también la usa `webapp.py` (DECISIONES.md D13)."""
    return _EVENT_LABELS_ES.get(event_type, event_type)


def state_label(state: str) -> str:
    """Traducción del `CopierState.name` interno (inglés) al español."""
    return _STATE_LABELS_ES.get(state, state)


def format_header(n_copiers: int) -> str:
    cols = ["Iter", "Reloj", "Evento", "RND_lleg", "T_lleg", "RND_atenc", "T_atenc",
            "RND_umbral", "T_umbral"]
    for i in range(n_copiers):
        cols += [f"Cop{i}_Estado", f"Cop{i}_UsoRest", f"Cop{i}_Cliente"]
    cols += ["Cola", "ColaMax", "Atendidos", "Correctivos", "Preventivos"]
    return " | ".join(cols)


def format_row(row: StateRow, *, show_clients: bool = True) -> str:
    rnd_lleg = f"{row.llegada.rnd:.4f}" if row.llegada else "-"
    t_lleg = f"{row.llegada.value:.2f}" if row.llegada else "-"
    rnd_at = f"{row.atencion.rnd:.4f}" if row.atencion else "-"
    t_at = f"{row.atencion.value:.2f}" if row.atencion else "-"
    if row.umbral:
        rnd_umb = ",".join(f"{draw.rnd:.4f}" for _, draw in row.umbral)
        t_umb = ",".join(f"{draw.value:.2f}" for _, draw in row.umbral)
    else:
        rnd_umb = t_umb = "-"

    fields = [str(row.iteration), f"{row.clock:.2f}", event_label(row.event_type),
              rnd_lleg, t_lleg, rnd_at, t_at, rnd_umb, t_umb]

    for c in row.copiers:
        client_field = str(c.client_id) if (show_clients and c.client_id is not None) else "-"
        fields += [state_label(c.state), f"{c.usage_remaining:.1f}", client_field]

    fields += [str(row.queue_length), str(row.max_queue_length), str(row.clients_served),
               str(row.corrective_maintenance_count), str(row.preventive_maintenance_count)]
    return " | ".join(fields)


def format_queue_detail(row: StateRow) -> str:
    """Detalle de los clientes vivos en la cola común de una fila puntual.

    Aparte de la tabla principal porque la cola no tiene tamaño acotado
    (DECISIONES.md D12) — no tiene sentido como columnas fijas.
    """
    if not row.clients_in_queue:
        return "(cola vacía)"
    return "\n".join(
        f"  cliente {c.id}: llegó en t={c.arrival_time:.2f} "
        f"(espera acumulada: {row.clock - c.arrival_time:.2f} min)"
        for c in row.clients_in_queue
    )


def render_full_report(state_vector: list[StateRow], n_copiers: int, j: int, i: int) -> str:
    """DISEÑO.md §9 / §8 del prompt: `i` filas a partir de `j`, más la
    última fila (sin objetos temporales — sin ids de cliente)."""
    window = state_vector[j : j + i]
    last = state_vector[-1]

    lines = [
        f"Vector de estado — filas {j} a {j + len(window) - 1} de {len(state_vector) - 1} "
        f"(iteración final={last.iteration}, reloj final={last.clock:.2f} min)",
        format_header(n_copiers),
    ]
    lines += [format_row(r) for r in window]
    lines.append("")
    lines.append(f"Última fila (iteración {last.iteration}, reloj={last.clock:.2f} min):")
    lines.append(format_header(n_copiers))
    lines.append(format_row(last, show_clients=False))
    return "\n".join(lines)


def format_summary(summary: SimulationSummary) -> str:
    """DISEÑO.md §10: la cola máxima (requerida) + las estadísticas de
    apoyo. No es una fila del vector de estado — es el resumen final de la
    corrida completa."""
    lines = [
        "Resumen de la corrida",
        f"  Tiempo total simulado: {summary.total_time:.2f} min",
        f"  Cola máxima: {summary.max_queue_length}",
        f"  Clientes atendidos: {summary.clients_served}",
    ]
    if summary.avg_wait_time is not None:
        lines.append(
            f"  Espera promedio (de los {summary.clients_that_waited} clientes que "
            f"esperaron): {summary.avg_wait_time:.2f} min"
        )
    else:
        lines.append("  Espera promedio: N/A (ningún cliente esperó)")
    lines.append(f"  Mantenimientos correctivos: {summary.corrective_maintenance_count}")
    lines.append(f"  Mantenimientos preventivos: {summary.preventive_maintenance_count}")
    lines.append("  Por copiadora (% del tiempo total simulado):")
    for c in summary.copiers:
        lines.append(
            f"    Copiadora {c.id}: ocupada {c.occupancy_pct:6.1%}  "
            f"mantenimiento {c.maintenance_pct:6.1%}  libre {c.free_pct:6.1%}"
        )
    return "\n".join(lines)
