# Top site memos

Generated 2026-10-21 by `pipeline/memos.py` from `data/processed/sites/candidate_sites.geojson` (25,733 ranked sites). One memo per site below.

Memos 1-10 are the top sites by the solar ranking; the rest are the top sites by the solar + data center ranking that were not already covered. Each list takes at most one site per contiguous ownership block and per nearest substation, across both lists, so the memos cover different places. Ranks are among all ranked sites; the full lists are in `deliverables/Southwest_Solar_Sites.xlsx` (Top 50 Solar, Top 50 Data Center). 'Provisional' means the nearest substation record is OSM-only or its voltage is inferred; every memo lists its provisional flags and offline checks.

| # | Site | Picked from | Solar rank | DC rank | State | County | Acres | Owner | Nearest 115 kV+ substation | Provisional | Solar score | DC score |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | [SW-NM-00001](01_SW-NM-00001.md) | solar | 1 | 1 | NM | Doña Ana | 3,697 | BLM (BLM solar-available) | AFTON 345 kV, 0.5 km | no | 95.9 | 88.2 |
| 2 | [SW-NM-00011](02_SW-NM-00011.md) | solar | 11 | 8 | NM | Luna | 2,065 | Private | LUNA 345 kV, 0.0 km | no | 89.8 | 85.5 |
| 3 | [SW-AZ-00017](03_SW-AZ-00017.md) | solar | 17 | 18 | AZ | Pinal | 3,954 | Private | PINAL CENTRAL 500 kV, 0.0 km | no | 89.0 | 83.5 |
| 4 | [SW-NM-00018](04_SW-NM-00018.md) | solar | 18 | 21 | NM | Doña Ana | 3,784 | Private | SANTA TERESA 115 kV, 0.6 km | no | 88.8 | 82.9 |
| 5 | [SW-NM-00022](05_SW-NM-00022.md) | solar | 22 | 56 | NM | Doña Ana | 5,557 | Private | CHAPARRAL 115 kV, 0.0 km | no | 88.0 | 81.1 |
| 6 | [SW-CA-00026](06_SW-CA-00026.md) | solar | 26 | 74 | CA | San Bernardino | 4,045 | Private | ADELANTO 500 kV, 0.0 km | no | 87.3 | 80.8 |
| 7 | [SW-NM-00030](07_SW-NM-00030.md) | solar | 30 | 194 | NM | Eddy | 3,954 | BLM (BLM solar-available) | SAND DUNES 115 kV, 0.0 km | no | 87.1 | 78.7 |
| 8 | [SW-AZ-00033](08_SW-AZ-00033.md) | solar | 33 | 52 | AZ | Pinal | 3,631 | Private | MARICOPA 230 kV, 0.0 km | no | 86.6 | 81.4 |
| 9 | [SW-AZ-00034](09_SW-AZ-00034.md) | solar | 34 | 57 | AZ | Cochise | 2,528 | Private | APACHE 230 kV, 2.2 km | no | 86.5 | 81.1 |
| 10 | [SW-NM-00037](10_SW-NM-00037.md) | solar | 37 | 144 | NM | Curry | 3,954 | Private | OASIS 230 kV, 0.0 km | no | 86.4 | 79.4 |
| 11 | [SW-AZ-00149](11_SW-AZ-00149.md) | dc | 149 | 5 | AZ | Mohave | 2,926 | Private | GRIFFITH 230 kV, 0.0 km | no | 83.5 | 85.9 |
| 12 | [SW-CA-00099](12_SW-CA-00099.md) | dc | 99 | 11 | CA | Riverside | 3,707 | Private | BUCK 230 kV, 0.2 km | no | 84.5 | 84.6 |
| 13 | [SW-CA-00422](13_SW-CA-00422.md) | dc | 422 | 15 | CA | Madera | 2,769 | Private | GREGG 230 kV, 0.0 km | no | 80.9 | 84.1 |
| 14 | [SW-AZ-00058](14_SW-AZ-00058.md) | dc | 58 | 16 | AZ | Pima | 3,695 | State | VAIL 345 kV, 1.2 km | no | 85.5 | 84.0 |
| 15 | [SW-AZ-00104](15_SW-AZ-00104.md) | dc | 104 | 20 | AZ | Cochise | 4,050 | State | RED TAIL 230 kV, 0.0 km | no | 84.4 | 83.0 |

## Best site in each state (solar ranking)

| State | Site | Solar rank | DC rank | County | Owner | Solar score |
|---|---|---|---|---|---|---|
| NM | SW-NM-00001 | 1 | 1 | Doña Ana | BLM | 95.9 |
| AZ | SW-AZ-00017 | 17 | 18 | Pinal | Private | 89.0 |
| CA | SW-CA-00026 | 26 | 74 | San Bernardino | Private | 87.3 |
| NV | SW-NV-00335 | 335 | 1543 | Nye | Private | 81.4 |
| UT | SW-UT-00374 | 374 | 97 | Iron | Private | 81.2 |

Limits: public data shows where lines and substations are, not spare capacity; ownership is surface managing agency, not title; all distances are straight-line. See `data/processed/sites/METHOD.md`.
