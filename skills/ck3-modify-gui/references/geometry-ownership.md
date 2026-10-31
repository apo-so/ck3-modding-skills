# Geometry ownership graph

Binding ownership answers **where data comes from**. Geometry ownership answers **where rendered space comes from**. Both are required for layout diagnosis.

## Owner ledger

For every nontrivial target widget/pane, record:

```text
node / role
x placement owner
y placement owner
width owner
height owner
expand consumer
first shared flow parent
competing siblings
spacing/padding owner
clip owner
scroll owner
outer allocation contract
inner content envelope
frozen status
```

Do not infer owner placement from glyph alignment. `align = left` can align text inside a text owner while the owner itself remains centered, fixed-width, or displaced by sibling allocation.

## Shared allocation

For a local repair, find the first ancestor where the target and an already accepted sibling compete for width/height. Freeze that shared allocation unless the task explicitly authorizes a multi-pane redesign.

Changing a target pane from expanding to fixed width is not local merely because the textual diff is inside that pane: it changes the space available to siblings.

## Outer versus inner geometry

Separate:

- outer allocation: how much space the parent gives the pane;
- inner content envelope: how children consume that space;
- glyph alignment: how text/images align within their immediate owner.

Prefer repairing the deepest incorrect inner owner while preserving an accepted outer allocation.

## Runtime receipt

A static geometry graph predicts risk; only rendered evidence proves visual realization. Record target resolution/UI scale, screenshot build ID, visible clipping/truncation/dead space, and whether every frozen region remained accepted.

## Cross-file background owners and shared-surface regression

Trace separate local frame/background and native HUD backdrop owners. A655-unit full-height native sidebar behind a474-unit custom frame can expose a wide blank strip; fitting the custom frame and content to the native allocation is the default repair. Preserve shared native backgrounds and their original visibility.

Rejected CN4 route, CK3 1.20.1.2: hiding sidebar_background_right using NOT(custom panel script/page predicate) made the custom screenshot look aligned, but the user later observed the native Military sidebar transparent. The persistent map/page state did not prove the custom window exclusively owned the foreground. Source-equivalent behavior outside that predicate did not cover real native-window transitions. The prior narrow screenshot success is superseded by this observed regression; do not repeat or recommend this route.

CN5 restored vanilla and retired the extra HUD override, but the user rejected its widened620-unit frame as wider than the bottom frame. The620+35=655 arithmetic did not prove visible alignment. Mark that width decision rejected; do not retain it as a recommended dimension. Compare the actual visible top/bottom decoration spans, local background, native body and bottom HUD separately, including rails, sprite alpha and template margins. Keep an explicit inner inset and preserve the shared native surfaces. CN6 proposes an inward adjustment; its source dimensions are not a universal preset or user acceptance. Record actual-frame observations and user acceptance separately.

## Native main-tab shell before pixel adjustments

CN6's inward nudges were also rejected by the user. CN5/CN6 numeric width recommendations are failed approaches for this shared-sidebar case. The missed cause was a structural mismatch: the CMM view owned a second compact background plus red Window_Decoration while native main-tab content uses the shared HUD background.

Current1.20.1.2 sources: window_military.gui lines5–44 and window_council.gui lines5–41 use Window_Size_MainTab, margin_widget with top30/bottom25/right13, inner widget100%, then Window_Margins. window_situation.gui lines4–40 uses the same root and margins26 vertically/right13. shared/windows.gui defines MainTab655×100%, position0/0, and content margins left40/right40/top18/bottom20. CMM's content562 is derived from that specific655-13-40-40 shell, not a universal hardcoded preset. Keep fixed viewport and fixed data rows inside it. The main roots do not need a second compact frame; unrelated popup roots in the same source file do have their own backgrounds. Inspect owner scope, not a whole-file grep hit. Do not alter the shared HUD to compensate for the custom root.
