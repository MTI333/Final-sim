"""Eventos programados del motor de simulación. Ver DISEÑO.md §5.

El inicio de mantenimiento NO es un evento propio (DECISIONES.md D3): se
decide dentro del procesamiento de estos cuatro tipos.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from copy_center.entities import Client


class EventType(Enum):
    ARRIVAL = auto()
    SERVICE_END = auto()
    MAINTENANCE_END = auto()
    SIMULATION_END = auto()


@dataclass
class Event:
    """Un evento programado en el tiempo.

    `copier_id` y `client` son opcionales según el tipo: una Llegada todavía
    no tiene copiadora asignada; un Fin de mantenimiento no tiene cliente.
    """

    time: float
    type: EventType
    copier_id: int | None = None
    client: Client | None = None
