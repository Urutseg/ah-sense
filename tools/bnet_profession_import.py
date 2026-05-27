#!/usr/bin/env python3
"""Import Battle.net profession recipe data into the local research database."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import sqlite3
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from bnet_item_import import (
    DEFAULT_ENV,
    env_first,
    env_int,
    fetch_item_detail,
    fetch_token,
    init_db,
    load_env,
    normalize_item,
    redact_url,
    request_json,
    require_env,
    upsert_item_detail,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "research" / "item-db" / "midnight-research.sqlite"
DEFAULT_JSONL = ROOT / "research" / "item-db" / "midnight-professions.raw.jsonl"
MIDNIGHT_TIER_PATTERN = "Midnight"


def request_bnet(
    path: str,
    *,
    api_base_url: str,
    namespace: str,
    locale: str,
    token: str,
    auth_mode: str,
) -> tuple[str, dict[str, Any]]:
    params = {"namespace": namespace, "locale": locale}
    if auth_mode == "query":
        params["access_token"] = token
    url = f"{api_base_url.rstrip('/')}{path}?{urllib.parse.urlencode(params)}"
    headers = {"Authorization": f"Bearer {token}"} if auth_mode == "header" else {}
    return url, request_json(url, headers=headers)


def ensure_profession_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS professions (
            profession_id INTEGER PRIMARY KEY,
            name TEXT,
            type TEXT,
            description TEXT,
            raw_json TEXT NOT NULL,
            fetched_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS profession_skill_tiers (
            profession_id INTEGER NOT NULL,
            skill_tier_id INTEGER NOT NULL,
            name TEXT,
            minimum_skill_level INTEGER,
            maximum_skill_level INTEGER,
            raw_json TEXT NOT NULL,
            fetched_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (profession_id, skill_tier_id)
        );

        CREATE TABLE IF NOT EXISTS profession_recipe_categories (
            profession_id INTEGER NOT NULL,
            skill_tier_id INTEGER NOT NULL,
            category_name TEXT NOT NULL,
            display_order INTEGER NOT NULL,
            PRIMARY KEY (profession_id, skill_tier_id, category_name)
        );

        CREATE TABLE IF NOT EXISTS recipes (
            recipe_id INTEGER PRIMARY KEY,
            profession_id INTEGER,
            skill_tier_id INTEGER,
            category_name TEXT,
            name TEXT,
            description TEXT,
            crafted_item_id INTEGER,
            raw_json TEXT NOT NULL,
            fetched_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS recipe_reagents (
            recipe_id INTEGER NOT NULL,
            reagent_item_id INTEGER NOT NULL,
            reagent_name TEXT,
            quantity INTEGER,
            PRIMARY KEY (recipe_id, reagent_item_id)
        );

        CREATE TABLE IF NOT EXISTS recipe_modified_crafting_slots (
            recipe_id INTEGER NOT NULL,
            slot_type_id INTEGER NOT NULL,
            slot_type_name TEXT,
            display_order INTEGER,
            PRIMARY KEY (recipe_id, slot_type_id)
        );

        CREATE TABLE IF NOT EXISTS modified_crafting_categories (
            category_id INTEGER PRIMARY KEY,
            name TEXT,
            raw_json TEXT NOT NULL,
            fetched_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS modified_crafting_slot_types (
            slot_type_id INTEGER PRIMARY KEY,
            name TEXT,
            description TEXT,
            raw_json TEXT NOT NULL,
            fetched_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS modified_crafting_slot_type_categories (
            slot_type_id INTEGER NOT NULL,
            category_id INTEGER NOT NULL,
            category_name TEXT,
            PRIMARY KEY (slot_type_id, category_id)
        );
        """
    )


def write_jsonl(path: Path, endpoint: str, url: str, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {"endpoint": endpoint, "url": redact_url(url), "payload": payload},
                ensure_ascii=False,
            )
            + "\n"
        )


def ref_id(value: dict[str, Any], key: str = "id") -> int | None:
    candidate = value.get(key)
    return candidate if isinstance(candidate, int) else None


def ref_name(value: dict[str, Any], key: str = "name") -> str | None:
    candidate = value.get(key)
    return candidate if isinstance(candidate, str) else None


def upsert_profession(conn: sqlite3.Connection, payload: dict[str, Any]) -> None:
    profession_type = payload.get("type")
    conn.execute(
        """
        INSERT INTO professions (
            profession_id, name, type, description, raw_json, fetched_at
        ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(profession_id) DO UPDATE SET
            name = excluded.name,
            type = excluded.type,
            description = excluded.description,
            raw_json = excluded.raw_json,
            fetched_at = CURRENT_TIMESTAMP
        """,
        (
            payload["id"],
            payload.get("name"),
            profession_type.get("type") if isinstance(profession_type, dict) else None,
            payload.get("description"),
            json.dumps(payload, ensure_ascii=False),
        ),
    )


def upsert_skill_tier(
    conn: sqlite3.Connection,
    *,
    profession_id: int,
    payload: dict[str, Any],
) -> None:
    conn.execute(
        """
        INSERT INTO profession_skill_tiers (
            profession_id, skill_tier_id, name, minimum_skill_level,
            maximum_skill_level, raw_json, fetched_at
        ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(profession_id, skill_tier_id) DO UPDATE SET
            name = excluded.name,
            minimum_skill_level = excluded.minimum_skill_level,
            maximum_skill_level = excluded.maximum_skill_level,
            raw_json = excluded.raw_json,
            fetched_at = CURRENT_TIMESTAMP
        """,
        (
            profession_id,
            payload["id"],
            payload.get("name"),
            payload.get("minimum_skill_level"),
            payload.get("maximum_skill_level"),
            json.dumps(payload, ensure_ascii=False),
        ),
    )


def recipe_ids_from_tier(
    conn: sqlite3.Connection,
    *,
    profession_id: int,
    skill_tier_id: int,
    payload: dict[str, Any],
) -> list[tuple[int, str | None, str | None]]:
    recipes: list[tuple[int, str | None, str | None]] = []
    conn.execute(
        """
        DELETE FROM profession_recipe_categories
        WHERE profession_id = ? AND skill_tier_id = ?
        """,
        (profession_id, skill_tier_id),
    )
    for index, category in enumerate(payload.get("categories") or []):
        if not isinstance(category, dict):
            continue
        category_name = category.get("name") or ""
        conn.execute(
            """
            INSERT OR REPLACE INTO profession_recipe_categories (
                profession_id, skill_tier_id, category_name, display_order
            ) VALUES (?, ?, ?, ?)
            """,
            (profession_id, skill_tier_id, category_name, index),
        )
        for recipe in category.get("recipes") or []:
            if isinstance(recipe, dict) and isinstance(recipe.get("id"), int):
                recipes.append((recipe["id"], recipe.get("name"), category_name))
    return recipes


def upsert_recipe(
    conn: sqlite3.Connection,
    *,
    profession_id: int,
    skill_tier_id: int,
    category_name: str | None,
    payload: dict[str, Any],
) -> list[int]:
    crafted_item = payload.get("crafted_item")
    crafted_item_id = ref_id(crafted_item) if isinstance(crafted_item, dict) else None
    recipe_id = payload["id"]
    conn.execute(
        """
        INSERT INTO recipes (
            recipe_id, profession_id, skill_tier_id, category_name, name,
            description, crafted_item_id, raw_json, fetched_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(recipe_id) DO UPDATE SET
            profession_id = excluded.profession_id,
            skill_tier_id = excluded.skill_tier_id,
            category_name = excluded.category_name,
            name = excluded.name,
            description = excluded.description,
            crafted_item_id = excluded.crafted_item_id,
            raw_json = excluded.raw_json,
            fetched_at = CURRENT_TIMESTAMP
        """,
        (
            recipe_id,
            profession_id,
            skill_tier_id,
            category_name,
            payload.get("name"),
            payload.get("description"),
            crafted_item_id,
            json.dumps(payload, ensure_ascii=False),
        ),
    )

    conn.execute("DELETE FROM recipe_reagents WHERE recipe_id = ?", (recipe_id,))
    reagent_item_ids = []
    for row in payload.get("reagents") or []:
        if not isinstance(row, dict):
            continue
        reagent = row.get("reagent")
        if not isinstance(reagent, dict) or not isinstance(reagent.get("id"), int):
            continue
        reagent_item_ids.append(reagent["id"])
        conn.execute(
            """
            INSERT OR REPLACE INTO recipe_reagents (
                recipe_id, reagent_item_id, reagent_name, quantity
            ) VALUES (?, ?, ?, ?)
            """,
            (recipe_id, reagent["id"], reagent.get("name"), row.get("quantity")),
        )

    conn.execute(
        "DELETE FROM recipe_modified_crafting_slots WHERE recipe_id = ?",
        (recipe_id,),
    )
    for row in payload.get("modified_crafting_slots") or []:
        if not isinstance(row, dict):
            continue
        slot = row.get("slot_type")
        if not isinstance(slot, dict) or not isinstance(slot.get("id"), int):
            continue
        conn.execute(
            """
            INSERT OR REPLACE INTO recipe_modified_crafting_slots (
                recipe_id, slot_type_id, slot_type_name, display_order
            ) VALUES (?, ?, ?, ?)
            """,
            (recipe_id, slot["id"], slot.get("name"), row.get("display_order")),
        )
    return reagent_item_ids


def upsert_modified_crafting_category(
    conn: sqlite3.Connection, payload: dict[str, Any]
) -> None:
    conn.execute(
        """
        INSERT INTO modified_crafting_categories (
            category_id, name, raw_json, fetched_at
        ) VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(category_id) DO UPDATE SET
            name = excluded.name,
            raw_json = excluded.raw_json,
            fetched_at = CURRENT_TIMESTAMP
        """,
        (payload["id"], payload.get("name"), json.dumps(payload, ensure_ascii=False)),
    )


def upsert_modified_crafting_slot_type(
    conn: sqlite3.Connection, payload: dict[str, Any]
) -> None:
    conn.execute(
        """
        INSERT INTO modified_crafting_slot_types (
            slot_type_id, name, description, raw_json, fetched_at
        ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(slot_type_id) DO UPDATE SET
            name = excluded.name,
            description = excluded.description,
            raw_json = excluded.raw_json,
            fetched_at = CURRENT_TIMESTAMP
        """,
        (
            payload["id"],
            payload.get("name"),
            payload.get("description"),
            json.dumps(payload, ensure_ascii=False),
        ),
    )
    conn.execute(
        "DELETE FROM modified_crafting_slot_type_categories WHERE slot_type_id = ?",
        (payload["id"],),
    )
    for category in payload.get("compatible_categories") or []:
        if not isinstance(category, dict) or not isinstance(category.get("id"), int):
            continue
        conn.execute(
            """
            INSERT OR REPLACE INTO modified_crafting_slot_type_categories (
                slot_type_id, category_id, category_name
            ) VALUES (?, ?, ?)
            """,
            (payload["id"], category["id"], category.get("name")),
        )


def import_modified_crafting(
    conn: sqlite3.Connection,
    *,
    jsonl_path: Path,
    api_base_url: str,
    namespace: str,
    locale: str,
    token: str,
    auth_mode: str,
) -> tuple[int, int]:
    _, category_index = request_bnet(
        "/data/wow/modified-crafting/category/index",
        api_base_url=api_base_url,
        namespace=namespace,
        locale=locale,
        token=token,
        auth_mode=auth_mode,
    )
    categories = [
        category["id"]
        for category in category_index.get("categories") or []
        if isinstance(category, dict) and isinstance(category.get("id"), int)
    ]
    category_count = 0
    for category_id in categories:
        url, payload = request_bnet(
            f"/data/wow/modified-crafting/category/{category_id}",
            api_base_url=api_base_url,
            namespace=namespace,
            locale=locale,
            token=token,
            auth_mode=auth_mode,
        )
        write_jsonl(jsonl_path, "modified-crafting-category", url, payload)
        upsert_modified_crafting_category(conn, payload)
        category_count += 1

    _, slot_index = request_bnet(
        "/data/wow/modified-crafting/reagent-slot-type/index",
        api_base_url=api_base_url,
        namespace=namespace,
        locale=locale,
        token=token,
        auth_mode=auth_mode,
    )
    slot_types = [
        slot_type["id"]
        for slot_type in slot_index.get("slot_types") or []
        if isinstance(slot_type, dict) and isinstance(slot_type.get("id"), int)
    ]
    slot_count = 0
    for slot_type_id in slot_types:
        url, payload = request_bnet(
            f"/data/wow/modified-crafting/reagent-slot-type/{slot_type_id}",
            api_base_url=api_base_url,
            namespace=namespace,
            locale=locale,
            token=token,
            auth_mode=auth_mode,
        )
        write_jsonl(jsonl_path, "modified-crafting-slot-type", url, payload)
        upsert_modified_crafting_slot_type(conn, payload)
        slot_count += 1
    conn.commit()
    return category_count, slot_count


def import_professions(
    conn: sqlite3.Connection,
    *,
    jsonl_path: Path,
    api_base_url: str,
    namespace: str,
    locale: str,
    token: str,
    auth_mode: str,
    skill_tier_pattern: str,
) -> tuple[int, int, int, set[int]]:
    url, index = request_bnet(
        "/data/wow/profession/index",
        api_base_url=api_base_url,
        namespace=namespace,
        locale=locale,
        token=token,
        auth_mode=auth_mode,
    )
    write_jsonl(jsonl_path, "profession-index", url, index)

    profession_count = 0
    skill_tier_count = 0
    recipe_count = 0
    reagent_item_ids: set[int] = set()
    professions = [
        profession["id"]
        for profession in index.get("professions") or []
        if isinstance(profession, dict) and isinstance(profession.get("id"), int)
    ]
    for profession_id in professions:
        url, profession = request_bnet(
            f"/data/wow/profession/{profession_id}",
            api_base_url=api_base_url,
            namespace=namespace,
            locale=locale,
            token=token,
            auth_mode=auth_mode,
        )
        write_jsonl(jsonl_path, "profession", url, profession)
        upsert_profession(conn, profession)
        profession_count += 1

        for tier_ref in profession.get("skill_tiers") or []:
            if not isinstance(tier_ref, dict) or not isinstance(tier_ref.get("id"), int):
                continue
            tier_name = tier_ref.get("name") or ""
            if skill_tier_pattern and skill_tier_pattern.lower() not in tier_name.lower():
                continue
            url, tier = request_bnet(
                f"/data/wow/profession/{profession_id}/skill-tier/{tier_ref['id']}",
                api_base_url=api_base_url,
                namespace=namespace,
                locale=locale,
                token=token,
                auth_mode=auth_mode,
            )
            write_jsonl(jsonl_path, "profession-skill-tier", url, tier)
            upsert_skill_tier(conn, profession_id=profession_id, payload=tier)
            skill_tier_count += 1
            for recipe_id, _recipe_name, category_name in recipe_ids_from_tier(
                conn,
                profession_id=profession_id,
                skill_tier_id=tier["id"],
                payload=tier,
            ):
                url, recipe = request_bnet(
                    f"/data/wow/recipe/{recipe_id}",
                    api_base_url=api_base_url,
                    namespace=namespace,
                    locale=locale,
                    token=token,
                    auth_mode=auth_mode,
                )
                write_jsonl(jsonl_path, "recipe", url, recipe)
                reagent_item_ids.update(
                    upsert_recipe(
                        conn,
                        profession_id=profession_id,
                        skill_tier_id=tier["id"],
                        category_name=category_name,
                        payload=recipe,
                    )
                )
                recipe_count += 1
                if recipe_count % 50 == 0:
                    conn.commit()
    conn.commit()
    return profession_count, skill_tier_count, recipe_count, reagent_item_ids


def ensure_reagent_items(
    conn: sqlite3.Connection,
    item_ids: set[int],
    *,
    api_base_url: str,
    region: str,
    namespace: str,
    locale: str,
    token: str,
    auth_mode: str,
    max_workers: int,
) -> int:
    existing = {
        row[0]
        for row in conn.execute(
            "SELECT item_id FROM item_details WHERE item_id IN (%s)"
            % ",".join("?" for _ in item_ids),
            tuple(sorted(item_ids)),
        )
    } if item_ids else set()
    missing = sorted(item_ids - existing)
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
            for item_id in missing
        ]
        for future in concurrent.futures.as_completed(futures):
            item_id, url, payload = future.result()
            if not conn.execute(
                "SELECT 1 FROM items WHERE item_id = ?", (item_id,)
            ).fetchone():
                item = normalize_item(payload, locale)
                conn.execute(
                    """
                    INSERT INTO items (
                        item_id, name, item_class_id, item_class_name,
                        item_subclass_id, item_subclass_name, inventory_type_id,
                        inventory_type_name, quality_type, level, required_level,
                        purchase_price, sell_price, is_stackable, is_equippable,
                        raw_json, expansion, source_endpoint, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    (
                        item_id,
                        item["name"] if item else payload.get("name"),
                        item["item_class_id"] if item else None,
                        item["item_class_name"] if item else None,
                        item["item_subclass_id"] if item else None,
                        item["item_subclass_name"] if item else None,
                        item["inventory_type_id"] if item else None,
                        item["inventory_type_name"] if item else None,
                        item["quality_type"] if item else None,
                        item["level"] if item else None,
                        item["required_level"] if item else None,
                        item["purchase_price"] if item else None,
                        item["sell_price"] if item else None,
                        item["is_stackable"] if item else None,
                        item["is_equippable"] if item else None,
                        item["raw_json"]
                        if item
                        else json.dumps(payload, ensure_ascii=False, sort_keys=True),
                        "midnight",
                        "profession-reagent",
                    ),
                )
            upsert_item_detail(conn, item_id=item_id, detail_url=url, payload=payload)
            enriched += 1
            if enriched % 50 == 0:
                conn.commit()
    conn.commit()
    return enriched


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", type=Path, default=DEFAULT_ENV)
    parser.add_argument("--database", type=Path, default=DEFAULT_DB)
    parser.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL)
    parser.add_argument("--append-jsonl", action="store_true")
    parser.add_argument("--skill-tier-pattern", default=MIDNIGHT_TIER_PATTERN)
    parser.add_argument("--skip-modified-crafting", action="store_true")
    parser.add_argument("--skip-reagent-item-details", action="store_true")
    parser.add_argument("--max-workers", type=int)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_env(args.env)
    if args.jsonl.exists() and not args.append_jsonl:
        args.jsonl.unlink()

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
    max_workers = max(1, args.max_workers or env_int("BN_MAX_WORKERS", 8))
    token = fetch_token(
        require_env("BN_CLIENT_ID", "BATTLENET_CLIENT_ID"),
        require_env("BN_CLIENT_SECRET", "BATTLENET_CLIENT_SECRET"),
        token_url,
    )

    conn = init_db(args.database)
    ensure_profession_schema(conn)
    category_count = 0
    slot_count = 0
    if not args.skip_modified_crafting:
        category_count, slot_count = import_modified_crafting(
            conn,
            jsonl_path=args.jsonl,
            api_base_url=api_base_url,
            namespace=namespace,
            locale=locale,
            token=token,
            auth_mode=auth_mode,
        )

    profession_count, skill_tier_count, recipe_count, reagent_item_ids = import_professions(
        conn,
        jsonl_path=args.jsonl,
        api_base_url=api_base_url,
        namespace=namespace,
        locale=locale,
        token=token,
        auth_mode=auth_mode,
        skill_tier_pattern=args.skill_tier_pattern,
    )
    enriched_count = 0
    if not args.skip_reagent_item_details:
        enriched_count = ensure_reagent_items(
            conn,
            reagent_item_ids,
            api_base_url=api_base_url,
            region=region,
            namespace=namespace,
            locale=locale,
            token=token,
            auth_mode=auth_mode,
            max_workers=max_workers,
        )

    conn.close()
    print(f"Imported professions: {profession_count}")
    print(f"Imported skill tiers: {skill_tier_count}")
    print(f"Imported recipes: {recipe_count}")
    print(f"Imported modified crafting categories: {category_count}")
    print(f"Imported modified crafting slot types: {slot_count}")
    print(f"Reagent item IDs found: {len(reagent_item_ids)}")
    print(f"Reagent item details enriched: {enriched_count}")
    print(f"Database: {args.database}")
    print(f"Raw payloads: {args.jsonl}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"HTTP {exc.code}: {body}", file=sys.stderr)
        raise
