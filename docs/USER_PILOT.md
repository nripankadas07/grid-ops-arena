# Try Grid Ops Arena and tell us what breaks

For energy modelling students, educators, and Python developers. Pick the browser route or a local task below; stopping at a
blocker is useful feedback. The times are estimates, not a completion requirement.

[Give first-use feedback](https://github.com/nripankadas07/grid-ops-arena/issues/new?template=user_feedback.yml) ·
[See known limitations](limitations.md)

## Try it in your browser (about 5 minutes)

Open the [synthetic dispatch report](https://nripankadas07.github.io/grid-ops-arena/).
Find an hour with unmet demand or a constraint violation. Use the step trace to
explain what was requested and what was feasible. Which missing explanation would
make this easier to use in a class or policy review?

## Compare two policies (about 15 minutes)

Requires Git and Python 3.9 or newer. These commands run from the checkout without
installing the package:

```bash
git clone https://github.com/nripankadas07/grid-ops-arena.git
cd grid-ops-arena
PYTHONPATH=src python3 -m grid_ops_arena demo --seed 17 --hours 48 --policy balanced --output-dir pilot/balanced
PYTHONPATH=src python3 -m grid_ops_arena demo --seed 17 --hours 48 --policy resilience --output-dir pilot/resilience
```

Open `pilot/balanced/grid_ops_report.html` and
`pilot/resilience/grid_ops_report.html`. Keep seed and hours identical. Compare
reliability, unserved energy, cost, emissions, and constraint violations. Pick a
policy for a stated teaching objective and point to one trace step supporting
your choice. Matching results are possible; report that and compare the
policy rationales rather than inventing a winner. Do not infer that a composite
score alone makes a policy better.

## Test a question from your own work

Copy `examples/synthetic_scenario.json` to `pilot-scenario.json`. Change
`config.battery_max_power_kw` from `35` to `10`, preserving every other field.
Predict how that constraint should affect dispatch, then run both versions:

```bash
PYTHONPATH=src python3 -m grid_ops_arena run --scenario examples/synthetic_scenario.json --policy balanced --output-dir pilot/original
PYTHONPATH=src python3 -m grid_ops_arena run --scenario pilot-scenario.json --policy balanced --output-dir pilot/lower-power
```

Use these synthetic inputs to represent a question relevant to your class,
research, or prototype. Report expected versus observed behavior, including a
step number. Do not upload private grid data. This hourly single-bus educational
simulator does not validate real dispatch, protection, or planning decisions.
Read [limitations](limitations.md).

## Share a specific observation

Use the [feedback form](https://github.com/nripankadas07/grid-ops-arena/issues/new?template=user_feedback.yml). It asks for your task, route, outcome,
version, and one specific result or blocker. Browser reviews and bundled-fixture
runs help test usability; applying a relevant question from your own work gives
stronger evidence of usefulness. A claim that you would return is different from
actually returning: if you try it again, add a dated comment to the same issue
with the new task and result.

**Feedback is public.** Do not post secrets, personal records, private customer
or employer data, or raw private event ledgers. Quotes need your separate approval.
Security concerns belong in the repository's security-reporting path, not this
public form. No reward, star, or endorsement is required.
