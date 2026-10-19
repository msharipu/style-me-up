"""Summarise benchmark results: error per zone against the 2 cm gate.

Writes results/summary.json and prints a table.
"""
from __future__ import annotations

import glob
import json

import numpy as np

ZONES = ["chest", "waist", "hip", "thigh", "inseam", "shoulder", "arm", "height", "weight"]
GATE = ["chest", "waist", "hip"]


def main():
    rows = [json.loads(l) for p in sorted(glob.glob("results/benchmark_*.jsonl")) for l in open(p)]
    ok = [r for r in rows if "errors" in r]
    failed = [r for r in rows if "error" in r]
    summary = {"subjects": len(rows), "fitted": len(ok), "failed": [r["id"] for r in failed], "zones": {}, "by_sex": {}}

    def stats(errs):
        a = np.abs(np.array(errs))
        return dict(mean_abs=round(float(a.mean()), 2), p90_abs=round(float(np.percentile(a, 90)), 2),
                    max_abs=round(float(a.max()), 2), within_2cm=round(float((a <= 2).mean()), 3),
                    bias=round(float(np.mean(errs)), 2))

    for z in ZONES:
        errs = [r["errors"][z] for r in ok if z in r["errors"]]
        if errs:
            summary["zones"][z] = stats(errs)
    for sex in ("male", "female"):
        g = [r for r in ok if r["sex"] == sex]
        summary["by_sex"][sex] = {z: stats([r["errors"][z] for r in g]) for z in GATE if g}
    all_gate = [all(abs(r["errors"][z]) <= 2 for z in GATE) for r in ok]
    summary["subjects_passing_gate"] = round(float(np.mean(all_gate)), 3) if ok else None
    summary["worst"] = sorted(
        ({"id": r["id"], **{z: r["errors"][z] for z in GATE}} for r in ok),
        key=lambda d: -max(abs(d[z]) for z in GATE),
    )[:5]
    summary["seconds_per_fit"] = round(float(np.mean([r["seconds"] for r in ok])), 1) if ok else None
    json.dump(summary, open("results/summary.json", "w"), indent=2)

    print(f"{len(ok)}/{len(rows)} fitted; {summary['subjects_passing_gate']:.0%} pass the 2 cm gate on chest, waist and hip")
    print(f"{'zone':9s} {'mean|e|':>8s} {'p90|e|':>8s} {'max|e|':>8s} {'≤2 cm':>7s} {'bias':>7s}")
    for z, s in summary["zones"].items():
        print(f"{z:9s} {s['mean_abs']:8.2f} {s['p90_abs']:8.2f} {s['max_abs']:8.2f} {s['within_2cm']:7.0%} {s['bias']:+7.2f}")
    print("worst:", summary["worst"])


if __name__ == "__main__":
    main()
