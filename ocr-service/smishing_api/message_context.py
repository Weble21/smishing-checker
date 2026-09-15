"""Shared, label-free message/domain features for training and serving."""
from __future__ import annotations

from urllib.parse import urlsplit

from .domain_registry import brand_is_relevant, load_domain_registry, lookup_domain
from .url_analysis import extract_urls, normalize_url, URL_PATTERN

INPUT_SCHEMA = "message-domain-v1"


def domain_context(message: str, registry: dict | None = None) -> str:
    registry = load_domain_registry() if registry is None else registry
    # A brand in a URL path/query must not count as a claim made by the SMS.
    body = URL_PATTERN.sub(" ", message)
    mentioned = [service for service in registry.get("official_services", [])
                 if brand_is_relevant(body, {**service, "kind": "official"})]
    brands = sorted({service["brand"] for service in mentioned})
    entries = []
    relations = set()
    for raw_url in extract_urls(message):
        try:
            url = normalize_url(raw_url)
            host = urlsplit(url).hostname or ""
        except ValueError:
            entries.append("주소해석실패")
            relations.add("주소해석실패")
            continue
        match = lookup_domain(url, registry)
        if match and match["kind"] == "messenger":
            relation = "메신저링크"
        elif match and mentioned:
            relation = "기관일치" if brand_is_relevant(body, match) else "다른기관도메인"
        elif match:
            relation = "공식목록등록_언급기관없음"
        else:
            relation = "공식목록미확인"
        relations.add(relation)
        entries.append(f"{host}: {relation}")
    # Relationships first: preserve evidence about later URLs before verbose hosts.
    return ("언급기관=" + (", ".join(brands) or "미확인")
            + "; 링크관계=" + (", ".join(sorted(relations)) or "링크없음")
            + "; 호스트=" + " | ".join(entries))


def encode_message(tokenizer, message: str, *, return_tensors=None):
    # Reserve up to 96 tokens for domain evidence so a long SMS cannot truncate it away.
    context_ids = tokenizer(domain_context(message), add_special_tokens=False)["input_ids"][:96]
    body_ids = tokenizer(message, add_special_tokens=False)["input_ids"]
    available = 256 - tokenizer.num_special_tokens_to_add(pair=True) - len(context_ids)
    return tokenizer.prepare_for_model(
        context_ids, pair_ids=body_ids[:available], padding=False,
        return_tensors=return_tensors, return_attention_mask=True,
        prepend_batch_axis=return_tensors is not None,
    )
