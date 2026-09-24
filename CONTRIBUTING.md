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

## Pull requests

Describe the problem, resulting behavior, scope and verification. Distinguish implemented code from design-only contracts and future acceptance scenarios. If a new native operation is added, document its real account/API support separately from mock tests; no public CI job should need ad credentials or spend money.

Preserve existing license notices. Contributions are licensed under the repository's MIT license.

