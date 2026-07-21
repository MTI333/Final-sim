"""Interfaz de línea de comandos. Ver README.md.

Corre la simulación con los parámetros pasados (o los defaults de
`SimulationConfig`, ver DISEÑO.md §2) y muestra el vector de estado (`i`
filas desde `j`, última fila) más el resumen final de estadísticas.
"""

from __future__ import annotations

import argparse

from copy_center.config import SimulationConfig
from copy_center.report import format_summary, render_full_report
from copy_center.simulation import Simulation


def _build_arg_parser() -> argparse.ArgumentParser:
    defaults = SimulationConfig()
    parser = argparse.ArgumentParser(
        prog="copy_center",
        description="Simulación de eventos discretos del Centro de Copiado (ver DISEÑO.md).",
    )
    parser.add_argument("--n-copiers", type=int, default=defaults.n_copiers,
                         help=f"Cantidad de copiadoras (default: {defaults.n_copiers}).")
    parser.add_argument("--mean-interarrival-time", type=float,
                         default=defaults.mean_interarrival_time,
                         help="Media del tiempo entre llegadas, en minutos. ⚠️ ver "
                              f"SUPUESTOS.md #1 (default: {defaults.mean_interarrival_time}).")
    parser.add_argument("--mean-service-time", type=float, default=defaults.mean_service_time,
                         help=f"Media del tiempo de atención, en minutos "
                              f"(default: {defaults.mean_service_time}).")
    parser.add_argument("--maintenance-threshold-min", type=float,
                         default=defaults.maintenance_threshold_min,
                         help="Umbral de mantenimiento correctivo, extremo inferior, en minutos "
                              f"de uso (default: {defaults.maintenance_threshold_min}).")
    parser.add_argument("--maintenance-threshold-max", type=float,
                         default=defaults.maintenance_threshold_max,
                         help="Umbral de mantenimiento correctivo, extremo superior, en minutos "
                              f"de uso (default: {defaults.maintenance_threshold_max}).")
    parser.add_argument("--maintenance-duration", type=float,
                         default=defaults.maintenance_duration,
                         help=f"Duración fija del mantenimiento, en minutos "
                              f"(default: {defaults.maintenance_duration}).")
    parser.add_argument("--max-iterations", type=int, default=defaults.max_iterations,
                         help=f"Tope de iteraciones (default: {defaults.max_iterations}).")
    parser.add_argument("--end-time", type=float, default=defaults.end_time,
                         help="Tiempo límite X, en minutos. Sin valor: solo corta por "
                              "--max-iterations (default: sin límite).")
    parser.add_argument("--report-from", type=int, default=defaults.report_from_iteration,
                         dest="report_from_iteration",
                         help=f"Iteración j desde la que se muestran filas "
                              f"(default: {defaults.report_from_iteration}).")
    parser.add_argument("--report-rows", type=int, default=defaults.report_row_count,
                         dest="report_row_count",
                         help=f"Cantidad de filas i a mostrar desde j "
                              f"(default: {defaults.report_row_count}).")
    parser.add_argument("--seed", type=int, default=defaults.seed,
                         help=f"Semilla del generador aleatorio, para reproducibilidad "
                              f"(default: {defaults.seed}).")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = _build_arg_parser().parse_args(argv)
    config = SimulationConfig(**vars(args))

    sim = Simulation(config)
    sim.run()

    print(render_full_report(
        sim.state_vector, config.n_copiers, config.report_from_iteration, config.report_row_count
    ))
    print()
    print(format_summary(sim.summary()))


if __name__ == "__main__":
    main()
