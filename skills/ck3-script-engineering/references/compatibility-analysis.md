# CK3 compatibility analysis

Do not reduce compatibility to same-file collisions.

## Collision classes

1. `FILE COLLISION` — multiple mods replace the same path.
2. `KEY COLLISION` — the same database key/definition is redefined, even from different files.
3. `SEMANTIC COLLISION` — definitions differ in assumptions, side effects, state ownership, or invariants without a direct key collision.
4. `CALLER/CALLEE COLLISION` — one mod changes a callee while another caller assumes vanilla/older behavior.
5. `LOAD-ORDER DEPENDENCY` — observed behavior depends on override order or registration order.
6. `GUI OVERRIDE COLLISION` — template/widget/blockoverride ownership intersects.
7. `LOCALIZATION COLLISION` — same localization key changes visible meaning or hides a compatibility issue.

## Analysis workflow

Map each mod's changed paths, definition keys, callers/consumers, persistent state, and full-file overrides. Build a directed dependency graph instead of only a filename intersection.

For each collision state:

- active winner by load order when determinable;
- behaviors lost from each side;
- callers that now receive changed semantics;
- minimum merge/compatibility patch;
- required runtime scenario.

If source inspection cannot decide the live winner or behavior, use `$ck3-runtime-probe` with a minimal discriminating test.
