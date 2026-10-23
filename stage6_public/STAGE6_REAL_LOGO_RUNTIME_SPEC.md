# Stage 6 Real-Logo Runtime Proof

## Intent

Prove on exact publisher-stock NSS 4.31 that club identity can select an exact custom badge without destroying the stock procedural fallback system.

## Verified stock facts

- `c_TClub.m_CreateClub` derives badge colours from the home shirt colours.
- `c_TClub.m_CreateClub` derives the procedural badge style from `club_id % 15`.
- `c_TScreen_ClubFixtures.m_SetUpTeamShield` copies team `m_badgecol1`, `m_badgecol2`, and `m_badgestyle` into `MatchColours/Badge1Col1`, `Badge1Col2`, and `BadgeStyle1`.
- `ShieldAnims.uih` selects a plain shield plus `MapShieldDesign1..15` from `BadgeStyle1/2`.
- Stock `MapShield*` records are packed `flag 0x8` stripped-triangle atlas records and must not be overwritten as rectangular atlas crops.
- `ShieldAnims.uih` already uses `Img:(Symbol,path.png)` declarations, including declarations without a `Pack:` suffix.

## Runtime fixture architecture

The proof uses a TEST-ONLY smali patch to preserve stock behavior for every non-target club while assigning two target club IDs to new selector values:

- club `3141` -> `BadgeStyle=16`
- club `3163` -> `BadgeStyle=17`
- every other club -> unchanged stock `club_id % 15`

`ShieldAnims.uih` is patched by duplicating the existing `MapShieldDesign15` draw transform in every `BadgeStyle1/2` selector and replacing only the symbol name for the two new children. Two raw PNG fixture badges are declared through new `Img:` lines and added under `assets/monkey/NewGUI/RebornBadges/`.

The fixture badges are deliberately synthetic test assets, not final club artwork. They prove the routing and fallback architecture; final artwork can replace them without changing the mechanism.

## Runtime proof

Android 10 / API 29 must demonstrate in one signed test build:

1. club 3141 resolves to fixture badge A;
2. club 3163 resolves to fixture badge B;
3. a non-target club retains its stock procedural shield;
4. the two fixture badge images remain visually distinct and are not replaced by atlas corruption;
5. no NSS fatal exception, ANR, or process death is observed during the sample.

## Safety boundary

- Numeric club IDs are not changed.
- Stock `MapShield*` atlas records are not modified.
- Stock style values `0..15` remain available unchanged.
- The hard-coded two-club mapping exists only in the public runtime proof branch.
- A production-scale mapping will be generated from a dedicated club-ID -> logo-index data source after the runtime mechanism is proven.
