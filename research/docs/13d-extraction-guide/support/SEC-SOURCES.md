# Schedule 13D: primary-source research for the extraction guide

Researched 2026-09-23. Explanatory research; no filing-level judgments, protocol changes, or model calls. None of the protected 52/200 human-first cases was examined for this note. Regulatory descriptions below explain the data, rather than determining anyone's compliance obligation.

## Sources and verification limits

- **Official form and instructions:** [2025 Code of Federal Regulations, title 17, volume 4](https://www.govinfo.gov/content/pkg/CFR-2025-title17-vol4/pdf/CFR-2025-title17-vol4.pdf), §240.13d-101, printed pages 191–195 (PDF pages 201–205). The government publication expressly permits republication. The live eCFR endpoints and individual section PDF failed in the browser; the full official volume was successfully read. This is an April 1, 2025 codification, not a certification that no later amendments exist.
- **Who files, covered securities, and transitions:** [Official 2025 §240.13d-1](https://www.govinfo.gov/content/pkg/CFR-2025-title17-vol4/pdf/CFR-2025-title17-vol4-sec240-13d-1.pdf). Its last page also begins §240.13d-2.
- **Rule changes and dates:** [SEC final release 33-11253 / 34-98704](https://www.sec.gov/files/rules/final/2023/33-11253.pdf), especially opening summary/table, sections II.E–G, and adopted rule text; [SEC adoption announcement](https://www.sec.gov/newsroom/press-releases/2023-219).
- **Structured format rollout:** [EDGAR release 23.4, December 18, 2023](https://www.sec.gov/submit-filings/edgar-news-announcements/edgar-release-23-4).
- **Current technical-version inventory:** [SEC technical specifications](https://www.sec.gov/submit-filings/technical-specifications). Schedule 13D/13G version 2.3 is dated April 15, 2026; version 2.2, March 16, 2026, introduced multiple CUSIP support. The inventory/change notes were read, not the entire XSD archive. No XML field-level schema claims are made here.

## What a 13D signifies—and does not signify

Rule 13d-1(a) generally requires a person acquiring beneficial ownership above **5% of a covered class** to file Schedule 13D, unless an alternative reporting provision applies. This is more than 5%, not at least 5%, and a class-level holding, not automatically a percentage of the entire issuer's economic value. Rule 13d-1(i) includes section 12 registered equity, specified insurance-company equity and equity of registered closed-end investment companies; it excludes non-voting classes. Therefore, “all listed common stocks” is an incomplete description of the legal universe. [Official rule](https://www.govinfo.gov/content/pkg/CFR-2025-title17-vol4/pdf/CFR-2025-title17-vol4-sec240-13d-1.pdf).

Schedule 13G alternatives depend on investor type and conditions. Crucially, an otherwise passive filer under 13d-1(c) becomes subject to 13D when ownership equals or exceeds 20%, under 13d-1(f). Consequently **13D form type is not a sufficient activist label**. Reporting person, investment mandate, issuer relationship, and current objective are separate research attributes. A joint filing can cover several reporting persons; legal identity and group status require the actual disclosures. [Official rule, paragraphs (b)–(k)](https://www.govinfo.gov/content/pkg/CFR-2025-title17-vol4/pdf/CFR-2025-title17-vol4-sec240-13d-1.pdf).

## Information architecture

The following is a paraphrase of the [official Schedule 13D and instructions](https://www.govinfo.gov/content/pkg/CFR-2025-title17-vol4/pdf/CFR-2025-title17-vol4.pdf#page=201), not an empirical claim that every filing supplies every field clearly.

| Location | What it asks for | Extraction implication |
|---|---|---|
| Main cover | Issuer, security class, CUSIP, communications contact, event date requiring filing, amendment number and prior-13G transition checkbox | Keep event date separate from SEC filing/acceptance time. Contact lawyer is not automatically the investor. |
| Reporting-person cover, one per person | Legal name, group checkbox, funds code, proceedings checkbox, citizenship/organization; sole/shared voting and disposition powers; aggregate shares; excluded shares checkbox; percentage and person type | Repeat person records; keep numeric holdings, power and disclaimers separate. |
| Item 1, Security and Issuer | Class title, issuer name, principal executive-office address | Security identity, not validated ticker history or market capitalization. |
| Item 2, Identity and Background | Entity organization, principal business and office; individuals' occupation/employer and citizenship; specified criminal and securities-related civil proceedings over five years | Distinguish fund, adviser, general partner, controlling person, officer and other mentioned party. Proceedings questions are narrow—not a comprehensive reputation score. |
| Item 3, Source and Amount of Funds or Other Consideration | Amount/source, acquisition-related borrowing and parties; method if acquired other than by purchase | Open-market buying, compensation, conversion, distribution and transaction consideration can have different economic meaning. Reported acquisition expenditure is not current position value. |
| Item 4, Purpose of Transaction | Purposes of acquisition; plans/proposals for the a–j topics below | Read affirmative objectives, conditions and attribution. Generic rights reservations are not concrete demands. |
| Item 5, Interest in Securities | Each person's aggregate/class percentage, rights to acquire, voting/disposition powers, recent transactions, rights to dividends/proceeds and date holdings cease to exceed 5% | Ownership graph and transaction records, not a sum of all cover-page percentages. |
| Item 6, Contracts and Relationships | Securities-related arrangements, counterparties, transfer/voting/proxy provisions, derivatives, lending and pledged/contingent interests | Terms may qualify the meaning of holdings and plans. A derivative reference does not automatically mean all notional shares are beneficially owned. |
| Item 7, Exhibits | Joint filing and relevant financing, control, transaction, voting, option and other agreements | Inventory, retrieve and read material incorporated evidence; Item 4 can point to where the actual demand appears. |
| Signatures | Certification, signers, titles, signature date; authority for representatives where applicable | Signature date and signatory are separate from event date, public acceptance time and investor identity. |

General instruction B permits exhibits to supply all or part of an item by explicit incorporation. Instruction C extends information requirements to certain partners, group members and controlling people/entities. Thus not every name in Item 2 is necessarily a separate reporting person, and not every item is self-contained. [Official instructions](https://www.govinfo.gov/content/pkg/CFR-2025-title17-vol4/pdf/CFR-2025-title17-vol4.pdf#page=202).

## Item 4 a–j in plain language

| Form topic | Plain-language content |
|---|---|
| (a) | Acquire more securities or dispose of securities |
| (b) | Extraordinary transaction: merger, reorganization, liquidation |
| (c) | Sell or transfer a material amount of assets |
| (d) | Board or management changes, including director numbers, terms or vacancies |
| (e) | Material capitalization or dividend-policy change |
| (f) | Other material business/corporate-structure change, including specified closed-end fund investment-policy changes |
| (g) | Charter/bylaw changes or other actions potentially impeding acquisition of control |
| (h) | Delisting or ending qualifying quotation |
| (i) | Becoming eligible to terminate Exchange Act registration |
| (j) | Similar actions |

Source: [Schedule 13D, Item 4](https://www.govinfo.gov/content/pkg/CFR-2025-title17-vol4/pdf/CFR-2025-title17-vol4.pdf#page=203). These are statutory disclosure topics, **not ten activism labels**. For example, a sponsor describing its agreed merger and an outsider demanding an issuer sale can both discuss (b), with very different research meanings. A research taxonomy should separately represent topic, actor, current action, relationship, specificity, stage and evidence completeness. That separation is a proposed modeling choice, not an SEC classification.

## Codes that can be decoded mechanically

Funds-source codes: SC = subject company; BK = bank; AF = reporting-person affiliate; WC = reporting-person working capital; PF = reporting-person personal funds; OO = other. Multiple codes can apply. The code alone does not fully explain acquisition financing; preserve Item 3 narrative. [Cover instruction (4)](https://www.govinfo.gov/content/pkg/CFR-2025-title17-vol4/pdf/CFR-2025-title17-vol4.pdf#page=202).

Reporting-person codes: BD = broker dealer; BK = bank; IC = insurance company; IV = investment company; IA = investment adviser; EP = employee benefit plan or endowment fund; HC = parent holding company/control person; SA = savings association; CP = church plan; CO = corporation; PN = partnership; IN = individual; OO = other. Multiple applicable codes may be reported. **IA does not mean hedge fund**, and there is no “activist hedge fund” code. CO/PN describes organizational form rather than investment mandate. [Cover instruction (14)](https://www.govinfo.gov/content/pkg/CFR-2025-title17-vol4/pdf/CFR-2025-title17-vol4.pdf#page=202).

## Ownership, transactions and contracts: common extraction traps

- The same block can be reported by a fund, its adviser, general partner and controller. Item 5 asks for separate person-level information and shared-power relationships; adding all reported amounts without proving disjointness can double count. Preserve explicit aggregate/group figures and the holding relationships instead. This is a research safeguard inferred from the form's person-level and shared-power structure. [Item 5](https://www.govinfo.gov/content/pkg/CFR-2025-title17-vol4/pdf/CFR-2025-title17-vol4.pdf#page=204).
- Item 5(c) covers transactions during **the past 60 days or since the most recent Schedule 13D, whichever is less**. Requested details include transacting person, date, quantity, price per share/unit, where and how. It is not a complete lifetime trading record or necessarily the entire position cost history. [Item 5(c)](https://www.govinfo.gov/content/pkg/CFR-2025-title17-vol4/pdf/CFR-2025-title17-vol4.pdf#page=204).
- Percentage denominators may use the issuer's recent available SEC filings, subject to knowledge of inaccuracy. Rights to acquire underlying shares need special treatment. Preserve the filer-stated denominator/date/basis; a simple shares/percentage reversal is at best an estimate and can fail with rounding or person-specific rights. [Item 5 and rule 13d-1(j)](https://www.govinfo.gov/content/pkg/CFR-2025-title17-vol4/pdf/CFR-2025-title17-vol4.pdf#page=204), [rule 13d-1](https://www.govinfo.gov/content/pkg/CFR-2025-title17-vol4/pdf/CFR-2025-title17-vol4-sec240-13d-1.pdf).
- Item 6 expressly covers puts, calls, security-based swaps and other derivatives, including issuer securities used as reference securities. The 2023 final rule clarified disclosure; it did **not** adopt the proposed blanket new rule deeming certain cash-settled derivative holders beneficial owners. Preserve derivative economic exposure separately from reported beneficial ownership. [SEC final rule, summary and section II.E](https://www.sec.gov/files/rules/final/2023/33-11253.pdf).

## Historical timing and amendments

Before the February 5, 2024 effective date, the usual initial 13D deadline was 10 calendar days and material amendments were required promptly. The 2023 adopted amendments changed the initial deadline to five business days and material amendments to two business days. The rules also address losing 13G eligibility. Avoid applying current timing retroactively to the 2013–2024 research sample. [SEC final release, opening table and effective date](https://www.sec.gov/files/rules/final/2023/33-11253.pdf).

A Schedule 13D/A is an update, not necessarily a complete standalone report. Rule 13d-2(a) covers material changes; an acquisition/disposition of at least one percentage point of the class is deemed material, while smaller changes may also be material. Preserve amendment number, earlier filings incorporated, changed items and disclosure-time availability. A later amendment cannot be used as information available at the initial event. [Official rule 13d-2(a)](https://www.govinfo.gov/content/pkg/CFR-2025-title17-vol4/pdf/CFR-2025-title17-vol4-sec240-13d-1.pdf#page=4).

For research alignment, keep at least event date, transaction date, SEC filing date, SEC acceptance timestamp, exhibit/letter date, and signature date separate. Choosing a first tradable market session requires the actual acceptance time, exchange calendar and a predefined execution convention; the form's event date is not a substitute. This is a research-design implication, not a regulatory prescription.

## Structured XML: useful but not semantic labels

EDGAR introduced voluntary structured 13D/13G filing on December 18, 2023; mandatory structured compliance began December 18, 2024. HTML/ASCII therefore coexist with XML in the 2024 historical sample. XML structures the filing disclosure, excluding exhibits from the structured mandate; it does not decide whether narrative describes an activist demand or a valuable investment. [SEC EDGAR release 23.4](https://www.sec.gov/submit-filings/edgar-news-announcements/edgar-release-23-4), [SEC final rule, section II.F](https://www.sec.gov/files/rules/final/2023/33-11253.pdf).

The current SEC technical inventory lists 2.3 (April 15, 2026) and notes that 2.2 added multiple CUSIPs. Store schema/format version and support repeated security identifiers rather than assuming today's rendering or a single scalar identifier fits every historical/future filing. The actual schema archive still needs inspection before implementing version-specific fields. [SEC technical specifications](https://www.sec.gov/submit-filings/technical-specifications).

## Consequence for the user's attribute redesign

Separate three layers: (1) filing facts and exact supporting passages; (2) explicit research interpretations such as issuer relationship and concrete current objective; (3) outside enrichment such as historical security mapping, market cap, liquidity and dated hedge-fund mandate evidence. The form does not prescribe market cap, daily prices, hedge-fund quality, campaign success, or return forecasts. Treat absent parser output as unresolved evidence availability, not a negative label. This is a proposed research design based on the form structure, not a change to the frozen project protocol.
