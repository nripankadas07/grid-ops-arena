# Changelog

All notable changes follow semantic versioning.

## 0.1.1 - 2026-08-16

- Reject arbitrarily large scenario and policy-action integers as controlled validation outcomes instead of leaking `OverflowError` tracebacks.
- Add regressions for oversized scenario series and configuration values at both the model and subprocess boundaries.
- Publish report bundles through a staged, symlink-safe writer that rejects linked destinations and restores the complete prior set after a mid-commit failure.
- Serialize cooperating report writers with an exclusive advisory lock on the verified output directory, recheck target identities immediately before publication, and reconcile rename outcomes before rollback when a filesystem wrapper raises after completing the operation.
- Close fallback temporary descriptors when text-stream setup fails, while removing the abandoned staged file.
- Ship examples, golden artifacts, documentation, and the release checker in the source distribution; CI now extracts the sdist and reruns its full suite on Python 3.9 and 3.12.
- Migrate package license metadata to the SPDX form and replace a retired research-document host with the paper's stable DOI.

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
