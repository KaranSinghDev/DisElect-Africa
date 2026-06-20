#!/usr/bin/env python3
"""Print the Gemini models your API key can call (and which support generateContent).
Run this FIRST to confirm the exact model strings to put in run_smoke.py CONFIG."""
import os, sys
try:
    from google import genai
except ImportError:
    sys.exit("Run:  pip install -r requirements.txt")
try:
    from dotenv import load_dotenv; load_dotenv()
except ImportError:
    pass

key = os.environ.get("GEMINI_API_KEY")
if not key:
    sys.exit("Set GEMINI_API_KEY (see .env.example).")
client = genai.Client(api_key=key)
print("Models available to your key (supporting generateContent):\n")
for m in client.models.list():
    actions = getattr(m, "supported_actions", None) or []
    if not actions or "generateContent" in actions:
        print(f"  {m.name:<45} {getattr(m,'display_name','')}")
print("\nCopy the Flash + Pro strings you want into run_smoke.py "
      "(MODELS_UNDER_TEST and JUDGE_MODEL).")
