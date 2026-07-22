"""Eventos programados del motor de simulación. Ver DISEÑO.md §5.

El inicio de mantenimiento NO es un evento propio (DECISIONES.md D3): se
decide dentro del procesamiento de estos cuatro tipos.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from copy_center.entities import Client


class EventType(Enum):
    """Los 4 tipos de evento que puede sacar el motor de la cola de
    prioridad (`Simulation._event_heap`). Cada uno dispara un handler
    distinto en `simulation.py` (`_process_event`)."""

    ARRIVAL = auto()  # Llega un cliente nuevo al sistema.
    SERVICE_END = auto()  # Una copiadora termina de atender a su cliente actual.
    MAINTENANCE_END = auto()  # Una copiadora termina su mantenimiento (correctivo o preventivo).
    SIMULATION_END = auto()  # Se alcanzó el tiempo límite `config.end_time`; corta la corrida.


@dataclass
class Event:
    """Un evento programado en el tiempo: qué va a pasar (`type`) y cuándo
    (`time`). El motor los va sacando del heap en orden de `time` creciente.

    `copier_id` y `client` son opcionales según el tipo: una Llegada todavía
    no tiene copiadora asignada; un Fin de mantenimiento no tiene cliente.
    """

    time: float  # Reloj absoluto (en minutos) en el que debe procesarse el evento.
    type: EventType  # Cuál de los 4 tipos es.
    copier_id: int | None = None  # Copiadora involucrada (SERVICE_END / MAINTENANCE_END).
    client: Client | None = None  # Cliente involucrado (no se usa actualmente: el cliente
    # atendido se lee de `copier.current_client` en el momento de procesar el evento).
