"""Estructuras del vector de estado. Ver DISEÑO.md §9.

Una `StateRow` es la foto del sistema justo después de procesar un evento (o
el estado inicial, antes del primer evento). `Simulation` arma una por cada
iteración; `report.py` se encarga de mostrarlas (separación entre motor y
presentación).
"""

from __future__ import annotations

from dataclasses import dataclass

from copy_center.random_utils import Draw


@dataclass
class CopierSnapshot:
    id: int
    state: str  # nombre del CopierState ("FREE"/"BUSY"/"MAINTENANCE")
    usage_remaining: float
    usage_threshold: float
    client_id: int | None


@dataclass
class ClientSnapshot:
    id: int
    arrival_time: float


@dataclass
class StateRow:
    iteration: int
    clock: float
    event_type: str  # nombre del EventType, o "INIT" para la fila inicial

    # RND por variable aleatoria (§8 del prompt). `umbral` es una lista
    # porque la fila inicial sortea 3 umbrales a la vez (uno por copiadora);
    # cualquier otra fila tiene a lo sumo un elemento.
    llegada: Draw | None
    atencion: Draw | None
    umbral: list[tuple[int, Draw]]

    queue_length: int
    max_queue_length: int
    clients_served: int
    corrective_maintenance_count: int
    preventive_maintenance_count: int
    total_wait_time: float
    clients_that_waited: int

    copiers: list[CopierSnapshot]
    # Objetos temporales vivos en la cola. No se listan en la tabla principal
    # (DECISIONES.md D12: la cola no tiene tamaño acotado); se pueden
    # inspeccionar puntualmente con `report.format_queue_detail`.
    clients_in_queue: list[ClientSnapshot]
