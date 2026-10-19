import { useEffect, useMemo, type MutableRefObject } from "react";
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import type { Zone } from "@stylemeup/fit-engine";
import { useFrame, useLoader, useThree } from "./three/fiber";
import { heatToRgb, ZONE_IDS } from "./heat";

interface Props {
  /** require("…/avatar.glb") */
  source: number | string;
  /** Heat per zone, -1 … 1. Zones not in the map are drawn in neutral clay. */
  zoneHeat: Partial<Record<Zone, number>>;
  /** Rotation around the vertical axis, in radians; updated by the drag handler. */
  rotation: MutableRefObject<number>;
}

export function Avatar({ source, zoneHeat, rotation }: Props) {
  const gltf = useLoader(GLTFLoader, source as string);

  // One mesh, one material with vertex colours, so the heatmap is a single attribute write.
  const { mesh, group } = useMemo(() => {
    const group = new THREE.Group();
    let mesh: THREE.Mesh | undefined;
    gltf.scene.traverse((o) => {
      if (!mesh && (o as THREE.Mesh).isMesh) mesh = o as THREE.Mesh;
    });
    if (!mesh) throw new Error("Avatar GLB has no mesh.");
    const geom = mesh.geometry as THREE.BufferGeometry;
    const count = geom.getAttribute("position").count;
    if (!geom.getAttribute("color")) {
      geom.setAttribute("color", new THREE.BufferAttribute(new Float32Array(count * 3), 3));
    }
    if (!geom.getAttribute("normal")) geom.computeVertexNormals();
    mesh.material = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.75, metalness: 0 });
    group.add(mesh.clone());
    return { mesh: group.children[0] as THREE.Mesh, group };
  }, [gltf]);

  useEffect(() => {
    const geom = mesh.geometry as THREE.BufferGeometry;
    const zone = geom.getAttribute("_zone") as THREE.BufferAttribute | undefined;
    const color = geom.getAttribute("color") as THREE.BufferAttribute;
    for (let i = 0; i < color.count; i++) {
      const z = zone ? ZONE_IDS[Math.round(zone.getX(i))] : undefined;
      const [r, g, b] = heatToRgb(z ? zoneHeat[z] : undefined);
      color.setXYZ(i, r, g, b);
    }
    color.needsUpdate = true;
  }, [mesh, zoneHeat]);

  useFrame(() => {
    // Ease toward the target rotation so drags feel smooth.
    group.rotation.y += (rotation.current - group.rotation.y) * 0.2;
  });

  return <primitive object={group} />;
}

/** Points the camera at the avatar's middle (R3F cameras look at the origin by default). */
export function CameraRig({ target = [0, 0.88, 0] as [number, number, number] }) {
  const camera = useThree((st) => st.camera);
  useEffect(() => {
    camera.lookAt(...target);
    camera.updateProjectionMatrix();
  }, [camera, target]);
  return null;
}
