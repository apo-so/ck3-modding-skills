# CK3 GUI binding and context ownership

This reference formalizes a failure class that token-level GUI validation cannot detect:

```text
valid binding + valid expression + wrong owner/context/subtree = semantic GUI defect
```

It is a generic engineering rule. Do not hard-code one vanilla page as the solution to future tasks.

## 1. Ownership graph model

Represent a nontrivial GUI as semantic nodes rather than a flat expression inventory:

```text
node
├─ parent owner
├─ inherited receiver/context
├─ local datacontext transition
├─ datamodel/data source
├─ visibility/enablement/selection gates
├─ callbacks and state transitions
├─ template and blockoverride contract
├─ visual properties owned here
└─ child roles
```

The graph may omit source formatting and comments. It must not omit relationships that change receiver type, visibility scope, state behavior, data/action pairing, or any sibling/property sequence that affects layout, draw order, navigation, or execution.

## 2. Typed context environment, inheritance, and ordered updates

Do **not** model CK3 GUI as having one scalar "current datacontext". Vanilla frequently installs several `datacontext` entries on the same owner, and descendants can continue to address multiple receiver types. Model an ordered typed context environment:

```text
owner inherited environment
→ datacontext #1 installs/updates receiver type A
→ datacontext #2 installs/updates receiver type B
→ descendants inherit A + B + controller contexts still exposed by the widget
```

Exact vanilla example from `gui/window_title.gui`:

```gui
hbox = {
    datacontext = "[TitleViewWindow.GetTitle]"
    datacontext = "[Title.GetHolder]"

    button_round = {
        visible = "[And( Character.IsLocalPlayer, TitleViewWindow.GetTitle.HasLaws )]"
    }
}
```

The second expression depends on the Title receiver installed by the first, while descendants still use `Character.*`, `Title.*`, and `TitleViewWindow.*`. Treating the second declaration as "replace the whole context" is incorrect.

Rules:

1. Preserve multiple `datacontext` declarations and their order.
2. Resolve/record the receiver type installed by each declaration when evidence permits.
3. A child-local context extension belongs only to that child subtree; siblings inherit the parent's environment, not the child's additions.
4. If two declarations install the same receiver type and precedence matters, do not guess replacement semantics; find an exact current-version analogue or project runtime evidence.
5. Moving an ancestor context into only one child can break sibling controls even when every expression still exists somewhere in the file.

## 3. Section gates versus leaf gates

Visibility, enablement, and selected-state bindings have spatial/semantic owners.

```text
section visible = target valid
```

is not equivalent to:

```text
portrait visible = target valid
```

when labels, backgrounds, buttons, spacing, or other descendants remain. Preserve the highest node whose existence is controlled by the condition.

## 4. Data/action association

When similar panels consume different collections, preserve the pairing:

```text
panel A -> dataset A -> sort/filter/action A
panel B -> dataset B -> sort/filter/action B
```

Do not score a reconstruction as correct merely because all four expressions appear. Association is part of correctness.

## 5. State/callback ownership

`on_start`, `onclick`, `enabled`, `down`, `on_edit`, color callbacks, and command validation belong to the state/control whose transition they govern. Relocating them can change when or whether they run.

## 6. Identity ownership

`name`, `widgetid`, custom type tags, scripted-widget registry names, and block names are integration identifiers, not formatting. Preserve an explicit inner `name` even when it equals the custom type name. Vanilla contains many custom types whose inner `name` deliberately differs from the type tag, so deriving one from the other is unsafe.

## 7. Template and visual ownership

A named `blockoverride` belongs to a particular template instance. Likewise a mask, alpha, modified texture, frame, or divider belongs to the visual node it modifies. Presence-only checks are insufficient.

## 8. Requirement extraction contract

For source-independent reconstruction, an ownership-aware requirement may reveal:

- semantic node roles/types/names required for integration;
- parent/child ownership;
- inherited and local context contracts;
- data/action pairings;
- required `using` and named `blockoverride` ownership;
- geometry and visual ownership;
- acceptance conditions.

It should withhold irrelevant implementation details such as comments, whitespace, exact source line numbers, and source formatting. It must preserve semantic child order for layout/presentation containers and ordered repeated properties whenever sequence can affect visible placement, draw/hit-test stacking, navigation, or execution.

## 8.1. Stable node identity and file-root declarations

Readable owner paths are diagnostics, not unique IDs. A reconstruction graph should assign every semantic node:

- opaque `node_id`;
- `parent_id` (or file root);
- sibling `ordinal`;
- node kind/tag/base/name;
- ordered property sequence;
- ordered child IDs.

Include empty nodes when their presence or position is semantic. This prevents duplicate anonymous paths from stealing another node's properties during reconstruction.

Also include semantic declarations that live at file root rather than under a widget: top-level `@symbol = value`, `template Name { ... }`, `types Namespace { ... }`, and custom `type` declarations. Omitting the file root from the graph is a semantic data-loss bug.

## 9. Project-verified contexts absent from vanilla

A zero-hit vanilla GUI search does not prove that a receiver type, scope projection, or constructor is invalid. Projects may have working GUI bindings that vanilla does not currently use. When the project contains documented runtime evidence, classify the exact expression `PROJECT-VERIFIED`, preserve it, and record the tested scenario/version. Without runtime evidence, classify it `UNVERIFIED`; do not delete or rewrite it merely to make it look more vanilla.

## 10. Ambiguity rule

If ownership is absent or ambiguous:

1. search a non-target current-version vanilla analogue using the same controller/template family;
2. derive the smallest proven ownership contract;
3. mark unresolved associations `UNVERIFIED`;
4. do not silently guess a plausible subtree.

## 11. Review rule

Review two dimensions independently:

1. **binding/API validity** — are the expressions supported?
2. **ownership semantics** — are they attached to the correct context, data consumer, state, section, and template instance?

A high API-token score cannot compensate for an ownership-semantic failure. Likewise, full ownership recall cannot compensate for an order-semantic failure. Review structural/execution order as a third independent dimension.
