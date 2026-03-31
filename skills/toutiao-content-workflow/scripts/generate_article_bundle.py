#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from openai import OpenAI
from openai import APIError
from openai import APIStatusError

from normalize_content_payload import normalize_payload

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
DATA_DIR = SKILL_DIR / "data"
RUNTIME_DIR = SKILL_DIR / "runtime"
ARTICLES_DIR = RUNTIME_DIR / "articles"
TOPICS_FILE = RUNTIME_DIR / "topics.json"
SETTINGS_FILE = DATA_DIR / "local_settings.json"
PROMPT_DIR = SKILL_DIR / "assets" / "prompts"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a Toutiao article bundle with local file storage."
    )
    parser.add_argument(
        "--content-type",
        choices=["article", "weitoutiao"],
        default="article",
        help="Content type to generate.",
    )
    parser.add_argument(
        "--topic",
        help="Optional user-specified topic. If omitted, the model must propose a fresh topic.",
    )
    parser.add_argument(
        "--material",
        help="Inline source material. Required for weitoutiao unless --material-file is used.",
    )
    parser.add_argument(
        "--material-file",
        help="Path to a UTF-8 or UTF-8-BOM text file containing source material.",
    )
    parser.add_argument(
        "--allow-duplicate-topic",
        action="store_true",
        help="Allow a user-specified topic even if it already exists in local topic history.",
    )
    return parser.parse_args()


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def ensure_runtime_dirs() -> None:
    ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_settings() -> dict:
    if not SETTINGS_FILE.exists():
        raise SystemExit(
            f"Missing settings file: {SETTINGS_FILE}. Copy local_settings.example.json first."
        )
    settings = load_json(SETTINGS_FILE, {})
    model = settings.get("model", {})
    if not model.get("api_url") or not model.get("api_key") or not model.get("model"):
        raise SystemExit("local_settings.json must define model.api_url, model.api_key, and model.model.")
    return settings


def load_prompt(content_type: str) -> str:
    name = "weitoutiao-generate.md" if content_type == "weitoutiao" else "article-generate.md"
    path = PROMPT_DIR / name
    if not path.exists():
        raise SystemExit(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8")


def load_material(args: argparse.Namespace) -> str:
    material_parts = []
    if args.material:
        material_parts.append(args.material.strip())
    if args.material_file:
        material_parts.append(Path(args.material_file).read_text(encoding="utf-8-sig").strip())
    material = "\n\n".join(part for part in material_parts if part)
    if args.content_type == "weitoutiao" and not material:
        raise SystemExit("weitoutiao generation requires --material or --material-file.")
    if not args.topic and not material:
        raise SystemExit("Provide at least --topic or --material.")
    return material


def load_topic_history() -> list[dict]:
    return load_json(TOPICS_FILE, [])


def topic_strings(records: list[dict]) -> list[str]:
    result = []
    seen = set()
    for item in records:
        topic = str(item.get("topic", "")).strip()
        if not topic:
            continue
        key = topic.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(topic)
    return result


def build_user_prompt(
    content_type: str,
    topic: str | None,
    material: str,
    previous_topics: list[str],
) -> str:
    sections = [
        f"content_type: {content_type}",
    ]

    if topic:
        sections.append(f"user_topic:\n{topic.strip()}")
    else:
        sections.append("user_topic:\n<none provided; choose a fresh topic>")

    if material:
        sections.append(f"source_material:\n{material}")
    else:
        sections.append("source_material:\n<none provided>")

    previous_text = json.dumps(previous_topics, ensure_ascii=False, indent=2)
    sections.append(
        "historical_topics_already_used:\n"
        f"{previous_text}\n"
        "You must treat this as the full historical topic list and avoid repeating or making near-duplicate topics."
    )

    sections.append(
        "Return only one JSON object with keys topic, title, content, tags, and image_prompts."
    )

    return "\n\n".join(sections)


def strip_code_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def request_model(settings: dict, system_prompt: str, user_prompt: str) -> dict:
    client = OpenAI(
        api_key=settings["model"]["api_key"],
        base_url=settings["model"]["api_url"],
    )
    temperature = settings.get("generation", {}).get("temperature", 0.8)

    try:
        response = client.chat.completions.create(
            model=settings["model"]["model"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            response_format={"type": "json_object"},
        )
    except Exception:
        try:
            response = client.chat.completions.create(
                model=settings["model"]["model"],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
            )
        except APIStatusError as exc:
            detail = exc.response.text if exc.response is not None else str(exc)
            raise SystemExit(f"Model request failed with status error: {detail}") from exc
        except APIError as exc:
            raise SystemExit(f"Model request failed: {exc}") from exc

    text = response.choices[0].message.content or ""
    text = strip_code_fence(text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Model did not return valid JSON: {exc}\nRaw output:\n{text}") from exc

    if not isinstance(data, dict):
        raise SystemExit("Model output must be a JSON object.")
    return data


def save_topic(topic_history: list[dict], topic: str, content_type: str, article_id: str) -> list[dict]:
    clean_topic = topic.strip()
    if not clean_topic:
        return topic_history

    existing_keys = {str(item.get("topic", "")).strip().casefold() for item in topic_history}
    if clean_topic.casefold() in existing_keys:
        return topic_history

    topic_history.append(
        {
            "id": uuid4().hex,
            "topic": clean_topic,
            "content_type": content_type,
            "article_id": article_id,
            "created_at": now_iso(),
        }
    )
    return topic_history


def write_markdown(path: Path, article: dict) -> None:
    title = article.get("title", "").strip()
    lines = [
        f"# {title}" if title else "# Untitled",
        "",
        f"- topic: {article['topic']}",
        f"- content_type: {article['content_type']}",
        f"- created_at: {article['created_at']}",
        "",
        article["content"].strip(),
        "",
    ]
    if article.get("tags"):
        lines.extend(["## Tags", "", ", ".join(article["tags"]), ""])

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    ensure_runtime_dirs()

    settings = load_settings()
    system_prompt = load_prompt(args.content_type)
    material = load_material(args)

    history = load_topic_history()
    previous_topics = topic_strings(history)

    if args.topic and not args.allow_duplicate_topic:
        if args.topic.strip().casefold() in {topic.casefold() for topic in previous_topics}:
            raise SystemExit("The provided topic already exists in topic history. Use a new topic or pass --allow-duplicate-topic.")

    user_prompt = build_user_prompt(args.content_type, args.topic, material, previous_topics)
    raw = request_model(settings, system_prompt, user_prompt)

    raw_topic = str(raw.get("topic") or args.topic or raw.get("title") or "").strip()
    if not raw_topic:
        raise SystemExit("Model output must include a non-empty topic.")

    normalized = normalize_payload(
        {
            "content_type": args.content_type,
            "title": raw.get("title", ""),
            "content": raw.get("content", ""),
            "tags": raw.get("tags", []),
            "image_prompts": raw.get("image_prompts", []),
        },
        args.content_type,
        allow_empty_title=args.content_type == "weitoutiao",
    )

    if not args.allow_duplicate_topic and raw_topic.casefold() in {topic.casefold() for topic in previous_topics}:
        raise SystemExit("The generated topic duplicates an existing topic in history.")

    article_id = uuid4().hex
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"{timestamp}_{args.content_type}_{article_id[:8]}"
    article_json_path = ARTICLES_DIR / f"{base_name}.json"
    article_md_path = ARTICLES_DIR / f"{base_name}.md"

    article_record = {
        "id": article_id,
        "topic": raw_topic,
        "content_type": args.content_type,
        "title": normalized["title"],
        "content": normalized["content"],
        "tags": normalized["tags"],
        "image_prompts": normalized["image_prompts"],
        "material_excerpt": material[:2000],
        "model": settings["model"]["model"],
        "created_at": now_iso(),
    }

    save_json(article_json_path, article_record)
    write_markdown(article_md_path, article_record)

    updated_topics = save_topic(history, raw_topic, args.content_type, article_id)
    save_json(TOPICS_FILE, updated_topics)

    result = {
        "article_id": article_id,
        "topic": raw_topic,
        "content_type": args.content_type,
        "title": article_record["title"],
        "article_json_path": str(article_json_path),
        "article_markdown_path": str(article_md_path),
        "topic_history_path": str(TOPICS_FILE),
        "historical_topic_count": len(topic_strings(updated_topics)),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
