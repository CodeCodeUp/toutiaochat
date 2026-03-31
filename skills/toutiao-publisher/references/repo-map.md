# Repo Map

Use this file when extracting or updating behavior from the current project.

## Browser automation

- File: `backend/app/services/publisher.py`
- Core responsibilities:
  - normalize cookies
  - launch Patchright
  - navigate to article or weitoutiao editors
  - import DOCX or fill content directly
  - input tags
  - verify publish success
  - capture screenshots on failure

## DOCX export

- File: `backend/app/services/docx_generator.py`
- Core responsibilities:
  - render title and content
  - place images by `cover`, `after_paragraph:N`, or `end`
  - save a reusable DOCX artifact

## Workflow handoff

- File: `backend/app/services/workflow/engine.py`
- Core responsibilities:
  - run stage order
  - decide whether auto-publish is enabled
  - hand article payload, tags, images, and DOCX into publisher logic
