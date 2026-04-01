---
name: toutiao-content-workflow
description: Generate Toutiao articles or micro-posts from a topic or brief, then refine them into a structured payload with title, content, tags, and image prompts. Use when Codex needs to create Toutiao-ready content, mirror a generate, optimize, image, and edit workflow, normalize AI output into a stable JSON contract, or prepare a finalized bundle for DOCX export or browser-based publishing.
---

# Toutiao Content Workflow

## Overview

Use this skill to turn a topic, outline, or raw brief into a stable Toutiao content bundle.

Keep the output contract stable even when the model response varies. Normalize every draft before handing it to downstream export or publishing steps.

Load [references/output-contract.md](references/output-contract.md) before validating payloads. Load [references/stage-map.md](references/stage-map.md) when you need to mirror the current repo's implementation details.
Load [references/weitoutiao-hot-patterns.md](references/weitoutiao-hot-patterns.md) when you need the latest observed platform-side traits for short Toutiao-style content.

Run `scripts/normalize_content_payload.py` whenever AI output is inconsistent, partially structured, or mixes prose with JSON.
Run `scripts/generate_article_bundle.py` for the database-free local workflow. It reads model settings from `data/local_settings.json`, stores generated topic history under `runtime/topics.json`, and saves article artifacts under `runtime/articles/`.
Run `scripts/generate_content_with_flow_images.py` when you want the full local chain: generate the article or weitoutiao bundle, select image prompts, call Google Flow, and backfill the saved local image paths into the article JSON and Markdown artifacts.
Run `scripts/open_google_flow_with_profile.py` to open Google Flow with a persistent automation-only Chrome profile stored inside this project. Log in once with that profile, then reuse it for later image-generation automation.
Load [references/google-flow-image-automation.md](references/google-flow-image-automation.md) before automating Google Flow image generation. Run `scripts/flow-playwright/generate_flow_images.js` after the profile is logged in to send a prompt, wait for new image cards, and download the resulting files into the skill runtime.

## Workflow

1. Choose the content type first.
Use `article` for a standard headline-driven post.
Use `weitoutiao` for a shorter micro-post where the title can stay empty.

2. Generate the first draft from a topic or brief.
Ask for a structured response that can be reduced to `title`, `content`, `tags`, and `image_prompts`.

3. Normalize the payload immediately.
Strip `#` from tags, deduplicate them, cap them at five, and convert image prompt items into `{description, position}` objects.

4. Run the optimize pass only after the draft is structurally usable.
Treat optimization as rewriting, not re-planning. Keep the topic, thesis, and major structure unless the user explicitly asks to change them.

5. Create or revise image prompts after the text is mostly final.
Prefer `cover`, `after_paragraph:N`, and `end` positions only.

6. If Google Flow image generation is requested, use the first image prompt by default.
Backfill the local image file paths into the saved bundle after the Flow run succeeds. Use every prompt only when the caller explicitly wants all prompt variants generated.

7. Hand the normalized bundle to the publisher skill.
Do not export DOCX or attempt browser publishing until the content payload and image paths are stable.

## Operating Rules

- Require a non-empty title for `article` unless the user explicitly wants a titleless draft artifact.
- Allow an empty title for `weitoutiao`, but preserve a working title if the model provides one.
- Keep `tags` short, literal, and platform-ready.
- Prefer image prompt descriptions that mention scene, style, subject, and mood in one compact sentence.
- If the model returns only prose, convert it into the output contract instead of asking the user to restructure it manually.
- If the user asks for a conversational multi-step workflow, keep stage snapshots so later steps can compare before and after versions.

## Repo Mapping

- Current generate stage logic lives in `backend/app/services/workflow/stages/generate.py`.
- Current optimize stage logic lives in `backend/app/services/workflow/stages/optimize.py`.
- Current image prompt and image generation orchestration lives in `backend/app/services/workflow/stages/image.py`.
- Current edit-stage handoff logic lives in `backend/app/services/workflow/stages/edit.py`.
- Current end-to-end stage transitions live in `backend/app/services/workflow/engine.py`.

Use those files as the source of truth when you need to keep behavior aligned with this repo.

## Resources

- `references/output-contract.md`
Field contract for article and micro-post payloads.

- `references/stage-map.md`
Stage-by-stage behavior, including manual vs auto flow.

- `references/weitoutiao-hot-patterns.md`
Observed writing traits, lengths, opening patterns, and direction options for short Toutiao-style content.

- `references/google-flow-image-automation.md`
Verified Google Flow page steps, selectors, and download logic for project-local image generation automation.

- `scripts/normalize_content_payload.py`
Normalize AI output into the contract used by the rest of the workflow.

- `scripts/generate_article_bundle.py`
Call the model through an OpenAI-compatible API, inject the full historical topic list into every request, and save generated topics plus articles to local files.

- `scripts/generate_content_with_flow_images.py`
Run the end-to-end local workflow: generate content, call Google Flow for image generation, and backfill the downloaded local image paths into the saved article bundle.

- `scripts/open_google_flow_with_profile.py`
Open the Google Flow project with a persistent Chrome profile so the login session can be reused later.

- `scripts/flow-playwright/generate_flow_images.js`
Open the logged-in Google Flow project in Chrome, type a prompt into the editor, wait for newly generated image cards, and download the resulting media files.

- `assets/prompts/`
Prompt templates for article and weitoutiao generation.
