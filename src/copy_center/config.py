"""Parámetros configurables de la simulación. Ver DISEÑO.md §2.

Ningún valor usado por la lógica de eventos debe estar "quemado" fuera de este
archivo (DECISIONES.md D9). Todas las magnitudes de tiempo están en minutos
(DECISIONES.md D1).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SimulationConfig:
    """Configuración completa de una corrida. Todo en minutos salvo lo aclarado."""

    n_copiers: int = 3

    # Llegadas y atención (SUPUESTOS.md #1, #3)
    mean_interarrival_time: float = 0.25  # lectura literal, decisión final (SUPUESTOS.md #1)
    mean_service_time: float = 15.0

    # Mantenimiento correctivo: umbral ~ Uniforme[min, max], duración fija.
    maintenance_threshold_min: float = 10_200.0  # 170 h
    maintenance_threshold_max: float = 13_800.0  # 230 h
    maintenance_duration: float = 120.0  # 2 h, fija (no aleatoria)

    # Corte de la simulación (§8 del prompt): lo que ocurra primero.
    max_iterations: int = 100_000
    end_time: float | None = None  # X; None = sin tope de tiempo, solo max_iterations

    # Presentación del vector de estado (§8 del prompt).
    report_from_iteration: int = 0  # j
    report_row_count: int = 50  # i

    # Reproducibilidad (DECISIONES.md D7).
    seed: int | None = 12345

    def __post_init__(self) -> None:
        if self.n_copiers <= 0:
            raise ValueError("n_copiers debe ser positivo")
        if self.mean_interarrival_time <= 0 or self.mean_service_time <= 0:
            raise ValueError("las medias de llegada/atención deben ser positivas")
        if self.maintenance_threshold_min <= 0 or self.maintenance_threshold_max <= 0:
            raise ValueError("los umbrales de mantenimiento deben ser positivos")
        if self.maintenance_threshold_min > self.maintenance_threshold_max:
            raise ValueError("maintenance_threshold_min no puede superar a _max")
        if self.maintenance_duration <= 0:
            raise ValueError("maintenance_duration debe ser positiva")
