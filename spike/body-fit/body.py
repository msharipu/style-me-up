"""Thin wrapper around Anny: parameters in, mesh + joints + tape measurements out."""
from __future__ import annotations

import warnings

import numpy as np
import torch
import trimesh

warnings.filterwarnings("ignore")
import anny  # noqa: E402

from fast_measure import Topology, fast_measure, pick_landmark_vertices, torso_circ  # noqa: E402
from measure import Landmarks, bone_measurements, find_landmarks, measure  # noqa: E402

PHENOTYPES = ["gender", "age", "muscle", "weight", "height", "proportions"]

# MakeHuman shape controls used to fine-tune toward tape measurements.
# Each is a signed value: negative shrinks, positive grows.
LOCAL = [
    "measure-bust-circ-incr",
    "measure-underbust-circ-incr",
    "measure-waist-circ-incr",
    "measure-hips-circ-incr",
    "measure-thigh-circ-incr",
    "measure-shoulder-dist-incr",
    "measure-upperleg-height-incr",
    "measure-lowerleg-height-incr",
    "measure-upperarm-length-incr",
    "measure-lowerarm-length-incr",
    "stomach-pregnant-incr",
    "buttocks-volume-incr",
    "torso-scale-depth-incr",
]

JOINTS = ["upperarm01.L", "upperarm01.R", "lowerarm01.L", "wrist.L"]

# Anny's age anchors: newborn -1/3, baby 0, child 1/3, young adult (≈25 y) 2/3, old (≈90 y) 1.
ADULT_AGE = 0.70  # ≈ 30 years


def age_param(years: float | None) -> float:
    """Map age in years to Anny's age control (adults only)."""
    if years is None:
        return ADULT_AGE
    if years <= 25:
        return 1 / 3 + (max(years, 11) - 11) / 14 * (1 / 3)
    return 2 / 3 + (min(years, 90) - 25) / 65 * (1 / 3)


class Body:
    def __init__(self):
        self.model = anny.Anny(local_changes=LOCAL)
        self.faces = self.model.faces.cpu().numpy()
        self.topo = Topology(self.faces)
        self.bone_index = {b: i for i, b in enumerate(self.model.bone_labels)}
        self._ids: dict[float, dict[str, int]] = {}
        self._navel: dict[float, int] = {}

    def build(self, pheno: dict[str, float], local: dict[str, float] | None = None):
        """Returns (vertices[N,3] in metres, joints)."""
        with torch.no_grad():
            out = self.model(
                phenotype_kwargs={k: torch.tensor([v], dtype=torch.float64) for k, v in pheno.items()},
                local_changes_kwargs={k: torch.tensor([v], dtype=torch.float64) for k, v in (local or {}).items()},
            )
        verts = out["rest_vertices"][0].cpu().numpy()
        heads = out["rest_bone_heads"][0].cpu().numpy()
        joints = {j: heads[self.bone_index[j]] for j in JOINTS}
        return verts, joints

    def mesh(self, verts) -> trimesh.Trimesh:
        return trimesh.Trimesh(verts, self.faces, process=False)

    def mass_kg(self, verts) -> float:
        # Anny's own estimate: mesh volume at 980 kg/m³.
        return abs(float(self.mesh(verts).volume)) * 980.0

    def measure(self, verts, joints, lm: Landmarks | None = None, gender: float | None = None):
        """Exact tailor-style measurements (slow: ~1 s).

        `waist` is the narrowest point (tailor's natural waist). With `gender` given, also
        returns `waist_navel`, the cut at navel height that surveys such as ANSUR II use.
        """
        lm = lm or find_landmarks(verts, self.topo, float(joints["upperarm01.L"][2]))
        m = measure(verts, self.topo, lm, joints)
        m["weight"] = self.mass_kg(verts)
        if gender is not None:
            m["waist_navel"] = torso_circ(verts, self.topo, float(verts[self.navel_id(gender), 2]))
        return m, lm

    def navel_id(self, gender: float) -> int:
        """Navel vertex: deepest point of the front midline near Anny's own (navel-level) waist loop."""
        key = round(gender, 1)
        if key not in self._navel:
            from anny.anthropometry import BASE_MESH_WAIST_VERTICES

            base = self.model.base_mesh_vertex_indices.cpu().numpy().tolist()
            loop = [base.index(i) for i in BASE_MESH_WAIST_VERTICES]
            v, _ = self.build(dict(gender=key, age=ADULT_AGE))
            z0 = v[loop, 2].mean()
            mid = np.where((np.abs(v[:, 0]) < 0.01) & (np.abs(v[:, 2] - z0) < 0.06) & (v[:, 1] < 0))[0]
            self._navel[key] = int(mid[np.argmax(v[mid, 1])])
        return self._navel[key]

    def landmark_ids(self, gender: float) -> dict[str, int]:
        """Template vertices that track each landmark, picked once per sex on the average body."""
        key = round(gender, 1)
        if key not in self._ids:
            verts, joints = self.build(dict(gender=key, age=ADULT_AGE))
            _, lm = self.measure(verts, joints)
            self._ids[key] = pick_landmark_vertices(verts, lm)
        return self._ids[key]

    def quick_measure(self, verts, joints, gender: float, with_weight: bool = False):
        """Fast measurements for the optimiser (~40 ms)."""
        m = fast_measure(verts, self.topo, self.landmark_ids(gender), bone_measurements(joints))
        m["waist_navel"] = torso_circ(verts, self.topo, float(verts[self.navel_id(gender), 2]))
        if with_weight:
            m["weight"] = self.mass_kg(verts)
        return m
