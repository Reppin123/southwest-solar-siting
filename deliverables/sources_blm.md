# Sources for the BLM Application and Policy Brief

All sources were checked on 2026-10-21. "How checked" means:
- **Full text**: we read the document itself (Federal Register API full text, eCFR API, or the PDF/page).
- **Page**: we fetched the live page and read the relevant part.
- **Search text**: the site blocked automated access (HTTP 403) or did not load; details come from the page text shown in web search results. Treat these as lower confidence and confirm before relying on them.
- **Secondary**: a law firm, trade press or advocacy summary of a primary document we could not open.

## Federal regulations and rules (BLM rights-of-way, rents, fees)

| Source | Publisher | Document date | URL | How checked |
|---|---|---|---|---|
| 43 CFR Part 2800 (ROW under FLPMA), sections 2804.10, 2804.12, 2804.14, 2804.25, 2804.35, 2805.10, 2805.11, 2805.20, 2806.50 to 2806.58, 2809.10 to 2809.18 | eCFR (National Archives / GPO) | Current as of 2026-10-20; part last amended 2025-08-01 | https://www.ecfr.gov/current/title-43/subtitle-B/chapter-II/subchapter-B/part-2800 | Full text (eCFR versioner API, XML for 2026-10-01) |
| 43 CFR 2806.52 Annual rents and fees for solar and wind | eCFR | Amended 2025-08-01 | https://www.ecfr.gov/current/title-43/subtitle-B/chapter-II/subchapter-B/part-2800/subpart-2806/subject-group-ECFR8cbf73f23187665/section-2806.52 | Full text |
| 43 CFR Part 2920, Leases, Permits and Easements (possible path for non-energy uses such as a data center) | eCFR | current as of 2026-10-01 | https://www.ecfr.gov/current/title-43/subtitle-B/chapter-II/subchapter-B/part-2920 | Table of contents confirmed via eCFR API; text not analyzed |
| eCFR version history for Part 2800 (shows 2024-12-26 and 2025-08-01 amendments) | eCFR | 2026-10-21 query | https://www.ecfr.gov/api/versioner/v1/versions/title-43.json?part=2800 | Full text (API) |
| Revisions to the Regulations Regarding Intermittent Energy, 90 FR 36111, FR Doc 2025-14627 (implements OBBB section 50302; effective 2025-08-01) | BLM, Federal Register | 2025-08-01 | https://www.federalregister.gov/documents/2025/08/01/2025-14627/revisions-to-the-regulations-regarding-intermittent-energy | Full text |
| Rights-of-Way, Leasing, and Operations for Renewable Energy, 89 FR 35634, FR Doc 2024-08099 (2024 Renewable Energy Rule) | BLM, Federal Register | 2024-05-01 | https://www.federalregister.gov/documents/2024/05/01/2024-08099/rights-of-way-leasing-and-operations-for-renewable-energy | Provisions read in current eCFR text; FR page link verified (HTTP 200) |
| Final Renewable Energy Rule Fact Sheet | BLM | 2024-04 | https://www.blm.gov/sites/default/files/docs/2024-04/BLM-Final-Renewable-Energy-Rule-Fact-sheet.pdf | Full text (PDF) |
| Interior to initiate action to rescind BLM's intermittent energy rule (press release) | BLM / DOI | 2025-05-14 | https://www.blm.gov/press-release/interior-initiate-action-rescind-blms-intermittent-energy-rule | Page |
| Federal Register API search: documents affecting 43 CFR 2800 published since 2025-01-01 (returned only FR Doc 2025-14627) | Federal Register | 2026-10-21 query | https://www.federalregister.gov/api/v1/documents.json?conditions[cfr][title]=43&conditions[cfr][part]=2800&conditions[publication_date][gte]=2025-01-01 | Full text (API) |
| IM 2026-003, Acreage Rent and Capacity Fee Billing and Collection for Intermittent Energy, with Attachment 1 (per-acre values by state and year) | BLM | 2025-12-16 | https://www.blm.gov/policy/im-2026-003 ; https://www.blm.gov/sites/default/files/docs/2025-12/IM2026-003%20att1.pdf | Page and full text (PDF) |
| PIM 2026-001, Calendar Year 2026 Cost Recovery Fee Schedule and Strict Liability Limit | BLM | 2026 (posted 2026-04) | https://www.blm.gov/policy/pim-2026-001 ; https://www.blm.gov/sites/default/files/docs/2026-04/PIM-2026-001%20-%202026%20Strict%20Liability%20Limit%20and%20Cost%20Recovery%20Fee%20Schedule_0.pdf | Full text (PDF) |
| Obtaining a right-of-way (SF-299 and process) | BLM | undated web page | https://www.blm.gov/programs/lands-and-realty/rights-way/obtaining-right-of-way | Link verified (HTTP 200) |
| Solar Energy Rents and Fees page | BLM | undated web page | https://www.blm.gov/programs/energy-and-minerals/renewable-energy/solar-energy/rent-and-fees | Link verified (HTTP 200) |
| Mineral and Land Records System (case lookup) | BLM | live system | https://mlrs.blm.gov/ | Link verified; case counts from the team's pull (below) |
| Rescission of Conservation and Landscape Health Rule, FR Doc 2026-09386 | BLM, Federal Register | 2026-05-12 | https://www.federalregister.gov/documents/2026/05/12/2026-09386/rescission-of-conservation-and-landscape-health-rule | Full text of abstract (API) |
| How BLM's repeal of the Public Lands Rule could slow clean energy deployment | Clean Air Task Force (advocacy) | 2026-06 | https://www.catf.us/2026/06/how-blms-repeal-public-lands-rule-could-slow-clean-energy-deployment/ | Page (secondary) |

## Western Solar Plan (2024 ROD), SEZs, DRECP

| Source | Publisher | Document date | URL | How checked |
|---|---|---|---|---|
| Notice of Availability of the Approved RMP Amendments and ROD for Utility-Scale Solar Energy Development, FR Doc 2024-30953 (31 M acres available incl. 3.8 M avoidance; 15 miles of 69 kV+ line or previously disturbed; slope over 10 percent excluded) | BLM, Federal Register | 2024-12-27 (ROD signed 2024-12-19) | https://www.federalregister.gov/documents/2024/12/27/2024-30953/notice-of-availability-of-the-approved-resource-management-plan-amendments-and-record-of-decision | Full text |
| BLM Director's response to appeals by Governors of California and Utah, FR Doc 2025-00753 | BLM, Federal Register | 2025-01-15 | https://www.federalregister.gov/documents/2025/01/15/2025-00753/blm-directors-response-to-the-appeals-by-the-governors-of-california-and-utah-of-the-blm-state | Full text |
| ROD / Approved RMP Amendments project page | BLM ePlanning | 2024-12 | https://eplanning.blm.gov/eplanning-ui/project/2022371/510 | Link verified (HTTP 200); ROD PDF not read in full |
| BLM National Solar PEIS ROD GIS layer (`BLM_Natl_Solar_PEIS_ROD.gdb`, layer `Solar_PEIS_ROD_Approved_Plan`, fields State, ApprovedPlan) | BLM (downloaded by the team's land helper to data/raw/land/) | metadata dated 2024-12-18 | data/raw/land/BLM_Natl_Solar_PEIS_ROD.gdb | Full data: we summed Shape_Area by State and ApprovedPlan (acres = m2 / 4046.86). 11-state totals (27.9 M available + 3.82 M avoidance) match the FR notice. |
| Interior Department finalizes framework for future of solar development on public lands (press release) | BLM / DOI | 2024-12-20 | https://www.blm.gov/press-release/interior-department-finalizes-framework-future-solar-development-public-lands | Page |
| California: Desert Renewable Energy Conservation Plan | BLM | undated web page | https://www.blm.gov/programs/planning-and-nepa/plans-in-development/california/desert-renewable-energy-conservation-plan | Link verified (HTTP 200); DRECP role in CA confirmed by the GIS "DRECP/CDCA" class |
| BLM Solar Energy Program site (SEZ maps) | BLM / Argonne | live site | https://blmsolar.anl.gov/ | Blocked (HTTP 403, bot challenge); not used for facts |
| Notice of Intent, RMP Amendment and EIS for the Mosey Solar Project, Clark and Nye Counties, NV, FR Doc 2026-15270 | BLM, Federal Register | 2026-07-29 | https://www.federalregister.gov/documents/2026/07/29/2026-15270/notice-of-intent-to-prepare-a-resource-management-plan-amendment-and-environmental-impact-statement | Full text of abstract (API) |
| Bonanza Solar Project EIS schedule | Federal Permitting Dashboard | accessed via search | https://www.permits.performance.gov/proj/bonanza-solar-project/environmental-impact-statement-eis | Search text (site returned 403) |

## 2025 to 2026 federal policy changes

| Source | Publisher | Document date | URL | How checked |
|---|---|---|---|---|
| EO 14156, Declaring a National Energy Emergency, 90 FR 8433 (definition of "energy" excludes solar and wind) | White House, Federal Register | signed 2025-01-20, published 2025-01-29 | https://www.federalregister.gov/documents/2025/01/29/2025-02003/declaring-a-national-energy-emergency | Full text |
| EO 14315, Ending Market Distorting Subsidies for Unreliable, Foreign-Controlled Energy Sources, 90 FR 30821 | White House, Federal Register | signed 2025-07-07, published 2025-07-10 | https://www.federalregister.gov/documents/2025/07/10/2025-12961/ending-market-distorting-subsidies-for-unreliable-foreign-controlled-energy-sources | Metadata (API); content as described by the DOI memo and IRS-related sources |
| EO 14318, Accelerating Federal Permitting of Data Center Infrastructure, 90 FR 35385 (definitions; Sec. 9 Federal Lands Availability) | White House, Federal Register | signed 2025-07-23, published 2025-07-28 | https://www.federalregister.gov/documents/2025/07/28/2025-14212/accelerating-federal-permitting-of-data-center-infrastructure | Full text |
| Departmental Review Procedures for Decisions, Actions, Consultations, and Other Undertakings Related to Wind and Solar Energy Facilities (69 items) | DOI Office of the Secretary (Deputy Chief of Staff, Policy) | 2025-07-15 | https://www.doi.gov/sites/default/files/documents/2025-07/dcos-pol-memo-doi-review-procedures-wind-and-solar-projects-2025-07-15-1-signed.pdf | Full text (PDF) |
| Federal Court Halts Wind and Solar Permitting Freeze (D. Mass. preliminary injunction, 2026-04-21; covers DOI memo, SO 3438, others; members of nine plaintiff associations only) | Holland & Hart (law firm) | 2026-04 | https://www.hollandhart.com/federal-court-halts-wind-and-solar-permitting-freeze | Page (secondary; court order not read) |
| Burgum's "density" order creates new roadblock for renewables | E&E News | 2025-08 | https://www.eenews.net/articles/burgums-density-order-creates-new-roadblock-for-renewables/ | Search text (secondary) |
| Interior bends on solar, but wind energy on public lands remains stalled (about 20 solar projects back in review) | E&E News | 2026-03-17 | https://www.eenews.net/articles/interior-bends-on-solar-but-wind-energy-on-public-lands-remains-stalled/ | Page (secondary) |
| After a five-month freeze, BLM finally advances a solar project (Libra, NV) | pv magazine USA | 2025-12-17 | https://pv-magazine-usa.com/2025/12/17/after-a-five-month-freeze-blm-finally-advances-a-solar-project/ | Page (secondary) |
| Trump admin swaps out solar project for data center on BLM land (Townsite Solar 2, Boulder City, NV) | Center for Western Priorities (advocacy) | 2026-07 | https://westernpriorities.org/2026/07/trump-admin-swaps-out-solar-project-for-data-center-on-blm-land/ | Page (secondary, advocacy source; BLM decision not read) |
| Trump Administration's Unified Agenda suggests major reversals (renewable energy rule rescission still unpublished) | Columbia Law School, Sabin Center | 2026-07-22 | https://blogs.law.columbia.edu/climatechange/2026/07/22/trump-administrations-unified-agenda-suggests-major-reversals-on-climate-safeguards/ | Page (secondary) |
| Removal of NEPA Implementing Regulations (CEQ interim final rule) | CEQ, Federal Register | 2025-02-25 | https://www.federalregister.gov/documents/2025/02/25/2025-03014/removal-of-national-environmental-policy-act-implementing-regulations | Abstract (API) |
| Removal of NEPA Implementing Regulations (CEQ final rule) | CEQ, Federal Register | 2026-01-08 | https://www.federalregister.gov/documents/2026/01/08/2026-00178/removal-of-national-environmental-policy-act-implementing-regulations | Abstract (API) |
| DOI NEPA Implementing Regulations (adopts 2025-07-03 interim final rule as final) | DOI, Federal Register | 2026-02-24 | https://www.federalregister.gov/documents/2026/02/24/2026-03708/national-environmental-policy-act-implementing-regulations | Abstract (API) |
| NEPA Implementing Procedures for the BLM (DOI NEPA Handbook revision) | DOI, Federal Register | 2026-04-28 | https://www.federalregister.gov/documents/2026/04/28/2026-08235/national-environmental-policy-act-implementing-procedures-for-the-bureau-of-land-management | Abstract (API) |
| 42 U.S.C. 4336a(g), NEPA deadlines (EIS 2 years, EA 1 year; start date rules) | Cornell LII (US Code) | current | https://www.law.cornell.edu/uscode/text/42/4336a | Full text of subsection (g) |

## Tax credits (45Y / 48E)

| Source | Publisher | Document date | URL | How checked |
|---|---|---|---|---|
| Explained: the clean energy provisions in the One Big Beautiful Bill | SEIA (trade association) | 2025 | https://seia.org/research-resources/clean-energy-provisions-big-beautiful-bill/ | Search text plus link verified (secondary) |
| One Big Beautiful Bill Act brings big changes to green energy tax credits | Kirkland & Ellis | 2025-08 | https://www.kirkland.com/publications/kirkland-alert/2025/08/one-big-beautiful-bill-act-brings-big-changes-to-green-energy-tax-credits | Search text (secondary) |
| Federal district court vacates Notice 2025-42 (*Oregon Environmental Council v. IRS*, D.D.C. No. 25-4400, 2026-06-06) | KPMG | 2026-06 | https://kpmg.com/us/en/taxnewsflash/news/2026/06/court-vacates-notice-2025-42-eliminated-safe-harbor-construction-wind-solar.html | Page (secondary; one other law firm summary dated the ruling 2026-06-12; we use KPMG's date) |

## State trust land

| Source | Publisher | Document date | URL | How checked |
|---|---|---|---|---|
| Solar Energy (school lands, lease summaries, AB 982) | California State Lands Commission | live page | https://www.slc.ca.gov/renewable-offshore-wind-energy/solar-energy/ | Page |
| Solar Applications (long-term commercial lease at auction; $2,000 fee; up to 90 days) | Arizona State Land Department | live page | https://land.az.gov/solar-applications | Search text (HTTP 403) |
| RAPID: Solar, Nevada, Land Access (about 3,000 acres of trust land; no solar lease rule) | OpenEI (NREL) | wiki page | https://openei.org/wiki/RAPID/Solar/Nevada/Land_Access | Search text plus link verified |
| Nevada Division of State Lands | State of Nevada | live site | https://lands.nv.gov/ | Link verified |
| Office of Renewable Energy (about 9 M acres available; existing projects) | New Mexico State Land Office | live page | https://www.nmstatelands.org/divisions/commercial-resources/renewable-energy/ | Page |
| Wind and Solar Lease Application Packet | New Mexico State Land Office | 2022-11-30 | https://www.nmstatelands.org/wp-content/uploads/2022/11/Wind-and-Solar-Lease-Application-20221130.pdf | Search text plus link verified |
| Energy and Minerals; Forms and Applications | Utah Trust Lands Administration | live pages | https://trustlands.utah.gov/work-with-us/energy-minerals ; http://trustlands.utah.gov/tools/forms-applications/ | Search text (HTTP 403) |
| Utah Admin. Code R850-3-400, Application Processing | Cornell LII | current | https://www.law.cornell.edu/regulations/utah/Utah-Admin-Code-R850-3-400 | Search text plus link verified |

## Interconnection and large loads

| Source | Publisher | Document date | URL | How checked |
|---|---|---|---|---|
| Improvements to Generator Interconnection Procedures and Agreements (Order No. 2023), 88 FR 61014 | FERC, Federal Register | 2023-09-06 | https://www.federalregister.gov/documents/2023/09/06/2023-16628/improvements-to-generator-interconnection-procedures-and-agreements | Full text (searched for site control, deposits in lieu, withdrawal penalties) |
| Generator interconnection (Cluster 16 window opens 2026-10-01; queue reports) | CAISO | page with reports dated 2026-10-16 | https://www.caiso.com/generation-transmission/generation/generator-interconnection | Page |
| FERC orders grid operators to promptly revise or justify interconnection rules for data centers and large loads (2026-06-18; 50 MW / 69 kV; RM26-4 open) | White & Case | 2026-06 | https://www.whitecase.com/insight-alert/ferc-orders-grid-operators-promptly-revise-or-justify-interconnection-rules-data | Search text (HTTP 403); consistent across several law firm summaries in the same search |
| Large Load Projects and Tariffs (APS XHLF E-01345A-25-0105; PG&E Rule 30 A.24-11-007; NV Energy CTT 24-05023; El Paso Electric NM 25-00082-UT) | Edison Electric Institute | updated 2026-10-09 | https://www.eei.org/-/media/Project/EEI/Documents/Issues%20and%20Policy/List%20of%20Large%20Customer%20Projects%20and%20Tariffs | Full text (PDF) |
| ACC Data Center / Large Load Workshop Highlights (APS, SRP, TEP figures) | Arizona Corporation Commission | 2026-04-20 (workshop 2026-04-16) | https://www.azcc.gov/news/home/2026/04/20/acc-large-load-data-center-workshop-highlights | Page |
| APS OASIS and Application Requirements Business Practice | APS | 2023-12-13 (business practice) | https://www.oasis.oati.com/AZPS/index.html ; https://www.oasis.oati.com/woa/docs/AZPS/AZPSdocs/Application_Requirements_Business_Practice_20231213.pdf | Did not load (connection failed); search text only |
| SRP 2026 All-Source RFP (hosting capacity study on OASIS) | Salt River Project | 2026 | https://www.srpnet.com/v3/assets/bltefc1fc708dcc94e7/blt7c2744713c80d9b9/2026-All-Source-RFP.pdf | Search text plus link verified |
| Generation Exceeding 20 MW | Tucson Electric Power | live page | https://www.tep.com/generation-interconnection-services/generation-exceeding-20-mw/ | Search text plus link verified |
| Developer Information; LGIP Attachment N | PNM | live pages | https://www.pnm.com/developerinformation ; https://www.pnm.com/documents/d/pnm.com/attachment-n-large-generator-interconnection-procedures-6-1-2-c001218_t2177-1- | Search text plus links verified |
| Synapse Large Load Policy Guide for NM PRC | NM Public Regulation Commission | 2026-08-20 | https://www.prc.nm.gov/wp-content/uploads/2026/08/Synapse-Large-Load-Policy-Guide-for-NM-PRC-FINAL-20260820.pdf | Search text plus link verified |
| NV Energy OASIS (LGIP, Attachment N) | NV Energy | live | https://www.oasis.oati.com/NEVP/index.html | Did not load; search text of a 2018 process document only |
| Microsoft seeks Nevada tariff to shield ratepayers from data center costs (PUCN Docket 20-08014) | Utility Dive | 2026 | https://www.utilitydive.com/news/microsoft-seeks-nevada-tariff-to-shield-ratepayers-from-data-center-costs/822250/ | Search text (HTTP 403) |
| PacifiCorp OASIS | PacifiCorp | live | https://www.oasis.oati.com/PPW/index.html | Did not load; window dates not confirmed |
| S.B. 132 Electric Utility Amendments (enrolled) | Utah Legislature | 2025 General Session | https://le.utah.gov/Session/2025/bills/enrolled/SB0132.pdf | Search text plus link verified (PDF not read in full) |
| Large service requests | Rocky Mountain Power | live page | https://www.rockymountainpower.net/working-with-us/large-service-requests.html | Link verified |

## Team data used

| Dataset | Owner | Retrieved | Path | Notes |
|---|---|---|---|---|
| Active BLM solar ROW cases by state and status (MLRS, commodity SOLAR ENERGY FACILITIES) | infra helper | 2026-10-21 | data/processed/infra/blm_solar_row_cases.geojson (counts in data/processed/infra/MANIFEST.json) | Includes testing, access and transmission cases, not only generation |
| BLM Solar PEIS ROD allocations | land helper (raw download) | per land helper | data/raw/land/BLM_Natl_Solar_PEIS_ROD.gdb | We only read it; acreage summary in brief section 3 |
