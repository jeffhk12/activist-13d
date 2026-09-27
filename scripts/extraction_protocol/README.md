# Extraction protocol tools

Run from the project root with the local `.venv/bin/python`, `PYTHONNOUSERSITE=1`, and `PYTHONIOENCODING=utf-8`.

- `build_v1.py` generates/verifies codebook, prompt and schema from the immutable category source. It refuses to change an existing version's bytes.
- `validate.py RECORD EVIDENCE` validates a **completed** extraction record against schema-v1.json, research/protocol/input hashes, category coverage, abstention rules and exact canonical-text citations. The evidence JSON uses `accession`, `source_sha256`, and a `documents` array with `document_id`, `text`, and `text_sha256`. This is a structural/provenance check, not semantic validation.
- `test_protocol.py` tests invented examples only; it produces no real human or model labels.

Blank human worksheets intentionally do not pass the completed-record schema. They are converted only after human review. The validator accepts only the v1 contract; a revised protocol requires a correspondingly versioned validator/run.

`input_manifest_sha256` means the SHA-256 of the exact bytes of the per-accession `document-text/ACCESSION.json` evidence bundle, including text. It does not mean the multi-accession `sample-manifest.json`. The saved bundle bytes are immutable inputs; reformatting produces a different input hash. Record the bundle path alongside the output in the run manifest.

Evidence bundles include observed `source_form` and each document's `source_accession`. The v1 validator accepts only embedded documents from that same accession and checks the initial/amendment analysis scope. External reference supplements need a later validated provenance contract; they remain evidence gaps here. `ambiguous` fields may contain zero alternatives when attribution or boundaries are unresolved; preserve all defensible alternatives whenever identifiable and explain the ambiguity.

Environment additions are pinned in `environment-lock.txt`. These tools do not call model APIs. Ordinary package installation used the public Python package index; no paid API was involved.
