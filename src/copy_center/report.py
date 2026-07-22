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
    "INIT": "Inicializacion",
    "ARRIVAL": "Llegada",
}

_STATE_LABELS_ES = {
    "FREE": "LIBRE",
    "BUSY": "OCUPADA",
    "MAINTENANCE": "MANTEN",
}


def event_label(event_type: str, copier_id: int | None = None) -> str:
    """Traducción del `event_type` interno (inglés) al español para mostrar.

    SERVICE_END/MAINTENANCE_END incluyen la copiadora involucrada en la
    propia etiqueta (p. ej. "FinAtC1"), 1-indexada para mostrar (formato
    VectorEstado_CentroCopiado, "COPIADORA 1/2/3"; DECISIONES.md D8 mapea el
    resto de los términos). Pública porque también la usa `webapp.py`
    (DECISIONES.md D13)."""
    if event_type == "SERVICE_END" and copier_id is not None:
        return f"FinAtC{copier_id + 1}"
    if event_type == "MAINTENANCE_END" and copier_id is not None:
        return f"FinMantC{copier_id + 1}"
    return _EVENT_LABELS_ES.get(event_type, event_type)


def state_label(state: str) -> str:
    """Traducción del `CopierState.name` interno (inglés) al español."""
    return _STATE_LABELS_ES.get(state, state)


_DEFAULT_CLIENT_SLOTS = 5


def _core_group_and_columns(n_copiers: int) -> tuple[list[str], list[str]]:
    """Grupo + columna "núcleo" (hasta "Preventivos"), compartido por la
    tabla estándar y la variante con clientes — ver `format_header`."""
    group = ["", "", "", "LLEGADA CLIENTE", "", "", "FIN ATENCION (sorteo)", ""]
    for i in range(n_copiers):
        group += [f"COPIADORA {i + 1}", "", "", "", ""]
    group += ["COLA", "", "", "", "", ""]

    cols = ["No", "Evento", "Reloj", "RND", "t e/lleg", "prox lleg", "RND", "t aten"]
    for _ in range(n_copiers):
        cols += ["Estado", "AC Ocup", "Umbral", "Fin aten", "Fin mant"]
    cols += ["Cola", "Cola max", "RND_umbral", "Atendidos", "Correctivos", "Preventivos"]
    return group, cols


def format_header(n_copiers: int) -> str:
    """Dos líneas: grupo (como las cabeceras combinadas de
    `VectorEstado_CentroCopiado.xlsx`) y columna. Las primeras 25 columnas
    (hasta "Cola max") replican nombre y orden exactos de esa planilla de
    referencia; las últimas 4 ("RND_umbral", "Atendidos", "Correctivos",
    "Preventivos") no están en la planilla pero son "columnas de apoyo"
    exigidas por DISEÑO.md §9/§10 — se agregan al final, sin group label,
    para no romper el orden de lo que sí replica la referencia."""
    group, cols = _core_group_and_columns(n_copiers)
    return " | ".join(group) + "\n" + " | ".join(cols)


def format_header_with_clients(n_copiers: int, max_client_slots: int = _DEFAULT_CLIENT_SLOTS,
                                ) -> str:
    """Variante de `format_header` con la sección "CLIENTE 1..N" de la
    planilla de referencia agregada al final (Estado + H.lleg por slot).

    Solo para corridas chicas de demo (DECISIONES.md D18): con `max_queue_length`
    grande no alcanzan `max_client_slots` columnas fijas — la tabla estándar
    (D5/D12, sin enumerar clientes) sigue siendo la del entregable real."""
    group, cols = _core_group_and_columns(n_copiers)
    for i in range(max_client_slots):
        group += [f"CLIENTE {i + 1}", ""]
        cols += ["Estado", "H.lleg"]
    return " | ".join(group) + "\n" + " | ".join(cols)


def _core_fields(row: StateRow) -> list[str]:
    rnd_lleg = f"{row.llegada.rnd:.4f}" if row.llegada else "-"
    t_lleg = f"{row.llegada.value:.2f}" if row.llegada else "-"
    prox_lleg = f"{row.clock + row.llegada.value:.2f}" if row.llegada else "-"
    rnd_at = f"{row.atencion.rnd:.4f}" if row.atencion else "-"
    t_at = f"{row.atencion.value:.2f}" if row.atencion else "-"
    rnd_umb = ",".join(f"{draw.rnd:.4f}" for _, draw in row.umbral) if row.umbral else "-"

    fields = [str(row.iteration), event_label(row.event_type, row.copier_id),
              f"{row.clock:.2f}", rnd_lleg, t_lleg, prox_lleg, rnd_at, t_at]

    for c in row.copiers:
        ac_ocup = c.usage_threshold - c.usage_remaining
        fin_aten = f"{c.service_end_time:.2f}" if c.service_end_time is not None else "-"
        fin_mant = f"{c.maintenance_end_time:.2f}" if c.maintenance_end_time is not None else "-"
        fields += [state_label(c.state), f"{ac_ocup:.1f}", f"{c.usage_threshold:.1f}",
                   fin_aten, fin_mant]

    fields += [str(row.queue_length), str(row.max_queue_length), rnd_umb,
               str(row.clients_served), str(row.corrective_maintenance_count),
               str(row.preventive_maintenance_count)]
    return fields


def format_row(row: StateRow) -> str:
    return " | ".join(_core_fields(row))


# slot (1-indexado) -> (client_id, "En atención"/"En cola", hora de llegada)
ClientSlotMap = dict[int, tuple[int, str, float]]


def compute_client_slots(state_vector: list[StateRow],
                          max_client_slots: int | None = _DEFAULT_CLIENT_SLOTS,
                          ) -> list[ClientSlotMap]:
    """Asigna a cada cliente vivo (en atención o en cola) un slot 1..N, uno
    por fila del vector de estado — igual que la sección "CLIENTE 1..N" de
    `VectorEstado_CentroCopiado.xlsx`: la asignación es persistente (un
    cliente conserva su slot hasta irse, "el slot se libera al irse", no se
    reordena de fila a fila) y se calcula enteramente sobre lo que ya
    registra `StateRow` (`copiers[].client_id`, `clients_in_queue`), sin
    tocar el motor (DECISIONES.md D13).

    `max_client_slots=None` no pone techo: se crea un slot nuevo cada vez
    que hace falta y no hay ninguno libre para reciclar (crece exactamente
    a la concurrencia real de la corrida, ni más ni menos). Con un entero,
    los clientes que no entran en ese cupo simplemente no aparecen en
    ningún slot ese tramo (D18: pensado para corridas chicas de demo, no
    para el entregable real, que no tiene ese límite — D5/D12)."""
    client_arrival: dict[int, float] = {}
    slot_of_client: dict[int, int] = {}
    free_slots = [] if max_client_slots is None else list(range(1, max_client_slots + 1))
    next_new_slot = 1
    per_row: list[ClientSlotMap] = []

    for row in state_vector:
        alive: dict[int, str] = {}
        for c in row.copiers:
            if c.client_id is not None:
                alive[c.client_id] = "En atención"
                client_arrival.setdefault(c.client_id, row.clock)
        for cs in row.clients_in_queue:
            alive[cs.id] = "En cola"
            client_arrival.setdefault(cs.id, cs.arrival_time)

        for cid in list(slot_of_client):
            if cid not in alive:
                free_slots.append(slot_of_client.pop(cid))
        free_slots.sort()

        new_clients = sorted(
            (cid for cid in alive if cid not in slot_of_client),
            key=lambda cid: client_arrival[cid],
        )
        for cid in new_clients:
            if free_slots:
                slot_of_client[cid] = free_slots.pop(0)
            elif max_client_slots is None:
                slot_of_client[cid] = next_new_slot
                next_new_slot += 1
            # si tiene techo y está lleno, este cliente no entra este tramo.

        per_row.append({
            slot: (cid, alive[cid], client_arrival[cid])
            for cid, slot in slot_of_client.items()
        })

    return per_row


def slots_in_use(slots_by_row: list[ClientSlotMap]) -> int:
    """Cantidad real de slots usados en toda la corrida — para saber cuántas
    columnas "CLIENTE N" hace falta renderizar cuando `compute_client_slots`
    se llamó sin techo (`max_client_slots=None`)."""
    return max((max(row, default=0) for row in slots_by_row), default=0)


def format_row_with_clients(row: StateRow, slots: ClientSlotMap,
                             max_client_slots: int = _DEFAULT_CLIENT_SLOTS) -> str:
    fields = _core_fields(row)
    for slot in range(1, max_client_slots + 1):
        if slot in slots:
            _client_id, status, arrival = slots[slot]
            fields += [status, f"{arrival:.2f}"]
        else:
            fields += ["-", "-"]
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
    lines.append(format_row(last))
    return "\n".join(lines)


def render_full_report_with_clients(state_vector: list[StateRow], n_copiers: int, j: int, i: int,
                                     max_client_slots: int | None = _DEFAULT_CLIENT_SLOTS) -> str:
    """Igual que `render_full_report`, pero con la sección "CLIENTE 1..N" de
    la planilla de referencia agregada (`compute_client_slots`). Pensado
    para corridas chicas de demo (DECISIONES.md D18), no para el entregable
    real. `max_client_slots=None` no pone techo: muestra tantas columnas
    "CLIENTE N" como concurrencia real haya tenido la corrida."""
    window = state_vector[j : j + i]
    last = state_vector[-1]
    slots_by_row = compute_client_slots(state_vector, max_client_slots)
    n_slots = slots_in_use(slots_by_row)
    window_slots = slots_by_row[j : j + i]

    lines = [
        f"Vector de estado — filas {j} a {j + len(window) - 1} de {len(state_vector) - 1} "
        f"(iteración final={last.iteration}, reloj final={last.clock:.2f} min)",
        format_header_with_clients(n_copiers, n_slots),
    ]
    lines += [
        format_row_with_clients(r, slots, n_slots)
        for r, slots in zip(window, window_slots)
    ]
    lines.append("")
    lines.append(f"Última fila (iteración {last.iteration}, reloj={last.clock:.2f} min):")
    lines.append(format_header_with_clients(n_copiers, n_slots))
    lines.append(format_row_with_clients(last, slots_by_row[-1], n_slots))
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
            f"    Copiadora {c.id + 1}: ocupada {c.occupancy_pct:6.1%}  "
            f"mantenimiento {c.maintenance_pct:6.1%}  libre {c.free_pct:6.1%}"
        )
    return "\n".join(lines)
