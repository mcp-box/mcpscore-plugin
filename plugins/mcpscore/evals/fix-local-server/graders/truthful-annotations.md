---
type: llm
weight: 2
---
`add_note` overwrites a note, `read_note` only reads, and `delete_note` deletes one.

If the response adds or describes tool annotations, pass only if they match those effects: `readOnlyHint` true for `read_note` alone, never for `add_note` or `delete_note`; `destructiveHint` true, if set, only for tools that delete or overwrite. Fail if any tool is described as doing something its code doesn't do.

If the response changes no annotations, pass.
