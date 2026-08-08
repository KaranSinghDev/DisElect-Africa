# Disclosure policy

This project measures whether language models will **write** election
disinformation when asked. Producing that measurement necessarily produces two
things that are unsafe to publish:

1. fully written, locale-specific false claims about real elections in South
   Africa, Kenya, the United Kingdom and Pennsylvania, and
2. the model responses in which a model complied, i.e. those same claims turned
   into fluent, publishable copy.

Released together, those are a ready-to-use disinformation kit aimed at real
electorates and requiring no skill to deploy. That is the exact harm this work
warns about, so they are withheld.

A note saying "these claims are artificial" does not help. Being false and
convincing is what makes the text dangerous; the artificiality is the one
property that does not matter to somebody who wants to use it.

## What is released

- the evaluation pipeline and the judge
- the constitution system prompt, in full
- the prompt **templates**, with each instantiated false claim replaced by a
  placeholder: `{WRONG_DATE}`, `{FALSE_STATION_RULE}`, `{FALSE_ID_RULE}`,
  `{FALSE_OFFICIAL_CLAIM}`, `{SEED_TWEET}`, `{OFFICIAL_NAME}`
- the verified ground truth and its official sources, so every claim remains
  checkable against the relevant electoral commission
- the benign control prompts, unchanged, because they contain no false claim
- the judgement labels and the aggregate statistics

## What is withheld

- the instantiated false claims
- the raw model responses

This follows the release practice of DisElect (Williams et al., PLOS One 2025),
which publishes results without raw model response text.

## Replicating an arm

The templates plus the ground-truth column are enough to rebuild a full arm.
A replicator supplies claims that contradict the verified procedure for their
own locale, and names checked against the sitting register for their own
jurisdiction. Official names in this release are `{OFFICIAL_NAME}` placeholders.

## Known limitation

The prompt files in this repository were public in unredacted form between June
and August 2026, so this redaction limits further distribution rather than
undoing the original release.
