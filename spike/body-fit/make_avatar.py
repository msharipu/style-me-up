"""Make an avatar GLB from tape measurements.

    python3 make_avatar.py --sex male --age 32 --height 175 --chest 96 --waist 82 --hip 96 \
        --thigh 56 --inseam 80 --shoulder 45 --arm 60 --weight 70 \
        --out ../../apps/mobile/assets/avatar

Writes <out>.glb (mesh with fit zones) and <out>.json (measurements, errors, model parameters).
Only --sex and --height are required; every extra measurement makes the avatar more accurate.
"""
from __future__ import annotations

import argparse

from body import Body
from export import export_fit
from fit import fit

ZONES = ["height", "chest", "waist", "hip", "thigh", "inseam", "shoulder", "arm", "weight"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sex", choices=["male", "female"], required=True)
    ap.add_argument("--age", type=float, default=None)
    ap.add_argument("--height", type=float, required=True, help="cm")
    for z in ZONES[1:]:
        ap.add_argument(f"--{z}", type=float, default=None, help="kg" if z == "weight" else "cm")
    ap.add_argument("--out", required=True, help="output path without extension")
    a = ap.parse_args()
    target = {z: getattr(a, z) for z in ZONES if getattr(a, z) is not None}

    body = Body()
    r = fit(body, target, a.sex, a.age, verbose=True)
    export_fit(body, r, f"{a.out}.glb", f"{a.out}.json", a.sex)
    print(f"Done in {r.seconds}s. Error per zone (cm):")
    for z, e in r.errors.items():
        flag = "  <-- over 2 cm" if z in ("chest", "waist", "hip") and abs(e) > 2 else ""
        print(f"  {z:9s} {e:+6.2f}{flag}")


if __name__ == "__main__":
    main()
