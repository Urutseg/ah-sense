#!/usr/bin/env python3
"""Import Battle.net item API payloads into a local research SQLite database."""

from __future__ import annotations

import argparse
import base64
import concurrent.futures
import json
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV = ROOT / ".env"


def load_env(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def env_first(*names: str, default: str | None = None) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return default


def require_env(*names: str) -> str:
    value = env_first(*names)
    if value:
        return value
    joined = " or ".join(names)
    raise SystemExit(f"Missing required environment value: {joined}")


def redact_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    redacted = [
        (key, "<redacted>" if key.lower() == "access_token" else value)
        for key, value in query
    ]
    return urllib.parse.urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            urllib.parse.urlencode(redacted, doseq=True),
            parsed.fragment,
        )
    )


def request_json(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    data: bytes | None = None,
    retries: int = 3,
) -> dict[str, Any]:
    for attempt in range(1, retries + 1):
        request = urllib.request.Request(url, headers=headers or {}, data=data)
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            retry_after = exc.headers.get("Retry-After")
            if exc.code == 429 and attempt < retries:
                time.sleep(float(retry_after or attempt * 2))
                continue
            body = exc.read().decode("utf-8", errors="replace")
            raise SystemExit(f"HTTP {exc.code} for {redact_url(url)}\n{body}") from exc
        except urllib.error.URLError as exc:
            if attempt < retries:
                time.sleep(attempt * 2)
                continue
            raise SystemExit(f"Request failed for {redact_url(url)}: {exc}") from exc

    raise SystemExit(f"Request failed for {redact_url(url)}")


def env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if not value:
        return default
    try:
        return max(1, int(value))
    except ValueError:
        raise SystemExit(f"{name} must be an integer")


def fetch_token(client_id: str, client_secret: str, token_url: str) -> str:
    token = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode(
        "ascii"
    )
    payload = urllib.parse.urlencode({"grant_type": "client_credentials"}).encode(
        "ascii"
    )
    response = request_json(
        token_url,
        headers={
            "Authorization": f"Basic {token}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data=payload,
    )
    access_token = response.get("access_token")
    if not access_token:
        raise SystemExit("Battle.net token response did not include access_token")
    return access_token


def build_url(
    endpoint: dict[str, Any],
    *,
    api_base_url: str,
    region: str,
    locale: str,
    namespace: str,
    token: str | None = None,
    page: int | None = None,
) -> str:
    path = endpoint["path"]
    if path.startswith("http://") or path.startswith("https://"):
        base = path
    else:
        base = f"{api_base_url.rstrip('/')}{path}"

    params = dict(endpoint.get("params", {}))
    params.setdefault("namespace", namespace)
    params.setdefault("locale", locale)
    if token:
        params["access_token"] = token

    if page is not None:
        params["_page"] = page
        params.setdefault("_pageSize", endpoint.get("page_size", 1000))

    separator = "&" if "?" in base else "?"
    return base + separator + urllib.parse.urlencode(params, doseq=True)


def init_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS items (
            item_id INTEGER PRIMARY KEY,
            name TEXT,
            item_class_id INTEGER,
            item_class_name TEXT,
            item_subclass_id INTEGER,
            item_subclass_name TEXT,
            inventory_type_id INTEGER,
            inventory_type_name TEXT,
            quality_type TEXT,
            level INTEGER,
            required_level INTEGER,
            purchase_price INTEGER,
            sell_price INTEGER,
            is_stackable INTEGER,
            is_equippable INTEGER,
            expansion TEXT,
            source_endpoint TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            raw_json TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS imports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            endpoint_name TEXT NOT NULL,
            url TEXT NOT NULL,
            imported_at TEXT DEFAULT CURRENT_TIMESTAMP,
            result_count INTEGER NOT NULL,
            raw_json TEXT NOT NULL
        )
        """
    )
    ensure_column(conn, "items", "item_class_name", "TEXT")
    ensure_column(conn, "items", "item_subclass_name", "TEXT")
    ensure_column(conn, "items", "inventory_type_name", "TEXT")
    ensure_column(conn, "items", "purchase_price", "INTEGER")
    ensure_column(conn, "items", "sell_price", "INTEGER")
    ensure_column(conn, "items", "is_stackable", "INTEGER")
    ensure_column(conn, "items", "is_equippable", "INTEGER")
    return conn


def ensure_column(
    conn: sqlite3.Connection, table_name: str, column_name: str, column_type: str
) -> None:
    columns = {
        row[1] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    if column_name not in columns:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")


def localized_name(value: Any, locale: str) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return value.get(locale) or value.get("en_US") or next(iter(value.values()), None)
    return None


def nested_id(data: dict[str, Any], *keys: str) -> int | None:
    value: Any = data
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value if isinstance(value, int) else None


def nested_name(data: dict[str, Any], locale: str, *keys: str) -> str | None:
    value: Any = data
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    if isinstance(value, dict):
        return localized_name(value.get("name"), locale)
    return None


def bool_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return 1 if value else 0
    return None


def optional_int(value: Any) -> int | None:
    return value if isinstance(value, int) else None


def normalize_item(result: dict[str, Any], locale: str) -> dict[str, Any] | None:
    data = result.get("data") if "data" in result else result
    if not isinstance(data, dict):
        return None

    item_id = data.get("id")
    if not isinstance(item_id, int):
        return None

    quality = data.get("quality")
    if isinstance(quality, dict):
        quality_type = quality.get("type") or quality.get("name")
    else:
        quality_type = None

    return {
        "item_id": item_id,
        "name": localized_name(data.get("name"), locale),
        "item_class_id": nested_id(data, "item_class", "id"),
        "item_class_name": nested_name(data, locale, "item_class"),
        "item_subclass_id": nested_id(data, "item_subclass", "id"),
        "item_subclass_name": nested_name(data, locale, "item_subclass"),
        "inventory_type_id": nested_id(data, "inventory_type", "id"),
        "inventory_type_name": nested_name(data, locale, "inventory_type"),
        "quality_type": quality_type,
        "level": optional_int(data.get("level")),
        "required_level": optional_int(data.get("required_level")),
        "purchase_price": optional_int(data.get("purchase_price")),
        "sell_price": optional_int(data.get("sell_price")),
        "is_stackable": bool_int(data.get("is_stackable")),
        "is_equippable": bool_int(data.get("is_equippable")),
        "raw_json": json.dumps(data, ensure_ascii=False, sort_keys=True),
    }


def extract_results(payload: dict[str, Any]) -> list[dict[str, Any]]:
    results = payload.get("results")
    if isinstance(results, list):
        return [item for item in results if isinstance(item, dict)]
    return [payload]


def upsert_items(
    conn: sqlite3.Connection,
    *,
    endpoint_name: str,
    expansion: str,
    locale: str,
    payload: dict[str, Any],
) -> int:
    count = 0
    for result in extract_results(payload):
        item = normalize_item(result, locale)
        if not item:
            continue

        conn.execute(
            """
            INSERT INTO items (
                item_id, name, item_class_id, item_class_name, item_subclass_id,
                item_subclass_name, inventory_type_id, inventory_type_name,
                quality_type, level, required_level, purchase_price, sell_price,
                is_stackable, is_equippable, expansion, source_endpoint, updated_at,
                raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
            ON CONFLICT(item_id) DO UPDATE SET
                name = excluded.name,
                item_class_id = excluded.item_class_id,
                item_class_name = excluded.item_class_name,
                item_subclass_id = excluded.item_subclass_id,
                item_subclass_name = excluded.item_subclass_name,
                inventory_type_id = excluded.inventory_type_id,
                inventory_type_name = excluded.inventory_type_name,
                quality_type = excluded.quality_type,
                level = excluded.level,
                required_level = excluded.required_level,
                purchase_price = excluded.purchase_price,
                sell_price = excluded.sell_price,
                is_stackable = excluded.is_stackable,
                is_equippable = excluded.is_equippable,
                expansion = excluded.expansion,
                source_endpoint = excluded.source_endpoint,
                updated_at = CURRENT_TIMESTAMP,
                raw_json = excluded.raw_json
            """,
            (
                item["item_id"],
                item["name"],
                item["item_class_id"],
                item["item_class_name"],
                item["item_subclass_id"],
                item["item_subclass_name"],
                item["inventory_type_id"],
                item["inventory_type_name"],
                item["quality_type"],
                item["level"],
                item["required_level"],
                item["purchase_price"],
                item["sell_price"],
                item["is_stackable"],
                item["is_equippable"],
                expansion,
                endpoint_name,
                item["raw_json"],
            ),
        )
        count += 1
    return count


def page_count(payload: dict[str, Any]) -> int | None:
    for key in ("pageCount", "page_count"):
        value = payload.get(key)
        if isinstance(value, int):
            return value
    return None


def expand_range_endpoint(endpoint: dict[str, Any]) -> list[dict[str, Any]]:
    range_config = endpoint.get("range")
    if not isinstance(range_config, dict):
        return [endpoint]

    field = range_config.get("field")
    start = range_config.get("start")
    end = range_config.get("end")
    step = range_config.get("step", 1000)
    if not isinstance(field, str) or not all(
        isinstance(value, int) for value in (start, end, step)
    ):
        raise SystemExit(f"Invalid range config for endpoint {endpoint.get('name')}")
    if step <= 0 or start > end:
        raise SystemExit(f"Invalid range bounds for endpoint {endpoint.get('name')}")

    expanded = []
    for lower in range(start, end + 1, step):
        upper = min(lower + step - 1, end)
        ranged = dict(endpoint)
        ranged.pop("range", None)
        ranged["params"] = dict(endpoint.get("params", {}))
        ranged["params"][field] = f"[{lower},{upper}]"
        ranged["name"] = f"{endpoint['name']}-{lower}-{upper}"
        expanded.append(ranged)
    return expanded


def import_endpoint(
    conn: sqlite3.Connection,
    jsonl_path: Path,
    endpoint: dict[str, Any],
    *,
    api_base_url: str,
    region: str,
    locale: str,
    namespace: str,
    token: str,
    auth_mode: str,
    expansion: str,
    max_workers: int,
) -> int:
    endpoint_name = endpoint["name"]
    is_paginated = endpoint.get("paginate", True)
    total = 0

    def fetch_page(page: int | None) -> tuple[int | None, str, dict[str, Any]]:
        url = build_url(
            endpoint,
            api_base_url=api_base_url,
            region=region,
            locale=locale,
            namespace=namespace,
            token=token if auth_mode == "query" else None,
            page=page,
        )
        headers = {}
        if auth_mode == "header":
            headers["Authorization"] = f"Bearer {token}"
        return page, url, request_json(url, headers=headers)

    def persist_payload(page: int | None, url: str, payload: dict[str, Any]) -> int:
        imported = upsert_items(
            conn,
            endpoint_name=endpoint_name,
            expansion=expansion,
            locale=locale,
            payload=payload,
        )
        conn.execute(
            """
            INSERT INTO imports (endpoint_name, url, result_count, raw_json)
            VALUES (?, ?, ?, ?)
            """,
            (
                endpoint_name,
                redact_url(url),
                imported,
                json.dumps(payload, ensure_ascii=False),
            ),
        )
        with jsonl_path.open("a", encoding="utf-8") as jsonl:
            jsonl.write(
                json.dumps(
                    {
                        "endpoint": endpoint_name,
                        "page": page,
                        "result_count": imported,
                        "payload": payload,
                    },
                    ensure_ascii=False,
                )
                + "\n"
        )

        conn.commit()
        return imported

    first_page = 1 if is_paginated else None
    page, url, payload = fetch_page(first_page)
    total += persist_payload(page, url, payload)

    if not is_paginated:
        return total

    pages = page_count(payload)
    if not pages or first_page is None or pages <= first_page:
        return total

    remaining_pages = range(first_page + 1, pages + 1)
    workers = min(max_workers, len(remaining_pages))
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(fetch_page, page_number) for page_number in remaining_pages]
        for future in concurrent.futures.as_completed(futures):
            page, url, payload = future.result()
            total += persist_payload(page, url, payload)

    return total


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoints", required=True, type=Path)
    parser.add_argument("--env", default=DEFAULT_ENV, type=Path)
    parser.add_argument("--database", type=Path)
    parser.add_argument("--jsonl", type=Path)
    parser.add_argument("--append-jsonl", action="store_true")
    parser.add_argument("--max-workers", type=int)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_env(args.env)

    endpoint_config = json.loads(args.endpoints.read_text(encoding="utf-8"))
    region = env_first("BN_REGION", "BATTLENET_REGION", default="us")
    locale = env_first("BN_LOCALE", "BATTLENET_LOCALE", default="en_US")
    namespace = env_first("BN_NAMESPACE", "BATTLENET_NAMESPACE", default=f"static-{region}")
    api_base_url = env_first(
        "BN_API_BASE_URL",
        "BATTLENET_API_BASE_URL",
        default=f"https://{region}.api.blizzard.com",
    )
    auth_mode = env_first("BN_AUTH_MODE", "BATTLENET_AUTH_MODE", default="header")
    if auth_mode not in {"header", "query"}:
        raise SystemExit("BN_AUTH_MODE must be header or query")
    token_url = env_first(
        "BN_TOKEN_URL",
        "BATTLENET_TOKEN_URL",
        default="https://oauth.battle.net/token",
    )
    output_dir = ROOT / env_first("BN_OUTPUT_DIR", default="research/item-db")
    expansion = endpoint_config.get("expansion", "midnight")
    max_workers = max(1, args.max_workers or env_int("BN_MAX_WORKERS", 8))

    database = args.database or output_dir / endpoint_config.get(
        "database", f"{expansion}-items.sqlite"
    )
    jsonl_path = args.jsonl or output_dir / endpoint_config.get(
        "jsonl", f"{expansion}-items.raw.jsonl"
    )
    if jsonl_path.exists() and not args.append_jsonl:
        jsonl_path.unlink()
    token = fetch_token(
        require_env("BN_CLIENT_ID", "BATTLENET_CLIENT_ID"),
        require_env("BN_CLIENT_SECRET", "BATTLENET_CLIENT_SECRET"),
        token_url,
    )

    conn = init_db(database)
    imported_total = 0
    for endpoint in endpoint_config.get("endpoints", []):
        for expanded_endpoint in expand_range_endpoint(endpoint):
            imported_total += import_endpoint(
                conn,
                jsonl_path,
                expanded_endpoint,
                api_base_url=api_base_url,
                region=region,
                locale=locale,
                namespace=namespace,
                token=token,
                auth_mode=auth_mode,
                expansion=expansion,
                max_workers=max_workers,
            )

    conn.close()
    print(f"Imported {imported_total} item rows into {database}")
    print(f"Wrote raw payloads to {jsonl_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
