"""Export a fitted body as a GLB the app can load, with fit zones baked in.

- Converted from Anny's Z-up, face-towards-−Y frame to glTF's Y-up, face-towards-+Z.
- Feet on the floor (y = 0), centred on x = z = 0, metres.
- A custom `_ZONE` vertex attribute (float) labels each vertex for the fit heatmap:
  0 not judged (head, neck, hands, lower legs, feet), 1 chest, 2 waist, 3 hip,
  4 thigh, 5 shoulder, 6 sleeve (arms). The app reads it as geometry attribute `_zone`.
"""
from __future__ import annotations

import json

import numpy as np
import pygltflib
import trimesh

from body import Body
from measure import Landmarks


def zone_labels(body: Body, verts: np.ndarray, lm: Landmarks, armpit: float) -> np.ndarray:
    w = body.model.vertex_bone_weights.cpu().numpy()
    idx = body.model.vertex_bone_indices.cpu().numpy()
    names = body.model.bone_labels
    dominant = [names[i] for i in idx[np.arange(len(idx)), np.argmax(w, axis=1)]]
    z = verts[:, 2]
    zones = np.zeros(len(verts), dtype=np.float32)
    hip_waist = (lm.hip + lm.waist) / 2
    waist_chest = (lm.waist + lm.chest) / 2
    for i, bone in enumerate(dominant):
        if bone.startswith(("upperarm", "lowerarm")):
            zones[i] = 6
        elif bone.startswith(("shoulder01", "clavicle")):
            zones[i] = 5
        elif bone.startswith("upperleg"):
            zones[i] = 4
        elif bone.startswith(("spine", "pelvis", "root")):
            if z[i] < hip_waist:
                zones[i] = 3
            elif z[i] < waist_chest:
                zones[i] = 2
            elif z[i] < armpit + 0.07:  # chest zone covers the pecs up to the collarbone line
                zones[i] = 1
            else:
                zones[i] = 5
    return zones


def to_gltf_frame(verts: np.ndarray) -> np.ndarray:
    # (x, y, z) Z-up, front −Y  →  (x, z, −y) Y-up, front +Z
    out = np.column_stack([verts[:, 0], verts[:, 2], -verts[:, 1]])
    out[:, 1] -= out[:, 1].min()
    out[:, 0] -= (out[:, 0].max() + out[:, 0].min()) / 2
    out[:, 2] -= (out[:, 2].max() + out[:, 2].min()) / 2
    return out


def write_glb(path: str, verts: np.ndarray, faces: np.ndarray, zones: np.ndarray) -> None:
    v = to_gltf_frame(verts).astype(np.float32)
    normals = trimesh.Trimesh(v, faces, process=False).vertex_normals.astype(np.float32)
    f = faces.astype(np.uint32)
    blobs = [f.tobytes(), v.tobytes(), normals.tobytes(), zones.astype(np.float32).tobytes()]
    offsets = np.cumsum([0] + [len(b) for b in blobs])
    gltf = pygltflib.GLTF2(
        asset=pygltflib.Asset(version="2.0", generator="Style Me Up! body-fit spike"),
        scene=0,
        scenes=[pygltflib.Scene(nodes=[0])],
        nodes=[pygltflib.Node(mesh=0, name="avatar")],
        meshes=[
            pygltflib.Mesh(
                name="avatar",
                primitives=[
                    pygltflib.Primitive(
                        attributes=pygltflib.Attributes(POSITION=1, NORMAL=2, _ZONE=3),
                        indices=0,
                    )
                ],
            )
        ],
        accessors=[
            pygltflib.Accessor(bufferView=0, componentType=pygltflib.UNSIGNED_INT, count=f.size, type=pygltflib.SCALAR),
            pygltflib.Accessor(bufferView=1, componentType=pygltflib.FLOAT, count=len(v), type=pygltflib.VEC3,
                               min=v.min(0).tolist(), max=v.max(0).tolist()),
            pygltflib.Accessor(bufferView=2, componentType=pygltflib.FLOAT, count=len(v), type=pygltflib.VEC3),
            pygltflib.Accessor(bufferView=3, componentType=pygltflib.FLOAT, count=len(v), type=pygltflib.SCALAR),
        ],
        bufferViews=[
            pygltflib.BufferView(buffer=0, byteOffset=int(offsets[0]), byteLength=len(blobs[0]), target=pygltflib.ELEMENT_ARRAY_BUFFER),
            pygltflib.BufferView(buffer=0, byteOffset=int(offsets[1]), byteLength=len(blobs[1]), target=pygltflib.ARRAY_BUFFER),
            pygltflib.BufferView(buffer=0, byteOffset=int(offsets[2]), byteLength=len(blobs[2]), target=pygltflib.ARRAY_BUFFER),
            pygltflib.BufferView(buffer=0, byteOffset=int(offsets[3]), byteLength=len(blobs[3]), target=pygltflib.ARRAY_BUFFER),
        ],
        buffers=[pygltflib.Buffer(byteLength=int(offsets[-1]))],
    )
    gltf.set_binary_blob(b"".join(blobs))
    gltf.save_binary(path)


def export_fit(body: Body, result, glb_path: str, json_path: str, sex: str) -> None:
    from measure import find_landmarks  # noqa: F401  (landmarks already on result)

    lm = result.landmarks
    # Same armpit search the measurer uses: first height where the torso loop widens sharply.
    from fast_measure import torso_loop

    armpit = float(result.joints["upperarm01.L"][2])
    prev = None
    for zz in np.arange(lm.chest, armpit + 0.03, 0.002):
        g = torso_loop(result.verts, body.topo, zz)
        if g is None:
            continue
        w = g[:, 0].max() - g[:, 0].min()
        if prev is not None and w > prev * 1.25:
            armpit = float(zz)
            break
        prev = w
    zones = zone_labels(body, result.verts, lm, armpit)
    write_glb(glb_path, result.verts, body.faces, zones)
    m = result.measured
    info = {
        "sex": sex,
        "measurements": {k: round(m[k], 1) for k in ["height", "chest", "waist", "hip", "thigh", "inseam", "shoulder", "arm"]},
        "target": result.target,
        "errors_cm": result.errors,
        "model": {"name": "Anny", "license": "Apache-2.0", "phenotype": result.pheno, "local_changes": result.local},
    }
    # The fit engine calls shoulder-to-wrist "arm".
    with open(json_path, "w") as f:
        json.dump(info, f, indent=2)
