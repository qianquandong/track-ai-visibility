#!/usr/bin/env python3
"""Local, dependency-free state store for the track-ai-visibility Codex skill."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

SCHEMA_VERSION = 1
DATA_FILES = {
    "prompts": "prompts.jsonl",
    "observations": "observations.jsonl",
    "mentions": "mentions.jsonl",
    "tasks": "tasks.jsonl",
    "pending-actions": "pending-actions.jsonl",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def state_dir(root: str | Path) -> Path:
    path = Path(root).expanduser().resolve()
    return path if path.name == ".ai-visibility" else path / ".ai-visibility"


def config_path(root: str | Path) -> Path:
    return state_dir(root) / "config.json"


def data_path(root: str | Path, kind: str) -> Path:
    return state_dir(root) / DATA_FILES[kind]


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_no}: invalid JSON: {exc.msg}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_no}: each JSONL line must be an object")
        rows.append(value)
    return rows


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(content, encoding="utf-8")
    temp.replace(path)


def require_config(root: str | Path) -> dict[str, Any]:
    path = config_path(root)
    if not path.exists():
        raise ValueError(f"No visibility project found at {state_dir(root)}. Run init first.")
    config = read_json(path)
    if config.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"Unsupported schema version: {config.get('schema_version')}")
    return config


def normalize_domain(url_or_domain: str) -> str:
    raw = url_or_domain.strip().lower()
    if not raw:
        return ""
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    return (parsed.hostname or "").removeprefix("www.")


def parse_competitor(value: str) -> dict[str, str]:
    name, _, domain = value.partition("|")
    if not name.strip():
        raise ValueError("Competitor must be NAME or NAME|DOMAIN")
    result = {"name": name.strip()}
    if domain.strip():
        result["domain"] = normalize_domain(domain)
    return result


def cmd_init(args: argparse.Namespace) -> dict[str, Any]:
    target = state_dir(args.root)
    cfg_path = target / "config.json"
    if cfg_path.exists() and not args.force:
        raise ValueError(f"Project already exists at {target}; omit init or pass --force to replace config only")
    target.mkdir(parents=True, exist_ok=True)
    (target / "reports").mkdir(exist_ok=True)
    config = {
        "schema_version": SCHEMA_VERSION,
        "brand": {
            "name": args.brand.strip(),
            "domain": normalize_domain(args.domain),
            "aliases": sorted(set(args.alias or [])),
        },
        "project": {
            "id": new_id("prj"),
            "name": args.project.strip(),
            "created_at": now_iso(),
        },
        "competitors": [parse_competitor(value) for value in (args.competitor or [])],
        "tracked_keywords": sorted(set(args.keyword or [])),
        "source_mode": "codex-native",
        "updated_at": now_iso(),
    }
    write_json(cfg_path, config)
    for filename in DATA_FILES.values():
        path = target / filename
        if not path.exists():
            path.write_text("", encoding="utf-8")
    if args.prompt:
        add_prompts(args.root, args.prompt, [])
    return {"status": "initialized", "state_dir": str(target), "config": config}


def add_prompts(root: str | Path, prompt_texts: list[str], tags: list[str]) -> dict[str, Any]:
    require_config(root)
    path = data_path(root, "prompts")
    rows = read_jsonl(path)
    by_text = {str(row.get("text", "")).strip().casefold(): row for row in rows}
    added: list[dict[str, Any]] = []
    restored: list[str] = []
    for text in prompt_texts:
        clean = text.strip()
        if not clean:
            continue
        key = clean.casefold()
        if key in by_text:
            row = by_text[key]
            if row.get("status") != "active":
                row["status"] = "active"
                row["updated_at"] = now_iso()
                restored.append(str(row["id"]))
            continue
        row = {
            "id": new_id("prm"),
            "text": clean,
            "status": "active",
            "tags": sorted(set(tags)),
            "created_at": now_iso(),
        }
        rows.append(row)
        by_text[key] = row
        added.append(row)
    write_jsonl(path, rows)
    return {"added": added, "restored_ids": restored, "active_count": sum(r.get("status") == "active" for r in rows)}


def cmd_add_prompts(args: argparse.Namespace) -> dict[str, Any]:
    prompts = list(args.prompt or [])
    if args.file:
        prompts.extend(line.strip() for line in Path(args.file).read_text(encoding="utf-8").splitlines() if line.strip())
    if not prompts:
        raise ValueError("Provide at least one --prompt or --file")
    return add_prompts(args.root, prompts, args.tag or [])


def cmd_remove_prompts(args: argparse.Namespace) -> dict[str, Any]:
    require_config(args.root)
    path = data_path(args.root, "prompts")
    rows = read_jsonl(path)
    ids = set(args.id or [])
    texts = {value.casefold() for value in (args.prompt or [])}
    changed: list[str] = []
    for row in rows:
        if row.get("id") in ids or str(row.get("text", "")).casefold() in texts:
            if row.get("status") != "archived":
                row["status"] = "archived"
                row["updated_at"] = now_iso()
                changed.append(str(row.get("id")))
    write_jsonl(path, rows)
    return {"archived_ids": changed}


def update_keywords(root: str | Path, values: list[str], remove: bool) -> dict[str, Any]:
    config = require_config(root)
    current = {str(value) for value in config.get("tracked_keywords", [])}
    if remove:
        current -= {value.strip() for value in values}
    else:
        current |= {value.strip() for value in values if value.strip()}
    config["tracked_keywords"] = sorted(current, key=str.casefold)
    config["updated_at"] = now_iso()
    write_json(config_path(root), config)
    return {"tracked_keywords": config["tracked_keywords"]}


def cmd_import(args: argparse.Namespace) -> dict[str, Any]:
    config = require_config(args.root)
    kind = args.kind
    incoming_path = Path(args.file)
    raw = incoming_path.read_text(encoding="utf-8")
    stripped = raw.lstrip()
    if stripped.startswith("["):
        values = json.loads(raw)
        if not isinstance(values, list):
            raise ValueError("JSON import must be an array")
    else:
        values = [json.loads(line) for line in raw.splitlines() if line.strip()]
    if not all(isinstance(value, dict) for value in values):
        raise ValueError("Every imported record must be an object")

    target = data_path(args.root, kind)
    existing = read_jsonl(target)
    existing_ids = {str(row.get("id")) for row in existing if row.get("id")}
    prompts = read_jsonl(data_path(args.root, "prompts")) if kind == "observations" else []
    prompt_by_id = {str(row.get("id")): row for row in prompts if row.get("id")}
    prompt_by_text = {str(row.get("text", "")).strip().casefold(): row for row in prompts if row.get("text")}
    prefix = {"observations": "obs", "mentions": "mnt", "tasks": "tsk"}[kind]
    imported = 0
    skipped = 0
    normalized: list[dict[str, Any]] = []
    for source in values:
        row = dict(source)
        row.setdefault("id", new_id(prefix))
        if str(row["id"]) in existing_ids:
            skipped += 1
            continue
        if kind == "observations":
            if not row.get("prompt_id") and not row.get("prompt_text"):
                raise ValueError("Observation requires prompt_id or prompt_text")
            if not row.get("prompt_id") and row.get("prompt_text"):
                matched_prompt = prompt_by_text.get(str(row["prompt_text"]).strip().casefold())
                if matched_prompt:
                    row["prompt_id"] = matched_prompt["id"]
            if row.get("prompt_id") and not row.get("prompt_text"):
                matched_prompt = prompt_by_id.get(str(row["prompt_id"]))
                if matched_prompt:
                    row["prompt_text"] = matched_prompt["text"]
            if not row.get("surface"):
                raise ValueError("Observation requires surface")
            if "brand_mentioned" not in row or not isinstance(row["brand_mentioned"], bool):
                raise ValueError("Observation requires boolean brand_mentioned")
            row.setdefault("captured_at", now_iso())
            row.setdefault("competitors", [])
            row.setdefault("citations", [])
            row.setdefault("evidence_urls", [])
            for citation in row["citations"]:
                if isinstance(citation, dict) and citation.get("url") and not citation.get("domain"):
                    citation["domain"] = normalize_domain(str(citation["url"]))
        elif kind == "mentions":
            if not row.get("source") or not row.get("url") or not row.get("title"):
                raise ValueError("Mention requires source, url, and title")
            row.setdefault("captured_at", now_iso())
        elif kind == "tasks":
            if not row.get("title"):
                raise ValueError("Task requires title")
            row.setdefault("kind", "other")
            row.setdefault("status", "queued")
            row.setdefault("cost_credits", 0)
            row.setdefault("created_at", now_iso())
            row.setdefault("updated_at", row["created_at"])
        existing_ids.add(str(row["id"]))
        normalized.append(row)
        imported += 1
    write_jsonl(target, [*existing, *normalized])
    return {"kind": kind, "imported": imported, "skipped_existing_ids": skipped, "project": config["project"]["id"]}


def filtered_observations(root: str | Path, days: int) -> list[dict[str, Any]]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result = []
    for row in read_jsonl(data_path(root, "observations")):
        captured = parse_time(str(row.get("captured_at", "")))
        if captured and captured >= cutoff:
            result.append(row)
    return result


def build_summary(root: str | Path, days: int) -> dict[str, Any]:
    config = require_config(root)
    prompts = read_jsonl(data_path(root, "prompts"))
    active_prompts = [row for row in prompts if row.get("status") == "active"]
    observations = filtered_observations(root, days)
    prompt_lookup = {str(row.get("id")): str(row.get("text")) for row in prompts}
    brand_domain = normalize_domain(str(config["brand"].get("domain", "")))

    mentioned = sum(bool(row.get("brand_mentioned")) for row in observations)
    positions = [float(row["brand_position"]) for row in observations if isinstance(row.get("brand_position"), (int, float))]
    owned_citations = 0
    citation_domains: Counter[str] = Counter()
    competitor_counts: Counter[str] = Counter()
    surface_counts: Counter[str] = Counter()
    covered_prompt_ids: set[str] = set()
    prompt_stats: dict[str, dict[str, Any]] = defaultdict(lambda: {"observations": 0, "brand_mentions": 0, "competitor_mentions": 0, "citation_domains": Counter()})

    for row in observations:
        surface_counts[str(row.get("surface", "unknown"))] += 1
        prompt_id = str(row.get("prompt_id", ""))
        prompt_key = prompt_id or str(row.get("prompt_text", "unknown"))
        if prompt_id:
            covered_prompt_ids.add(prompt_id)
        stats = prompt_stats[prompt_key]
        stats["observations"] += 1
        stats["brand_mentions"] += int(bool(row.get("brand_mentioned")))
        competitors = row.get("competitors", [])
        if isinstance(competitors, list):
            for competitor in competitors:
                name = competitor.get("name") if isinstance(competitor, dict) else str(competitor)
                if name:
                    competitor_counts[str(name)] += 1
                    stats["competitor_mentions"] += 1
        citations = row.get("citations", [])
        if isinstance(citations, list):
            for citation in citations:
                if not isinstance(citation, dict):
                    continue
                domain = normalize_domain(str(citation.get("domain") or citation.get("url") or ""))
                if domain:
                    citation_domains[domain] += 1
                    stats["citation_domains"][domain] += 1
                    if brand_domain and domain == brand_domain:
                        owned_citations += 1

    gaps = []
    for prompt_key, stats in prompt_stats.items():
        total = int(stats["observations"])
        brand_rate = stats["brand_mentions"] / total if total else 0
        competitor_rate = min(1.0, stats["competitor_mentions"] / total) if total else 0
        external_citations = sum(count for domain, count in stats["citation_domains"].items() if domain != brand_domain)
        citation_signal = min(1.0, external_citations / total) if total else 0
        score = round((1 - brand_rate) * 60 + competitor_rate * 25 + citation_signal * 15)
        gaps.append({
            "prompt_id": prompt_key if prompt_key in prompt_lookup else None,
            "prompt": prompt_lookup.get(prompt_key, prompt_key),
            "observations": total,
            "visibility_rate": round(brand_rate * 100, 1),
            "competitor_mentions": stats["competitor_mentions"],
            "opportunity_score": score,
        })
    gaps.sort(key=lambda value: (-value["opportunity_score"], -value["observations"], value["prompt"]))

    mentions = read_jsonl(data_path(root, "mentions"))
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    fresh_mentions = [row for row in mentions if (parse_time(str(row.get("captured_at") or row.get("published_at") or "")) or datetime.min.replace(tzinfo=timezone.utc)) >= cutoff]
    tasks = read_jsonl(data_path(root, "tasks"))

    total = len(observations)
    return {
        "period_days": days,
        "generated_at": now_iso(),
        "brand": config["brand"],
        "project": config["project"],
        "coverage": {
            "active_prompts": len(active_prompts),
            "covered_prompts": len(covered_prompt_ids),
            "observations": total,
            "surfaces": dict(surface_counts),
            "prompt_coverage_pct": round((len(covered_prompt_ids) / len(active_prompts) * 100), 1) if active_prompts else 0,
        },
        "visibility": {
            "brand_mentions": mentioned,
            "visibility_rate_pct": round((mentioned / total * 100), 1) if total else 0,
            "average_position": round(sum(positions) / len(positions), 2) if positions else None,
            "owned_domain_citations": owned_citations,
            "citation_rate_pct": round((owned_citations / total * 100), 1) if total else 0,
        },
        "competitors": [{"name": name, "mentions": count} for name, count in competitor_counts.most_common()],
        "citation_domains": [{"domain": domain, "citations": count, "owned": domain == brand_domain} for domain, count in citation_domains.most_common()],
        "prompt_gaps": gaps,
        "listening": {
            "mentions": len(fresh_mentions),
            "by_source": dict(Counter(str(row.get("source", "unknown")) for row in fresh_mentions)),
            "top_items": fresh_mentions[:10],
        },
        "tasks": dict(Counter(str(row.get("status", "unknown")) for row in tasks)),
    }


def cmd_status(args: argparse.Namespace) -> dict[str, Any]:
    config = require_config(args.root)
    counts = {kind: len(read_jsonl(data_path(args.root, kind))) for kind in DATA_FILES}
    return {"state_dir": str(state_dir(args.root)), "config": config, "counts": counts}


def cmd_validate(args: argparse.Namespace) -> dict[str, Any]:
    config = require_config(args.root)
    errors: list[str] = []
    for kind in DATA_FILES:
        try:
            read_jsonl(data_path(args.root, kind))
        except ValueError as exc:
            errors.append(str(exc))
    if not config.get("brand", {}).get("name"):
        errors.append("config.brand.name is required")
    if not config.get("brand", {}).get("domain"):
        errors.append("config.brand.domain is required")
    return {"valid": not errors, "errors": errors, "schema_version": config.get("schema_version")}


def cmd_prepare_task(args: argparse.Namespace) -> dict[str, Any]:
    require_config(args.root)
    payload = {
        "kind": args.kind,
        "title": args.title.strip(),
        "details": args.details or "",
        "cost_credits": max(0, args.cost_credits),
        "idempotency_key": args.idempotency_key or hashlib.sha256(f"{args.kind}\0{args.title}\0{args.details or ''}".encode()).hexdigest()[:24],
    }
    existing_tasks = read_jsonl(data_path(args.root, "tasks"))
    for task in existing_tasks:
        if task.get("idempotency_key") == payload["idempotency_key"]:
            return {"status": "already_confirmed", "task": task}
    token = new_id("confirm")
    pending = {
        "id": token,
        "action": "create_task",
        "payload": payload,
        "status": "pending",
        "created_at": now_iso(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=30)).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }
    rows = read_jsonl(data_path(args.root, "pending-actions"))
    write_jsonl(data_path(args.root, "pending-actions"), [*rows, pending])
    return {"status": "confirmation_required", "confirmation_token": token, "preview": payload, "expires_at": pending["expires_at"]}


def cmd_confirm_task(args: argparse.Namespace) -> dict[str, Any]:
    require_config(args.root)
    pending_path = data_path(args.root, "pending-actions")
    rows = read_jsonl(pending_path)
    match = next((row for row in rows if row.get("id") == args.token), None)
    if not match:
        raise ValueError("Unknown confirmation token")
    if match.get("status") == "confirmed":
        tasks = read_jsonl(data_path(args.root, "tasks"))
        task = next((row for row in tasks if row.get("id") == match.get("task_id")), None)
        return {"status": "already_confirmed", "task": task}
    expiry = parse_time(str(match.get("expires_at", "")))
    if not expiry or expiry < datetime.now(timezone.utc):
        match["status"] = "expired"
        write_jsonl(pending_path, rows)
        raise ValueError("Confirmation token expired; prepare the task again")
    payload = dict(match["payload"])
    tasks_path = data_path(args.root, "tasks")
    tasks = read_jsonl(tasks_path)
    existing = next((row for row in tasks if row.get("idempotency_key") == payload.get("idempotency_key")), None)
    if existing:
        task = existing
    else:
        task = {
            "id": new_id("tsk"),
            **payload,
            "status": "queued",
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
        tasks.append(task)
        write_jsonl(tasks_path, tasks)
    match["status"] = "confirmed"
    match["task_id"] = task["id"]
    match["confirmed_at"] = now_iso()
    write_jsonl(pending_path, rows)
    return {"status": "confirmed", "task": task}


def cmd_cancel_task(args: argparse.Namespace) -> dict[str, Any]:
    require_config(args.root)
    path = data_path(args.root, "tasks")
    tasks = read_jsonl(path)
    task = next((row for row in tasks if row.get("id") == args.id), None)
    if not task:
        raise ValueError("Unknown task ID")
    if task.get("status") not in {"cancelled", "refunded"}:
        task["status"] = "cancelled"
        task["updated_at"] = now_iso()
        write_jsonl(path, tasks)
    return {"task": task}


def cmd_refund_task(args: argparse.Namespace) -> dict[str, Any]:
    require_config(args.root)
    path = data_path(args.root, "tasks")
    tasks = read_jsonl(path)
    task = next((row for row in tasks if row.get("id") == args.id), None)
    if not task:
        raise ValueError("Unknown task ID")
    if task.get("status") != "refunded":
        task["status"] = "refunded"
        task["refunded_credits"] = task.get("cost_credits", 0)
        task["updated_at"] = now_iso()
        write_jsonl(path, tasks)
    return {"task": task}


def render_report(summary: dict[str, Any]) -> str:
    coverage = summary["coverage"]
    visibility = summary["visibility"]
    lines = [
        f"# AI Visibility Report — {summary['brand']['name']}",
        "",
        f"Generated: {summary['generated_at']}  ",
        f"Window: last {summary['period_days']} days",
        "",
        "## Coverage",
        "",
        f"- {coverage['observations']} observations across {coverage['covered_prompts']} of {coverage['active_prompts']} active prompts ({coverage['prompt_coverage_pct']}%).",
        f"- Surfaces: {', '.join(f'{key} ({value})' for key, value in coverage['surfaces'].items()) or 'none'}.",
        "",
        "## Visibility",
        "",
        f"- Visibility rate: **{visibility['visibility_rate_pct']}%** ({visibility['brand_mentions']}/{coverage['observations']}).",
        f"- Average recorded position: **{visibility['average_position'] if visibility['average_position'] is not None else 'n/a'}**.",
        f"- Owned-domain citation rate: **{visibility['citation_rate_pct']}%** ({visibility['owned_domain_citations']}/{coverage['observations']}).",
        "",
        "## Competitors",
        "",
    ]
    if summary["competitors"]:
        lines.extend(f"- {item['name']}: {item['mentions']} mentions" for item in summary["competitors"][:10])
    else:
        lines.append("- No competitor mentions recorded.")
    lines.extend(["", "## Highest-opportunity prompt gaps", ""])
    if summary["prompt_gaps"]:
        lines.extend(
            f"- **{item['opportunity_score']}** — {item['prompt']} (visibility {item['visibility_rate']}%, {item['observations']} observations)"
            for item in summary["prompt_gaps"][:10]
        )
    else:
        lines.append("- No observations available. Run a current scan.")
    lines.extend(["", "## Citation sources", ""])
    if summary["citation_domains"]:
        lines.extend(f"- {item['domain']}: {item['citations']} citations{' (owned)' if item['owned'] else ''}" for item in summary["citation_domains"][:15])
    else:
        lines.append("- No citation evidence recorded.")
    lines.extend([
        "",
        "## Listening",
        "",
        f"- {summary['listening']['mentions']} recent mentions: {json.dumps(summary['listening']['by_source'], ensure_ascii=False)}",
        "",
        "## Interpretation note",
        "",
        "Metrics describe only the recorded prompts, surfaces, and dates. They are not a universal measure of every AI model.",
        "",
    ])
    return "\n".join(lines)


def cmd_report(args: argparse.Namespace) -> dict[str, Any]:
    summary = build_summary(args.root, args.days)
    report = render_report(summary)
    output = Path(args.output).expanduser().resolve() if args.output else state_dir(args.root) / "reports" / "latest.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    return {"output": str(output), "summary": summary}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Initialize a local visibility project")
    init.add_argument("--root", default=".")
    init.add_argument("--brand", required=True)
    init.add_argument("--domain", required=True)
    init.add_argument("--project", default="AI visibility")
    init.add_argument("--alias", action="append")
    init.add_argument("--competitor", action="append", help="NAME or NAME|DOMAIN")
    init.add_argument("--keyword", action="append")
    init.add_argument("--prompt", action="append")
    init.add_argument("--force", action="store_true")
    init.set_defaults(func=cmd_init)

    for name, func in (("status", cmd_status), ("validate", cmd_validate)):
        command = sub.add_parser(name)
        command.add_argument("--root", default=".")
        command.set_defaults(func=func)

    add_prompts_parser = sub.add_parser("add-prompts")
    add_prompts_parser.add_argument("--root", default=".")
    add_prompts_parser.add_argument("--prompt", action="append")
    add_prompts_parser.add_argument("--file")
    add_prompts_parser.add_argument("--tag", action="append")
    add_prompts_parser.set_defaults(func=cmd_add_prompts)

    remove_prompts_parser = sub.add_parser("remove-prompts")
    remove_prompts_parser.add_argument("--root", default=".")
    remove_prompts_parser.add_argument("--id", action="append")
    remove_prompts_parser.add_argument("--prompt", action="append")
    remove_prompts_parser.set_defaults(func=cmd_remove_prompts)

    for name, remove in (("add-keywords", False), ("remove-keywords", True)):
        command = sub.add_parser(name)
        command.add_argument("--root", default=".")
        command.add_argument("--keyword", action="append", required=True)
        command.set_defaults(func=lambda args, should_remove=remove: update_keywords(args.root, args.keyword, should_remove))

    importer = sub.add_parser("import")
    importer.add_argument("--root", default=".")
    importer.add_argument("--kind", choices=("observations", "mentions", "tasks"), required=True)
    importer.add_argument("--file", required=True)
    importer.set_defaults(func=cmd_import)

    summary = sub.add_parser("summary")
    summary.add_argument("--root", default=".")
    summary.add_argument("--days", type=int, default=30)
    summary.set_defaults(func=lambda args: build_summary(args.root, args.days))

    report = sub.add_parser("report")
    report.add_argument("--root", default=".")
    report.add_argument("--days", type=int, default=30)
    report.add_argument("--output")
    report.set_defaults(func=cmd_report)

    prepare = sub.add_parser("prepare-task")
    prepare.add_argument("--root", default=".")
    prepare.add_argument("--kind", default="other")
    prepare.add_argument("--title", required=True)
    prepare.add_argument("--details")
    prepare.add_argument("--cost-credits", type=int, default=0)
    prepare.add_argument("--idempotency-key")
    prepare.set_defaults(func=cmd_prepare_task)

    confirm = sub.add_parser("confirm-task")
    confirm.add_argument("--root", default=".")
    confirm.add_argument("--token", required=True)
    confirm.set_defaults(func=cmd_confirm_task)

    for name, func in (("cancel-task", cmd_cancel_task), ("refund-task", cmd_refund_task)):
        command = sub.add_parser(name)
        command.add_argument("--root", default=".")
        command.add_argument("--id", required=True)
        command.set_defaults(func=func)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        result = args.func(args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if isinstance(result, dict) and result.get("valid") is False:
            return 1
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
