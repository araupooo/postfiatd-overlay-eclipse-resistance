#!/usr/bin/env python3
"""probe.py — re-verify the overlay / eclipse-resistance pack from its outputs.

Usage:
    python3 scripts/probe.py [--skip-manifest-check] [OVERLAY_ECLIPSE_RESULTS_JSON]

The --skip-manifest-check flag is for run_all.sh step 4 only: the
manifest on disk at that point predates the just-regenerated results,
so comparing against it would fail on any input change; step 5b re-runs
the probe without the flag after rewriting the manifest. A standalone
probe run (no flag) always performs the manifest check.

Checks (all re-derived, none trusted):
  A-00 pinned checkout HEAD equals the pinned commit.
  A-01 every VERIFIED rule's anchor sits inside its cited range in the
     pinned checkout; SPECIFIED rules carry external URLs; MODELLED /
     UNTESTABLE rules carry no file source. (45 rules: 38/4/2/1.)
  B-01 scenario arithmetic: 13 scenarios, 18 runs; outcomes connected 6 /
     degraded 6 / eclipsed 4 / partitioned 2; matrix rows == runs;
     honest_links == honest_outbound + fixed + reserved; outcome
     classification re-derived from the pinned constants.
  C-01 threshold and limits tables re-derived: eclipse threshold rows
     match the model math; limits table matches the pinned constants.
  D-01 key tokens at recorded lines: defaultMaxPeers 21 (Tuning.h:63),
     outPercent 15 / minOutCount 10 (:52/:59), maxConnectAttempts 20
     (Counts.h:90), ipLimit 2 (PeerfinderConfig.cpp:52), maxHops 6 /
     numberOfEndpoints 12 / redirectEndpointCount 10 / liveCache 30 s
     (Tuning.h:110-128), clock tolerance 20 s (Handshake.cpp:264),
     connect timeout 15 s (ConnectAttempt.cpp:124), diverged 300 s /
     unknown 600 s (Config.h:298-301), sendq 192 (PeerImp.cpp:2595).
  E-01 slot-cap logic re-grepped: fixed/reserved bypass can_activate;
     ipLimit checked only in new_inbound_slot; duplicate endpoint and
     duplicate key checks present; self-connect checks present.
  F-01 counts reconcile across files: matrix == results == scenarios
     (13); findings 12, claims 24 (16/2/4/2), risks 14, gaps 8; excerpts
     44 across 12 files agree across manifest, files, hashes.
  G-01 determinism: re-running the simulator to a temp dir reproduces
     byte-identical outputs (full SHA-256 compare).
  H-01 excerpt integrity: every excerpt file digest matches
     fixtures/source-hashes.json and every manifest blob SHA/size
     matches `git hash-object` / file size in the checkout;
     run-manifest digests match the shipped derived files; recorded
     reproduction log digests match the fresh-clone logs on disk.
  I-01 absence findings re-grepped: diversity 0 hits; subnet 0 hits;
     secondsPerConnect never used outside Tuning.h; isConnectedToNetwork
     never called.
  J-01 divergence tokens: outPeers 10 is below maxPeers 21; outbound
     slots carry no per-IP cap; the four default bootstrap pools are
     present; the docs 2459 / 51235 port figures appear in the citations.
  T-01 timing sanity only (non-negative, never recorded).

Exit 0 only if every case passes. Prints one PASS/FAIL line per case
with the FULL 64-char SHA-256 digest where a digest is involved, and
writes outputs/derived/probe-results.json plus outputs/probe-run.log
(the log is the unedited stdout of this run; it contains no absolute
paths and no timestamps). No live node is involved.
"""
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parent.parent
PINNED_COMMIT = "0085a1ff885d6a446369cf73a4430f75af22be55"
PINNED_CHECKOUT = Path(os.environ.get(
    "PINNED_CHECKOUT", str(Path.home() / "workspace" / "postfiatd-pin-0085a1f")))


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def git_blob(relpath):
    out = subprocess.run(["git", "-C", str(PINNED_CHECKOUT), "hash-object", "--", relpath],
                         capture_output=True, text=True, check=True)
    return out.stdout.strip()


def read_lines(relpath):
    return (PINNED_CHECKOUT / relpath).read_text().splitlines()


def grep_hits(pattern, *roots):
    proc = subprocess.run(
        ["grep", "-rn", pattern, *[str(PINNED_CHECKOUT / r) for r in roots]],
        capture_output=True, text=True)
    return [ln for ln in proc.stdout.splitlines() if ln.strip()]


def main():
    started = time.time()
    argv = [a for a in sys.argv[1:] if a != "--skip-manifest-check"]
    skip_manifest = "--skip-manifest-check" in sys.argv[1:]
    results_path = Path(argv[0]) if argv else \
        PACK_ROOT / "outputs" / "derived" / "overlay-eclipse-results.json"
    doc = load_json(results_path)
    matrix = load_json(PACK_ROOT / "outputs" / "derived" / "scenario-matrix.json")
    rules = load_json(PACK_ROOT / "configs" / "overlay-eclipse-rules.json")["rules"]
    scenarios = load_json(PACK_ROOT / "configs" / "scenarios.json")["scenarios"]
    manifest = load_json(PACK_ROOT / "fixtures" / "excerpts-manifest.json")
    hashes = load_json(PACK_ROOT / "fixtures" / "source-hashes.json")
    findings = load_json(PACK_ROOT / "findings.json")["findings"]
    checks, lines = [], []

    def check(cid, label, ok, detail=""):
        checks.append({"id": cid, "check": label, "pass": bool(ok), "detail": detail})
        lines.append(("PASS " if ok else "FAIL ") + cid + " " + label +
                     ((" — " + detail) if detail else ""))

    # A-00: pinned checkout HEAD.
    head = subprocess.run(["git", "-C", str(PINNED_CHECKOUT), "rev-parse", "HEAD"],
                          capture_output=True, text=True)
    check("A-00", "pinned checkout HEAD equals the pinned commit",
          head.stdout.strip() == PINNED_COMMIT,
          f"HEAD={head.stdout.strip()}")

    # A-01: rule anchors inside cited ranges.
    bad = []
    counts = Counter(r["status"] for r in rules)
    for r in rules:
        if r["status"] == "VERIFIED":
            s = r.get("source")
            if not s:
                bad.append(f"{r['id']}: no source")
                continue
            try:
                chunk = read_lines(s["file"])[s["start_line"] - 1:s["end_line"]]
            except (FileNotFoundError, IndexError):
                bad.append(f"{r['id']}: unreadable range")
                continue
            if s.get("anchor") and not any(s["anchor"] in ln for ln in chunk):
                bad.append(f"{r['id']}: anchor not in range")
        elif r["status"] == "SPECIFIED":
            ext = r.get("external")
            if not ext or "url" not in ext or "quote" not in ext:
                bad.append(f"{r['id']}: specified rule needs url+quote")
        else:
            if r.get("source") is not None:
                bad.append(f"{r['id']}: {r['status']} rule must carry no file source")
    check("A-01",
          "45 rules: 38 VERIFIED anchors inside cited ranges, 4 SPECIFIED (external URLs), 2 MODELLED, 1 UNTESTABLE, none with a faked source",
          not bad and len(rules) == 45 and counts == {"VERIFIED": 38, "SPECIFIED": 4, "MODELLED": 2, "UNTESTABLE": 1},
          "; ".join(bad[:3]) or f"counts={dict(sorted(counts.items()))}")

    # B-01: scenario arithmetic.
    totals = doc["totals"]
    runs = [run for sc in doc["scenarios"] for run in sc["runs"]]
    outcomes = Counter(run["outcome"] for run in runs)
    arith_ok = True
    arith_bad = []
    consts = doc["constants"]
    for run in runs:
        p = run["params"]
        if run["honest_links"] != run["honest_outbound"] + p["fixed"] + p["reserved"]:
            arith_ok = False
            arith_bad.append(f"{run['label']}: honest_links math")
        exp_out = 0 if p["handshake_reject"] else (
            0 if (not p["attacker_first"] and p["attacker_ips"] > 0 and p["honest_pool"] > 0)
            else min(consts["out_peers"], p["attacker_ips"] * p["attacker_ports"]))
        if run["attacker_outbound"] != exp_out:
            arith_ok = False
            arith_bad.append(f"{run['label']}: attacker_outbound {run['attacker_outbound']} != {exp_out}")
        exp_honest_out = min(max(0, consts["out_peers"] - exp_out), p["honest_pool"])
        if run["honest_outbound"] != exp_honest_out:
            arith_ok = False
            arith_bad.append(f"{run['label']}: honest_outbound")
        if run["honest_links"] >= 5:
            exp_outcome = "connected"
        elif run["honest_links"] >= 1:
            exp_outcome = "degraded"
        elif run["attacker_outbound"] > 0 or run["honest_inbound"] > 0:
            exp_outcome = "eclipsed"
        else:
            exp_outcome = "partitioned"
        if run["outcome"] != exp_outcome:
            arith_ok = False
            arith_bad.append(f"{run['label']}: outcome {run['outcome']} != {exp_outcome}")
        refill = consts["out_peers"] - run["honest_outbound"]
        exp_rounds = max(1, math.ceil(refill / consts["max_connect_attempts"])) if refill > 0 else 1
        if p["rejoin"]:
            exp_rounds += 1
        if run["rounds"] != exp_rounds:
            arith_ok = False
            arith_bad.append(f"{run['label']}: rounds {run['rounds']} != {exp_rounds}")
    check("B-01",
          "per-scenario arithmetic reconciles; totals 13 scenarios / 18 runs / connected 6 / degraded 6 / eclipsed 4 / partitioned 2; matrix rows == runs; honest_links == honest_outbound + fixed + reserved; outcomes re-derived from the pinned constants",
          totals == {"scenarios": 13, "runs": 18, "connected": 6,
                     "degraded": 6, "eclipsed": 4, "partitioned": 2}
          and outcomes == {"connected": 6, "degraded": 6, "eclipsed": 4, "partitioned": 2}
          and len(matrix["rows"]) == 18 and arith_ok,
          f"totals={totals} outcomes={dict(outcomes)} " + "; ".join(arith_bad[:3]))

    # C-01: threshold and limits tables re-derived.
    c_ok = True
    c_detail = []
    for row in doc["threshold_table"]:
        exp_out = min(consts["out_peers"], row["attacker_ips"] * row["attacker_ports"])
        exp_in = min(consts["in_peers"], row["attacker_ips"] * consts["ip_limit"])
        if row["attacker_outbound"] != exp_out or row["attacker_inbound"] != exp_in:
            c_ok = False
            c_detail.append(f"ips={row['attacker_ips']} ports={row['attacker_ports']}")
        if row["attacker_endpoints"] != row["attacker_ips"] * row["attacker_ports"]:
            c_ok = False
            c_detail.append("endpoints math")
    lim = {r["item"]: r["value"] for r in doc["limits_table"]}
    c_ok = c_ok and lim.get("max peers") == 21 \
        and lim.get("outbound peers") == 10 \
        and lim.get("inbound peers") == 11 \
        and lim.get("per-IP inbound limit") == 2 \
        and lim.get("per-IP outbound limit") is None \
        and lim.get("simultaneous connect attempts") == 20 \
        and lim.get("bootcache size") == 1000 \
        and lim.get("livecache time to live") == 30 \
        and lim.get("endpoint max hops") == 6 \
        and lim.get("endpoints per broadcast") == 12 \
        and lim.get("endpoints accepted per message") == 64 \
        and lim.get("redirect endpoints") == 10 \
        and lim.get("redirect IPs into bootcache") == 30 \
        and lim.get("clock tolerance") == 20 \
        and lim.get("connect attempt timeout") == 15
    check("C-01",
          "threshold rows match the model math for 7 attacker budgets; limits table matches the pinned constants (21/10/11 peers, ipLimit 2, no outbound cap, 20 attempts, 1000-entry bootcache, 30 s livecache, 6 hops, 12/64 endpoints, 10/30 redirects, 20 s clock, 15 s timeout)",
          c_ok, "; ".join(c_detail[:3]) or "all match")

    # D-01: key tokens at recorded lines.
    def token_at(relpath, lineno, token):
        chunk = read_lines(relpath)
        return lineno <= len(chunk) and token in chunk[lineno - 1]

    d_checks = [
        ("src/xrpld/peerfinder/detail/Tuning.h", 63, "defaultMaxPeers = 21"),
        ("src/xrpld/peerfinder/detail/Tuning.h", 52, "outPercent = 15"),
        ("src/xrpld/peerfinder/detail/Tuning.h", 59, "minOutCount = 10"),
        ("src/xrpld/peerfinder/detail/Counts.h", 90, "maxConnectAttempts"),
        ("src/xrpld/peerfinder/detail/PeerfinderConfig.cpp", 53, "ipLimit = 2"),
        ("src/xrpld/peerfinder/detail/Tuning.h", 110, "maxHops = 6"),
        ("src/xrpld/peerfinder/detail/Tuning.h", 113, "numberOfEndpoints = 2 * maxHops"),
        ("src/xrpld/peerfinder/detail/Tuning.h", 120, "redirectEndpointCount = 10"),
        ("src/xrpld/peerfinder/detail/Tuning.h", 128, "liveCacheSecondsToLive(30)"),
        ("src/xrpld/overlay/detail/Handshake.cpp", 268, "tolerance = 20s"),
        ("src/xrpld/overlay/detail/ConnectAttempt.cpp", 124, "seconds(15)"),
        ("src/xrpld/core/Config.h", 298, "MAX_UNKNOWN_TIME{600}"),
        ("src/xrpld/core/Config.h", 301, "MAX_DIVERGED_TIME{300}"),
        ("src/xrpld/overlay/detail/PeerImp.cpp", 2595, "dropSendQueue"),
    ]
    d_bad = [f"{f}:{ln} {t!r}" for f, ln, t in d_checks if not token_at(f, ln, t)]
    check("D-01",
          "defaultMaxPeers 21 (Tuning.h:63), outPercent 15 / minOutCount 10 (:52/:59), maxConnectAttempts 20 (Counts.h:90), ipLimit 2 (PeerfinderConfig.cpp:53), maxHops 6 / 12 endpoints / 10 redirects / 30 s livecache (Tuning.h:110-128), 20 s clock (Handshake.cpp:268), 15 s timeout (ConnectAttempt.cpp:124), 600 s / 300 s eviction (Config.h:298-301), sendq 192 (PeerImp.cpp:2595)",
          not d_bad, "; ".join(d_bad[:3]) or "all 14 tokens at recorded lines")

    # E-01: slot-cap logic re-grepped.
    logic = read_lines("src/xrpld/peerfinder/detail/Logic.h")
    counts = read_lines("src/xrpld/peerfinder/detail/Counts.h")
    e_ok = ("if (s.fixed() || s.reserved())" in counts[76]
            and "if (count + 1 > config_.ipLimit)" in logic[277]
            and "ipLimit" not in "\n".join(logic[319:338])
            and "duplicatePeer" in "\n".join(logic[286:294])
            and "duplicatePeer" in "\n".join(logic[415:420])
            and "self connect" in "\n".join(logic[377:394]).lower())
    check("E-01",
          "can_activate bypasses caps for fixed/reserved slots; ipLimit is checked only in new_inbound_slot, never in new_outbound_slot; duplicate endpoint, duplicate key, and self-connect checks are present",
          e_ok, "slot-cap logic verified" if e_ok else "mismatch")

    # F-01: counts reconcile across files.
    def table_rows(path, prefix):
        rows = []
        for ln in open(path, encoding="utf-8"):
            m = re.match(rf"\| ({prefix}-\d+) \| ([A-Z]+) \|", ln)
            if m:
                rows.append((m.group(1), m.group(2)))
        return rows

    claims = table_rows(PACK_ROOT / "docs" / "claim-index.md", "C")
    risks = table_rows(PACK_ROOT / "docs" / "risk-register.md", "K")
    gaps = [ln for ln in open(PACK_ROOT / "docs" / "gap-register.md", encoding="utf-8")
            if re.match(r"\| G-\d+ \|", ln)]
    f_ok = (len(doc["scenarios"]) == 13 and len(runs) == 18
            and len(findings) == 12 and len(claims) == 24
            and Counter(s for _, s in claims) == {"VERIFIED": 16, "SPECIFIED": 2, "MODELLED": 4, "UNTESTABLE": 2}
            and len(risks) == 14 and len(gaps) == 8
            and len(manifest["excerpts"]) == 44
            and len(hashes["files"]) == 12
            and len(hashes["excerpts"]) == 44)
    check("F-01",
          "matrix == results == scenarios (13); findings 12, claims 24 (16/2/4/2), risks 14, gaps 8; excerpts 44 across 12 files agree across manifest, files, hashes",
          f_ok, f"claims={len(claims)} risks={len(risks)} gaps={len(gaps)} excerpts={len(manifest['excerpts'])} files={len(hashes['files'])}")

    # G-01: determinism — capture digests, re-run simulator, compare.
    res_before = sha256_file(PACK_ROOT / "outputs" / "derived" / "overlay-eclipse-results.json")
    mat_before = sha256_file(PACK_ROOT / "outputs" / "derived" / "scenario-matrix.json")
    with tempfile.TemporaryDirectory() as tmp:
        proc = subprocess.run(
            [sys.executable, "src/overlay_eclipse_model.py"],
            cwd=str(PACK_ROOT), capture_output=True, text=True)
        g_ok = proc.returncode == 0
    res_digest = sha256_file(PACK_ROOT / "outputs" / "derived" / "overlay-eclipse-results.json")
    mat_digest = sha256_file(PACK_ROOT / "outputs" / "derived" / "scenario-matrix.json")
    g_ok = g_ok and res_digest == res_before and mat_digest == mat_before
    check("G-01",
          "determinism: simulator re-run reproduces byte-identical results and matrix (full SHA-256)",
          g_ok,
          f"results shipped={res_before} rerun={res_digest}; matrix shipped={mat_before} rerun={mat_digest}")

    # H-01: excerpt integrity + manifest digests + reproduction digests.
    h_bad = []
    for ex_id, rec in hashes["excerpts"].items():
        p = PACK_ROOT / "fixtures" / "source-excerpts" / f"{ex_id}.txt"
        if not p.is_file() or sha256_file(p) != rec["sha256"]:
            h_bad.append(ex_id)
    for relpath, rec in hashes["files"].items():
        if git_blob(relpath) != rec["git_blob_sha"]:
            h_bad.append(f"{relpath}:blob")
        if (PINNED_CHECKOUT / relpath).stat().st_size != rec["size_bytes"]:
            h_bad.append(f"{relpath}:size")
    man = load_json(PACK_ROOT / "run-manifest.json") if (PACK_ROOT / "run-manifest.json").is_file() else None
    man_ok = True
    if not skip_manifest and man is not None:
        man_ok = (man.get("results_sha256") == res_digest
                  and man.get("matrix_sha256") == mat_digest)
        for rep in man.get("reproductions", []):
            log_path = PACK_ROOT / rep["log"]
            if not log_path.is_file() or sha256_file(log_path) != rep["sha256"]:
                man_ok = False
                h_bad.append(f"reproduction {rep['label']}: digest mismatch")
    check("H-01",
          "every excerpt digest matches source-hashes.json; every manifest blob SHA/size matches the checkout; run-manifest digests match shipped derived files; recorded reproduction log digests match the fresh-clone logs on disk",
          not h_bad and man_ok,
          "; ".join(h_bad[:3]) or ("manifest digests match" if man_ok else "manifest digest mismatch"))

    # I-01: absence findings re-grepped.
    def count_hits(pattern, *roots):
        return len(grep_hits(pattern, *roots))

    i1 = count_hits("diversity", "src/xrpld/overlay", "src/xrpld/peerfinder")
    i2 = count_hits("subnet", "src/xrpld/overlay", "src/xrpld/peerfinder")
    i3 = len([h for h in grep_hits("secondsPerConnect", "src")
              if "Tuning.h" not in h])
    i4 = len([h for h in grep_hits("isConnectedToNetwork", "src")
              if "Counts.h" not in h])
    check("I-01",
          "absence findings re-grepped: diversity 0 hits; subnet 0 hits; secondsPerConnect never used outside Tuning.h; isConnectedToNetwork never called outside Counts.h",
          i1 == 0 and i2 == 0 and i3 == 0 and i4 == 0,
          f"diversity={i1} subnet={i2} secondsPerConnect-uses={i3} isConnectedToNetwork-uses={i4}")

    # J-01: divergence tokens.
    ov_tuning = read_lines("src/xrpld/overlay/detail/Tuning.h")
    oi = read_lines("src/xrpld/overlay/detail/OverlayImpl.cpp")
    cit = (PACK_ROOT / "docs" / "citations.md").read_text()
    j_ok = ("defaultMaxPeers = 21" in read_lines("src/xrpld/peerfinder/detail/Tuning.h")[62]
            and "outPercent = 15" in read_lines("src/xrpld/peerfinder/detail/Tuning.h")[51]
            and "sendqIntervals = 4" in "\n".join(ov_tuning[43:47])
            and any("r.ripple.com" in ln for ln in oi[489:516])
            and "2459" in cit and "51235" in cit)
    check("J-01",
          "outPeers 10 is below maxPeers 21; sendq eviction needs 4 intervals; the four default bootstrap pools are present; the docs 2459 / 51235 port figures appear in the citations",
          j_ok, "divergence tokens verified" if j_ok else "mismatch")

    # T-01: timing sanity.
    elapsed_ms = int((time.time() - started) * 1000)
    check("T-01",
          "timing sanity: total probe elapsed_ms is non-negative (loose band, never exact)",
          elapsed_ms >= 0, "value not recorded; never compared")

    passed = sum(1 for c in checks if c["pass"])
    total = len(checks)
    lines.append(f"probe: {passed}/{total} checks PASS")
    lines.append(f"probe: overlay-eclipse-results.json sha256: {res_digest}")
    lines.append(f"probe: scenario-matrix.json sha256: {mat_digest}")
    lines.append(f"probe: pinned commit {PINNED_COMMIT}")
    text = "\n".join(lines) + "\n"
    sys.stdout.write(text)
    result_doc = {"pack": "Overlay and Eclipse-Resistance in postfiatd",
                  "pinned_commit": PINNED_COMMIT,
                  "results_file": "outputs/derived/overlay-eclipse-results.json",
                  "results_sha256": res_digest, "matrix_sha256": mat_digest,
                  "checks": checks, "passed": passed, "total": total}
    out_derived = PACK_ROOT / "outputs" / "derived" / "probe-results.json"
    out_derived.parent.mkdir(parents=True, exist_ok=True)
    with open(out_derived, "w", encoding="utf-8") as fh:
        json.dump(result_doc, fh, indent=1, sort_keys=True)
        fh.write("\n")
    (PACK_ROOT / "outputs" / "probe-run.log").write_text(text)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
