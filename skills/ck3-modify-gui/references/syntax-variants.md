# CK3 GUI syntax variants and opaque values

## 1. Do not teach a single serializer grammar

Current CK3 1.19 GUI source uses multiple surface forms for equivalent declaration families. Editing tools should preserve the form already present in the target file/owner.

Verified vanilla examples include:

```gui
blockoverride "header_text" { }
blockoverride = "tab_glow" { }
block "command_callbacks" { }
block = "mm_glow" { }

types SomeNamespace { }
Types SaveGameTypes { }

local_template character_tooltip { }
layer debug { priority = 50 }
```

The capitalized `Types` spelling is uncommon but present in current vanilla. Do not case-normalize it during an existing-file edit.

## 2. Brace-valued properties are open-ended

Do not maintain a closed list such as only `size`, `position`, and `color`. Current vanilla also uses brace-valued properties such as `translate_uv`, `bezier`, `tintcolor`, `uv`, `portrait_scale`, `portrait_offset`, `format_override`, coat-of-arms offsets/scales, camera limits, and others.

For a requirement extractor, classify a brace occurrence from source structure and preserve its ordered token payload. If its semantics are unknown, keep it opaque instead of converting it into a child widget tree.

## 3. Optional `=` and no-equals forms

Current vanilla includes rare forms such as:

```gui
size { 5 0 }
margin { 0 -5 }
```

Do not insert `=` when reconstructing an existing source shape. Conversely, do not remove `=` from the normal `size = { ... }` form.

## 4. Exact value tokens

Whitespace between GUI tokens may be reformatted for a new file, but the token payload itself must remain intact. In particular, do not collapse whitespace inside quoted strings or bracket expressions during extraction/serialization. A quoted payload can contain user-visible spaces or nested script string literals.

## 5. Project-source-only forms

External projects can contain source forms not found in the current vanilla corpus. Source presence is useful preservation evidence but is not runtime proof. During minimal editing:

- preserve the observed form;
- label it `UNVERIFIED` unless project runtime evidence exists;
- do not replace it with a guessed canonical form simply because vanilla negative search returns zero.
