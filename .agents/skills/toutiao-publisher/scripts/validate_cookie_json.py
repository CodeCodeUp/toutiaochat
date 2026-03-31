#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

VALID_SAME_SITE = {"Strict", "Lax", "None"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate and normalize a Toutiao cookie JSON file."
    )
    parser.add_argument("input", help="Path to the cookie JSON file.")
    parser.add_argument(
        "--output",
        help="Write normalized cookies to this path. Defaults to stdout.",
    )
    return parser.parse_args()


def load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise SystemExit(f"Cookie file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc}") from exc


def unwrap_cookies(payload: object) -> list[dict]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict) and isinstance(payload.get("cookies"), list):
        return [item for item in payload["cookies"] if isinstance(item, dict)]
    raise SystemExit("Expected a JSON array of cookies or an object with a cookies array.")


def normalize_cookie(cookie: dict) -> dict | None:
    name = str(cookie.get("name", "")).strip()
    value = str(cookie.get("value", "")).strip()
    if not name or not value:
        return None

    same_site = str(cookie.get("sameSite", "Lax")).strip().capitalize()
    if same_site not in VALID_SAME_SITE:
        same_site = "Lax"

    normalized = {
        "name": name,
        "value": value,
        "domain": str(cookie.get("domain", "")).strip(),
        "path": str(cookie.get("path", "/") or "/").strip() or "/",
        "sameSite": same_site,
    }

    if "secure" in cookie:
        normalized["secure"] = bool(cookie["secure"])
    if "httpOnly" in cookie:
        normalized["httpOnly"] = bool(cookie["httpOnly"])
    if "expires" in cookie and str(cookie["expires"]).strip():
        normalized["expires"] = cookie["expires"]

    return normalized


def write_output(data: list[dict], output_path: str | None) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if output_path:
        Path(output_path).write_text(text + "\n", encoding="utf-8")
        return
    sys.stdout.write(text + "\n")


def main() -> None:
    args = parse_args()
    raw_payload = load_json(Path(args.input))
    cookies = unwrap_cookies(raw_payload)

    normalized = []
    for cookie in cookies:
        item = normalize_cookie(cookie)
        if item is not None:
            normalized.append(item)

    if not normalized:
        raise SystemExit("No valid cookies found.")

    write_output(normalized, args.output)


if __name__ == "__main__":
    main()
