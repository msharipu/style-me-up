import {
  CIRCUMFERENCE_ZONES,
  defaultStretch,
  idealEase,
  looseTolerance,
  targetLength,
  tightTolerance,
} from "./ease";
import type {
  BodyMeasurements,
  ChartValue,
  FitPreference,
  FitReport,
  SizeChart,
  SizeResult,
  SizeRow,
  Verdict,
  Zone,
  ZoneResult,
} from "./types";

const ALL_ZONES: Zone[] = ["chest", "waist", "hip", "shoulder", "thigh", "sleeve", "length", "inseam"];

const WEIGHT: Record<Zone, number> = {
  chest: 3,
  waist: 3,
  hip: 3,
  shoulder: 2,
  thigh: 2,
  sleeve: 1,
  length: 1,
  inseam: 1,
};

/** Bottoms live or die by the waist. */
const BOTTOM_WAIST_WEIGHT = 4;
const BOTTOMS = new Set(["jeans", "trousers", "shorts", "skirt"]);

const BODY_KEY: Partial<Record<Zone, keyof BodyMeasurements>> = {
  chest: "chest",
  waist: "waist",
  hip: "hip",
  shoulder: "shoulder",
  thigh: "thigh",
};

export interface CheckOptions {
  preference?: FitPreference;
}

type Judged = Pick<ZoneResult, "verdict" | "heat" | "note" | "deviation">;

const clamp = (x: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, x));
const round1 = (x: number) => Math.round(x * 10) / 10;
const mid = (v: ChartValue) => (typeof v === "number" ? v : (v.min + v.max) / 2);

function isCircumference(zone: Zone) {
  return CIRCUMFERENCE_ZONES.includes(zone);
}

/** Converts a chart cell to a garment circumference/length in cm. */
function garmentValue(chart: SizeChart, zone: Zone, v: ChartValue): number {
  const m = mid(v);
  // Thigh on flat charts is usually leg opening width at the thigh, also doubled.
  return chart.flat && isCircumference(zone) ? m * 2 : m;
}

function judgeCircumference(
  zone: Zone,
  ease: number,
  range: { min: number; max: number },
  stretch: "none" | "some" | "high",
): Judged {
  const tTol = tightTolerance(zone, stretch);
  const lTol = looseTolerance(zone, range);
  // Charts and tapes are only good to about a centimetre; don't flag misses smaller than that.
  const grace = zone === "shoulder" ? 0.5 : 1;
  let verdict: Verdict = "right";
  let heat = 0;
  let deviation = 0;
  if (ease < range.min) {
    deviation = -(range.min - ease) / (tTol * 1.5);
    if (ease < range.min - grace) {
      verdict = ease < range.min - tTol ? "too-tight" : "snug";
      heat = -clamp(-deviation, 0.15, 1);
    }
  } else if (ease > range.max) {
    deviation = (ease - range.max) / (lTol * 1.5);
    if (ease > range.max + grace) {
      verdict = ease > range.max + lTol ? "too-loose" : "roomy";
      heat = clamp(deviation, 0.15, 1);
    }
  }
  const name = zone === "shoulder" ? "shoulders" : zone;
  const notes: Record<string, string> = {
    "too-tight": `Too small at the ${name}; likely won't fit.`,
    snug: `Snug at the ${name}.`,
    right: `Good fit at the ${name}.`,
    roomy: `Roomy at the ${name}.`,
    "too-loose": `Very loose at the ${name}.`,
  };
  return { verdict, heat, note: notes[verdict], deviation: clamp(deviation, -1, 1) };
}

function judgeLength(
  zone: Zone,
  delta: number,
  range: { min: number; max: number },
): Judged {
  const tol = 4;
  const grace = 1;
  let verdict: Verdict = "right";
  let heat = 0;
  let deviation = 0;
  if (delta < range.min) {
    deviation = -(range.min - delta) / (tol * 1.5);
    if (delta < range.min - grace) {
      verdict = delta < range.min - tol ? "too-short" : "short";
      heat = -clamp(-deviation, 0.15, 1);
    }
  } else if (delta > range.max) {
    deviation = (delta - range.max) / (tol * 3);
    if (delta > range.max + grace) {
      verdict = delta > range.max + tol * 2 ? "too-long" : "long";
      heat = clamp(deviation, 0.15, 1);
    }
  }
  const what = zone === "length" ? "Length" : zone === "sleeve" ? "Sleeves" : "Leg length";
  const hemmable = zone === "inseam" && (verdict === "long" || verdict === "too-long");
  const notes: Record<string, string> = {
    "too-short": `${what} too short.`,
    short: `${what} a little short.`,
    right: `${what} about right.`,
    long: hemmable ? "Legs a little long; easy to hem." : `${what} a little long.`,
    "too-long": hemmable ? "Legs long; needs hemming." : `${what} too long.`,
  };
  return { verdict, heat, note: notes[verdict], deviation: clamp(deviation, -1, 1) };
}

/** Body chart: the shop says which body each size is for. */
function judgeBodyChart(
  zone: Zone,
  body: number,
  v: ChartValue,
): Judged & Pick<ZoneResult, "ease" | "idealRange"> {
  const range = typeof v === "number" ? { min: v - 2, max: v + 2 } : v;
  // Positive ease = the size is meant for a bigger body than yours.
  const ease = mid(range) - body;
  let verdict: Verdict = "right";
  let heat = 0;
  let deviation = 0;
  if (body > range.max) {
    deviation = -(body - range.max) / 6;
    if (body > range.max + 1) {
      verdict = body > range.max + 4 ? "too-tight" : "snug";
      heat = -clamp(-deviation, 0.15, 1);
    }
  } else if (body < range.min) {
    deviation = (range.min - body) / 8;
    if (body < range.min - 1) {
      verdict = body < range.min - 5 ? "too-loose" : "roomy";
      heat = clamp(deviation, 0.15, 1);
    }
  }
  const name = zone === "shoulder" ? "shoulders" : zone;
  const notes: Record<string, string> = {
    "too-tight": `Made for a smaller ${name} than yours.`,
    snug: `Slightly small at the ${name}.`,
    right: `Your ${name} is in this size's range.`,
    roomy: `Slightly big at the ${name}.`,
    "too-loose": `Made for a bigger ${name} than yours.`,
  };
  return { verdict, heat, note: notes[verdict], deviation: clamp(deviation, -1, 1), ease: round1(ease), idealRange: range };
}

function zonePenalty(r: ZoneResult): number {
  // Smooth in the deviation, so a 0.3 cm miss costs almost nothing.
  // Too small hurts more than too big: big can be belted, hemmed or worn oversized.
  const d = r.deviation;
  return d < 0 ? 2 * d * d : d * d;
}

function checkSize(
  chart: SizeChart,
  row: SizeRow,
  body: BodyMeasurements,
  preference: FitPreference,
  missing: Set<Zone>,
): SizeResult {
  const stretch = chart.stretch ?? defaultStretch(chart.category);
  const zones: ZoneResult[] = [];

  for (const zone of ALL_ZONES) {
    const cell = row[zone];
    if (cell === undefined) continue;

    if (zone === "length" || zone === "sleeve" || zone === "inseam") {
      if (chart.kind === "body") continue; // body charts rarely carry garment lengths
      const g = garmentValue(chart, zone, cell);
      // A short sleeve is a style, not a misfit.
      if (zone === "sleeve" && body.arm && g < body.arm * 0.6) continue;
      const range = targetLength(zone, chart.category, body);
      if (!range) {
        if ((zone === "sleeve" && !body.arm) || (zone === "inseam" && !body.inseam)) missing.add(zone);
        continue;
      }
      const judged = judgeLength(zone, g, range);
      zones.push({ zone, ease: round1(g - (range.min + range.max) / 2), idealRange: range, ...judged });
      continue;
    }

    const key = BODY_KEY[zone]!;
    const b = body[key] as number | undefined;
    if (b === undefined) {
      missing.add(zone);
      continue;
    }

    if (chart.kind === "body") {
      zones.push({ zone, ...judgeBodyChart(zone, b, cell) });
      continue;
    }

    const range = idealEase(chart.category, zone, preference);
    if (!range) continue; // zone not meaningful for this category (e.g. hip on a tee)
    const ease = garmentValue(chart, zone, cell) - b;
    zones.push({ zone, ease: round1(ease), idealRange: range, ...judgeCircumference(zone, ease, range, stretch) });
  }

  let penalty = 0;
  for (const z of zones) {
    const w = z.zone === "waist" && BOTTOMS.has(chart.category) ? BOTTOM_WAIST_WEIGHT : WEIGHT[z.zone];
    penalty += w * zonePenalty(z);
  }
  // Too tight at a circumference means it may not go on; tight shoulders block unless the fabric is very stretchy.
  const blocking = zones.some(
    (z) => z.verdict === "too-tight" && (z.zone !== "shoulder" || stretch !== "high"),
  );
  return { label: row.label, zones, penalty: round1(penalty * 100) / 100, blocking };
}

/** Compare a garment's size chart with the user's body and pick the best size. */
export function checkFit(chart: SizeChart, body: BodyMeasurements, options: CheckOptions = {}): FitReport {
  if (!chart.sizes.length) throw new Error("Size chart has no sizes.");
  const preference = options.preference ?? "regular";
  const missing = new Set<Zone>();
  const sizes = chart.sizes.map((row) => checkSize(chart, row, body, preference, missing));

  // Length alone can't pick a size: need at least one key zone (chest, waist, hip, shoulder, thigh).
  const candidates = sizes.filter((s) => !s.blocking && s.zones.some((z) => WEIGHT[z.zone] >= 2));
  const best = candidates.reduce<SizeResult | null>(
    (acc, s) => (acc === null || s.penalty < acc.penalty ? s : acc),
    null,
  );

  const judgedZones = new Set(sizes.flatMap((s) => s.zones.map((z) => z.zone)));
  const keyZonesJudged = [...judgedZones].filter((z) => WEIGHT[z] >= 2).length;
  let confidence = 0;
  if (best) {
    // Two key zones (e.g. chest + shoulder, or waist + hip) give full coverage.
    const coverage = Math.min(1, keyZonesJudged / 2);
    const quality = 1 / (1 + best.penalty);
    // A clear winner is more trustworthy than a near tie.
    const others = candidates.filter((s) => s !== best).map((s) => s.penalty);
    const margin = others.length ? Math.min(1, (Math.min(...others) - best.penalty) / 2) : 1;
    confidence = round1((0.5 * coverage + 0.35 * quality + 0.15 * margin) * 100) / 100;
  }

  return {
    recommended: best?.label ?? null,
    confidence,
    sizes,
    missingBody: [...missing],
    summary: summarise(best, sizes, missing),
  };
}

function summarise(best: SizeResult | null, sizes: SizeResult[], missing: Set<Zone>): string {
  if (sizes.every((s) => !s.zones.some((z) => WEIGHT[z.zone] >= 2))) {
    return missing.size
      ? `Add your ${[...missing].join(", ")} measurement to check this item.`
      : "This size chart has no measurements we can compare.";
  }
  if (!best) {
    const allTight = sizes.every((s) => s.blocking);
    return allTight ? "Every listed size looks too small for you." : "No size fits well.";
  }
  const issues = best.zones.filter((z) => z.verdict !== "right");
  if (!issues.length) return `Size ${best.label} should fit you well.`;
  return `Size ${best.label} is your best fit. ${issues.map((z) => z.note).join(" ")}`;
}
