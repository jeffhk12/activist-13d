# Professor proposal V2 build record

Canonical text: `docs/PROFESSOR-PROPOSAL-v2.md`.
Editable output: `docs/PROFESSOR-PROPOSAL-v2.docx`.
Review PDF: `output/professor-review/Activist-13D-Professor-Proposal-v2.pdf`.
Agreed roadmap: `docs/PROJECT-PLAN.md`.

Run `python docs/proposal_v2/build.py` using Python with python-docx 1.2.0.
The page-break comment in the Markdown deliberately begins the methods section
on page two. The builder preserves the existing V1 proposal and shared renderer.

Validated on September 13, 2026: DOCX rendered through the document skill's
`render_docx.py`; both page images inspected after the final typography changes.
The resulting PDF has two US Letter pages. Builder lint passed. No research
pipeline changes, model API calls, or data downloads were performed for this task.

The skill's workspace runtime was unavailable, and Microsoft Word automation
timed out. Fallback rendering used an isolated temporary Python environment
(python-docx 1.2.0, pdf2image 1.17.0) and a temporary LibreOffice 26.2.6 image
from the official Document Foundation distribution, not a desktop installation.
The image SHA-256 matched the publisher's checksum:
`94bb3248df074c225490a8a6d1d9dc87c7d6783dbb7a8e9f0d0c3d94348552af`.
The disk image was detached after verification. QA outputs remain ignored under
`output/proposal-v2-qa-final/` and are not the professor deliverable.

Proposal text was developed and drafted with ChatGPT/Codex assistance in this
conversation. This disclosure appears in the document. Research extraction
prompts and per-call model versions do not yet exist; those are Phase 2 outputs.
