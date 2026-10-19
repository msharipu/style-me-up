"""Fit Anny to front + side silhouettes and height (the photo path).

A phone photo becomes a binary person mask with any segmentation model; BodyM ships masks
directly. From each mask we read the body's *width profile* (front view) and *depth profile*
(side view): at each height level, how wide or deep the central body run is, in cm, scaled by
the person's known height. We then fit Anny's controls until the avatar casts the same
profiles, and read circumferences off the fitted mesh with the virtual tape.

Levels are fractions of stature from the floor, limited to the torso and upper legs, where the
silhouette is the body itself rather than arms or hair.
"""
from __future__ import annotations

import time

import numpy as np
from PIL import Image, ImageDraw
from scipy.optimize import least_squares

from body import LOCAL, Body, age_param
from fast_measure import plane_loops, _straddles

GLOBAL = ["muscle", "weight", "height", "proportions"]

# Torso levels (fraction of stature) between upper thigh and chest, under the arms.
LEVELS = np.round(np.arange(0.44, 0.73, 0.015), 3)
LOCAL_REG = 2.5


# ---------- Profiles from a binary mask ----------

def mask_profile(mask: np.ndarray, height_cm: float, view: str, levels=LEVELS) -> np.ndarray:
    """Width (front) or depth (side) of the central body run at each level, in cm.

    mask: 2-D bool array, True = person, rows top→bottom, feet at the bottom of the body.
    """
    rows = np.where(mask.any(axis=1))[0]
    top, bottom = rows[0], rows[-1]
    px_per_cm = (bottom - top) / height_cm
    cols = np.where(mask.any(axis=0))[0]
    centre = mask[top : bottom + 1].nonzero()[1].mean()
    out = []
    for f in levels:
        r = int(round(bottom - f * (bottom - top)))
        line = mask[r]
        runs = _runs(line)
        if not runs:
            out.append(np.nan)
            continue
        if view == "front":
            # The run that contains the body's centre line; at upper-thigh height there are two leg
            # runs, so take the span from the outer edges of the two runs nearest the centre.
            hit = [ru for ru in runs if ru[0] <= centre <= ru[1]]
            if hit:
                a, b = hit[0]
            else:
                left = [ru for ru in runs if ru[1] < centre]
                right = [ru for ru in runs if ru[0] > centre]
                if not left or not right:
                    out.append(np.nan)
                    continue
                a, b = left[-1][0], right[0][1]
        else:
            # Side view: the longest run is the torso (arms overlap it).
            a, b = max(runs, key=lambda ru: ru[1] - ru[0])
        out.append((b - a + 1) / px_per_cm)
    return np.array(out)


def _runs(line: np.ndarray) -> list[tuple[int, int]]:
    d = np.diff(np.concatenate([[0], line.astype(np.int8), [0]]))
    starts, ends = np.where(d == 1)[0], np.where(d == -1)[0] - 1
    return list(zip(starts, ends))


# ---------- Profiles from the avatar mesh ----------

def _merge(intervals):
    out = []
    for a, b in sorted(intervals):
        if out and a <= out[-1][1] + 0.005:  # gaps under 5 mm vanish in a photo silhouette
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def mesh_profile(verts: np.ndarray, topo, levels=LEVELS) -> tuple[np.ndarray, np.ndarray]:
    """(front width, side depth) at each level, in cm, read exactly as from a silhouette.

    An orthographic silhouette row at height z is the union of every cross-section at z projected
    onto the image axis, arms included, so we build it that way and apply the same run rules
    as mask_profile.
    """
    floor, top = verts[:, 2].min(), verts[:, 2].max()
    h = top - floor
    widths, depths = [], []
    for f in levels:
        loops = [g for g in plane_loops(verts, topo, floor + f * h) if len(g) > 3]
        if not loops:
            widths.append(np.nan); depths.append(np.nan)
            continue
        xs = _merge([(g[:, 0].min(), g[:, 0].max()) for g in loops])
        ys = _merge([(g[:, 1].min(), g[:, 1].max()) for g in loops])
        centre = 0.0
        hit = [r for r in xs if r[0] <= centre <= r[1]]
        if hit:
            w = hit[0][1] - hit[0][0]
        else:
            left = [r for r in xs if r[1] < centre]
            right = [r for r in xs if r[0] > centre]
            w = (right[0][1] - left[-1][0]) if left and right else np.nan
        widths.append(w * 100)
        depths.append(max(b - a for a, b in ys) * 100)
    return np.array(widths), np.array(depths)


# ---------- Rendering silhouettes from a mesh (for testing without real photos) ----------

def render_mask(verts: np.ndarray, faces: np.ndarray, view: str, px_per_m: float = 400) -> np.ndarray:
    """Orthographic binary silhouette. front: x→columns; side: y→columns. z up."""
    a = 0 if view == "front" else 1
    pts = verts[:, [a, 2]]
    lo, hi = pts.min(0) - 0.05, pts.max(0) + 0.05
    w, hgt = ((hi - lo) * px_per_m).astype(int) + 1
    img = Image.new("1", (int(w), int(hgt)), 0)
    draw = ImageDraw.Draw(img)
    p = (pts - lo) * px_per_m
    p[:, 1] = hgt - 1 - p[:, 1]
    for tri in faces:
        draw.polygon([tuple(p[i]) for i in tri], fill=1)
    return np.array(img, dtype=bool)


# ---------- Fit ----------

def fit_silhouettes(body: Body, front: np.ndarray, side: np.ndarray, height_cm: float, sex: str,
                    age_years=None, weight_kg=None, verbose=False):
    t0 = time.time()
    gender = 0.0 if sex == "male" else 1.0
    age = age_param(age_years)
    tw = mask_profile(front, height_cm, "front")
    td = mask_profile(side, height_cm, "side")
    n_g = len(GLOBAL)

    def split(x):
        p = dict(gender=gender, age=age, **{k: float(x[i]) for i, k in enumerate(GLOBAL)})
        return p, {k: float(x[n_g + i]) for i, k in enumerate(LOCAL)}

    def residuals(x):
        p, l = split(x)
        v, _ = body.build(p, l)
        mw, md = mesh_profile(v, body.topo)
        h = (v[:, 2].max() - v[:, 2].min()) * 100
        r = [2.0 * (h - height_cm)]
        for a, b in ((mw, tw), (md, td)):
            d = a - b
            r += list(np.where(np.isfinite(d), d, 0.0))
        if weight_kg is not None:
            r.append(0.3 * (body.mass_kg(v) - weight_kg))
        return r + list(LOCAL_REG * x[n_g:])

    # Start near the right size: two-point height calibration, then global shape only, then everything.
    def height_at(xh):
        v, _ = body.build(*split(np.concatenate([[0.5, 0.5, xh, 0.5], np.zeros(len(LOCAL))])))
        return (v[:, 2].max() - v[:, 2].min()) * 100

    h0, h1 = height_at(0.0), height_at(1.0)
    x_h = float(np.clip((height_cm - h0) / (h1 - h0), 0, 1))

    def residuals_global(xg):
        return residuals(np.concatenate([xg, np.zeros(len(LOCAL))]))[: -len(LOCAL)]

    s1 = least_squares(residuals_global, [0.5, 0.5, x_h, 0.5], bounds=(0, 1), diff_step=0.02, max_nfev=80, xtol=1e-5)
    lo = [0] * n_g + [-1] * len(LOCAL)
    hi = [1] * n_g + [1] * len(LOCAL)
    x0 = np.concatenate([s1.x, np.zeros(len(LOCAL))])
    s = least_squares(residuals, x0, bounds=(lo, hi), diff_step=0.02, max_nfev=250, xtol=1e-5)
    p, l = split(s.x)
    v, j = body.build(p, l)
    measured, lm = body.measure(v, j, gender=gender)
    if verbose:
        print(f"  silhouette fit: cost {s.cost:.1f}, {s.nfev} evals, {time.time() - t0:.0f}s")
    return dict(pheno=p, local=l, measured=measured, verts=v, joints=j, landmarks=lm,
                seconds=round(time.time() - t0, 1), profiles=dict(front=tw.tolist(), side=td.tolist()))
