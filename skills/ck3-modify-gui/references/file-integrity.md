# CK3 GUI file-integrity contract

Semantic GUI equivalence and file-integrity equivalence are separate checks.

## 1. Record before modification

For an existing `.gui` file, record at least:

```text
path
UTF-8 BOM: present/absent
newline: CRLF/LF/mixed
trailing newline: yes/no
```

Preserve these properties unless the task explicitly calls for normalization or a verified engine/project rule requires a change.

## 2. BOM

Do not add or remove a UTF-8 BOM merely because a text editor or serializer defaults one way. Current vanilla GUI files are not uniform: some contain a BOM and some do not. Therefore the safe editing rule is **preserve the source file's state**.

For a newly created file, use the surrounding project convention and record the choice in static audit output.

## 3. Newlines

Preserve the source newline convention when replacing a complete existing file. A semantic parser may normalize line endings, so newline checks must run on raw bytes/text rather than only on the parsed GUI tree.

For a source file with **mixed** line endings, distinguish two goals:

- ordinary editing of the existing file: patch the original bytes/text and preserve the actual mixed pattern where practical;
- source-independent reconstruction from a semantic requirement graph: a single `newline = MIXED` label proves only the category, not the original per-line pattern. Exact mixed-newline reproduction requires lexical/per-line newline metadata, which is outside a formatting-stripped semantic graph. Do not claim byte-level newline fidelity from the category alone.

## 4. Validation

Report two independent results:

1. semantic/static GUI validation;
2. file-integrity validation.

A semantic PASS does not imply BOM/newline PASS.


## 5. Comment-only and archival GUI files

A semantics-only requirement graph intentionally omits comments. If a `.gui` file is empty after comment removal, reconstructing semantic nodes cannot reproduce its comment text or line-ending pattern. Classify such a file as `COMMENT_ONLY/ARCHIVE` for semantic benchmarks rather than claiming byte-level reconstruction. For a real edit, patch the original file bytes/text so comments and file contract remain intact.

## 6. Surgical-edit byte preservation

For a local existing-file change, prefer patching the original bytes/text over serializing the whole parsed tree. Comments, untouched formatting, and the exact per-line newline bytes are part of the preservation boundary even when they are not part of the semantic requirement graph. A static local-edit check should prove that raw bytes outside the declared edit span are unchanged.
