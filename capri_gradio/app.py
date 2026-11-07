"""The capri-mod GUI as a hosted page (a Hugging Face Space, or any server): the same page as capri_gui.py, configured
by environment variables instead of the command line, in shared mode (each browser session its own scenario folder,
mini-EU runs only, one run at a time).

Environment (a Space's variables and secrets; nothing is read from files):
  CAPRI_LLM            none | openai | anthropic                       (default none)
  CAPRI_LLM_MODEL      e.g. openai/gpt-oss-120b:<provider> on Hugging Face's router
  CAPRI_LLM_BASE_URL   e.g. https://router.huggingface.co/v1           (openai only)
  CAPRI_LLM_KEY_ENV    the variable that holds the key, e.g. HF_TOKEN  (set the key itself as a secret)
  CAPRI_SCENARIOS_DIR  where the sessions' scenario folders go          (default user_scenarios/ in the repository)
  CAPRI_RESULTS_DIR    the results store                               (default: the setting run.results_dir)
  CAPRI_SHARED         1 (default) for a page several people use, 0 for one user
A Space starts this file (README front matter app_file: capri_gradio/app.py) and serves on its port 7860.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import assistant_llm as L   # noqa: E402
import capri_gui as G       # noqa: E402
import results_data as RD   # noqa: E402
import scenario_tools as T  # noqa: E402


try:                                   # Hugging Face's ZeroGPU hardware (the project lead's Space, 7 November 2026)
    import spaces
except ImportError:                    # elsewhere the package is not needed
    spaces = None

if spaces is not None:
    @spaces.GPU(duration=1)
    def _zerogpu_placeholder():
        """ZeroGPU starts only an app that declares a GPU function (huggingface.co/docs/hub/spaces-zerogpu). capri-mod
        uses no GPU (the language model is called through an API), so this one is never called; the decorator has no
        effect outside ZeroGPU."""
        return None


def make_app():
    env = os.environ.get
    backend = L.make_backend(env("CAPRI_LLM", "none"), env("CAPRI_LLM_MODEL", ""), env("CAPRI_LLM_BASE_URL", ""),
                             env("CAPRI_LLM_KEY_ENV", ""))
    sdir = Path(env("CAPRI_SCENARIOS_DIR", "") or T.default_scenarios_dir()).expanduser()
    sdir.mkdir(parents=True, exist_ok=True)
    store = Path(env("CAPRI_RESULTS_DIR", "") or RD.default_store()).expanduser()
    if not (store / "runs").exists():
        raise SystemExit(f"{store}: not a results store (no runs table); set CAPRI_RESULTS_DIR")
    return G.build(backend, sdir, [store], shared=env("CAPRI_SHARED", "1") != "0")


if __name__ == "__main__":
    make_app().launch(server_name="0.0.0.0", server_port=int(os.environ.get("PORT", "7860")), show_api=False)
