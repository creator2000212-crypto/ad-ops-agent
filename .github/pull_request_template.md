## What and why

<!-- The problem, the resulting behavior, and what is out of scope. -->

## Decision impact

<!--
Does this change what the engine decides on the fictional round?
Paste the output of `git diff -- demo/expected/summary.json`, or write "none".
If a decision changed, say which rule or threshold caused it and why the new
verdict is right. Regenerate with `python3 demo/run_demo.py --refresh`, read the
diff, then commit the expected files.
-->

```diff
```

## Verification

<!-- Tick what you ran; CI runs the same list on Python 3.9 and 3.13. -->

- [ ] `python3 -m unittest discover -s tests -v`
- [ ] `python3 demo/run_demo.py --check` (English and Chinese reports)
- [ ] `readback.py` and `preflight.py` golden checks (see CONTRIBUTING.md)
- [ ] `python3 scripts/render_decision_matrix.py --check`
- [ ] `python3 scripts/render_visuals.py --check`
- [ ] `python3 scripts/check_repository.py`
- [ ] CHANGELOG.md updated under the unreleased version

## Safety

- [ ] No real ad account, Page, pixel, campaign or advertiser IDs, offer or tracking domains, partner names, amounts from real accounts, tokens or local paths. Fixtures use fictional values and `example.com`.
- [ ] The offline boundary is unchanged: no network call, credential or platform write was added to the public code, and `native_platform_calls` stays 0.
- [ ] Nothing here helps an ad pass review without fixing it. Disapprovals are handled only by fixing the content and resubmitting, or by the platform's review process.
- [ ] A write still needs a passed gate and an approved batch; `ready` and `ACTIVATE` still mean "state check passed", not "approved".
