"""capri-mod's GUI (draft): define a scenario with an assistant or a form, run it, and explore its results, in the
spirit of CAPRI's GUI (gui2014.pdf: tasks, scenario editor, run, exploitation tools).

Tabs:
  Assistant   a chat with a language model (assistant_llm.py; the provider is chosen at start-up, none by default)
              that builds scenarios through checked tool calls (scenario_tools.py); it cannot start runs
  Scenario    the same definition as a form: a reference, then CAPRI's Green Deal group switches or policy shocks;
              checked and written to the user's scenario folder
  Run         start a scenario (full EU or the 20 mini-EU units), one run at a time, and follow its iterations
  Results     the results browser (results_browser.py) on the results store

Draft, local and single-user: it runs capri-mod on this machine and writes scenarios to the user's folder (setting
run.scenarios_dir, else user_scenarios/ in the repository), never to capri_data/scenarios.

Usage:
    python capri_gradio/capri_gui.py [--llm none|openai|anthropic] [--llm-model NAME] [--llm-base-url URL]
                                     [--llm-key-env VAR] [--scenarios-dir DIR] [--store DIR] [--port 7860]
Needs gradio (pip install ".[gui]"); requests for a language model.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# at module level: the callbacks' gr.Request annotations are resolved in this module's namespace
import gradio as gr         # noqa: E402
import assistant_llm as L  # noqa: E402
import results_browser as RB  # noqa: E402
import results_data as RD     # noqa: E402
import scenario_tools as T    # noqa: E402

MINI_EU = "mini-EU (20 units, about 10 minutes)"
FULL_EU = "full EU (1-2 hours)"


def _mini_units() -> str:
    sys.path.insert(0, str(T.ROOT / "tools" / "run"))
    from run_mini_eu import UNITS
    return ",".join(UNITS)


def _scenario_choices(sdir):
    sc = T.list_scenarios(sdir)
    return ([n for n, v in sc.items() if v.get("kind") == "scenario"],
            [n for n, v in sc.items() if v.get("kind") == "reference"])


def _chat_messages(hist: list) -> list:
    """The neutral history as Gradio chat messages; tool calls and results shown folded."""
    out = []
    for m in hist:
        if m["role"] == "user":
            out.append({"role": "user", "content": m["content"]})
        elif m["role"] == "assistant":
            if m.get("content"):
                out.append({"role": "assistant", "content": m["content"]})
            for c in m.get("tool_calls") or []:
                out.append({"role": "assistant", "content": f"```json\n{json.dumps(c['arguments'], indent=1)}\n```",
                            "metadata": {"title": f"tool call: {c['name']}"}})
        elif m["role"] == "tool":
            try:
                res = json.loads(m["content"])
                ok = res.get("ok")
            except Exception:
                res, ok = m["content"], None
            body = res.get("toml") if isinstance(res, dict) and res.get("toml") else json.dumps(res, indent=1)[:4000]
            status = "ok" if ok else "errors" if ok is False else "result"
            out.append({"role": "assistant", "content": f"```\n{body}\n```",
                        "metadata": {"title": f"{m.get('name')}: {status}"}})
    return out


def build(backend: L.Backend, sdir: Path, stores: list, shared: bool = False):
    """The page. shared: a page several people use (a hosted Space): each browser session writes its scenarios to its
    own folder under sdir, only mini-EU runs can be started, and a run is stopped only by the session that started
    it; one run at a time for everyone."""
    scen0, refs0 = _scenario_choices(None if shared else sdir)
    gd_vals = T.GREENDEAL_VALUES

    def _sd(request) -> Path:
        """The session's scenario folder."""
        if not shared:
            return sdir
        d = sdir / re.sub(r"[^A-Za-z0-9]", "", str(getattr(request, "session_hash", "") or "anon"))[:40]
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _who(request) -> str:
        return str(getattr(request, "session_hash", "") or "")

    with gr.Blocks(title="capri-mod") as app:
        where = "your session's folder" if shared else f"`{sdir}`"
        gr.Markdown(f"## capri-mod\nScenarios in {where} · results in `{stores[0].name}` · "
                    f"assistant: **{backend.name}**" + (" · shared page: mini-EU runs only, one run at a time"
                                                        if shared else ""))
        hist_state = gr.State([])

        # ------------------------------------------------------------------ assistant
        with gr.Tab("Assistant"):
            gr.Markdown("Describe a scenario; the assistant writes it with checked tool calls. It cannot run the "
                        "model: start the run in the **Run** tab. " +
                        ("" if backend.name != "none" else
                         "_No language model configured: use the Scenario tab, or restart with `--llm`._"))
            chat = gr.Chatbot(type="messages", height=480, label="assistant")
            with gr.Row():
                msg = gr.Textbox(placeholder="e.g. Farm-to-Fork as JRC121368 but with a 25% organic target only",
                                 scale=5, show_label=False)
                send = gr.Button("Send", variant="primary", scale=1)
            clear = gr.Button("New conversation", size="sm")

        # ------------------------------------------------------------------ scenario form
        with gr.Tab("Scenario"):
            with gr.Row():
                f_name = gr.Textbox(label="name (letters, digits, _)")
                f_ref = gr.Dropdown(refs0, value=refs0[0] if refs0 else None, label="reference")
            f_desc = gr.Textbox(label="description")
            f_mode = gr.Radio(["Green Deal group", "policy shocks"], value="Green Deal group", label="kind")
            with gr.Group(visible=True) as gd_box:
                with gr.Row():
                    gd_inputs = {k: gr.Dropdown([str(v) for v in vals], value=str(vals[0]), label=k)
                                 for k, vals in gd_vals.items()}
                with gr.Row():
                    gd_surplus = gr.Dropdown(["star3", "jrc121368"], value="star3", label="surplus_rule")
                    gd_pest = gr.Dropdown(["star3", "jrc121368"], value="star3", label="pesticide_rule")
            with gr.Group(visible=False) as sh_box:
                shock_fields = [k for k in T.SD.Shocks.model_fields]
                with gr.Row():
                    sh_inputs = {k: gr.Textbox(label=k, placeholder="default") for k in shock_fields}
            with gr.Row():
                f_manure = gr.Dropdown(["from the reference", "true", "false"], value="from the reference",
                                       label="manure_trade")
                f_biof = gr.Dropdown(["from the reference", "true", "false"], value="from the reference",
                                     label="biofuel_markets")
                f_over = gr.Checkbox(label="overwrite an existing user scenario")
            f_save = gr.Button("Check and save", variant="primary")
            f_msg = gr.Markdown()
            f_toml = gr.Code(language=None, label="settings.toml")

        # ------------------------------------------------------------------ run
        with gr.Tab("Run"):
            with gr.Row():
                r_scen = gr.Dropdown(scen0, value=scen0[0] if scen0 else None, label="scenario", scale=3)
                r_refresh = gr.Button("Reload scenarios", size="sm", scale=1)
            r_regions = gr.Radio([MINI_EU] if shared else [MINI_EU, FULL_EU, "custom"], value=MINI_EU,
                                 label="regions")
            r_custom = gr.Textbox(label="custom regions (comma-separated regional units)", visible=False)
            r_over = gr.Code(language="json", value="{}", label="setting overrides (JSON, e.g. "
                             "{\"outer_loop.max_outer_iter\": 30})")
            # the log's level (run.verbosity): CAPRI's run log, the model's timed lines, each solve's own log (as
            # CAPRI's GUI shows GAMS's output with the solvers' iteration logs)
            r_verb = gr.Radio(T.LOG_LEVELS, value="capri", label="log (run.verbosity)")
            with gr.Row():
                r_start = gr.Button("Start run", variant="primary")
                r_stop = gr.Button("Stop run", variant="stop")
            r_msg = gr.Markdown()
            r_job = gr.State("")
            r_title = gr.Markdown()
            r_iters = gr.Textbox(label="iterations (step report)", lines=8, interactive=False)
            r_tail = gr.Textbox(label="log", lines=24, max_lines=24, interactive=False, autoscroll=True)
            timer = gr.Timer(5.0)

        # ------------------------------------------------------------------ results
        with gr.Tab("Results"):
            RB.add_results(stores, app)

        # ================================================================== callbacks
        def on_send(text, hist, request: gr.Request):
            if not text.strip():
                return hist, _chat_messages(hist), ""
            sd = _sd(request)
            try:
                hist = L.run_turn(backend, hist, text, T.model_tools(),
                                  lambda n, a: T.call_tool(n, a, scenarios_dir=sd, results_dir=stores[0]))
            except Exception as e:
                hist = hist + [{"role": "user", "content": text},
                               {"role": "assistant", "content": f"The model could not be reached: {e}"}]
            return hist, _chat_messages(hist), ""

        send.click(on_send, [msg, hist_state], [hist_state, chat, msg])
        msg.submit(on_send, [msg, hist_state], [hist_state, chat, msg])
        clear.click(lambda: ([], []), None, [hist_state, chat])

        f_mode.change(lambda m: (gr.update(visible=m == "Green Deal group"),
                                 gr.update(visible=m != "Green Deal group")), f_mode, [gd_box, sh_box])

        def on_save(request: gr.Request, *inputs):
            # the request first: Gradio puts it at its position, and a parameter after *inputs is not filled
            name, ref, desc, mode, manure, biof, over, surplus, pest = inputs[:9]
            vals = inputs[9:]
            sd = _sd(request)
            gd = dict(zip(gd_inputs, vals[:len(gd_inputs)]))
            sh = dict(zip(sh_inputs, vals[len(gd_inputs):]))
            args = {"name": name, "reference": ref, "description": desc}
            if mode == "Green Deal group":
                args["group"] = "greendeal_group"
                args["greendeal"] = {k: (v if k == "mineRedu" else int(v)) for k, v in gd.items()}
                args["greendeal"].update(surplus_rule=surplus, pesticide_rule=pest)
            else:
                shocks = {}
                for k, v in sh.items():
                    if str(v).strip():
                        v = str(v).strip()
                        shocks[k] = (v.lower() == "true") if v.lower() in ("true", "false") else float(v)
                args["shocks"] = shocks
            for k, v in (("manure_trade", manure), ("biofuel_markets", biof)):
                if v in ("true", "false"):
                    args[k] = v == "true"
            try:
                r = T.make_scenario(args, sd, overwrite=bool(over))
            except ValueError as e:
                r = {"ok": False, "errors": [str(e)]}
            if r.get("ok"):
                sc, _ = _scenario_choices(sd)
                warn = "".join(f"\n- warning: {w}" for w in r.get("warnings", []))
                return f"**Saved** `{r['path']}`{warn}", r["toml"], gr.update(choices=sc, value=r["name"])
            return "**Not saved:**\n" + "\n".join(f"- {e}" for e in r.get("errors", [])), "", gr.update()

        f_save.click(on_save, [f_name, f_ref, f_desc, f_mode, f_manure, f_biof, f_over, gd_surplus, gd_pest,
                               *gd_inputs.values(), *sh_inputs.values()], [f_msg, f_toml, r_scen])

        def on_refresh(request: gr.Request):
            return gr.update(choices=_scenario_choices(_sd(request))[0])

        r_refresh.click(on_refresh, None, r_scen)
        app.load(on_refresh, None, r_scen)
        r_regions.change(lambda v: gr.update(visible=v == "custom"), r_regions, r_custom)

        def on_start(scen, regions, custom, over_text, verb, request: gr.Request):
            if shared and regions != MINI_EU:
                return "**Not started:** only mini-EU runs on a shared page", ""
            try:
                over = json.loads(over_text or "{}")
            except json.JSONDecodeError as e:
                return f"**Overrides are not valid JSON:** {e}", ""
            regs = _mini_units() if regions == MINI_EU else (custom.strip() if regions == "custom" else "")
            if verb in T.LOG_LEVELS:
                over = {**over, "run.verbosity": verb}
            r = T.start_run(scen, scenarios_dir=_sd(request), regions=regs, overrides=over, owner=_who(request))
            if not r.get("ok"):
                return "**Not started:**\n" + "\n".join(f"- {e}" for e in r["errors"]), ""
            return f"**Started** `{r['job']}`; log `{r['log']}`", r["job"]

        r_start.click(on_start, [r_scen, r_regions, r_custom, r_over, r_verb], [r_msg, r_job])
        def on_stop(job, request: gr.Request):
            r = T.stop_run(job, owner=_who(request) if shared else None)
            return "**Stopped**" if r.get("ok") else "**Not stopped:** " + "; ".join(r.get("errors", []))

        r_stop.click(on_stop, r_job, r_msg)

        def on_tick(job):
            if not job or job not in T.JOBS:
                return gr.update(), gr.update(), gr.update()
            st = T.JOBS[job].status()
            head = ("running" if st["running"] else f"finished (exit {st['returncode']})") + f", {st['seconds']} s"
            if st["saved"]:
                head += "\n" + st["saved"]
            return (f"**{st['title']}**" if st["title"] else "", head + "\n\n" + "\n".join(st["iterations"]),
                    st["tail"])

        timer.tick(on_tick, r_job, [r_title, r_iters, r_tail])
    return app


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--llm", default="none", choices=("none", "openai", "anthropic"))
    ap.add_argument("--llm-model", default="")
    ap.add_argument("--llm-base-url", default="", help="openai: the server's base URL, e.g. http://localhost:8000/v1")
    ap.add_argument("--llm-key-env", default="", help="the environment variable that holds the API key")
    ap.add_argument("--scenarios-dir", default="", help="where scenarios are written (default: run.scenarios_dir, "
                                                       "else user_scenarios/ in the repository)")
    ap.add_argument("--store", action="append", default=[], help="a results store (repeat for several)")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=7860)
    a = ap.parse_args()
    backend = L.make_backend(a.llm, a.llm_model, a.llm_base_url, a.llm_key_env)
    sdir = Path(a.scenarios_dir).expanduser().resolve() if a.scenarios_dir else T.default_scenarios_dir()
    sdir.mkdir(parents=True, exist_ok=True)
    stores = [Path(s).resolve() for s in a.store] or [RD.default_store()]
    missing = [s for s in stores if not (s / "runs").exists()]
    if missing:
        raise SystemExit(f"not a results store (no runs table): {', '.join(map(str, missing))}")
    build(backend, sdir, stores).launch(server_name=a.host, server_port=a.port, show_api=False)


if __name__ == "__main__":
    main()
