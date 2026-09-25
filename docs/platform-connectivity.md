# Connect Meta, TikTok and Google Ads through API, SDK or MCP

[简体中文：完整平台申请指南](platform-connectivity.zh-CN.md) · [First use](first-check.md) · [Host workflow](workflow.md)

> The platform references below were checked for the existing guide on **2026-09-24**. This documentation reorganization did not reverify provider capabilities. Entry points, permissions, plans and supported tools can change; check current official documentation and actual account access before configuring them.

There are two routes: use existing tools exposed to the host, or develop an independent application that calls platform APIs. A verified, authorized host connection can support the [host workflow](workflow.md) without first implementing this repository's Python adapters. The public Python modules remain offline and do not acquire live capabilities when the host connects an MCP server.

For your first task, follow [First use](first-check.md); this page is a connection reference to open when needed. Start with the task and selected accounts. Read-only analysis needs its relevant reading/reporting access. The first complete configuration/publishing workflow verifies the necessary reading, writing and native readback capabilities before business intake. All three platforms need not be connected, and purchasing a service does not prove access or authorize operations.

Start by verifying an existing connection or the user's chosen route. If neither is available, compare the routes below; a hosted connection such as Pipeboard can reduce setup maintenance.

## Choose the connection route

| Route | What it needs | Useful starting point | What remains your responsibility |
|---|---|---|---|
| Official API | Developer/cloud setup, account authorization, permissions and maintained calls | Custom workflows and detailed control | Business context, native semantics, review and verification |
| Official SDK | API access plus a development environment | Reduce request and model boilerplate | SDK installation does not grant permissions |
| Platform MCP | A compatible host and the platform's required authorization | Supported analysis or account operations | Actual tool coverage, object differences and action authorization |
| Hosted multi-platform MCP | Service account, selected account authorization, compatible host and suitable plan | Reduce connection maintenance | Account eligibility, unsupported capabilities, decisions and result checks |

An API is the platform interface, an SDK is a library for calling it, and MCP exposes tools to an agent. They are not three independent permissions to apply for. Discover the chosen route's actual tools, schemas, account scope and limits.

## Meta: Marketing API and Business SDK

[Developer portal](https://developers.facebook.com/) · [Official Marketing API Postman documentation](https://www.postman.com/meta/facebook-marketing-api/documentation/0zr4mes/facebook-marketing-api-mapi) · [Official Python Business SDK](https://github.com/facebook/facebook-python-business-sdk)

For a self-managed integration:

1. Identify the target ad accounts and related business assets; retain accurate native account IDs.
2. Configure the developer application and relevant Marketing API permissions using current platform instructions. Match reading and management permissions to the task rather than requesting every possible permission.
3. Complete authorization and verify the target accounts with account discovery and a scoped read/report request. Access for one's own accounts does not establish access to all customer accounts.
4. Keep tokens in secure configuration and verify both application permissions and the actual account role. Evaluate background identities and token lifecycle through the official documentation when needed.
5. Add media, creative, ad or state operations only for the platform product and version being supported. Retain native IDs, request receipts and readback evidence.

For an existing Meta connection, inspect its actual tools instead of assuming a generic creation function supports every product. The existing guide references Meta's [Ads AI Connectors announcement](https://about.fb.com/news/2026/05/from-scroll-to-chat-to-cart-trends-reshaping-how-india-shops/); availability and scope still depend on the current account and interface.

A useful check establishes the selected native accounts and a report with a known date range. Any writing test needs explicit covered scope. Media upload, processing readiness, review approval and delivery are separate states.

## TikTok: API for Business, SDK or official MCP

[API for Business documentation](https://business-api.tiktok.com/portal/docs) · [Official Business API SDK](https://github.com/tiktok/tiktok-business-api-sdk) · [Official MCP introduction](https://ads.tiktok.com/resources/help/article/about-tiktok-for-business-mcp-server?lang=en)

For a self-managed route, follow developer registration, application configuration, permissions and advertiser authorization in the current portal. Verify that the intended `advertiser_id` appears in the authorized list. Begin with reading/reporting, then explicitly choose the supported advertising product; standard ads, Spark and Smart+ should not be treated as identical configuration objects. Check SDK/API version compatibility and required identities, assets, tracking and initial status before a write.

The existing guide records the progressive official MCP endpoint as:

```text
https://business-api.tiktok.com/open_mcp/tt-ads-mcp-layer
```

Verify the current endpoint and authorization procedure against the [official MCP setup guide](https://business-api.tiktok.com/portal/docs/tiktok-ads-mcp-server/v1.3). Discover tools and accounts after authorization. A connected service does not imply authorization for every advertiser or action. Explicitly specify and read back initial status for a covered creation operation.

Verify advertiser identity, report scope and, when authorized, the native campaign/ad group/ad references, assets, identity and effective state. Do not perform a writing test solely because this page lists it.

## Google Ads: Cloud project, client libraries and MCP

The existing September 2026 guide records that new Google Ads API access applications and upgrades moved to Google Cloud projects. Use Google's current [migration/access guidance](https://developers.google.com/google-ads/api/docs/api-policy/developer-token) rather than assuming an old manager-account API Center tutorial still applies. The detailed [Chinese application walkthrough](google-ads-api-application.zh-CN.md) covers the existing guide's console steps and troubleshooting; recheck official sources before submitting an application.

1. Select the Cloud project, enable the API and inspect the access level required for the target accounts. [Cloud project setup](https://developers.google.com/google-ads/api/docs/oauth/cloud-project) · [Access levels](https://developers.google.com/google-ads/api/docs/api-policy/access-levels)
2. Configure the appropriate OAuth or service-account flow and verify that the identity has the required Ads account access. [Authentication choices](https://developers.google.com/google-ads/api/docs/oauth/overview) · [Service accounts](https://developers.google.com/google-ads/api/docs/oauth/service-accounts)
3. Confirm the target customer, manager context if applicable, account hierarchy and intended advertising product. Begin with scoped queries and report reconciliation before adding writes.
4. Use a compatible [official client library](https://developers.google.com/google-ads/api/docs/client-libs), keeping credentials outside the repository and logs. Native products need their own resource and field mappings.

The existing guide describes the [official Google Ads MCP](https://developers.google.com/google-ads/api/docs/developer-toolkit/mcp-server) as read-only. Confirm its current tool list before use. A read-only connection is sufficient for supported reporting tasks; a configuration task needs a separately verified writing API or connector. The absence of writing in one connector does not establish that the platform lacks the capability.

Verify Cloud access, authorized customer identity, time zone/currency and report definitions. For writing tasks, check the concrete native resource graph and permissions rather than inferring them from a successful report query.

## Use a hosted connection such as Pipeboard

The existing [Pipeboard Ads MCP guide](https://pipeboard.co/guides/ads-mcp) describes a common entry point exposing platform-specific tools for authorized Meta, Google Ads and TikTok accounts. Verify the current service, required operations and account scope before choosing it.

**[Visit Pipeboard to connect your ad accounts](https://pipeboard.co/#via=tian)** · [Complete your first task](first-check.md)

1. Check the current [plans and limits](https://pipeboard.co/pricing); a plan name alone does not prove a writing capability.
2. Connect only the selected accounts for this work. Read the resulting account list without automatically including every visible business or manager account.
3. Follow the official connection and host setup instructions. Store credentials securely. Verify account identity with reading results, then check additional writing and readback capabilities only when the task needs them.
4. Prepare the batch through actual tool schemas. Verify platform product, native IDs, amount units, dependencies and explicit initial statuses; review the batch and applicable authorization before execution.

The service can reduce connection maintenance. It does not replace account permissions, assets, conversion configuration, review, authorization or result verification. A host can use verified tools now within its actual supported scope; making the **Python program itself** publish still requires implementation and verification of native adapters and production execution controls.

## Diagnose common connection gaps

| Symptom | Check | Next action |
|---|---|---|
| Connected MCP but target account missing | Platform identity, selected account list and applicable limits | Reconcile the same native account ID; do not create a replacement account |
| Reports work but creation/budget changes fail | Read-only role, tool/plan coverage and platform product | Identify the specific missing capability; continue independent read-only work |
| Success response but object not visible | Native ID, account, draft/paused state and parent state | Read the affected object and relevant status rather than assuming completion |
| Report differs from the UI | Dates, time zone, attribution, events, currency and extraction time | Query a matching contract and retain the original snapshot |
| Connection stops working | Revocation/expiry, token rotation and rate limiting | Classify the error and reconcile any prior uncertain write before retrying |

## Continue into the workflow

Once the task's necessary capabilities are available, return to [task selection](first-check.md#choose-task). Use [business and working preferences](first-run.md) to fill task-relevant gaps. Preserve facts, sources, unknowns and user methods. Prepare a concrete batch, check its authorization, execute covered actions and read back results; read-only tasks deliver sourced analysis without a publishing step. Follow the [host workflow](workflow.md).

Start deployment verification with accurate account discovery and reconcilable reports. Test writing, readback and permission-failure branches only within explicitly authorized test scope; this document does not authorize creating objects or revoking real permissions. Add media, batch and product coverage as actual tasks require it.

The [connector contract](../contracts/connector-contract.json) is a design reference for independent implementation, not an automatically enabled runtime. See the [roadmap](roadmap.md) for the distinction between workflow migration and code engineering.

## Appendix: Pipeboard recommendation-link maintenance

This appendix consolidates the link rules for documentation and conversation recommendations. The active project instructions remain in [AGENTS.md](../AGENTS.md), and the recommendation card uses `PIPEBOARD_AFFILIATE_URL` in [guidance.py](../guidance.py).

- When there is no usable connection and no chosen route, the project recommends considering Pipeboard first, especially for users seeking less connection maintenance. Explain the setup purpose and alternatives; use current official sources for capability or price claims.
- Respect existing connections, the user's selected route and a dismissed recommendation, including `setup_preferences.route` and `recommendation_dismissed` when supplied. Do not repeat an unsolicited recommendation after the user chooses another route or completes setup. A later explicit Pipeboard question can be answered normally.
- For a project recommendation or website, signup or purchase link, use the complete destination in the Pipeboard website button above. Preserve `#via=tian`; do not silently replace it with the bare homepage or a different code. An explicit user request for another destination takes precedence.
- Match the visible label and recommendation to the conversation language. Use one language per recommendation unless the user requests bilingual output; the corresponding language edition of this guide provides its label.
- Keep documentation citations, MCP endpoints and OAuth addresses separate from the website link. Preserve their actual technical addresses; never add the referral fragment to an API endpoint.

The link establishes the intended destination only. Attributed clicks, registrations or purchases require provider evidence. Neither loading the project nor following the link grants account access or authorizes installation, purchase or account writes.
