#!/usr/bin/env python3
"""Generate and review AhSense ontology candidates from the local item DB."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "research" / "item-db" / "midnight-research.sqlite"
DEFAULT_STATE = ROOT / "research" / "ontology-review" / "reviews.json"
DEFAULT_EXPORT_DIR = ROOT / "research" / "ontology-review" / "generated"
REQUIRED_TABLES = {"items", "item_details", "item_stats", "item_spells"}
REQUIRED_ITEM_COLUMNS = {
    "item_id",
    "name",
    "item_class_id",
    "item_class_name",
    "item_subclass_name",
    "quality_type",
    "level",
    "required_level",
    "stat_signature",
    "spell_ids_json",
    "equip_use_text",
    "required_profession_name",
    "binding_type",
}
AUCTIONABLE_FILTER = "(binding_type is null or binding_type != 'ON_ACQUIRE')"


def slug(value: str) -> str:
    value = value.lower().replace("&", "and")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "candidate"


def compact_hash(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:8]


def wowhead_url(item_id: int) -> str:
    return f"https://www.wowhead.com/item={item_id}"


def lua_quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def load_state(path: Path = DEFAULT_STATE) -> dict[str, Any]:
    if not path.exists():
        return {"reviews": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(state: dict[str, Any], path: Path = DEFAULT_STATE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")


def connect(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        raise SystemExit(f"Database not found: {db_path}")
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    return con


def validate_database(db_path: Path) -> list[str]:
    errors: list[str] = []
    con = connect(db_path)
    tables = {
        row["name"]
        for row in con.execute(
            "select name from sqlite_master where type='table' order by name"
        )
    }
    missing_tables = sorted(REQUIRED_TABLES - tables)
    if missing_tables:
        errors.append(f"Missing required tables: {', '.join(missing_tables)}")

    if "items" in tables:
        columns = {row["name"] for row in con.execute("pragma table_info(items)")}
        missing_columns = sorted(REQUIRED_ITEM_COLUMNS - columns)
        if missing_columns:
            errors.append(f"Missing required items columns: {', '.join(missing_columns)}")

    return errors


def rows_to_items(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    items = []
    for row in rows:
        item_id = int(row["item_id"])
        items.append(
            {
                "itemID": item_id,
                "name": row["name"],
                "quality": row["quality_type"],
                "level": row["level"],
                "requiredLevel": row["required_level"],
                "subclass": row["item_subclass_name"],
                "wowheadUrl": wowhead_url(item_id),
                "equipUseText": row["equip_use_text"],
                "statSignature": row["stat_signature"],
                "spellIds": row["spell_ids_json"],
            }
        )
    return items


def candidate_id(rule: str, parts: list[Any], item_ids: list[int]) -> str:
    readable = "-".join(slug(str(part)) for part in parts if part)
    digest = compact_hash(f"{rule}:{','.join(str(item_id) for item_id in item_ids)}")
    return f"{readable}-{digest}"


def build_profession_candidates(con: sqlite3.Connection) -> list[dict[str, Any]]:
    sql = """
        select *
        from items
        where item_class_id = 19
          and {auctionable}
          and required_profession_name is not null
          and stat_signature is not null
          and stat_signature != ''
          and spell_ids_json is not null
          and spell_ids_json != '[]'
          and equip_use_text is not null
        order by required_profession_name, quality_type, level, item_id
    """.format(auctionable=AUCTIONABLE_FILTER)
    buckets: dict[tuple[Any, ...], list[sqlite3.Row]] = {}
    for row in con.execute(sql):
        key = (
            row["required_profession_name"],
            row["item_subclass_name"],
            row["quality_type"],
            row["level"],
            row["required_level"],
            row["stat_signature"],
            row["spell_ids_json"],
            row["equip_use_text"],
        )
        buckets.setdefault(key, []).append(row)

    candidates = []
    for key, rows in buckets.items():
        if len(rows) < 2:
            continue
        profession, subclass, quality, level, required_level, stats, spells, equip = key
        item_ids = [int(row["item_id"]) for row in rows]
        candidates.append(
            {
                "id": candidate_id(
                    "profession_exact_utility_match",
                    ["midnight", subclass, quality, "exact-utility", level],
                    item_ids,
                ),
                "rule": "profession_exact_utility_match",
                "category": "profession_tool",
                "confidenceTier": "tier1",
                "passiveEligible": False,
                "hint": "Comparable profession item available",
                "rationale": f"Same {profession} profession stats and skill bonus",
                "items": rows_to_items(rows),
                "evidence": [
                    f"Profession: {profession}",
                    f"Quality: {quality}",
                    f"Item level: {level}",
                    f"Required level: {required_level}",
                    f"Stats: {stats}",
                    f"Spell IDs: {spells}",
                    f"Equip text: {equip}",
                ],
                "riskFlags": [],
            }
        )
    return candidates


def build_consumable_same_name_candidates(con: sqlite3.Connection) -> list[dict[str, Any]]:
    allowed_subclasses = {"Potions", "Flasks & Phials", "Food & Drink"}
    sql = """
        select *
        from items
        where item_class_id = 0
          and {auctionable}
          and spell_ids_json is not null
          and spell_ids_json != '[]'
        order by item_subclass_name, name, level desc, item_id
    """.format(auctionable=AUCTIONABLE_FILTER)
    buckets: dict[tuple[Any, ...], list[sqlite3.Row]] = {}
    for row in con.execute(sql):
        if row["item_subclass_name"] not in allowed_subclasses:
            continue
        key = (row["item_subclass_name"], row["name"], row["spell_ids_json"])
        buckets.setdefault(key, []).append(row)

    candidates = []
    for key, rows in buckets.items():
        if len(rows) < 2:
            continue
        subclass, name, spells = key
        item_ids = [int(row["item_id"]) for row in rows]
        candidates.append(
            {
                "id": candidate_id(
                    "consumable_same_name_spell_variants",
                    ["midnight", subclass, name],
                    item_ids,
                ),
                "rule": "consumable_same_name_spell_variants",
                "category": "consumable_family",
                "confidenceTier": "tier1",
                "passiveEligible": False,
                "hint": "Comparable consumables available",
                "rationale": f"Same {name} effect across item-level variants",
                "items": rows_to_items(rows),
                "evidence": [
                    f"Subclass: {subclass}",
                    f"Name: {name}",
                    f"Spell IDs: {spells}",
                    "Item text differs only by scaling or quality-sensitive values",
                ],
                "riskFlags": [],
            }
        )
    return candidates


def build_consumable_same_spell_candidates(con: sqlite3.Connection) -> list[dict[str, Any]]:
    allowed_subclasses = {"Potions", "Flasks & Phials"}
    sql = """
        select *
        from items
        where item_class_id = 0
          and {auctionable}
          and spell_ids_json is not null
          and spell_ids_json != '[]'
        order by item_subclass_name, spell_ids_json, name, item_id
    """.format(auctionable=AUCTIONABLE_FILTER)
    buckets: dict[tuple[Any, ...], list[sqlite3.Row]] = {}
    for row in con.execute(sql):
        if row["item_subclass_name"] not in allowed_subclasses:
            continue
        key = (row["item_subclass_name"], row["spell_ids_json"])
        buckets.setdefault(key, []).append(row)

    candidates = []
    for key, rows in buckets.items():
        names = sorted({row["name"] for row in rows})
        if len(rows) < 2 or len(names) < 2:
            continue
        subclass, spells = key
        item_ids = [int(row["item_id"]) for row in rows]
        candidates.append(
            {
                "id": candidate_id(
                    "consumable_same_spell_family",
                    ["midnight", subclass, "same-spell", spells],
                    item_ids,
                ),
                "rule": "consumable_same_spell_family",
                "category": "consumable_family",
                "confidenceTier": "tier2",
                "passiveEligible": False,
                "hint": "Comparable consumables available",
                "rationale": "Same item-provided spell across related consumables",
                "items": rows_to_items(rows),
                "evidence": [
                    f"Subclass: {subclass}",
                    f"Names: {', '.join(names)}",
                    f"Spell IDs: {spells}",
                ],
                "riskFlags": ["Different item names require human review"],
            }
        )
    return candidates


def build_candidates(db_path: Path = DEFAULT_DB) -> list[dict[str, Any]]:
    con = connect(db_path)
    candidates = (
        build_profession_candidates(con)
        + build_consumable_same_name_candidates(con)
        + build_consumable_same_spell_candidates(con)
    )
    return sorted(candidates, key=lambda c: (c["category"], c["rule"], c["id"]))


def merge_reviews(candidates: list[dict[str, Any]], state: dict[str, Any]) -> list[dict[str, Any]]:
    reviews = state.get("reviews", {})
    merged = []
    for candidate in candidates:
        candidate = dict(candidate)
        candidate["review"] = reviews.get(candidate["id"], {"status": "pending"})
        merged.append(candidate)
    return merged


def approved_candidates(candidates: list[dict[str, Any]], state: dict[str, Any]) -> list[dict[str, Any]]:
    reviews = state.get("reviews", {})
    return [
        candidate
        for candidate in candidates
        if reviews.get(candidate["id"], {}).get("status") == "approved"
    ]


def approved_item_conflicts(candidates: list[dict[str, Any]]) -> dict[int, list[str]]:
    seen: dict[int, list[str]] = {}
    for candidate in candidates:
        for item in candidate["items"]:
            seen.setdefault(int(item["itemID"]), []).append(candidate["id"])
    return {item_id: ids for item_id, ids in seen.items() if len(ids) > 1}


def lua_group(candidate: dict[str, Any]) -> str:
    lines = [
        f'ns.Ontology.AddGroup({lua_quote(candidate["id"])}, {{',
        f'    category = {lua_quote(candidate["category"])},',
        f'    confidence_tier = {lua_quote(candidate["confidenceTier"])},',
        f"    passive_eligible = {'true' if candidate['passiveEligible'] else 'false'},",
        f'    rationale = {lua_quote(candidate["rationale"])},',
        f'    hint = {lua_quote(candidate["hint"])},',
        "    items = {",
    ]
    for item in candidate["items"]:
        lines.extend(
            [
                "        {",
                f'            itemID = {item["itemID"]},',
                f'            name = {lua_quote(item["name"])},',
                "        },",
            ]
        )
    lines.extend(["    },", "})", ""])
    return "\n".join(lines)


def export_lua(candidates: list[dict[str, Any]], state: dict[str, Any], out_dir: Path) -> dict[str, Path]:
    approved = approved_candidates(candidates, state)
    conflicts = approved_item_conflicts(approved)
    if conflicts:
        examples = []
        for item_id, ids in sorted(conflicts.items())[:8]:
            examples.append(f"{item_id}: {', '.join(ids)}")
        raise ValueError(
            "Approved candidates overlap; each item can ship in only one ontology "
            "group with the current addon schema. Resolve these review decisions "
            "before export:\n" + "\n".join(examples)
        )

    grouped: dict[str, list[dict[str, Any]]] = {
        "Consumables.lua": [],
        "ProfessionTools.lua": [],
    }
    for candidate in approved:
        if candidate["category"] == "profession_tool":
            grouped["ProfessionTools.lua"].append(candidate)
        elif candidate["category"] == "consumable_family":
            grouped["Consumables.lua"].append(candidate)

    out_dir.mkdir(parents=True, exist_ok=True)
    written = {}
    for filename, items in grouped.items():
        path = out_dir / filename
        body = ["local _, ns = ...", ""]
        for candidate in sorted(items, key=lambda c: c["id"]):
            body.append(lua_group(candidate))
        path.write_text("\n".join(body).rstrip() + "\n", encoding="utf-8")
        written[filename] = path
    return written


HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AhSense Ontology Review</title>
  <style>
    :root { color-scheme: light; font-family: Arial, sans-serif; }
    body { margin: 0; background: #f6f7f9; color: #20242a; }
    header { padding: 14px 20px; background: #ffffff; border-bottom: 1px solid #d9dee7; display: flex; justify-content: space-between; gap: 16px; align-items: center; }
    main { display: grid; grid-template-columns: 320px 1fr; min-height: calc(100vh - 58px); }
    aside { border-right: 1px solid #d9dee7; background: #ffffff; overflow: auto; }
    button { border: 1px solid #b7bfcd; background: #ffffff; border-radius: 6px; padding: 8px 10px; cursor: pointer; }
    button.primary { background: #176b52; border-color: #176b52; color: white; }
    button.danger { background: #8f2f2f; border-color: #8f2f2f; color: white; }
    button:disabled { opacity: .55; cursor: default; }
    .toolbar { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
    .list-item { padding: 12px 14px; border-bottom: 1px solid #edf0f4; cursor: pointer; }
    .list-item.active { background: #e9f1ee; }
    .list-item small, .muted { color: #68717d; }
    .content { padding: 22px; overflow: auto; }
    .panel { background: #ffffff; border: 1px solid #d9dee7; border-radius: 8px; padding: 18px; max-width: 1040px; }
    .badge { display: inline-block; padding: 3px 7px; border: 1px solid #c8d0db; border-radius: 999px; font-size: 12px; margin-right: 6px; background: #f9fafb; }
    .risk { border-color: #e4b24d; background: #fff7e6; }
    table { width: 100%; border-collapse: collapse; margin-top: 12px; }
    th, td { text-align: left; padding: 8px; border-bottom: 1px solid #edf0f4; vertical-align: top; }
    pre { white-space: pre-wrap; background: #f4f6f8; padding: 12px; border-radius: 6px; }
    .actions { display: flex; gap: 8px; margin-top: 16px; flex-wrap: wrap; }
    .links { display: none; margin-top: 12px; }
    .links.open { display: block; }
    @media (max-width: 800px) { main { grid-template-columns: 1fr; } aside { max-height: 280px; } }
  </style>
</head>
<body>
  <header>
    <strong>AhSense Ontology Review</strong>
    <div class="toolbar">
      <span id="summary" class="muted"></span>
      <button id="export">Export Lua Drafts</button>
    </div>
  </header>
  <main>
    <aside id="list"></aside>
    <section class="content"><div id="detail" class="panel"></div></section>
  </main>
  <script>
    let candidates = [];
    let selected = 0;

    async function api(path, options) {
      const response = await fetch(path, options);
      if (!response.ok) throw new Error(await response.text());
      return response.json();
    }

    function esc(value) {
      return String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
    }

    function statusOf(candidate) {
      return candidate.review?.status || 'pending';
    }

    function renderList() {
      const counts = candidates.reduce((acc, c) => {
        acc[statusOf(c)] = (acc[statusOf(c)] || 0) + 1;
        return acc;
      }, {});
      document.getElementById('summary').textContent =
        `${candidates.length} candidates | ${counts.pending || 0} pending | ${counts.approved || 0} approved | ${counts.rejected || 0} rejected`;
      document.getElementById('list').innerHTML = candidates.map((c, index) => `
        <div class="list-item ${index === selected ? 'active' : ''}" onclick="selected=${index};render()">
          <strong>${esc(c.items[0]?.name || c.id)}</strong><br>
          <small>${esc(c.rule)} | ${esc(statusOf(c))}</small>
        </div>
      `).join('');
    }

    function renderDetail() {
      const c = candidates[selected];
      if (!c) {
        document.getElementById('detail').innerHTML = '<p>No candidates found.</p>';
        return;
      }
      const risks = c.riskFlags.map(r => `<span class="badge risk">${esc(r)}</span>`).join('');
      document.getElementById('detail').innerHTML = `
        <h2>${esc(c.id)}</h2>
        <p>
          <span class="badge">${esc(c.category)}</span>
          <span class="badge">${esc(c.confidenceTier)}</span>
          <span class="badge">${esc(c.rule)}</span>
          <span class="badge">${c.passiveEligible ? 'passive eligible' : 'active only'}</span>
          ${risks}
        </p>
        <p><strong>Rationale:</strong> ${esc(c.rationale)}</p>
        <p><strong>Hint:</strong> ${esc(c.hint)}</p>
        <h3>Items</h3>
        <table>
          <thead><tr><th>ID</th><th>Name</th><th>Level</th><th>Evidence Text</th></tr></thead>
          <tbody>
            ${c.items.map(item => `
              <tr>
                <td>${item.itemID}</td>
                <td>${esc(item.name)}</td>
                <td>${esc(item.level)}</td>
                <td>${esc(item.equipUseText || item.statSignature || item.spellIds || '')}</td>
              </tr>`).join('')}
          </tbody>
        </table>
        <h3>Trace</h3>
        <pre>${esc(c.evidence.join('\\n'))}</pre>
        <div class="actions">
          <button class="primary" onclick="review('approved')">Yes, ship it</button>
          <button class="danger" onclick="review('rejected')">No, reject it</button>
          <button onclick="toggleLinks()">Show Wowhead links</button>
        </div>
        <div id="links" class="links">
          ${c.items.map(item => `<p><a href="${item.wowheadUrl}" target="_blank" rel="noreferrer">${item.itemID}: ${esc(item.name)}</a></p>`).join('')}
        </div>
      `;
    }

    function render() {
      renderList();
      renderDetail();
    }

    function toggleLinks() {
      document.getElementById('links').classList.toggle('open');
    }

    async function review(status) {
      const candidate = candidates[selected];
      await api('/api/review', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({id: candidate.id, status})
      });
      await load();
      while (selected < candidates.length && statusOf(candidates[selected]) !== 'pending') selected++;
      if (selected >= candidates.length) selected = Math.max(0, candidates.length - 1);
      render();
    }

    async function load() {
      candidates = await api('/api/candidates');
      const pending = candidates.findIndex(c => statusOf(c) === 'pending');
      selected = pending >= 0 ? pending : 0;
    }

    document.getElementById('export').addEventListener('click', async () => {
      try {
        const result = await api('/api/export', {method: 'POST'});
        alert('Wrote:\\n' + result.files.join('\\n'));
      } catch (err) {
        alert(err.message);
      }
    });

    load().then(render).catch(err => {
      document.getElementById('detail').innerHTML = `<p>${esc(err.message)}</p>`;
    });
  </script>
</body>
</html>
"""


class ReviewHandler(BaseHTTPRequestHandler):
    db_path = DEFAULT_DB
    state_path = DEFAULT_STATE
    export_dir = DEFAULT_EXPORT_DIR

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def json_response(self, value: Any, status: int = 200) -> None:
        body = json.dumps(value).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            body = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/api/candidates":
            candidates = merge_reviews(build_candidates(self.db_path), load_state(self.state_path))
            self.json_response(candidates)
            return
        self.send_error(404)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", "0"))
        data = json.loads(self.rfile.read(length).decode("utf-8") or "{}")

        if path == "/api/review":
            status = data.get("status")
            if status not in {"approved", "rejected"}:
                self.json_response({"error": "Invalid review status"}, 400)
                return
            candidate_id_value = data.get("id")
            known = {candidate["id"] for candidate in build_candidates(self.db_path)}
            if candidate_id_value not in known:
                self.json_response({"error": "Unknown candidate"}, 404)
                return
            state = load_state(self.state_path)
            state.setdefault("reviews", {})[candidate_id_value] = {"status": status}
            save_state(state, self.state_path)
            self.json_response({"ok": True})
            return

        if path == "/api/export":
            try:
                files = export_lua(
                    build_candidates(self.db_path),
                    load_state(self.state_path),
                    self.export_dir,
                )
            except ValueError as exc:
                body = str(exc).encode("utf-8")
                self.send_response(409)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            self.json_response({"files": [str(path) for path in files.values()]})
            return

        self.send_error(404)


def command_candidates(args: argparse.Namespace) -> int:
    candidates = merge_reviews(build_candidates(args.database), load_state(args.state))
    if args.json:
        print(json.dumps(candidates, indent=2))
    else:
        counts: dict[str, int] = {}
        for candidate in candidates:
            key = f"{candidate['category']}:{candidate['rule']}"
            counts[key] = counts.get(key, 0) + 1
        print(f"{len(candidates)} candidates")
        for key, count in sorted(counts.items()):
            print(f"  {key}: {count}")
    return 0


def command_validate(args: argparse.Namespace) -> int:
    errors = validate_database(args.database)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    candidates = build_candidates(args.database)
    print(f"Database schema OK: {args.database}")
    print(f"Generated candidates: {len(candidates)}")
    return 0


def command_export(args: argparse.Namespace) -> int:
    try:
        files = export_lua(build_candidates(args.database), load_state(args.state), args.output)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1
    for path in files.values():
        print(path)
    return 0


def command_serve(args: argparse.Namespace) -> int:
    errors = validate_database(args.database)
    if errors:
        raise SystemExit("\n".join(errors))

    ReviewHandler.db_path = args.database
    ReviewHandler.state_path = args.state
    ReviewHandler.export_dir = args.output
    server = ThreadingHTTPServer((args.host, args.port), ReviewHandler)
    url = f"http://{args.host}:{server.server_address[1]}"
    print(f"Ontology review server running at {url}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DB)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--output", type=Path, default=DEFAULT_EXPORT_DIR)

    subparsers = parser.add_subparsers(dest="command", required=True)

    candidates = subparsers.add_parser("candidates", help="List generated candidates")
    candidates.add_argument("--json", action="store_true")
    candidates.set_defaults(func=command_candidates)

    validate = subparsers.add_parser("validate", help="Validate DB schema and candidate generation")
    validate.set_defaults(func=command_validate)

    export = subparsers.add_parser("export-lua", help="Export approved candidates as Lua drafts")
    export.set_defaults(func=command_export)

    serve = subparsers.add_parser("serve", help="Run the local review UI")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    serve.set_defaults(func=command_serve)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
