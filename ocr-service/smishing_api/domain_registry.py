from __future__ import annotations

import csv
import json
import re
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

from .config import DOMAIN_SEED_PATH, OFFICIAL_DOMAINS_PATH


def _hostname(value: str) -> str:
    candidate = value if "://" in value else f"https://{value}"
    try:
        return (urlsplit(candidate).hostname or "").lower().strip(".")
    except ValueError:
        return ""


def _domain_matches(hostname: str, allowed_domain: str) -> bool:
    allowed = allowed_domain.lower().strip(".")
    return hostname == allowed or hostname.endswith(f".{allowed}")


@lru_cache(maxsize=1)
def load_domain_registry(path: str | None = None, csv_path: str | None = None) -> dict:
    registry_path = Path(path).resolve() if path else DOMAIN_SEED_PATH
    try:
        seeds = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        seeds = {"official_services": [], "messenger_services": []}
    # Explicit JSON paths retain the legacy registry interface.
    if path is not None and csv_path is None:
        return seeds
    registry = {"official_services": [], "messenger_services": []}
    source = Path(csv_path) if csv_path is not None else OFFICIAL_DOMAINS_PATH
    try:
        with source.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            required = {"brand", "registered_domain", "url_category"}
            if not required.issubset(reader.fieldnames or []):
                return registry
            services = {}
            for row in reader:
                domain = (row.get("registered_domain") or "").strip().lower().rstrip(".")
                brand = (row.get("brand") or "").strip()
                kind = row.get("url_category")
                if kind not in {"official", "messenger"} or not brand:
                    continue
                if not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", domain):
                    continue
                if "." not in domain or any(not label or label.startswith("-") or label.endswith("-") for label in domain.split(".")):
                    continue
                key = (kind, domain)
                service = services.setdefault(key, {
                    "brand": brand, "aliases": [], "domains": [domain],
                    "category": row.get("service_group", ""),
                })
                aliases = [brand]
                # Preserve curated synonyms only for the same brand and domain.
                for seed in seeds.get(f"{kind}_services", []):
                    if domain in seed.get("domains", []) and brand in [seed.get("brand"), *seed.get("aliases", [])]:
                        aliases.extend(seed.get("aliases", []))
                service["aliases"] = list(dict.fromkeys([*service["aliases"], *aliases]))
            for (kind, _), service in services.items():
                registry[f"{kind}_services"].append(service)
    except (OSError, UnicodeError, csv.Error):
        # Missing/unreadable CSV must not silently trust the old domain list.
        return {"official_services": [], "messenger_services": []}
    return registry


def lookup_domain(url_or_hostname: str, registry: dict | None = None) -> dict | None:
    host = _hostname(url_or_hostname)
    data = registry if registry is not None else load_domain_registry()
    matches = []
    for kind in ("messenger", "official"):
        for service in data.get(f"{kind}_services", []):
            for domain in service.get("domains", []):
                if domain and _domain_matches(host, domain):
                    matches.append((len(domain), {**service, "kind": kind, "host": host}))
    return max(matches, key=lambda match: match[0])[1] if matches else None


def brand_is_relevant(message: str, domain_match: dict | None) -> bool:
    if not domain_match or domain_match.get("kind") != "official":
        return False
    compact_message = re.sub(r"\s+", "", message).casefold()
    return any(
        re.sub(r"\s+", "", alias).casefold() in compact_message
        for alias in domain_match.get("aliases", [])
    )
