# Style Me Up!

Measurement-accurate 3D avatars, a size-chart fit check that works with any shop, and (from Phase 2) community rating of fit and style. Web, iOS and Android from one codebase. SEA-first.

Plan: [Project plan & tech stack](https://claude.ai/code/artifact/366148b2-0f44-4fda-8228-9d99e05c29c9) · Backlog: [Linear project](https://linear.app/maliffromi/project/style-me-up-08848d9dc857)

## Repository

| Path | What it is | Stack |
| --- | --- | --- |
| `packages/fit-engine` | Compares a garment size chart with a body and picks a size, with a verdict per zone (tight / right / loose) | TypeScript, Vitest |
| `apps/mobile` | The app: avatar viewer with fit heatmap and sample garments | Expo SDK 58, React Native, React Three Fiber, three.js |
| `spike/body-fit` | Phase 0 spike: fits the Anny body model to tape measurements and exports the avatar GLB | Python, PyTorch, Anny (Apache 2.0) |
| `docs` | Phase 0 findings | Markdown |

## Run it

```bash
# Fit-check engine tests
cd packages/fit-engine && npm install && npm test

# App (web on your computer; scan the QR code with Expo Go for iPhone/Android)
cd apps/mobile && npm install && npx expo start

# Make an avatar from measurements (first run downloads PyTorch, ~3 GB; CPU is fine)
cd spike/body-fit
pip install anny trimesh shapely scipy pygltflib matplotlib
python3 make_avatar.py --sex male --age 32 --height 175 --chest 96 --waist 82 --hip 96 \
  --thigh 56 --inseam 80 --shoulder 45 --arm 60 --weight 70 --out ../../apps/mobile/assets/avatar

# Accuracy benchmark on 40 synthetic adults (about 1 hour on 2 CPU cores)
python3 benchmark.py --shard 0 --of 2 & python3 benchmark.py --shard 1 --of 2; python3 report.py
```

## How the body fit works

1. **Anny** (NAVER LABS, Apache 2.0) generates a body from interpretable controls: sex, age, muscle, weight, height, proportions, plus MakeHuman shape targets for bust, waist, hips, thigh, shoulders and limb lengths.
2. A **virtual tape measure** cuts the mesh with horizontal planes at tailor landmarks (under the armpits, natural waist, fullest buttock point, just below the crotch) and takes the convex-hull perimeter, as a tape would. Loops are separated by mesh connectivity, so an arm resting on the torso never counts toward the chest.
3. **SciPy least squares** adjusts the controls until the tape readings match the user's, in three stages: global shape, local shape (lightly regularised to stay natural), and a correction pass against the exact tape measure.
4. The result is exported as a **GLB** with a `_ZONE` vertex attribute, so the app can colour chest, waist, hip, thigh, shoulders and arms by fit verdict.

## Licences to keep clean

- Anny body model: Apache 2.0, fine for commercial use.
- Do **not** use SMPL / SMPL-X, CatVTON or IDM-VTON in production: their licences are non-commercial.
- SAM 3D Body (photo → body, MAL-9): Meta SAM License, which allows commercial use with use restrictions. The weights are gated; accept the licence on Hugging Face first.
