"""Fit Anny to a person's tape measurements.

Stage 1  global shape: muscle, weight, height, proportions (age and sex fixed from the user).
Stage 2  local MakeHuman controls (bust, waist, hips, thigh, shoulders, leg and arm length…),
         lightly regularised so the body stays natural.
Stage 3  one bias-correction pass: measure the result with the exact tailor-style tape,
         shift the targets by the fast-vs-exact difference, and refine again.

Inputs and outputs are centimetres and kilograms.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import least_squares

from body import LOCAL, Body, age_param

GLOBAL = ["muscle", "weight", "height", "proportions"]

# How much each centimetre of error matters in the fit.
ZONE_WEIGHT = dict(height=2.0, chest=1.0, waist=1.0, hip=1.0, thigh=0.7, inseam=1.0, shoulder=0.7, arm=0.5)
WEIGHT_PER_KG = 0.3
LOCAL_REG = 2.5  # cm-equivalent penalty per unit of each local control


@dataclass
class FitResult:
    pheno: dict[str, float]
    local: dict[str, float]
    measured: dict[str, float]
    target: dict[str, float]
    errors: dict[str, float]
    seconds: float
    evaluations: int
    verts: np.ndarray = field(repr=False)
    joints: dict = field(repr=False)
    landmarks: object = field(repr=False)


def _residuals(m: dict, target: dict, zones: list[str]) -> list[float]:
    r = []
    for z in zones:
        if z == "weight":
            r.append(WEIGHT_PER_KG * (m["weight"] - target["weight"]))
        else:
            val = m[z]
            r.append(ZONE_WEIGHT[z] * ((val if np.isfinite(val) else 0.0) - target[z]))
    return r


def fit(body: Body, target: dict[str, float], sex: str, age_years: float | None = None, verbose=False) -> FitResult:
    t0 = time.time()
    gender = 0.0 if sex == "male" else 1.0
    age = age_param(age_years)
    zones = [z for z in ZONE_WEIGHT if z in target]
    use_weight = "weight" in target
    if use_weight:
        zones.append("weight")
    evals = 0

    def measure_fast(pheno, local):
        nonlocal evals
        evals += 1
        v, j = body.build(pheno, local)
        return body.quick_measure(v, j, gender, with_weight=use_weight)

    # Stage 1: global phenotype.
    def pheno_of(x):
        return dict(gender=gender, age=age, **{k: float(x[i]) for i, k in enumerate(GLOBAL)})

    def f1(x):
        return _residuals(measure_fast(pheno_of(x), None), target, zones)

    # Start height from a two-point calibration so the optimiser begins near the right size.
    h0 = measure_fast(pheno_of([0.5, 0.5, 0.0, 0.5]), None)["height"]
    h1 = measure_fast(pheno_of([0.5, 0.5, 1.0, 0.5]), None)["height"]
    x_h = float(np.clip((target["height"] - h0) / (h1 - h0), 0, 1))
    s1 = least_squares(f1, [0.5, 0.5, x_h, 0.5], bounds=(0, 1), diff_step=0.02, max_nfev=60, xtol=1e-4)
    if verbose:
        print(f"  stage 1: cost {s1.cost:.1f}, {evals} evals")

    # Stage 2: add local controls.
    n_g = len(GLOBAL)

    def split(x):
        return pheno_of(x[:n_g]), {k: float(x[n_g + i]) for i, k in enumerate(LOCAL)}

    def make_f2(tgt):
        def f2(x):
            p, l = split(x)
            r = _residuals(measure_fast(p, l), tgt, zones)
            return r + list(LOCAL_REG * x[n_g:])
        return f2

    lo = [0] * n_g + [-1] * len(LOCAL)
    hi = [1] * n_g + [1] * len(LOCAL)
    x = np.concatenate([s1.x, np.zeros(len(LOCAL))])
    s2 = least_squares(make_f2(target), x, bounds=(lo, hi), diff_step=0.02, max_nfev=200, xtol=1e-4)
    if verbose:
        print(f"  stage 2: cost {s2.cost:.1f}, {evals} evals")

    # Stage 3: correct the fast-vs-exact measurement bias, then refine.
    p, l = split(s2.x)
    v, j = body.build(p, l)
    exact, _ = body.measure(v, j)
    fast = body.quick_measure(v, j, gender, with_weight=use_weight)
    shifted = dict(target)
    for z in ("chest", "waist", "hip", "thigh", "inseam"):
        if z in target and np.isfinite(exact[z]) and np.isfinite(fast[z]):
            shifted[z] = target[z] - (exact[z] - fast[z])
    s3 = least_squares(make_f2(shifted), s2.x, bounds=(lo, hi), diff_step=0.02, max_nfev=80, xtol=1e-4)

    p, l = split(s3.x)
    v, j = body.build(p, l)
    measured, lm = body.measure(v, j)
    errors = {z: round(measured[z] - target[z], 2) for z in target if z in measured}
    return FitResult(
        pheno=p,
        local={k: round(val, 4) for k, val in l.items()},
        measured={k: round(val, 2) for k, val in measured.items()},
        target=target,
        errors=errors,
        seconds=round(time.time() - t0, 1),
        evaluations=evals,
        verts=v,
        joints=j,
        landmarks=lm,
    )
