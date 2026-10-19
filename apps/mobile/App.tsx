import { Suspense, useMemo, useRef, useState } from "react";
import {
  PanResponder,
  Platform,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { StatusBar } from "expo-status-bar";
import { checkFit, type BodyMeasurements, type Zone } from "@stylemeup/fit-engine";
import { Avatar, CameraRig } from "./src/Avatar";
import { Canvas } from "./src/three/fiber";
import { heatToRgb, rgbToCss, VERDICT_LABEL } from "./src/heat";
import { SAMPLES } from "./src/samples";
import avatarInfo from "./assets/avatar.json";

const body = avatarInfo.measurements as BodyMeasurements;
const ZONE_NAME: Record<Zone, string> = {
  chest: "Chest",
  waist: "Waist",
  hip: "Hip",
  shoulder: "Shoulders",
  sleeve: "Sleeves",
  length: "Length",
  inseam: "Leg length",
  thigh: "Thigh",
};

export default function App() {
  const [garmentId, setGarmentId] = useState(SAMPLES[0].id);
  const garment = SAMPLES.find((g) => g.id === garmentId)!;
  const report = useMemo(() => checkFit(garment.chart, body), [garment]);
  const [picked, setPicked] = useState<string | null>(null);
  const sizeLabel = picked && report.sizes.some((s) => s.label === picked) ? picked : report.recommended ?? report.sizes[0].label;
  const size = report.sizes.find((s) => s.label === sizeLabel)!;

  const zoneHeat = useMemo(() => {
    const h: Partial<Record<Zone, number>> = {};
    for (const z of size.zones) h[z.zone] = z.heat;
    return h;
  }, [size]);

  // Drag horizontally to turn the avatar.
  const rotation = useRef(0);
  const start = useRef(0);
  const pan = useMemo(
    () =>
      PanResponder.create({
        onStartShouldSetPanResponder: () => true,
        onMoveShouldSetPanResponder: () => true,
        onPanResponderGrant: () => (start.current = rotation.current),
        onPanResponderMove: (_, g) => (rotation.current = start.current + g.dx * 0.012),
      }),
    [],
  );

  return (
    <SafeAreaView style={s.root}>
      <StatusBar style="dark" />
      <ScrollView contentContainerStyle={s.page}>
        <View style={s.header}>
          <Text style={s.brand}>Style Me Up!</Text>
          <Text style={s.sub}>
            Avatar {body.height} cm · chest {body.chest} · waist {body.waist} · hip {body.hip}
          </Text>
        </View>

        <View style={s.stage} {...pan.panHandlers}>
          <Canvas camera={{ position: [0, 0.9, 3.7], fov: 30 }} style={{ flex: 1 }}>
            <CameraRig />
            <hemisphereLight args={["#ffffff", "#b8b0a8", 1.4]} />
            <directionalLight position={[2, 4, 3]} intensity={1.6} />
            <directionalLight position={[-3, 2, -2]} intensity={0.5} />
            <Suspense fallback={null}>
              <Avatar source={require("./assets/avatar.glb")} zoneHeat={zoneHeat} rotation={rotation} />
            </Suspense>
          </Canvas>
          <Text style={s.hint}>Drag to turn</Text>
        </View>

        <Text style={s.label}>Item</Text>
        <View style={s.row}>
          {SAMPLES.map((g) => (
            <Chip key={g.id} active={g.id === garmentId} onPress={() => { setGarmentId(g.id); setPicked(null); }}>
              {g.name}
            </Chip>
          ))}
        </View>
        <Text style={s.caption}>{garment.shop}</Text>

        <Text style={s.label}>Size</Text>
        <View style={s.row}>
          {report.sizes.map((sz) => (
            <Chip key={sz.label} active={sz.label === sizeLabel} onPress={() => setPicked(sz.label)}>
              {sz.label}
              {sz.label === report.recommended ? "  ★" : ""}
            </Chip>
          ))}
        </View>

        <View style={s.card}>
          <Text style={s.summary}>
            {sizeLabel === report.recommended ? report.summary : `Size ${sizeLabel}: ${size.zones.filter((z) => z.verdict !== "right").map((z) => z.note).join(" ") || "fits well."}`}
          </Text>
          {size.zones.map((z) => (
            <View key={z.zone} style={s.zone}>
              <View style={[s.dot, { backgroundColor: rgbToCss(heatToRgb(z.heat)) }]} />
              <Text style={s.zoneName}>{ZONE_NAME[z.zone]}</Text>
              <Text style={s.zoneVerdict}>{VERDICT_LABEL[z.verdict]}</Text>
              <Text style={s.zoneEase}>
                {z.ease > 0 ? "+" : ""}
                {z.ease} cm
              </Text>
            </View>
          ))}
          <Text style={s.caption}>
            Confidence {Math.round(report.confidence * 100)}%
            {report.missingBody.length ? ` · add ${report.missingBody.join(", ")} to check more` : ""}
          </Text>
        </View>

        <View style={s.legend}>
          {[["Tight", -1], ["Right", 0], ["Loose", 1]].map(([l, h]) => (
            <View key={l as string} style={s.legendItem}>
              <View style={[s.dot, { backgroundColor: rgbToCss(heatToRgb(h as number)) }]} />
              <Text style={s.caption}>{l}</Text>
            </View>
          ))}
        </View>
        <Text style={s.footer}>Phase 0 prototype · avatar fitted with Anny (Apache 2.0)</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

function Chip({ active, onPress, children }: { active: boolean; onPress: () => void; children: React.ReactNode }) {
  return (
    <Pressable onPress={onPress} style={[s.chip, active && s.chipActive]}>
      <Text style={[s.chipText, active && s.chipTextActive]}>{children}</Text>
    </Pressable>
  );
}

const INK = "#1F1B18";
const QUIET = "#6E655D";
const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: "#F6F2EE" },
  page: { padding: 16, paddingBottom: 40, width: "100%", maxWidth: 520, alignSelf: "center" },
  header: { marginBottom: 8 },
  brand: { fontSize: 26, fontWeight: "800", color: INK, letterSpacing: -0.5 },
  sub: { fontSize: 13, color: QUIET, marginTop: 2 },
  stage: {
    height: 420,
    borderRadius: 20,
    backgroundColor: "#EAE3DC",
    overflow: "hidden",
    marginVertical: 12,
    ...(Platform.OS === "web" ? ({ cursor: "grab", touchAction: "none" } as object) : {}),
  },
  hint: { position: "absolute", bottom: 10, alignSelf: "center", fontSize: 12, color: QUIET },
  label: { fontSize: 12, fontWeight: "700", color: QUIET, textTransform: "uppercase", letterSpacing: 0.8, marginTop: 12, marginBottom: 6 },
  row: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  chip: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 999, borderWidth: 1, borderColor: "#D6CCC2", backgroundColor: "#FFFFFF" },
  chipActive: { backgroundColor: INK, borderColor: INK },
  chipText: { fontSize: 14, color: INK, fontWeight: "600" },
  chipTextActive: { color: "#FFFFFF" },
  caption: { fontSize: 12, color: QUIET, marginTop: 6 },
  card: { backgroundColor: "#FFFFFF", borderRadius: 16, padding: 16, marginTop: 16, gap: 10 },
  summary: { fontSize: 15, color: INK, lineHeight: 21, fontWeight: "600" },
  zone: { flexDirection: "row", alignItems: "center", gap: 10 },
  dot: { width: 12, height: 12, borderRadius: 6 },
  zoneName: { fontSize: 14, color: INK, width: 90 },
  zoneVerdict: { fontSize: 14, color: INK, flex: 1, fontWeight: "600" },
  zoneEase: { fontSize: 13, color: QUIET, fontVariant: ["tabular-nums"] },
  legend: { flexDirection: "row", gap: 16, marginTop: 14, justifyContent: "center" },
  legendItem: { flexDirection: "row", alignItems: "center", gap: 6 },
  footer: { fontSize: 11, color: QUIET, textAlign: "center", marginTop: 20 },
});
