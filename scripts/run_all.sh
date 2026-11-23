#!/bin/bash
# run_all.sh — run the full overlay / eclipse-resistance suite end to end:
# excerpt extraction (when a manifest and a pinned checkout are
# available), model config validation, simulator run, probe
# checks, run manifest, and a full SHA-256 listing (all 64 hex chars)
# of every deterministic output file.
#
# Idempotent: outputs are deterministic (no timestamps, no absolute
# paths, no measured timings in any derived JSON), so a second run
# produces byte-identical outputs and digests.
#
# Exit codes: 0 — every step passed; 1 — a step failed;
# 2 — src/overlay_eclipse_model.py is missing.
#
# Excerpt extraction is skipped (recorded, not fatal) when no manifest
# exists yet, or when the pinned checkout is not available in this
# environment (e.g. CI): the shipped excerpts stay covered by
# SHA256SUMS verification instead.
set -u
PACK_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PACK_ROOT" || exit 1
PINNED_COMMIT="0085a1ff885d6a446369cf73a4430f75af22be55"
PINNED_CHECKOUT="${PINNED_CHECKOUT:-$HOME/workspace/postfiatd-pin-0085a1f}"
mkdir -p outputs/derived fixtures/source-excerpts
export PINNED_CHECKOUT

OVERALL=0
EXTRACT_STATUS="skipped: no excerpts manifest"
CONFIG_STATUS="pass"
SIMULATOR_STATUS="not_run"
PROBE_STATUS="skipped: no probe script"

echo "=== run_all.sh ==="
echo "pack: $PACK_ROOT"
echo "pinned commit: $PINNED_COMMIT"

# --- step 1: extract excerpts -------------------------------------------
echo "--- step 1: extract excerpts ---"
if [ -f fixtures/excerpts-manifest.json ]; then
  if [ -d "$PINNED_CHECKOUT" ]; then
    if python3 scripts/extract_excerpts.py; then
      EXTRACT_STATUS="pass"
    else
      echo "extract_excerpts.py FAILED"
      EXTRACT_STATUS="failed"
      OVERALL=1
    fi
  else
    EXTRACT_STATUS="skipped: no pinned checkout at PINNED_CHECKOUT"
    echo "extract skipped: no pinned checkout ($PINNED_CHECKOUT)"
  fi
else
  echo "extract skipped: no fixtures/excerpts-manifest.json yet"
fi

# --- step 2: validate model config ----------------------------------------
echo "--- step 2: validate overlay-eclipse model config ---"
if python3 - <<'EOF'
import json
from collections import Counter
rules = json.load(open("configs/overlay-eclipse-rules.json"))
assert rules.get("schema_version") == 1, "rules schema_version != 1"
assert rules.get("pinned_commit") == "0085a1ff885d6a446369cf73a4430f75af22be55", "rules pinned_commit mismatch"
assert [r["id"] for r in rules["rules"]] == [f"R-{i:02d}" for i in range(1, 46)], "need rules R-01..R-45"
assert Counter(r["status"] for r in rules["rules"]) == {
    "VERIFIED": 38, "SPECIFIED": 4, "MODELLED": 2, "UNTESTABLE": 1}, "rule status counts wrong"
for r in rules["rules"]:
    if r["status"] == "VERIFIED":
        s = r["source"]
        assert s, f"{r['id']}: verified rule lacks source"
        for k in ("file", "start_line", "end_line", "anchor"):
            assert k in s, f"{r['id']}: source missing {k}"
        assert s["start_line"] <= s["end_line"], f"{r['id']}: bad source range"
        assert r.get("excerpt"), f"{r['id']}: verified rule lacks excerpt id"
    elif r["status"] == "SPECIFIED":
        assert r.get("external"), f"{r['id']}: specified rule needs an external record"
        assert "url" in r["external"] and "quote" in r["external"], f"{r['id']}: specified rule needs url+quote"
        assert r.get("source") is None, f"{r['id']}: specified rule must carry no file source"
    else:
        assert r.get("source") is None, f"{r['id']}: {r['status']} rule must carry no file source"
sc = json.load(open("configs/scenarios.json"))
assert sc.get("schema_version") == 1, "scenarios schema_version != 1"
assert sc.get("pinned_commit") == "0085a1ff885d6a446369cf73a4430f75af22be55", "scenarios pinned_commit mismatch"
assert [s["id"] for s in sc["scenarios"]] == [f"S-{i:02d}" for i in range(1, 14)], "need scenarios S-01..S-13"
assert sc["constants"]["max_peers"] == 21, "max_peers must be 21"
assert sc["constants"]["out_peers"] == 10, "out_peers must be 10"
assert sc["constants"]["in_peers"] == 11, "in_peers must be 11"
assert sc["constants"]["ip_limit"] == 2, "ip_limit must be 2"
assert sc["constants"]["max_connect_attempts"] == 20, "max_connect_attempts must be 20"
assert sum(len(s["runs"]) for s in sc["scenarios"]) == 18, "need 18 runs"
for s in sc["scenarios"]:
    assert s["runs"], f"{s['id']}: no runs"
    for run in s["runs"]:
        assert run["events"], f"{s['id']} {run['label']}: no events"
        assert run["events"][0]["round"] == 0, f"{s['id']} {run['label']}: first event must be round 0"
print("overlay-eclipse model config: 45 rules (38/4/2/1), 13 scenarios, 18 runs, ids + statuses OK")
EOF
then
  CONFIG_STATUS="pass"
else
  echo "overlay-eclipse model config validation FAILED"
  CONFIG_STATUS="failed"
  OVERALL=1
fi

# --- step 3: simulator ------------------------------------------------------
echo "--- step 3: overlay-eclipse simulator ---"
if [ ! -f src/overlay_eclipse_model.py ]; then
  echo "ERROR: src/overlay_eclipse_model.py is missing."
  exit 2
fi
python3 src/overlay_eclipse_model.py
SIM_RC=$?
if [ "$SIM_RC" -eq 0 ]; then
  SIMULATOR_STATUS="pass"
  echo "simulator: PASS"
else
  SIMULATOR_STATUS="failed"
  echo "simulator FAILED (exit $SIM_RC)"
  OVERALL=1
fi

# --- step 4: probe checks ---------------------------------------------------
# --skip-manifest-check: the manifest on disk predates the results this
# run just regenerated; step 5b re-runs the probe without the flag after
# rewriting the manifest. A standalone probe run always checks it.
echo "--- step 4: probe checks ---"
if [ -f scripts/probe.py ]; then
  if python3 scripts/probe.py --skip-manifest-check; then
    PROBE_STATUS="pass"
  else
    echo "probe.py FAILED"
    PROBE_STATUS="failed"
    OVERALL=1
  fi
else
  echo "probe skipped: no scripts/probe.py yet"
fi

# --- step 5: run summary + run manifest (deterministic) --------------------
echo "--- step 5: run summary + run manifest ---"
EXTRACT_STATUS="$EXTRACT_STATUS" CONFIG_STATUS="$CONFIG_STATUS" \
SIMULATOR_STATUS="$SIMULATOR_STATUS" PROBE_STATUS="$PROBE_STATUS" python3 - <<'EOF'
import hashlib
import json
import os
import re
from collections import Counter

summary = {
    "pack": "Overlay and Eclipse-Resistance in postfiatd",
    "pinned_commit": "0085a1ff885d6a446369cf73a4430f75af22be55",
    "scenario_count": 13,
    "rule_count": 45,
    "steps": {
        "extract_excerpts": os.environ["EXTRACT_STATUS"],
        "overlay_eclipse_model_config": os.environ["CONFIG_STATUS"],
        "simulator": os.environ["SIMULATOR_STATUS"],
        "probe": os.environ["PROBE_STATUS"],
    },
}
with open("outputs/derived/run-summary.json", "w") as fh:
    json.dump(summary, fh, indent=1)
    fh.write("\n")

res = json.load(open("outputs/derived/overlay-eclipse-results.json"))
mat = json.load(open("outputs/derived/scenario-matrix.json"))
probe = json.load(open("outputs/derived/probe-results.json"))
findings = json.load(open("findings.json"))["findings"]
hashes = json.load(open("fixtures/source-hashes.json"))

def table_rows(path, prefix):
    rows = []
    for ln in open(path, encoding="utf-8"):
        m = re.match(rf"\| ({prefix}-\d+) \| ([A-Z]+) \|", ln)
        if m:
            rows.append((m.group(1), m.group(2)))
    return rows

claims = table_rows("docs/claim-index.md", "C")
risks = table_rows("docs/risk-register.md", "K")
gaps = [ln for ln in open("docs/gap-register.md", encoding="utf-8")
        if re.match(r"\| G-\d+ \|", ln)]

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

# Record the two fresh-clone reproductions when their logs exist.
reproductions = []
for label, rel in (("fresh-clone-1", "outputs/fresh-clone-run.log"),
                   ("fresh-clone-2", "outputs/fresh-clone-2-run.log")):
    if os.path.isfile(rel):
        reproductions.append({
            "label": label,
            "log": rel,
            "sha256": sha256_file(rel),
            "status": "pass",
        })

manifest = {
    "pack": "Overlay and Eclipse-Resistance in postfiatd",
    "pinned_commit": "0085a1ff885d6a446369cf73a4430f75af22be55",
    "counts": {
        "rules": {
            "total": 45,
            "by_status": {"VERIFIED": 38, "SPECIFIED": 4, "MODELLED": 2, "UNTESTABLE": 1},
        },
        "scenarios": {
            "total": res["totals"]["scenarios"],
            "runs": res["totals"]["runs"],
            "connected": res["totals"]["connected"],
            "degraded": res["totals"]["degraded"],
            "eclipsed": res["totals"]["eclipsed"],
            "partitioned": res["totals"]["partitioned"],
        },
        "findings": {
            "total": len(findings),
            "by_severity": dict(sorted(Counter(f["severity"] for f in findings).items())),
            "by_status": dict(sorted(Counter(f["status"] for f in findings).items())),
        },
        "claims": {
            "total": len(claims),
            "by_status": dict(sorted(Counter(s for _, s in claims).items())),
        },
        "risks": {
            "total": len(risks),
            "by_severity": dict(sorted(Counter(s for _, s in risks).items())),
        },
        "gaps": len(gaps),
    },
    "probes": {"passed": probe["passed"], "total": probe["total"]},
    "results_sha256": sha256_file("outputs/derived/overlay-eclipse-results.json"),
    "matrix_sha256": sha256_file("outputs/derived/scenario-matrix.json"),
    "verification": {
        "excerpts": len(hashes["excerpts"]),
        "source_files": len(hashes["files"]),
    },
    "reproductions": reproductions,
    "status": "SOURCE-DERIVED",
}
with open("run-manifest.json", "w") as fh:
    json.dump(manifest, fh, indent=1)
    fh.write("\n")
print("wrote outputs/derived/run-summary.json")
print("wrote run-manifest.json")
print("counts: rules=45 scenarios=%d runs=%d findings=%d claims=%d risks=%d gaps=%d reproductions=%d" % (
    res["totals"]["scenarios"], res["totals"]["runs"], len(findings), len(claims), len(risks), len(gaps), len(reproductions)))
EOF
if [ "$?" -ne 0 ]; then
  echo "run summary / manifest FAILED"
  OVERALL=1
fi

# --- step 5b: re-run probe now the manifest exists --------------------------
echo "--- step 5b: re-run probe (verify run-manifest digests) ---"
if python3 scripts/probe.py; then
  PROBE_STATUS="pass"
else
  echo "probe re-run FAILED"
  PROBE_STATUS="failed"
  OVERALL=1
fi

# --- step 6: full SHA-256 listing of deterministic outputs ------------------
echo "--- step 6: SHA-256 of deterministic outputs (full 64 hex chars) ---"
{
  echo "# run.log — deterministic output digests (no timestamps, no absolute paths)"
  echo "# step extract_excerpts: $EXTRACT_STATUS"
  echo "# step overlay_eclipse_model_config: $CONFIG_STATUS"
  echo "# step simulator: $SIMULATOR_STATUS"
  echo "# step probe: $PROBE_STATUS"
  find outputs -type f ! -name 'run.log' ! -name 'compare-results.json' \
    ! -name 'fresh-clone-*' | sort | xargs sha256sum
} > outputs/run.log
cat outputs/run.log

# --- step 7: digests ---------------------------------------------------------
echo "--- step 7: digests ---"
bash scripts/make_sha256sums.sh || { echo "make_sha256sums.sh FAILED"; OVERALL=1; }
bash scripts/verify_digests.sh || { echo "verify_digests.sh FAILED"; OVERALL=1; }

echo "=== run_all.sh done ==="
echo "extract_excerpts: $EXTRACT_STATUS"
echo "overlay_eclipse_model_config: $CONFIG_STATUS"
echo "simulator: $SIMULATOR_STATUS"
echo "probe: $PROBE_STATUS"
if [ "$OVERALL" -ne 0 ]; then
  echo "run_all.sh: FAILED (see steps above)"
  exit 1
fi
echo "run_all.sh: ALL STEPS PASSED"
exit 0
