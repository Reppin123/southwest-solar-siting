# BLM Application and Policy Brief: Utility-Scale Solar (and Co-Located Load) in CA, AZ, NV, NM, UT

Prepared for: Aki
Prepared: 2026-10-21 (all sources checked on this date unless another date is given)
Companion files: `deliverables/sources_blm.md` (every source, its date, and how it was checked), `deliverables/Southwest_Solar_Sites.xlsx` and the dashboard (`uv run --script app/serve.py`, use the "BLM-only" toggle) for the actual candidate parcels.

This is a practical guide, not legal advice. Federal policy on solar on public land changed several times in 2025 and 2026 and is still being litigated. Confirm anything that drives money or schedule with the BLM field office and a land-use attorney before filing.

---

## 1. Bottom line (read this first)

1. **You can still apply.** The regulations for solar rights-of-way (ROW) on BLM land (43 CFR Part 2800) are in force, and the 2024 Western Solar Plan still governs where BLM accepts solar applications (about 31 million acres across 11 states). BLM is still moving some solar projects: a Notice of Intent for an EIS on the Mosey Solar Project in Clark and Nye Counties, NV was published on 2026-07-29 ([Federal Register 2026-15270](https://www.federalregister.gov/documents/2026/07/29/2026-15270/notice-of-intent-to-prepare-a-resource-management-plan-amendment-and-environmental-impact-statement)).
2. **Expect a slow, political review.** Since a 2025-07-15 Interior memo, almost every BLM step on a solar project goes to the Secretary's office ([DOI memo, 2025-07-15](https://www.doi.gov/sites/default/files/documents/2025-07/dcos-pol-memo-doi-review-procedures-wind-and-solar-projects-2025-07-15-1-signed.pdf)). A federal court blocked that memo on 2026-04-21, but **only for members of the nine plaintiff trade associations** ([Holland & Hart summary, 2026](https://www.hollandhart.com/federal-court-halts-wind-and-solar-permitting-freeze)). If your company is not a member of one of those groups (for the Southwest the most relevant is Interwest Energy Alliance), the memo still applies to you.
3. **Rent is now set by statute and is mostly a revenue fee.** Since 2025-07-04 you pay the greater of a small acreage rent or **3.9 percent of gross electricity sales** from the public-land share of the project ([43 CFR 2806.52](https://www.ecfr.gov/current/title-43/subtitle-B/chapter-II/subchapter-B/part-2800/subpart-2806/subject-group-ECFR8cbf73f23187665/section-2806.52); [Federal Register 2025-14627](https://www.federalregister.gov/documents/2025/08/01/2025-14627/revisions-to-the-regulations-regarding-intermittent-energy)). The 2024 rule's 80 percent capacity-fee discount is gone.
4. **Federal tax credits for new solar are effectively closed for a project starting BLM permitting today.** Solar had to begin construction by 2026-07-04, or be placed in service by 2027-12-31, to keep the 45Y/48E credits ([SEIA summary of the 2025 law](https://seia.org/research-resources/clean-energy-provisions-big-beautiful-bill/)). A BLM project filed now cannot realistically be built by end of 2027. Battery storage keeps its credit longer (phase-down starts after 2032) but faces foreign-entity rules. Model a new BLM solar project **without** solar ITC/PTC.
5. **What to file first:** a pre-application meeting request with the BLM field office for your best "Available" parcel near a substation with headroom, and, in parallel, a utility interconnection request (site control rules apply). See the 10-step plan in section 11.

---

## 2. What changed in 2025 to 2026 (and what it means today)

| Date | Action | What it does | What it means for you today (2026-10-21) |
|---|---|---|---|
| 2025-01-20 | [EO 14156, Declaring a National Energy Emergency](https://www.federalregister.gov/documents/2025/01/29/2025-02003/declaring-a-national-energy-emergency) (90 FR 8433) | Emergency permitting for "energy". The order defines energy as oil, gas, uranium, coal, biofuels, geothermal, hydro and critical minerals. | Solar and wind are **not** in the definition (checked in the order text), so emergency fast-track procedures do not help a solar ROW. (Our reading of the text.) |
| 2025-02-25, final 2026-01-08 | CEQ removed its NEPA regulations ([interim](https://www.federalregister.gov/documents/2025/02/25/2025-03014/removal-of-national-environmental-policy-act-implementing-regulations), [final](https://www.federalregister.gov/documents/2026/01/08/2026-00178/removal-of-national-environmental-policy-act-implementing-regulations)) | Agencies now use their own NEPA procedures. | BLM uses the DOI NEPA regulations as revised 2025-07-03 and finalized 2026-02-24 ([DOI rule](https://www.federalregister.gov/documents/2026/02/24/2026-03708/national-environmental-policy-act-implementing-regulations)) and the DOI NEPA Handbook, with BLM-specific procedures revised 2026-04-28 ([notice](https://www.federalregister.gov/documents/2026/04/28/2026-08235/national-environmental-policy-act-implementing-procedures-for-the-bureau-of-land-management)). Ask the field office which documents and page limits apply to your project. |
| 2025-05-14 | [Interior announces it will rescind the 2024 Renewable Energy Rule](https://www.blm.gov/press-release/interior-initiate-action-rescind-blms-intermittent-energy-rule) | Announcement only; a proposed rescission was to follow in the Federal Register. | As of 2026-10-21 we found **no** proposed or final rescission in the Federal Register (API search of documents affecting 43 CFR 2800 since 2025-01-01 returned only the 2025-08-01 fee rule). A July 2026 review of the federal regulatory agenda says it is still unpublished ([Columbia Sabin Center, 2026-07-22](https://blogs.law.columbia.edu/climatechange/2026/07/22/trump-administrations-unified-agenda-suggests-major-reversals-on-climate-safeguards/)). The non-fee parts of the 2024 rule (application steps, prioritization, leasing in designated leasing areas) are still in the eCFR. Could change with little notice. |
| 2025-07-04 | One Big Beautiful Bill Act, Public Law 119-21, section 50302 | Sets solar/wind acreage rent and a 3.9 percent capacity fee by statute; ends the Secretary's discretion to discount. Separately terminates 45Y/48E for wind and solar (see 2026-07-04 row). | Rent formula and capacity fee in section 6 below. Fee discounts for domestic content and project labor agreements are gone. |
| 2025-07-07 | [EO 14315, Ending Market Distorting Subsidies for Unreliable, Foreign-Controlled Energy Sources](https://www.federalregister.gov/documents/2025/07/10/2025-12961/ending-market-distorting-subsidies-for-unreliable-foreign-controlled-energy-sources) | Directs strict enforcement of credit cutoffs and review of preferences for wind and solar. | Basis for the Interior memo below and for IRS Notice 2025-42. |
| 2025-07-15 | [DOI memo: Departmental review procedures for wind and solar](https://www.doi.gov/sites/default/files/documents/2025-07/dcos-pol-memo-doi-review-procedures-wind-and-solar-projects-2025-07-15-1-signed.pdf) | 69 listed actions (ROW applications, ROW grants, cost recovery agreements, NEPA documents, ESA consultations, bonds, rent determinations, and "any other similar" action) need review by the Executive Secretariat, the Deputy Secretary and final review by the Secretary. | Every step can stall. Press reported a roughly five-month freeze on BLM solar actions until a Nevada project (Libra) advanced in December 2025 ([pv magazine, 2025-12-17](https://pv-magazine-usa.com/2025/12/17/after-a-five-month-freeze-blm-finally-advances-a-solar-project/)) and about 20 solar projects back under review by March 2026 ([E&E News, 2026-03-17](https://www.eenews.net/articles/interior-bends-on-solar-but-wind-energy-on-public-lands-remains-stalled/)). |
| 2025-07-23 | [EO 14318, Accelerating Federal Permitting of Data Center Infrastructure](https://www.federalregister.gov/documents/2025/07/28/2025-14212/accelerating-federal-permitting-of-data-center-infrastructure) (90 FR 35385) | Interior and DOE to offer authorizations on sites they identify for "Qualifying Projects" (data centers over 100 MW of new load, or $500M+ capex). Section 9 covers federal lands. | Opens a door for data centers on federal land, but the order's list of supporting energy infrastructure names gas, coal, nuclear, geothermal and "dispatchable baseload" sources and transmission; it does not name solar. A solar-only power plan for a federal-land data center will not get special treatment under this order. |
| 2025-08-01 | [BLM final rule: Revisions to the Regulations Regarding Intermittent Energy](https://www.federalregister.gov/documents/2025/08/01/2025-14627/revisions-to-the-regulations-regarding-intermittent-energy) (90 FR 36111) | Writes the statutory rent and 3.9 percent capacity fee into 43 CFR 2806.50 to 2806.52; effective 2025-08-01. | Current fee rules. BLM billing guidance: [IM 2026-003, 2025-12-16](https://www.blm.gov/policy/im-2026-003). |
| 2025-08-01 | Secretary's Order 3438 ("capacity density") | Tells Interior to weigh energy output per acre when evaluating projects; solar ranks low on that metric (as described in [Holland & Hart](https://www.hollandhart.com/federal-court-halts-wind-and-solar-permitting-freeze) and [E&E News](https://www.eenews.net/articles/burgums-density-order-creates-new-roadblock-for-renewables/)). | Expect BLM to ask for denser layouts or smaller footprints, and to compare your project against "denser" alternatives in NEPA. We could not open the order text itself on doi.gov; the description here comes from the court summary and press. |
| 2025-08-15 | IRS Notice 2025-42 | Removed the 5 percent cost safe harbor for starting construction on wind and solar over 1.5 MW. | Vacated by the US District Court for D.C. on 2026-06-06 (*Oregon Environmental Council v. IRS*, No. 25-4400) ([KPMG](https://kpmg.com/us/en/taxnewsflash/news/2026/06/court-vacates-notice-2025-42-eliminated-safe-harbor-construction-wind-solar.html)). Only matters for projects that claim to have started before 2026-07-04. |
| 2026-04-21 | Preliminary injunction, US District Court for Massachusetts (Chief Judge Casper) ([Holland & Hart](https://www.hollandhart.com/federal-court-halts-wind-and-solar-permitting-freeze)) | Blocks the 2025-07-15 DOI memo, SO 3438 (capacity density), a USFWS IPaC restriction, an Army Corps memo and an offshore M-Opinion. | **Applies only to members of the nine plaintiff trade associations**, not nationwide. The government may appeal. If you are developing, check whether joining a plaintiff association (for example Interwest Energy Alliance) brings you under the injunction; ask counsel. |
| 2026-05-12 | BLM rescinded the 2024 Public Lands (Conservation and Landscape Health) Rule ([Federal Register 2026-09386](https://www.federalregister.gov/documents/2026/05/12/2026-09386/rescission-of-conservation-and-landscape-health-rule); context in [CATF, June 2026](https://www.catf.us/2026/06/how-blms-repeal-public-lands-rule-could-slow-clean-energy-deployment/)) | Removes "mitigation leasing" as a tool to offset project impacts. | Fewer formal mitigation options; plan to propose on-site and compensatory mitigation yourself. |
| 2026-06-18 | FERC show-cause orders on large-load interconnection to the six RTOs/ISOs (including CAISO) ([White & Case](https://www.whitecase.com/insight-alert/ferc-orders-grid-operators-promptly-revise-or-justify-interconnection-rules-data)) | Defines large loads as over 50 MW at over 69 kV; RTOs must justify or revise their tariffs. Rulemaking docket RM26-4 stays open. | Affects data center hookups in CAISO territory. APS, SRP, TEP, PNM, NV Energy and PacifiCorp are not RTOs, so state commission rules (section 10) matter more there. |
| 2026-07-04 | Begin-construction deadline for 45Y/48E wind and solar | After this date, a new solar project must be placed in service by 2027-12-31 to qualify ([SEIA](https://seia.org/research-resources/clean-energy-provisions-big-beautiful-bill/); [Kirkland](https://www.kirkland.com/publications/kirkland-alert/2025/08/one-big-beautiful-bill-act-brings-big-changes-to-green-energy-tax-credits)). | A BLM solar project filed now gets no solar ITC/PTC in a realistic schedule. Standalone or paired storage may still qualify under 48E (phase-down after 2032) subject to foreign-entity restrictions. |
| 2026-07 | Boulder City, NV: BLM let an approved solar-plus-storage ROW (Townsite Solar 2) be repurposed for a data center using a Determination of NEPA Adequacy ([Center for Western Priorities, 2026-07](https://westernpriorities.org/2026/07/trump-admin-swaps-out-solar-project-for-data-center-on-blm-land/), an advocacy group) | Shows BLM is willing to authorize data center load on existing ROWs. | Possible path for co-location; also a litigation and community-opposition risk. We have not seen the BLM decision document itself. |

---

## 3. The 2024 Western Solar Plan: what land is open

**Official basis:** Record of Decision and Approved Resource Management Plan Amendments for Utility-Scale Solar Energy Development, signed 2024-12-19 ([Federal Register notice 2024-30953, 2024-12-27](https://www.federalregister.gov/documents/2024/12/27/2024-30953/notice-of-availability-of-the-approved-resource-management-plan-amendments-and-record-of-decision); [ePlanning project page with the ROD](https://eplanning.blm.gov/eplanning-ui/project/2022371/510)). Governors of California and Utah appealed; the BLM Director rejected both appeals ([Federal Register 2025-00753, 2025-01-15](https://www.federalregister.gov/documents/2025/01/15/2025-00753/blm-directors-response-to-the-appeals-by-the-governors-of-california-and-utah-of-the-blm-state)). As of 2026-10-21 we found no Federal Register action revoking or amending the plan.

**The rule for "Available" land (quoted from the FR notice):** after resource exclusions and excluding slopes over 10 percent, public lands are available if they are **within 15 miles of an existing or planned transmission line of at least 69 kV**, or are **"previously disturbed"** under criteria in the ROD. About 31 million acres are available, including about 3.8 million acres of "avoidance" lands (open, but with more conflicts). About 131 million acres are excluded.

**Acres by state (computed by us from BLM's ROD GIS layer, `BLM_Natl_Solar_PEIS_ROD.gdb`, downloaded by the land helper; approximate, rounded to 0.01 million acres):**

| State | Available | Avoidance | Under the California Desert plan (DRECP/CDCA) | Excluded |
|---|---|---|---|---|
| Arizona | 2.81 M | 0.01 M | n/a | 8.98 M |
| California | 0.16 M | 0.02 M | 10.83 M | 3.96 M |
| Nevada | 8.85 M | 2.99 M | n/a | 32.89 M |
| New Mexico | 4.02 M | 0.01 M | n/a | 8.65 M |
| Utah | 4.78 M | 0.23 M | n/a | 16.38 M |

Cross-check: the 11-state totals from the same layer are 27.9 M available plus 3.82 M avoidance, which matches the "about 31 million, including about 3.8 million avoidance" in the FR notice. The layer also has an "Other" class (about 5.3 M acres across 11 states) that we could not define from the metadata; ask BLM before relying on it.

**California is different.** In the California desert, solar siting on BLM land follows the 2016 Desert Renewable Energy Conservation Plan (DRECP) and its Development Focus Areas, not the 2024 availability rule ([BLM DRECP page](https://www.blm.gov/programs/planning-and-nepa/plans-in-development/california/desert-renewable-energy-conservation-plan)). The GIS shows 10.83 M acres of BLM land in California under "DRECP/CDCA". If a California site is on BLM land, check it against the DRECP DFA map, not just the Western Solar Plan layer.

**Solar Energy Zones (SEZs) and priority areas.** BLM's regulations treat "designated leasing areas, which include solar energy zones, development focus areas, and renewable energy development areas" as preferred areas and prioritize applications there ([43 CFR 2804.35(b)(1)](https://www.ecfr.gov/current/title-43/subtitle-B/chapter-II/subchapter-B/part-2800)). The SEZs from the 2012 plan are mapped on the BLM solar program site ([blmsolar.anl.gov](https://blmsolar.anl.gov/), which blocked automated access on 2026-10-21) and in the team's land layer `data/processed/land/solar_energy_zones.geojson` when that is built. We could not confirm from primary text whether the 2024 ROD created a separate "priority area" category beyond SEZs/DLAs; read the ROD on ePlanning or ask the state office. In the dashboard, treat SEZ/DLA parcels as the strongest BLM candidates.

**Important:** "Available" means BLM will accept an application. It is not a promise of approval. No project is authorized by the plan itself; each needs its own NEPA review ([BLM press release, 2024-12-20](https://www.blm.gov/press-release/interior-department-finalizes-framework-future-solar-development-public-lands)).

---

## 4. Where the competition already is (team data)

The infra helper pulled active BLM solar ROW cases from BLM's Mineral and Land Records System on 2026-10-21 (`data/processed/infra/blm_solar_row_cases.geojson`, MANIFEST counts). Active solar-commodity cases by state:

| State | Authorized | Pending | Interim |
|---|---|---|---|
| Arizona | 6 | 56 | 2 |
| California | 35 | 34 | 5 |
| Nevada | 44 | 128 | 6 |
| New Mexico | 1 | 13 | 1 |
| Utah | 4 | 14 | 0 |

These include testing, access and transmission cases, not only generation. Nevada (Las Vegas, Pahrump and Tonopah field offices) is the most crowded. A pending application on your parcel usually blocks you or triggers a competitive process (43 CFR 2809.10(d)). Always check [MLRS](https://mlrs.blm.gov/) for the exact sections before you spend money.

Sources: BLM MLRS ROW layer as pulled by the team on 2026-10-21 (`data/processed/infra/MANIFEST.json`, source URL https://nlsdbpubgis.blm.gov/arcgishub/rest/services/HUB/BLM_Natl_MLRS_LUA_ROW/FeatureServer/0); competitive-process rule in [43 CFR 2809.10](https://www.ecfr.gov/current/title-43/subtitle-B/chapter-II/subchapter-B/part-2800) (eCFR current 2026-10-20).

---

## 5. The right-of-way process, step by step

All citations are to the current eCFR text of [43 CFR Part 2800](https://www.ecfr.gov/current/title-43/subtitle-B/chapter-II/subchapter-B/part-2800) (current as of 2026-10-20 per eCFR).

1. **Pre-application meeting (2804.10).** Encouraged for all ROWs. Request it from the BLM field office with jurisdiction. BLM will flag constraints, say whether the land is in a designated corridor or leasing area, tentatively schedule processing and explain costs.
2. **File SF-299 (2804.12(a)).** Standard Form 299, "Application for Transportation and Utility Systems and Facilities on Federal Lands", available on [blm.gov](https://www.blm.gov/programs/lands-and-realty/rights-way/obtaining-right-of-way). Must include: project description, schedule, project life and reclamation approach, map plus GIS shapefiles, statement of financial and technical capability, a POD (plan of development) submission schedule, and a certification. Business entities add formation documents, signing authority, and every shareholder with 3 percent or more (2804.12(e)).
3. **Extra solar requirements (2804.12(b) and (c)).**
   - Address known resource conflicts and propose avoidance, minimization and compensation measures.
   - Start talks with affected grazing permittees.
   - **Application filing fee: $15 per acre** for solar or wind development. It is credited against processing costs and any excess refunded.
   - **Within 6 months** after BLM receives the cost recovery fee, hold **two preliminary application review meetings**: one with BLM, one with federal, state, tribal and local agencies.
4. **Cost recovery (2804.14; [PIM 2026-001](https://www.blm.gov/policy/pim-2026-001)).** Utility-scale solar is **Category 6** (more than 64 federal work hours): you pay BLM's full reasonable costs under a cost recovery agreement, including third-party NEPA contractors. For reference, the 2026 fixed fees for small actions are $285 (Cat 1), $1,141 (Cat 2), $2,283 (Cat 3), $3,708 (Cat 4). Note the 2025-07-15 DOI memo lists "cost recovery agreements" among actions needing Secretary review.
5. **Completeness, prioritization and public meeting (2804.12(j), 2804.25, 2804.35).** BLM notifies you when the application is complete, prioritizes it (preferred areas, low conflict, plan conformance, state and local consistency, best practices) and holds a local public meeting if no other early engagement occurs. Prioritization is not appealable and can change.
6. **Plan of Development (2804.25(c)).** Detailed construction, operation, reclamation and environmental protection plan, plus cultural and species surveys. Use BLM's POD template.
7. **NEPA (2804.25(e)(4)).** An Environmental Assessment or, for most large projects, an EIS, often with a land use plan amendment. Statutory deadlines under NEPA as amended in 2023 are 2 years for an EIS and 1 year for an EA ([42 U.S.C. 4336a(g)](https://www.law.cornell.edu/uscode/text/42/4336a)). For an EIS the clock starts at the earliest of: BLM deciding an EIS is needed, BLM notifying you that your ROW application is complete, or the Notice of Intent. So a complete application starts the clock; filing alone does not. Real examples run longer: the Bonanza Solar project's EIS had an NOI in June 2023, a draft in September 2024 and a planned final in December 2027 per the federal permitting dashboard ([permits.performance.gov](https://www.permits.performance.gov/proj/bonanza-solar-project/environmental-impact-statement-eis)), as shown in search results; we did not open that page directly.
8. **Decision and grant (2805.10, 2805.11).** If approved, you get an unsigned grant to sign. Solar generation grants or leases run **up to 50 years**, with reviews at year 20 and every 10 years after. A Notice to Proceed is needed before ground disturbance.
9. **Bond (2805.20).** Outside designated leasing areas, a performance and reclamation bond of **at least $10,000 per disturbed acre**, based on a reclamation cost estimate, before the Notice to Proceed. Leases inside designated leasing areas: $10,000 per acre (2809.18(e)).
10. **Construction and operation.** Rent and fees start at issuance (section 6). For leases won competitively: POD due within 2 years, construction within 5 years, generation within 7 years (2809.18).

**Realistic timeline today:** pre-application to decision has historically taken roughly 2 to 4 years for EIS-level projects (this is our estimate from the Bonanza and Mosey examples, not an official figure). Add an unknown delay for Secretary-level review under the July 2025 memo unless you are covered by the April 2026 injunction.

---

## 6. Rents and fees today (statute plus 2025 rule)

**Annual payment = the greater of acreage rent or capacity fee** ([43 CFR 2806.50 and 2806.52](https://www.ecfr.gov/current/title-43/subtitle-B/chapter-II/subchapter-B/part-2800/subpart-2806/subject-group-ECFR8cbf73f23187665/section-2806.52)).

- **Acreage rent per acre = A x B x (1 + C)^D**, where A is the state per-acre value (5-year average NASS pastureland cash rent, fixed for the year the ROW is issued), B is 100 percent for solar, C is 3 percent, D is the year of the ROW term. Due by January 1 each year.
- **Capacity fee = 3.9 percent of the project's annual gross proceeds from electricity sales**, due the year after production, prorated to the public-land share of the footprint. Holders report gross proceeds by March 15; BLM bills by April 15 ([IM 2026-003](https://www.blm.gov/policy/im-2026-003)).

**State per-acre values (A) for ROWs issued in 2024 and 2025** (BLM IM 2026-003 Attachment 1; 2026 values were not in this table, ask BLM):

| State | 2024 | 2025 |
|---|---|---|
| Arizona | $2.04 | $1.96 |
| California | $12.80 | $13.00 |
| Nevada | $10.90 | $10.90 |
| New Mexico | $3.18 | $3.36 |
| Utah | $4.38 | $4.58 |

**Worked example (illustrative; the capacity factor and power price are our assumptions, not data):** 200 MWac on 1,400 acres of BLM land in Nevada, ROW issued at the 2025 value.
- Acreage rent, year 1: $10.90 x 1.0 x 1.03 = $11.23 per acre, about **$15,700 per year**.
- Capacity fee: 200 MW x 8,760 h x 30 percent capacity factor = 525,600 MWh; at an assumed $40/MWh, gross proceeds about $21.0 million; 3.9 percent is about **$820,000 per year**.
- So the capacity fee, not the acreage rent, sets the payment once the plant runs. Budget about 4 percent of revenue for BLM.

**Other fees:** $15/acre application filing fee; Category 6 cost recovery; $5/acre refundable nomination fee if you nominate land for a competitive offer (2809.11(b)); testing grants $2,000/year or $2/acre (2806.58).

---

## 7. The 2024 Renewable Energy Rule: what survives

The rule "Rights-of-Way, Leasing, and Operations for Renewable Energy" ([89 FR 35634, 2024-05-01](https://www.federalregister.gov/documents/2024/05/01/2024-08099/rights-of-way-leasing-and-operations-for-renewable-energy); [BLM fact sheet](https://www.blm.gov/sites/default/files/docs/2024-04/BLM-Final-Renewable-Energy-Rule-Fact-sheet.pdf)) did four things:

| 2024 rule feature | Status on 2026-10-21 |
|---|---|
| 80 percent capacity-fee cut through 2035 (stepping down to 20 percent by 2038), plus 20 percent cuts each for domestic content and project labor agreements | **Gone.** Superseded by statute on 2025-07-04 and removed from the CFR on 2025-08-01. |
| Rates locked at the time of authorization, adjusted annually | Replaced by the statutory formula (rate A fixed by year of issuance, 3 percent escalator). |
| Application process: $15/acre filing fee, two preliminary meetings, prioritization criteria, public meeting | **Still in the CFR** (2804.12, 2804.25, 2804.35). |
| Leasing inside designated leasing areas by application without a competitive process; BLM discretion to run competitive offers elsewhere | **Still in the CFR** (subpart 2809). Interior announced rescission on 2025-05-14; no proposed rule found in the Federal Register as of 2026-10-21. |

**Competitive process rules worth knowing (2809.10 to 2809.18):** BLM may run a competitive offer on its own, after a call for nominations, at an applicant's request, or when two or more applications compete. **BLM will not put land into a competitive process once it has accepted your complete application, received your POD and signed a cost recovery agreement** (2809.10(e)), unless you missed a deadline for information. That is the main reason to move quickly from SF-299 to a complete application and POD.

---

## 8. Co-located load and data centers on BLM land

- There is **no dedicated BLM rule** for data centers. A data center is not a "solar energy development" under Part 2800. Options to discuss with BLM: (a) a FLPMA Title V ROW or an amendment to a solar ROW (the Boulder City Townsite Solar 2 case, as reported, used an amendment with a Determination of NEPA Adequacy); (b) a land use lease or permit under [43 CFR Part 2920](https://www.ecfr.gov/current/title-43/subtitle-B/chapter-II/subchapter-B/part-2920); (c) a land sale or exchange to move the load site into private ownership. We have not confirmed which path BLM prefers; treat this as an open question for the pre-application meeting.
- **EO 14318** ([90 FR 35385, signed 2025-07-23](https://www.federalregister.gov/documents/2025/07/28/2025-14212/accelerating-federal-permitting-of-data-center-infrastructure)) tells Interior and DOE to offer authorizations on federal sites they identify for data centers needing over 100 MW of new load. As of 2026-10-21 we did not find a published BLM list of such sites; ask the state office whether any have been identified near your target.
- **Practical setup:** keep the solar plant and the load on separate authorizations, with the load on private or state land next to BLM land where possible. That keeps the solar ROW clean under Part 2800 and avoids the novelty and litigation risk of a data center ROW.
- Large-load utility rules (section 10) usually decide whether a co-located data center works, more than BLM does.

Sources (checked 2026-10-21): EO 14318 full text (link above); [Center for Western Priorities, 2026-07](https://westernpriorities.org/2026/07/trump-admin-swaps-out-solar-project-for-data-center-on-blm-land/) for the Boulder City example; [43 CFR Part 2800](https://www.ecfr.gov/current/title-43/subtitle-B/chapter-II/subchapter-B/part-2800) for the scope of solar ROWs.

---

## 9. State trust land as an alternative (by state)

State trust land is often faster than BLM, is not subject to NEPA unless there is a federal nexus, and is not affected by the Interior memo. Trust agencies must get full market value for their beneficiaries, so expect auctions and revenue-based rent.

| State | Agency | How solar works | Notes and sources |
|---|---|---|---|
| California | State Lands Commission (school lands) | Lease application to the Commission; projects added to the CEC renewable dashboard once complete. | About 340,000 desert acres in a checkerboard pattern, which makes large blocks hard. Only two solar leases, both in Kern County: BigBeau (up to 17 MW, 2020, 40 years) and Windhub Solar B (about 20 MW, 2023, 40 years). Law (AB 982, 2011) supports land exchanges with BLM to consolidate parcels. Contact SchoolLands.Public@slc.ca.gov. [SLC Solar Energy page](https://www.slc.ca.gov/renewable-offshore-wind-energy/solar-energy/) (fetched 2026-10-21). |
| Arizona | Arizona State Land Department (ASLD) | Solar uses a **long-term commercial lease**, offered at **public auction**. Online application; $2,000 application fee; decision can take up to 90 days; talk to the Commercial Leasing Section first. Wind and transmission use ROWs. | [ASLD Solar Applications](https://land.az.gov/solar-applications). The site returned HTTP 403 to automated access on 2026-10-21; details are from the page text shown in search results. Confirm the fee before filing. Arizona has large trust holdings near Phoenix and Tucson load. |
| Nevada | Nevada Division of State Lands | Very little trust land remains (about 3,000 acres; the state sold most of its grant early in statehood). No specific solar lease rule; a lease from NDSL would be needed in the rare case. | [OpenEI RAPID: Nevada solar land access](https://openei.org/wiki/RAPID/Solar/Nevada/Land_Access); [NDSL](https://lands.nv.gov/). **Not a practical alternative**; in Nevada the choice is BLM or private. |
| New Mexico | State Land Office, Office of Renewable Energy | Renewable energy business lease: notarized application, PLSS legal description, site plan showing roads, interconnection point and gen-tie, existing encumbrances. | About 9 million acres "available for lease to renewable energy companies". Existing solar on trust land includes a 50 MW First Solar plant on about 440 acres in Luna County. [NMSLO Office of Renewable Energy](https://www.nmstatelands.org/divisions/commercial-resources/renewable-energy/) (fetched 2026-10-21); [application packet](https://www.nmstatelands.org/wp-content/uploads/2022/11/Wind-and-Solar-Lease-Application-20221130.pdf). |
| Utah | Trust Lands Administration (formerly SITLA) | Solar and wind lease by application with supplemental form, preliminary development plan, maps and proposed business terms. Initial evaluation within 15 days; if accepted, a 30-day public notice and comment period. Cultural, environmental or paleontological surveys may be required. | [Trust Lands Energy and Minerals](https://trustlands.utah.gov/work-with-us/energy-minerals) and [forms](http://trustlands.utah.gov/tools/forms-applications/). Site blocked automated access on 2026-10-21; details from search results and [Utah Admin. Code R850-3-400](https://www.law.cornell.edu/regulations/utah/Utah-Admin-Code-R850-3-400). |

---

## 10. Interconnection and large-load (data center) service, by utility

**Common federal rule.** FERC Order No. 2023 ([88 FR 61014, 2023-09-06](https://www.federalregister.gov/documents/2023/09/06/2023-16628/improvements-to-generator-interconnection-procedures-and-agreements)) requires transmission providers to use annual **cluster studies** ("first-ready, first-served"), study and readiness deposits, **site control at the time of the interconnection request**, and withdrawal penalties. Where regulatory limits prevent site control (federal land is the usual case), the pro forma allows a limited deposit in lieu of site control. Each utility's exact rules are in its FERC tariff (OATT) and can differ; check before you rely on a pending BLM application as site control.

| Utility / area | Generator interconnection (over 20 MW) | Large-load / data center rules (status as found) |
|---|---|---|
| **CAISO** (PG&E, SCE, SDG&E areas, CA) | Annual cluster windows with intake scoring and zonal limits. **Cluster 16 window opened 2026-10-01** ([CAISO interconnection page](https://www.caiso.com/generation-transmission/generation/generator-interconnection), Cluster 16 queue report dated 2026-10-16). Cluster 15 was cut from 541 requests (347 GW) to 145 (about 68 GW) by scoring, per search-result summaries of CAISO material. The next window is likely about a year away. | PG&E Electric Rule 30 (transmission-level retail service) approved on an interim basis, CPUC A.24-11-007: customers who fund transmission upfront can connect faster ([EEI Large Load Tariffs list, updated 2026-10-09](https://www.eei.org/-/media/Project/EEI/Documents/Issues%20and%20Policy/List%20of%20Large%20Customer%20Projects%20and%20Tariffs)). FERC 2026-06-18 show-cause order to CAISO on large loads (50 MW+ at 69 kV+). |
| **APS** (AZ) | LGIP in APS OATT, posted on [APS OASIS](https://www.oasis.oati.com/AZPS/index.html) ([APS application requirements business practice](https://www.oasis.oati.com/woa/docs/AZPS/AZPSdocs/Application_Requirements_Business_Practice_20231213.pdf)). OASIS did not load for us on 2026-10-21. | Proposed changes to its XHLF (extra high load factor) tariff in its June 2025 rate case, ACC docket E-01345A-25-0105 (EEI list). At an ACC workshop on 2026-04-16, APS and SRP described their own queues for data centers, bring-your-own-power concepts and upfront financial security; the ACC summary attributes to APS a figure of about 13.1 GW of large-customer peak demand (the summary does not define it further) ([ACC, 2026-04-20](https://www.azcc.gov/news/home/2026/04/20/acc-large-load-data-center-workshop-highlights)). |
| **SRP** (AZ, not ACC rate-regulated) | Interconnection under SRP's OATT; SRP points developers to its Hosting Capacity Study on OASIS ([SRP 2026 All-Source RFP](https://www.srpnet.com/v3/assets/bltefc1fc708dcc94e7/blt7c2744713c80d9b9/2026-All-Source-RFP.pdf)). | 59 large-load customers with about 7,000 MW combined (ACC workshop). Reported E-67 price plan with minimum bills for new loads of 20 MW+ and a Large Customer Integration Process; we saw this only in secondary sources, confirm with SRP. |
| **TEP / UNS** (AZ) | LGIP in TEP OATT for generators over 20 MW; service at 138, 345 and 500 kV ([TEP Generation Exceeding 20 MW](https://www.tep.com/generation-interconnection-services/generation-exceeding-20-mw/)). Older TEP pages describe geographic clustering; confirm the current post-Order 2023 process on OASIS. | One contracted data center (286 MW), about 800 MW of other prospects and 8 to 10 GW of speculative requests (ACC workshop). |
| **PNM** (NM) | LGIP (Attachment N) in PNM OATT for over 20 MW; cluster study completed within 150 calendar days after the customer engagement window ([PNM Developer Information](https://www.pnm.com/developerinformation); [Attachment N](https://www.pnm.com/documents/d/pnm.com/attachment-n-large-generator-interconnection-procedures-6-1-2-c001218_t2177-1-)). | PNM committed in its 2026 IRP to file a large-load tariff (minimum revenue, exit fees); NM PRC is running a large-load working group with Synapse support ([NM PRC report, Aug 2026](https://www.prc.nm.gov/wp-content/uploads/2026/08/Synapse-Large-Load-Policy-Guide-for-NM-PRC-FINAL-20260820.pdf)). El Paso Electric (southern NM) proposed two large-load tariffs in NM PRC case 25-00082-UT (EEI list). |
| **NV Energy** (NV) | LGIP (Attachment N) in NV Energy OATT for over 20 MW; a defined point of interconnection is required. An older (2018) NV Energy process document shows two windows a year; a 2026 third-party summary describes one mid-year window. **Confirm the current window on [NV Energy OASIS](https://www.oasis.oati.com/NEVP/index.html).** | Clean Transition Tariff approved (PUCN 24-05023) for customers buying from new clean resources (EEI list). The 2026 IRP is driven by data center demand; Microsoft filed a ratepayer-protection tariff proposal in PUCN Docket 20-08014 in May 2026 ([Utility Dive](https://www.utilitydive.com/news/microsoft-seeks-nevada-tariff-to-shield-ratepayers-from-data-center-costs/822250/)). |
| **PacifiCorp / Rocky Mountain Power** (UT) | Cluster process under PacifiCorp's OATT, posted on [PacifiCorp OASIS](https://www.oasis.oati.com/PPW/index.html). A third-party source gives an annual request window of roughly early September to late October; **not confirmed on OASIS by us**. | Utah SB 132 (2025) lets new loads expected to reach 100 MW within 5 years seek their own supply if Rocky Mountain Power cannot serve them without major investment (90-day utility evaluation; credit requirements) ([enrolled bill](https://le.utah.gov/Session/2025/bills/enrolled/SB0132.pdf)). Start with [Rocky Mountain Power large service requests](https://www.rockymountainpower.net/working-with-us/large-service-requests.html). |

**What this means for siting:** in the dashboard, a site near a substation in an RTO (CAISO) faces a once-a-year window and heavy scoring. Outside CAISO, check each utility's next window and file the interconnection request as soon as you have site control or a qualifying deposit.

---

## 11. Ten-step filing plan

1. **Pick 3 to 5 parcels** from the dashboard with the "BLM-only" toggle: "Available" (or SEZ/DLA, or DRECP DFA in California), slope under 5 percent, 600+ contiguous acres, within a few miles of a 115 to 345 kV substation, and no active MLRS case on the same sections.
2. **Check the land record**: MLRS for existing cases and claims, the Surface Management Agency layer, grazing allotments, mining claims, and any withdrawals. Pull the BLM ROD GIS layer and DRECP map for the parcel.
3. **Talk to the utility first** (or in parallel): confirm the next cluster window, deposit sizes, and whether a filed BLM application counts as site control or needs a deposit in lieu. For co-located load, open a large-load request at the same time.
4. **Decide your federal posture**: confirm with counsel whether you (or your parent) are a member of a plaintiff association covered by the 2026-04-21 injunction, and model schedules both with and without Secretary-level review.
5. **Request the BLM pre-application meeting** (2804.10) with the field office; bring maps, a draft layout, and questions on corridors, DLAs, competing interest, cost estimates, and (if relevant) how a data center would be authorized.
6. **File SF-299** with the $15/acre filing fee, full GIS shapefiles, financial and technical capability statement, conflict-avoidance measures, POD schedule and business-entity documents.
7. **Sign the Category 6 cost recovery agreement** and pay; then **hold the two preliminary application review meetings within 6 months** (BLM, then agencies/tribes/local governments). Contact grazing permittees.
8. **Submit the POD and start surveys** (biological, cultural, desert tortoise where relevant, visual, water). Getting to a complete application plus POD plus cost recovery agreement protects the land from a competitive offer (2809.10(e)).
9. **Support NEPA**: fund the third-party contractor, respond fast to deficiency notices, and plan for a land use plan amendment if needed. Track every Secretary-level review step.
10. **Close out**: sign the grant, post the reclamation bond (at least $10,000 per disturbed acre), get the Notice to Proceed, and set up annual rent and the gross-proceeds reporting for the 3.9 percent capacity fee.

Sources (checked 2026-10-21): [43 CFR Part 2800](https://www.ecfr.gov/current/title-43/subtitle-B/chapter-II/subchapter-B/part-2800) (eCFR current 2026-10-20) for steps 5 to 10; [FERC Order 2023](https://www.federalregister.gov/documents/2023/09/06/2023-16628/improvements-to-generator-interconnection-procedures-and-agreements) (2023-09-06) for step 3; [Holland & Hart on the 2026-04-21 injunction](https://www.hollandhart.com/federal-court-halts-wind-and-solar-permitting-freeze) for step 4; [FR 2024-30953](https://www.federalregister.gov/documents/2024/12/27/2024-30953/notice-of-availability-of-the-approved-resource-management-plan-amendments-and-record-of-decision) (2024-12-27) for step 1. Step order is our recommendation.

---

## 12. Checklist

**Before the pre-application meeting**
- [ ] Parcel shapefile and legal description (PLSS) for each candidate
- [ ] Confirmed "Available"/SEZ/DLA/DFA status from the BLM ROD GIS layer and DRECP (CA)
- [ ] MLRS search: no conflicting active ROW, mining claims or withdrawals
- [ ] Nearest substation, voltage and owner; utility contact and next cluster window
- [ ] Draft layout at a realistic acres-per-MW (expect "capacity density" questions)
- [ ] Known sensitive resources list (critical habitat, ACECs, cultural sites, wilderness, military airspace)
- [ ] Draft schedule, budget including Category 6 costs and bond
- [ ] Decision on co-located load: separate parcel and authorization, or not

**SF-299 package**
- [ ] SF-299 signed by an authorized officer
- [ ] Project description, facilities, schedule, life, reclamation approach
- [ ] Maps and GIS shapefiles
- [ ] Financial and technical capability statement
- [ ] Resource conflict analysis with avoidance and mitigation measures
- [ ] POD submission schedule (BLM POD template)
- [ ] Business entity: articles, bylaws, signing authority, owners of 3 percent or more, affiliates
- [ ] Application filing fee: $15 x acres
- [ ] Grazing permittee outreach record

Sources: SF-299 contents from [43 CFR 2804.12](https://www.ecfr.gov/current/title-43/subtitle-B/chapter-II/subchapter-B/part-2800) (eCFR current 2026-10-20); fee and meeting rules from the same section; cost recovery from [PIM 2026-001](https://www.blm.gov/policy/pim-2026-001) (2026).

**After filing**
- [ ] Category 6 cost recovery agreement signed and funded
- [ ] Preliminary meeting 1 (BLM) and meeting 2 (agencies, tribes, local) within 6 months
- [ ] Completeness letter received
- [ ] POD submitted; surveys contracted
- [ ] Interconnection request filed and deposits posted
- [ ] NEPA schedule agreed; land use plan amendment need confirmed
- [ ] Bond estimate (reclamation cost estimate) prepared

---

## 13. Red flags

- **An active pending application on the same sections.** BLM can deny yours or run a competitive offer.
- **Land outside "Available"** (excluded, or slope over 10 percent, or more than 15 miles from a 69 kV+ line and not previously disturbed). BLM will not accept it without a plan amendment, which is unlikely now.
- **California desert parcels outside DRECP Development Focus Areas.**
- **Avoidance lands, ACECs, critical habitat (for example desert tortoise), wilderness study areas, military training routes**: long NEPA and high litigation risk.
- **Any financial model that assumes the solar ITC/PTC** for a project not already under construction by 2026-07-04, or the 2024 rule's fee discounts.
- **Relying on a BLM application as interconnection site control** without the utility confirming it in writing.
- **Data center on a BLM ROW**: legally novel, attracted press and community criticism in Boulder City; expect challenges.
- **Assuming the April 2026 injunction protects you** when you are not a member of a plaintiff association, or assuming it will last (it is preliminary and can be appealed).
- **Water**: large data centers and some solar cleaning plans need water in closed or over-allocated basins (check the team's water stress layer and Arizona AMA/INA areas).
- **Old interconnection guidance**: several utility pages we found predate Order 2023 compliance. Always use the current OATT on OASIS.

Sources: each red flag ties to a source cited in sections 2 to 10 (checked 2026-10-21), mainly [43 CFR Part 2800](https://www.ecfr.gov/current/title-43/subtitle-B/chapter-II/subchapter-B/part-2800), [FR 2024-30953](https://www.federalregister.gov/documents/2024/12/27/2024-30953/notice-of-availability-of-the-approved-resource-management-plan-amendments-and-record-of-decision), [SEIA on the 2025 tax law](https://seia.org/research-resources/clean-energy-provisions-big-beautiful-bill/), and [Holland & Hart on the injunction](https://www.hollandhart.com/federal-court-halts-wind-and-solar-permitting-freeze).

---

## 14. What we could not confirm (open items)

- The text of Secretary's Order 3438 (capacity density) on doi.gov; we relied on the court summary and press.
- Whether the 2024 ROD defines a separate "priority area" class, and the exact meaning of the "Other" class in the ROD GIS layer.
- 2026 per-acre rent values (the IM 2026-003 table ends at 2025).
- Whether Interior will publish the proposed rescission of the 2024 rule, and when.
- Whether the government appealed the 2026-04-21 injunction, and current First Circuit status.
- Current generator interconnection window dates for APS, SRP, TEP, PNM, NV Energy and PacifiCorp (OASIS sites did not load from our environment). SRP's E-67 plan details.
- ASLD and Utah Trust Lands page details were read from search-result text, not the live pages (403 errors).
- The BLM decision document for the Townsite Solar 2 data center conversion.
- Any published list of federal sites identified for data centers under EO 14318.

Full source list with dates and verification method: `deliverables/sources_blm.md`.
