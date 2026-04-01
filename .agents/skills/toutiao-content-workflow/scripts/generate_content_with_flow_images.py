#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
RUNTIME_DIR = SKILL_DIR / "runtime"
ARTICLES_DIR = RUNTIME_DIR / "articles"
FLOW_OUTPUT_ROOT = RUNTIME_DIR / "flow-images"
GENERATE_SCRIPT = SCRIPT_DIR / "generate_article_bundle.py"
FLOW_SCRIPT = SCRIPT_DIR / "flow-playwright" / "generate_flow_images.js"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate Toutiao content, run Google Flow image generation, and backfill image paths."
    )
    parser.add_argument(
        "--content-type",
        choices=["article", "weitoutiao"],
        default="article",
        help="Content type to generate.",
    )
    parser.add_argument("--topic", help="Optional user-specified topic.")
    parser.add_argument("--direction", help="Optional creative direction.")
    parser.add_argument("--material", help="Inline source material.")
    parser.add_argument("--material-file", help="Path to source material file.")
    parser.add_argument(
        "--allow-duplicate-topic",
        action="store_true",
        help="Allow a user-specified topic even if it already exists in local topic history.",
    )
    parser.add_argument(
        "--all-image-prompts",
        action="store_true",
        help="Generate images for every image prompt instead of only the first one.",
    )
    parser.add_argument(
        "--flow-timeout-seconds",
        type=int,
        default=600,
        help="Timeout for each Google Flow generation run.",
    )
    parser.add_argument(
        "--flow-expected-count",
        type=int,
        default=1,
        help="Minimum number of images expected from each Google Flow run.",
    )
    return parser.parse_args()


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_json(path: Path, payload) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_markdown(path: Path, article: dict) -> None:
    title = str(article.get("title", "")).strip()
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

    tags = article.get("tags") or []
    if tags:
        lines.extend(["## Tags", "", ", ".join(tags), ""])

    image_prompts = article.get("image_prompts") or []
    if image_prompts:
        lines.extend(["## Image Prompts", ""])
        for index, item in enumerate(image_prompts, start=1):
            description = str(item.get("description", "")).strip()
            position = str(item.get("position", "")).strip()
            lines.append(f"{index}. [{position}] {description}")

            generated = item.get("generated_images") or []
            for generated_item in generated:
                file_path = str(generated_item.get("file_path", "")).strip()
                if file_path:
                    lines.append(f"   - {file_path}")
        lines.append("")

    generated_images = article.get("generated_image_paths") or []
    if generated_images:
        lines.extend(["## Generated Images", ""])
        for file_path in generated_images:
            lines.append(f"- {file_path}")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def parse_json_from_text(text: str) -> dict:
    text = text.strip()
    if not text:
        raise SystemExit("Command returned empty output.")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Failed to parse JSON output:\n{text}") from exc


def run_generate_command(args: argparse.Namespace) -> dict:
    command = [
        sys.executable,
        str(GENERATE_SCRIPT),
        "--content-type",
        args.content_type,
    ]
    if args.topic:
        command.extend(["--topic", args.topic])
    if args.direction:
        command.extend(["--direction", args.direction])
    if args.material:
        command.extend(["--material", args.material])
    if args.material_file:
        command.extend(["--material-file", args.material_file])
    if args.allow_duplicate_topic:
        command.append("--allow-duplicate-topic")

    completed = subprocess.run(
        command,
        cwd=str(SCRIPT_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit(completed.stderr.strip() or completed.stdout.strip() or "Article generation failed.")
    return parse_json_from_text(completed.stdout)


def run_flow_command(prompt: str, output_dir: Path, timeout_seconds: int, expected_count: int) -> dict:
    command = [
        "node",
        str(FLOW_SCRIPT),
        "--prompt",
        prompt,
        "--timeout-seconds",
        str(timeout_seconds),
        "--expected-count",
        str(expected_count),
        "--output-dir",
        str(output_dir),
    ]
    completed = subprocess.run(
        command,
        cwd=str(SKILL_DIR.parent.parent.parent),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit(completed.stderr.strip() or completed.stdout.strip() or "Google Flow generation failed.")

    result_json_path: Path | None = None
    run_dir: Path | None = None
    for raw_line in completed.stdout.splitlines():
        line = raw_line.strip()
        if line.startswith("RESULT_JSON="):
            result_json_path = Path(line.split("=", 1)[1].strip())
        elif line.startswith("RUN_DIR="):
            run_dir = Path(line.split("=", 1)[1].strip())

    if result_json_path is None or not result_json_path.exists():
        raise SystemExit(f"Google Flow did not report a result.json path.\n{completed.stdout}")

    payload = load_json(result_json_path)
    payload["_result_json_path"] = str(result_json_path)
    payload["_run_dir"] = str(run_dir or result_json_path.parent)
    return payload


def choose_prompt_indexes(article: dict, all_image_prompts: bool) -> list[int]:
    prompts = article.get("image_prompts") or []
    indexes = [index for index, item in enumerate(prompts) if str(item.get("description", "")).strip()]
    if not indexes:
        return []
    if all_image_prompts:
        return indexes
    return [indexes[0]]


def slug_fragment(text: str) -> str:
    buffer: list[str] = []
    for char in text.lower():
        if char.isascii() and char.isalnum():
            buffer.append(char)
        elif buffer and buffer[-1] != "_":
            buffer.append("_")
    slug = "".join(buffer).strip("_")
    return slug[:40] or "image_prompt"


def attach_flow_results(article: dict, flow_runs: list[dict]) -> None:
    flattened_paths: list[str] = []
    for run in flow_runs:
        prompt_index = run["prompt_index"]
        target = article["image_prompts"][prompt_index]
        generated_items = []
        for item in run["saved_files"]:
            file_path = str(item.get("filePath") or item.get("file_path") or "").strip()
            if file_path:
                flattened_paths.append(file_path)
            generated_items.append(
                {
                    "file_path": file_path,
                    "file_name": str(item.get("fileName") or item.get("file_name") or "").strip(),
                    "media_name": str(item.get("mediaName") or item.get("media_name") or "").strip(),
                    "content_type": str(item.get("contentType") or item.get("content_type") or "").strip(),
                    "size_bytes": int(item.get("sizeBytes") or item.get("size_bytes") or 0),
                }
            )

        target["generated_images"] = generated_items
        target["flow_run_dir"] = run["run_dir"]
        target["flow_result_json_path"] = run["result_json_path"]
        target["generated_at"] = now_iso()

    article["generated_image_paths"] = flattened_paths
    article["image_generation"] = {
        "provider": "google-flow",
        "generated_at": now_iso(),
        "runs": flow_runs,
    }


def build_result_payload(article_path: Path, markdown_path: Path, article: dict) -> dict:
    flow_runs = article.get("image_generation", {}).get("runs", [])
    return {
        "article_json_path": str(article_path),
        "article_markdown_path": str(markdown_path),
        "topic": article.get("topic", ""),
        "title": article.get("title", ""),
        "content_type": article.get("content_type", ""),
        "generated_image_paths": article.get("generated_image_paths", []),
        "image_generation_runs": len(flow_runs),
    }


def main() -> None:
    args = parse_args()
    article_result = run_generate_command(args)

    article_path = Path(article_result["article_json_path"])
    markdown_path = Path(article_result["article_markdown_path"])
    article = load_json(article_path)

    prompt_indexes = choose_prompt_indexes(article, args.all_image_prompts)
    if not prompt_indexes:
        article["image_generation"] = {
            "provider": "google-flow",
            "generated_at": now_iso(),
            "runs": [],
            "status": "skipped_no_image_prompt",
        }
        save_json(article_path, article)
        write_markdown(markdown_path, article)
        print(json.dumps(build_result_payload(article_path, markdown_path, article), ensure_ascii=False, indent=2))
        return

    flow_runs: list[dict] = []
    article_slug = article_path.stem
    article_flow_root = FLOW_OUTPUT_ROOT / article_slug
    article_flow_root.mkdir(parents=True, exist_ok=True)

    for prompt_index in prompt_indexes:
        prompt_item = article["image_prompts"][prompt_index]
        prompt_text = str(prompt_item.get("description", "")).strip()
        position = str(prompt_item.get("position", "")).strip() or f"prompt_{prompt_index + 1}"
        prompt_output_root = article_flow_root / f"{prompt_index + 1:02d}_{slug_fragment(position)}"

        flow_result = run_flow_command(
            prompt_text,
            prompt_output_root,
            args.flow_timeout_seconds,
            args.flow_expected_count,
        )
        flow_runs.append(
            {
                "prompt_index": prompt_index,
                "position": position,
                "prompt": prompt_text,
                "run_dir": flow_result["_run_dir"],
                "result_json_path": flow_result["_result_json_path"],
                "saved_files": flow_result.get("savedFiles", []),
                "new_media_names": flow_result.get("newMediaNames", []),
            }
        )

    attach_flow_results(article, flow_runs)
    save_json(article_path, article)
    write_markdown(markdown_path, article)

    print(json.dumps(build_result_payload(article_path, markdown_path, article), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
