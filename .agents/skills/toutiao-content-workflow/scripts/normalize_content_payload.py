#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Normalize a Toutiao content payload into a stable JSON contract."
    )
    parser.add_argument("input", help="Path to the source JSON file.")
    parser.add_argument(
        "--output",
        help="Write normalized JSON to this path. Defaults to stdout.",
    )
    parser.add_argument(
        "--content-type",
        choices=["article", "weitoutiao"],
        help="Override the content_type field in the payload.",
    )
    parser.add_argument(
        "--allow-empty-title",
        action="store_true",
        help="Allow an empty title even when content_type is article.",
    )
    return parser.parse_args()


def load_payload(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise SystemExit(f"Input file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc}") from exc


def normalize_tags(raw_tags: object) -> list[str]:
    if not isinstance(raw_tags, list):
        return []

    result: list[str] = []
    seen: set[str] = set()
    for item in raw_tags:
        if not isinstance(item, str):
            continue
        tag = item.strip().lstrip("#").strip()
        if not tag:
            continue
        key = tag.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(tag)
        if len(result) >= 5:
            break
    return result


def count_paragraphs(content: str) -> int:
    return len([block for block in content.splitlines() if block.strip()])


def normalize_position(position: object, paragraph_count: int) -> str:
    if position in {"cover", "end"}:
        return str(position)

    if isinstance(position, str) and position.startswith("after_paragraph:"):
        suffix = position.split(":", 1)[1].strip()
        if suffix.isdigit():
            number = int(suffix)
            if 1 <= number <= max(paragraph_count, 1):
                return f"after_paragraph:{number}"
    return "end"


def normalize_image_prompts(
    raw_prompts: object,
    paragraph_count: int,
    content_type: str,
) -> list[dict[str, str]]:
    if not isinstance(raw_prompts, list):
        return []

    prompts: list[dict[str, str]] = []
    for index, item in enumerate(raw_prompts):
        if isinstance(item, str):
            description = item.strip()
            if not description:
                continue
            position = "cover" if index == 0 else "end"
            prompts.append({"description": description, "position": position})
            continue

        if isinstance(item, dict):
            description = str(item.get("description", "")).strip()
            if not description:
                continue
            prompts.append(
                {
                    "description": description,
                    "position": normalize_position(item.get("position", "end"), paragraph_count),
                }
            )
    if content_type == "weitoutiao":
        if not prompts:
            return []
        first = dict(prompts[0])
        first["position"] = "cover"
        return [first]

    return prompts


def normalize_payload(payload: dict, content_type_override: str | None, allow_empty_title: bool) -> dict:
    content_type = content_type_override or payload.get("content_type") or "article"
    content_type = str(content_type).strip().lower()
    if content_type not in {"article", "weitoutiao"}:
        raise SystemExit(f"Unsupported content_type: {content_type}")

    title = str(payload.get("title", "") or "").strip()
    content = str(
        payload.get("content")
        or payload.get("body")
        or payload.get("text")
        or ""
    ).strip()

    if not content:
        raise SystemExit("Content is required.")

    if content_type == "article" and not title and not allow_empty_title:
        raise SystemExit("Title is required for article payloads.")

    paragraph_count = count_paragraphs(content)
    return {
        "content_type": content_type,
        "title": title,
        "content": content,
        "tags": normalize_tags(payload.get("tags", [])),
        "image_prompts": normalize_image_prompts(
            payload.get("image_prompts", []),
            paragraph_count,
            content_type,
        ),
    }


def write_output(data: dict, output_path: str | None) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if output_path:
        Path(output_path).write_text(text + "\n", encoding="utf-8")
        return
    sys.stdout.write(text + "\n")


def main() -> None:
    args = parse_args()
    payload = load_payload(Path(args.input))
    normalized = normalize_payload(payload, args.content_type, args.allow_empty_title)
    write_output(normalized, args.output)


if __name__ == "__main__":
    main()
