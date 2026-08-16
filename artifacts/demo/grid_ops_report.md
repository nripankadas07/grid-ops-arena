# Grid Ops Arena report

> **Synthetic demo:** All loads&#44; generation&#44; prices&#44; emissions factors&#44; and outage events in the bundled examples are synthetic demonstration data&#44; not current facts&#46;

- Scenario: `synthetic&#45;microgrid&#45;seed&#45;17`
- Policy: `balanced`
- Schema: `1&#46;0&#46;0`

## Scorecard

| Metric | Value |
|---|---:|
| Composite score | 83.60 |
| Reliability | 98.722% |
| Safety score | 98.96 |
| Total synthetic cost | 656.80 |
| Emissions | 542.68 kg |
| Unserved energy | 34.493 kWh |
| Constraint violations | 2 |

## Event log

- Steps 16–18: **grid&#95;outage** — Synthetic feeder outage A
- Steps 24–27: **renewable&#95;derate** — Synthetic cloud&#45;and&#45;wind lull
- Steps 36–37: **grid&#95;outage** — Synthetic feeder outage B
- Steps 36–36: **peaker&#95;unavailable** — Synthetic peaker start failure

## Dispatch excerpt

| Step | Load | Renewable | Battery | Peaker | Grid | Unserved | SOC |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 48.2 | 13.3 | 0.0 | 0.0 | 34.9 | 0.0 | 72.0 |
| 1 | 51.2 | 8.6 | 0.0 | 0.0 | 42.6 | 0.0 | 72.0 |
| 2 | 49.9 | 12.3 | 0.0 | 0.0 | 37.5 | 0.0 | 72.0 |
| 3 | 49.1 | 7.0 | 0.0 | 0.0 | 42.1 | 0.0 | 72.0 |
| 4 | 44.7 | 9.5 | 0.0 | 0.0 | 35.2 | 0.0 | 72.0 |
| 5 | 49.7 | 8.3 | 0.0 | 0.0 | 41.5 | 0.0 | 72.0 |
| 6 | 51.1 | 8.9 | 0.0 | 0.0 | 42.3 | 0.0 | 72.0 |
| 7 | 56.4 | 26.9 | 0.0 | 0.0 | 29.5 | 0.0 | 72.0 |
| 8 | 55.8 | 39.0 | 0.0 | 0.0 | 16.8 | 0.0 | 72.0 |
| 9 | 55.3 | 47.3 | 0.0 | 0.0 | 8.1 | 0.0 | 72.0 |
| 10 | 62.2 | 48.9 | 0.0 | 0.0 | 13.3 | 0.0 | 72.0 |
| 11 | 61.5 | 57.4 | 0.0 | 0.0 | 4.1 | 0.0 | 72.0 |
| 12 | 63.1 | 55.9 | 0.0 | 0.0 | 7.2 | 0.0 | 72.0 |
| 13 | 59.6 | 60.3 | -0.7 | 0.0 | 0.0 | 0.0 | 72.7 |
| 14 | 59.7 | 50.4 | 0.0 | 0.0 | 9.3 | 0.0 | 72.7 |
| 15 | 55.8 | 48.4 | 0.0 | 0.0 | 7.4 | 0.0 | 72.7 |
| 16 | 59.4 | 39.0 | 20.5 | 0.0 | 0.0 | 0.0 | 50.9 |
| 17 | 58.4 | 25.7 | 32.7 | 0.0 | 0.0 | 0.0 | 16.2 |
| 18 | 66.8 | 14.3 | 15.2 | 7.5 | 0.0 | 29.8 | 0.0 |
| 19 | 62.6 | 9.3 | 0.0 | 0.0 | 53.3 | 0.0 | 0.0 |
| 20 | 61.4 | 12.8 | 0.0 | 0.0 | 48.7 | 0.0 | 0.0 |
| 21 | 59.9 | 14.6 | 0.0 | 0.0 | 45.2 | 0.0 | 0.0 |
| 22 | 55.6 | 13.0 | 0.0 | 0.0 | 42.7 | 0.0 | 0.0 |
| 23 | 55.3 | 8.2 | 0.0 | 0.0 | 47.2 | 0.0 | 0.0 |

Generated deterministically by Grid Ops Arena.
