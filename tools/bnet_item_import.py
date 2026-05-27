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
            binding_type TEXT,
            binding_name TEXT,
            description TEXT,
            limit_category TEXT,
            bonus_list_json TEXT,
            stat_signature TEXT,
            spell_ids_json TEXT,
            equip_use_text TEXT,
            required_profession_id INTEGER,
            required_profession_name TEXT,
            required_profession_skill INTEGER,
            required_profession_display TEXT,
            modified_crafting_stat_type TEXT,
            modified_crafting_stat_name TEXT,
            modified_crafting_id INTEGER,
            modified_crafting_category_id INTEGER,
            modified_crafting_category_name TEXT,
            is_crafting_reagent INTEGER,
            expansion TEXT,
            source_endpoint TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            raw_json TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS item_details (
            item_id INTEGER PRIMARY KEY,
            detail_url TEXT NOT NULL,
            fetched_at TEXT DEFAULT CURRENT_TIMESTAMP,
            raw_json TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS item_stats (
            item_id INTEGER NOT NULL,
            stat_type TEXT,
            stat_name TEXT,
            stat_value INTEGER,
            is_equip_bonus INTEGER,
            display_string TEXT,
            PRIMARY KEY (item_id, stat_type)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS item_spells (
            item_id INTEGER NOT NULL,
            spell_id INTEGER NOT NULL,
            spell_name TEXT,
            description TEXT,
            PRIMARY KEY (item_id, spell_id)
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
    ensure_column(conn, "items", "binding_type", "TEXT")
    ensure_column(conn, "items", "binding_name", "TEXT")
    ensure_column(conn, "items", "description", "TEXT")
    ensure_column(conn, "items", "limit_category", "TEXT")
    ensure_column(conn, "items", "bonus_list_json", "TEXT")
    ensure_column(conn, "items", "stat_signature", "TEXT")
    ensure_column(conn, "items", "spell_ids_json", "TEXT")
    ensure_column(conn, "items", "equip_use_text", "TEXT")
    ensure_column(conn, "items", "required_profession_id", "INTEGER")
    ensure_column(conn, "items", "required_profession_name", "TEXT")
    ensure_column(conn, "items", "required_profession_skill", "INTEGER")
    ensure_column(conn, "items", "required_profession_display", "TEXT")
    ensure_column(conn, "items", "modified_crafting_stat_type", "TEXT")
    ensure_column(conn, "items", "modified_crafting_stat_name", "TEXT")
    ensure_column(conn, "items", "modified_crafting_id", "INTEGER")
    ensure_column(conn, "items", "modified_crafting_category_id", "INTEGER")
    ensure_column(conn, "items", "modified_crafting_category_name", "TEXT")
    ensure_column(conn, "items", "is_crafting_reagent", "INTEGER")
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


def optional_text(value: Any) -> str | None:
    return value if isinstance(value, str) else None


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
    modified_crafting = data.get("modified_crafting")
    modified_crafting = modified_crafting if isinstance(modified_crafting, dict) else {}
    modified_category = modified_crafting.get("category")
    modified_category = modified_category if isinstance(modified_category, dict) else {}

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
        "modified_crafting_id": optional_int(modified_crafting.get("id")),
        "modified_crafting_category_id": optional_int(modified_category.get("id")),
        "modified_crafting_category_name": localized_name(
            modified_category.get("name"), locale
        ),
        "raw_json": json.dumps(data, ensure_ascii=False, sort_keys=True),
    }


def detail_preview(data: dict[str, Any]) -> dict[str, Any]:
    preview = data.get("preview_item")
    return preview if isinstance(preview, dict) else {}


def normalize_stats(preview: dict[str, Any]) -> list[dict[str, Any]]:
    stats = preview.get("stats")
    if not isinstance(stats, list):
        return []

    normalized = []
    for stat in stats:
        if not isinstance(stat, dict):
            continue
        stat_type = stat.get("type")
        display = stat.get("display")
        normalized.append(
            {
                "stat_type": stat_type.get("type")
                if isinstance(stat_type, dict)
                else None,
                "stat_name": stat_type.get("name")
                if isinstance(stat_type, dict)
                else None,
                "stat_value": optional_int(stat.get("value")),
                "is_equip_bonus": bool_int(stat.get("is_equip_bonus")),
                "display_string": display.get("display_string")
                if isinstance(display, dict)
                else None,
            }
        )
    return normalized


def normalize_spells(preview: dict[str, Any]) -> list[dict[str, Any]]:
    spells = preview.get("spells")
    if not isinstance(spells, list):
        return []

    normalized = []
    for spell_row in spells:
        if not isinstance(spell_row, dict):
            continue
        spell = spell_row.get("spell")
        if not isinstance(spell, dict) or not isinstance(spell.get("id"), int):
            continue
        normalized.append(
            {
                "spell_id": spell["id"],
                "spell_name": optional_text(spell.get("name")),
                "description": optional_text(spell_row.get("description")),
            }
        )
    return normalized


def stat_signature(stats: list[dict[str, Any]]) -> str | None:
    if not stats:
        return None
    parts = []
    for stat in sorted(stats, key=lambda row: row.get("stat_type") or ""):
        parts.append(f"{stat.get('stat_type')}={stat.get('stat_value')}")
    return "|".join(parts)


def normalize_detail(data: dict[str, Any]) -> dict[str, Any]:
    preview = detail_preview(data)
    requirements = preview.get("requirements")
    requirements = requirements if isinstance(requirements, dict) else {}
    skill = requirements.get("skill")
    skill = skill if isinstance(skill, dict) else {}
    profession = skill.get("profession")
    profession = profession if isinstance(profession, dict) else {}
    binding = preview.get("binding")
    binding = binding if isinstance(binding, dict) else {}
    modified = preview.get("modified_crafting_stat")
    modified = modified if isinstance(modified, dict) else {}
    modified_crafting = data.get("modified_crafting")
    modified_crafting = modified_crafting if isinstance(modified_crafting, dict) else {}
    modified_category = modified_crafting.get("category")
    modified_category = modified_category if isinstance(modified_category, dict) else {}
    stats = normalize_stats(preview)
    spells = normalize_spells(preview)

    return {
        "binding_type": optional_text(binding.get("type")),
        "binding_name": optional_text(binding.get("name")),
        "description": optional_text(data.get("description"))
        or optional_text(preview.get("description")),
        "limit_category": optional_text(preview.get("limit_category")),
        "bonus_list_json": json.dumps(preview.get("bonus_list"), ensure_ascii=False)
        if isinstance(preview.get("bonus_list"), list)
        else None,
        "stat_signature": stat_signature(stats),
        "spell_ids_json": json.dumps(
            [spell["spell_id"] for spell in spells], ensure_ascii=False
        )
        if spells
        else None,
        "equip_use_text": "\n".join(
            spell["description"] for spell in spells if spell.get("description")
        )
        or None,
        "required_profession_id": optional_int(profession.get("id")),
        "required_profession_name": optional_text(profession.get("name")),
        "required_profession_skill": optional_int(skill.get("level")),
        "required_profession_display": optional_text(skill.get("display_string")),
        "modified_crafting_stat_type": optional_text(modified.get("type")),
        "modified_crafting_stat_name": optional_text(modified.get("name")),
        "modified_crafting_id": optional_int(modified_crafting.get("id")),
        "modified_crafting_category_id": optional_int(modified_category.get("id")),
        "modified_crafting_category_name": optional_text(modified_category.get("name")),
        "is_crafting_reagent": 1
        if isinstance(preview.get("crafting_reagent"), str)
        else None,
        "stats": stats,
        "spells": spells,
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
                is_stackable, is_equippable, modified_crafting_id,
                modified_crafting_category_id, modified_crafting_category_name,
                expansion, source_endpoint, updated_at, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
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
                modified_crafting_id = excluded.modified_crafting_id,
                modified_crafting_category_id = excluded.modified_crafting_category_id,
                modified_crafting_category_name = excluded.modified_crafting_category_name,
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
                item["modified_crafting_id"],
                item["modified_crafting_category_id"],
                item["modified_crafting_category_name"],
                expansion,
                endpoint_name,
                item["raw_json"],
            ),
        )
        count += 1
    return count


def upsert_item_detail(
    conn: sqlite3.Connection,
    *,
    item_id: int,
    detail_url: str,
    payload: dict[str, Any],
) -> None:
    detail = normalize_detail(payload)
    conn.execute(
        """
        INSERT INTO item_details (item_id, detail_url, fetched_at, raw_json)
        VALUES (?, ?, CURRENT_TIMESTAMP, ?)
        ON CONFLICT(item_id) DO UPDATE SET
            detail_url = excluded.detail_url,
            fetched_at = CURRENT_TIMESTAMP,
            raw_json = excluded.raw_json
        """,
        (item_id, redact_url(detail_url), json.dumps(payload, ensure_ascii=False)),
    )
    conn.execute(
        """
        UPDATE items SET
            binding_type = ?,
            binding_name = ?,
            description = ?,
            limit_category = ?,
            bonus_list_json = ?,
            stat_signature = ?,
            spell_ids_json = ?,
            equip_use_text = ?,
            required_profession_id = ?,
            required_profession_name = ?,
            required_profession_skill = ?,
            required_profession_display = ?,
            modified_crafting_stat_type = ?,
            modified_crafting_stat_name = ?,
            modified_crafting_id = ?,
            modified_crafting_category_id = ?,
            modified_crafting_category_name = ?,
            is_crafting_reagent = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE item_id = ?
        """,
        (
            detail["binding_type"],
            detail["binding_name"],
            detail["description"],
            detail["limit_category"],
            detail["bonus_list_json"],
            detail["stat_signature"],
            detail["spell_ids_json"],
            detail["equip_use_text"],
            detail["required_profession_id"],
            detail["required_profession_name"],
            detail["required_profession_skill"],
            detail["required_profession_display"],
            detail["modified_crafting_stat_type"],
            detail["modified_crafting_stat_name"],
            detail["modified_crafting_id"],
            detail["modified_crafting_category_id"],
            detail["modified_crafting_category_name"],
            detail["is_crafting_reagent"],
            item_id,
        ),
    )
    conn.execute("DELETE FROM item_stats WHERE item_id = ?", (item_id,))
    conn.executemany(
        """
        INSERT INTO item_stats (
            item_id, stat_type, stat_name, stat_value, is_equip_bonus,
            display_string
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (
                item_id,
                stat["stat_type"],
                stat["stat_name"],
                stat["stat_value"],
                stat["is_equip_bonus"],
                stat["display_string"],
            )
            for stat in detail["stats"]
        ],
    )
    conn.execute("DELETE FROM item_spells WHERE item_id = ?", (item_id,))
    conn.executemany(
        """
        INSERT OR REPLACE INTO item_spells (
            item_id, spell_id, spell_name, description
        )
        VALUES (?, ?, ?, ?)
        """,
        [
            (
                item_id,
                spell["spell_id"],
                spell["spell_name"],
                spell["description"],
            )
            for spell in detail["spells"]
        ],
    )


def fetch_item_detail(
    item_id: int,
    *,
    api_base_url: str,
    region: str,
    locale: str,
    namespace: str,
    token: str,
    auth_mode: str,
) -> tuple[int, str, dict[str, Any]]:
    url = build_url(
        {"path": f"/data/wow/item/{item_id}", "params": {}},
        api_base_url=api_base_url,
        region=region,
        locale=locale,
        namespace=namespace,
        token=token if auth_mode == "query" else None,
    )
    headers = {}
    if auth_mode == "header":
        headers["Authorization"] = f"Bearer {token}"
    return item_id, url, request_json(url, headers=headers)


def enrich_item_details(
    conn: sqlite3.Connection,
    *,
    api_base_url: str,
    region: str,
    locale: str,
    namespace: str,
    token: str,
    auth_mode: str,
    max_workers: int,
) -> int:
    item_ids = [
        row[0]
        for row in conn.execute("SELECT item_id FROM items ORDER BY item_id").fetchall()
    ]
    enriched = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(
                fetch_item_detail,
                item_id,
                api_base_url=api_base_url,
                region=region,
                locale=locale,
                namespace=namespace,
                token=token,
                auth_mode=auth_mode,
            )
            for item_id in item_ids
        ]
        for future in concurrent.futures.as_completed(futures):
            item_id, url, payload = future.result()
            upsert_item_detail(conn, item_id=item_id, detail_url=url, payload=payload)
            enriched += 1
            if enriched % 100 == 0:
                conn.commit()
    conn.commit()
    return enriched


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
    parser.add_argument("--enrich-details", action="store_true")
    parser.add_argument(
        "--details-only",
        action="store_true",
        help="skip endpoint imports and enrich details for existing database rows",
    )
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
    if jsonl_path.exists() and not args.append_jsonl and not args.details_only:
        jsonl_path.unlink()
    token = fetch_token(
        require_env("BN_CLIENT_ID", "BATTLENET_CLIENT_ID"),
        require_env("BN_CLIENT_SECRET", "BATTLENET_CLIENT_SECRET"),
        token_url,
    )

    conn = init_db(database)
    imported_total = 0
    if not args.details_only:
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
    enriched_total = 0
    if args.enrich_details or args.details_only:
        enriched_total = enrich_item_details(
            conn,
            api_base_url=api_base_url,
            region=region,
            locale=locale,
            namespace=namespace,
            token=token,
            auth_mode=auth_mode,
            max_workers=max_workers,
        )

    conn.close()
    print(f"Imported {imported_total} item rows into {database}")
    if enriched_total:
        print(f"Enriched {enriched_total} item detail rows")
    if not args.details_only:
        print(f"Wrote raw payloads to {jsonl_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
