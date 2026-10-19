import type { FitPreference, GarmentCategory, Zone } from "./types";

/**
 * "Right" ease ranges (garment minus body, cm) for a regular fit.
 * Sources: standard pattern-making ease allowances for wovens and knits,
 * kept deliberately simple for the Phase 0 prototype. Tune with beta data.
 */
type Range = { min: number; max: number };
type EaseTable = Partial<Record<Zone, Range>>;

const REGULAR: Record<GarmentCategory, EaseTable> = {
  tee: { chest: { min: 8, max: 14 }, waist: { min: 8, max: 18 }, shoulder: { min: -1, max: 2.5 } },
  shirt: { chest: { min: 10, max: 16 }, waist: { min: 10, max: 20 }, shoulder: { min: -0.5, max: 2 } },
  knit: { chest: { min: 2, max: 8 }, waist: { min: 2, max: 10 }, shoulder: { min: -1.5, max: 2.5 } },
  jacket: { chest: { min: 12, max: 20 }, waist: { min: 12, max: 22 }, shoulder: { min: 0, max: 2.5 } },
  dress: { chest: { min: 4, max: 10 }, waist: { min: 2, max: 10 }, hip: { min: 4, max: 12 } },
  jeans: { waist: { min: 0, max: 4 }, hip: { min: 2, max: 8 }, thigh: { min: 3, max: 10 } },
  trousers: { waist: { min: 1, max: 4 }, hip: { min: 4, max: 10 }, thigh: { min: 5, max: 12 } },
  shorts: { waist: { min: 1, max: 4 }, hip: { min: 4, max: 12 }, thigh: { min: 6, max: 16 } },
  skirt: { waist: { min: 1, max: 3 }, hip: { min: 4, max: 10 } },
};

/** Waist on bottoms must sit on the body; preference doesn't loosen it. */
const PREFERENCE_LOCKED: Partial<Record<GarmentCategory, Zone[]>> = {
  jeans: ["waist"],
  trousers: ["waist"],
  shorts: ["waist"],
  skirt: ["waist"],
};

export const CIRCUMFERENCE_ZONES: Zone[] = ["chest", "waist", "hip", "thigh"];
export const LENGTH_ZONES: Zone[] = ["length", "sleeve", "inseam"];

export function idealEase(
  category: GarmentCategory,
  zone: Zone,
  preference: FitPreference,
): Range | undefined {
  const base = REGULAR[category][zone];
  if (!base) return undefined;
  if (preference === "regular" || PREFERENCE_LOCKED[category]?.includes(zone)) {
    return { ...base };
  }
  const width = base.max - base.min;
  if (preference === "slim") {
    const shift = 0.5 * width;
    return { min: base.min - shift, max: base.max - shift };
  }
  return { min: base.min + 0.3 * width, max: base.max + 1.0 * width };
}

/** How far below the ideal minimum a zone can go before it stops fitting, by fabric stretch. */
export function tightTolerance(zone: Zone, stretch: "none" | "some" | "high"): number {
  if (zone === "shoulder") return stretch === "high" ? 3 : 1.5;
  return { none: 2, some: 4, high: 8 }[stretch];
}

/** How far above the ideal maximum a zone can go before it reads as "too loose". */
export function looseTolerance(zone: Zone, range: Range): number {
  if (zone === "shoulder") return 3;
  return Math.max(6, range.max - range.min);
}

/** Default stretch when the shop doesn't say. */
export function defaultStretch(category: GarmentCategory): "none" | "some" | "high" {
  if (category === "tee" || category === "knit") return "high";
  if (category === "jeans" || category === "trousers" || category === "dress") return "some";
  return "none";
}

/** Rough target garment lengths from height, used only when the shop gives a length. */
export function targetLength(
  zone: "length" | "sleeve" | "inseam",
  category: GarmentCategory,
  body: { height: number; arm?: number; inseam?: number },
): Range | undefined {
  if (zone === "length") {
    // Top length from high shoulder point. Ratios fitted to common SEA/Asian size charts.
    const ratio = { tee: 0.41, shirt: 0.43, knit: 0.4, jacket: 0.42 }[category as "tee"];
    if (!ratio) return undefined;
    const t = body.height * ratio;
    return { min: t - 3, max: t + 3 };
  }
  if (zone === "sleeve") {
    if (!body.arm || !["shirt", "jacket", "knit"].includes(category)) return undefined;
    return { min: body.arm - 1, max: body.arm + 3 };
  }
  if (!body.inseam || !["jeans", "trousers"].includes(category)) return undefined;
  return { min: body.inseam - 4, max: body.inseam + 1 };
}
