# Smoke Test — DisElect-Africa

A minimal **elicit → judge** run to prove the pipeline works before the full base run. It sends ~10 SA
prompts to a model, judges each response with the DisElect 4-class scheme, and writes a results CSV + summary.
This is a **defensive AI-safety evaluation** — keep raw outputs private.

Supports two backends: **Ollama** (local, no API key) and **Gemini** (cloud API).

## What's here

- `run_smoke_ollama.py` — runner + LLM-as-judge for the **Ollama** path (local, no API key). Takes
  `--model` / `--judge-model` flags. (Also retains a `--backend gemini` option for parity.)
- `run_smoke_gemini.py` — runner + LLM-as-judge for the **Gemini** path (cloud API). Configured via the
  `MODELS_UNDER_TEST` / `JUDGE_MODEL` constants at the top of the file.
- `run_smoke.py` — convenience alias, identical to `run_smoke_gemini.py`.
- `list_models.py` — prints the exact Gemini model strings your key can call.
- `judge_template.txt` — DisElect's verbatim 4-class judge prompt.
- `smoke_prompts_south_africa.csv` — 10-prompt subset (3 News, 3 Reply, 2 MP, 2 benign).
- `requirements.txt`, `.env.example`.

---

## Option A — Ollama (local, no API key required) ✅ recommended for teammates

### 1. Install Ollama

Download from **https://ollama.com** and run the installer (Mac/Linux/Windows).

### 2. Pull a model

```bash
ollama pull llama3.2          # ~2 GB — good for a smoke test
# or a larger model for better judge quality:
ollama pull llama3.1
```

### 3. Start the Ollama server (if not already running)

```bash
ollama serve
```

Leave this terminal open. Ollama listens on `http://localhost:11434` by default.

### 4. Set up Python

```bash
cd smoke-test/
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 5. Run the smoke test

```bash
python run_smoke_ollama.py
```

To use a specific model:

```bash
python run_smoke_ollama.py --model llama3.2
```

To use a different model as the judge (e.g. a larger model):

```bash
python run_smoke_ollama.py --model llama3.2 --judge-model llama3.1
```

### Environment variables (optional)

| Variable | Default | Purpose |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Custom Ollama server URL |
| `OLLAMA_MODEL` | `llama3.1` | Default model when `--model` not passed |

---

## Option B — Gemini (cloud API)

### 1. Get a Gemini API key

Go to **https://aistudio.google.com/apikey**, sign in with a Google account, click **Create API key**.
The free tier is sufficient for the smoke test (~30 calls). Copy the key.

### 2. Install Python 3.10+ and deps

```bash
cd smoke-test/
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Add your key

```bash
cp .env.example .env
# open .env and set:  GEMINI_API_KEY=AIza...your_key...
```

(`.env` is git-ignored — never commit your key.)

### 4. Confirm model names

```bash
python list_models.py
```

Edit the `MODELS_UNDER_TEST` and `JUDGE_MODEL` constants in `run_smoke_gemini.py` if the defaults differ
from what your key can access.

### 5. Run

```bash
python run_smoke_gemini.py
```

### Quota / billing note

Google's free tier is ~20 requests/day for Flash models. The smoke test makes ~30 calls total, so on free
tier you may hit quota. Options: enable billing on AI Studio (cents for a few hundred calls), or use the
Ollama backend instead.

---

## What "passing" looks like

- Every prompt returns either a response or a logged block/error — no crashes.
- The judge returns one of the 4 classes (`comply / softrefuse / refuse / incoherent`) for each row.
  More than ~1 `unparsed` means the judge output needs a parsing tweak.
- Eyeball 3–4 rows in `smoke_results.csv`: does `judge_class` match the response?
- The 2 **benign** prompts should mostly be `comply` (model helps with legit info).

## Notes

- **Run params**: `temperature=1, top_p=0.95, top_k=40` for the model under test; judge at `temperature=0`.
- **Blocked vs refused**: platform safety blocks (Gemini) are logged as `blocked` and kept separate from
  model-level `refuse`. Local Ollama models have no platform filter — `blocked` will rarely appear on the
  Ollama path; this is expected and the column is kept for cross-backend parity.
- **Self-preference**: using the same model as judge and model-under-test is acceptable for a smoke test.
  For the real run, validate the judge against 30–50 hand labels (spec §4.2) and use a non-self judge.
- **Results CSV**: `smoke_results.csv` is git-ignored (raw model outputs; responsible-release).

## After the smoke test

- Run all 55 SA prompts × both models × **3 runs**; log every raw response.
- Compute compliance rates per arm/model; McNemar's + CIs for H1.
- Add the Constitutional-AI system prompt; re-run (H3).
