# Stage Map

This repo uses a four-stage workflow plus completion.

## Generate

- Purpose: create the first usable draft.
- Repo source: `backend/app/services/workflow/stages/generate.py`
- Output: title, content, tags, and optional image prompts.

## Optimize

- Purpose: rewrite the draft without changing the core topic unless requested.
- Repo source: `backend/app/services/workflow/stages/optimize.py`
- Output: revised title and content, with the original version retained in stage data when needed.

## Image

- Purpose: create or refine image prompts, then call the image generator.
- Repo source: `backend/app/services/workflow/stages/image.py`
- Output: normalized `image_prompts` and generated image records with path, url, index, and position.

## Edit

- Purpose: preview the final content, make targeted edits, and prepare the final DOCX handoff.
- Repo source: `backend/app/services/workflow/stages/edit.py`
- Output: finalized content bundle and DOCX path.

## Completed

- Purpose: mark the workflow as ready for export or publishing.
- Repo source: `backend/app/services/workflow/engine.py`

## Manual vs auto

- Manual mode accepts stage-by-stage user feedback and stores conversation history.
- Auto mode executes the same logical order without waiting for user interaction.
- The current repo can skip optimize, image generation, or auto-publish based on workflow config flags.
