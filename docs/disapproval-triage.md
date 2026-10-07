# Disapproval triage: fix or appeal

[简体中文](disapproval-triage.zh-CN.md) · [Operations cards (Chinese)](operations.md) · [Documentation guide](index.en.md)

**Disapprovals are resolved only by fixing the content or through the platform's review process.**

This page is the procedure the agent follows when an ad, creative or media asset does not go live. It separates two situations that can look the same in a status column: a technical upload or processing failure, and a policy disapproval. They need different actions, and only the first one is ever handled by uploading a file again.

**Scope:** this is a host-workflow procedure; [creative-recovery.json](../contracts/creative-recovery.json) is its design contract. The public Python code makes no platform calls, so it does not upload media, edit creatives, submit reviews or poll review state. The offline [operating loop](operating-loop.md) only flags the condition: an ad set whose configured status is `ACTIVE` while its effective status is `DISAPPROVED` raises `AD_STATUS`.

## Triage at a glance

| | A. Upload or processing failure | B. Policy disapproval |
|---|---|---|
| How you recognise it | Decode or format error, upload timeout, media stuck in processing, wrong asset reference. The object has **no** review decision | The platform's review state is disapproved or rejected and names a reason or policy |
| Action | Reconcile, then re-export to spec or re-upload **once**; log it; read back | Read the reason, then either fix the substance and submit the edited version, or Request Review with evidence |
| Done when | Media reads back ready and the ad references the intended asset | The review state reads back approved, with the edit or the appeal on record |
| Stop | A second technical failure on the same asset: stop and report the error | A second rejection for the same reason: stop; a human does the policy review |

## A. Upload and processing failures (no disapproval)

These are file, transport or reference problems. Nothing about the content has been judged.

1. **Reconcile before retrying.** A timeout does not mean nothing was created. Look up the upload session, returned IDs and existing assets first, then retry only what is actually missing. A batch of 25 creatives that timed out on Sep 10, 2026 was handled this way.
2. **Fix the file or the reference, once.** Re-export to the documented spec (container, resolution, duration, bitrate) or re-upload the file once. Correct a wrong asset reference on the object it belongs to. Keep the original and record the derived version.
3. **Log it.** Record the error as returned, the file version, the action, the returned IDs and timestamps.
4. **Read back.** Check that the media is ready, the placement previews render, and the ad references the intended asset. For Meta video, readiness is `status.video_status = ready`; the official uploader does not wait for encoding by default ([VideoUploader, pinned SDK commit](https://github.com/facebook/facebook-python-business-sdk/blob/5286888addfe3ba3718db65fbf132bd66de3ddfe/facebook_business/video_uploader.py)). A successful upload is not readiness, and readiness is not approval.

This route applies only while the object has no review decision. If it carries a disapproval, go to B: uploading again is not a review fix.

## B. Policy disapprovals

1. **Read the reason.** Record the native review state, the reason or policy named, the element it points to (claim, visual, copy, landing page or other destination) and the read time. Meta exposes configured and effective status, review feedback and issue details on the ad object ([Ad model, pinned SDK commit](https://github.com/facebook/facebook-python-business-sdk/blob/5286888addfe3ba3718db65fbf132bd66de3ddfe/facebook_business/adobjects/ad.py)). If no reason can be read, record the gap and escalate; do not guess.
2. **Choose one path.**
   - **Fix:** change the substance the reason points to (the claim, the visual, the copy or the landing page) and submit the edited version. Show the owner the before-and-after difference first, because a changed claim or landing page changes the agreed expression.
   - **Appeal:** if the content complies and the decision looks wrong, use the platform's official review channel (Meta calls it Request Review) and attach evidence: what the ad shows, the landing page and the product documentation that supports the claim.
3. **Read back.** Keep the submission or appeal receipt, then read the review state and effective status again. Approved, delivering and performing are three separate states.
4. **A second rejection for the same reason stops the case.** Do not submit again. Hand the case record (reason, edit made or evidence sent, receipts) to a human for policy review. The count follows the case, not object IDs: a new creative, ad, connector or account does not reset it. A rejection for a different reason opens its own triage on the same record.

### Never

- Re-upload unchanged or merely re-encoded media to get a fresh review.
- Duplicate a disapproved ad, or build a replacement with the same content, to get past review.
- Rotate ad accounts, Pages or identities to get past review.
- Report a new file, media ID, creative ID or ad ID as a fix. Only a content change or a review decision resolves a disapproval.

## What each case records

| Field | Example (fictional) |
|---|---|
| Case and objects | `case-0001`; ad `ad_demo_01`, creative `cr_demo_01`, video `vid_demo_01` |
| Reason as returned, with read time | "Unsupported claim in primary text", read 2026-01-12T09:40Z |
| Path | Fix |
| Change or evidence | Primary text: "guaranteed results" removed; landing page heading aligned |
| Approval reference | Owner approved the edited text in the batch review |
| Submission receipt and time | Edited version submitted 2026-01-12T10:05Z |
| Review readback | Approved at 2026-01-12T14:30Z; ad set effective status `ACTIVE` |
| Rejections for this reason | 1 (a second one escalates to human policy review) |

## Track content, not only IDs

A local file digest, a platform media reference (`image_hash` or `video_id`), a `creative_id`, an `ad_id` and a post reference (`object_story_id` / `effective_object_story_id`) are different objects ([AdCreative model](https://github.com/facebook/facebook-python-business-sdk/blob/5286888addfe3ba3718db65fbf132bd66de3ddfe/facebook_business/adobjects/adcreative.py)). Keep them in separate fields so a case history follows the content across objects. A new ID is not new content and does not reset a case.

## Authorization

Submitting an edited version and filing a Request Review are writes. They go through the same batch review as any other change: concrete difference, owner approval, execution through verified tools, then readback. A design contract, a past approval or a simulated authorization does not cover them.

Related: [operations cards](operations.md) for media, posts, links and states · [acceptance scenarios](../contracts/acceptance-scenarios.json) (`REC-*`) · [runtime knowledge base (Chinese)](knowledge-base.zh-CN.md), entry `KB-META-08`.

Back to the [documentation guide](index.en.md).
