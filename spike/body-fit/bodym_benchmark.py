"""Photo-path benchmark: fit Anny to BodyM silhouettes + entered height/weight, score vs measured truth.

Usage: python3 bodym_benchmark.py [--split testA] [--shard K --of N]
Writes results_bodym/benchmark_<shard>.jsonl. BodyM is non-commercial: internal evaluation only.
"""
from __future__ import annotations

import argparse
import json
import os

from body import Body
from bodym import masks, subjects
from silhouette import fit_silhouettes

COMPARE = {"chest": "chest", "waist": "waist", "waist_navel": "waist", "hip": "hip", "thigh": "thigh", "height": "height"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="testA")
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--of", type=int, default=1)
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    os.makedirs("results_bodym", exist_ok=True)
    subs = subjects(a.split)[: a.limit][a.shard :: a.of]
    path = f"results_bodym/benchmark_{a.shard}.jsonl"
    done = {json.loads(l)["id"] for l in open(path)} if os.path.exists(path) else set()
    body = Body()
    with open(path, "a") as f:
        for s in subs:
            if s["id"] in done:
                continue
            try:
                front, side = masks(s)
                r = fit_silhouettes(body, front, side, s["height_entered"], s["sex"], weight_kg=s["weight"])
                m = r["measured"]
                errors = {ours: round(m[ours] - s["truth"][theirs], 2) for ours, theirs in COMPARE.items()}
                row = dict(id=s["id"], sex=s["sex"], height_entered=s["height_entered"], weight=s["weight"],
                           truth=s["truth"], measured={k: round(v, 2) for k, v in m.items()}, errors=errors,
                           seconds=r["seconds"])
            except Exception as e:
                row = dict(id=s["id"], sex=s["sex"], error=repr(e))
            f.write(json.dumps(row) + "\n")
            f.flush()
            print(s["id"], row.get("errors", row.get("error")), flush=True)


if __name__ == "__main__":
    main()
