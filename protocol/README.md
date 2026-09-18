# protocol/

Versioned, hashed definitions that the pipeline reads and the report cites.
**Never edited in place** — a change means a new version file, because labels
produced under v1 and v2 are not comparable and the panel has to record which
produced each row.

| File | Purpose |
|---|---|
| `categories-v1.yaml` | The single source of category definitions |
| `intent-codebook-v1.md` | Human-facing rendering, for hand labelling |
| `extraction-prompt-v1.md` | Model-facing rendering, for the extraction call |
| `outcome-codebook-v1.md` | The five competing terminal states and the decision rule for ties |
| `schema-v1.json` | Emitted from the pydantic model; hashed and recorded per response |

## The rule that matters

`intent-codebook-v1.md` and `extraction-prompt-v1.md` are **two renderings of
one source**, generated from `categories-v1.yaml`. If they drift, the human
labels and the model labels measure different constructs and every agreement
statistic between them is noise.

The outcome codebook is the larger of the two and currently the least specified
part of the project — five heterogeneous evidence sources plus a decision rule
for ambiguity and censoring. Draft it alongside the intent codebook, not after.
