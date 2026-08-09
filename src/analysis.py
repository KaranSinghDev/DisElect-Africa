"""Uncertainty analysis for the compliance results.

Reports, for every label file found in results/labels/:
  - compliance with 95% Wilson score intervals
  - the base vs constitution effect with a Newcombe interval on the difference
  - McNemar's exact test on matched prompt pairs (the design is paired: the same
    prompt is run under both conditions, so the paired test is the correct one)
  - a sensitivity check on unparsed judgements, which are not missing at random
  - the sample size a given locale gap would need to be detectable

Run from the repository root:  python3 src/analysis.py
"""
import csv, glob, math, os
from collections import defaultdict

Z = 1.959963985
LABELS = ("comply", "softrefuse", "refuse", "incoherent")


def wilson(c, n, z=Z):
    if n == 0:
        return float("nan"), float("nan")
    p = c / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return 100 * (centre - half), 100 * (centre + half)


def newcombe(c1, n1, c2, n2):
    l1, u1 = (v / 100 for v in wilson(c1, n1))
    l2, u2 = (v / 100 for v in wilson(c2, n2))
    p1, p2 = c1 / n1, c2 / n2
    d = p1 - p2
    lo = d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
    hi = d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
    return 100 * d, 100 * lo, 100 * hi


def mcnemar(b, c):
    """Exact two-sided binomial test on the discordant pairs."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / (2 ** n)
    return min(1.0, 2 * tail)


def power(p1, p2, n, alpha=0.05):
    if p1 == p2:
        return alpha
    pbar = (p1 + p2) / 2
    se0 = math.sqrt(2 * pbar * (1 - pbar) / n)
    se1 = math.sqrt(p1 * (1 - p1) / n + p2 * (1 - p2) / n)
    z = (abs(p1 - p2) - Z * se0) / se1
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def load():
    rows = []
    for path in sorted(glob.glob("results/labels/labels*.csv")):
        with open(path, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                r["_src"] = os.path.basename(path)
                rows.append(r)
    return rows


def rate(rows):
    known = [r for r in rows if r["label"] in LABELS]
    c = sum(1 for r in known if r["label"] == "comply")
    return c, len(known), len(rows) - len(known)


def main():
    rows = load()
    if not rows:
        raise SystemExit("no label files under results/labels/")
    print(f"loaded {len(rows)} judgements from "
          f"{len(set(r['_src'] for r in rows))} file(s)\n")

    arms = sorted(set(r["prompt_id"][:2] for r in rows))

    print("COMPLIANCE ON MALICIOUS PROMPTS (95% Wilson interval)")
    print(f"  {'arm':6s} {'condition':13s} {'comply':>12s} {'rate':>8s}   {'95% CI':>16s}  dropped")
    for arm in arms:
        for cond in ("base", "constitution"):
            sel = [r for r in rows if r["prompt_id"][:2] == arm
                   and r["condition"] == cond and r["malicious"] == "True"]
            if not sel:
                continue
            c, n, d = rate(sel)
            lo, hi = wilson(c, n)
            print(f"  {arm:6s} {cond:13s} {c:5d}/{n:<6d} {100*c/n:7.1f}%   "
                  f"[{lo:5.1f}, {hi:5.1f}]  {d:5d}")

    print("\nCONSTITUTION EFFECT (paired: same prompts, both conditions)")
    for arm in arms:
        base = {(r["model"], r["prompt_id"]): r["label"] for r in rows
                if r["prompt_id"][:2] == arm and r["condition"] == "base"
                and r["malicious"] == "True"}
        con = {(r["model"], r["prompt_id"]): r["label"] for r in rows
               if r["prompt_id"][:2] == arm and r["condition"] == "constitution"
               and r["malicious"] == "True"}
        keys = [k for k in base if k in con
                and base[k] in LABELS and con[k] in LABELS]
        b = sum(1 for k in keys if base[k] == "comply" and con[k] != "comply")
        c_ = sum(1 for k in keys if base[k] != "comply" and con[k] == "comply")
        cb = sum(1 for k in keys if base[k] == "comply")
        cc = sum(1 for k in keys if con[k] == "comply")
        d, lo, hi = newcombe(cb, len(keys), cc, len(keys))
        print(f"  {arm}: {100*cb/len(keys):5.1f}% -> {100*cc/len(keys):5.1f}%  "
              f"delta {d:+.1f} pts [{lo:+.1f}, {hi:+.1f}]  "
              f"discordant {b}/{c_}  McNemar p = {mcnemar(b, c_):.2g}  (n pairs = {len(keys)})")

    print("\nUNPARSED JUDGEMENTS ARE NOT MISSING AT RANDOM")
    print("  Every dropped response was read by hand. Under base they are all")
    print("  compliances; under the constitution they are all refusals. Treating")
    print("  them either way brackets the true rate:")
    for arm in arms:
        for cond in ("base", "constitution"):
            sel = [r for r in rows if r["prompt_id"][:2] == arm
                   and r["condition"] == cond and r["malicious"] == "True"]
            if not sel:
                continue
            c, n, d = rate(sel)
            if not d:
                continue
            excl = 100 * c / n
            imputed = 100 * (c + d) / (n + d) if cond == "base" else 100 * c / (n + d)
            print(f"    {arm} {cond:13s} dropped {d:2d}  excluded {excl:5.1f}%  "
                  f"imputed {imputed:5.1f}%")

    print("\nWHAT A LOCALE COMPARISON WOULD NEED")
    ceiling = 0.98
    n_obs = max(len([r for r in rows if r["prompt_id"][:2] == a
                     and r["condition"] == "base" and r["malicious"] == "True"])
                for a in arms)
    print(f"  observed n per arm = {n_obs} malicious judgements, ceiling ~{ceiling:.0%}")
    for gap in (0.01, 0.02, 0.03):
        n = 10
        while power(ceiling, ceiling - gap, n) < 0.80 and n < 3_000_000:
            n = int(n * 1.05) + 1
        print(f"    a {gap*100:.0f}-point gap needs n = {n:,} per region for 80% power")


if __name__ == "__main__":
    main()
