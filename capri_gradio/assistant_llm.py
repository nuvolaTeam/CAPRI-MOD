"""The scenario assistant's language model, behind one provider-neutral interface (capri_gradio/capri_gui.py).

Which model is not decided (claude/release_huggingface.md: the choice by measurement on a fixed set of requests), so the
assistant talks to a backend chosen at start-up:
  none       no model: the GUI's forms only
  openai     any server with the OpenAI chat-completions API and tool calls (hosted providers, or local servers such as
             vLLM, llama.cpp's server or Ollama's OpenAI endpoint): base URL, model name, key from an environment
             variable
  anthropic  the Anthropic Messages API with tool use: model name, key from an environment variable
Nothing is sent but the conversation and the tools' small results (scenario_tools.py); the model's tool calls are
executed by scenario_tools.call_tool, which checks every one. The model cannot start a run: the user does, in the GUI.

The conversation is kept in one neutral form: {"role": "user"|"assistant"|"tool", "content": str,
"tool_calls": [{"id", "name", "arguments": dict}], "tool_call_id", "name"}; each backend converts it.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Callable, List, Optional

SYSTEM_PROMPT = """You help a user of capri-mod, an open Python reimplementation of the CAPRI agricultural economic
model (CAPRI star 3.0), to define scenarios and read their results.

Rules:
- Build scenarios only with the make_scenario tool. Use list_scenarios and describe_scenario first to choose the
  reference and to see how existing scenarios are written. If make_scenario returns errors, correct the definition and
  call it again; never claim a scenario was written unless the tool returned ok.
- A scenario either uses CAPRI's Green Deal scenario group (group "greendeal_group" with the greendeal switches, whose
  allowed values are in the schema) or policy shocks (the shocks table), on a reference (kind "reference").
- You cannot run the model. When a scenario is written, tell the user its name and that they can start it in the Run
  tab; a full EU run takes one to two hours, a run on the 20 mini-EU units about ten minutes.
- When you report results, give each number with the run it comes from (scenario | run id), call them capri-mod's
  results (never CAPRI's), and say when a run covers a subset of regions (its EU figures are then not comparable with
  CAPRI's).
- Be accurate and do not overstate: if you do not know, say so.
"""


@dataclass
class Reply:
    text: str
    tool_calls: list        # [{"id", "name", "arguments": dict}]


class Backend:
    name = "none"

    def chat(self, messages: list, tools: list) -> Reply:
        raise NotImplementedError


class NoModel(Backend):
    name = "none"

    def chat(self, messages, tools):
        return Reply("No language model is configured (start the GUI with --llm openai or --llm anthropic). "
                     "Use the Scenario tab to define a scenario by hand.", [])


def _post(url: str, headers: dict, body: dict, timeout: float) -> dict:
    import requests
    r = requests.post(url, headers=headers, data=json.dumps(body), timeout=timeout)
    if r.status_code >= 400:
        raise RuntimeError(f"{url}: HTTP {r.status_code}: {r.text[:500]}")
    return r.json()


class OpenAICompatible(Backend):
    """POST {base_url}/chat/completions with tools (the OpenAI function-calling form)."""
    name = "openai"

    def __init__(self, model: str, base_url: str, key_env: str = "", timeout: float = 120.0):
        if not model or not base_url:
            raise ValueError("the openai backend needs --llm-model and --llm-base-url")
        self.model, self.base_url, self.key_env, self.timeout = model, base_url.rstrip("/"), key_env, timeout

    def _messages(self, messages):
        out = [{"role": "system", "content": SYSTEM_PROMPT}]
        for m in messages:
            if m["role"] == "tool":
                out.append({"role": "tool", "tool_call_id": m["tool_call_id"], "content": m["content"]})
            elif m.get("tool_calls"):
                out.append({"role": "assistant", "content": m.get("content") or None,
                            "tool_calls": [{"id": c["id"], "type": "function",
                                            "function": {"name": c["name"], "arguments": json.dumps(c["arguments"])}}
                                           for c in m["tool_calls"]]})
            else:
                out.append({"role": m["role"], "content": m["content"]})
        return out

    def chat(self, messages, tools):
        headers = {"Content-Type": "application/json"}
        key = os.environ.get(self.key_env, "") if self.key_env else ""
        if key:
            headers["Authorization"] = f"Bearer {key}"
        body = {"model": self.model, "messages": self._messages(messages),
                "tools": [{"type": "function", "function": {"name": t["name"], "description": t["description"],
                                                            "parameters": t["input_schema"]}} for t in tools]}
        msg = _post(f"{self.base_url}/chat/completions", headers, body, self.timeout)["choices"][0]["message"]
        calls = []
        for c in msg.get("tool_calls") or []:
            try:
                args = json.loads(c["function"].get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {"_unparsed": c["function"].get("arguments")}
            calls.append({"id": c["id"], "name": c["function"]["name"], "arguments": args})
        return Reply(msg.get("content") or "", calls)


class Anthropic(Backend):
    """POST https://api.anthropic.com/v1/messages with tools (Anthropic tool use)."""
    name = "anthropic"
    URL = "https://api.anthropic.com/v1/messages"
    VERSION = "2023-06-01"

    def __init__(self, model: str, key_env: str = "ANTHROPIC_API_KEY", max_tokens: int = 4096,
                 timeout: float = 120.0):
        if not model:
            raise ValueError("the anthropic backend needs --llm-model")
        self.model, self.key_env, self.max_tokens, self.timeout = model, key_env, max_tokens, timeout

    def _messages(self, messages):
        out = []
        for m in messages:
            if m["role"] == "tool":
                block = {"type": "tool_result", "tool_use_id": m["tool_call_id"], "content": m["content"]}
                if out and out[-1]["role"] == "user" and isinstance(out[-1]["content"], list):
                    out[-1]["content"].append(block)
                else:
                    out.append({"role": "user", "content": [block]})
            elif m.get("tool_calls"):
                content = ([{"type": "text", "text": m["content"]}] if m.get("content") else []) + [
                    {"type": "tool_use", "id": c["id"], "name": c["name"], "input": c["arguments"]}
                    for c in m["tool_calls"]]
                out.append({"role": "assistant", "content": content})
            else:
                out.append({"role": m["role"], "content": m["content"]})
        return out

    def chat(self, messages, tools):
        key = os.environ.get(self.key_env, "")
        if not key:
            raise RuntimeError(f"no API key in the environment variable {self.key_env}")
        headers = {"x-api-key": key, "anthropic-version": self.VERSION, "content-type": "application/json"}
        body = {"model": self.model, "max_tokens": self.max_tokens, "system": SYSTEM_PROMPT,
                "messages": self._messages(messages), "tools": tools}
        res = _post(self.URL, headers, body, self.timeout)
        text = "".join(b.get("text", "") for b in res.get("content", []) if b.get("type") == "text")
        calls = [{"id": b["id"], "name": b["name"], "arguments": b.get("input") or {}}
                 for b in res.get("content", []) if b.get("type") == "tool_use"]
        return Reply(text, calls)


def make_backend(kind: str, model: str = "", base_url: str = "", key_env: str = "") -> Backend:
    if kind in ("", "none"):
        return NoModel()
    if kind == "openai":
        return OpenAICompatible(model, base_url, key_env)
    if kind == "anthropic":
        return Anthropic(model, key_env or "ANTHROPIC_API_KEY")
    raise ValueError(f"unknown --llm {kind!r}: none, openai or anthropic")


def run_turn(backend: Backend, history: list, user_text: str, tools: list,
             execute: Callable[[str, dict], dict], max_rounds: int = 8,
             on_event: Optional[Callable[[dict], None]] = None) -> list:
    """One user turn: the model answers, its tool calls are executed (checked) and their results returned to it, until
    it answers without tools or max_rounds is reached. Returns the history with the turn's messages appended."""
    hist = list(history) + [{"role": "user", "content": user_text}]
    for _ in range(max_rounds):
        rep = backend.chat(hist, tools)
        msg = {"role": "assistant", "content": rep.text}
        if rep.tool_calls:
            msg["tool_calls"] = rep.tool_calls
        hist.append(msg)
        if on_event:
            on_event(msg)
        if not rep.tool_calls:
            return hist
        for c in rep.tool_calls:
            result = execute(c["name"], c["arguments"])
            tmsg = {"role": "tool", "tool_call_id": c["id"], "name": c["name"],
                    "content": json.dumps(result, default=str)[:20000]}
            hist.append(tmsg)
            if on_event:
                on_event(tmsg)
    hist.append({"role": "assistant", "content": f"(stopped after {max_rounds} tool rounds)"})
    return hist
