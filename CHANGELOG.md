# Changelog

All notable changes follow semantic versioning.

## 0.1.0 - 2026-08-16

- Enforce per-step source-to-sink energy balance and bounded reliability, safety, and composite scores.
- Reject coercive scenario booleans and non-numeric grid configuration with stable CLI errors.
- Require exact scenario root, series, and configuration schemas with no implicit defaults or unknown fields.
- Fail closed on non-finite derived multiplication, accumulation, state, or score arithmetic.
- Neutralize all Markdown image, link, and autolink delimiters in untrusted report text.
- Initial deterministic microgrid simulator.
- Versioned scenario and report schemas.
- Three baseline policies and enforced safety constraints.
- JSON, Markdown, and single-file HTML reports.
