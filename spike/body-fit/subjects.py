"""Synthetic test subjects with realistic adult tape measurements.

Stand-in for the volunteer study (MAL-8) until real tape data arrives. Heights and BMI
follow broad Southeast Asian adult distributions; circumferences come from simple
height/BMI relationships with individual shape noise, so the set includes pear, apple,
slim and broad builds the body model has to reach. These numbers are illustrative,
not survey data: they test whether Anny can *represent* plausible bodies, not whether
photos can recover them.
"""
from __future__ import annotations

import numpy as np


def make_subjects(n_per_sex: int = 20, seed: int = 7) -> list[dict]:
    rng = np.random.default_rng(seed)
    out = []
    for sex in ("male", "female"):
        for i in range(n_per_sex):
            if sex == "male":
                h = float(np.clip(rng.normal(170, 6.5), 155, 190))
                bmi = float(np.clip(rng.lognormal(np.log(24.5), 0.15), 17.5, 36))
                chest = 58 + 1.6 * bmi + 0.15 * (h - 170)
                waist = h * (0.22 + 0.0122 * bmi)
                hip = 55 + 1.75 * bmi + 0.25 * (h - 170)
                thigh = 20 + 1.45 * bmi
                inseam = 0.455 * h
                shoulder = 0.262 * h
                arm = 0.345 * h
            else:
                h = float(np.clip(rng.normal(158, 6), 145, 175))
                bmi = float(np.clip(rng.lognormal(np.log(23.5), 0.17), 16.5, 38))
                chest = 50 + 1.7 * bmi + 0.12 * (h - 158)
                waist = h * (0.20 + 0.0125 * bmi)
                hip = 52 + 1.95 * bmi + 0.25 * (h - 158)
                thigh = 18 + 1.65 * bmi
                inseam = 0.45 * h
                shoulder = 0.24 * h
                arm = 0.335 * h
            # Individual shape variation (cm), so circumferences don't move in lockstep with BMI.
            out.append(dict(
                id=f"{'M' if sex == 'male' else 'F'}{i + 1:02d}",
                sex=sex,
                age=int(rng.integers(20, 56)),
                height=round(h, 1),
                weight=round(bmi * (h / 100) ** 2, 1),
                chest=round(chest + rng.normal(0, 3.0), 1),
                waist=round(waist + rng.normal(0, 3.5), 1),
                hip=round(hip + rng.normal(0, 3.0), 1),
                thigh=round(thigh + rng.normal(0, 2.0), 1),
                inseam=round(inseam + rng.normal(0, 1.8), 1),
                shoulder=round(shoulder + rng.normal(0, 1.5), 1),
                arm=round(arm + rng.normal(0, 1.5), 1),
            ))
    return out
