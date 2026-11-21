"""A local results browser for capri-mod's stored runs, in the spirit of CAPRI's GUI exploitation tools: pick a run,
filter the results by block, region, item and column, see them as a pivot table and a chart, compare the scenario
with its baseline, two runs with each other, and a run with CAPRI's figures.

Read-only: it reads results stores (capri_mod/io_results.py) and never writes to them or runs the model.

Usage:
    python capri_gradio/results_browser.py [--store DIR ...] [--port 7860] [--host 127.0.0.1]

--store defaults to the run script's store (the setting run.results_dir, relative to the repository's root); give it
more than once to browse several stores (e.g. two worktrees' results). Needs gradio (pip install ".[gui]").
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

__import__("sys").path.insert(0, str(Path(__file__).resolve().parent))
import results_data as RD  # noqa: E402

MAX_TABLE_ROWS = 5000      # rows sent to the table view (the CSV download has them all)
MAX_CHART_BARS = 60        # bars in the chart (the largest by absolute value of the measure)
#: one colour per convergence measure (an explicit map, so the line chart draws its legend)
CONV_COLOURS = dict(zip(RD.CONV_MEASURES,
                        ("#2a6fdb", "#e8590c", "#c92a2a", "#2b8a3e", "#7048e8", "#868e96", "#d6a400")))


# --------------------------------------------------------------------------- #
# Figures (plotly; colours from the reference palette of the dataviz method: diverging blue <-> red with a grey
# midpoint for changes, one blue ramp for levels, categorical blue then orange for two series)
# --------------------------------------------------------------------------- #
DIVERGING = [[0.0, "#e34948"], [0.5, "#f0efec"], [1.0, "#2a78d6"]]      # decrease red, no change grey, increase blue
SEQUENTIAL = [[0.0, "#cde2fb"], [0.5, "#3987e5"], [1.0, "#0d366b"]]
SERIES = ("#2a78d6", "#eb6834")
GISCO_NOTE = "Boundaries: Eurostat GISCO, NUTS 2024 (c) EuroGeographics"



#: buttons as wide as their label (Gradio stretches a button to the row's or column's width otherwise); in a row they
#: sit at the bottom, level with the inputs beside them
BUTTON_CSS = """
.capri-btn { flex-grow: 0 !important; flex-basis: auto !important; width: auto !important; min-width: 7em !important;
             max-width: 16em; align-self: flex-end; }
.column > .capri-btn, .tabitem > .capri-btn, .gap > .capri-btn:only-child { align-self: flex-start; }
"""
BTN = dict(scale=0, min_width=0, elem_classes=["capri-btn"])

#: the tabs as a menu (the project lead, 18 November 2026: Gradio's tabs read as plain text): bold labels on a tinted
#: ground with a frame, the open tab in the accent colour with a bar under it, the disabled ones dimmed. The page's top
#: tabs carry the class capri-tabs-top, the results' tabs capri-tabs-sub; the tabs nested in either take the sub style.
#: Gradio's theme variables, so the dark theme follows
_TAB = 'button[role="tab"]'
_TABS_TOP = f".capri-tabs-top > .tab-wrapper {_TAB}"
_TABS_SUB = (f".capri-tabs-sub > .tab-wrapper {_TAB}, .capri-tabs-sub .tabs > .tab-wrapper {_TAB}, "
             f".capri-tabs-top .tabs > .tab-wrapper {_TAB}")


def _sel(group: str, suffix: str) -> str:
    return ", ".join(x.strip() + suffix for x in group.split(","))


TAB_CSS = f"""
{_TABS_TOP}, {_TABS_SUB} {{
  font-weight: 600 !important; color: var(--body-text-color) !important;
  background: var(--background-fill-secondary) !important;
  border: 1px solid var(--border-color-primary) !important; border-bottom: none !important;
  border-radius: 8px 8px 0 0 !important; margin-right: 4px !important; padding: 0.45em 1em !important;
}}
{_TABS_TOP} {{ font-weight: 700 !important; font-size: 1.05rem !important; padding: 0.55em 1.25em !important; }}
{_sel(_TABS_TOP, ".selected")}, {_sel(_TABS_SUB, ".selected")} {{
  background: var(--color-accent-soft) !important; color: var(--color-accent) !important;
  box-shadow: inset 0 -3px 0 var(--color-accent) !important;
}}
{_sel(_TABS_TOP, ":hover:not(:disabled):not(.selected)")}, {_sel(_TABS_SUB, ":hover:not(:disabled):not(.selected)")} {{
  background: var(--background-fill-primary) !important; color: var(--color-accent) !important;
}}
{_sel(_TABS_TOP, ":disabled")} {{ opacity: 0.45 !important; cursor: not-allowed !important; }}
"""
#: the results page's style: the buttons and the tabs
PAGE_STYLE = BUTTON_CSS + TAB_CSS


# Gradio 5 and 6 both: Gradio 6.0 moved css from the Blocks constructor to launch(), replaced launch(show_api) by
# footer_links and dropped Chatbot(type=...) (messages are its only format). The keyword arguments for the version
# installed, read off its signatures.
def _accepts(fn, name: str) -> bool:
    import inspect
    try:
        return name in inspect.signature(fn).parameters
    except (TypeError, ValueError):
        return False


def blocks_args(css: str) -> dict:
    """gr.Blocks(...)'s style argument: css on the constructor up to Gradio 5, none from Gradio 6 (launch_args)."""
    import gradio as gr
    return {"css": css} if _accepts(gr.Blocks.__init__, "css") else {}


def launch_args(css: str) -> dict:
    """app.launch(...)'s arguments: no API page link (show_api=False up to Gradio 5, footer_links without "api" from
    Gradio 6) and, from Gradio 6, the css."""
    import gradio as gr
    a = {}
    if _accepts(gr.Blocks.launch, "show_api"):
        a["show_api"] = False
    if _accepts(gr.Blocks.launch, "footer_links"):
        a["footer_links"] = ["gradio", "settings"]
    if _accepts(gr.Blocks.launch, "css") and not _accepts(gr.Blocks.__init__, "css"):
        a["css"] = css
    return a


def chatbot_args() -> dict:
    """gr.Chatbot(...)'s message format: type="messages" up to Gradio 5, the only format from Gradio 6."""
    import gradio as gr
    return {"type": "messages"} if _accepts(gr.Chatbot.__init__, "type") else {}

def _layout(fig, title: str, height: int):
    fig.update_layout(title=dict(text=title, x=0.01, font=dict(size=15)), height=height,
                      margin=dict(l=10, r=10, t=50, b=40), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", font=dict(size=12))
    return fig


def map_figure(frame: pd.DataFrame, measure: str, title: str, lim=None):
    """A choropleth of a map_frame on NUTS 2024: a change on the diverging scale centred at 0, a level on the blue
    ramp; regions without a value grey; hover with the region, the value and the CAPRI units behind it. lim: the
    change's saturation (default the 90th percentile of |value|; two maps to be compared take the same)."""
    import plotly.graph_objects as go
    geo = RD.nuts_geometry()
    names = {f["id"]: f["properties"]["name"] for f in geo["features"]}
    f = frame.dropna(subset=["value"])
    change = measure in ("% change", "scenario - baseline")
    # colours saturate at the 90th percentile of |value| (a region with a tiny base can change by 1000%); the hover
    # shows every region's own value
    if lim is None:
        lim = _saturation(f["value"])
    text = [f"{n} ({c})<br>CAPRI units: {u}" + (f"<br>{note}" if note else "")
            for c, n, u, note in zip(f["nuts2024"], f["nuts2024"].map(names), f["units"], f["note"])]
    fig = go.Figure()
    fig.add_trace(go.Choropleth(geojson=geo, locations=list(geo and [x["id"] for x in geo["features"]]),
                                z=[0] * len(geo["features"]), featureidkey="id", showscale=False,
                                colorscale=[[0, "#e7e6e2"], [1, "#e7e6e2"]], marker_line_color="#ffffff",
                                marker_line_width=0.4, hoverinfo="skip"))
    fig.add_trace(go.Choropleth(
        geojson=geo, locations=f["nuts2024"], z=f["value"], featureidkey="id", text=text,
        hovertemplate="%{text}<br><b>%{z:,.2f}</b><extra></extra>",
        colorscale=DIVERGING if change else SEQUENTIAL, zmid=0 if change else None,
        zmin=-lim if change else None, zmax=lim if change else None,
        marker_line_color="#ffffff", marker_line_width=0.4,
        colorbar=dict(title=dict(text=measure + (f"<br>(saturates at ±{lim:,.3g})" if change else "")),
                      thickness=12, len=0.7)))
    # Europe's mainland and islands (the outermost regions, e.g. the Canaries or the French overseas departments, are
    # drawn but outside the view)
    fig.update_geos(visible=False, projection_type="mercator", lataxis_range=[34, 71.5], lonaxis_range=[-25, 45])
    fig.add_annotation(text=GISCO_NOTE, x=0, y=0, xref="paper", yref="paper", showarrow=False,
                       font=dict(size=10, color="#6b6b66"), xanchor="left", yanchor="bottom")
    return _layout(fig, title, 620)


def _saturation(values) -> float:
    """The colour scale's saturation of a change map: the 90th percentile of |value| (a region with a tiny base can
    change by 1000%)."""
    v = np.abs(pd.Series(values, dtype=float).dropna())
    return max(float(np.percentile(v, 90)), 1e-9) if len(v) else 1.0


def bar_figure(labels, values, title: str, axis: str, colour: str = SERIES[0]):
    """Horizontal bars, sorted, one series (no legend), a zero line."""
    import plotly.graph_objects as go
    d = pd.DataFrame({"l": list(labels), "v": list(values)}).dropna().sort_values("v")
    fig = go.Figure(go.Bar(x=d["v"], y=d["l"], orientation="h", marker_color=colour, marker_line_width=0,
                           hovertemplate="%{y}: <b>%{x:,.2f}</b><extra></extra>"))
    fig.add_vline(x=0, line_width=1, line_color="#8a8984")
    fig.update_xaxes(title=axis, gridcolor="#e7e6e2", zeroline=False)
    fig.update_yaxes(title=None)
    return _layout(fig, title, max(300, 22 * len(d) + 90))


def indicator_figure(ind: pd.DataFrame, run_cols: list):
    """capri-mod's Farm-to-Fork indicators (% change from the baseline) beside JRC121368's: grouped horizontal bars,
    the run(s) in blue (one run) and JRC121368 in orange, a legend."""
    import plotly.graph_objects as go
    d = ind.iloc[::-1]
    fig = go.Figure()
    colours = list(SERIES) if len(run_cols) == 1 else ["#2a78d6", "#1baf7a", "#6250d6", "#e87ba4"]
    for k, c in enumerate(run_cols):
        fig.add_trace(go.Bar(y=d["indicator"], x=d[c], orientation="h", name=f"capri-mod: {c}",
                             marker_color=colours[k % len(colours)],
                             hovertemplate="%{y}: <b>%{x:+.1f}%</b><extra>" + c + "</extra>"))
    fig.add_trace(go.Bar(y=d["indicator"], x=d["JRC121368 (CAPRI)"], orientation="h", name="JRC121368 (CAPRI)",
                         marker_color=SERIES[1], hovertemplate="%{y}: <b>%{x:+.1f}%</b><extra>JRC121368</extra>"))
    fig.add_vline(x=0, line_width=1, line_color="#8a8984")
    fig.update_layout(barmode="group", bargap=0.25, bargroupgap=0.08,
                      legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0))
    fig.update_xaxes(title="% change from the baseline (EU27)", gridcolor="#e7e6e2", zeroline=False)
    return _layout(fig, "Farm-to-Fork indicators: capri-mod compared with JRC121368", 820)


def pair_figure(labels, model, capri, title: str, axis: str, ref_name: str = "CAPRI"):
    """The model's % changes beside CAPRI's (or another reference's, ref_name), grouped horizontal bars in the order
    given (capri-mod blue, the reference orange, a legend)."""
    import plotly.graph_objects as go
    d = pd.DataFrame({"l": list(labels), "m": list(model), "c": list(capri)}).iloc[::-1]
    fig = go.Figure()
    fig.add_trace(go.Bar(y=d["l"], x=d["m"], orientation="h", name="capri-mod", marker_color=SERIES[0],
                         hovertemplate="%{y}: <b>%{x:+.1f}</b><extra>capri-mod</extra>"))
    fig.add_trace(go.Bar(y=d["l"], x=d["c"], orientation="h", name=ref_name, marker_color=SERIES[1],
                         hovertemplate="%{y}: <b>%{x:+.1f}</b><extra>" + ref_name + "</extra>"))
    fig.add_vline(x=0, line_width=1, line_color="#8a8984")
    fig.update_layout(barmode="group", bargap=0.25, bargroupgap=0.08,
                      legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0))
    fig.update_xaxes(title=axis, gridcolor="#e7e6e2", zeroline=False)
    fig.update_yaxes(title=None)
    return _layout(fig, title, max(320, 34 * len(d) + 110))


def scatter_figure(frame: pd.DataFrame, title: str):
    """The regional units' % changes, the model's (y) and CAPRI's (x), with the diagonal; hover with the unit."""
    import plotly.graph_objects as go
    f = frame.dropna(subset=["model_pct", "capri_pct"])
    lo = float(min(f["model_pct"].min(), f["capri_pct"].min(), 0.0)) if len(f) else -1.0
    hi = float(max(f["model_pct"].max(), f["capri_pct"].max(), 0.0)) if len(f) else 1.0
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[lo, hi], y=[lo, hi], mode="lines", line=dict(color="#8a8984", width=1, dash="dot"),
                             hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(x=f["capri_pct"], y=f["model_pct"], mode="markers", text=f["capri_unit"],
                             marker=dict(size=8, color=SERIES[0], line=dict(color="#ffffff", width=1)),
                             hovertemplate="%{text}<br>CAPRI %{x:+.1f}%<br>capri-mod %{y:+.1f}%<extra></extra>",
                             showlegend=False))
    fig.update_xaxes(title="CAPRI, % change", gridcolor="#e7e6e2", zeroline=True, zerolinecolor="#c9c8c3")
    fig.update_yaxes(title="capri-mod, % change", gridcolor="#e7e6e2", zeroline=True, zerolinecolor="#c9c8c3")
    return _layout(fig, title, 520)


def _labels(root) -> list:
    """The store's runs for a dropdown: (label with the run's date, the label the callbacks parse)."""
    return RD.run_choices(root)


def _first(choices: list):
    return choices[0][1] if choices else None


def _filters(region, rows, cols, dim5) -> dict:
    return {"region": region or [], "rows": rows or [], "cols": cols or [], "dim5": dim5 or []}


def _csv(df: pd.DataFrame, name: str) -> str:
    import tempfile
    fd, p = tempfile.mkstemp(prefix=f"capri_mod_{name}_", suffix=".csv")
    with open(fd, "w", newline="") as fh:
        df.to_csv(fh, index=False)
    return p


def _shown(df: pd.DataFrame) -> pd.DataFrame:
    """A table for the screen: at most MAX_TABLE_ROWS rows, numbers to 6 significant digits (the CSV keeps them
    all)."""
    d = df.head(MAX_TABLE_ROWS).copy()
    for c in d.columns:
        if pd.api.types.is_float_dtype(d[c]):
            d[c] = d[c].map(lambda v: float(f"{v:.6g}") if pd.notna(v) else v)
    return d


def _chart_frame(table: pd.DataFrame, measure: str, row_dim: str, col_dim: str) -> pd.DataFrame:
    """The pivot's cells as one bar each (no stacking: x is the cell's "down | across" label), the largest
    MAX_CHART_BARS by absolute value; coloured by the across value when there are at most 10 of them."""
    if table.empty:
        return pd.DataFrame(columns=["x", "value", "series"])
    t = table.copy()
    t.index = t.index.astype(str)
    t.columns = t.columns.astype(str)
    idx = t.index.name or "index"
    long = t.reset_index().melt(id_vars=idx, var_name="across", value_name="value").dropna(subset=["value"])
    single = col_dim in (None, "", row_dim)
    long["x"] = long[idx] if single else long[idx] + " | " + long["across"]
    long["series"] = measure if single or long["across"].nunique() > 10 else long["across"]
    keep = long.assign(a=long["value"].abs()).nlargest(MAX_CHART_BARS, "a")
    return keep[["x", "value", "series"]].sort_values("value")


def _keep_selected(codes: list, selected, dim: str = "", block=None) -> dict:
    """A dropdown's new choices, each code shown with its name (the value stays the code), with its selection kept and
    given again: a multiselect dropdown whose choices change otherwise may show other labels than the values it
    sends."""
    import gradio as gr
    sel = list(selected or [])
    return gr.update(choices=[(RD.code_label(c, dim, block), c) for c in sorted(set(codes) | set(sel))], value=sel)


def _named(table: pd.DataFrame, down: str, across, block=None) -> pd.DataFrame:
    """A pivot with each code of its index and columns shown with its name."""
    t = table.copy()
    t.index = [RD.code_label(v, down, block) for v in t.index]
    t.index.name = down
    if across and across != down:
        t.columns = [RD.code_label(v, across, block) for v in t.columns]
    return t


def build(stores: list):
    """The results browser as a page of its own."""
    import gradio as gr
    with gr.Blocks(title="capri-mod results", **blocks_args(PAGE_STYLE)) as app:
        gr.Markdown("## capri-mod results browser\nRead-only view of stored runs (`results_dir`). "
                    "Pick a store and a run; the filters narrow the rows, the pivot puts one dimension down and one "
                    "across.")
        add_results(stores, app)
    return app


def add_results(stores: list, app):
    """The results browser's components and events, inside the page being built (app: its gr.Blocks, for the load
    events); capri_gradio/capri_gui.py puts them in its Results tab."""
    import gradio as gr
    store_names = [str(s) for s in stores]
    dim_names = list(RD.DIMS)
    labs0 = _labels(stores[0])          # the first store's runs, shown before the page's load event fills them
    first0 = _first(labs0)

    with gr.Column():
        store = gr.Dropdown(store_names, value=store_names[0], label="results store", allow_custom_value=True)

        # the result tabs; the page opens on the comparison with CAPRI
        with gr.Tabs(selected="capri", elem_classes=["capri-tabs-sub"]):
            # ------------------------------------------------------------------ runs
            with gr.Tab("Runs"):
                gr.Markdown("The runs in the store, newest first. Pick one to see how it converged, its metadata and "
                            "the "
                            "settings it ran with.")
                refresh = gr.Button("Reload runs", size="sm", **BTN)
                runs_df = gr.Dataframe(interactive=False, wrap=False, max_height=420, show_search="filter",
                                       pinned_columns=1, label="scenario runs (newest first)")
                with gr.Row():
                    run_pick = gr.Dropdown(labs0, value=first0, label="run", interactive=True, scale=3)
                    conv_point = gr.Radio(["baseline", "scenario"], value="scenario", label="point", scale=1)
                conv_plot = gr.LinePlot(x="it", y="value", color="measure", color_title="measure",
                                        color_map=CONV_COLOURS,
                                        x_title="outer iteration",
                                        y_title="log10 of the measure",
                                        label="convergence measures per outer iteration (a measure at 0 is not drawn)",
                                        height=340)
                # the colour key in text: Gradio 5.49's line chart draws the legend's title without its entries here
                gr.Markdown("\n".join(f'- <span style="color:{CONV_COLOURS[k]}">&#9632;</span> `{k}`: {v}'
                                       for k, v in RD.CONV_MEASURES.items()))
                summary = gr.JSON(label="run metadata: convergence, solver fallbacks, settings changed, code version")
                with gr.Accordion("effective settings (settings.toml)", open=False):
                    settings_txt = gr.Code(language=None, label="settings")

            # ------------------------------------------------------------------ scenario and its baseline
            with gr.Tab("Scenario and its baseline"):
                gr.Markdown("Shows a run's scenario beside its own baseline: pick a block, narrow the rows with the "
                            "filters, choose the measure and what goes down and across the table, then press Show.")
                with gr.Row():
                    sv_run = gr.Dropdown(labs0, value=first0, label="run")
                    sv_block = gr.Dropdown([], label="block")
                with gr.Row():
                    sv_region = gr.Dropdown([], multiselect=True, label="region")
                    sv_rows = gr.Dropdown([], multiselect=True, label="item (rows)")
                    sv_cols = gr.Dropdown([], multiselect=True, label="column (cols)")
                    sv_dim5 = gr.Dropdown([], multiselect=True, label="dim5")
                with gr.Row():
                    sv_measure = gr.Radio(list(RD.MEASURES), value="% change", label="measure")
                    sv_down = gr.Dropdown(dim_names, value="region", label="down")
                    sv_across = gr.Dropdown([""] + dim_names, value="rows", label="across")
                    sv_go = gr.Button("Show", variant="primary", **BTN)
                sv_msg = gr.Markdown()
                sv_table = gr.Dataframe(interactive=False, label="pivot")
                sv_chart = gr.BarPlot(x="x", y="value", color="series", label="chart", height=460, sort="y",
                                      x_label_angle=-60)
                with gr.Accordion("matched rows", open=False):
                    sv_rows_df = gr.Dataframe(interactive=False)
                    sv_file = gr.File(label="download (CSV)")

            # ------------------------------------------------------------------ two runs
            with gr.Tab("Compare two runs"):
                gr.Markdown("Compares two runs, from the same store or from two stores, row by row: where they "
                            "differ, as "
                            "a table and a chart.")
                with gr.Row():
                    store_b = gr.Dropdown(store_names, value=store_names[-1], label="store of run B",
                                          allow_custom_value=True)
                with gr.Row():
                    cr_a = gr.Dropdown(labs0, value=first0, label="run A")
                    cr_pa = gr.Radio(["baseline", "scenario"], value="scenario", label="point of A")
                    cr_b = gr.Dropdown([], label="run B")
                    cr_pb = gr.Radio(["baseline", "scenario"], value="scenario", label="point of B")
                with gr.Row():
                    cr_block = gr.Dropdown([], label="block")
                    cr_region = gr.Dropdown([], multiselect=True, label="region")
                    cr_rows = gr.Dropdown([], multiselect=True, label="item (rows)")
                    cr_cols = gr.Dropdown([], multiselect=True, label="column (cols)")
                with gr.Row():
                    cr_measure = gr.Radio(["A", "B", "B - A", "% change"], value="% change", label="measure")
                    cr_down = gr.Dropdown(dim_names, value="region", label="down")
                    cr_across = gr.Dropdown([""] + dim_names, value="rows", label="across")
                    cr_go = gr.Button("Compare", variant="primary", **BTN)
                cr_msg = gr.Markdown()
                cr_dev = gr.Dataframe(interactive=False, label="where the runs differ (per block and column)")
                cr_table = gr.Dataframe(interactive=False, label="pivot")
                cr_chart = gr.BarPlot(x="x", y="value", color="series", label="chart", height=460, sort="y",
                                      x_label_angle=-60)
                cr_file = gr.File(label="matched rows (CSV)")

            # ------------------------------------------------------------------ CAPRI
            with gr.Tab("Map"):
                gr.Markdown("Draws one result of a run on a map of the EU's regions: pick a block and an item, and "
                            "whether to show the scenario, the baseline or the change between them. Where one of the "
                            "model's regional units covers several regions, each of them shows the unit's value (an "
                            "area "
                            "or a quantity is split by the regions' farmland). Below the map, the same item added up "
                            "by "
                            "member state, for items that can be added up.")
                with gr.Row():
                    mp_run = gr.Dropdown(labs0, value=first0, label="run", scale=3)
                    mp_block = gr.Dropdown([], label="block", scale=1)
                with gr.Row():
                    mp_item = gr.Dropdown([], label="item (rows · cols · dim5 [unit])", scale=3)
                    mp_measure = gr.Radio(list(RD.MEASURES), value="% change", label="measure", scale=2)
                mp_go = gr.Button("Draw", variant="primary", **BTN)
                mp_msg = gr.Markdown()
                mp_map = gr.Plot(label="map")
                mp_ms = gr.Plot(label="by member state")
                with gr.Accordion("regions (table)", open=False):
                    mp_table = gr.Dataframe(interactive=False)

            with gr.Tab("Charts"):
                gr.Markdown("Puts the Farm-to-Fork indicators of up to four runs side by side (EU27, % change from "
                            "each "
                            "run's baseline) with the figures the JRC published from CAPRI in its Farm-to-Fork study "
                            "(JRC121368). Meaningful for Farm-to-Fork runs on all regions.")
                with gr.Row():
                    ch_runs = gr.Dropdown(labs0, value=[first0] if first0 else [], multiselect=True,
                                          label="runs (up to four)", scale=4)
                    ch_go = gr.Button("Draw", variant="primary", **BTN)
                ch_msg = gr.Markdown()
                ch_plot = gr.Plot(label="indicators")

            with gr.Tab("Comparison with CAPRI", id="capri"):
                gr.Markdown("Compares a run with CAPRI, as a check: the run's 2030 baseline with CAPRI's own 2030 "
                            "reference, and the run's scenario with CAPRI's result for the same scenario.")
                with gr.Tab("2030 baseline"):
                    gr.Markdown(
                        "The first table compares the run's 2030 baseline with CAPRI's own 2030 "
                        "reference for the EU27, block by block (prices by their relative levels, not in euros); the "
                        "second "
                        "summarises how close each block is.")
                    with gr.Row():
                        cp_run = gr.Dropdown(labs0, value=first0, label="run")
                        cp_go = gr.Button("Compute", variant="primary", **BTN)
                    cp_msg = gr.Markdown()
                    cp_base = gr.Dataframe(interactive=False, label="2030 baseline compared with CAPRI's 2030 "
                                                                    "reference")
                    cp_stats = gr.Dataframe(interactive=False, label="per block: median gap from CAPRI (%) and share "
                                                                     "of rows within 10%")

                with gr.Tab("Scenarios"):
                    gr.Markdown(
                        "Compares a scenario run with CAPRI's result for the same scenario: the Green Deal 2030 with "
                        "the "
                        "project's CAPRI run of it, or Farm-to-Fork 2030 with the figures published in JRC121368 "
                        "(EU27 only). "
                        "Both sides are shown as % changes from each model's own reference: first the EU27 activities, "
                        "prices, yields and nitrogen balance, then one activity by member state, on two maps and "
                        "region by "
                        "region.")
                    with gr.Row():
                        gd_kind = gr.Radio(["Green Deal 2030 · CAPRI's run", "Farm-to-Fork 2030 · JRC121368"],
                                           value="Green Deal 2030 · CAPRI's run", label="comparison", scale=3)
                        gd_run = gr.Dropdown(labs0, value=first0, label="run", scale=4)
                        gd_go = gr.Button("Compare", variant="primary", **BTN)
                    gd_msg = gr.Markdown()
                    with gr.Row():
                        gd_act = gr.Plot(label="EU27 activity levels")
                        gd_pri = gr.Plot(label="EU27 producer prices")
                    with gr.Row():
                        gd_yld = gr.Plot(label="EU27 crop yields")
                        gd_nbal = gr.Plot(label="EU27 N balance")
                    gr.Markdown("**By member state and region**")
                    with gr.Row():
                        gd_item = gr.Dropdown([], label="activity (or N balance item)", scale=3)
                        gd_go2 = gr.Button("Draw", **BTN)
                    gd_ms = gr.Plot(label="by member state")
                    with gr.Row():
                        gd_map_m = gr.Plot(label="capri-mod, regional units")
                        gd_map_c = gr.Plot(label="CAPRI, regional units")
                    gd_sc = gr.Plot(label="regional units: capri-mod compared with CAPRI")
                    with gr.Accordion("tables", open=False):
                        gd_table = gr.Dataframe(interactive=False, label="EU27 and member states")
                        gd_file = gr.File(label="all comparisons (CSV)")
                    gr.Markdown("**Farm-to-Fork indicators of several runs**: the runs' Farm-to-Fork indicators side "
                                "by side "
                                "with the figures the JRC published from CAPRI (JRC121368), % change from the "
                                "baseline. It "
                                "applies to Farm-to-Fork runs on all regions.")
                    with gr.Row():
                        cp_more = gr.Dropdown(labs0, value=[], multiselect=True, label="runs (same store)", scale=4)
                        ind_go = gr.Button("Show", **BTN)
                    cp_ind = gr.Dataframe(interactive=False, label="Farm-to-Fork indicators, % change from the "
                                                                   "baseline")

        # ================================================================== callbacks
        def load_runs(root):
            r = RD.runs(root)
            labs = _labels(root)
            first = _first(labs)
            show = r.drop(columns=["reference_run_id"]) if not r.empty else r
            # one update per output: Gradio consumes an update when it applies it
            return (show, *[gr.update(choices=labs, value=first) for _ in range(5)],
                    gr.update(choices=labs, value=[first] if first else []))

        def load_runs_b(root):
            labs = _labels(root)
            return gr.update(choices=labs, value=_first(labs))

        def show_run(root, label, point):
            if not label:
                return None, None, ""
            s, r = RD.parse_label(label)
            it = RD.iterations(root, s, r)
            it = it[it["point"] == point]
            it = it[it["value"] > 0].assign(value=lambda d: d["value"].map(lambda v: __import__("math").log10(v)))
            return it, RD.run_summary(root, s, r), RD.read_settings(root, s, r)

        def sv_blocks(root, label):
            if not label:
                return gr.update(choices=[], value=None)
            base, scen = RD.points(root, *RD.parse_label(label))
            blocks = sorted(set(scen["block"]) | set(base["block"]))
            return gr.update(choices=blocks, value="market" if "market" in blocks else blocks[0])

        def sv_choices(root, label, block, region, rows, cols, dim5):
            if not label or not block:
                return [gr.update()] * 4
            _, scen = RD.points(root, *RD.parse_label(label))
            f = _filters(region, rows, cols, dim5)
            return [_keep_selected(RD.choices(scen, block, f, d), f[d], d, block)
                    for d in ("region", "rows", "cols", "dim5")]

        def sv_show(root, label, block, region, rows, cols, dim5, measure, down, across):
            if not label:
                return "Pick a run.", None, None, None, None
            s, r = RD.parse_label(label)
            j = RD.scenario_vs_baseline(root, s, r, block, _filters(region, rows, cols, dim5))
            msg = f"{len(j)} rows matched"
            try:
                t = RD.pivot(j, measure, down, across or None)
            except ValueError as e:
                return f"{msg}. **{e}**", None, None, _shown(RD.with_names(j, block)), _csv(j, "scenario_vs_baseline")
            units = sorted(set(j["unit"]) - {""})
            msg += f"; unit: {', '.join(units) if units else 'not recorded'}"
            if measure == "% change":
                msg += "; % change is empty where the baseline is 0"
            t = _named(t, down, across, block)
            return (msg, _shown(t.reset_index()), _chart_frame(t, measure, down, across),
                    _shown(RD.with_names(j, block)), _csv(j, "scenario_vs_baseline"))

        def cr_blocks(root_a, a, root_b, b):
            if not a or not b:
                return gr.update(choices=[], value=None)
            sa, sb = RD.points(root_a, *RD.parse_label(a))[1], RD.points(root_b, *RD.parse_label(b))[1]
            blocks = sorted(set(sa["block"]) | set(sb["block"]))
            return gr.update(choices=[""] + blocks, value="market" if "market" in blocks else "")

        def cr_choices(root_a, a, block, region, rows, cols):
            if not a:
                return [gr.update()] * 3
            _, sa = RD.points(root_a, *RD.parse_label(a))
            f = _filters(region, rows, cols, [])
            return [_keep_selected(RD.choices(sa, block or None, f, d), f[d], d, block or None)
                    for d in ("region", "rows", "cols")]

        def cr_show(root_a, a, pa, root_b, b, pb, block, region, rows, cols, measure, down, across):
            if not a or not b:
                return "Pick two runs.", None, None, None, None
            j = RD.compare_runs(root_a, a, pa, root_b, b, pb, block or None, _filters(region, rows, cols, []))
            dev = RD.deviation_summary(j, "A", "B")
            n_diff = int(dev["rows differing"].sum()) if not dev.empty else 0
            msg = (f"{len(j)} rows; {n_diff} differ; "
                   f"{int(dev['one run only'].sum()) if not dev.empty else 0} in one run only")
            try:
                t = _named(RD.pivot(j, measure, down, across or None), down, across, block or None)
                shown, chart = _shown(t.reset_index()), _chart_frame(t, measure, down, across)
            except ValueError as e:
                msg += f". **{e}**"
                shown, chart = None, None
            return msg, _shown(dev), shown, chart, _csv(j, "compare_runs")

        def cp_show(root, label):
            if not label:
                return "Pick a run.", None, None
            s, r = RD.parse_label(label)
            msg = []
            base = RD.baseline_vs_capri(root, s, r)
            stats = None
            if base.empty:
                msg.append("The run has no base_market block: no baseline comparison.")
            else:
                g = base.assign(ad=base["dev %"].abs()).groupby("block")
                stats = pd.DataFrame({"n": g.size(), "median |dev| %": g["ad"].median(),
                                      "within 10%": g["ad"].apply(lambda x: float((x <= 10).mean()))}).reset_index()
            regs = str((RD.read_meta(root, s, r).get("options") or {}).get("regions") or "")
            if regs:
                msg.append(f"The run solved {len(regs.split(','))} regional units (--regions): its EU figures mix "
                           "two sets of units; not comparable with CAPRI's EU27 (KNOWN_ISSUES K83).")
            return "  \n".join(msg), _shown(base), _shown(stats) if stats is not None else None

        def ind_show(root, labels):
            labels = [m for m in (labels or []) if m]
            return _shown(RD.jrc_indicators(root, labels).round(1)) if labels else None

        # wiring
        store.change(load_runs, store, [runs_df, run_pick, sv_run, cr_a, cp_run, gd_run, cp_more])
        refresh.click(load_runs, store, [runs_df, run_pick, sv_run, cr_a, cp_run, gd_run, cp_more])
        app.load(load_runs, store, [runs_df, run_pick, sv_run, cr_a, cp_run, gd_run, cp_more])
        app.load(load_runs_b, store_b, cr_b)
        store_b.change(load_runs_b, store_b, cr_b)

        for ev in (run_pick.change, conv_point.change):
            ev(show_run, [store, run_pick, conv_point], [conv_plot, summary, settings_txt])

        sv_run.change(sv_blocks, [store, sv_run], sv_block)
        app.load(sv_blocks, [store, sv_run], sv_block)
        app.load(show_run, [store, run_pick, conv_point], [conv_plot, summary, settings_txt])
        sv_ins = [store, sv_run, sv_block, sv_region, sv_rows, sv_cols, sv_dim5]
        for ev in (sv_block.change, sv_region.blur, sv_rows.blur, sv_cols.blur, sv_dim5.blur):
            ev(sv_choices, sv_ins, [sv_region, sv_rows, sv_cols, sv_dim5])
        sv_go.click(sv_show, sv_ins + [sv_measure, sv_down, sv_across],
                    [sv_msg, sv_table, sv_chart, sv_rows_df, sv_file])

        for ev in (cr_a.change, cr_b.change):
            ev(cr_blocks, [store, cr_a, store_b, cr_b], cr_block)
        app.load(cr_blocks, [store, cr_a, store_b, cr_b], cr_block)
        cr_ins = [store, cr_a, cr_block, cr_region, cr_rows, cr_cols]
        for ev in (cr_block.change, cr_region.blur, cr_rows.blur, cr_cols.blur):
            ev(cr_choices, cr_ins, [cr_region, cr_rows, cr_cols])
        cr_go.click(cr_show, [store, cr_a, cr_pa, store_b, cr_b, cr_pb, cr_block, cr_region, cr_rows, cr_cols,
                              cr_measure, cr_down, cr_across], [cr_msg, cr_dev, cr_table, cr_chart, cr_file])

        cp_go.click(cp_show, [store, cp_run], [cp_msg, cp_base, cp_stats])
        ind_go.click(ind_show, [store, cp_more], cp_ind)

        # ------------------------------------------------------------------ Comparison with CAPRI: scenarios (Green Deal, Farm-to-Fork)
        def _subset_note(root, s_, r_):
            regs = str((RD.read_meta(root, s_, r_).get("options") or {}).get("regions") or "")
            return (f"The run solved {len(regs.split(','))} regional units only (--regions): not comparable with "
                    "CAPRI's EU27 (KNOWN_ISSUES K83). " if regs else "")

        def f2f_show(root, s_, r_):
            d = RD.f2f_jrc(root, s_, r_)
            ok = d.dropna(subset=["model_pct"])
            same = np.mean(np.sign(ok["jrc_pct"].round(1)) == np.sign(ok["model_pct"].round(1))) if len(ok) else 0
            msg = (_subset_note(root, s_, r_) + f"EU27, {len(ok)} indicators: mean absolute gap "
                   f"{ok['gap_pts'].abs().mean():.1f} points, same sign {same:.0%}. JRC121368 publishes EU27 figures "
                   "only: the member-state and regional charts below are for the Green Deal comparison.")
            figs = []
            for grp in ("herds and production", "prices", "environment"):
                g = d[d["group"] == grp]
                figs.append(pair_figure(g["indicator"], g["model_pct"], g["jrc_pct"], f"Farm-to-Fork, EU27: {grp}",
                                        "% change from the baseline", ref_name="JRC121368 (CAPRI)"))
            return (msg, *figs, None, _shown(d), _csv(d, "farm_to_fork_vs_jrc121368"),
                    gr.update(choices=[], value=None))

        def gd_show(root, label, kind=None):
            if not label:
                return ("Pick a run.",) + (None,) * 6 + (gr.update(choices=[], value=None),)
            s_, r_ = RD.parse_label(label)
            if kind and kind.startswith("Farm-to-Fork"):
                return f2f_show(root, s_, r_)
            act = RD.gd_activities(root, s_, r_)
            pri = RD.gd_prices(root, s_, r_)
            yld = RD.gd_yields(root, s_, r_)
            nb = RD.gd_n_balance(root, s_, r_)
            eu = act[act["region"] == "EU27"]
            nbe = nb[nb["region"] == "EU27"]
            same = np.mean(np.sign(eu["capri_pct"].round(1)) == np.sign(eu["model_pct"].round(1))) if len(eu) else 0
            msg = (_subset_note(root, s_, r_) + f"EU27 activities: mean absolute gap {eu['gap_pts'].abs().mean():.1f} "
                   f"points, same sign {same:.0%}; prices: mean absolute gap {pri['gap_pts'].abs().mean():.1f} points; "
                   f"N surplus {float(nbe.loc[nbe['item'].str.startswith('gross'), 'model_pct'].sum()):+.1f}% (CAPRI "
                   f"{float(nbe.loc[nbe['item'].str.startswith('gross'), 'capri_pct'].sum()):+.1f}%).")
            f_act = pair_figure([RD.code_label(a, "cols", "supply") for a in eu["activity"]], eu["model_pct"],
                                eu["capri_pct"], "Activity levels, EU27",
                                "% change from the reference")
            f_pri = pair_figure([RD.code_label(p, "rows", "market") for p in pri["product"]], pri["model_pct"],
                                pri["capri_pct"], "Producer prices, EU27",
                                "% change from the reference")
            f_yld = pair_figure([RD.code_label(c, "cols", "supply") for c in yld["crop"]], yld["model_pct"],
                                yld["capri_pct"], "Crop yields, EU27",
                                "% change from the reference")
            f_nb = pair_figure(nbe["item"], nbe["model_pct"], nbe["capri_pct"], "N balance, EU27",
                               "% change from the reference")
            table = pd.concat([act.assign(kind="activity"),
                               pri.rename(columns={"product": "activity"}).assign(region="EU27", kind="price"),
                               yld.rename(columns={"crop": "activity"}).assign(region="EU27", kind="yield"),
                               nb.rename(columns={"item": "activity"}).assign(kind="N balance")], ignore_index=True)
            items = ([(RD.code_label(a, "cols", "supply"), a) for a in eu["activity"]]
                     + [(f"N: {x}", f"N: {x}") for x in nbe["item"]])
            codes = [v for _, v in items]
            return (msg, f_act, f_pri, f_yld, f_nb, _shown(table), _csv(table, "greendeal_vs_capri"),
                    gr.update(choices=items, value="GRAI" if "GRAI" in codes else (codes[0] if codes else None)))

        def gd_draw(root, label, item):
            if not (label and item):
                return None, None, None, None
            s_, r_ = RD.parse_label(label)
            if item.startswith("N: "):
                nb = RD.gd_n_balance(root, s_, r_)
                d = nb[(nb["item"] == item[3:]) & (nb["region"] != "EU27")]
                return (pair_figure([RD.code_label(x, "region") for x in d["region"]], d["model_pct"], d["capri_pct"],
                                    f"{item[3:]} by member state",
                                    "% change from the reference"), None, None, None)
            act = RD.gd_activities(root, s_, r_)
            d = act[(act["activity"] == item) & (act["region"] != "EU27")]
            name = RD.code_label(item, "cols", "supply")
            f_ms = pair_figure([RD.code_label(x, "region") for x in d["region"]], d["model_pct"], d["capri_pct"],
                               f"{name} by member state", "% change from the reference")
            reg = RD.gd_regional(root, s_, r_, item)
            fm = RD.map_frame(RD.gd_unit_values(reg, "model"), "% change")
            fc = RD.map_frame(RD.gd_unit_values(reg, "capri"), "% change")
            lim = max(_saturation(fm["value"]), _saturation(fc["value"]))     # one scale for both maps
            mm = map_figure(fm, "% change", f"{name} · capri-mod", lim)
            mc = map_figure(fc, "% change", f"{name} · CAPRI", lim)
            ok = reg.dropna(subset=["model_pct", "capri_pct"])
            corr = (f"correlation {np.corrcoef(ok['model_pct'], ok['capri_pct'])[0, 1]:.2f}" if len(ok) > 2
                    else "too few units for a correlation")
            sc = scatter_figure(reg, f"{name}: {len(ok)} regional units, {corr}")
            return f_ms, mm, mc, sc

        gd_go.click(gd_show, [store, gd_run, gd_kind], [gd_msg, gd_act, gd_pri, gd_yld, gd_nbal, gd_table, gd_file,
                                                         gd_item])
        gd_go2.click(gd_draw, [store, gd_run, gd_item], [gd_ms, gd_map_m, gd_map_c, gd_sc])

        # ------------------------------------------------------------------ map and charts
        def _item_label(r):
            parts = [RD.code_label(r[d], d, r["block"]) for d in ("rows", "cols", "dim5") if str(r[d])]
            return " · ".join(parts) + (f" [{r['unit']}]" if r["unit"] else "")

        def mp_blocks(root, label):
            if not label:
                return gr.update(choices=[], value=None), gr.update(choices=[], value=None)
            it = RD.regional_items(root, *RD.parse_label(label))
            blocks = sorted(it["block"].unique())
            b0 = "supply" if "supply" in blocks else (blocks[0] if blocks else None)
            return gr.update(choices=blocks, value=b0), mp_items(root, label, b0)

        def mp_items(root, label, block):
            if not label or not block:
                return gr.update(choices=[], value=None)
            it = RD.regional_items(root, *RD.parse_label(label))
            it = it[it["block"] == block]
            labs = [_item_label(r) for r in it.to_dict("records")]
            pref = [l for l in labs if l.startswith("activities · SWHE")] or labs
            return gr.update(choices=labs, value=pref[0] if pref else None)

        def mp_draw(root, label, block, item, measure):
            if not (label and block and item):
                return "Pick a run, a block and an item.", None, None, None
            s_, r_ = RD.parse_label(label)
            it = RD.regional_items(root, s_, r_)
            it = it[it["block"] == block]
            rec = next((r for r in it.to_dict("records") if _item_label(r) == item), None)
            if rec is None:
                return "Item not found in this run.", None, None, None
            v = RD.unit_values(root, s_, r_, block, rec["cols"], rec["rows"], rec["dim5"])
            mf = RD.map_frame(v, measure)
            title = f"{item} · {measure} · {s_}"
            fig = map_figure(mf, measure, title)
            msf = RD.member_state_frame(v, measure)
            ms_fig = (bar_figure(msf["member_state"], msf["value"], f"{item} by member state · {measure}", measure)
                      if not msf.empty else None)
            regs = str((RD.read_meta(root, s_, r_).get("options") or {}).get("regions") or "")
            msg = (f"{mf['value'].notna().sum()} of {len(mf)} NUTS-2024 regions with a value; "
                   f"{'additive item' if rec['additive'] else 'not additive: no member-state sums'}")
            if regs:
                msg += f". The run solved {len(regs.split(','))} regional units only: the others show the baseline's " \
                       "units outside the run (KNOWN_ISSUES K83)"
            table = mf.merge(pd.DataFrame([{"nuts2024": f["id"], "name": f["properties"]["name"]}
                                           for f in RD.nuts_geometry()["features"]]), on="nuts2024", how="left")
            return msg, fig, ms_fig, _shown(table.sort_values("value"))

        mp_run.change(mp_blocks, [store, mp_run], [mp_block, mp_item])
        app.load(mp_blocks, [store, mp_run], [mp_block, mp_item])
        mp_block.change(mp_items, [store, mp_run, mp_block], mp_item)
        mp_go.click(mp_draw, [store, mp_run, mp_block, mp_item, mp_measure], [mp_msg, mp_map, mp_ms, mp_table])

        def ch_draw(root, labels):
            labels = [l for l in (labels or []) if l][:4]
            if not labels:
                return "Pick at least one run.", None
            ind = RD.jrc_indicators(root, labels)
            sub = [l for l in labels
                   if str((RD.read_meta(root, *RD.parse_label(l)).get("options") or {}).get("regions") or "")]
            msg = ("" if not sub else "Not comparable with JRC121368 (subset of regions): " + "; ".join(sub))
            return msg, indicator_figure(ind, labels)

        ch_go.click(ch_draw, [store, ch_runs], [ch_msg, ch_plot])
    return store


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--store", action="append", default=[], help="a results store (repeat for several)")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=7860)
    a = ap.parse_args()
    stores = [Path(s).resolve() for s in a.store] or [RD.default_store()]
    missing = [s for s in stores if not (s / "runs").exists()]
    if missing:
        raise SystemExit(f"not a results store (no runs table): {', '.join(map(str, missing))}")
    build(stores).launch(server_name=a.host, server_port=a.port, **launch_args(PAGE_STYLE))


if __name__ == "__main__":
    main()
