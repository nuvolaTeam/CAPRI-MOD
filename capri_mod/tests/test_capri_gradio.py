"""The GUI's scenario tools and assistant loop (capri_gradio/scenario_tools.py, capri_gradio/assistant_llm.py): every
scenario a model or a form writes is checked against capri-mod's scenario definition and read back as a run reads it;
a model's tool calls are executed only through the checked tools. No network, no model run, no gradio."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "capri_gradio"))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "capri_gradio" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod                 # the dataclasses need their module registered
    spec.loader.exec_module(mod)
    return mod


T = _load("scenario_tools")
L = _load("assistant_llm")


def test_a_green_deal_scenario_is_written_and_read_back_as_a_run_reads_it(tmp_path):
    from capri_mod.scenarios import definition as SD
    r = T.make_scenario({"name": "f2f_organic_only", "reference": "ref_jrc121368", "group": "greendeal_group",
                         "description": "organic 25% only",
                         "greendeal": {"orgTarg": 25, "surplus_rule": "jrc121368", "pesticide_rule": "jrc121368"}},
                        tmp_path)
    assert r["ok"], r
    d = SD.load("f2f_organic_only", tmp_path)
    assert d.kind == "scenario" and d.greendeal.orgTarg == 25 and d.greendeal.pestRedu == 0
    # the reference's settings are inherited as for the repository's scenarios
    assert d.manure_trade is False and d.endotech.as_dict()["ghgTechMYld"] == 0.2
    sc = SD.to_policy_scenario(d, tmp_path)
    assert sc.name == "f2f_organic_only"
    assert r["warnings"] == []
    # a scenario that changes nothing is written, with a warning
    w = T.make_scenario({"name": "same_as_ref", "reference": "ref_star3"}, tmp_path)
    assert w["ok"] and "reproduce the baseline" in w["warnings"][0]


def test_invalid_scenarios_are_refused_with_their_errors_and_nothing_written(tmp_path):
    bad = [({"name": "x", "reference": "ref_star3"}, "name"),
           ({"name": "neg_tax", "reference": "ref_star3", "shocks": {"carbon_tax": -1}}, "carbon_tax"),
           ({"name": "no_ref", "reference": "not_a_reference"}, "reference"),
           ({"name": "gd_odd", "reference": "ref_star3", "group": "greendeal_group",
             "greendeal": {"pestRedu": 33}}, "pestRedu"),
           ({"name": "farm_to_fork_jrc121368", "reference": "ref_jrc121368"}, "repository"),
           ({"name": "extra_field", "reference": "ref_star3", "colour": "blue"}, "colour")]
    for args, word in bad:
        r = T.make_scenario(args, tmp_path)
        assert not r["ok"] and any(word in e for e in r["errors"]), (args, r)
    assert not any(tmp_path.iterdir())


def test_an_existing_user_scenario_is_kept_unless_overwritten(tmp_path):
    a = {"name": "ctax80", "reference": "ref_star3", "shocks": {"carbon_tax": 80.0}}
    assert T.make_scenario(a, tmp_path)["ok"]
    assert not T.make_scenario({**a, "shocks": {"carbon_tax": 90.0}}, tmp_path)["ok"]
    assert T.make_scenario({**a, "shocks": {"carbon_tax": 90.0}}, tmp_path, overwrite=True)["ok"]
    assert "carbon_tax = 90.0" in (tmp_path / "ctax80" / "settings.toml").read_text()


def test_the_schema_holds_the_green_deal_switches_allowed_values():
    s = T.scenario_schema()
    gd = s["$defs"]["GreenDeal"]["properties"]
    from capri_mod.policy import greendeal as G
    assert gd["pestRedu"]["enum"] == list(G._SUPPORTED["pestRedu"]) and gd["dietShift"]["enum"] == [0]
    assert "kind" not in s["properties"] and set(s["required"]) == {"name", "reference"}


def test_run_overrides_and_command_are_checked():
    assert T.check_overrides({"outer_loop.max_outer_iter": 30}) == []
    errs = T.check_overrides({"outer_loop.max_outer_iter": "x", "no.such": 1})
    assert len(errs) == 2
    cmd = T.run_command("ctax80", Path("out.pkl"), Path("scen"), "DE110000", {"outer_loop.max_outer_iter": 30})
    assert cmd[1].endswith("tools/run/run_f2f_2030.py") and cmd[3:5] == ["--scenario", "ctax80"]
    assert ["--set", "outer_loop.max_outer_iter=30"] == cmd[-2:]


class _Scripted(L.Backend):
    """A stand-in model: first an invalid scenario, then (after seeing the errors) a valid one, then an answer."""
    name = "scripted"

    def __init__(self):
        self.calls = 0
        self.seen = []

    def chat(self, messages, tools):
        self.calls += 1
        self.seen.append(messages[-1])
        if self.calls == 1:
            return L.Reply("", [{"id": "c1", "name": "make_scenario",
                                 "arguments": {"name": "ctax_bad", "reference": "ref_star3",
                                               "shocks": {"carbon_tax": -5}}}])
        if self.calls == 2:
            return L.Reply("", [{"id": "c2", "name": "make_scenario",
                                 "arguments": {"name": "ctax_ok", "reference": "ref_star3",
                                               "shocks": {"carbon_tax": 20}}}])
        return L.Reply("Written: ctax_ok. Start it in the Run tab.", [])


def test_the_assistant_loop_returns_tool_errors_to_the_model_and_runs_nothing(tmp_path):
    b = _Scripted()
    hist = L.run_turn(b, [], "a carbon tax of 20 EUR/t", T.model_tools(),
                      lambda n, a: T.call_tool(n, a, scenarios_dir=tmp_path))
    first = json.loads(b.seen[1]["content"])
    assert b.seen[1]["role"] == "tool" and not first["ok"] and "carbon_tax" in first["errors"][0]
    assert (tmp_path / "ctax_ok" / "settings.toml").exists() and not (tmp_path / "ctax_bad").exists()
    assert hist[-1]["content"].startswith("Written") and "start_run" not in {t["name"] for t in T.model_tools()}
    assert not T.JOBS


def test_the_backends_convert_the_neutral_history():
    hist = [{"role": "user", "content": "hi"},
            {"role": "assistant", "content": "", "tool_calls": [{"id": "t1", "name": "list_scenarios",
                                                                 "arguments": {}}]},
            {"role": "tool", "tool_call_id": "t1", "name": "list_scenarios", "content": "{}"}]
    oa = L.OpenAICompatible("m", "http://x/v1")._messages(hist)
    assert oa[0]["role"] == "system" and oa[2]["tool_calls"][0]["function"]["name"] == "list_scenarios"
    assert oa[3] == {"role": "tool", "tool_call_id": "t1", "content": "{}"}
    an = L.Anthropic("m")._messages(hist)
    assert an[1]["content"][0]["type"] == "tool_use" and an[2]["content"][0]["type"] == "tool_result"
    with pytest.raises(ValueError):
        L.make_backend("openai")             # no model, no base URL


def test_a_shared_page_lets_only_the_starting_session_stop_a_run(tmp_path):
    import subprocess
    p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        T.JOBS["j"] = T.Job(scenario="s", cmd=[], log=tmp_path / "l", out=tmp_path / "o", proc=p, owner="alice")
        assert not T.stop_run("j", owner="bob")["ok"]
        assert not T.start_run("ctax", scenarios_dir=tmp_path)["ok"]          # one run at a time
        assert T.stop_run("j", owner="alice")["ok"]
    finally:
        p.kill()
        T.JOBS.pop("j", None)
