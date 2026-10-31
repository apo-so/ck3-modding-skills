# Rendered-UI acceptance for CK3 GUI

Static structure, correct bindings, and byte-preserving edits are necessary but do not prove that a CK3 GUI is usable after rendering. A rendered screenshot or observed game window is first-class evidence for geometry, content fit, information hierarchy, and visual state.

## 1. Evidence boundary

Use these terms distinctly:

- `STATIC PASS`: syntax/source/ownership/file-integrity checks passed.
- `RENDERED-UI OBSERVED`: a screenshot or live game frame from the target build/resolution/UI scale was inspected.
- `RENDERED-UI PASS`: the requested layout/content-fit/state-salience acceptance criteria were observed in that rendered frame.
- `HOT-RELOAD OBSERVED`, `COLD-START PASS`, and `SCENARIO PASS`: separate runtime gates; a screenshot does not prove them unless the corresponding process/scenario was actually exercised.

Rendered evidence overrides static assumptions about geometry. If arithmetic says a pane is 510 px but the screenshot shows a much wider pane, the screenshot wins and the constraint path must be traced.

## 2. Constraint-realization ledger

For every dimension that matters to the design, record both the intended value and the property that actually enforces it:

```text
region: right detail pane
intent: fixed width from @prefix_detail_width
owner: hbox/right-pane
constraint sink: size / minimumsize / maximumsize / parent contract
layout policy: fixed / expanding
status: enforced / inherited / not enforced
```

A declared `@width` constant is not a layout contract until the intended owner consumes it through an effective sizing constraint. Flag these cases:

- a design says `left + gap + right = total`, but one pane remains `layoutpolicy_horizontal = expanding` with no proven fixed/min/max sink;
- a child uses a hard-coded inner width much smaller than its expanding pane, producing dead space;
- the header and data rows share column constants but the outer pane ignores the matching total-width constant;
- an inherited template overrides or weakens a local size assumption.

Do not claim a fixed split merely because constants with the desired numbers exist in the file.

### 2.1 Flow-layout anchor/origin risk

A project screenshot exposed a recurrent failure pattern: a fixed-size page child was placed inside a normal `vbox` flow and then given `parentanchor = hcenter`. The rendered result did **not** behave like CSS-style centering; the page began near the parent center, leaving a large leading blank area and pushing the detail pane off-screen.

Treat this combination as a **STATIC GEOMETRY RISK** signature:

```text
flow-managed child
+ fixed horizontal size
+ parentanchor = hcenter|center
+ no exact analogue proving the anchor/origin behavior
```

Rendered symptom:

```text
large blank area before the page
+ expected content starts near window center
+ trailing pane clipped/off-screen
```

Repair order:

1. remove the unverified anchor and restore ordinary parent flow;
2. keep child pane constraints intact;
3. re-render before changing pane widths or adding spacers;
4. only reintroduce anchoring if an exact vanilla/project-verified composition requires it.

Do not generalize this into “never use parentanchor”. Use it where the target composition is evidenced; do not use it as a generic centering shortcut.

### 2.2 Frozen-region and sibling-impact gate

A local geometry task must preserve regions that already passed rendered acceptance, including indirect effects caused by a changed sibling. Raw-byte equality of the frozen sibling alone is insufficient when both siblings share flow allocation.

Before editing, record a frozen-region ledger such as:

```text
frozen region: left ledger
baseline: last RENDERED-UI PASS build
owner: page/hbox/left-pane
protected subtree: byte/semantic exact
shared flow parent: page/hbox
protected allocation: parent width/layout/spacing + left pane width + sibling outer allocation
target owner: page/hbox/right-pane/scrollbox/scrollbox_content/vbox
allowed: inner content layout/wrapping/row composition
forbidden: shared parent geometry; frozen pane geometry; right-pane outer width/layout-policy changes that redistribute sibling space
```

Apply the **shared flow parent** test even when the edited source lines are entirely inside the target sibling. In an `hbox`, changing one child's fixed width or horizontal layout policy can move/compress another child without touching that sibling's bytes. That is an **indirect geometry regression** and must fail the local-patch gate unless the mutation budget explicitly allows both panes to move.

For a “right pane only” repair, the default repair order is:

1. restore the last rendered-accepted outer pane geometry;
2. keep the shared parent and frozen sibling allocation byte/semantic-identical;
3. repair the deepest inner owner first (`scrollbox_content`, inner flow container, wrapping, row width, localized text);
4. re-render and compare both the target pane and every frozen sibling.

Static acceptance should include both: (a) frozen-subtree equality and (b) shared-allocation equality. If either cannot be proven, report `STATIC GEOMETRY RISK` and do not claim a surgical visual fix.

### 2.3 Fixed-child left-rail placement

A second rendered failure signature is:

```text
expanding vbox
+ neighboring expanding headings start at the expected left edge
+ fixed-width text/button/hbox/container children appear shifted right
+ `align = left` is present on the text but does not fix the shift
```

This is an owner-placement problem, not a glyph-alignment problem. `align = left` governs text inside its own rectangle; it does not establish the rectangle's x-origin in the parent flow.

For an intentionally narrow left rail, prefer ordinary flow with an explicit trailing consumer:

```gui
hbox = {
    layoutpolicy_horizontal = expanding
    widget_or_control = { size = { 330 30 } }
    expand = {}
}
```

The fixed child is first in the horizontal flow; unused width is consumed to its right. This pattern must still be rendered-tested, but it avoids solving a local placement defect by widening the pane, changing a shared sibling allocation, or adding an unverified centering anchor.

Repair order for this signature:

1. freeze outer pane and accepted sibling geometry;
2. wrap the shifted fixed-width owner in an expanding horizontal flow with trailing `expand`;
3. keep the fixed child's own width unless content-fit evidence requires a separate change;
4. re-render and compare the fixed child's left edge to an already-correct expanding heading in the same inner `vbox`;
5. only then consider margins or widths.

## 3. Content-fit and localization gate

Column alignment is not enough; localized content must fit at the target UI scale.

For every fixed-width text/control column, inspect:

- actual localized label length;
- `autoresize`, `max_width`, and fixed `size` interaction;
- icon/padding/divider space consumed inside the nominal column;
- truncation, overlap, ellipsis, clipping, or unreadably compressed labels;
- whether the same column is used by header and rows but has different content-density needs.

When a dense ledger header does not fit, prefer one of:

1. shorter localized header plus full tooltip;
2. a wider/rebalanced column;
3. a clear icon plus tooltip for status/realm/rule columns;
4. moving lower-priority metadata out of the ledger.

Do not "fix" overflow by silently shrinking fonts below the surrounding UI norm unless the design explicitly calls for that tradeoff.

## 4. Pane utilization and dead-space review

A pane can be structurally valid and still waste most of its area. Inspect the ratio between the rendered pane and its actual content envelope.

Flag a rendered design when:

- an expanding pane contains a much narrower fixed inner column while important information is pushed below the fold;
- large blank regions coexist with clipped or crowded neighboring content;
- a fixed-width detail row is substantially narrower than the pane that owns it without an intentional centering/composition reason;
- the page reserves space for secondary decoration while primary task information is off-screen.

The fix should normally target the owning constraint or content composition, not add arbitrary spacer widgets.

## 5. First-viewport information hierarchy

Before implementation, classify right-pane sections or major blocks as:

- `PRIMARY`: information/actions central to why the page exists;
- `SECONDARY`: explanatory statistics or metadata;
- `DIAGNOSTIC`: development/debug/support detail.

At the target viewport, `PRIMARY` information should normally be visible without scrolling unless the design explicitly chooses otherwise. If secondary one-value-per-row statistics push the primary action/status section below the fold, compact or rearrange the secondary section (for example a two-column stats grid) before increasing window height.

Do not equate "all information exists somewhere in the scrollbox" with good information architecture.

## 6. Selected-state salience

A correct `down = ...` or `ObjectsEqual(...)` binding proves state logic, not visual discoverability.

Rendered acceptance should answer: can the selected row/control be identified directly, without reading the detail pane and cross-referencing names?

If not, add or strengthen one project-consistent cue such as:

- selected background/frame;
- edge marker;
- subtle highlight/glow;
- stronger but non-destructive text/frame treatment.

Keep one authoritative selection state. This rule changes presentation, not state ownership.

## 7. Toolbar grouping and action-label fit

Dense toolbars should expose task groups rather than one undifferentiated stream of controls. Review:

- search/filter controls;
- primary category/tier tabs;
- sort/group controls;
- count/status indicators;
- refresh/commit actions.

Use spacing/dividers to separate groups. A text action whose label is visibly truncated is a rendered failure; either allocate sufficient width, shorten the localization with a tooltip, or use a proven icon treatment.

## 8. Ellipsis and placeholder triage

Visible `...`, blank text, or placeholder-looking output is ambiguous. Do not classify it as a layout bug or a binding bug without tracing the source.

Check in this order:

1. Is the localization value literally `...` or another placeholder?
2. Is a valid rendered string being clipped/truncated by fixed width or `autoresize = no`?
3. Does the binding return an empty/invalid object under the current typed context environment?
4. Is a fallback text/localization branch being selected?
5. Do current logs report a context/binding error?

Record the classification as `LITERAL PLACEHOLDER`, `TRUNCATED`, `EMPTY/FALLBACK`, `BINDING/CONTEXT RISK`, or `UNRESOLVED`. A screenshot alone can prove that `...` is visible, but not why.

## 9. Screenshot comparison protocol

When the user supplies a rendered screenshot or compares a result to a mock/preview, review region by region instead of giving one similarity score.

Use a rendered acceptance ledger:

```text
region | design intent | rendered observation | severity | likely owner | next action
```

Cover at minimum:

- overall window and pane proportions;
- toolbar grouping and label fit;
- header/data column alignment and content fit;
- row rhythm and clipping;
- selected-state salience;
- dead space versus crowded zones;
- right-pane information hierarchy and first-fold position;
- scrollbars/clipping;
- placeholders/ellipsis;
- target resolution and UI scale.

For a screenshot-driven iteration, freeze the diagnosis before editing. The next patch should declare a visual mutation budget just like a source mutation budget: which pane widths, column widths, section order, or style cues are allowed to change.

## 10. Static preflight versus rendered proof

Static preflight can flag risks but must not overclaim:

- fixed pane constant declared but not consumed by owner -> `STATIC RISK`;
- many narrow fixed localized header columns -> `CONTENT-FIT RISK`;
- primary section placed after a long secondary stack -> `FIRST-VIEWPORT RISK`;
- selected logic present but no explicit visual cue beyond inherited `down` style -> `SALIENCE RISK`.

Only rendered evidence can close those risks as a visual PASS. Preserve the distinction in handoff documents.
