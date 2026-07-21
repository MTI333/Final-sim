"""Entidades del modelo: Cliente (temporal) y Copiadora (permanente).

Ver DISEÑO.md §3 para la tabla de atributos y DECISIONES.md D8 para la
correspondencia de términos español (enunciado) ↔ inglés (código).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class CopierState(Enum):
    FREE = auto()
    BUSY = auto()
    MAINTENANCE = auto()


@dataclass
class Client:
    """Objeto temporal: se descarta al terminar su atención (DECISIONES.md D5)."""

    id: int
    arrival_time: float
    service_start_time: float | None = None

    @property
    def waited(self) -> bool:
        """True si pasó tiempo real en la cola antes de ser atendido."""
        return (
            self.service_start_time is not None
            and self.service_start_time > self.arrival_time
        )


@dataclass
class Copier:
    """Objeto permanente. Ver DISEÑO.md §3.2.

    `state_since`, `busy_time` y `maintenance_time` sostienen las
    estadísticas síncronas de apoyo (DISEÑO.md §10.2: % ocupación, % tiempo
    en mantenimiento). El tiempo libre no se acumula aparte: se deriva como
    `total_time - busy_time - maintenance_time` (Simulation.summary()).
    """

    id: int
    state: CopierState = CopierState.FREE
    usage_threshold: float = 0.0
    usage_remaining: float = 0.0
    current_client: Client | None = None
    state_since: float = 0.0
    busy_time: float = 0.0
    maintenance_time: float = 0.0

    def is_free(self) -> bool:
        return self.state is CopierState.FREE

    def consume_usage(self, minutes: float) -> None:
        """Descuenta minutos de uso efectivo. Solo se llama al terminar una
        atención (DISEÑO.md §8.1: el uso se acumula solo mientras atiende)."""
        self.usage_remaining -= minutes

    def needs_corrective_maintenance(self) -> bool:
        return self.usage_remaining <= 0
