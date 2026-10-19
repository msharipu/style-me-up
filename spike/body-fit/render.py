"""Quick 2D render of an Anny mesh (front + side) with landmark lines, for checking."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
import numpy as np


def render(mesh, lm, path, title=""):
    v, f = mesh.vertices, mesh.faces
    fig, axes = plt.subplots(1, 2, figsize=(7, 7))
    for ax, (a, b), name in [(axes[0], (0, 2), "front"), (axes[1], (1, 2), "side")]:
        normals = mesh.face_normals
        view = np.array([0, -1, 0]) if name == "front" else np.array([1, 0, 0])
        shade = np.clip(np.abs(normals @ view), 0.15, 1)
        order = np.argsort((v[f].mean(1) @ view))  # painter's order, far to near
        polys = v[f][order][:, :, [a, b]]
        pc = PolyCollection(polys, facecolors=plt.cm.Greys(0.25 + 0.55 * shade[order]), edgecolors="none")
        ax.add_collection(pc)
        ax.set_xlim(v[:, a].min() - 0.05, v[:, a].max() + 0.05)
        ax.set_ylim(lm.floor - 0.02, lm.top + 0.02)
        ax.set_aspect("equal"); ax.axis("off"); ax.set_title(name)
        for key, col in [("chest", "#DB4A40"), ("waist", "#3DA873"), ("hip", "#4578DB"), ("crotch", "#999"), ("thigh", "#B07AD6")]:
            ax.axhline(getattr(lm, key), color=col, lw=1)
            ax.text(ax.get_xlim()[1], getattr(lm, key), key, fontsize=7, color=col, va="center")
    fig.suptitle(title, fontsize=9)
    fig.savefig(path, dpi=110, bbox_inches="tight"); plt.close(fig)
