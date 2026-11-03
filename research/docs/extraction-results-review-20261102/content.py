"""Reader-facing content for the extraction results and methods review.
Inputs: calculated local report analysis. Outputs: typed report sections.
Identity: narrative counts use the 627-filing production scope unless qualified.
Tier: 1 explanatory content; no extraction judgments or investment fit.
Imported by build_report.py; all proposed choices remain visibly proposed.
"""
from pathlib import Path

LABELS = {
 'board_representation':'Board representation', 'leadership_change':'Executive leadership change',
 'capital_return':'Return of capital', 'capital_structure':'Capital structure',
 'sale_of_company':'Sale of the company', 'asset_transaction':'Asset or business transaction',
 'operational_change':'Operational change', 'governance_change':'Governance policy change',
 'other_stated_objective':'Other specific objective'}


def make_sections(a):
    o=a['overview']; t=o['totals']; s=a['sources']; f=a['flags']; readers=a['reader_field_records']; v=a['critic_by_field']
    E=readers['extractor']; B=readers['blind']
    sections=[]
    def section(title, subtitle, blocks):
        sections.append({'id':f'section-{len(sections)+1:02}','title':title,'subtitle':subtitle,'blocks':blocks})
    def p(text):return {'type':'p','text':text}
    def h(text):return {'type':'h','text':text}
    def call(text):return {'type':'callout','text':text}
    def table(headers,rows,widths=None):return {'type':'table','headers':headers,'rows':rows,'widths':widths}
    def bullets(items):return {'type':'bullets','items':items}
    def fig(name,caption):return {'type':'figure','name':name,'caption':caption}

    section('The investment question and current answer','Completed extraction is a measurement stage. The investment test comes next.',[
      p('We are studying whether information in an investor\'s initial Schedule 13D disclosure helps rank subsequent investment opportunities. The incremental question is whether reading stated objectives and qualified funding adds useful information beyond a comparable model using structured company and filing data.'),
      p('The eligible extraction collection is complete: <b>640 filings</b>, comprising <b>627 filings in the production run and 13 earlier completed v3 cases</b>. The original 667-event panel also contains 27 protected or connected filings that stayed outside this production interpretation. Those counts refer to filings, not unique companies, managers or independent campaigns. [S1, S2]'),
      table(['What we know','What it means'],[
       ['265 of 627 production filings have at least one qualifying positive objective','There is variation in stated intent that could become an experimental model input.'],
       ['314 have all nine categories eligible as not stated','A specific qualifying intervention was not established under the current definitions. This does not classify the investor as passive.'],
       ['48 have no eligible positive and at least one unresolved category','These remain distinct from the fully classified negative group.'],
       ['221 critic flags and 165 excluded objective decisions remain','The two review queues overlap and need a documented follow-up.']],[.36,.64]),
      call('The extraction has produced traceable, experimental measurements. No extraction-enhanced ranking model has been fitted, no natural-filing accuracy estimate is available, and no investment edge is established.'),
      p('The immediate decision is how to adjudicate uncertainty and define the usable feature table. Historical financial-data timing and mapping must also be resolved before interpreting a definitive financial-versus-text ranking comparison. [S3, S10]')])

    section('The questions the project is trying to answer','Separate the investment hypothesis from the document-reading questions.',[
      table(['Question','How we answer it','Status'],[
       ['Does following an initial 13D disclosure produce an attractive benchmark-relative outcome?','Use explicit entry, horizon, benchmark, overlap and missing-price conventions.','Earlier baseline work exists; it is separate from extraction.'],
       ['Can structured data rank later opportunities?','Fit a simple baseline on earlier, fully matured observations and evaluate later scores.','An exploratory non-LLM comparison exists.'],
       ['What does the reporting investor specifically intend to change?','Apply nine objective definitions and a common qualification gate to the supplied filing.','627 production filings completed.'],
       ['How was the reported investment financed?','Retain actor, funding type, certainty and link to the current acquisition.','Extracted; final feature transformation is pending.'],
       ['Which holdings and contractual events are disclosed?','Keep person/security attribution, overlap, timing and material conditions.','Extracted for evidence; specified model features remain excluded.'],
       ['Are the extracted answers dependable enough for research?','Combine independent readings, backward checks, exact citations, controls and explicit abstention.','Automated checks completed; independent accuracy acceptance is unmet.'],
       ['Does text improve ranking beyond the baseline?','Compare models on the same eligible observations and evaluation periods.','Not yet tested with this completed extraction.']],[.30,.43,.27]),
      p('These are different questions. A correctly quoted sentence can still be assigned the wrong category. A consistently assigned category can still have no predictive value. A model that ranks historical observations well can still fail on later data or after implementation costs.'),
      p('The report therefore distinguishes source facts, model interpretations, mechanical verification and proposed research choices. None substitutes for another.')])

    section('Which filings and sources are covered','The numerical results in this report use a consistent 627-filing production scope.',[
      table(['Scope item','Count or range','Interpretation'],[
       ['Original panel','667 filing events','The starting project panel; not a census of all 13D filings.'],
       ['Earlier v3 cases','13','Completed before the production queue; excluded from its aggregate statistics.'],
       ['Protected or connected cases','27','Includes seven unreleased reserved accessions and known connected cases.'],
       ['Production run','627 initial SC 13D filings','All 1,881 assigned jobs finalized: 627 for each role.'],
       ['Public acceptance dates',f"{s['accepted_et_min'][:10]} to {s['accepted_et_max'][:10]}",'Eastern-time source acceptance metadata; not the report date.'],
       ['Issuer identifiers',str(s['unique_issuer_ciks'])+' distinct CIKs','Some issuers recur. CIKs do not certify independent campaigns.'],
       ['Queue ordering','593 regular and 34 long filings','Workload tier, then seeded accession hash; all long filings retained.']],[.27,.30,.43]),
      table(['Acceptance year','2018','2019','2020','2021','2022','2023'],[['Production filings']+[str(s['filings_by_acceptance_year'][str(y)]) for y in range(2018,2024)]],[.28,.12,.12,.12,.12,.12,.12]),
      p('The queue was frozen before release of the production sources and was not ordered using investment outcomes or inferred objectives. Workload ordering means an early batch is not a random accuracy sample. Completing the whole queue removes that ordering issue from the aggregate counts, but does not make the original panel representative of the wider 13D universe. [S1, S2]'),
      p('Repeated issuers, related reporters and overlapping investment horizons create dependence. A later statistical evaluation must account for that structure; 627 filing events should not automatically be treated as 627 independent investment experiments.')])

    section('How the source evidence was prepared','Readability, historical eligibility and completeness are separate concepts.',[
      p('The workflow uses preserved local SEC submissions and a canonical text representation for each readable document. Canonical text is the exact character sequence used to locate quotations. Its hash identifies that representation; changing whitespace or decoding creates a different text version.'),
      table(['Source measure','Observed production scope'],[
       ['Inventoried canonical documents',f"{s['canonical_documents']:,}"],
       ['Readable characters per filing',f"Median {s['readable_characters_per_filing']['median']:,}; range {s['readable_characters_per_filing']['minimum']:,} to {s['readable_characters_per_filing']['maximum']:,}"],
       ['Readable characters across filings',f"{s['readable_characters_per_filing']['total']:,}; before three-role repetition"],
       ['Textless document inventory',f"{s['documents_without_text']} items in {s['filings_with_documents_without_text']} filings"],
       ['Reference detections',f"{s['unresolved_reference_detections']:,} detections across {s['filings_with_unresolved_reference_detections']} filings"]],[.40,.60]),
      call('Reference detections are parser inventory warnings. They can include internal or irrelevant references; they are not 9,439 confirmed missing material exhibits. Similarly, a textless item is not automatically a missing substantive agreement.'),
      p('Every role received all readable text through a helper, in chunks of at most 16,000 Unicode characters with a large output allowance. Coverage receipts tracked which character intervals were delivered. All 1,881 finalized production records report complete readable delivery. That proves delivery coverage, not comprehension or completeness of documents that were never available. [S2, S4]'),
      p('A material missing letter can make a particular objective unknown. An unrelated missing image should not make every objective unknown. Later amendments, later outcomes, remembered campaign histories and web retrieval were excluded during this extraction. Historical identifier and financial-statement eligibility remain separate workstreams.')])

    section('What one extracted record contains','A record separates reported facts from judgments about their meaning.',[
      p('We treat each initial 13D as a dated disclosure package: the main filing plus relevant supplied exhibits. The familiar starting points are Item 3 for sources of funds, Item 4 for the purpose and stated plans, Item 5 for interests in the securities, and Item 6 for contracts and arrangements. The agents reviewed the whole readable bundle rather than relying on one section or a keyword search.'),
      table(['Question asked of the filing','Stored answer','Why the distinction matters'],[
       ['Who is the issuer and who are the reporting persons?','Names, identities and exact evidence','A source name is not a validated economic-manager match.'],
       ['What security holding is attributed to each person?','Security, amount, percentage, role and overlap','The same shares can appear under multiple beneficial owners.'],
       ['What financed the acquisition?','Actor, type, certainty, acquisition link and description','An available facility is different from borrowing actually used.'],
       ['What material events or undertakings are described?','Transaction kind, actors, timing, conditions and context','A completed event, future condition and historical background differ.'],
       ['Which specific issuer-directed objectives qualify?','Nine states, actor, target, qualification, rationale and quotations','A reference to a topic alone does not establish an intervention.'],
       ['What could not be established?','Evidence gaps, uncertain states and alternative readings','Missing information remains visible rather than becoming a negative.']],[.30,.35,.35]),
      p('Each finalized record also retains source and protocol hashes, role, case identity, timestamps, draft provenance and delivery information. Exact model identifiers and generation settings were not exposed by the subscription-agent interface and remain null; they are not filled with an assumed model name. [S2, S4]'),
      h('Worked teaching example - invented, not a sample observation'),
      p('Suppose a fund states that it purchased shares with working capital and is nominating two directors. The purchase funding and nomination are separate measurements. If the same paragraph says working capital may include margin loans, the borrowing component stays possible. It does not become confirmed borrowing merely because working-capital funding is established.'),
      p('The record describes what was disclosed at that time. It does not establish whether the nominations succeeded, whether management improved, or whether the stock was attractive.')])

    section('How an objective qualifies','The common gate is applied before choosing one of the nine categories.',[
      p('A qualifying positive is a specific current request, proposal or plan directed at the issuer, attributable to a reporting person, and independently meaningful beyond ordinary transaction implementation. A primary plan to acquire control of the whole company qualifies as sale of the company. A specific independent intervention can remain conditional. [S4]'),
      table(['Boundary','Treatment under the frozen rules'],[
       ['Whole-company acquisition with automatic director succession and delisting','The control bid can qualify as a sale objective. Succession and delisting remain transaction facts without automatic extra objectives.'],
       ['Continuing investor right to nominate a director','Can qualify as board representation if it is an independently meaningful continuing intervention.'],
       ['Generic discussions about operations, governance or value creation','Do not automatically establish specific operating or governance proposals.'],
       ['Conditional proposal','Assess specificity and independence. Conditionality alone does not disqualify it.'],
       ['Separate request to remove a takeover defense','Can qualify as governance change with current attribution and exact evidence.'],
       ['Missing letter that contains the investor\'s actual proposal','Use category-specific uncertainty if the missing material could determine the answer.']],[.39,.61]),
      table(['State','Meaning','What it does not establish'],[
       ['Present','A qualifying stated objective is supported under the definitions.','Success, investment merit or a return forecast.'],
       ['Not stated','Relevant supplied evidence was reviewed and no unresolved material gap prevents a negative coding.','No private intentions, no activism or no future action.'],
       ['Cannot determine','Material missing evidence or unresolved attribution, scope or definition.','A negative label or a failed investment.']],[.17,.46,.37]),
      p('Multiple objectives require separately qualifying evidence. The catch-all other category is reserved for a specific qualifying intervention outside the eight named categories; it is not a place to put uncertainty.')])

    section('The nine objective questions','Examples are definitions and teaching illustrations, not additional findings.',[
      table(['Category','Question','Typical qualifying example'],[
       ['Board representation','Does the investor seek board seats or a change in board composition?','Nominate or remove directors.'],
       ['Executive leadership','Does the investor seek a change in executive management?','Replace the CEO.'],
       ['Return of capital','Does the investor request cash or other capital distributions?','Special dividend or issuer repurchase.'],
       ['Capital structure','Does the investor seek issuer financing, leverage or recapitalization changes?','Debt reduction or refinancing proposal.'],
       ['Sale of company','Does the investor seek a whole-company control transaction?','Take-private bid or request to sell the issuer.'],
       ['Asset or business transaction','Does the investor seek a specific asset/business acquisition or separation?','Sell a division or pursue a spin-off.'],
       ['Operational change','Does the investor seek a specified operating or business-strategy action?','A concrete cost-reduction or restructuring demand.'],
       ['Governance policy','Does the investor seek governance-rule or shareholder-rights reform?','Remove a poison pill or alter voting policy.'],
       ['Other specific objective','Is there another attributable and independently qualifying issuer-directed objective?','A strategic-review demand without a specified transaction.']],[.22,.45,.33]),
      p('Seeking directors alone is not automatically a second governance-policy label. Investor borrowing to buy shares is not automatically an issuer capital-structure objective. Purchasing securities is not an asset/business transaction objective. These distinctions keep different economic questions from collapsing into the same keyword count.'),
      p('The current definitions still leave some genuine boundaries unresolved, such as board observers and certain corporate-opportunity waivers. Those questions appear in the review queue; this report does not silently amend the frozen definitions. [S4, S6]')])

    section('How the three agent roles worked','Independent readings are procedural safeguards within the same model setup.',[
      table(['Role','What it received and did','What it was kept separate from'],[
       ['Assigned extractor','Read the complete readable bundle and produced the structured record with evidence.','Other role answers and investment outcomes.'],
       ['Independent reader','Read the same source afresh and produced its own structured record.','The extractor\'s answer and critic verdicts.'],
       ['Backward critic','Reviewed every claim from the always-preassigned extractor against the source and common rules.','The independent reader\'s answer; it did not pick the better of two candidates.']],[.21,.45,.34]),
      p('Every filing used fresh one-role, one-filing agent contexts. The parent workflow finalized the two readings and critic judgments before comparing them. Original answers were retained rather than repeatedly generated until they agreed. The critic candidate was sealed to the assigned extractor. [S2]'),
      p('A supported verdict requires the whole claim to satisfy source evidence and definitions, including actor, security, units, timing and material conditions. Contradicted requires incompatible evidence or an explicit rule conflict. Insufficient evidence preserves missing support or unresolved interpretation.'),
      call('The agents used the same inherited model setup. They were not different model families, and shared-filesystem separation was procedural rather than a cryptographically isolated blind experiment. Shared errors remain possible.'),
      p('A backward critic can detect an omitted condition in a claim it sees. It cannot guarantee discovery of an objective omitted by both source readers. The independent second reading helps expose omissions, but does not replace an independent reference standard.'),
      p('Execution used 126 internal checkpoints: 125 of five filings and one of two. Reporting groups combined completed checkpoints into 25-filing reports, with a final 22-filing group. Group size changed reporting cadence, not the three-role review requirement.')])

    section('Mechanical quality checks and their limits','A technical pass establishes reproducibility and structural validity.',[
      table(['Check actually used','What it establishes','What it leaves open'],[
       ['Source and canonical-text hashes','The exact recorded input bytes/text have not changed.','Whether the source itself is correct or economically complete.'],
       ['Full-readable-delivery intervals','Every readable character range was served to each role.','Comprehension and unavailable documents.'],
       ['Schema validation','Required fields, permitted states and expected structures are valid.','Truth or category correctness.'],
       ['Exact quotation checks','The quoted text matches the cited canonical character span.','Whether the quote supports the whole interpretation.'],
       ['Every candidate claim reviewed once','The critic has a verdict for the required claim inventory.','Claims or objectives omitted from the candidate.'],
       ['Normalization replay','Saved drafts reproduce finalized record transformations.','A new independent semantic judgment.'],
       ['Preserved drafts and file inventories','Failures, repairs and prior results remain inspectable.','That a later repair proves the original meaning was correct.'],
       ['Sequential release gates','The next checkpoint follows passing technical checks.','A minimum semantic agreement or accuracy threshold.']],[.27,.36,.37]),
      p('The production summaries record passing delivery, schema, exact quotation and normalization replay checks. There are 119,360 exact-quotation entries across the records. Entries can repeat the same supporting text across fields or roles; they are not 119,360 independent facts. [S3]'),
      p('Mechanical citation or JSON repairs preserved their draft history. Model-capacity failures before source execution were operational retries, not selections among alternative answers. A missing temporary preservation helper near the end was replaced in a separately versioned recovery; the saved baseline was retained and reverified. No completed role was repeated to improve its score. [S11]')])

    section('Semantic safeguards and preproduction controls','Designed examples tested rule behavior before production; human accuracy remains unmeasured.',[
      p('Semantic safeguards address meaning: a common frozen codebook, exact actor/issuer attribution, funding and ownership qualifiers, category-specific abstention, two source readings and the backward critic. The qualification rules were shared across roles so a critic did not silently apply a different definition.'),
      table(['Earlier constructed-control exercise','Observed result','Interpretation'],[
       ['Extractor on eight designed fixtures','72 of 72 objective states matched the expected fixture answers.','The examples exercised specified rule boundaries.'],
       ['Independent reader on the same eight fixture designs','72 of 72 objective states matched.','A second execution passed those designed cases.'],
       ['Critic on eight unchanged and eight deliberately changed claims','16 of 16 verdicts matched; all eight changed claims were flagged.','The critic detected the constructed changes supplied to it.']],[.36,.31,.33]),
      p('These controls belong to the earlier v3 development exercise and are separate from the 627 production filings. They include rule-specific checks for conditionality, actor attribution, ownership overlap, historical versus current financing and transaction implementation. The constructed answers and development exposure prevent treating them as a natural-filing accuracy test. [S7]'),
      h('Three quality questions that remain different'),
      bullets(['Traceability: Can we reproduce the record and locate the cited source? Mechanical checks address this.',
               'Consistency: Do the readers agree, and does the critic support the assigned claims? The completed results measure this.',
               'Correctness: Do the measurements match independently established reference labels? The required natural-data acceptance criteria remain unmet.']),
      p('The user authorized automated experimental scaling without completing human review. That authorization did not turn model judgments into reference truth. Precision, recall and accuracy remain unestimated, and no objective category is accuracy-certified.'),
      p('The earlier literature probe provides background on source-based critics, omission checks, diverse judges and controlled-error exercises. Its paper links are a reading guide; the quality numbers in this report come from our local run, not from published benchmark scores. [S13]')])

    section('What the production run found','The first result is a usable measurement inventory with explicit uncertainty.',[
      fig('filing-groups.png','Production filings, n=627. The three groups are mutually exclusive; a filing in the positive group can also have unresolved other objectives.'),
      p('There are 265 filings with at least one eligible positive objective, 314 with all nine objectives eligible as not stated, and 48 with no eligible positive and at least one unresolved category. The three counts sum to 627. An additional way to view uncertainty is that 107 filings have at least one unresolved objective, including 59 that also have a positive objective. [S3]'),
      p('Across 5,643 filing/category decisions, 366 are eligible positive measurements and 5,112 are eligible not-stated measurements. The remaining 165 are excluded by the current experimental rule. Multiple categories can occur in a filing, so 366 positive decisions are not 366 separate filings.'),
      call('The frequency of a category is a description of this panel under these definitions. It does not rank the category\'s profitability, effectiveness or investment attractiveness.'),
      p('The 627 production filings contain 604 distinct issuer CIKs and a union of 500 reporter CIKs in source inventory metadata. Those identifiers are not validated campaign or economic-manager counts. Repeated issuer/party relationships must be addressed in the later investment evaluation. [S1, S3]')])

    category_order=sorted(LABELS,key=lambda key:o['categories'][key].get('eligible_present',0),reverse=True)
    category_rows=[]
    for key in category_order:
        row=o['categories'][key]; n=row.get('eligible_present',0); unresolved=627-n-row.get('eligible_not_stated',0)
        category_rows.append([LABELS[key],str(n),str(row.get('eligible_not_stated',0)),str(unresolved),f'{100*n/627:.1f}%'])
    section('Results for each objective category','Positive counts require matching nonunknown readings and critic support.',[
      table(['Objective','Positive','Not stated','Unresolved','Positive / 627'],category_rows,[.36,.14,.16,.17,.17]),
      fig('objective-positives.png','Eligible positive measurements among 627 filings. Categories overlap; the nine positive counts sum to 366 decisions, not 366 unique filings.'),
      p('Board representation and whole-company sale are the largest positive groups. Leadership change, capital structure and return of capital have few positive measurements. That sparsity limits how much we can infer about those individual categories and makes a complex prediction model easier to overfit.'),
      p('A small count can reflect actual disclosure frequency, our qualification rule, missing material, or reading error. The current data do not distinguish those causes reliably. We should not rewrite the category definitions simply to create more positives.')])

    section('What the agreement numbers actually measure','High overall consistency is dominated by shared negative classifications.',[
      table(['Measure','Calculation','Result'],[
       ['Reader agreement','5,581 matching states / 5,643 category decisions','98.9%'],
       ['Experimental objective eligibility','5,478 matching nonunknown states with critic support / 5,643','97.1%'],
       ['Critic support','18,848 supported assigned claims / 19,069 reviewed claims','98.84%'],
       ['Positive-set overlap','376 both-positive decisions / 408 decisions positive to either reader','92.2%']],[.29,.51,.20]),
      p('The first two measures answer different questions. Agreement includes shared uncertainty. Experimental eligibility requires agreement on present or not stated plus critic support. Matching answers can therefore remain excluded.'),
      table(['Both readers chose','Decisions','Treatment'],[
       ['Not stated','5,140','5,112 eligible; 28 lack critic support.'],
       ['Present','376','366 eligible; 10 lack critic support.'],
       ['Cannot determine','65','Excluded regardless of agreement.'],
       ['Different states','62','Excluded pending resolution.']],[.29,.17,.54]),
      p('Positive-set overlap focuses on the subset where at least one reader saw an objective. It is a descriptive intersection/union calculation, not precision or recall. Both readers can miss the same objective or agree on the same incorrect positive.'),
      p('Two-reader state frequencies are saved: two present readings give present frequency 1, and one present/one not-stated gives frequencies 0.5 and 0.5. These are counts divided by two, not calibrated truth probabilities. A value of 1 does not mean certainty, and 0.5 does not mean a measured 50% chance of truth. [S2, S3]')])

    section('Funding results and qualifications','A funding mention, a component and actual current borrowing are different units.',[
      table(['Raw reader output across 627 filings','Extractor','Independent reader'],[
       ['Funding status present',str(E['funding_status']['present']),str(B['funding_status']['present'])],
       ['Funding status not stated',str(E['funding_status']['not_stated']),str(B['funding_status']['not_stated'])],
       ['Funding status cannot determine',str(E['funding_status']['cannot_determine']),str(B['funding_status']['cannot_determine'])],
       ['Funding components',str(E['funding_components']),str(B['funding_components'])],
       ['Components labeled confirmed actual',str(E['funding_certainty']['confirmed_actual']),str(B['funding_certainty']['confirmed_actual'])],
       ['Components labeled possible',str(E['funding_certainty']['possible']),str(B['funding_certainty']['possible'])]],[.58,.21,.21]),
      table(['Type appears in a filing','Extractor filings','Independent-reader filings'],[
       ['Working capital','318','318'],['Borrowed funds, with all certainty states retained','203','204'],
       ['Personal funds','82','80'],['Contributions','83','82'],['Noncash distributions','32','30'],
       ['Fund net assets','30','30'],['Other','225','235'],['Unknown source component','57','51']],[.58,.21,.21]),
      call('These are raw experimental reader outputs, with overlapping types. The 203 borrowed-funds filings are not 203 proven debt-financed acquisitions. Possible, historical and unresolved components remain in those type counts.'),
      p('The critic reviewed 2,075 funding claims: 627 top-level funding answers plus 1,448 extractor components. It supported 2,032 and flagged 43. Support for a top-level summary does not automatically validate every component qualifier. The independent reader\'s components were not separately passed through the critic.'),
      p('Funding tuples differ descriptively in 332 filings. Actor wording, component granularity and qualifier choices can create differences without factual disagreement. A final mapping from these components to model features has not been frozen. [S5]')])

    section('Ownership and transaction results','These facts remain available as evidence, with specified feature exclusions.',[
      table(['Recorded rows across 627 filings','Extractor','Independent reader'],[
       ['Reporting-party rows','2,839','2,839'],['Ownership relation rows','4,130','4,377'],
       ['Transaction or contractual-fact rows','3,755','4,001']],[.58,.21,.21]),
      p('These are row counts, not unique people, shares, economic exposures or campaigns. An ownership relation can describe direct holdings, deemed ownership, an explicitly reported group aggregate or an explicit no-holding relationship. Supporting shareholders and other parties in exhibits can also appear in the raw inventory.'),
      p('For example, the same one million shares may be attributed to a fund, its manager and a controlling person. Adding three source-reported positions would invent three million shares of economic exposure. The workflow therefore retains overlap and attribution rather than summing those rows.'),
      table(['Critic checks of assigned extractor claims','Reviewed','Supported','Flagged'],[
       ['Ownership relations','4,130','4,078','52'],['Transactions or undertakings','3,755','3,693','62']],[.49,.17,.17,.17]),
      p('Ownership tuple strings differ in 480 filings; transaction row counts differ in 316. Punctuation, security descriptions and different grouping of the same undertaking can produce such differences. These counts are not measured factual-error or omission rates.'),
      call('The first model excludes LLM ownership-derived counts, sums, percentages or control features without reporter/target-security validation, and excludes transaction-fact counts. Extracting these fields did not authorize treating their raw row counts as economic signals. [S5]'),
      p('A transaction fact can still provide evidence for an objective or funding decision. Lower priority for a standalone feature does not make its material contractual conditions irrelevant.')])

    section('The 221 flags and the wider uncertainty queue','The counts overlap, so adding 221 and 165 would double-count objective decisions.',[
      table(['Flagged claim field','Claims','Current handling'],[
       ['Stated objectives','64','All are in the excluded objective set.'],['Funding','43','Preserve actor/type/certainty/acquisition link; map only after review.'],
       ['Ownership','52','Retain facts and flags; specified features excluded.'],['Transactions and contracts','62','Prioritize dependencies affecting objectives or funding.']],[.31,.16,.53]),
      p('The 221 critic flags affect 127 filings. Of the verdicts, 34 are contradicted and 187 are insufficient evidence. These remain critic judgments rather than independently established errors. The flagged share is 221 of 19,069 assigned claims, or 1.16%; that denominator includes identity and other relatively straightforward claims. [S6]'),
      table(['Excluded objective decisions','Count'],[['Reader disagreement','62'],['Both readers uncertain','65'],['Matching nonunknown states without critic support','38'],['Total excluded objective decisions','165']],[.78,.22]),
      p('Of those 165 objective decisions, 64 also have critic flags and 101 do not. A complete combined review inventory therefore contains <b>322 distinct field decisions</b>: 165 objectives, 43 funding claims, 52 ownership claims and 62 transaction claims. It is not 322 filings. The original 221-claim register remains unchanged.'),
      p('For the first feature study, the priority scope is all 165 unresolved objectives plus the 43 funding flags, together with material supporting transaction facts. The 107 objective/funding critic flags affect 73 filings; the full priority scope is wider because some unresolved objectives have no critic flag.'),
      p('Issue codes overlap: a claim can have timing, attribution and support problems simultaneously. The largest codes include inadequate support (151), temporal scope (50), definition ambiguity (49) and missing reference (37). They are not additive categories. Fifteen flags in one filing repeat an ownership-overlap issue; one recurring problem can create many claim flags.')])

    ex={item['case']['case_id']:item for item in a['worked_examples']}
    section('Worked examples from the completed extraction','These illustrate preserved judgments; none has been newly adjudicated here.',[
      h('Broad discussion language versus a specific proposal'),
      p(f"<b>{ex['B001_01']['case']['issuer']} - B001_01.</b> The filing describes discussions about management, capital allocation, operations and other possibilities. The readings did not promote that list into separate positive objectives. Funding includes working capital and a qualified possibility of margin loans. This illustrates why a topic mention and confirmed current borrowing are different measurements."),
      h('A materially incomplete contract condition'),
      p(f"<b>{ex['B118_02']['case']['issuer']} - B118_02, transaction.001.</b> The critic found that an ownership-cap description omitted existing shares held by the investor and affiliates from the cap test. The merger description could otherwise be right while the whole claim remained underqualified. The preserved verdict is contradicted."),
      h('A definition boundary'),
      p(f"<b>{ex['B119_02']['case']['issuer']} - B119_02, board representation.</b> The source discloses a conditional board-observer right. The critic identified uncertainty about whether an observer falls within a category centered on directors and board composition. The right itself can be real while its category remains unresolved."),
      h('Two readers can agree while missing evidence prevents use'),
      p(f"<b>{ex['B122_01']['case']['issuer']} - B122_01.</b> The filing refers to an unavailable detailed concerns letter. The critic challenged definitive negative governance and operational labels because the absent letter could contain a specific separate request. Matching negative labels remained excluded."),
      h('A reported funding code without a current-acquisition bridge'),
      p(f"<b>{ex['B124_02']['case']['issuer']} - B124_02.</b> Four working-capital claims were flagged because the holding history and contemplated acquisition did not establish the asserted actual current-funding link. The objection concerned timing and linkage, not proof that working capital had never been used."),
      p('Each example is traceable to the original case notes, candidate and critic record through the HTML explorer. The appropriate final resolution may uphold, correct or abstain; these examples do not select a new answer. [S6]')])

    section('How we should resolve the open decisions','Proposed adjudication process; no semantic revisions have been applied.',[
      table(['Problem type','Resolution approach','Permitted endpoint'],[
       ['Clear error under an existing rule','Recheck complete relevant source; propose a minimal correction; verify all qualifiers.','Corrected in a new derived revision layer.'],
       ['Critic objection not supported','Reassess source and existing rule without assuming the critic is right.','Original upheld with a documented rationale.'],
       ['Material evidence absent or source internally conflicting','Recover historically eligible evidence where authorized; preserve alternatives if unresolved.','Unknown or excluded field with an explicit gap.'],
       ['Definition genuinely ambiguous','Specify a policy decision, version changed rules and identify all affected cases.','New-version treatment, consistently applied beyond the flagged cases.']],[.28,.45,.27]),
      bullets(['Preserve the frozen v3 records, quotations, drafts and critic judgments. Add a separate adjudication record with old value, issue, evidence, proposed value, rule version and decision rationale.',
               'Group repeated patterns, but do not apply a blanket replacement without checking each source relation.',
               'Pilot the process on varied objective and funding issues before applying it to the priority queue. More model votes alone are not a truth standard.',
               'Keep subsequent returns and model-performance results hidden during adjudication. Do not prefer the interpretation that improves a backtest.',
               'If a rule changes, search the whole affected scope, including unflagged records. Correcting only flagged examples would create inconsistent treatment.']),
      p('Policy questions likely to need a decision include board observers, corporate-opportunity waivers, ongoing merger-related voting arrangements and what constitutes an independently meaningful issuer-directed intervention. The existing funding rule already requires actual current-acquisition support; many funding flags may be resolvable without changing that rule.'),
      call('A documented unknown is a valid resolution. Closing a review item does not require changing it to present or not stated, and it does not require discarding the entire filing.')])

    section('What the quality process cannot establish','The main unresolved risks are shared interpretation errors, omissions and historical completeness.',[
      table(['Remaining risk','Research consequence','Next safeguard'],[
       ['Shared model errors','Readers and critic can agree on the same wrong interpretation.','Independent references and, if separately specified, a different-model robustness exercise.'],
       ['Shared omissions','A critic cannot reject a claim that neither reader extracted.','Source-first reference review and omission-focused sampling.'],
       ['Missing or unreadable material','A technically complete readable bundle can still omit decisive evidence.','Category-specific abstention and historically eligible evidence recovery.'],
       ['Rare positive categories','High overall agreement can conceal weak behavior on scarce positives.','Report category-specific precision/recall with adequate independent labels.'],
       ['Selection and dependent filings','This panel need not represent all 13D events or independent campaigns.','Document coverage and design grouped/time-aware evaluation.'],
       ['Human-review gap','Automated acceptance does not estimate correctness.','Maintain the protected reference process; do not substitute AI answers into blank human worksheets.'],
       ['Source inconsistency','Quoted numbers or names can conflict within one filing.','Preserve alternatives rather than silently choosing a plausible value.']],[.27,.37,.36]),
      p('Accuracy is the share of reference decisions classified correctly. Precision asks how many positive predictions are correct. Recall asks how many true positives were found. The current reader agreement and critic-support rates calculate none of these because the independent natural-data reference is missing.'),
      p('The controls, exact quotations and preservation receipts strengthen traceability and specific rule checks. They do not remove these limits. Model labels remain noisy measurements, and resolving known flags alone cannot certify all unflagged answers.')])

    section('From extracted measurements to a ranking experiment','The next modeling comparison needs its own frozen specification.',[
      p('A feature is information supplied to a model, such as an objective state, its two-reader frequency, an unresolved-status indicator or a carefully qualified funding component. A target is the later outcome the model tries to rank. Training estimates the relationship from earlier observations; evaluation checks later observations not used in that fit.'),
      table(['Comparison','Inputs','Question answered'],[
       ['Structured-data baseline','Validated filing/company inputs available at the decision date.','How well can the baseline rank the eligible observations?'],
       ['Baseline plus objectives','The same baseline, sample, outcomes and evaluation periods, with specified objective measurements.','Does stated-intent information add incremental ranking value?'],
       ['Baseline plus objectives and qualified funding','Add a frozen funding transformation with unknown/possible/historical distinctions.','Does funding information add beyond objectives?']],[.29,.40,.31]),
      p('These are proposed comparisons, not fitted results. The previous non-LLM experiment used deterministic SEC/history/size/industry inputs; its own protocol explicitly says it is not yet a validated financial-fundamentals baseline. It compared raw-return ridge, rank-target ridge and a shallow tree in previously exposed chronological development data. [S9]'),
      p('The earlier design uses approximately 12- and 24-month horizons, annual fitting and only training observations whose outcome windows ended before the fitting cutoff. This avoids training on a future return that was not yet observable. Spearman correlation compares predicted ordering with realized ordering within an evaluation period. A high value indicates ranking alignment, not an after-cost investment return.'),
      p('Before a definitive comparison, resolve Bloomberg historical security/company mapping, information-release timing, original financial vintages and field definitions. Preserve common samples and report exclusions. Prevent the protected extraction reference set and any future investment test set from becoming tuning data. [S9, S10]'),
      call('Do not choose a more complex ML model to compensate for an unsettled measurement definition. First make the feature meanings and uncertainty treatment explicit.')])

    section('Decisions, readiness and learning checkpoints','What is settled, what remains open and what each next step will establish.',[
      table(['Decision or stage','Current position','Next action'],[
       ['Production extraction','Complete for 627 queued filings; 13 earlier cases separately complete.','Keep the frozen records as the baseline.'],
       ['Objective definitions','v3 frozen for the completed run.','Adjudicate uncertainty; version any changed boundary.'],
       ['Funding feature mapping','Candidate only; not frozen.','Specify treatment of actor, certainty and acquisition link.'],
       ['Ownership and transaction-count features','Specified first-model exclusions remain in force.','Use facts for evidence; revisit features only under a separate validated scope.'],
       ['Natural-data extraction accuracy','Unmeasured; human-reference acceptance unmet.','Complete an independent-reference evaluation without contaminating protected worksheets.'],
       ['Historical financial baseline','Timing/mapping remediation is separate pending work.','Correct and verify the vendor pilot before scaling a definitive comparison.'],
       ['Extraction-enhanced ranking','Not fitted.','Freeze comparable samples, targets, features, preprocessing and later-data evaluation.']],[.29,.36,.35]),
      h('Suggested order of work'),
      p('First establish the adjudication record and pilot the priority objective/funding cases. Then freeze feature transformations and missingness treatment. Resolve financial-input eligibility in parallel where authorized. Finally run the controlled baseline-versus-added-text comparison and publish its learning checkpoint.'),
      h('Questions to use in the next discussion'),
      bullets(['Which ambiguity should be a policy definition, and which should remain a source-level unknown?',
               'What evidence would persuade us that a positive objective was missed by both readers?',
               'What is the minimum independently labeled sample needed for each rare category?',
               'How will we keep uncertain features and incomplete financial coverage from changing the comparison sample unfairly?',
               'What would count as economically useful improvement after costs and implementation constraints?'])])

    section('Glossary and evidence map','Use the HTML appendices to inspect every production filing and every critic flag.',[
      table(['Term','Meaning in this project'],[
       ['Extraction','Converting disclosed text into structured source-backed measurements.'],
       ['Codebook or protocol','Versioned definitions that specify how to classify the text.'],
       ['Canonical text','The exact stored text whose character offsets identify quotations.'],
       ['Hash','A fingerprint used to detect changes in bytes or text.'],
       ['Source-only reader','A reader instructed to use its assigned evidence rather than other answers or outcomes.'],
       ['Backward verification','Checking a supplied claim against source evidence and the common definitions.'],
       ['Abstention','Recording cannot determine instead of forcing a definite answer.'],
       ['Adjudication','A documented follow-up decision about a disputed measurement.'],
       ['Feature','An input to the later investment-ranking model.'],
       ['Target','The future outcome the model is trained to rank.'],
       ['Ridge regression','A linear prediction model that penalizes large coefficients to reduce overfitting.'],
       ['Rank target','Training on relative outcome order instead of raw return magnitude.'],
       ['Shallow decision tree','A model using a small number of if-then splits rather than many fitted branches.'],
       ['Look-ahead or leakage','Using information that would not have been known at the decision or fitting date.'],
       ['Holdout','Observations kept out of learning and tuning for a later evaluation.'],
       ['Incremental value','Improvement from text beyond the same baseline on a comparable sample.']],[.29,.71]),
      p('The HTML report includes a searchable 627-filing explorer, a searchable 221-flag register, the numerical evidence files and links back to source case notes. The PDF is the narrative reading copy. The report calculation reads finalized records and adds no new extraction interpretations.'),
      p('For independent reproduction, run analyze.py and build_report.py with the project Python and the documented environment variables. The calculation records its source hashes, checks all 1,881 role deliveries, reconciles the headline counts to the checkpoint summaries, and requires a byte-identical re-run of the analysis. See verification.json for report-specific checks.')])
    return sections


SOURCES=[
 ('S1','Frozen production queue and exclusions','research/runs/extraction-batches/20261028-v1/queue.json'),
 ('S2','Frozen production protocol','research/runs/extraction-batches/20261028-v1/protocol.json'),
 ('S3','Reconciled aggregate calculations','research/runs/extraction-overview/20261102-v1/overview.json'),
 ('S4','Common extraction rules version 3','research/protocol/extraction-common-rules-v3.md'),
 ('S5','Feature use policy fixed before production','research/runs/extraction-revision/20261027-v3/feature-use-policy.json'),
 ('S6','Flag inventory and full original register','research/runs/extraction-overview/20261102-v1/flag-inventory.json'),
 ('S7','Earlier version 3 development and control summary','research/runs/extraction-revision/20261027-v3/summary.json'),
 ('S8','Final queue completion verification','research/runs/extraction-batches/20261028-v1/reporting-25-v1/batch-030/completion-verification.json'),
 ('S9','Earlier non-LLM ranking specification','research/protocol/ranking-no-llm-v1.json'),
 ('S10','Bloomberg timing and identity review','research/runs/bloomberg-timing/20261026-v1/index.html'),
 ('S11','Execution completion and integrity recovery receipts','research/runs/extraction-batches/20261028-v1/overnight-20261101-v1/completion-20261102.json'),
 ('S12','Field-level report calculations and input fingerprints','research/docs/extraction-results-review-20261102/analysis.json'),
 ('S13','Earlier literature probe on reviewing LLM extraction','research/docs/llm-extraction-review-research-20261027/index.html')]
