# Architecture

Grid Ops Arena separates four concerns:

1. `model.py` defines the versioned scenario and action boundary.
2. `policies.py` contains deliberately small, auditable baselines.
3. `simulator.py` owns scenario generation, constraint enforcement, energy balance, and scoring.
4. `reporting.py` renders the same result artifact without changing its meaning.

## Determinism

Scenario generation uses a dedicated `random.Random(seed)` instance. Simulation contains no wall-clock, network, process-global random, or platform service input. Values are rounded at artifact boundaries so reports remain stable across ordinary Python builds.

## Safety boundary

Policies request actions; they never directly mutate equipment state. The simulator clamps non-finite, over-power, over-energy, unavailable, and over-capacity requests, records each intervention, and calculates the safety score from the intervention log. Each step also closes an explicit source-to-sink balance: charging is limited to renewable/peaker surplus or an available grid, discharge and peaker output are limited to useful demand, and energy recorded as unserved can never increase battery state of charge.

## Schema policy

Artifacts use semantic schema versions independent of the package version. Scenario readers require exactly the documented root, series, event, and configuration fields and reject missing or unknown fields rather than applying defaults or guessing. Additive report fields may appear in a `1.x` schema; renames or semantic changes require a major schema version.

## Numeric boundary

Input numbers must be finite, but finite inputs can still overflow when multiplied or accumulated. The simulator therefore checks each derived energy, cost, emissions, state, total, and score operation and raises a controlled `ValueError` before rendering if a result is non-finite.
