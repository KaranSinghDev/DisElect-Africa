#!/usr/bin/env python3
"""
DisElect-Africa | Smoke test runner + LLM-as-judge.
Elicit -> Judge pipeline on a ~10-prompt SA subset, to prove the harness works
before the full base run. Defensive AI-safety evaluation (DisElect replication).

Supports two backends via --backend {gemini,ollama}:
  gemini  — Google Gemini API (requires GEMINI_API_KEY).
  ollama  — Local Ollama server (no API key required; default http://localhost:11434).

Key behaviours:
  - Retries 429 (RESOURCE_EXHAUSTED on Gemini) with exponential backoff.
  - Distinguishes API ERROR and platform SAFETY BLOCK from genuine model REFUSAL
    (an empty/failed response is NEVER silently counted as "refuse").
  - Robust text extraction for "thinking" Gemini models.
  - Local models (Ollama) have no platform safety filter, so "blocked" will rarely
    fire on the Ollama path — kept in output schema for cross-backend parity.

Run params follow the build spec: temperature=1, top_p=0.95, top_k=40 (judge at temp=0).
"""
import os, csv, sys, time, datetime, argparse, json
from pathlib import Path

try:
    from dotenv import load_dotenv; load_dotenv()
except ImportError:
    pass

# ──────────────────────────── CONFIG ────────────────────────────────────────
# Team standard: everyone runs local Ollama on the SAME model (gemma4:e4b) so results compare.
MODELS_UNDER_TEST = ["gemma4:e4b"]        # overridden by --model
JUDGE_MODEL       = None                  # None = same as model under test
MAX_PROMPTS       = None                  # e.g. 4 to keep a re-run tiny
PROMPTS_CSV       = "smoke_prompts_south_africa.csv"
JUDGE_TEMPLATE    = "judge_template.txt"
OUT_CSV           = "smoke_results.csv"

OLLAMA_BASE_URL   = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL      = os.environ.get("OLLAMA_MODEL", "gemma4:e4b")

GEN_CONFIG   = dict(temperature=1.0, top_p=0.95, top_k=40)   # model under test
JUDGE_CONFIG = dict(temperature=0.0)                          # deterministic judge
MAX_RETRIES  = 4
BASE_DELAY   = 5   # seconds; doubles each retry

DISELECT_CLASSES = ["comply", "softrefuse", "refuse", "incoherent"]
# Non-response analysis classes (kept SEPARATE from model behaviour):
#   blocked = platform safety filter;  error = API/quota failure (excluded from rates)
# ────────────────────────────────────────────────────────────────────────────

HERE = Path(__file__).parent


# ════════════════════════════════════════════════════════════════════════════
# Gemini backend
# ════════════════════════════════════════════════════════════════════════════

def _gemini_client():
    try:
        from google import genai
    except ImportError:
        sys.exit("Missing SDK. Run:  pip install -r requirements.txt")
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        sys.exit("Set GEMINI_API_KEY in .env (see .env.example / README.md).")
    return genai.Client(api_key=api_key)


def _gemini_call(client, model, contents, cfg):
    """Call Gemini with 429 backoff. Returns (response, error_str)."""
    from google.genai import types
    delay = BASE_DELAY
    for attempt in range(MAX_RETRIES):
        try:
            r = client.models.generate_content(
                model=model, contents=contents,
                config=types.GenerateContentConfig(**cfg))
            return r, None
        except Exception as e:
            msg = str(e)
            if ("429" in msg or "RESOURCE_EXHAUSTED" in msg) and attempt < MAX_RETRIES - 1:
                print(f"    429 quota — backing off {delay}s (attempt {attempt+1}/{MAX_RETRIES})")
                time.sleep(delay); delay *= 2; continue
            return None, f"{type(e).__name__}:{msg[:140]}"
    return None, "retries_exhausted"


def _gemini_extract_text(r):
    out = []
    for c in (getattr(r, "candidates", None) or []):
        content = getattr(c, "content", None)
        for p in (getattr(content, "parts", None) or []):
            t = getattr(p, "text", None)
            if t:
                out.append(t)
    return "".join(out)


def gemini_generate(client, model, prompt, cfg):
    r, err = _gemini_call(client, model, prompt, cfg)
    if err:
        return "", f"ERROR:{err}"
    pf = getattr(r, "prompt_feedback", None)
    if pf and getattr(pf, "block_reason", None):
        return "", f"BLOCKED:{pf.block_reason}"
    finish = ""
    cands = getattr(r, "candidates", None) or []
    if cands:
        finish = str(getattr(cands[0], "finish_reason", "") or "")
    text = _gemini_extract_text(r)
    if not text:
        if "SAFETY" in finish.upper():
            return "", f"BLOCKED:{finish}"
        return "", f"NO_TEXT:{finish or 'unknown'}"
    return text, finish or "STOP"


# ════════════════════════════════════════════════════════════════════════════
# Ollama backend  (uses the OpenAI-compatible /v1/chat/completions endpoint)
# ════════════════════════════════════════════════════════════════════════════

def _ollama_call(model, messages, cfg):
    """Call local Ollama with retry on connection errors. Returns (data_dict, error_str)."""
    import urllib.request, urllib.error
    url = f"{OLLAMA_BASE_URL.rstrip('/')}/v1/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "temperature": cfg.get("temperature", 1.0),
        "top_p": cfg.get("top_p", 0.95),
        "stream": False,
    }
    if "top_k" in cfg:
        payload["options"] = {"top_k": cfg["top_k"]}

    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    delay = BASE_DELAY
    for attempt in range(MAX_RETRIES):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.loads(resp.read().decode()), None
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < MAX_RETRIES - 1:
                print(f"    Ollama 429 — backing off {delay}s")
                time.sleep(delay); delay *= 2; continue
            return None, f"HTTPError:{e.code}:{e.reason}"
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                print(f"    Ollama error ({e}) — retry {attempt+1}/{MAX_RETRIES}")
                time.sleep(delay); delay *= 2; continue
            return None, f"{type(e).__name__}:{str(e)[:140]}"
    return None, "retries_exhausted"


def ollama_generate(model, prompt, cfg):
    messages = [{"role": "user", "content": prompt}]
    data, err = _ollama_call(model, messages, cfg)
    if err:
        return "", f"ERROR:{err}"
    try:
        text = data["choices"][0]["message"]["content"]
        finish = data["choices"][0].get("finish_reason", "stop") or "stop"
        return text, finish.upper()
    except (KeyError, IndexError, TypeError) as e:
        return "", f"NO_TEXT:{e}"


# ════════════════════════════════════════════════════════════════════════════
# Shared classification + judge
# ════════════════════════════════════════════════════════════════════════════

def classify_nonresponse(status):
    s = status.upper()
    if s.startswith("ERROR"):
        return "error"
    if "BLOCK" in s or "SAFETY" in s:
        return "blocked"
    return "incoherent"


def _parse_judge_text(raw):
    low = raw.lower().replace("*", "")
    token = low.strip().split()[0].strip('.:,"\'') if low.strip() else ""
    if token in DISELECT_CLASSES:
        return token
    found = [c for c in DISELECT_CLASSES if c in low]
    return found[0] if len(found) == 1 else "unparsed"


def judge(prompt, response, status, backend, judge_model, gemini_client=None):
    """Return (raw, class). Only calls the judge when there is real text."""
    if not response.strip():
        return f"(no response: {status})", classify_nonresponse(status)

    tmpl = (HERE / JUDGE_TEMPLATE).read_text(encoding="utf-8")
    q = tmpl.replace("{INPUT_PROMPT}", prompt).replace("{OUTPUT_RESPONSE}", response)

    if backend == "gemini":
        r, err = _gemini_call(gemini_client, judge_model, q, JUDGE_CONFIG)
        if err:
            return f"JUDGE_ERROR:{err[:60]}", "error"
        raw = _gemini_extract_text(r).strip()
    else:
        data, err = _ollama_call(judge_model, [{"role": "user", "content": q}], JUDGE_CONFIG)
        if err:
            return f"JUDGE_ERROR:{err[:60]}", "error"
        try:
            raw = data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as e:
            return f"JUDGE_ERROR:{e}", "error"

    return raw[:80], _parse_judge_text(raw)


# ════════════════════════════════════════════════════════════════════════════
# Main
# ════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="DisElect-Africa smoke test runner")
    parser.add_argument(
        "--backend", choices=["gemini", "ollama"], default="ollama",
        help="Model backend to use (default: ollama)"
    )
    parser.add_argument(
        "--model", default=None,
        help="Model name to test (default: OLLAMA_MODEL env var or 'gemma4:e4b' for ollama; "
             "edit MODELS_UNDER_TEST in script for gemini)"
    )
    parser.add_argument(
        "--judge-model", default=None, dest="judge_model",
        help="Judge model (default: same as --model)"
    )
    parser.add_argument(
        "--max-prompts", type=int, default=MAX_PROMPTS, dest="max_prompts",
        help="Limit number of prompts (useful for quick re-runs)"
    )
    args = parser.parse_args()

    backend = args.backend

    # Resolve models
    if backend == "ollama":
        models_under_test = [args.model or OLLAMA_MODEL]
    else:
        models_under_test = [args.model] if args.model else MODELS_UNDER_TEST

    judge_model_name = args.judge_model or models_under_test[0]

    # Init Gemini client if needed
    gemini_client = None
    if backend == "gemini":
        gemini_client = _gemini_client()

    # Check Ollama is reachable before starting
    if backend == "ollama":
        import urllib.request, urllib.error
        try:
            urllib.request.urlopen(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        except Exception as e:
            sys.exit(
                f"Cannot reach Ollama at {OLLAMA_BASE_URL} ({e}).\n"
                f"Start Ollama with:  ollama serve\n"
                f"Then pull a model:  ollama pull {models_under_test[0]}"
            )

    prompts = list(csv.DictReader(open(HERE / PROMPTS_CSV, encoding="utf-8")))
    max_p = args.max_prompts
    if max_p:
        prompts = prompts[:max_p]

    print(f"Backend : {backend}")
    print(f"Models  : {models_under_test}")
    print(f"Judge   : {judge_model_name}")
    print(f"Prompts : {len(prompts)}\n")

    results = []
    for model in models_under_test:
        for p in prompts:
            prompt_text = p["prompt_text"]

            # Generate
            if backend == "gemini":
                resp, status = gemini_generate(gemini_client, model, prompt_text, GEN_CONFIG)
            else:
                resp, status = ollama_generate(model, prompt_text, GEN_CONFIG)

            # Judge
            raw_j, label = judge(
                prompt_text, resp, status,
                backend, judge_model_name, gemini_client=gemini_client
            )

            results.append({
                "prompt_id":       p["prompt_id"],
                "model":           model,
                "backend":         backend,
                "stage":           p["stage"],
                "subject_id":      p["subject_id"],
                "persona_id":      p.get("persona_id", ""),
                "is_false":        p["is_false"],
                "gen_status":      status,
                "judge_class":     label,
                "judge_label_raw": raw_j,
                "response_text":   resp.replace("\n", " ").strip(),
                "prompt_text":     prompt_text,
                "timestamp":       datetime.datetime.now().isoformat(timespec="seconds"),
            })
            print(f"[{model}] {p['prompt_id']:<7} {p['stage']:<11} -> {label:<12} ({status[:40]})")
            time.sleep(0.3)

    cols = [
        "prompt_id", "model", "backend", "stage", "subject_id", "persona_id",
        "is_false", "gen_status", "judge_class", "judge_label_raw",
        "response_text", "prompt_text", "timestamp",
    ]
    with open(HERE / OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(results)

    from collections import Counter
    print("\n=== SMOKE SUMMARY (counts by judge class) ===")
    all_classes = DISELECT_CLASSES + ["blocked", "unparsed", "error"]
    for model in models_under_test:
        sub = [r for r in results if r["model"] == model]
        c = Counter(r["judge_class"] for r in sub)
        disinfo = [r for r in sub if r["is_false"] == "TRUE"]
        valid = [r for r in disinfo if r["judge_class"] not in ("error",)]
        comply = sum(1 for r in valid if r["judge_class"] == "comply")
        n_err = sum(1 for r in disinfo if r["judge_class"] == "error")
        print(f"\n{model}  [{backend}]:")
        for cls in all_classes:
            if c.get(cls):
                print(f"   {cls:<11}: {c[cls]}")
        denom = len(valid)
        rate = f"{comply}/{denom}" if denom else "n/a (no valid responses)"
        print(f"   --> compliance on disinfo prompts: {rate}"
              + (f"   [{n_err} excluded: API errors]" if n_err else ""))

    errs = sum(1 for r in results if r["judge_class"] == "error")
    if errs:
        print(f"\n!! {errs} API errors. Results are not valid until these clear.")
    print(f"\nWrote {OUT_CSV}.")


if __name__ == "__main__":
    main()
