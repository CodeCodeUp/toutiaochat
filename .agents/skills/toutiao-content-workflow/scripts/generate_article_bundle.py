#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import httpx

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
        "--direction",
        help="Optional creative direction, such as 情感共鸣 or 人生感悟.",
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
    env_base_url = os.environ.get("GOOGLE_GEMINI_BASE_URL", "").strip()
    env_api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    env_model = os.environ.get("GEMINI_MODEL", "").strip()

    if env_base_url:
        model["api_url"] = env_base_url
    if env_api_key:
        model["api_key"] = env_api_key
    if env_model:
        model["model"] = env_model

    settings["model"] = model
    if not model.get("api_url") or not model.get("api_key") or not model.get("model"):
        raise SystemExit("local_settings.json must define model.api_url, model.api_key, and model.model.")
    return settings


def load_prompt(content_type: str) -> str:
    name = "article-generate.md"
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
    direction: str | None,
    material: str,
    previous_topics: list[str],
) -> str:
    sections = [
        f"内容类型：{content_type}",
    ]

    if topic:
        sections.append(f"用户指定主题：\n{topic.strip()}")
    else:
        sections.append("用户指定主题：\n<未提供，请自行选择新主题>")

    if direction:
        sections.append(f"创作方向：\n{direction.strip()}")
    else:
        sections.append("创作方向：\n<未指定，请从允许方向中自行选择最合适的一类>")

    if material:
        sections.append(f"原始素材：\n{material}")
    else:
        sections.append("原始素材：\n<未提供>")

    previous_text = json.dumps(previous_topics, ensure_ascii=False, indent=2)
    sections.append(
        "历史已用主题（每次都要全量参考，避免重复创作）：\n"
        f"{previous_text}\n"
        "如果用户提供了主题，必须使用该主题，不得改成其他主题。"
    )

    sections.append(
        "只返回一个 JSON 对象，字段必须包含 topic、title、content、tags、image_prompts。"
    )

    return "\n\n".join(sections)


def compact_text_length(text: str) -> int:
    return len("".join(text.split()))


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
    temperature = settings.get("generation", {}).get("temperature", 0.8)
    api_url = settings["model"]["api_url"].rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings['model']['api_key']}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings["model"]["model"],
        "temperature": temperature,
        "messages": [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
        ],
        "response_format": {"type": "json_object"},
    }
    last_error: str | None = None
    timeout_seconds = 600

    for attempt in range(1, 4):
        try:
            with httpx.Client(timeout=timeout_seconds, trust_env=False) as client:
                response = client.post(
                    api_url,
                    headers=headers,
                    json=payload,
                )
        except Exception as exc:
            last_error = repr(exc)
            if attempt < 3:
                time.sleep(attempt * 2)
                continue

        if response.status_code == 200:
            break

        last_error = response.text
        if response.status_code in {429, 500, 502, 503, 504} and attempt < 3:
            time.sleep(attempt * 2)
            continue
        if response.status_code == 400 and attempt == 1:
            fallback_payload = dict(payload)
            fallback_payload.pop("response_format", None)
            payload = fallback_payload
            time.sleep(1)
            continue
        if response.status_code == 403 and "blocked" in response.text.lower() and attempt < 3:
            simplified_payload = {
                "model": settings["model"]["model"],
                "temperature": max(0.2, min(temperature, 0.7)),
                "messages": [
                    {
                        "role": "system",
                        "content": "你是中文文章生成助手。只返回JSON对象。",
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
                "response_format": {"type": "json_object"},
            }
            payload = simplified_payload
            time.sleep(attempt * 2)
            continue
        if attempt < 3:
                time.sleep(attempt * 2)
                continue
    else:
        raise SystemExit(f"Model request failed: {last_error or 'unknown error'}")

    response_data = response.json()
    choices = response_data.get("choices") or []
    if not choices:
        raise SystemExit(f"Model response missing choices: {response.text[:1000]}")
    text = choices[0].get("message", {}).get("content") or ""
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


def topic_matches_requested(requested_topic: str | None, generated_topic: str) -> bool:
    if not requested_topic:
        return True
    requested = requested_topic.strip().casefold()
    generated = generated_topic.strip().casefold()
    if not requested or not generated:
        return False
    return requested == generated


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

    user_prompt = build_user_prompt(args.content_type, args.topic, args.direction, material, previous_topics)
    raw = None
    raw_topic = ""
    normalized = None
    followup_prompt = user_prompt

    for attempt in range(1, 4):
        raw = request_model(settings, system_prompt, followup_prompt)

        raw_topic = str(raw.get("topic") or args.topic or raw.get("title") or "").strip()
        if not raw_topic:
            if attempt == 3:
                raise SystemExit("Model output must include a non-empty topic.")
            followup_prompt = (
                user_prompt
                + "\n\n上一次返回缺少 topic 字段。请重试，并确保 topic 存在且在用户指定主题场景下与用户主题完全一致。"
            )
            continue

        if not topic_matches_requested(args.topic, raw_topic):
            if attempt == 3:
                raise SystemExit(
                    f"Model ignored the requested topic. Requested: {args.topic} | Generated: {raw_topic}"
                )
            followup_prompt = (
                user_prompt
                + f"\n\n你上一次错误地把主题写成了“{raw_topic}”。这次必须严格使用用户指定主题“{args.topic}”，不得换题。"
            )
            continue

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
        if args.content_type == "weitoutiao":
            content_length = compact_text_length(normalized["content"])
            if not 250 <= content_length <= 350:
                if attempt == 3:
                    raise SystemExit(
                        f"Weitoutiao content length must stay between 250 and 350 characters. Got {content_length}."
                    )
                followup_prompt = (
                    user_prompt
                    + f"\n\n你上一次返回的微头条正文长度为 {content_length} 字，不符合要求。"
                    + " 这一次必须把正文严格控制在 250 到 350 字之间，只返回合法 JSON。"
                )
                normalized = None
                continue
        break

    if normalized is None or raw is None:
        raise SystemExit("Model did not return a valid normalized payload.")

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
        "direction": args.direction or "",
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
