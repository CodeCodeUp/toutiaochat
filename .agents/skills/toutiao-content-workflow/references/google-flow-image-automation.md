# Google Flow Image Automation

This workflow uses the project-local Chrome profile at `browser-profile/chrome` so Google login can be reused without touching the user's everyday browser profile.

## Verified steps

1. Open `https://labs.google/fx/zh/tools/flow/project/354a1f5c-6935-4e53-9cde-8efe14b8349b` with a persistent Chrome profile.
2. If the cookie banner appears, click `OK, got it`.
3. Focus the bottom prompt editor:
   - selector: `div[role="textbox"][contenteditable="true"]`
   - the editor is a Slate contenteditable, so keyboard typing is more reliable than `fill()`
4. Type the image prompt.
5. Click the bottom `arrow_forward / create` button.
6. Wait for new generated media cards to appear.
   - generated images use URLs shaped like `/fx/api/trpc/media.getMediaUrlRedirect?name=<uuid>`
   - the current Flow setup now yields one new image per run
7. Download the newly generated media through the same authenticated browser context.
   - verified response type: `image/jpeg`
   - the redirect target currently resolves to a Google Cloud Storage URL
8. Save the downloaded images plus a `result.json` manifest under `runtime/flow-images/<timestamp>/`

## Stable selectors and signals

- Prompt editor: `div[role="textbox"][contenteditable="true"]`
- Create button: `button` containing `arrow_forward`
- Cookie button: `button` with text `OK, got it`
- Generated image source pattern:
  - `/fx/api/trpc/media.getMediaUrlRedirect?name=<uuid>`

## Why download via media URL instead of a UI menu

The generated cards already expose authenticated media URLs in the DOM. Downloading through the same browser context is more stable than trying to hover cards and chase changing menu buttons, while still respecting the login session stored in the project profile.

## Stealth-oriented launch choices

The current script intentionally reduces obvious automation fingerprints by:

- reusing a persistent Chrome profile saved inside this project
- launching the system Chrome channel instead of the bundled Chromium
- running headed instead of headless
- removing Playwright's default `--enable-automation`
- adding `--disable-blink-features=AutomationControlled`
- overriding `navigator.webdriver`, `navigator.languages`, `navigator.plugins`, and `window.chrome`

This lowers the chance of simple automation checks, but it does not guarantee invisibility against stronger anti-bot systems.

## Script

Use `scripts/flow-playwright/generate_flow_images.js`.

Example:

```powershell
node .agents\skills\toutiao-content-workflow\scripts\flow-playwright\generate_flow_images.js --prompt "A yellow banana on a minimal studio background, photorealistic, soft light."
```

Optional flags:

- `--timeout-seconds 600`
- `--expected-count 1`
- `--output-dir <path>`
