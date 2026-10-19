import { describe, expect, it } from "vitest";
import { checkFit, type BodyMeasurements, type SizeChart } from "../src";

// A typical 175 cm man: chest 96, waist 82, hip 96.
const romi: BodyMeasurements = {
  height: 175,
  chest: 96,
  waist: 82,
  hip: 96,
  shoulder: 45,
  arm: 60,
  inseam: 80,
  thigh: 56,
};

// Shopee-style tee chart: laid-flat widths, garment measurements.
const shopeeTee: SizeChart = {
  kind: "garment",
  category: "tee",
  flat: true,
  sizes: [
    { label: "S", chest: 48, length: 68, shoulder: 42 },
    { label: "M", chest: 52, length: 71, shoulder: 44.5 },
    { label: "L", chest: 55, length: 73, shoulder: 47 },
    { label: "XL", chest: 58, length: 75, shoulder: 49 },
  ],
};

describe("garment charts", () => {
  it("picks M for a 96 cm chest on a flat tee chart", () => {
    const r = checkFit(shopeeTee, romi);
    expect(r.recommended).toBe("M");
    const m = r.sizes.find((s) => s.label === "M")!;
    expect(m.zones.find((z) => z.zone === "chest")!.verdict).toBe("right"); // 104 - 96 = 8 ease
    expect(m.zones.find((z) => z.zone === "chest")!.ease).toBe(8);
  });

  it("doesn't let a sub-centimetre miss push the pick a size up (regression)", () => {
    // Fitted avatar: chest 96.3 → M's ease is 7.7, 0.3 cm under the ideal 8.
    const avatar = { ...romi, chest: 96.3, shoulder: 43.9 };
    const r = checkFit(shopeeTee, avatar);
    expect(r.recommended).toBe("M");
    expect(r.sizes[1].zones.find((z) => z.zone === "chest")!.verdict).toBe("right");
  });

  it("doubles flat widths before comparing", () => {
    const s = checkFit(shopeeTee, romi).sizes.find((x) => x.label === "S")!;
    expect(s.zones.find((z) => z.zone === "chest")!.ease).toBe(0); // 96 - 96
  });

  it("goes a size up for a relaxed preference", () => {
    expect(checkFit(shopeeTee, romi, { preference: "relaxed" }).recommended).toBe("L");
  });

  it("flags every size too small for a much bigger body", () => {
    const big = { ...romi, chest: 130, shoulder: 52 };
    const r = checkFit({ ...shopeeTee, stretch: "none" }, big);
    expect(r.recommended).toBeNull();
    expect(r.summary).toMatch(/too small/);
  });

  it("treats stretchy fabric as more forgiving", () => {
    const chart: SizeChart = { kind: "garment", category: "knit", sizes: [{ label: "One", chest: 90 }] };
    const woven = checkFit({ ...chart, stretch: "none" }, romi);
    const stretchy = checkFit({ ...chart, stretch: "high" }, romi);
    expect(woven.sizes[0].zones[0].verdict).toBe("too-tight"); // ease -6, tolerance 2
    expect(stretchy.sizes[0].zones[0].verdict).toBe("snug"); // tolerance 8
  });
});

describe("bottoms", () => {
  const jeans: SizeChart = {
    kind: "garment",
    category: "jeans",
    stretch: "some",
    sizes: [
      { label: "30", waist: 78, hip: 96, inseam: 78 },
      { label: "32", waist: 83, hip: 100, inseam: 80 },
      { label: "34", waist: 88, hip: 105, inseam: 80 },
    ],
  };

  it("chooses the waist that fits over a closer hip", () => {
    const r = checkFit(jeans, romi);
    expect(r.recommended).toBe("32");
    expect(r.sizes[0].zones.find((z) => z.zone === "waist")!.verdict).not.toBe("right");
  });

  it("says long legs can be hemmed", () => {
    const shortLegs = { ...romi, inseam: 72 };
    const z = checkFit(jeans, shortLegs).sizes[1].zones.find((x) => x.zone === "inseam")!;
    expect(z.verdict).toMatch(/long/);
    expect(z.note).toMatch(/hem/);
  });
});

describe("body charts", () => {
  const brand: SizeChart = {
    kind: "body",
    category: "shirt",
    sizes: [
      { label: "S", chest: { min: 86, max: 91 }, waist: { min: 72, max: 77 } },
      { label: "M", chest: { min: 92, max: 97 }, waist: { min: 78, max: 83 } },
      { label: "L", chest: { min: 98, max: 103 }, waist: { min: 84, max: 89 } },
    ],
  };

  it("matches the size whose range contains the body", () => {
    const r = checkFit(brand, romi);
    expect(r.recommended).toBe("M");
    expect(r.sizes[1].zones.every((z) => z.verdict === "right")).toBe(true);
    expect(r.summary).toBe("Size M should fit you well.");
  });

  it("calls a smaller size snug, not right", () => {
    const s = checkFit(brand, romi).sizes[0];
    expect(s.zones.find((z) => z.zone === "chest")!.verdict).toBe("too-tight"); // 96 vs max 91
  });
});

describe("missing data", () => {
  it("asks for the missing measurement", () => {
    const r = checkFit(shopeeTee, { height: 175 });
    expect(r.recommended).toBeNull();
    expect(r.missingBody).toContain("chest");
    expect(r.summary).toMatch(/Add your/);
  });

  it("has lower confidence with only one zone", () => {
    const only = checkFit({ ...shopeeTee, sizes: shopeeTee.sizes.map(({ label, chest }) => ({ label, chest })) }, romi);
    const full = checkFit(shopeeTee, romi);
    expect(only.confidence).toBeLessThan(full.confidence);
  });

  it("ignores short sleeves", () => {
    const chart: SizeChart = { kind: "garment", category: "shirt", flat: true, sizes: [{ label: "M", chest: 54, sleeve: 22 }] };
    expect(checkFit(chart, romi).sizes[0].zones.map((z) => z.zone)).toEqual(["chest"]);
  });

  it("rejects an empty chart", () => {
    expect(() => checkFit({ kind: "garment", category: "tee", sizes: [] }, romi)).toThrow();
  });
});

describe("heatmap values", () => {
  it("are 0 for right, negative for tight, positive for loose, within ±1", () => {
    const r = checkFit(shopeeTee, romi);
    for (const s of r.sizes)
      for (const z of s.zones) {
        expect(z.heat).toBeGreaterThanOrEqual(-1);
        expect(z.heat).toBeLessThanOrEqual(1);
        if (z.verdict === "right") expect(z.heat).toBe(0);
        if (z.verdict === "snug" || z.verdict === "too-tight") expect(z.heat).toBeLessThan(0);
        if (z.verdict === "roomy" || z.verdict === "too-loose") expect(z.heat).toBeGreaterThan(0);
      }
  });
});
