# capri-mod as a Hugging Face Space (draft)

How to put the GUI (`capri_gradio/`) on a Space. Nothing here is deployed by the repository's tools: the project lead
pushes to the Space.

## Decided (7 November 2026)

- The Space runs capri-mod and the GUI; the language model is **called, not run, in the Space**: gpt-oss through
  Hugging Face's Inference Providers (OpenAI-compatible router, `https://router.huggingface.co/v1`, tool calling
  supported; huggingface.co/docs/inference-providers/guides/gpt-oss). gpt-oss-20b alone needs about 16 GB, the whole
  of a CPU Basic Space.
- The Space stays **private** until the Bonn review and the CAPRI data-rights question are settled (it holds CAPRI's
  data).

## The Space's README front matter

The Space repository's README.md starts with (Spaces read it; app_file points at this folder's entry point):

```yaml
---
title: capri-mod
sdk: gradio
app_file: capri_gradio/app.py
python_version: "3.12"
pinned: false
---
```

`sdk_version` may be added to pin gradio (the draft is tested with 5.49.1). The Python version is to be checked
against those Spaces offer: capri-mod needs 3.10 or later and is tested here on 3.13.

## Variables and secrets (the Space's settings page)

| Name | Kind | Value |
|---|---|---|
| `CAPRI_LLM` | variable | `openai` |
| `CAPRI_LLM_BASE_URL` | variable | `https://router.huggingface.co/v1` |
| `CAPRI_LLM_MODEL` | variable | `openai/gpt-oss-120b:<provider>` (or the 20b; the provider suffix from the model's page) |
| `CAPRI_LLM_KEY_ENV` | variable | `HF_TOKEN` |
| `HF_TOKEN` | **secret** | a Hugging Face token with inference permission |
| `CAPRI_SHARED` | variable | `1` (each session its own scenarios, mini-EU runs only) |

The key is never written to a file or the repository; the GUI reads the variable named by `CAPRI_LLM_KEY_ENV`.

## What the Space repository needs

- The repository's code and `capri_data/` (the model's inputs), `requirements.txt` at the root (the Space installs it).
- A results store with at least one run, for the Results tab: `results/` (the run script writes it), or
  `CAPRI_RESULTS_DIR`.
- Not the HSL library (not redistributable): IPOPT runs with MUMPS, the default.

## Open before it is used by others

- **Persistence:** a Space's disk is not persistent; scenarios and runs written there are lost on a restart unless
  kept in a Hugging Face dataset (to be built).
- **Load:** CPU Basic has 2 vCPU and 16 GB; a mini-EU run takes about ten minutes and holds both cores; the page
  runs one at a time for everyone.
- **The model's quality on this task:** to be measured on a fixed set of requests (Farm-to-Fork variants, a carbon
  tax, a value it must correct) before its scenarios are trusted.
- **Cost:** the router's free monthly credits, then pay-as-you-go; a Gradio Space needs a paid plan (CPU Basic itself
  has no hourly cost).
