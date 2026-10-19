import type { SizeChart } from "@stylemeup/fit-engine";

/** Sample listings the way shops write them, for the Phase 0 demo. */
export interface SampleGarment {
  id: string;
  name: string;
  shop: string;
  chart: SizeChart;
}

export const SAMPLES: SampleGarment[] = [
  {
    id: "tee",
    name: "Cotton crew tee",
    shop: "Shopee-style chart · laid-flat cm",
    chart: {
      kind: "garment",
      category: "tee",
      flat: true,
      sizes: [
        { label: "S", chest: 48, length: 68, shoulder: 42 },
        { label: "M", chest: 52, length: 71, shoulder: 44.5 },
        { label: "L", chest: 55, length: 73, shoulder: 47 },
        { label: "XL", chest: 58, length: 75, shoulder: 49 },
      ],
    },
  },
  {
    id: "shirt",
    name: "Oxford shirt",
    shop: "Brand chart · body measurements",
    chart: {
      kind: "body",
      category: "shirt",
      sizes: [
        { label: "S", chest: { min: 86, max: 91 }, waist: { min: 72, max: 77 } },
        { label: "M", chest: { min: 92, max: 97 }, waist: { min: 78, max: 83 } },
        { label: "L", chest: { min: 98, max: 103 }, waist: { min: 84, max: 89 } },
        { label: "XL", chest: { min: 104, max: 110 }, waist: { min: 90, max: 96 } },
      ],
    },
  },
  {
    id: "jeans",
    name: "Slim stretch jeans",
    shop: "Taobao-style chart · garment cm",
    chart: {
      kind: "garment",
      category: "jeans",
      stretch: "some",
      sizes: [
        { label: "28", waist: 73, hip: 92, thigh: 54, inseam: 76 },
        { label: "30", waist: 78, hip: 96, thigh: 57, inseam: 78 },
        { label: "32", waist: 83, hip: 100, thigh: 60, inseam: 80 },
        { label: "34", waist: 88, hip: 105, thigh: 63, inseam: 80 },
        { label: "36", waist: 93, hip: 110, thigh: 66, inseam: 81 },
      ],
    },
  },
];
