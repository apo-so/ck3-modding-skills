# CK3 GUI surgical minimal-edit protocol

This reference applies when modifying an existing GUI file rather than reconstructing it from a requirement graph.

## 1. Resolve the semantic target before touching text

A textual occurrence is not an owner. Locate the target with the strongest available combination of:

- explicit `name` / `widgetid`;
- custom `type`, `template`, `block`, or `blockoverride` identity;
- ancestor owner chain;
- local `datacontext`, `datamodel`, text key, or action discriminator;
- sibling ordinal/stable node ID when repeated anonymous siblings remain ambiguous.

Before patching, assert the candidate locator resolves to exactly one intended owner. If `margin_left = 0`, `widget_game_rule_option = {`, or an identical `onclick` occurs several times, a first-match replacement is invalid even when the resulting file parses.

## 2. Define a mutation budget

Write the intended semantic delta before editing, for example:

```text
owner: header/button_close
allowed: append one onclick after existing onclick #2
forbidden: move/delete/rewrite either existing onclick
forbidden: any other semantic token delta
```

The budget should state:

- owner;
- allowed insertion/replacement/deletion;
- required relative order;
- expected binding/context environment;
- whether any sibling geometry/order may change.

## 3. Patch the original source, do not casually reserialize it

For a local edit, patch original bytes/text so that comments, formatting, syntax variants, and unrelated user edits remain intact. Full reconstruction/serialization is justified only when the task actually requires broad structural replacement or the source is being generated from scratch.

For mixed-newline files, choose the inserted line ending from the local owner and leave every pre-existing line ending untouched outside the patch span. Preserve BOM and trailing-newline behavior.

## 4. Verify zero collateral

After editing, run four independent checks:

1. candidate parses/has balanced structure;
2. requested semantic delta exists on the correct owner and in the required statement order;
3. comment-stripped semantic token diff contains only the declared mutation budget;
4. raw bytes outside the edit span are unchanged for a surgical patch.

If a tool cannot prove which occurrence it edited, or a token diff contains an undeclared change, the local-edit static gate fails.

## 5. Negative-control pattern

When validating an editing workflow, include duplicate-anchor cases. A useful negative control intentionally applies an unscoped first-match replacement and confirms that it would hit the wrong owner. This demonstrates that owner-aware targeting, rather than literal-search luck, is carrying the result.
## 6. Indirect rendered collateral for layout edits

Byte preservation outside the edited span does not prove visual locality. In flow layouts, changing a target sibling's width or horizontal layout policy can move an untouched sibling. For screenshot-driven geometry work, add a frozen-region contract to the mutation budget:

- name the last rendered-accepted baseline;
- identify frozen sibling owners and their first shared flow parent with the target;
- freeze the shared parent's horizontal allocation properties;
- freeze the frozen sibling subtree;
- when the task is pane-local, freeze the target pane's **outer allocation** and edit only deeper content owners unless a wider mutation was explicitly authorized;
- reject the candidate if a protected allocation property changes, even when the textual diff is inside the nominal target pane.

A task-specific static audit should compare the frozen subtree and shared allocation against the accepted baseline. A subsequent rendered frame must confirm that the frozen region did not move, compress, clip, or gain dead space.
