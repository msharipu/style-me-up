"""BodyM (Amazon) silhouettes + measurements, for testing the photo path.

https://registry.opendata.aws/bodym/ — 2,505 people; per photo a front mask (mask/) and a
left-side mask (mask_left/), 720×960 PNG; per person height, weight, sex and 14 measurements.

Licence is ambiguous (page names CC BY-NC 4.0, links CC BY 4.0). We treat it as
NON-COMMERCIAL: internal evaluation only. Never train on it, ship it, or commit it to git.
Data is cached under spike/body-fit/data/bodym/ (gitignored).
"""
from __future__ import annotations

import csv
import os
import urllib.request

import numpy as np
from PIL import Image

BUCKET = "https://amazon-bodym.s3.us-west-2.amazonaws.com"
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "bodym")


def _get(rel: str) -> str:
    path = os.path.join(CACHE, rel)
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        urllib.request.urlretrieve(f"{BUCKET}/{rel}", path)
    return path


def _csv(rel: str) -> list[dict]:
    with open(_get(rel)) as f:
        return list(csv.DictReader(f))


def subjects(split: str = "testA") -> list[dict]:
    hwg = {r["subject_id"]: r for r in _csv(f"{split}/hwg_metadata.csv")}
    meas = {r["subject_id"]: r for r in _csv(f"{split}/measurements.csv")}
    photos: dict[str, list[str]] = {}
    for r in _csv(f"{split}/subject_to_photo_map.csv"):
        photos.setdefault(r["subject_id"], []).append(r["photo_id"])
    out = []
    for i, (sid, h) in enumerate(sorted(hwg.items())):
        if sid not in meas or sid not in photos:
            continue
        m = meas[sid]
        out.append(dict(
            id=f"B{i + 1:03d}",
            subject_id=sid,
            split=split,
            sex=h["gender"],
            height_entered=float(h["height_cm"]),  # what the person typed in
            weight=float(h["weight_kg"]),
            photo_id=sorted(photos[sid])[0],
            truth={k: float(m[k]) for k in ("height", "chest", "waist", "hip", "thigh", "shoulder-breadth", "leg-length")},
        ))
    return out


def masks(s: dict) -> tuple[np.ndarray, np.ndarray]:
    front = np.array(Image.open(_get(f"{s['split']}/mask/{s['photo_id']}.png")).convert("L")) > 127
    side = np.array(Image.open(_get(f"{s['split']}/mask_left/{s['photo_id']}.png")).convert("L")) > 127
    return front, side
