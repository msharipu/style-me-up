"""Fit every synthetic subject and report error per zone against the 2 cm gate.

Usage: python3 benchmark.py [--shard K --of N]   (run N shards in parallel, then merge)
Writes results/benchmark_<shard>.jsonl, one line per subject.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from body import Body
from fit import fit
from subjects import make_subjects

ZONES = ["height", "chest", "waist", "hip", "thigh", "inseam", "shoulder", "arm", "weight"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--of", type=int, default=1)
    args = ap.parse_args()
    os.makedirs("results", exist_ok=True)
    subjects = make_subjects()[args.shard :: args.of]
    body = Body()
    path = f"results/benchmark_{args.shard}.jsonl"
    done = set()
    if os.path.exists(path):
        done = {json.loads(l)["id"] for l in open(path)}
    with open(path, "a") as f:
        for s in subjects:
            if s["id"] in done:
                continue
            target = {z: s[z] for z in ZONES}
            try:
                r = fit(body, target, s["sex"], s["age"])
                row = dict(id=s["id"], sex=s["sex"], age=s["age"], target=target, measured=r.measured,
                           errors=r.errors, seconds=r.seconds, pheno=r.pheno, local=r.local)
            except Exception as e:  # keep going; a failed fit is itself a result
                row = dict(id=s["id"], sex=s["sex"], target=target, error=repr(e))
            f.write(json.dumps(row) + "\n")
            f.flush()
            print(s["id"], row.get("errors", row.get("error")), flush=True)


if __name__ == "__main__":
    sys.exit(main())
