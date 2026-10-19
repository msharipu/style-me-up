"""Silhouette fit on rendered avatars with known measurements (no real photos needed)."""
import numpy as np
from body import Body, ADULT_AGE
from silhouette import render_mask, mask_profile, mesh_profile, fit_silhouettes

CASES = [
    ("male, heavier", 0.0, dict(muscle=0.6, weight=0.7, height=0.55, proportions=0.4), {"measure-waist-circ-incr": 0.3, "stomach-pregnant-incr": 0.2, "measure-hips-circ-incr": -0.2}),
    ("female, pear", 1.0, dict(muscle=0.3, weight=0.55, height=0.35, proportions=0.6), {"measure-hips-circ-incr": 0.4, "measure-bust-circ-incr": -0.2}),
]
b = Body()
for name, g, ph, loc in CASES:
    v, j = b.build(dict(gender=g, age=ADULT_AGE, **ph), loc)
    truth, _ = b.measure(v, j, gender=g)
    front, side = render_mask(v, b.faces, "front"), render_mask(v, b.faces, "side")
    H = truth["height"]
    mw, md = mesh_profile(v, b.topo)
    print(f"{name}: profile mask vs mesh — front max {np.nanmax(np.abs(mask_profile(front,H,'front')-mw)):.2f} cm, side max {np.nanmax(np.abs(mask_profile(side,H,'side')-md)):.2f} cm")
    r = fit_silhouettes(b, front, side, H, "male" if g == 0 else "female", verbose=True)
    m = r["measured"]
    print("   " + "  ".join(f"{k} {m[k]-truth[k]:+.1f}" for k in ["chest", "waist", "waist_navel", "hip", "thigh", "inseam"]))
