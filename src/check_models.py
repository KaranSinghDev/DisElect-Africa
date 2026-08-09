#!/usr/bin/env python3
"""
Step 1: OpenRouter model availability + service-quality check.

What it does:
  1. Pulls the LIVE list of FREE models from OpenRouter (so model IDs are never stale).
  2. Shows your account's rate limit / usage.
  3. Burst-pings each free model to measure success rate + latency, then RANKS them
     by service quality -- i.e. which models actually serve requests reliably right now.

Setup:  pip install openai python-dotenv      (.env: OPENROUTER_API_KEY=...)
Run:    python3 check_models.py
"""

import os
import json
import time
import urllib.request

try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass

from openai import OpenAI

BASE = "https://openrouter.ai/api/v1"
KEY = os.getenv("OPENROUTER_API_KEY")

MAX_MODELS = 15    # cap how many free models we ping (protects your rate limit)
PINGS = 3          # quick calls per model to gauge burst tolerance
GAP = 0.4          # seconds between pings (small gap => tests burst capacity)


def _get(path):
    req = urllib.request.Request(BASE + path,
                                 headers={"Authorization": f"Bearer {KEY}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def free_models():
    data = _get("/models").get("data", [])
    free = []
    for m in data:
        p = m.get("pricing", {}) or {}
        try:
            if float(p.get("prompt", 1)) == 0 and float(p.get("completion", 1)) == 0:
                free.append(m["id"])
        except (TypeError, ValueError):
            continue
    return free


def show_account_limit():
    try:
        k = _get("/key").get("data", {})
        print(f"Account: limit={k.get('limit')}  used={k.get('usage')}  "
              f"free_tier={k.get('is_free_tier')}  rate_limit={k.get('rate_limit')}")
    except Exception as e:
        print(f"(could not read /key: {e})")


def burst(client, model):
    ok, lat = 0, []
    for _ in range(PINGS):
        t = time.time()
        try:
            client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "ok"}],
                max_tokens=2, temperature=0, timeout=30)  # 30s cap per call
            ok += 1
            lat.append(time.time() - t)
        except Exception:
            break  # took >30s or errored -> skip to the next model
        time.sleep(GAP)
    avg = sum(lat) / len(lat) if lat else None
    return ok, avg


def main():
    if not KEY:
        raise SystemExit("OPENROUTER_API_KEY not found (.env or export).")
    client = OpenAI(base_url=BASE, api_key=KEY, default_headers={"X-Title": "model-check"})

    show_account_limit()
    try:
        models = free_models()
    except Exception as e:
        raise SystemExit(f"Could not fetch model list: {e}")
    print(f"{len(models)} free models found; burst-testing up to {MAX_MODELS}.\n")
    models = models[:MAX_MODELS]

    rows = []
    print(f"{'model':<48}{'ok':>6}{'avg_s':>9}")
    print("-" * 64)
    for m in models:
        ok, avg = burst(client, m)
        rows.append((m, ok, avg))
        avg_str = f"{avg:.1f}" if avg else "-"
        print(f"{m:<48}{ok:>3}/{PINGS}{avg_str:>9}")

    rows.sort(key=lambda r: (-r[1], r[2] if r[2] is not None else 9e9))
    print("\nRecommended (fully reliable under burst, fastest first):")
    best = [r for r in rows if r[1] == PINGS]
    for m, ok, avg in best:
        print(f"   {m}   ({avg:.1f}s avg)")
    if not best:
        print("   (none passed all pings cleanly -- pick the highest 'ok' rows above)")
    print("\nPut the top 4-5 into your eval MODELS list.")


if __name__ == "__main__":
    main()
