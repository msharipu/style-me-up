/** All lengths are centimetres. */

/** Zones the engine knows how to judge. */
export type Zone =
  | "chest"
  | "waist"
  | "hip"
  | "shoulder"
  | "sleeve"
  | "length"
  | "inseam"
  | "thigh";

/** The user's body, as measured on the avatar or with a tape. */
export interface BodyMeasurements {
  height: number;
  chest?: number;
  waist?: number;
  hip?: number;
  /** Shoulder width, seam to seam across the back. */
  shoulder?: number;
  /** Shoulder point to wrist. */
  arm?: number;
  /** Crotch to floor. */
  inseam?: number;
  /** Thigh circumference at the fullest point. */
  thigh?: number;
  /** Back of neck (C7) to waist line; used for top length. */
  torsoLength?: number;
}

export type GarmentCategory =
  | "tee"
  | "shirt"
  | "knit"
  | "jacket"
  | "dress"
  | "jeans"
  | "trousers"
  | "shorts"
  | "skirt";

export type FitPreference = "slim" | "regular" | "relaxed";

/**
 * How the shop wrote its size chart.
 * - "garment": measurements of the garment itself (most Shopee, Taobao, Lazada listings).
 * - "body": the body the size is meant for (most brand charts, e.g. "chest 88–92").
 */
export type ChartKind = "garment" | "body";

/** A value, or a range like 88–92 that body charts often use. */
export type ChartValue = number | { min: number; max: number };

export interface SizeRow {
  /** Label shown to the user, e.g. "M", "32", "EU 40". */
  label: string;
  chest?: ChartValue;
  waist?: ChartValue;
  hip?: ChartValue;
  shoulder?: ChartValue;
  sleeve?: ChartValue;
  length?: ChartValue;
  inseam?: ChartValue;
  thigh?: ChartValue;
}

export interface SizeChart {
  kind: ChartKind;
  category: GarmentCategory;
  /**
   * True when circumference zones are laid-flat widths (pit-to-pit, waist across).
   * They are doubled before comparison. Ignored for body charts.
   */
  flat?: boolean;
  /** Fabric stretch: "none" for woven cotton/denim, "some" for 1–3% elastane, "high" for knits/jersey. */
  stretch?: "none" | "some" | "high";
  sizes: SizeRow[];
}

/** Ordered from too small to too big. */
export type Verdict =
  | "too-tight"
  | "snug"
  | "right"
  | "roomy"
  | "too-loose"
  /** Length zones use these instead of tight/loose. */
  | "too-short"
  | "short"
  | "long"
  | "too-long";

export interface ZoneResult {
  zone: Zone;
  verdict: Verdict;
  /** Garment minus body, in cm (for length zones: garment minus target length). */
  ease: number;
  /** The ease range the engine considered "right" for this zone. */
  idealRange: { min: number; max: number };
  /** -1 (far too small) … 0 (ideal) … +1 (far too big); drives the heatmap colour. 0 whenever verdict is "right". */
  heat: number;
  /** Continuous version of heat without the 1 cm grace band; used to rank sizes. */
  deviation: number;
  note: string;
}

export interface SizeResult {
  label: string;
  zones: ZoneResult[];
  /** Lower is better. */
  penalty: number;
  /** True when any circumference zone is "too-tight" — the garment may not go on. */
  blocking: boolean;
}

export interface FitReport {
  recommended: string | null;
  /** 0–1. Low when few zones could be compared or the best size is still a compromise. */
  confidence: number;
  sizes: SizeResult[];
  /** Zones in the chart that could not be judged because the body measurement is missing. */
  missingBody: Zone[];
  summary: string;
}
