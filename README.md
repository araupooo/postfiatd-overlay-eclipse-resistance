# Overlay and Eclipse-Resistance in postfiatd

How postfiatd's peer-to-peer overlay resists Sybil flooding, eclipse
attacks, churn, and partition-and-rejoin — at commit
`0085a1ff885d6a446369cf73a4430f75af22be55` (2026-10-10).

## Headline findings

- **Outbound slots have no per-IP cap.** One attacker IP with 10
  distinct ports fills all 10 default outbound slots
  (`Logic.h:274-285` checks `ipLimit` only for inbound slots).
- **There is no subnet or prefix diversity anywhere in peer
  selection.** `ipLimit` is 2 per exact IP, inbound only; `diversity`
  and `subnet` have zero hits in the overlay and peerfinder trees.
- **Reserved and cluster slots bypass all caps with no bound on the
  reservation count** (`Counts.h:77-78`; `PeerReservationTable` has
  no size limit in the pinned source).
- **Redirect IPs enter the bootcache unchecked, up to 30 per
  redirect** (`Logic.h:1274-1280`) — a full peer can poison caches.
- **Fixed peers are the only anchor.** One fixed honest peer turns
  a single-IP eclipse into a degraded connection (scenario S-01);
  the default configuration has no fixed peers.
- **Eclipse threshold: 10 attacker endpoints fill all outbound
  slots regardless of IP count.** The threshold is endpoints, not
  IPs.

## Contents

- 45 rules (VERIFIED 38, SPECIFIED 4, MODELLED 2, UNTESTABLE 1) —
  `configs/overlay-eclipse-rules.json`, with grep-verified file:line
  ranges and verbatim excerpts in `fixtures/source-excerpts/` (44
  excerpts, 12 source files).
- Deterministic simulator (`src/overlay_eclipse_model.py`) + scenario
  matrix — 13 scenarios, 18 runs: connected 6, degraded 6,
  eclipsed 4, partitioned 2.
- Claim-to-evidence index: 24 claims (VERIFIED 16, SPECIFIED 2,
  MODELLED 4, UNTESTABLE 2) — `docs/claim-index.md`.
- Findings: 12 (HIGH 3, MEDIUM 5, LOW 4) — `findings.json`.
- Risk register: 14 risks (HIGH 3, MEDIUM 8, LOW 3) —
  `docs/risk-register.md`. Gap register: 8 gaps —
  `docs/gap-register.md`.
- Operator decision memo (fixed peers, reservations, partition
  recovery) — `docs/decision-memo.md`. Methodology —
  `docs/methodology.md`. Evidence index — `docs/evidence-index.md`.

## Reproduction

```bash
bash scripts/run_all.sh        # exit 0 only if every check passes
bash scripts/clean_reproduce.sh  # fresh-copy reproduction (run twice)
```

- Full suite: `run_all.sh` exits 0; probe 12/12 checks pass.
- `outputs/run.log` (unedited full-run log, 10 lines) SHA-256:
  `eb014519fb934e17492e532b4ab144228ab2820cd2c55b18d8a3443b0f220fe2`
- Fresh-copy reproduction was run twice; both passed with
  byte-identical deterministic outputs. Fresh-clone run log:
  `outputs/fresh-clone-run.log` SHA-256:
  `eb014519fb934e17492e532b4ab144228ab2820cd2c55b18d8a3443b0f220fe2`
  (identical to the shipped `run.log` digest — the first fresh copy
  reproduces the shipped log byte-for-byte). Second fresh-clone run
  log: `outputs/fresh-clone-2-run.log` SHA-256:
  `eb014519fb934e17492e532b4ab144228ab2820cd2c55b18d8a3443b0f220fe2`
  (also identical).
- Digests: `overlay-eclipse-results.json`
  `ecfd2059503b4d2b737d2f354864ffe0071a753ded191654556a392f31790a5e`;
  `scenario-matrix.json`
  `ac702a53b26a4862d4a67ab67bf6ed392ba1c39b23855986b30457b4baa0b9d3`.
- Verify all digests: `bash scripts/verify_digests.sh`.

The logs are independently resolvable as raw files:

https://raw.githubusercontent.com/araupooo/postfiatd-overlay-eclipse-resistance/main/outputs/run.log
https://raw.githubusercontent.com/araupooo/postfiatd-overlay-eclipse-resistance/main/outputs/fresh-clone-run.log
https://raw.githubusercontent.com/araupooo/postfiatd-overlay-eclipse-resistance/main/outputs/fresh-clone-2-run.log
https://raw.githubusercontent.com/araupooo/postfiatd-overlay-eclipse-resistance/main/outputs/probe-run.log

## CI

Continuous integration runs the same suite on every push; see the
workflow runs page:

https://github.com/araupooo/postfiatd-overlay-eclipse-resistance/actions/workflows/verify.yml

## What is simulated vs source-derived

- **Source-derived:** all 38 VERIFIED rules, the 44 excerpts, the
  peer-slot and eviction constants.
- **Simulated:** the 13 scenarios / 18 runs and the eclipse-threshold
  table — deterministic outputs of
  `src/overlay_eclipse_model.py` on the stated inputs in
  `configs/scenarios.json`. Simulated results are labelled MODELLED
  in the claim index and are never presented as code facts.
- **Unknown:** live-network state (real honest-peer pool sizes,
  churn rates, live eclipse resistance against a botnet with
  distinct public IPs) — see `docs/gap-register.md`. No live node
  was run.
