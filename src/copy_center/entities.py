"""Entidades del modelo: Cliente (temporal) y Copiadora (permanente).

Ver DISEÑO.md §3 para la tabla de atributos y DECISIONES.md D8 para la
correspondencia de términos español (enunciado) ↔ inglés (código).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class CopierState(Enum):
    """Los 3 estados posibles de una copiadora en todo momento de la
    simulación (nunca hay un cuarto estado ni superposición)."""

    FREE = auto()  # Libre: puede tomar un cliente nuevo apenas llegue o salga de la cola.
    BUSY = auto()  # Ocupada: atendiendo a `current_client`.
    MAINTENANCE = auto()  # En mantenimiento (correctivo o preventivo): no puede atender.


@dataclass
class Client:
    """Objeto temporal: se descarta al terminar su atención (DECISIONES.md D5).
    No se guarda un historial de clientes; solo existe mientras está en el
    sistema (en cola o siendo atendido)."""

    id: int  # Identificador secuencial, asignado por `Simulation._next_client_id`.
    arrival_time: float  # Reloj en el que llegó (se fija una sola vez, al crearse).
    service_start_time: float | None = None  # Reloj en que empezó a ser atendido;
    # `None` mientras sigue esperando en la cola.

    @property
    def waited(self) -> bool:
        """True si pasó tiempo real en la cola antes de ser atendido."""
        # Si `service_start_time` == `arrival_time`, lo atendieron al instante
        # (copiadora libre disponible en el momento de la llegada) y no cuenta
        # como espera real, aunque técnicamente ya haya sido "asignado".
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

    id: int  # Identificador fijo (0, 1, 2, ...), asignado una vez al crear la simulación.
    state: CopierState = CopierState.FREE  # Estado actual. Mutarlo SIEMPRE a través de
    # `Simulation._change_copier_state`, nunca de forma directa (ver ese método).
    usage_threshold: float = 0.0  # Umbral de uso sorteado (Uniforme) que dispara el
    # próximo mantenimiento correctivo; se vuelve a sortear cada vez que sale de mantenimiento.
    usage_remaining: float = 0.0  # Cuánto uso le queda antes de necesitar mantenimiento
    # correctivo. Arranca igual a `usage_threshold` y se descuenta con `consume_usage`.
    current_client: Client | None = None  # Cliente que está atendiendo ahora mismo
    # (`None` si está LIBRE o en MANTENIMIENTO).
    state_since: float = 0.0  # Reloj en el que entró al estado actual; se usa para calcular
    # cuánto tiempo estuvo en él la próxima vez que cambie de estado.
    busy_time: float = 0.0  # Acumulado de minutos totales que pasó OCUPADA (para el % final).
    maintenance_time: float = 0.0  # Acumulado de minutos totales en MANTENIMIENTO (para el % final).
    # Reloj absoluto en que termina la atención/mantenimiento en curso (o
    # `None` si no aplica). Se exponen en el vector de estado como
    # "Fin aten"/"Fin mant" por copiadora (formato VectorEstado_CentroCopiado).
    service_end_time: float | None = None  # Cuándo termina la atención en curso (si está BUSY).
    maintenance_end_time: float | None = None  # Cuándo termina el mantenimiento en curso (si está en MAINTENANCE).

    def is_free(self) -> bool:
        return self.state is CopierState.FREE

    def consume_usage(self, minutes: float) -> None:
        """Descuenta minutos de uso efectivo. Solo se llama al terminar una
        atención (DISEÑO.md §8.1: el uso se acumula solo mientras atiende)."""
        # Nota: puede dejar `usage_remaining` en negativo (no se trunca en 0),
        # porque la atención en curso nunca se interrumpe aunque se cruce el
        # umbral a mitad de camino (SUPUESTOS.md #2).
        self.usage_remaining -= minutes

    def needs_corrective_maintenance(self) -> bool:
        # Se llama justo después de `consume_usage`, al cerrar una atención.
        return self.usage_remaining <= 0
