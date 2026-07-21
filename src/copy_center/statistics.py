"""Estadísticas finales de una corrida. Ver DISEÑO.md §10.

Igual que `state_vector.py`/`report.py`: estructuras de datos separadas del
motor (`Simulation.summary()` las arma, pero el cálculo de porcentajes vive
acá para poder testearlo aislado).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CopierStats:
    id: int
    occupancy_pct: float  # % ocupada, síncrono: busy_time / total_time
    maintenance_pct: float  # % en mantenimiento, síncrono: maintenance_time / total_time
    free_pct: float  # derivado: 1 - occupancy_pct - maintenance_pct


@dataclass
class SimulationSummary:
    total_time: float
    max_queue_length: int
    clients_served: int
    avg_wait_time: float | None  # None si ningún cliente esperó
    clients_that_waited: int
    corrective_maintenance_count: int
    preventive_maintenance_count: int
    copiers: list[CopierStats]


def copier_stats(copier_id: int, busy_time: float, maintenance_time: float,
                  total_time: float) -> CopierStats:
    if total_time <= 0:
        return CopierStats(id=copier_id, occupancy_pct=0.0, maintenance_pct=0.0, free_pct=1.0)
    occupancy_pct = busy_time / total_time
    maintenance_pct = maintenance_time / total_time
    free_pct = max(0.0, 1.0 - occupancy_pct - maintenance_pct)
    return CopierStats(
        id=copier_id,
        occupancy_pct=occupancy_pct,
        maintenance_pct=maintenance_pct,
        free_pct=free_pct,
    )
