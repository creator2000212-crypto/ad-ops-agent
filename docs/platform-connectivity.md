# Connect Meta, TikTok and Google Ads through API, SDK or MCP

[简体中文：完整平台申请指南](platform-connectivity.zh-CN.md) · [First use](first-check.md) · [Host workflow](workflow.md)

> The platform references below were checked for the existing guide on **2026-09-24**. This documentation reorganization did not reverify provider capabilities. Entry points, permissions, plans and supported tools can change; check current official documentation and actual account access before configuring them.

There are two routes: use existing tools exposed to the host, or develop an independent application that calls platform APIs. A verified, authorized host connection can support the [host workflow](workflow.md) without first implementing this repository's Python adapters. The public Python modules remain offline and do not acquire live capabilities when the host connects an MCP server.

For your first task, follow [First use](first-check.md); this page is a connection reference to open when needed. Start with the task and selected accounts. Read-only analysis needs its relevant reading/reporting access. The first complete configuration/publishing workflow verifies the necessary reading, writing and native readback capabilities before business intake. All three platforms need not be connected, and purchasing a service does not prove access or authorize operations.

Start by verifying the connection the user already has, or the route they chose. If there is none, compare the routes below and choose by their trade-offs. They are listed in no particular order; this project does not prefer one.

## Choose the connection route

| Route | What it needs | Trade-offs | What remains your responsibility |
|---|---|---|---|
| Official API | Developer/cloud setup, account authorization, permissions and maintained calls | Full control of permissions, fields and versions, with no third party in the access path; you maintain OAuth, tokens and the adapter | Business context, native semantics, review and verification |
| Official SDK | API access plus a development environment | Less request and model boilerplate; the same app registration and permissions as the API | SDK installation does not grant permissions |
| Platform MCP | A compatible host and the platform's required authorization | Run by the platform; tool coverage differs by platform (see each section below) | Actual tool coverage, object differences and action authorization |
| Self-hosted MCP server | The API's developer apps and tokens, plus somewhere to run the server | A tool interface for the agent while credentials, hosting and the exposed tool list stay under your control; you maintain and secure the server | Same as the official API |
| Hosted MCP connector | Provider account, selected account authorization, compatible host and suitable plan | Little setup or connection maintenance; adds a third party to the access path, and coverage, limits, pricing and data handling are set by the provider | Account eligibility, unsupported capabilities, decisions and result checks |

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

## Use an MCP server: self-hosted or hosted

Both expose platform tools to the agent. They differ in who runs the server and holds the credentials.

- **Self-hosted:** run an open-source or self-built MCP server on top of the official APIs above, with your own developer apps and tokens. Expose only the tools the task needs; a read-only tool list is a stronger boundary than a read-only chat instruction.
- **Hosted connector:** a provider runs the server and the account authorization flow, for example [Pipeboard](https://pipeboard.co). Read the provider's current documentation, plans, limits and data-handling terms; a plan name alone does not prove a writing capability.

For either:

1. Connect only the selected accounts for this work. Read the resulting account list without automatically including every visible business or manager account.
2. Follow the server's or provider's own setup instructions for your agent client. Store credentials in secure configuration, never in a conversation or the repository. Verify account identity with reading results, then check writing and readback capabilities only when the task needs them.
3. Prepare the batch through actual tool schemas. Verify platform product, native IDs, amount units, dependencies and explicit initial statuses. Default statuses for new objects differ between platforms and tools, so set status explicitly and read it back.

A connector reduces connection work. It does not replace account permissions, assets, conversion configuration, review, authorization or result verification. A host can use verified tools now within its actual supported scope; making the **Python program itself** publish still requires implementation and verification of native adapters and production execution controls.

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
