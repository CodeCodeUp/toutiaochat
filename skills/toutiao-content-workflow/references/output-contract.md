# Output Contract

Use one contract for every draft, even when the response starts as free-form text.

## Article payload

```json
{
  "content_type": "article",
  "title": "Readable headline",
  "content": "Full article body in markdown or plain paragraphs.",
  "tags": ["tag-1", "tag-2"],
  "image_prompts": [
    {
      "description": "Editorial cover image for the core idea.",
      "position": "cover"
    },
    {
      "description": "Supporting image after paragraph 3.",
      "position": "after_paragraph:3"
    }
  ]
}
```

## Weitoutiao payload

```json
{
  "content_type": "weitoutiao",
  "title": "",
  "content": "Short micro-post body.",
  "tags": ["tag-1"],
  "image_prompts": [
    {
      "description": "Simple visual for the post.",
      "position": "cover"
    }
  ]
}
```

## Field rules

- `title`
Required for `article`.
Optional for `weitoutiao`.

- `content`
Required for both content types.
Prefer final publishable prose, not notes.

- `tags`
Use a flat list of strings.
Strip a leading `#`.
Deduplicate while preserving order.
Limit to five tags.

- `image_prompts`
Allow either strings or objects during drafting, but normalize to objects before downstream use.
Use only these positions:
  - `cover`
  - `after_paragraph:N`
  - `end`

## Normalization rules

- Treat `body` or `text` as aliases for `content`.
- Convert invalid image positions to `end`.
- If paragraph counts are unknown, keep only `cover` and `end`.
- Preserve extra metadata outside this contract only when the caller explicitly needs it.
