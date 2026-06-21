# DisElect-Africa — Compliance Pipeline

Runs the election-disinformation **compliance** evaluation on any set of models.
For every prompt it: (1) asks a model to generate, (2) asks a separate **judge**
model to label the response, and (3) reports compliance rates.

Labels (DisElect's 4 classes): `comply` / `softrefuse` / `refuse` / `incoherent`.

Headline numbers it prints:
- **H1** — malicious comply rate: **African arms (A) vs Western arms (W)**
- **H2** — malicious comply: **base vs constitution** (does the fix help?)
- **H3** — benign comply: base vs constitution (does the fix over-refuse safe questions?)

---

## Run it in 4 steps

1. **Install:** `pip install openai python-dotenv`
2. **Start your model server** (either works — both are OpenAI-compatible):
   - **LM Studio:** Developer → Start Server (port 1234) → `http://<host>:1234/v1`
   - **Ollama:** already serves `http://localhost:11434/v1`
3. **Edit the CONFIG block** at the top of `src/compliance_eval.py` (table below).
4. **Run from the repo root:** `python3 src/compliance_eval.py`

---

## What to change for YOUR system (the CONFIG block)

| Setting | What it is | Examples |
|---|---|---|
| `GEN_BASE_URL` | your model server | LM Studio `http://localhost:1234/v1` · Ollama `http://localhost:11434/v1` · WSL→Windows `http://172.19.0.1:1234/v1` |
| `MODELS` | models to test (exact ids) | `["llama-3.2-3b-instruct", "gemma-2-2b-it", ...]` |
| `JUDGE_BASE_URL` / `JUDGE_MODEL` | the judge — **must NOT be a tested model** | local Mistral 7B, or Gemini (commented block provided) |
| `CONDITIONS` | which conditions to run | `["base"]` or `["base", "constitution"]` |
| `LIMIT` | prompts to run | `5` = smoke test · `None` = all |

**Find your exact model ids:** `curl http://<your-host>:1234/v1/models`
(ignore any `text-embedding-*` entry — that's not a chat model.)

---

## Using a hosted API instead of a local server (e.g. Gemini Flash)

The harness talks plain OpenAI format, so any OpenAI-compatible API works — just point
the `GEN_*` (to test an API model) or `JUDGE_*` (to judge with one) at it.

**Gemini (Google AI Studio — free tier, get a key at aistudio.google.com):**
```python
GEN_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
GEN_API_KEY  = os.getenv("GEMINI_API_KEY")     # put the key in .env, never hard-code it
MODELS       = ["gemini-2.5-flash-lite"]        # confirm the current id in AI Studio
SLEEP        = 1.0                              # pace the free tier (avoid 429s)
```
The same three lines work for the **judge** (`JUDGE_BASE_URL` / `JUDGE_API_KEY` /
`JUDGE_MODEL`). Using Gemini as the **judge** is the most credible setup — a frontier
judge beats a small local one.

**Other APIs** (OpenAI, OpenRouter, etc.) follow the identical pattern: change
`BASE_URL`, `API_KEY`, and the model id. Only the base URL and model name differ.

**Keys:** store them in a `.env` file (e.g. `GEMINI_API_KEY=...`) — `.env` is gitignored,
so keys never get committed. Read them with `os.getenv("GEMINI_API_KEY")` as above.

> With an API you may hit rate limits across 55 prompts × conditions × models — set
> `SLEEP` (1–2s) and/or test with `LIMIT = 5` first.

---

## Outputs (after a run)

- `results/labels/labels.csv` — one row per (model, condition, prompt). **Safe to share.**
- `results/summary/summary.json` — the headline rates.
- `results/raw/*.jsonl` — full model responses. **GITIGNORED — never commit (holds generated content).**

Rates exclude failed/unknown judgements from the denominator and report how many were dropped.

---

## Add your country arm

Drop a `prompts_<country>.csv` into `prompts/` using the 16-column schema in
`prompts/SCHEMA.md`. Key fields the harness uses:
`arm` (`A`=African / `W`=Western), `is_false` (`TRUE`=malicious / `FALSE`=benign),
`prompt_text` (sent to the model). It auto-loads every `prompts/prompts_*.csv`.

## The constitution (the fix)

`constitution/constitution.md` is the system prompt used in the `constitution` condition.
Edit it to test different safeguards. **Keep it principle-based** — do NOT hard-code an
exact refusal sentence; that just measures your own prompt, not the model's behaviour.

---

## Rules that keep the results credible

- **The judge must not be one of the tested models** (no self-grading).
- Prefer a strong judge (e.g. Gemini) over a small one. If you use a small local
  judge, hand-check ~25 labels and report the human-agreement rate.
- Quantize at **Q4_K_M minimum** — heavier quant (Q2/Q3) changes safety behaviour.
- **Never commit `results/raw/`** — it contains the generated disinformation.
