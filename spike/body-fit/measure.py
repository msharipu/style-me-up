"""Virtual tape measure for Anny meshes.

Anny's rest pose has the arms hanging slightly away from the body, Z up, metres,
+Y towards the back. Circumferences are measured the way a tape would: cut the mesh
with a horizontal plane, keep the torso (or one leg) loop, and take the perimeter of
its convex hull, because a tape bridges hollows such as the spine.

Loops are separated by mesh connectivity, so an arm resting against the torso is
never counted in the chest or waist.

All measurements are centimetres.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

from fast_measure import Topology, plane_loops, thigh_circ, torso_circ, _straddles


@dataclass
class Landmarks:
    """Heights (metres, mesh coordinates) where each measurement is taken."""
    floor: float
    top: float
    crotch: float
    hip: float
    waist: float
    chest: float
    thigh: float


def _legs(loops):
    return [g for g in loops if len(g) > 10 and abs(g[:, 0].mean()) < 0.2 and not _straddles(g)]


def find_landmarks(verts: np.ndarray, topo: Topology, shoulder_z: float) -> Landmarks:
    """Search horizontal cuts for crotch, hip, waist and chest heights."""
    floor, top = float(verts[:, 2].min()), float(verts[:, 2].max())
    height = top - floor

    # Crotch: lowest height where the legs have joined into one loop across the midline.
    crotch = None
    for z in np.arange(floor + 0.35 * height, floor + 0.62 * height, 0.002):
        loops = plane_loops(verts, topo, z)
        if any(len(g) > 10 and _straddles(g) for g in loops) and not _legs(loops):
            crotch = float(z)
            break
    if crotch is None:
        raise RuntimeError("Could not find the crotch.")

    # Hip: height of the most prominent point of the buttocks (+Y), where a tailor puts the tape.
    band = (verts[:, 2] > crotch + 0.01) & (verts[:, 2] < crotch + 0.15 * height) & (np.abs(verts[:, 0]) < 0.12)
    hip = float(verts[band][np.argmax(verts[band][:, 1]), 2])

    # Armpit: where the arm joins the torso loop, seen as a jump in its width.
    armpit = shoulder_z
    prev_w = None
    for z in np.arange(hip + 0.05, shoulder_z + 0.03, 0.002):
        loops = [g for g in plane_loops(verts, topo, z) if len(g) > 10 and _straddles(g)]
        if not loops:
            continue
        g = max(loops, key=len)
        w = g[:, 0].max() - g[:, 0].min()
        if prev_w is not None and w > prev_w * 1.25:
            armpit = float(z)
            break
        prev_w = w

    def scan(lo, hi, step):
        zs = np.arange(lo, hi, step)
        c = np.array([torso_circ(verts, topo, z) for z in zs])
        ok = ~np.isnan(c)
        return zs[ok], c[ok]

    # Chest: fullest torso cut in the band just under the armpits (about 13 cm deep on a
    # 170 cm adult). A bounded band stops a full stomach being taken for the chest.
    zs, c = scan(armpit - 0.075 * height, armpit - 0.012, 0.003)
    chest = float(zs[np.argmax(c)])
    # Waist: narrowest torso cut in the middle of the hip-to-armpit span, where the natural
    # waist sits; bounded so a flat or round torso doesn't push it to the hip or bust.
    span = armpit - hip
    zs, c = scan(hip + 0.30 * span, min(hip + 0.80 * span, chest - 0.03), 0.003)
    waist = float(zs[np.argmin(c)])

    return Landmarks(floor=floor, top=top, crotch=crotch, hip=hip, waist=waist, chest=chest, thigh=crotch - 0.02)


def bone_measurements(joints: dict[str, np.ndarray]) -> dict[str, float]:
    # Shoulder width across the back: shoulder joint centres plus the deltoid on each side
    # (~4 cm total on adults; calibrate against volunteers).
    shoulder = float(np.linalg.norm(joints["upperarm01.L"] - joints["upperarm01.R"])) * 100 + 4.0
    # Arm: bony shoulder point to wrist bone, along the bones.
    arm = float(
        np.linalg.norm(joints["upperarm01.L"] - joints["lowerarm01.L"])
        + np.linalg.norm(joints["lowerarm01.L"] - joints["wrist.L"])
    ) * 100 + 2.0
    return dict(shoulder=shoulder, arm=arm)


def measure(verts: np.ndarray, topo: Topology, lm: Landmarks, joints: dict[str, np.ndarray]) -> dict[str, float]:
    return dict(
        height=(lm.top - lm.floor) * 100,
        chest=torso_circ(verts, topo, lm.chest),
        waist=torso_circ(verts, topo, lm.waist),
        hip=torso_circ(verts, topo, lm.hip),
        thigh=thigh_circ(verts, topo, lm.thigh),
        inseam=(lm.crotch - lm.floor) * 100,
        **bone_measurements(joints),
    )


def landmarks_dict(lm: Landmarks) -> dict:
    return asdict(lm)
