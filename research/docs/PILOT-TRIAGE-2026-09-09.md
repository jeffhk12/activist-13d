# Pilot evidence triage — 2026-09-09

## Scope and status

Reviewed the ten generated filing sheets, including their attached exhibit text,
after successful offline replay. This is **model-assisted preliminary triage by
Codex**, not independent human validation, a frozen codebook, or training labels.
The underlying model version is not recorded in this workspace. Do not use these
judgments as a gold-standard validation set. No external extraction-provider API
was called during this review.

Each linked sheet identifies the accession, raw submission path, SEC URL, and
source SHA-256. Supporting spans below refer to Item 4 unless stated otherwise.
This pass does not certify extraction boundaries against raw HTML/XML, resolve
all incorporated references, or determine campaign outcomes. Absence of a concrete
demand in the reviewed passage does not establish absence of activism elsewhere.

## Preliminary review ledger

| Accession / source sheet | Supporting span | Model judgment and next evidence needed |
|---|---|---|
| [0001104659-24-000323](../runs/pilot-filings/0001104659-24-000323.md) | “Chavant Capital expects to distribute to its members”; “Dr. Jiong Ma serves as a member of the Board” | Sponsor/distribution and board-affiliation context. Do not automatically count as outsider activism. Read the incorporated Explanatory Note and Items 3 and 6 before deciding eligibility. |
| [0001398344-24-000853](../runs/pilot-filings/0001398344-24-000853.md) | Item 4: “Letter was sent to the company. See exhibit B.” Exhibit B: “The stockholders urge the Board to seek stockholder approval” | Concrete governance-demand candidate supported by the attached shareholder proposal. Preserve Exhibit B as label evidence; Item 4 alone omits the demand. Resolve Bulldog versus Special Opportunities Fund roles before defining the campaign entity. CUSIP remains missing. |
| [0001104659-24-024047](../runs/pilot-filings/0001104659-24-024047.md) | “his position as Interim Principal Executive Officer”; “his position as a director” | Insider holdings/compensation context. No specific outsider demand established by this passage. Read incorporated Item 6. The isolated “3” in extracted text is a likely page-number artifact requiring raw-source confirmation. |
| [0001493152-24-008748](../runs/pilot-filings/0001493152-24-008748.md) | “investment purposes only”; “no present intention of doing so” | No current concrete demand identified in the reviewed passage. Retain as a potential negative example only after independent review; do not infer a campaign from form type alone. |
| [0001193125-24-081594](../runs/pilot-filings/0001193125-24-081594.md) | “Item 3 and Item 6”; “lock-up period as part of the Transaction” | Transaction context is unresolved in Item 4 alone. Defer eligibility until incorporated financing/transaction terms are reviewed. The attached joint filing agreement does not resolve those terms. |
| [0000807249-25-000003](../runs/pilot-filings/0000807249-25-000003.md) | “may suggest or take a position”; “no present plans or proposals” | General investment philosophy and conditional engagement language, without a specific current demand established here. Manager reputation must not substitute for filing-level evidence. |
| [0001640334-25-000152](../runs/pilot-filings/0001640334-25-000152.md) | “conversion of debt by PreCheck”; “as an officer and director of PreCheck” | Debt conversion/compensation context with stated influence intent. Relationship to the issuer needs resolution; the text names PreCheck, so do not silently equate entities. No specific governance demand established here. |
| [0001104659-25-014424](../runs/pilot-filings/0001104659-25-014424.md) | “Founder Shares”; “newly organized blank check company” | SPAC sponsor/business-combination context. Generic merger language would create a false activist signal if treated as a demand without context. Review incorporated Item 6 and eligibility rules. |
| [0000950142-25-000685](../runs/pilot-filings/0000950142-25-000685.md) | “completed a spin-off”; “Mr. Knott serves as a director of the Board and the Issuer's Chief Executive Officer” | Spin-off and insider/control context. Read incorporated Item 6. Annex A describes overlapping beneficial ownership; do not sum reporting-person percentages. |
| [0001477932-25-002177](../runs/pilot-filings/0001477932-25-002177.md) | “sole director of the Issuer”; “Chief Executive Officer of the Issuer” | Insider/control context, not sufficient evidence of an outsider campaign. Review incorporated Item 3 before final eligibility. |

## Implications for the next implementation

1. Build source-addressable evidence bundles containing Item 4, explicitly
   referenced sections, and referenced exhibits. Keep original passages separate;
   do not overwrite the extracted Item 4 field with concatenated text.
2. Record unresolved references explicitly, including documents incorporated from
   other filings. A located Item 4 is not a completeness check.
3. Add a regression case for Bulldog: the governance demand must remain traceable
   to Exhibit B, while the original Item 4 remains intact.
4. Resolve filer groups and issuer identity before collecting amendment chains.
   Initial accessions are filing events, not automatically distinct campaigns.
5. Decide corporate versus CEF scope before freezing the intent codebook. Keep
   insider/sponsor context and current concrete demands distinct in that design.

The ten filings are a deterministic parser sample. This ledger supports no
estimate of activism prevalence or expected campaign sample size.

## Revalidated checkpoint

On 2026-09-09, `pytest -m 'not network'` passed 34 tests with one network test
deselected; Ruff passed. `scripts/verify_pilot.py` verified ten unique filings,
their source hashes, two source-pinned examples, and byte-identical JSONL/audit
replay. These checks establish reproducibility, not semantic correctness.
