"""Fast tape measure used inside the optimiser (~1 ms instead of ~2 s).

Landmarks are tracked as template vertices (the sternum at chest height, the navel line,
the buttock point, the crotch), so they move with the body as its shape changes.
Each circumference is the convex-hull perimeter of where the mesh edges cross a
horizontal plane, keeping only the torso (or one leg) by splitting on gaps in X.
The slow, exact search in measure.py is still used for final reporting.
"""
from __future__ import annotations

import numpy as np
from scipy.spatial import ConvexHull


class Topology:
    """Edge list plus, for each face, the ids of its three edges."""

    def __init__(self, faces: np.ndarray):
        e = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
        e.sort(axis=1)
        self.edges, inverse = np.unique(e, axis=0, return_inverse=True)
        n = len(faces)
        self.face_edges = np.stack([inverse[:n], inverse[n : 2 * n], inverse[2 * n :]], axis=1)


def _find(parent, i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i


def plane_loops(verts: np.ndarray, topo: Topology, z: float) -> list[np.ndarray]:
    """Points where the mesh crosses height z, grouped into connected cross-sections."""
    a, b = verts[topo.edges[:, 0], 2] - z, verts[topo.edges[:, 1], 2] - z
    crosses = (a * b) < 0
    ids = np.where(crosses)[0]
    if len(ids) == 0:
        return []
    pa, pb = verts[topo.edges[ids, 0]], verts[topo.edges[ids, 1]]
    t = a[ids] / (a[ids] - b[ids])
    pts = (pa + (pb - pa) * t[:, None])[:, :2]

    # Union the two crossing edges of every face that the plane cuts.
    local = -np.ones(len(topo.edges), dtype=np.int64)
    local[ids] = np.arange(len(ids))
    fe = topo.face_edges
    cut = crosses[fe]
    faces_cut = np.where(cut.sum(axis=1) == 2)[0]
    parent = list(range(len(ids)))
    for f in faces_cut:
        e = fe[f][cut[f]]
        ra, rb = _find(parent, local[e[0]]), _find(parent, local[e[1]])
        if ra != rb:
            parent[ra] = rb
    roots = np.array([_find(parent, i) for i in range(len(ids))])
    return [pts[roots == r] for r in np.unique(roots)]


def _perimeter(points: np.ndarray) -> float:
    if len(points) < 3:
        return float("nan")
    hull = ConvexHull(points)
    p = points[hull.vertices]
    return float(np.linalg.norm(np.roll(p, -1, axis=0) - p, axis=1).sum())


def _straddles(g):
    return g[:, 0].min() < 0 < g[:, 0].max()


def torso_loop(verts, topo, z):
    loops = [g for g in plane_loops(verts, topo, z) if len(g) > 10 and _straddles(g)]
    return max(loops, key=len) if loops else None


def torso_circ(verts, topo, z) -> float:
    g = torso_loop(verts, topo, z)
    return _perimeter(g) * 100 if g is not None else float("nan")


def thigh_circ(verts, topo, z) -> float:
    loops = [g for g in plane_loops(verts, topo, z) if len(g) > 10]
    # Legs: the loops nearest the midline that don't cross it.
    legs = [g for g in loops if abs(g[:, 0].mean()) < 0.2 and not _straddles(g)]
    if not legs:
        return float("nan")
    return max(_perimeter(g) for g in legs) * 100


def pick_landmark_vertices(verts: np.ndarray, lm) -> dict[str, int]:
    """Choose template vertices that sit at each landmark height on the body midline."""
    mid = np.abs(verts[:, 0]) < 0.012
    idx = np.where(mid)[0]

    def front_midline(z):
        # Front surface (most negative Y) of the midline near height z (sternum, navel line).
        for tol in (0.02, 0.04, 0.08):
            cand = idx[np.abs(verts[idx, 2] - z) < tol]
            if len(cand) == 0:
                continue
            y = verts[cand, 1]
            cand = cand[y <= np.percentile(y, 30)]
            if len(cand):
                return int(cand[np.argmin(np.abs(verts[cand, 2] - z))])
        raise RuntimeError(f"No midline vertex near z={z:.3f}")

    # Hip: the buttock's most prominent vertex (the back midline sits in the crease, so it can't be used).
    height = verts[:, 2].max() - verts[:, 2].min()
    band = np.where((verts[:, 2] > lm.crotch + 0.01) & (verts[:, 2] < lm.crotch + 0.15 * height) & (np.abs(verts[:, 0]) < 0.12))[0]
    hip = int(band[np.argmax(verts[band, 1])])

    torso_mid = idx[(verts[idx, 2] > lm.crotch - 0.05) & (verts[idx, 2] < lm.hip)]
    crotch = int(torso_mid[np.argmin(np.abs(verts[torso_mid, 2] - lm.crotch))])
    return dict(chest=front_midline(lm.chest), waist=front_midline(lm.waist), hip=hip, crotch=crotch)


def fast_measure(verts, topo: Topology, ids: dict[str, int], bones: dict[str, float]) -> dict[str, float]:
    """Measurements for the optimiser: tracked landmark heights, refined by a short local search
    (fullest chest and hip, narrowest waist within ±4 cm) so they agree with the tailor's definition."""
    floor, top = verts[:, 2].min(), verts[:, 2].max()
    crotch = verts[ids["crotch"], 2]
    offsets = np.arange(-0.04, 0.0401, 0.01)

    def around(key, pick, arm_guard=False):
        z0 = verts[ids[key], 2]
        vals, base_w = [], None
        for d in offsets:  # bottom to top
            g = torso_loop(verts, topo, z0 + d)
            if g is None:
                continue
            w = g[:, 0].max() - g[:, 0].min()
            base_w = base_w or w
            # Near the armpit the arm joins the torso loop and its width jumps: stop there.
            if arm_guard and w > base_w * 1.2:
                break
            vals.append(_perimeter(g) * 100)
        return float(pick(vals)) if vals else float("nan")

    return dict(
        height=(top - floor) * 100,
        chest=around("chest", np.max, arm_guard=True),
        waist=around("waist", np.min),
        hip=around("hip", np.max),
        thigh=thigh_circ(verts, topo, crotch - 0.02),
        inseam=(crotch - floor) * 100,
        **bones,
    )
