"""Motor de simulación. Ver DISEÑO.md §7 y §11.

Etapa 1: estructuras de datos y estado inicial del sistema (SUPUESTOS.md #8).
Etapa 2: procesamiento de Llegada y Fin de atención — cola común y asignación
de copiadoras (DISEÑO.md §7.1, §7.2).
Etapa 3: mantenimiento correctivo (DISEÑO.md §7.2 pasos 2-3, §7.3, §8.1) —
consumo de uso por atención y disparo por umbral.
Etapa 4: mantenimiento preventivo (DISEÑO.md §7.4, §8.2) — si las 3
copiadoras quedan Libres a la vez, se manda a mantenimiento a la más próxima
a fallar.
Etapa 5: vector de estado (DISEÑO.md §9) — una `StateRow` por iteración, con
el RND de cada variable aleatoria usada en ese evento. La presentación
(tabla, i filas desde j, última fila) vive en `report.py`.
Etapa 6 (actual): estadísticas de apoyo síncronas (DISEÑO.md §10.2) — %
ocupación y % tiempo en mantenimiento por copiadora, acumulados por Δt cada
vez que una copiadora cambia de estado (`_change_copier_state`). El resumen
final se arma en `summary()` (ver `statistics.py`).
"""

from __future__ import annotations

import heapq
import itertools
from collections import deque

from copy_center.config import SimulationConfig
from copy_center.entities import Client, Copier, CopierState
from copy_center.events import Event, EventType
from copy_center.random_utils import Draw, RandomGenerator
from copy_center.state_vector import ClientSnapshot, CopierSnapshot, StateRow
from copy_center.statistics import SimulationSummary, copier_stats


class Simulation:
    def __init__(self, config: SimulationConfig) -> None:
        self.config = config
        self.rng = RandomGenerator(config.seed)

        self.clock: float = 0.0
        self.iteration: int = 0

        self._event_heap: list[tuple[float, int, Event]] = []
        self._event_seq = itertools.count()
        self._next_client_id = itertools.count()

        # RND capturados durante el procesamiento del evento en curso, para
        # poder volcarlos a la StateRow correspondiente (§8 del prompt: "para
        # cada variable aleatoria se muestra el RND usado"). Se resetean en
        # `_record_state_row`.
        self._current_draws: dict[str, Draw] = {}
        self._current_umbral_draws: list[tuple[int, Draw]] = []

        self.copiers: list[Copier] = [self._new_copier(i) for i in range(config.n_copiers)]
        self.queue: deque[Client] = deque()

        # Acumuladores estadísticos (DISEÑO.md §10).
        self.max_queue_length: int = 0
        self.corrective_maintenance_count: int = 0
        self.preventive_maintenance_count: int = 0
        self.clients_served: int = 0
        self.total_wait_time: float = 0.0
        self.clients_that_waited: int = 0

        self.state_vector: list[StateRow] = []

        self._schedule_next_arrival()
        if config.end_time is not None:
            self._schedule(Event(time=config.end_time, type=EventType.SIMULATION_END))

        self._record_state_row("INIT")

    def _new_copier(self, copier_id: int) -> Copier:
        draw = self._draw_uniform_threshold(copier_id)
        return Copier(
            id=copier_id,
            state=CopierState.FREE,
            usage_threshold=draw.value,
            usage_remaining=draw.value,
        )

    def _schedule(self, event: Event) -> None:
        # El segundo elemento de la tupla (contador monótono) desempata
        # eventos con el mismo `time` por orden de programación, así el heap
        # no necesita comparar objetos Event entre sí.
        heapq.heappush(self._event_heap, (event.time, next(self._event_seq), event))

    def _draw_exponential(self, kind: str, mean: float) -> Draw:
        draw = self.rng.exponential(mean)
        self._current_draws[kind] = draw
        return draw

    def _draw_uniform_threshold(self, copier_id: int) -> Draw:
        draw = self.rng.uniform(
            self.config.maintenance_threshold_min, self.config.maintenance_threshold_max
        )
        self._current_umbral_draws.append((copier_id, draw))
        return draw

    def _schedule_next_arrival(self) -> None:
        draw = self._draw_exponential("llegada", self.config.mean_interarrival_time)
        self._schedule(Event(time=self.clock + draw.value, type=EventType.ARRIVAL))

    def _pop_next_event(self) -> Event:
        _, _, event = heapq.heappop(self._event_heap)
        return event

    def _update_max_queue_length(self) -> None:
        self.max_queue_length = max(self.max_queue_length, len(self.queue))

    def _select_free_copier(self) -> Copier:
        """Entre las copiadoras libres, la de mayor `usage_remaining` (más
        lejana a fallar); desempate por menor id (SUPUESTOS.md #5 y #6)."""
        free = [c for c in self.copiers if c.is_free()]
        return min(free, key=lambda c: (-c.usage_remaining, c.id))

    def _change_copier_state(self, copier: Copier, new_state: CopierState) -> None:
        """Acumula el tiempo que `copier` pasó en su estado anterior
        (DISEÑO.md §10.2) antes de cambiarlo. Único punto de mutación de
        `copier.state` — así el % ocupación/mantenimiento siempre es
        consistente, sin importar desde dónde se dispare el cambio."""
        elapsed = self.clock - copier.state_since
        if copier.state is CopierState.BUSY:
            copier.busy_time += elapsed
        elif copier.state is CopierState.MAINTENANCE:
            copier.maintenance_time += elapsed
        copier.state = new_state
        copier.state_since = self.clock

    def _start_maintenance(self, copier: Copier, *, corrective: bool) -> None:
        """Manda una copiadora a mantenimiento (DISEÑO.md §8.1/§8.2).

        No es un evento programado independiente (DECISIONES.md D3): se
        llama desde dentro del procesamiento de otro evento.
        """
        self._change_copier_state(copier, CopierState.MAINTENANCE)
        copier.current_client = None
        self._schedule(
            Event(
                time=self.clock + self.config.maintenance_duration,
                type=EventType.MAINTENANCE_END,
                copier_id=copier.id,
            )
        )
        if corrective:
            self.corrective_maintenance_count += 1
        else:
            self.preventive_maintenance_count += 1

    def _maybe_trigger_preventive_maintenance(self) -> None:
        """DISEÑO.md §7.4/§8.2: si las 3 copiadoras están Libres a la vez, se
        manda a mantenimiento a la de menor `usage_remaining` (más próxima a
        fallar); desempate por menor id (SUPUESTOS.md #4 y #6). Se llama al
        final de Fin de atención y Fin de mantenimiento, nunca desde Llegada
        (una llegada solo puede reducir la cantidad de libres, nunca dejar a
        las 3 libres a la vez)."""
        if not all(c.state is CopierState.FREE for c in self.copiers):
            return
        copier = min(self.copiers, key=lambda c: (c.usage_remaining, c.id))
        self._start_maintenance(copier, corrective=False)

    def _assign_client(self, copier: Copier, client: Client) -> None:
        client.service_start_time = self.clock
        if client.waited:
            self.total_wait_time += client.service_start_time - client.arrival_time
            self.clients_that_waited += 1

        self._change_copier_state(copier, CopierState.BUSY)
        copier.current_client = client
        draw = self._draw_exponential("atencion", self.config.mean_service_time)
        self._schedule(
            Event(time=self.clock + draw.value, type=EventType.SERVICE_END, copier_id=copier.id)
        )

    def _process_arrival(self, event: Event) -> None:
        self._schedule_next_arrival()

        client = Client(id=next(self._next_client_id), arrival_time=self.clock)
        free_copiers = [c for c in self.copiers if c.is_free()]
        if free_copiers:
            self._assign_client(self._select_free_copier(), client)
        else:
            self.queue.append(client)
            self._update_max_queue_length()

    def _process_service_end(self, event: Event) -> None:
        assert event.copier_id is not None
        copier = self.copiers[event.copier_id]
        finished_client = copier.current_client
        assert finished_client is not None
        assert finished_client.service_start_time is not None

        service_duration = self.clock - finished_client.service_start_time
        copier.current_client = None
        self.clients_served += 1
        copier.consume_usage(service_duration)

        if copier.needs_corrective_maintenance():
            # SUPUESTOS.md #2: no se interrumpe la atención en curso, así que
            # `usage_remaining` puede quedar negativo — recién acá, al
            # terminar, se manda a mantenimiento.
            self._start_maintenance(copier, corrective=True)
        elif self.queue:
            next_client = self.queue.popleft()
            self._update_max_queue_length()
            self._assign_client(copier, next_client)
        else:
            self._change_copier_state(copier, CopierState.FREE)

        self._maybe_trigger_preventive_maintenance()

    def _process_maintenance_end(self, event: Event) -> None:
        assert event.copier_id is not None
        copier = self.copiers[event.copier_id]

        draw = self._draw_uniform_threshold(copier.id)
        copier.usage_threshold = draw.value
        copier.usage_remaining = draw.value

        if self.queue:
            next_client = self.queue.popleft()
            self._update_max_queue_length()
            self._assign_client(copier, next_client)
        else:
            self._change_copier_state(copier, CopierState.FREE)

        self._maybe_trigger_preventive_maintenance()

    def _snapshot_copier(self, copier: Copier) -> CopierSnapshot:
        return CopierSnapshot(
            id=copier.id,
            state=copier.state.name,
            usage_remaining=copier.usage_remaining,
            usage_threshold=copier.usage_threshold,
            client_id=copier.current_client.id if copier.current_client else None,
        )

    def _record_state_row(self, event_type: str) -> None:
        row = StateRow(
            iteration=self.iteration,
            clock=self.clock,
            event_type=event_type,
            llegada=self._current_draws.get("llegada"),
            atencion=self._current_draws.get("atencion"),
            umbral=list(self._current_umbral_draws),
            queue_length=len(self.queue),
            max_queue_length=self.max_queue_length,
            clients_served=self.clients_served,
            corrective_maintenance_count=self.corrective_maintenance_count,
            preventive_maintenance_count=self.preventive_maintenance_count,
            total_wait_time=self.total_wait_time,
            clients_that_waited=self.clients_that_waited,
            copiers=[self._snapshot_copier(c) for c in self.copiers],
            clients_in_queue=[
                ClientSnapshot(id=c.id, arrival_time=c.arrival_time) for c in self.queue
            ],
        )
        self.state_vector.append(row)
        self._current_draws = {}
        self._current_umbral_draws = []

    def _finalize_copier_time_accounting(self) -> None:
        """Cierra el último intervalo abierto de cada copiadora hasta el
        reloj final, para que el % ocupación/mantenimiento contemple también
        el estado en el que quedó cada una al cortar la simulación."""
        for copier in self.copiers:
            self._change_copier_state(copier, copier.state)

    def summary(self) -> SimulationSummary:
        """Estadísticas finales (DISEÑO.md §10): la requerida (cola máxima)
        más las de apoyo. Se puede llamar en cualquier momento, pero los
        porcentajes por copiadora solo están cerrados una vez que `run()`
        terminó (`_finalize_copier_time_accounting`)."""
        avg_wait_time = (
            self.total_wait_time / self.clients_that_waited
            if self.clients_that_waited > 0
            else None
        )
        return SimulationSummary(
            total_time=self.clock,
            max_queue_length=self.max_queue_length,
            clients_served=self.clients_served,
            avg_wait_time=avg_wait_time,
            clients_that_waited=self.clients_that_waited,
            corrective_maintenance_count=self.corrective_maintenance_count,
            preventive_maintenance_count=self.preventive_maintenance_count,
            copiers=[
                copier_stats(c.id, c.busy_time, c.maintenance_time, self.clock)
                for c in self.copiers
            ],
        )

    def _process_event(self, event: Event) -> None:
        if event.type is EventType.ARRIVAL:
            self._process_arrival(event)
        elif event.type is EventType.SERVICE_END:
            self._process_service_end(event)
        elif event.type is EventType.MAINTENANCE_END:
            self._process_maintenance_end(event)
        else:
            raise ValueError(f"Tipo de evento inesperado en _process_event: {event.type}")

    def run(self) -> None:
        """Motor de eventos completo: Llegada, Fin de atención, mantenimiento
        correctivo y preventivo (DISEÑO.md §7), registrando una `StateRow`
        por iteración (DISEÑO.md §9).

        Corta al llegar a `max_iterations` o al procesar `SIMULATION_END`, lo
        que ocurra primero (§8 del prompt).
        """
        while self.iteration < self.config.max_iterations and self._event_heap:
            event = self._pop_next_event()
            if event.type is EventType.SIMULATION_END:
                self.clock = event.time
                break

            self.clock = event.time
            self.iteration += 1
            self._process_event(event)
            self._record_state_row(event.type.name)

        self._finalize_copier_time_accounting()
