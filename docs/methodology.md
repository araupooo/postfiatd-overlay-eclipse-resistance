# Methodology

## Pinned source

All source findings are pinned to postfiatd commit
`0085a1ff885d6a446369cf73a4430f75af22be55` (2026-10-10). Every cited
line was verified with `grep -n` on a local checkout of that commit
(`~/workspace/postfiatd-pin-0085a1f`); no line number comes from a web
fetch. The 44 verbatim excerpts in `fixtures/source-excerpts/` were
extracted by `scripts/extract_excerpts.py` from that checkout, and
`fixtures/source-hashes.json` records the SHA-256, git blob SHA, and
size of every excerpt and every cited source file.

## How the rules were built

1. Read the overlay and peerfinder code paths end to end:
   `PeerfinderConfig` (maxPeers, outPercent, minOutCount, ipLimit,
   calcOutPeers), `Counts` (slot activation, fixed/reserved bypass,
   maxConnectAttempts, the dead `isConnectedToNetwork`),
   `Logic` (autoconnect order, inbound/outbound slot checks,
   duplicate endpoint and duplicate key checks, self-connect
   checks, endpoint gossip filtering, livecache expiry, redirect
   handling), `Bootcache` (valence, prune), `OverlayImpl`
   (bootstrap pools, redirect responses, resource limits, timer),
   `Handshake` (session signature, network ID, clock tolerance,
   key type, IP header consistency), `PeerImp` (send-queue
   eviction, diverged/unknown eviction, ping timeout),
   `ConnectAttempt` (15 second timeout), and `Config`
   (MAX_DIVERGED_TIME / MAX_UNKNOWN_TIME).
2. Recorded every hard-coded constant that bounds the behaviour:
   maxPeers 21, outPeers 10, inPeers 11, outPercent 15,
   minOutCount 10, ipLimit 2 (inbound only), maxConnectAttempts 20,
   bootcache 1000 entries with 10 percent prune, livecache TTL 30 s,
   maxHops 6, 12 endpoints per broadcast, at most 64 accepted per
   message, 10 redirect endpoints, at most 30 redirect IPs into
   the bootcache, 151 s endpoint cadence, 15 s connect timeout,
   20 s clock tolerance, 300 s / 600 s diverged / unknown eviction,
   sendq 192 / 128 / 4 intervals, 60 s peer timer, 1 s overlay
   timer.
3. Grepped for what is absent, not just what is present:
   `diversity` 0 hits, `subnet` 0 hits, `secondsPerConnect`
   defined but never used, `isConnectedToNetwork` defined but
   never called, `ipLimit` appearing only in `new_inbound_slot`.
   Absence claims are re-grepped by the probe (I-01).
4. Separated the four kinds of statement. VERIFIED rules are read
   from the pinned source with a file:line citation and a verbatim
   excerpt. SPECIFIED rules come from the public peer-protocol
   documentation (`docs/citations.md`) and are labelled as such.
   MODELLED rules are outputs of the deterministic simulator.
   UNTESTABLE rules cannot be decided from the pinned source alone.
   The claim index (`docs/claim-index.md`) carries the same labels
   on every claim.

## How the simulator works

`src/overlay_eclipse_model.py` reads `configs/scenarios.json` and
computes, for each run, attacker outbound endpoints
(`min(outPeers, attacker_ips * attacker_ports)` — outbound slots
have no per-IP cap), honest outbound links
(`min(outPeers - attacker_outbound, honest_pool)`), attacker
inbound endpoints (`min(inPeers, attacker_ips * 2)` — the ipLimit
cap applies inbound only), honest inbound links, and honest links
(`honest_outbound + fixed + reserved`; fixed and reserved slots
bypass the caps). Outcomes: connected when honest links are at
least 5 (half the outbound target), degraded at 1–4, eclipsed when
honest links are 0 but the victim is still connected (attacker
outbound > 0 or honest inbound > 0), partitioned when honest links
are 0, honest inbound is 0, and attacker outbound is 0 (no peer
connections at all). Partition and churn runs report the worst
phase; recovery rounds are `ceil(slots to refill / 20)` plus one
round when a rejoin follows total honest loss. No live node is
involved, no timestamps are recorded, and no wall-clock time is
measured: re-running produces byte-identical outputs.

## How the pack is verified

`scripts/run_all.sh` runs the full suite: excerpt extraction,
config validation, simulator, probe, run manifest, and a full
SHA-256 listing. `scripts/probe.py` re-derives every number from
the pinned checkout and the shipped outputs (12 checks, exit 0
only if all pass). `scripts/clean_reproduce.sh` runs the whole
suite twice from fresh copies and compares byte-for-byte; both
reproductions are shipped as `outputs/fresh-clone-*` and
`outputs/fresh-clone-2-*`. `scripts/verify_digests.sh` checks every
shipped file against `SHA256SUMS`.

## Limits

This pack measures code, not the live network. No live node was
run, no real network test was performed, and no honest-peer pool
sizes or churn rates were measured. Every attack outcome is a
simulator output on stated inputs (gaps G-01, G-02). The eclipse
threshold (10 attacker endpoints fill all outbound slots) is a
model consequence of the verified absence of a per-IP outbound
cap, not a live observation.
