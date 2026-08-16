# AI-assisted development disclosure

OpenAI Codex assisted with research synthesis, architecture exploration, implementation scaffolding, documentation drafting, and test-case generation for the initial `0.1.0` release.

Human review remains required. The maintainer is responsible for accepting design decisions, verifying licenses and claims, reviewing changes, and deciding whether the software is appropriate for any use. AI-generated suggestions are treated like untrusted contributions: they must pass tests and domain review before merge.

## Verification performed for 0.1.0

- deterministic unit and CLI integration tests;
- adversarial oversized and non-finite action tests;
- strict JSON serialization and schema-version checks;
- byte-for-byte golden report comparison;
- Python 3.9 grammar, wheel-build, install, and console-script smoke tests.

No external project code or data was copied. The runtime makes no model or network calls, and all demo facts are explicitly synthetic.
