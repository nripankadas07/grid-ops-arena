# Roadmap

Grid Ops Arena is at `0.1.1`: the artifact contract is versioned, while the physical model is intentionally compact. Items are ordered by evidence value, not promised dates.

## 0.2 — Policy conformance

- publish a policy adapter protocol with observation/action schema fixtures;
- add sub-hourly timesteps and demand-response actions;
- add invariant and conservation tests for every dispatch step;
- compare all built-in policies across a seeded scenario matrix.

Exit criterion: a third-party policy can be evaluated without importing simulator internals, and every invalid action has a stable failure code.

## 0.3 — Richer operations

- multiple storage and dispatchable asset classes;
- forecast error and rolling-horizon observations;
- reserve-margin and recovery-time metrics;
- tournament reports with Pareto views rather than only a composite rank.

Exit criterion: at least two materially different policy families can be compared across normal, outage, and recovery phases.

## 1.0 — Reference-grade arena contract

- documented schema migration and compatibility policy;
- calibration hooks for external, user-owned datasets;
- cross-validation examples against a higher-fidelity grid tool;
- property-based scenario fuzzing and long-horizon reproducibility checks.

## Non-goals

Protection studies, AC optimal power flow, live control, market settlement, and claims of real-grid safety remain out of scope unless independently validated and governed.
