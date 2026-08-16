# Limitations

- All bundled inputs are synthetic and unsuitable as current grid or climate evidence.
- The simulator uses one-hour, single-bus energy balance; it has no AC/DC power flow, voltage, frequency, reactive power, ramp, minimum-run-time, or protection model.
- Battery aging, thermal limits, degradation cost, and state-of-health are omitted.
- Peaker starts are instantaneous except for explicit availability events.
- Grid exports are represented as curtailed surplus and receive no market value.
- The composite score is an explicit demonstration weighting, not a regulatory or investment standard.
- Reliability is bounded to `[0, 1]`; safety and composite scores are bounded to `[0, 100]`. These bounds prevent invalid score artifacts but do not make the demonstration weights externally calibrated.
- Scenario JSON requires the exact versioned root, series, event, and configuration fields, actual JSON booleans for availability, and finite JSON numbers for grid configuration. Missing fields, unknown fields, string coercion, and integers too large for the simulator's floating-point representation are intentionally rejected at the trust boundary.
- Finite inputs that overflow during multiplication or accumulation terminate with a controlled validation error; no partial report is written.
- Policy actions that cannot be represented as finite floating-point values are recorded as constraint violations and clamped to zero.
- Report output path components and pre-existing artifacts must be real directories and regular files, not symbolic links. The three report formats are staged before commit and restored as one prior set if publication fails partway through. Cooperating writers serialize publication with an advisory lock on the verified output directory; locking fails closed when unavailable, but cannot coordinate non-cooperating writers or filesystems that ignore `flock`-style locks.
- Markdown reports conservatively encode punctuation in untrusted labels and descriptions, including image, link, and autolink delimiters. This favors inert output over preserving rich Markdown in user-controlled text.
- Baselines are heuristics, not optimal controllers.
- Floating-point arithmetic and simplified efficiencies make the tool inappropriate for settlement.

Use the project to compare software behavior under a controlled synthetic scenario, not to operate equipment or make financial, safety, or policy decisions.
