import type { Verdict, Zone } from "@stylemeup/fit-engine";

/** Colours for the fit heatmap. Tight = warm, right = green, loose = cool. */
export const COLORS = {
  tight: [0.86, 0.29, 0.25] as const, // #DB4A40
  right: [0.24, 0.66, 0.45] as const, // #3DA873
  loose: [0.27, 0.47, 0.86] as const, // #4578DB
  skin: [0.82, 0.78, 0.74] as const, // clay grey, unjudged zones
};

type RGB = readonly [number, number, number];
const lerp = (a: RGB, b: RGB, t: number): RGB => [
  a[0] + (b[0] - a[0]) * t,
  a[1] + (b[1] - a[1]) * t,
  a[2] + (b[2] - a[2]) * t,
];

/** heat: -1 (too tight) … 0 (right) … +1 (too loose). */
export function heatToRgb(heat: number | undefined): RGB {
  if (heat === undefined) return COLORS.skin;
  const t = Math.min(1, Math.abs(heat));
  return heat < 0 ? lerp(COLORS.right, COLORS.tight, t) : lerp(COLORS.right, COLORS.loose, t);
}

export const rgbToCss = ([r, g, b]: RGB) =>
  `rgb(${Math.round(r * 255)}, ${Math.round(g * 255)}, ${Math.round(b * 255)})`;

export const VERDICT_LABEL: Record<Verdict, string> = {
  "too-tight": "Too tight",
  snug: "Snug",
  right: "Right",
  roomy: "Roomy",
  "too-loose": "Too loose",
  "too-short": "Too short",
  short: "A bit short",
  long: "A bit long",
  "too-long": "Too long",
};

/** Zone ids baked into the avatar GLB's _ZONE vertex attribute (see spike/body-fit/zones.py). */
export const ZONE_IDS: Record<number, Zone | undefined> = {
  0: undefined, // head, hands, feet, lower legs — not judged
  1: "chest",
  2: "waist",
  3: "hip",
  4: "thigh",
  5: "shoulder",
  6: "sleeve", // upper and lower arms
};
