#!/usr/bin/env python3
"""overlay_eclipse_model.py — deterministic overlay / eclipse-resistance model.

Usage:
    python3 src/overlay_eclipse_model.py [--help]

Reads configs/scenarios.json and writes:
    outputs/derived/overlay-eclipse-results.json
    outputs/derived/scenario-matrix.json

Every number comes from the scenario inputs plus the pinned-code
constants in configs/scenarios.json (maxPeers 21, outPeers 10,
inPeers 11, per-IP inbound limit 2, 20 simultaneous connect attempts,
bootcache 1000 entries, livecache TTL 30 s, maxHops 6, 12 endpoints per
broadcast, at most 64 accepted per message, 10 redirect endpoints, at
most 30 redirect IPs into the bootcache, 151 s endpoint cadence,
15 s connect timeout, 20 s clock tolerance, 300 s / 600 s diverged /
unknown eviction, sendq 192 / 128 / 4 intervals, 60 s peer timer).
No live node is involved, no timestamps are recorded, and no wall-clock
time is measured: re-running produces byte-identical outputs.

Outcome rules (each is a direct application of a pinned rule):
  - Outbound slots have no per-IP cap (ipLimit is checked only for
    inbound slots), so attacker outbound endpoints are
    min(outPeers, attacker_ips * attacker_ports).
  - Honest outbound links are min(outPeers - attacker_outbound,
    honest_pool); handshake-rejected attackers take no slots.
  - Inbound slots are capped at 2 per public IP, so attacker inbound
    endpoints are min(inPeers, attacker_ips * 2).
  - honest_links = honest_outbound + fixed anchors + reserved anchors.
    Fixed and reserved slots bypass the caps.
  - connected: honest_links >= 5 (at least half the outbound target).
  - degraded: 1 <= honest_links <= 4.
  - eclipsed: honest_links == 0 while the victim is still connected
    (attacker outbound > 0 or honest inbound > 0): its outbound view
    is fully attacker-controlled.
  - partitioned: honest_links == 0, honest inbound == 0, and attacker
    outbound == 0: the victim has no peer connections at all.
  - Partition / churn runs report the worst phase; recovery rounds are
    ceil(slots to refill / 20) plus one round when a rejoin follows a
    total honest loss.
"""
import json
import math
import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parent.parent
PINNED_COMMIT = "0085a1ff885d6a446369cf73a4430f75af22be55"


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def simulate_run(scenario, run, consts):
    p = run["params"]
    out_peers = consts["out_peers"]
    in_peers = consts["in_peers"]
    ip_limit = consts["ip_limit"]
    max_attempts = consts["max_connect_attempts"]

    attacker_ips = p["attacker_ips"]
    attacker_ports = p["attacker_ports"]
    honest_pool = p["honest_pool"]
    honest_inbound_pool = p["honest_inbound_pool"]
    fixed = p["fixed"]
    reserved = p["reserved"]
    rejoin = p["rejoin"]

    events = [{"round": ev["round"], "text": ev["text"]}
              for ev in run["events"]]

    if p["handshake_reject"]:
        attacker_outbound = 0
        attacker_inbound = 0
        events.append({"round": 0, "text": "every attacker handshake rejected (bad signature / wrong network / clock skew): attacker takes no slot"})
    elif not p["attacker_first"] and attacker_ips > 0 and honest_pool > 0:
        # Mature node: honest bootcache entries carry high valence and are
        # tried first, so attacker endpoints stay untried.
        attacker_outbound = 0
        attacker_inbound = min(in_peers, attacker_ips * ip_limit)
        events.append({"round": 0, "text": "honest bootcache entries outrank attacker endpoints: attacker outbound attempts stay untried"})
    else:
        attacker_outbound = min(out_peers, attacker_ips * attacker_ports)
        attacker_inbound = min(in_peers, attacker_ips * ip_limit)

    honest_outbound = min(max(0, out_peers - attacker_outbound), honest_pool)
    honest_inbound = max(0, min(in_peers - attacker_inbound, honest_inbound_pool))
    honest_links = honest_outbound + fixed + reserved

    if honest_links >= 5:
        outcome, reason = "connected", "honest_links_at_least_half_outbound_target"
    elif honest_links >= 1:
        outcome, reason = "degraded", "honest_links_below_half_outbound_target"
    elif attacker_outbound > 0 or honest_inbound > 0:
        outcome, reason = "eclipsed", "no_honest_outbound_link_attacker_controls_outbound_view"
    else:
        outcome, reason = "partitioned", "no_peer_connections_at_all"

    refill = out_peers - honest_outbound
    rounds = max(1, math.ceil(refill / max_attempts)) if refill > 0 else 1
    if rejoin:
        rounds += 1
        events.append({"round": rounds, "text": f"rejoin complete after {rounds} rounds; worst phase was {outcome}"})

    return {
        "label": run["label"],
        "title": run["title"],
        "params": p,
        "outcome": outcome,
        "reason": reason,
        "attacker_outbound": attacker_outbound,
        "attacker_inbound": attacker_inbound,
        "honest_outbound": honest_outbound,
        "honest_inbound": honest_inbound,
        "honest_links": honest_links,
        "rounds": rounds,
        "events": events,
    }


def main():
    if "--help" in sys.argv[1:]:
        print(__doc__.strip())
        print("\nusage: python3 src/overlay_eclipse_model.py [--help]")
        return 0
    sc = load_json(PACK_ROOT / "configs" / "scenarios.json")
    consts = sc["constants"]
    assert sc.get("pinned_commit") == PINNED_COMMIT, "scenarios pinned_commit mismatch"
    assert sc.get("schema_version") == 1, "scenarios schema_version != 1"

    results_scenarios = []
    matrix_rows = []
    totals = {"scenarios": 0, "runs": 0, "connected": 0, "degraded": 0,
              "eclipsed": 0, "partitioned": 0}
    for scenario in sc["scenarios"]:
        runs = [simulate_run(scenario, run, consts)
                for run in scenario["runs"]]
        results_scenarios.append({
            "id": scenario["id"],
            "title": scenario["title"],
            "runs": runs,
        })
        totals["scenarios"] += 1
        for run in runs:
            totals["runs"] += 1
            totals[run["outcome"]] += 1
            matrix_rows.append({
                "scenario": scenario["id"],
                "run": run["label"],
                "attacker_ips": run["params"]["attacker_ips"],
                "attacker_ports": run["params"]["attacker_ports"],
                "fixed": run["params"]["fixed"],
                "reserved": run["params"]["reserved"],
                "outcome": run["outcome"],
                "reason": run["reason"],
                "attacker_outbound": run["attacker_outbound"],
                "honest_outbound": run["honest_outbound"],
                "honest_inbound": run["honest_inbound"],
                "honest_links": run["honest_links"],
                "rounds": run["rounds"],
            })

    threshold_table = []
    for ips, ports in ((1, 1), (1, 5), (1, 10), (2, 10), (5, 2), (5, 10), (11, 1)):
        attacker_outbound = min(consts["out_peers"], ips * ports)
        attacker_inbound = min(consts["in_peers"], ips * consts["ip_limit"])
        honest_outbound = min(max(0, consts["out_peers"] - attacker_outbound), 50)
        honest_inbound = max(0, min(consts["in_peers"] - attacker_inbound, 50))
        honest_links = honest_outbound
        if honest_links >= 5:
            outcome = "connected"
        elif honest_links >= 1:
            outcome = "degraded"
        elif attacker_outbound > 0 or honest_inbound > 0:
            outcome = "eclipsed"
        else:
            outcome = "partitioned"
        threshold_table.append({
            "attacker_ips": ips,
            "attacker_ports": ports,
            "attacker_endpoints": ips * ports,
            "attacker_outbound": attacker_outbound,
            "attacker_inbound": attacker_inbound,
            "honest_outbound": honest_outbound,
            "honest_inbound": honest_inbound,
            "honest_links": honest_links,
            "outcome": outcome,
        })

    limits_table = [
        {"item": "max peers", "value": consts["max_peers"], "unit": "peers"},
        {"item": "outbound peers", "value": consts["out_peers"], "unit": "peers"},
        {"item": "inbound peers", "value": consts["in_peers"], "unit": "peers"},
        {"item": "outbound share", "value": consts["out_percent"], "unit": "percent"},
        {"item": "minimum outbound peers", "value": consts["min_out_count"], "unit": "peers"},
        {"item": "per-IP inbound limit", "value": consts["ip_limit"], "unit": "connections per IP"},
        {"item": "per-IP outbound limit", "value": None, "unit": "none: no cap in code"},
        {"item": "simultaneous connect attempts", "value": consts["max_connect_attempts"], "unit": "attempts"},
        {"item": "connect attempt timeout", "value": consts["connect_timeout_s"], "unit": "s"},
        {"item": "overlay timer tick", "value": consts["overlay_timer_s"], "unit": "s"},
        {"item": "peer ping interval", "value": consts["peer_timer_interval_s"], "unit": "s"},
        {"item": "clock tolerance", "value": consts["clock_tolerance_s"], "unit": "s"},
        {"item": "bootcache size", "value": consts["bootcache_size"], "unit": "entries"},
        {"item": "bootcache prune", "value": consts["bootcache_prune_percent"], "unit": "percent"},
        {"item": "livecache time to live", "value": consts["livecache_ttl_s"], "unit": "s"},
        {"item": "endpoint max hops", "value": consts["max_hops"], "unit": "hops"},
        {"item": "endpoints per broadcast", "value": consts["endpoints_per_broadcast"], "unit": "endpoints"},
        {"item": "endpoints accepted per message", "value": consts["endpoints_max"], "unit": "endpoints"},
        {"item": "redirect endpoints", "value": consts["redirect_endpoints"], "unit": "endpoints"},
        {"item": "redirect IPs into bootcache", "value": consts["max_redirects"], "unit": "addresses"},
        {"item": "endpoint broadcast cadence", "value": consts["seconds_per_message"], "unit": "s"},
        {"item": "diverged eviction", "value": consts["max_diverged_time_s"], "unit": "s"},
        {"item": "unknown eviction", "value": consts["max_unknown_time_s"], "unit": "s"},
        {"item": "send queue drop threshold", "value": consts["sendq_drop"], "unit": "messages"},
        {"item": "send queue target", "value": consts["sendq_target"], "unit": "messages"},
        {"item": "send queue eviction intervals", "value": consts["sendq_intervals"], "unit": "intervals"},
    ]

    results = {
        "pack": "Overlay and Eclipse-Resistance in postfiatd",
        "pinned_commit": PINNED_COMMIT,
        "constants": consts,
        "scenarios": results_scenarios,
        "totals": totals,
        "threshold_table": threshold_table,
        "limits_table": limits_table,
    }
    matrix = {"rows": matrix_rows, "totals": totals}

    outdir = PACK_ROOT / "outputs" / "derived"
    outdir.mkdir(parents=True, exist_ok=True)
    with open(outdir / "overlay-eclipse-results.json", "w") as fh:
        json.dump(results, fh, indent=1, sort_keys=True)
        fh.write("\n")
    with open(outdir / "scenario-matrix.json", "w") as fh:
        json.dump(matrix, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print(f"simulator: {totals['scenarios']} scenarios, {totals['runs']} runs")
    print(f"simulator: connected {totals['connected']}, degraded {totals['degraded']}, "
          f"eclipsed {totals['eclipsed']}, partitioned {totals['partitioned']}")
    print("simulator: wrote outputs/derived/overlay-eclipse-results.json")
    print("simulator: wrote outputs/derived/scenario-matrix.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
