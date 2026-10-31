# CK3 GUI structural and execution order

This reference covers a defect class that ownership-only validation still misses:

```text
correct owner + correct property + wrong sequence = potentially different GUI
```

## 1. Ordered child roles

Treat children of layout and presentation containers as an ordered sequence when order affects what the player sees or interacts with. Typical examples are `vbox`, `hbox`, flow containers, button rows, tab/filter lists, stacked backgrounds, and custom-type content.

Record semantic sequence as roles, not as copied source lines:

```text
children in order:
1. header
2. explanatory text
3. action row
4. list body
5. footer
```

For repeated anonymous children, keep a stable semantic discriminator such as widget type plus key binding/text/context, rather than sorting them alphabetically.

## 2. Unified owner statement order

Do not serialize an owner as `all properties` followed by `all child nodes` unless the source/requirement actually has that order. Current vanilla frequently interleaves them:

```text
property
child
property
child
```

Record one ordered statement stream per owner. A statement is a property occurrence, a child/declaration occurrence, or another preserved source-semantic item. Child-only order and property-only order are projections of this stream, not substitutes for it.

This matters especially around `using`, callbacks, block declarations/overrides, state/animation content, and template composition. Even where engine evaluation order is not proven, source-independent reconstruction must not silently reorder an existing target-version form.

## 3. Ordered repeated properties

A GUI node may repeat the same property. Preserve occurrence order when it can change behavior:

```gui
onclick = "[Controller.Commit]"
onclick = "[Controller.Close]"
```

Do not normalize this into an unordered set. The same rule applies to state/animation callbacks and any repeated `using` whose precedence is not proven irrelevant.

## 4. Draw and hit-test order

Sibling images/backgrounds/masks can overlap. Even when all style properties and owners are correct, reordering those siblings can change compositing, visual masking, or input interception. Preserve stack order unless a current-version analogue proves the elements are independent.

## 5. Layout order

For `vbox` and `hbox`, child sequence directly determines top-to-bottom or left-to-right placement. For flow/grid/list constructs, sequence can determine traversal and presentation order even when the `datamodel` itself supplies row data.

## 6. Requirement extraction

A source-independent requirement should retain:

- one unified ordered statement sequence per owner, preserving property/child interleaving;
- ordered child-role sequence per owner;
- ordered repeated values for behaviorally relevant properties;
- ordered local `using` composition unless proven commutative;
- named block declaration/override placement relative to its owning reusable type/template;
- explicit order-sensitive acceptance assertions for user-visible rows/actions.

It may omit comments, whitespace, line numbers, indentation, and exact lexical formatting.

## 7. Review

Review order separately from presence and ownership:

1. are required nodes/properties present?
2. are they attached to the correct owner/context?
3. are order-sensitive siblings/callbacks in the correct sequence?

A page must not receive a full semantic score if step 3 fails.

## 8. Existing-file edits need owner-scoped anchors

Structural order preservation does not by itself guarantee that the correct repeated owner was edited. Before a local patch, prove anchor cardinality inside the intended owner and define the exact statement delta/order budget. Never use the first matching textual occurrence when the same property, callback, custom-type instance, or geometry value appears in several siblings. See [minimal-edit.md](minimal-edit.md).
