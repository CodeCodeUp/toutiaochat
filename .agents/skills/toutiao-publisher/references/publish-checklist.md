# Publish Checklist

Use this checklist before every browser-based publish attempt.

## Preflight

1. Confirm the payload is finalized.
2. Confirm the target route:
   - article: `https://mp.toutiao.com/profile_v4/graphic/publish`
   - weitoutiao: `https://mp.toutiao.com/profile_v4/weitoutiao/publish?from=toutiao_pc`
3. Validate the cookie file.
4. Confirm image paths exist.
5. Export DOCX if the browser flow imports a document.

## Publish flow

1. Launch a headed browser unless you have a verified virtual display.
2. Inject normalized cookies before navigating to the editor.
3. Stop immediately if navigation lands on a login page.
4. Fill content or import DOCX.
5. Add tags only after the editor content is in place.
6. Publish and wait for a real completion signal.

## Success signals

- Success toast text
- Redirect to a known success or content page
- Another verified completion state from the live UI

## Failure handling

- Save a timestamped screenshot.
- Record the current URL.
- Record the selector or step that failed.
- Check whether the issue is:
  - expired cookies
  - changed selectors
  - missing upload input
  - failed confirmation dialog
