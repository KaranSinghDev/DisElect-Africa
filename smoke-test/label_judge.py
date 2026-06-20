#!/usr/bin/env python3
"""
Judge validation — STEP 1: blind human labelling (DisElect spec §4.2).

Shows each model RESPONSE and asks you to classify it into one of DisElect's 4 classes,
WITHOUT showing the judge's label (blind, to avoid anchoring). Saves after every label and
is resumable. Then run validate_judge.py to compare your labels to the judge.

Usage:
    python label_judge.py                      # labels smoke_results.csv -> human_labels.csv
    python label_judge.py --results FILE --labels OUT --rater JP
    python label_judge.py --show-judge         # NOT blind (only if you really want it)
"""
import csv, argparse, datetime, sys
from pathlib import Path

CLASSES = {"c": "comply", "s": "softrefuse", "r": "refuse", "i": "incoherent"}
HELP = "[c]omply  [s]oftrefuse  [r]efuse  [i]ncoherent  |  [k]skip  [q]save+quit"


def load_done(labels_path):
    done = {}
    if labels_path.exists():
        for row in csv.DictReader(open(labels_path, encoding="utf-8")):
            done[(row["prompt_id"], row["model"])] = row["human_class"]
    return done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="smoke_results.csv")
    ap.add_argument("--labels", default="human_labels.csv")
    ap.add_argument("--rater", default="")
    ap.add_argument("--show-judge", action="store_true")
    a = ap.parse_args()

    rp, lp = Path(a.results), Path(a.labels)
    if not rp.exists():
        sys.exit(f"No results file: {rp}")
    rows = list(csv.DictReader(open(rp, encoding="utf-8")))
    # Only validatable rows: a real text response exists (skip API errors / safety blocks).
    rows = [r for r in rows if (r.get("response_text") or "").strip()]
    done = load_done(lp)
    todo = [r for r in rows if (r["prompt_id"], r["model"]) not in done]

    print(f"\n{len(rows)} responses with text; {len(done)} already labelled; {len(todo)} to go.")
    if not todo:
        print("Nothing left to label. Run:  python validate_judge.py")
        return
    rater = a.rater or input("Your initials (rater id): ").strip() or "anon"

    new_file = not lp.exists()
    out = open(lp, "a", newline="", encoding="utf-8")
    w = csv.writer(out)
    if new_file:
        w.writerow(["prompt_id", "model", "human_class", "rater", "timestamp"])

    for i, r in enumerate(todo, 1):
        print("\n" + "=" * 78)
        print(f"[{i}/{len(todo)}]  {r['prompt_id']}  | model: {r['model']}  | stage: {r['stage']}"
              f"  | is_false: {r['is_false']}")
        print("-" * 78)
        print("PROMPT:\n  " + r["prompt_text"])
        print("\nRESPONSE:\n  " + r["response_text"])
        if a.show_judge:
            print(f"\n[judge said: {r.get('judge_class','?')}]")
        print("-" * 78)
        while True:
            choice = input(f"{HELP}\n> ").strip().lower()
            if choice in ("q", "quit"):
                out.close()
                print(f"\nSaved {i-1} new labels to {lp}. Re-run to continue.")
                return
            if choice in ("k", "skip"):
                break
            # accept letter or full word
            cls = CLASSES.get(choice) or (choice if choice in CLASSES.values() else None)
            if cls:
                w.writerow([r["prompt_id"], r["model"], cls, rater,
                            datetime.datetime.now().isoformat(timespec="seconds")])
                out.flush()
                break
            print("  ? enter one of c / s / r / i (or k, q)")

    out.close()
    print(f"\nDone. Labels in {lp}. Next:  python validate_judge.py")


if __name__ == "__main__":
    main()
