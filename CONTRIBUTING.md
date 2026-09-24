# Contributing

Contributions are welcome in Chinese or English. Start with the [architecture](docs/architecture.md) and [roadmap](docs/roadmap.md).

## Local checks

```bash
python3 -m unittest discover -s tests -v
python3 scripts/demo.py
python3 scripts/check_repository.py
```

Use fictional fixtures and keep generated state under the ignored `runs/` directory. Never include credentials, raw customer data, account exports or private campaign/media files in a commit, issue or pull request.

## Useful contributions

- A platform adapter for a clearly defined advertising product and operation.
- A connector binding with explicit field units, scopes, pagination and readback behavior.
- A workflow improvement that reduces manual configuration without hiding uncertainty.
- A documented operational recipe with applicable conditions, primary evidence, side effects and a way to verify the outcome.
- An executable test for meaningful failure or recovery behavior.

Keep product-specific strategy configurable. Do not hard-code one vendor's tool names into business logic or claim that all advertising platforms share one object graph.

## Knowledge contributions

The runtime catalog lives in `knowledge/catalog.json` and is loaded by `knowledge.py`. Files under `contracts/` remain design-only and are not automatically loaded. Read the [knowledge-base guide](docs/knowledge-base.zh-CN.md) before adding a runtime entry.

- Define the relevant platform, workflow stage, business conditions and required evidence. Unknown, conflicting or hypothetical inputs must not count as confirmed evidence.
- Distinguish official platform facts, reusable methods and experience-based hypotheses. Cite primary sources for platform claims and record a meaningful verification date and review interval. Do not refresh the date without checking the source.
- Document the recommendation, next evidence to collect, outcome verification and boundaries. A single campaign result does not establish a universal strategy or a causal effect.
- Keep recommendations advisory. A knowledge entry cannot add account access, change the approved budget, broaden authorization or execute a platform operation.
- Add meaningful tests for applicability, missing evidence and an incompatible context. Source freshness and catalog drift must preserve the existing plan-review boundary.

Keep private observations outside Git. Review and anonymize them before proposing public knowledge; feedback does not automatically promote itself into a rule. A catalog update changes the basis of frozen plans, so users must regenerate and review affected plans and their simulation authorization.

## Pull requests

Describe the problem, resulting behavior, scope and verification. Distinguish implemented code from design-only contracts and future acceptance scenarios. If a new native operation is added, document its real account/API support separately from mock tests; no public CI job should need ad credentials or spend money.

Preserve existing license notices. Contributions are licensed under the repository's MIT license.
