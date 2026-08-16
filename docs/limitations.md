# Limitations

- All bundled inputs are synthetic and unsuitable as current grid or climate evidence.
- The simulator uses one-hour, single-bus energy balance; it has no AC/DC power flow, voltage, frequency, reactive power, ramp, minimum-run-time, or protection model.
- Battery aging, thermal limits, degradation cost, and state-of-health are omitted.
- Peaker starts are instantaneous except for explicit availability events.
- Grid exports are represented as curtailed surplus and receive no market value.
- The composite score is an explicit demonstration weighting, not a regulatory or investment standard.
- Reliability is bounded to `[0, 1]`; safety and composite scores are bounded to `[0, 100]`. These bounds prevent invalid score artifacts but do not make the demonstration weights externally calibrated.
- Scenario JSON requires the exact versioned root, series, event, and configuration fields, actual JSON booleans for availability, and JSON numbers for grid configuration. Missing fields, unknown fields, and string coercion are intentionally rejected at the trust boundary.
- Finite inputs that overflow during multiplication or accumulation terminate with a controlled validation error; no partial report is written.
- Markdown reports conservatively encode punctuation in untrusted labels and descriptions, including image, link, and autolink delimiters. This favors inert output over preserving rich Markdown in user-controlled text.
- Baselines are heuristics, not optimal controllers.
- Floating-point arithmetic and simplified efficiencies make the tool inappropriate for settlement.

Use the project to compare software behavior under a controlled synthetic scenario, not to operate equipment or make financial, safety, or policy decisions.
