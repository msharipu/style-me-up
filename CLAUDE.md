# Style Me Up! — working notes for Claude

Romi is vibe-coding this project: Claude writes, runs and tests all code; Romi makes product decisions and does only what needs a real person (sign-ups, device testing, his own measurements). Explain results in plain language, not code.

## Where things are
- Plan & tech stack (doc): https://claude.ai/code/artifact/366148b2-0f44-4fda-8228-9d99e05c29c9
- Phase 0 findings + gate recommendation (doc): https://claude.ai/code/artifact/419a8aba-c393-4987-8e2a-dee534b485f6
- Web prototype: https://claude.ai/artifact/VxHQhEKEe34nBQpNMDpfxv
- Linear: project "Style Me Up!" (P-MAL-1), team Maliffromi, issues MAL-5 onward. Labels: "Claude builds", "Needs Romi".
- claude.ai Project "Style Me Up!" docs: claude/phase-0-status.md (handoff), claude/competitive-landscape.md

## Status (20 Oct 2026)
Phase 0 is done; Phase 1 (MVP) is next.
- Tape path proven on real people: ANSUR II, 60 people (half Asian), 60/60 within 2 cm on chest, navel waist, hip; mean error 0.16 / 0.15 / 0.33 cm.
- Photo path not good enough: BodyM silhouettes, 87 people, 0/87 within the gate (chest +7.6 cm, hip −5.1 cm mean). Research track MAL-13.
- **Working assumption for Phase 1: tape-first MVP.** Input = height + chest, waist, hip from a tape (thigh, inseam optional); photos optional for looks; height+weight-only users get a low-confidence size guess. Romi had not explicitly confirmed this when Phase 0 closed: confirm it at the start of Phase 1 (MAL-11).

Open Phase 0 leftovers: MAL-7 (run the app on a real phone), MAL-8 (Romi's self-test), MAL-10 (try-on API trial, needs a FASHN key), MAL-11 (gate sign-off), MAL-12 (waist rule for torsos with no narrowing, inseam weighting).

## Repo
| Path | What | Run |
| --- | --- | --- |
| packages/fit-engine | TypeScript: size chart vs body → verdict per zone + recommended size | `npm install && npm test` (15 tests) |
| apps/mobile | Expo SDK 58, React Native 0.88, React Three Fiber 9.8, three 0.186; avatar viewer with fit heatmap | `npm install && npx expo start`; web build `CI=1 EXPO_OFFLINE=1 npx expo export --platform web` |
| spike/body-fit | Python: Anny body model fitted to measurements, virtual tape, GLB export, benchmarks | `pip install anny trimesh shapely scipy pygltflib matplotlib` |

Key spike files: body.py (Anny wrapper), measure.py / fast_measure.py (virtual tape), fit.py (3-stage fit), export.py + make_avatar.py (GLB with `_ZONE` attribute), benchmark.py `--set synthetic|ansur`, report.py, ansur.py, bodym.py + bodym_benchmark.py, silhouette.py.

## Rules and gotchas
- Licences: Anny is Apache 2.0 (fine commercially). Never use SMPL/SMPL-X, CatVTON or IDM-VTON in the product. BodyM is treated as non-commercial: evaluation only, never committed (gitignored) and never trained on. ANSUR II is public domain and is committed at spike/body-fit/data/ansur_ii.csv.
- Photos of real people never go in the repo.
- Two waist definitions: `waist` = narrowest point (tailor); `waist_navel` = navel level (ANSUR, and the rule for torsos with no narrowing).
- Anny rest pose: Z up, +Y towards the back, metres; adult age parameter ≈ 0.70.
- `@react-three/native` is not on npm; use `@react-three/fiber/native` with expo-gl. R3F cameras look at the origin, so use `CameraRig` to aim at the avatar.
- Workspace network: npm, PyPI, GitHub, calmcode.io and the BodyM S3 bucket are reachable; huggingface.co, download.pytorch.org and api.expo.dev are blocked (use `EXPO_OFFLINE=1`). PyTorch installs from PyPI (~3 GB).
- Live benchmark output (`results*/benchmark_*.jsonl`) is gitignored; commit `summary.json` files only. Benchmarks take 1–2 min per person on CPU: run in the background.
- Commit and push after each piece of work; the Claude GitHub App is installed on msharipu/style-me-up.
