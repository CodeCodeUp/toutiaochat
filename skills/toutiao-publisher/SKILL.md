---
name: toutiao-publisher
description: Export finalized Toutiao article or micro-post payloads to DOCX, validate cookie JSON, and drive browser-based publishing flows. Use when Codex needs to package finished Toutiao content, check account cookies, publish to article or weitoutiao editors, or troubleshoot browser automation failures during publication.
---

# Toutiao Publisher

## Overview

Use this skill after the content payload is finalized.

Package the draft into a deterministic export artifact, verify browser credentials before launch, and only then attempt publication.

Load [references/publish-checklist.md](references/publish-checklist.md) before any publish attempt. Load [references/repo-map.md](references/repo-map.md) when you need to align behavior with the current project implementation.

Run `scripts/validate_cookie_json.py` before browser automation. Run `scripts/export_docx.py` when the user wants a DOCX deliverable or when the publish flow imports DOCX into Toutiao.

## Workflow

1. Confirm the target route.
Use the article route for long-form posts.
Use the weitoutiao route for micro-posts.

2. Validate the publish inputs.
Check title, content, tags, image paths, cookies, and whether DOCX import is required.

3. Export the DOCX artifact if needed.
Prefer deterministic export over ad hoc formatting in the browser.

4. Launch browser automation in headed mode unless the target environment has a verified virtual display setup.
Capture screenshots on failure and preserve them with timestamps.

5. Publish only after a successful login check.
If login redirects appear, stop and refresh credentials instead of retrying blindly.

## Operating Rules

- Normalize cookies before browser launch.
- Prefer explicit article or weitoutiao routes over generic publishing code paths.
- Preserve a final publish bundle that includes the normalized payload, DOCX path, image list, and cookie source path.
- Treat DOM selectors as unstable. When the page changes, inspect live selectors before patching automation logic.
- Do not mark a publish as successful until the UI shows a success toast, a success redirect, or another confirmed completion state.

## Repo Mapping

- Current browser automation logic lives in `backend/app/services/publisher.py`.
- Current DOCX export logic lives in `backend/app/services/docx_generator.py`.
- Current auto-publish handoff lives in `backend/app/services/workflow/engine.py`.
- Current account validation API logic is part of `PublisherService.check_account_status`.

Use those files when you need to pull selectors, publish routes, or environment assumptions from the repo.

## Resources

- `references/publish-checklist.md`
Preflight and troubleshooting flow for publication.

- `references/repo-map.md`
Quick map back to the project files and browser routes.

- `scripts/export_docx.py`
Create a DOCX deliverable from the normalized content payload.

- `scripts/validate_cookie_json.py`
Normalize and validate the cookie file before browser automation.
