# Stage 6 Real-Logo Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove two club-ID-specific custom badge images and one untouched stock fallback on Android 10 without modifying stock club IDs or packed MapShield records.

**Architecture:** Rebuild only `classes3.dex` through pinned smali/baksmali, inserting two TEST-ONLY club-ID overrides after the stock `% 15` badge-style calculation. Patch stock `ShieldAnims.uih` by adding two raw `Img:` declarations and cloning each Design15 selector child into styles 16/17. Package, sign, install, navigate a deterministic fixture screen, and verify custom/fallback badge identity from captured frames and runtime logs.

**Tech Stack:** Python 3, Pillow, smali/baksmali 3.0.10 fat jars, Android SDK build-tools, adb, GitHub Actions API29 emulator.

**Spec:** `stage6_public/STAGE6_REAL_LOGO_RUNTIME_SPEC.md`

## Global Constraints

- Exact publisher-stock NSS 4.31 XAPK SHA-256: `afa4c3319e275de558da7a1c253dec84964094b0a4c1cb2ad557f53dbaf5b57e`.
- Exact stock base APK SHA-256: `46b5577b464b35c7122c3cf9737c6a7887ae28bb0911c7687b8b433ea6880aa4`.
- Do not modify numeric club IDs.
- Do not overwrite stock `MapShield*` atlas records.
- Preserve stock `% 15` style calculation for all non-target clubs.
- Runtime target: Android 10 / API 29 / x86_64 / Pixel 4.
- Test fixture only; no final copyrighted club artwork is required.

## Review Focus

- Smali patch must match exactly one `m_CreateClub` stock sequence and fail closed otherwise.
- Register use must not clobber values live after the badge-style assignment.
- Every `BadgeStyle1/2` selector variant must receive styles 16/17 using the same transform as its local Design15 entry.
- Raw PNG declarations must resolve from the packaged APK; missing images must fail before emulator launch.
- Fallback sample must remain stock procedural, not accidentally inherit one of the custom images.

---

### Task 1: Build deterministic Stage6 fixture patchers

**Files:**
- Create: `stage6_runtime/patch_club_badge_styles.py`
- Create: `stage6_runtime/patch_shield_ui.py`
- Create: `stage6_runtime/generate_fixture_badges.py`
- Test: `stage6_runtime/test_stage6_patchers.py`

**Interfaces:**
- `patch_club_badge_styles.py IN.smali OUT.smali` inserts ID 3141 -> 16 and ID 3163 -> 17 while keeping the stock path for every other ID.
- `patch_shield_ui.py IN.uih OUT.uih` adds `RebornBadge3141`/`RebornBadge3163` declarations and selector children 16/17.
- `generate_fixture_badges.py OUT_DIR` writes two visually distinct transparent PNGs with fixed dimensions.

- [ ] Write tests that assert exact one-site smali matching, two target overrides, unchanged fallback block, all selector blocks patched once, and idempotence refusal.
- [ ] Run tests and verify RED before implementations exist.
- [ ] Implement the three patchers minimally.
- [ ] Run tests and verify PASS.
- [ ] Commit.

### Task 2: Build and structurally verify the patched stock APK

**Files:**
- Create: `stage6_runtime/build_fixture_apk.sh`
- Create: `stage6_runtime/verify_fixture_apk.py`

**Interfaces:**
- Build script consumes exact stock XAPK plus pinned smali/baksmali fat jars and emits signed split APKs under a work directory.
- Verifier checks rebuilt `classes3.dex`, patched `ShieldAnims.uih`, both PNG members, stock club IDs, and untouched `MapShield*` Key.key bytes.

- [ ] Write verifier assertions first and run against unpatched stock to confirm failure.
- [ ] Download pinned smali 3.0.10 fat jars and verify published SHA-256 values before use.
- [ ] Disassemble/reassemble only `classes3.dex`, patch base APK members, zipalign/sign all installed splits.
- [ ] Run verifier and require all structural gates PASS.
- [ ] Commit.

### Task 3: Add Android 10 multi-club runtime gate

**Files:**
- Create: `stage6_runtime/runtime_logo_gate.sh`
- Create: `stage6_runtime/verify_runtime_evidence.py`
- Create: `.github/workflows/nss-stage6-real-logo-runtime.yml`

**Interfaces:**
- Runtime gate installs the signed fixture build, reaches deterministic club-shield surfaces, captures custom club 3141, custom club 3163, and one non-target fallback club.
- Runtime verifier emits `STAGE6_CUSTOM_3141=PASS`, `STAGE6_CUSTOM_3163=PASS`, `STAGE6_STOCK_FALLBACK=PASS`, `STAGE6_ATLAS_INTEGRITY=PASS`, and `STAGE6_REAL_LOGO_RUNTIME=PASS` only when image identity and crash guards all pass.

- [ ] Write evidence verifier tests for distinct custom hashes, fallback mismatch from custom fixtures, and crash/ANR refusal.
- [ ] Run verifier tests RED before runtime evidence exists.
- [ ] Implement runtime navigation/capture using existing Stage1/Stage5 public-safe coordinate and startup helpers where possible.
- [ ] Add pinned API29 workflow and artifact upload.
- [ ] Run workflow and diagnose any failure by layer: build -> install -> navigation -> image routing -> evidence.
- [ ] Require a green workflow and inspect the downloaded artifact before claiming closure.
- [ ] Commit.

### Task 4: Record Stage6 evidence without overclaiming

**Files:**
- Create or update in private source-of-truth repo only after runtime PASS: `docs/STAGE6_BADGE_LOGO_ARCHITECTURE.md`
- Update only after runtime PASS: `docs/REVERSE_ENGINEERING_9_STAGE.md`
- Update only after runtime PASS: `docs/REVERSE_ENGINEERING_100.md`
- Create only after runtime PASS: `baseline/STAGE6_REAL_LOGO_RUNTIME_EVIDENCE.json`

**Interfaces:**
- Documentation distinguishes verified stock architecture, TEST-ONLY two-ID override, and the future production mapping boundary.

- [ ] Verify artifact digest and final gate text.
- [ ] Record exact workflow/run/job/commit identities and structural/runtime evidence.
- [ ] Mark Etap 6 complete only if all five declared exit criteria are supported.
- [ ] Run repository documentation/guard tests available for the touched files.
- [ ] Commit.
