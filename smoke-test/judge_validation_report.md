# Judge validation report (DisElect §4.2)

_Generated 2026-06-20T20:59:51 · results=`smoke_results.csv` · labels=`human_labels.csv`_


## Headline

- Pairs compared: **10**  (excluded: 0)
- Accuracy: **1.00**
- **Macro-F1: 1.00**   _(DisElect benchmark ≈ 0.76)_
- Cohen's κ: **1.00**   _(>0.6 acceptable, >0.8 strong)_

> ⚠️ Only 10 pairs — metrics are noisy. Spec wants 30–50 for a real estimate.

## Per-class (gold = human labels)

| class | TP | FP | FN | precision | recall | F1 |
|---|---|---|---|---|---|---|
| comply | 10 | 0 | 0 | 1.00 | 1.00 | 1.00 |

## Confusion matrix (rows = human, cols = judge)

| human\judge | comply |
|---|---|
| comply | 10 |

## Disagreements (0) — eyeball these

_None — judge matched human on every pair._