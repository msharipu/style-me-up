"""Real test subjects from ANSUR II (US Army anthropometric survey, 2012; public domain).

Source CSV: https://calmcode.io/static/data/ergonomics.csv (6,068 people; mm, weight in 0.1 kg).
We sample a balanced set: per sex, half from the survey's Asian group (DODRace 4), half from
everyone else, so the test covers both SEA-like proportions and a wide range of builds.

ANSUR definitions mapped to ours:
  stature → height · chestcircumference (nipple level) → chest · waistcircumference (navel level)
  → waist_navel · buttockcircumference (max buttock protrusion) → hip · thighcircumference
  (gluteal furrow) → thigh · crotchheight → inseam · weightkg → weight.
Shoulder and arm are left out: ANSUR's caliper breadths don't match our tape definitions.
"""
from __future__ import annotations

import csv
import os

import numpy as np

DEFAULT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "ansur_ii.csv")


def load(path: str = DEFAULT_PATH) -> list[dict]:
    with open(path, encoding="utf-8", errors="replace") as f:
        return list(csv.DictReader(f))


def to_subject(row: dict, sid: str) -> dict:
    mm = lambda k: round(float(row[k]) / 10, 1)  # noqa: E731
    return dict(
        id=sid,
        source_id=row["subjectid"],
        sex="male" if row["gender"] == "Male" else "female",
        age=int(row["age"]),
        asian=row["dodrace"] == "4",
        height=mm("stature"),
        weight=round(float(row["weightkg"]) / 10, 1),
        chest=mm("chestcircumference"),
        waist_navel=mm("waistcircumference"),
        hip=mm("buttockcircumference"),
        thigh=mm("thighcircumference"),
        inseam=mm("crotchheight"),
    )


def sample(n_per_group: int = 15, seed: int = 11, path: str = DEFAULT_PATH) -> list[dict]:
    rows = load(path)
    rng = np.random.default_rng(seed)
    out = []
    for sex in ("Male", "Female"):
        for asian in (True, False):
            pool = [r for r in rows if r["gender"] == sex and (r["dodrace"] == "4") == asian]
            pick = rng.choice(len(pool), size=n_per_group, replace=False)
            for k, i in enumerate(sorted(pick)):
                tag = f"{'M' if sex == 'Male' else 'F'}{'A' if asian else 'O'}{k + 1:02d}"
                out.append(to_subject(pool[i], tag))
    return out
