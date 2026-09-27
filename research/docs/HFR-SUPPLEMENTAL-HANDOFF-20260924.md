# Supplemental activist universe — 24 September 2026

User authorized adding Starboard Value, Pershing Square, Sachem Head, TCI,
ValueAct and Icahn-related entities alongside Elliott. Keep selection separate
from historical HFR membership. Third Point, Trian and JANA already belong to
the historical HFR universe and were not added twice.

Run: `/Users/jefflu/Projects/activist-13d/research/runs/investor-identity/20260924-supplemental-v1/`.
[Open report](../runs/investor-identity/20260924-supplemental-v1/index.html).
Reproduce with `scripts/data_collection/include_supplemental_activists.py`
using the project venv and AGENTS.md environment settings. The script pins
deduplication/count arithmetic and refuses changed frozen output on replay.

The denominator is 75,631 unique local parsed 13D/13D-A accessions.
Six new groups: 1,145 filings (124 initials, 1,021 amendments).
With Elliott: 1,375 (163 initials, 1,212 amendments).
Union with dated HFR Event-Driven: 3,125 (404 initials, 2,721 amendments), 4.13%.
Union with dated HFR Activist: 2,636 (323 initials, 2,313 amendments), 3.49%.
There is zero accession overlap between the supplemental set and either HFR
candidate set in this local screen; all union lists are saved explicitly.

These are candidate metadata links, not validated campaigns. Explicit source
reporting-entity CIK/name pairs are saved in universe.json. Separate entities
within a manager group need dated relationship verification. ValueAct's small
local sample remains a collection/alias investigation priority. No claim of
complete manager coverage or raw-source hash reverification is made.

Earlier broad token counts included incidental names. Removed Starboard
Enterprises, Icahn School of Medicine and unrelated Elliott people/family
entities. Exact excluded metadata hits are preserved in excluded-token-hits.json.
The broader Elliott set has 230 candidates across three entities; only the
earlier 56-filing Elliott Investment Management subset had prior identity/source
verification. Do not transfer that verification to the broader set.

Temporal scope differs: the HFR screen requires a strictly earlier supplied
delivery proxy, beginning in 2018; this externally selected supplement searches
all local filing dates. Combined totals measure discovery coverage, not a
historically investable or time-consistent backtest universe. Next: verify
entities and relationships, reconcile sources, review issuer eligibility and
build initial/amendment timelines before defining campaign events.
