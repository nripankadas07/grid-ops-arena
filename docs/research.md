# Research and differentiation

Research reviewed on 2026-08-16. This note records conceptual influences and the boundary between Grid Ops Arena and established engineering tools. No source code, scenarios, parameters, or datasets were copied from the projects below.

## Primary sources

| Source | What informed this project |
|---|---|
| [NLR/NREL REopt](https://github.com/NatLabRockies/REopt.jl) and the [REopt API](https://github.com/NatLabRockies/REopt_API) | Treating cost, energy performance, resilience, emissions, storage, renewables, and conventional generation as related—but separately reportable—objectives. |
| [PowerModelsONM](https://github.com/lanl-ansi/PowerModelsONM.jl) | The importance of explicit outage/restoration conditions and networked-microgrid operational constraints. |
| [GridLAB-D](https://github.com/gridlab-d/gridlab-d) | The value of stepwise, inspectable distribution-system simulation and reproducible event inputs. |
| [Gymnasium environment API](https://gymnasium.farama.org/api/env/) | A small observation/action boundary that lets policies remain independent from environment internals. |
| [NREL research on REopt microgrid resilience](https://docs.nrel.gov/docs/fy24osti/87314.pdf) | Reporting performance under user-specified outage conditions instead of implying generic resilience. |

## Deliberate differentiation

Grid Ops Arena is not an optimal power-flow solver, investment optimizer, protection model, or grid digital twin. It is a small, dependency-free policy arena designed for fast review:

- an agent returns one typed `Action`; the simulator owns feasibility and records every clamp;
- synthetic outages, peaker failures, and renewable derates are first-class versioned events;
- reliability, cost, emissions, and safety remain visible before they are combined;
- seeded scenarios and reports are byte-reproducible and suitable for regression tests;
- the JSON artifact, Markdown evidence, and single-file HTML all come from one result object.

The narrow model is intentional. A useful extension path is to validate policy behavior against a higher-fidelity tool above, not to present this simulator as a substitute for one.

## Data boundary

Every bundled load, generation value, tariff, emissions factor, and outage is synthetic. Links above motivate software requirements only; they are not sources for the demo values.
