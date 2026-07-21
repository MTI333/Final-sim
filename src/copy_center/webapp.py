"""Interfaz web local para explorar la simulación de forma interactiva.

⚠️ No forma parte del entregable del TP — la consigna (§8 del prompt) pide el
vector de estado en el formato de tabla de `report.py`/CLI. Esto es una
herramienta adicional, pedida explícitamente para explorar resultados y
parámetros más cómodamente durante el desarrollo. Ver README.md.

Solo librería estándar (DECISIONES.md D16): `http.server` sirve HTML armado
a mano; no hay motor de plantillas ni framework web. Cada request es
stateless — recibe los parámetros por query string, corre una `Simulation`
completa desde cero y renderiza la página (mismo patrón de separación
motor/presentación que `report.py`, DECISIONES.md D13).
"""

from __future__ import annotations

import argparse
import html
import json
import math
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

from copy_center.config import SimulationConfig
from copy_center.report import event_label, state_label
from copy_center.simulation import Simulation
from copy_center.state_vector import StateRow
from copy_center.statistics import SimulationSummary

# (nombre del campo, etiqueta para el form, tipo)
_FIELDS: list[tuple[str, str, str]] = [
    ("n_copiers", "Copiadoras", "int"),
    ("mean_interarrival_time", "Media entre llegadas (min)", "float"),
    ("mean_service_time", "Media de atención (min)", "float"),
    ("maintenance_threshold_min", "Umbral mantenimiento mín (min de uso)", "float"),
    ("maintenance_threshold_max", "Umbral mantenimiento máx (min de uso)", "float"),
    ("maintenance_duration", "Duración mantenimiento (min)", "float"),
    ("max_iterations", "Tope de iteraciones", "int"),
    ("end_time", "Tiempo límite X (min, vacío = sin límite)", "optional_float"),
    ("report_from_iteration", "Mostrar desde iteración (j)", "int"),
    ("report_row_count", "Cantidad de filas a mostrar (i)", "int"),
    ("seed", "Semilla (vacío = aleatoria)", "optional_int"),
]

_CSS = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
body {
  margin: 0; padding: 24px 32px 64px;
  background: #f5f5f7; color: #1c1c1e;
  font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}
header { margin-bottom: 20px; }
h1 { margin: 0 0 4px; font-size: 22px; }
.subtitle { margin: 0; color: #6e6e73; font-size: 13px; }
h2 { font-size: 14px; color: #3a3a3c; margin: 0 0 10px; text-transform: uppercase;
     letter-spacing: 0.04em; }
section, form.params { background: #fff; border: 1px solid #e2e2e5; border-radius: 10px;
  padding: 16px 20px; margin-bottom: 16px; }
.params-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 10px 16px; }
.params-grid label { display: flex; flex-direction: column; font-size: 12px; color: #3a3a3c;
  gap: 4px; }
.params-grid input { font-size: 13px; padding: 6px 8px; border: 1px solid #d0d0d5;
  border-radius: 6px; font-family: inherit; }
form.params button { margin-top: 14px; background: #2f5fdb; color: #fff; border: none;
  padding: 9px 18px; border-radius: 6px; font-size: 13px; cursor: pointer; }
form.params button:hover { background: #274ec0; }
.cards { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 14px; }
.card { background: #fafafa; border: 1px solid #ececee; border-radius: 8px;
  padding: 8px 14px; min-width: 130px; }
.card-label { display: block; font-size: 11px; color: #6e6e73; }
.card-value { display: block; font-size: 17px; font-weight: 600; margin-top: 2px; }
.copier-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.copier-table td { padding: 6px 8px; border-bottom: 1px solid #f0f0f0; white-space: nowrap; }
.bar { position: relative; width: 160px; height: 10px; background: #eceef1;
  border-radius: 5px; overflow: hidden; display: inline-flex; }
.bar-busy { background: #2f5fdb; height: 100%; }
.bar-maint { background: #e2a33d; height: 100%; }
.pagination { display: flex; gap: 14px; align-items: center; padding: 10px 4px; }
.page-link { font-size: 12px; color: #2f5fdb; text-decoration: none; }
.page-link:hover { text-decoration: underline; }
.page-link.disabled { color: #b6b6ba; pointer-events: none; }
.table-scroll { overflow-x: auto; max-height: 560px; overflow-y: auto; border: 1px solid #eee;
  border-radius: 8px; }
table.state-table { border-collapse: collapse; font-size: 11.5px; width: 100%;
  font-variant-numeric: tabular-nums; }
table.state-table th { position: sticky; top: 0; background: #f0f1f3; text-align: left;
  padding: 6px 8px; border-bottom: 1px solid #dcdce0; white-space: nowrap; z-index: 1; }
table.state-table td { padding: 5px 8px; border-bottom: 1px solid #f2f2f4; white-space: nowrap; }
table.state-table tbody tr:nth-child(even) { background: #fafafb; }
.state { padding: 1px 6px; border-radius: 4px; font-size: 10.5px; font-weight: 600; }
.state-free { background: #e4f6ea; color: #1f8a4c; }
.state-busy { background: #e6edfc; color: #2f5fdb; }
.state-maintenance { background: #fdefdc; color: #b06a11; }
.error-box { background: #fdecec; border: 1px solid #f3b7b7; color: #a12222;
  border-radius: 8px; padding: 12px 16px; margin-bottom: 16px; font-size: 13px; }
footer { margin-top: 24px; font-size: 11px; color: #9a9a9e; }

.card-link { text-decoration: none; color: inherit; display: block; transition: box-shadow .1s; }
.card-link:hover, .card-link:focus-visible { box-shadow: 0 0 0 1.5px #2f5fdb inset; }

.chart-wrap { position: relative; }
.chart-caption { margin: -6px 0 12px; font-size: 11.5px; color: #6e6e73; }
svg.queue-chart { width: 100%; height: auto; display: block; }
.chart-gridline { stroke: #e6e6ea; stroke-width: 1; }
.chart-axis { stroke: #c7c7cc; stroke-width: 1; }
.chart-tick-label { fill: #8a8a8e; font-size: 10px; font-family: inherit; }
.chart-area { fill: #2f5fdb; fill-opacity: 0.1; }
.chart-line { fill: none; stroke: #2f5fdb; stroke-width: 2; stroke-linejoin: round;
  stroke-linecap: round; }
.chart-max-dot { fill: #2f5fdb; stroke: #fff; stroke-width: 2; }
.chart-max-label { fill: #1c1c1e; font-size: 11px; font-weight: 600; font-family: inherit; }
.chart-capture { fill: transparent; cursor: crosshair; }
.chart-crosshair { stroke: #b6b6ba; stroke-width: 1; opacity: 0; pointer-events: none; }
.chart-hover-dot { fill: #2f5fdb; stroke: #fff; stroke-width: 2; opacity: 0; pointer-events: none; }
.chart-tooltip { position: absolute; left: 0; top: 0; opacity: 0; pointer-events: none;
  background: #1c1c1e; color: #fff; font-size: 11px; line-height: 1.45; padding: 6px 9px;
  border-radius: 6px; white-space: nowrap; transform: translate(10px, -100%);
  transition: opacity .08s; z-index: 2; }
.chart-tooltip strong { display: block; font-size: 12px; }

tr.row-max-queue { background: rgba(47, 95, 219, 0.08); box-shadow: inset 3px 0 0 #2f5fdb; }
.badge-max { margin-left: 6px; font-size: 9.5px; font-weight: 700; color: #2f5fdb; }
"""


def _parse_value(raw: str, kind: str) -> int | float | None:
    if kind == "int":
        return int(raw)
    if kind == "float":
        return float(raw)
    if kind == "optional_int":
        return int(raw) if raw != "" else None
    if kind == "optional_float":
        return float(raw) if raw != "" else None
    raise ValueError(f"tipo de campo desconocido: {kind}")


def _config_from_query(query: dict[str, list[str]]) -> SimulationConfig:
    defaults = SimulationConfig()
    kwargs: dict[str, int | float | None] = {}
    for name, _label, kind in _FIELDS:
        raw = query.get(name, [""])[0]
        if raw == "" and kind in ("int", "float"):
            kwargs[name] = getattr(defaults, name)
        else:
            kwargs[name] = _parse_value(raw, kind)
    return SimulationConfig(**kwargs)


def _query_string(config: SimulationConfig, **overrides: object) -> str:
    params: dict[str, object] = {name: getattr(config, name) for name, _l, _k in _FIELDS}
    params.update(overrides)
    clean = {k: ("" if v is None else v) for k, v in params.items()}
    return urlencode(clean)


def _nice_axis_max(raw_max: float, *, steps: int = 4) -> tuple[float, list[float]]:
    """Redondea `raw_max` al múltiplo 'lindo' (1/2/2.5/5 · 10^n) más chico que lo
    cubre y devuelve (tope, ticks de 0 al tope en `steps` pasos iguales)."""
    if raw_max <= 0:
        return 1.0, [0.0, 1.0]
    exponent = math.floor(math.log10(raw_max / steps))
    base = 10**exponent
    step = base
    for multiple in (1, 2, 2.5, 5, 10):
        step = multiple * base
        if step * steps >= raw_max:
            break
    ticks = [round(step * i, 10) for i in range(steps + 1)]
    return ticks[-1], ticks


def _downsample_for_chart(rows: list[StateRow], max_points: int = 400) -> list[StateRow]:
    """Recorta la cantidad de puntos a graficar preservando, en cada bloque, el
    primero y el de mayor `queue_length` — así una corrida de 100.000
    iteraciones no infla el SVG y el pico de cola sigue siendo visible en el
    trazo (no solo en el marcador, que además siempre usa el dato completo)."""
    n = len(rows)
    if n <= max_points:
        return rows
    picked: dict[int, StateRow] = {}
    for bucket in range(max_points):
        lo = bucket * n // max_points
        hi = max(lo + 1, (bucket + 1) * n // max_points)
        chunk = rows[lo:hi]
        picked[chunk[0].iteration] = chunk[0]
        peak = max(chunk, key=lambda r: r.queue_length)
        picked[peak.iteration] = peak
    picked[rows[-1].iteration] = rows[-1]
    return [picked[k] for k in sorted(picked)]


def render_form(config: SimulationConfig) -> str:
    inputs = []
    for name, label, kind in _FIELDS:
        value = getattr(config, name)
        value_str = "" if value is None else str(value)
        step = ' step="any"' if kind in ("float", "optional_float") else ' step="1"'
        inputs.append(
            f'<label>{html.escape(label)}'
            f'<input type="number"{step} name="{name}" value="{html.escape(value_str)}"></label>'
        )
    return f"""
<form class="params" method="get" action="/">
  <div class="params-grid">
    {"".join(inputs)}
  </div>
  <button type="submit">Ejecutar simulación</button>
</form>
"""


def render_summary(summary: SimulationSummary, config: SimulationConfig, *,
                    max_iteration: int | None, total_rows: int) -> str:
    if summary.avg_wait_time is not None:
        wait = f"{summary.avg_wait_time:.2f} min ({summary.clients_that_waited} esperaron)"
    else:
        wait = "N/A"

    # (etiqueta, valor, iteración a la que saltar si se hace click — None = card no clickeable)
    card_specs: list[tuple[str, object, int | None]] = [
        ("Cola máxima", summary.max_queue_length, max_iteration),
        ("Clientes atendidos", summary.clients_served, None),
        ("Espera promedio", wait, None),
        ("Mant. correctivos", summary.corrective_maintenance_count, None),
        ("Mant. preventivos", summary.preventive_maintenance_count, None),
        ("Tiempo simulado", f"{summary.total_time:.1f} min", None),
    ]

    card_html: list[str] = []
    for label, value, jump_iteration in card_specs:
        inner = (
            f'<span class="card-label">{html.escape(label)}</span>'
            f'<span class="card-value">{value}</span>'
        )
        if jump_iteration is None:
            card_html.append(f'<div class="card">{inner}</div>')
        else:
            jump_from = max(0, min(
                jump_iteration - config.report_row_count // 2,
                max(0, total_rows - config.report_row_count),
            ))
            qs = _query_string(config, report_from_iteration=jump_from)
            card_html.append(
                f'<a class="card card-link" href="/?{qs}" '
                f'title="Ir a la fila donde se alcanzó">{inner}</a>'
            )
    cards = "".join(card_html)

    copier_rows = "\n".join(
        f"<tr><td>Copiadora {c.id}</td>"
        f'<td><span class="bar">'
        f'<span class="bar-busy" style="width:{c.occupancy_pct * 100:.1f}%"></span>'
        f'<span class="bar-maint" style="width:{c.maintenance_pct * 100:.1f}%"></span>'
        f"</span></td>"
        f"<td>{c.occupancy_pct:.1%} ocupada</td>"
        f"<td>{c.maintenance_pct:.1%} mantenimiento</td>"
        f"<td>{c.free_pct:.1%} libre</td></tr>"
        for c in summary.copiers
    )

    return f"""
<section>
  <h2>Resumen</h2>
  <div class="cards">{cards}</div>
  <table class="copier-table"><tbody>{copier_rows}</tbody></table>
</section>
"""


def render_queue_chart(state_vector: list[StateRow], summary: SimulationSummary,
                        max_iteration: int | None) -> str:
    """Gráfico de la cola (`queue_length`) en función del reloj.

    Es un SVG en escalera (`queue_length` es constante entre eventos, no
    interpolado) armado a mano, sin librerías (DECISIONES.md D16, mismo
    criterio que el resto de la webapp). Para corridas grandes se
    submuestrea (`_downsample_for_chart`) preservando siempre el pico real,
    así el trazo nunca esconde la cola máxima aunque se recorte resolución;
    el detalle exacto de cualquier fila sigue disponible en la tabla."""
    if len(state_vector) < 2 or summary.total_time <= 0:
        return (
            '<section class="chart-wrap"><h2>Cola en el tiempo</h2>'
            '<p class="chart-caption">No hay suficientes eventos para graficar.</p></section>'
        )

    plotted = _downsample_for_chart(state_vector)
    downsampled = len(plotted) < len(state_vector)

    vb_w, vb_h = 880, 220
    ml, mr, mt, mb = 40, 14, 14, 26
    pw, ph = vb_w - ml - mr, vb_h - mt - mb

    x_max = summary.total_time
    y_max, y_ticks = _nice_axis_max(max(1, summary.max_queue_length))
    _x_step, x_ticks = _nice_axis_max(x_max, steps=5)

    def x_of(clock: float) -> float:
        return ml + (clock / x_max) * pw

    def y_of(q: float) -> float:
        return mt + ph - (q / y_max) * ph

    points = [(x_of(r.clock), y_of(r.queue_length)) for r in plotted]
    path = f"M {points[0][0]:.1f} {points[0][1]:.1f}"
    for x, y in points[1:]:
        path += f" H {x:.1f} V {y:.1f}"
    path += f" H {ml + pw:.1f}"
    area = path + f" V {mt + ph:.1f} H {points[0][0]:.1f} Z"

    grid = "".join(
        f'<line class="chart-gridline" x1="{ml}" x2="{ml + pw}" y1="{y_of(t):.1f}" '
        f'y2="{y_of(t):.1f}"></line>'
        f'<text class="chart-tick-label" x="{ml - 8}" y="{y_of(t) + 3:.1f}" '
        f'text-anchor="end">{t:g}</text>'
        for t in y_ticks
    )
    x_axis_labels = "".join(
        f'<text class="chart-tick-label" x="{x_of(t):.1f}" y="{mt + ph + 18}" '
        f'text-anchor="middle">{t:g}</text>'
        for t in x_ticks if t <= x_max
    )

    max_marker = ""
    if max_iteration is not None:
        max_row = next((r for r in state_vector if r.iteration == max_iteration), None)
        if max_row is not None:
            mx, my = x_of(max_row.clock), y_of(max_row.queue_length)
            label_y = my - 10 if my - 10 > mt + 8 else my + 16
            max_marker = (
                f'<circle class="chart-max-dot" cx="{mx:.1f}" cy="{my:.1f}" r="4">'
                f"<title>Cola máxima: {max_row.queue_length} clientes en "
                f"t={max_row.clock:.2f} min (iteración {max_row.iteration})</title>"
                "</circle>"
                f'<text class="chart-max-label" x="{mx:.1f}" y="{label_y:.1f}" '
                f'text-anchor="middle">Cola máx: {max_row.queue_length}</text>'
            )

    chart_data = json.dumps(
        [{"t": round(r.clock, 4), "q": r.queue_length, "i": r.iteration} for r in plotted]
    )
    plot_meta = html.escape(json.dumps(
        {"vbw": vb_w, "ml": ml, "pw": pw, "mt": mt, "ph": ph, "xmax": x_max, "ymax": y_max}
    ))

    caption = (
        f"Submuestreado a {len(plotted)} de {len(state_vector)} filas para performance — "
        "el detalle exacto de cada evento sigue en la tabla debajo."
        if downsampled else f"{len(plotted)} eventos graficados."
    )

    return f"""
<section class="chart-wrap">
  <h2>Cola en el tiempo</h2>
  <p class="chart-caption">{html.escape(caption)}</p>
  <svg class="queue-chart" id="queue-chart" viewBox="0 0 {vb_w} {vb_h}" data-plot='{plot_meta}'>
    {grid}
    <line class="chart-axis" x1="{ml}" x2="{ml}" y1="{mt}" y2="{mt + ph}"></line>
    <line class="chart-axis" x1="{ml}" x2="{ml + pw}" y1="{mt + ph}" y2="{mt + ph}"></line>
    <path class="chart-area" d="{area}"></path>
    <path class="chart-line" d="{path}"></path>
    {x_axis_labels}
    {max_marker}
    <rect class="chart-capture" x="{ml}" y="{mt}" width="{pw}" height="{ph}"></rect>
    <line class="chart-crosshair" x1="{ml}" x2="{ml}" y1="{mt}" y2="{mt + ph}"></line>
    <circle class="chart-hover-dot" cx="{ml}" cy="{mt}" r="4"></circle>
  </svg>
  <div class="chart-tooltip" id="queue-chart-tooltip"></div>
  <script type="application/json" id="queue-chart-data">{chart_data}</script>
  <script>
(function () {{
  var svg = document.getElementById("queue-chart");
  var wrap = svg.closest(".chart-wrap");
  var plot = JSON.parse(svg.getAttribute("data-plot"));
  var pts = JSON.parse(document.getElementById("queue-chart-data").textContent);
  var capture = svg.querySelector(".chart-capture");
  var crosshair = svg.querySelector(".chart-crosshair");
  var dot = svg.querySelector(".chart-hover-dot");
  var tooltip = document.getElementById("queue-chart-tooltip");

  function nearest(clock) {{
    var lo = 0, hi = pts.length - 1;
    while (lo < hi) {{
      var mid = (lo + hi) >> 1;
      if (pts[mid].t < clock) {{ lo = mid + 1; }} else {{ hi = mid; }}
    }}
    if (lo > 0 && Math.abs(pts[lo - 1].t - clock) < Math.abs(pts[lo].t - clock)) {{ lo -= 1; }}
    return pts[lo];
  }}

  function onMove(evt) {{
    var svgRect = svg.getBoundingClientRect();
    var wrapRect = wrap.getBoundingClientRect();
    var scale = svgRect.width / plot.vbw;
    var xSvg = (evt.clientX - svgRect.left) / scale;
    var clock = Math.max(0, Math.min(plot.xmax, ((xSvg - plot.ml) / plot.pw) * plot.xmax));
    var p = nearest(clock);
    var x = plot.ml + (p.t / plot.xmax) * plot.pw;
    var y = plot.mt + plot.ph - (p.q / plot.ymax) * plot.ph;

    crosshair.setAttribute("x1", x); crosshair.setAttribute("x2", x);
    crosshair.setAttribute("opacity", "1");
    dot.setAttribute("cx", x); dot.setAttribute("cy", y);
    dot.setAttribute("opacity", "1");

    tooltip.innerHTML = "";
    var strong = document.createElement("strong");
    strong.textContent = p.q + " en cola";
    var span = document.createElement("span");
    span.textContent = "t=" + p.t.toFixed(2) + " min \\u00b7 iteraci\\u00f3n " + p.i;
    tooltip.appendChild(strong);
    tooltip.appendChild(span);
    tooltip.style.left = ((svgRect.left - wrapRect.left) + x * scale) + "px";
    tooltip.style.top = ((svgRect.top - wrapRect.top) + y * scale) + "px";
    tooltip.style.opacity = "1";
  }}

  function onLeave() {{
    crosshair.setAttribute("opacity", "0");
    dot.setAttribute("opacity", "0");
    tooltip.style.opacity = "0";
  }}

  capture.addEventListener("pointermove", onMove);
  capture.addEventListener("pointerleave", onLeave);
}})();
  </script>
</section>
"""


def render_pagination(config: SimulationConfig, total_rows: int) -> str:
    prev_from = max(0, config.report_from_iteration - config.report_row_count)
    next_from = config.report_from_iteration + config.report_row_count
    has_prev = config.report_from_iteration > 0
    has_next = next_from < total_rows

    if has_prev:
        prev_qs = _query_string(config, report_from_iteration=prev_from)
        prev_link = f'<a class="page-link" href="/?{prev_qs}">« Iteraciones anteriores</a>'
    else:
        prev_link = '<span class="page-link disabled">« Iteraciones anteriores</span>'

    if has_next:
        next_qs = _query_string(config, report_from_iteration=next_from)
        next_link = f'<a class="page-link" href="/?{next_qs}">Iteraciones siguientes »</a>'
        last_qs = _query_string(
            config, report_from_iteration=max(0, total_rows - config.report_row_count)
        )
        last_link = f'<a class="page-link" href="/?{last_qs}">Ir al final »»</a>'
    else:
        next_link = '<span class="page-link disabled">Iteraciones siguientes »</span>'
        last_link = '<span class="page-link disabled">Ir al final »»</span>'

    return f'<div class="pagination">{prev_link}{next_link}{last_link}</div>'


def render_table(rows: list[StateRow], n_copiers: int, *, title: str,
                  hide_clients: bool = False, highlight_iteration: int | None = None) -> str:
    headers = ["Iter", "Reloj", "Evento", "RND lleg", "T lleg", "RND atenc", "T atenc",
               "RND umbral", "T umbral"]
    for i in range(n_copiers):
        headers += [f"Cop{i} Estado", f"Cop{i} Uso", f"Cop{i} Cliente"]
    headers += ["Cola", "ColaMáx", "Atendidos", "Correctivos", "Preventivos"]
    header_html = "".join(f"<th>{h}</th>" for h in headers)

    body_rows = []
    for row in rows:
        rnd_lleg = f"{row.llegada.rnd:.4f}" if row.llegada else "-"
        t_lleg = f"{row.llegada.value:.2f}" if row.llegada else "-"
        rnd_at = f"{row.atencion.rnd:.4f}" if row.atencion else "-"
        t_at = f"{row.atencion.value:.2f}" if row.atencion else "-"
        if row.umbral:
            rnd_umb = ",".join(f"{d.rnd:.4f}" for _, d in row.umbral)
            t_umb = ",".join(f"{d.value:.2f}" for _, d in row.umbral)
        else:
            rnd_umb = t_umb = "-"

        tds = [
            f"<td>{row.iteration}</td>", f"<td>{row.clock:.2f}</td>",
            f"<td>{event_label(row.event_type)}</td>",
            f"<td>{rnd_lleg}</td>", f"<td>{t_lleg}</td>",
            f"<td>{rnd_at}</td>", f"<td>{t_at}</td>",
            f"<td>{rnd_umb}</td>", f"<td>{t_umb}</td>",
        ]
        for c in row.copiers:
            client_field = str(c.client_id) if (not hide_clients and c.client_id is not None) \
                else "-"
            tds.append(
                f'<td><span class="state state-{c.state.lower()}">{state_label(c.state)}'
                f"</span></td>"
            )
            tds.append(f"<td>{c.usage_remaining:.1f}</td>")
            tds.append(f"<td>{client_field}</td>")
        is_max_row = row.iteration == highlight_iteration
        cola_badge = ' <span class="badge-max">◆ máx</span>' if is_max_row else ""
        tds += [
            f"<td>{row.queue_length}{cola_badge}</td>", f"<td>{row.max_queue_length}</td>",
            f"<td>{row.clients_served}</td>", f"<td>{row.corrective_maintenance_count}</td>",
            f"<td>{row.preventive_maintenance_count}</td>",
        ]
        row_class = ' class="row-max-queue"' if is_max_row else ""
        body_rows.append(f"<tr{row_class}>{''.join(tds)}</tr>")

    body_html = "\n".join(body_rows) if body_rows else \
        f'<tr><td colspan="{len(headers)}">(sin filas)</td></tr>'

    return f"""
<section>
  <h2>{html.escape(title)}</h2>
  <div class="table-scroll">
    <table class="state-table">
      <thead><tr>{header_html}</tr></thead>
      <tbody>{body_html}</tbody>
    </table>
  </div>
</section>
"""


def render_page(config: SimulationConfig, sim: Simulation) -> str:
    summary = sim.summary()
    total_rows = len(sim.state_vector)
    j = max(0, min(config.report_from_iteration, max(0, total_rows - 1)))
    window = sim.state_vector[j: j + config.report_row_count]
    last = sim.state_vector[-1]

    # None si nunca se formó cola: no tiene sentido resaltar/enlazar una fila
    # "pico" cuando cualquier fila vale 0.
    max_iteration = None
    if summary.max_queue_length > 0:
        max_iteration = next(
            (r.iteration for r in sim.state_vector
             if r.queue_length == summary.max_queue_length),
            None,
        )

    window_title = (
        f"Vector de estado — filas {j} a {j + len(window) - 1} de {total_rows - 1} "
        f"(iteración final={last.iteration}, reloj final={last.clock:.2f} min)"
    )

    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Centro de Copiado — Simulación</title>
<style>{_CSS}</style>
</head>
<body>
<header>
  <h1>Centro de Copiado</h1>
  <p class="subtitle">Simulación de eventos discretos — interfaz de exploración (no forma parte
  del entregable del TP, ver README.md)</p>
</header>
{render_form(config)}
{render_summary(summary, config, max_iteration=max_iteration, total_rows=total_rows)}
{render_queue_chart(sim.state_vector, summary, max_iteration)}
{render_pagination(config, total_rows)}
{render_table(window, config.n_copiers, title=window_title, highlight_iteration=max_iteration)}
{render_table([last], config.n_copiers, title="Última fila (sin objetos temporales)",
               hide_clients=True, highlight_iteration=max_iteration)}
<footer>Cada carga de página corre la simulación completa desde el principio con los
parámetros del formulario (no hay estado guardado entre requests) — DECISIONES.md.</footer>
</body>
</html>"""


def render_error_page(config: SimulationConfig, exc: Exception) -> str:
    return f"""<!doctype html>
<html lang="es">
<head><meta charset="utf-8"><title>Error — Centro de Copiado</title><style>{_CSS}</style></head>
<body>
<header><h1>Centro de Copiado</h1></header>
<div class="error-box"><strong>Error al correr la simulación:</strong> {html.escape(str(exc))}</div>
{render_form(config)}
</body>
</html>"""


_LANDING_MAX_ITERATIONS = 200
"""Tope de iteraciones para la primera carga de "/" (sin query string).

Los defaults reales de SimulationConfig (mean_interarrival_time=0.25, sin confirmar aún
con la cátedra — SUPUESTOS.md #1) describen una tasa de arribo mayor que la capacidad de
servicio: la cola crece sin límite. Combinado con el O(n²) conocido de `Simulation`
(rebuilds `clients_in_queue` en cada fila, ver PROGRESO.md), correr la landing page con
max_iterations=100_000 tal cual cuelga el server. Este tope solo aplica a la carga
inicial; el formulario sigue permitiendo pedir cualquier valor a mano.
"""


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 (nombre impuesto por BaseHTTPRequestHandler)
        parsed = urlparse(self.path)
        if parsed.path not in ("/", ""):
            self.send_error(404, "No encontrado")
            return

        query = parse_qs(parsed.query)
        if not query:
            query = {"max_iterations": [str(_LANDING_MAX_ITERATIONS)]}
        try:
            config = _config_from_query(query)
        except (ValueError, TypeError) as exc:
            self._respond(400, render_error_page(SimulationConfig(), exc))
            return

        try:
            sim = Simulation(config)
            sim.run()
        except Exception as exc:  # límite del sistema: parámetros válidos pero absurdos
            self._respond(500, render_error_page(config, exc))
            return

        self._respond(200, render_page(config, sim))

    def _respond(self, status: int, body: str) -> None:
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="copy_center.webapp",
        description="Interfaz web local para explorar la simulación (complementaria al CLI).",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)

    server = HTTPServer((args.host, args.port), _Handler)
    print(f"Interfaz web en http://{args.host}:{args.port}/  (Ctrl+C para cortar)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
