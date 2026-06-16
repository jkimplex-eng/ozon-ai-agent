from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from rich.markup import escape

from ozon_agent.skills.ozon_api.swagger_models import (
    EndpointCategory,
    OzonApiEndpoint,
    SwaggerDocument,
    SwaggerLoaderError,
    SwaggerValidationError,
)
from ozon_agent.skills.skill_loader import SkillNotFoundError, get_skill

_SWAGGER_CACHE: SwaggerDocument | None = None


def load_swagger(swagger_path: Path | None = None) -> SwaggerDocument:
    global _SWAGGER_CACHE
    if swagger_path is not None:
        _SWAGGER_CACHE = _read_swagger(swagger_path)
        return _SWAGGER_CACHE
    if _SWAGGER_CACHE is None:
        _SWAGGER_CACHE = _read_swagger(swagger_path)
    return _SWAGGER_CACHE


def reload_swagger(swagger_path: Path | None = None) -> SwaggerDocument:
    global _SWAGGER_CACHE
    _SWAGGER_CACHE = _read_swagger(swagger_path)
    return _SWAGGER_CACHE


def validate_swagger(payload: dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise SwaggerValidationError("Swagger payload must be a mapping")
    version = payload.get("openapi") or payload.get("swagger")
    if not isinstance(version, str) or not version.strip():
        raise SwaggerValidationError("Swagger version is missing")
    info = payload.get("info")
    if not isinstance(info, dict):
        raise SwaggerValidationError("Swagger info section is missing")
    title = info.get("title")
    if not isinstance(title, str) or not title.strip():
        raise SwaggerValidationError("Swagger info.title is missing")
    paths = payload.get("paths")
    if not isinstance(paths, dict) or not paths:
        raise SwaggerValidationError("Swagger paths section is missing or empty")


def get_swagger_version(swagger_path: Path | None = None) -> str:
    return load_swagger(swagger_path).version


def _read_swagger(swagger_path: Path | None) -> SwaggerDocument:
    resolved_path = swagger_path or _resolve_swagger_path()
    if not resolved_path.exists():
        raise SwaggerLoaderError(f"Swagger file not found: {resolved_path}")
    try:
        payload = json.loads(resolved_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SwaggerLoaderError(f"Failed to parse swagger.json: {exc}") from exc

    validate_swagger(payload)
    info = payload["info"]
    endpoints = _build_endpoints(payload)
    tag_groups = _build_tag_groups(payload)
    return SwaggerDocument(
        version=str(payload.get("openapi") or payload.get("swagger")),
        title=str(info.get("title", "")),
        description=str(info.get("description", "")),
        endpoints=endpoints,
        tag_groups=tag_groups,
        raw=payload,
    )


def _resolve_swagger_path() -> Path:
    try:
        skill = get_skill("ozon_api")
        return skill.path / "swagger.json"
    except SkillNotFoundError:
        return Path(__file__).resolve().parents[4] / "skills" / "ozon_api" / "swagger.json"


def _build_tag_groups(payload: dict[str, Any]) -> dict[str, list[str]]:
    groups = payload.get("x-tagGroups", [])
    if not isinstance(groups, list):
        return {}
    result: dict[str, list[str]] = {}
    for group in groups:
        if not isinstance(group, dict):
            continue
        name = group.get("name")
        tags = group.get("tags")
        if isinstance(name, str) and isinstance(tags, list):
            result[name] = [str(tag) for tag in tags]
    return result


def _build_endpoints(payload: dict[str, Any]) -> list[OzonApiEndpoint]:
    paths = payload.get("paths", {})
    components = payload.get("components", {})
    endpoints: list[OzonApiEndpoint] = []
    seen_names: set[str] = set()
    for path, methods in paths.items():
        if not isinstance(path, str) or not isinstance(methods, dict):
            continue
        for method, operation in methods.items():
            if method.lower() not in {"get", "post", "put", "patch", "delete"}:
                continue
            if not isinstance(operation, dict):
                continue
            endpoint_name = _derive_endpoint_name(path)
            if endpoint_name in seen_names:
                endpoint_name = f"{endpoint_name}-{method.lower()}"
            seen_names.add(endpoint_name)
            endpoint = OzonApiEndpoint(
                name=endpoint_name,
                path=path,
                method=method.upper(),
                summary=escape(str(operation.get("summary", ""))),
                description=escape(str(operation.get("description", ""))),
                tags=[str(tag) for tag in operation.get("tags", []) if isinstance(tag, str)],
                request_schema=_extract_request_schema(operation, components),
                response_schema=_extract_response_schema(operation, components),
                category=_categorize_endpoint(path, operation),
            )
            endpoints.append(endpoint)
    endpoints.sort(key=lambda item: (item.category.value, item.name, item.method))
    return endpoints


def _derive_endpoint_name(path: str) -> str:
    parts = [part for part in path.split("/") if part and not part.startswith("v")]
    normalized_parts = [
        re.sub(r"[^a-zA-Z0-9]+", "-", part).strip("-").lower()
        for part in parts
    ]
    return "-".join(part for part in normalized_parts if part) or "unknown-endpoint"


def _extract_request_schema(
    operation: dict[str, Any],
    components: dict[str, Any],
) -> dict[str, Any]:
    request_body = operation.get("requestBody")
    if not isinstance(request_body, dict):
        return {}
    resolved_body = _resolve_refs(request_body, components)
    content = resolved_body.get("content")
    if not isinstance(content, dict):
        return {}
    json_body = content.get("application/json")
    if not isinstance(json_body, dict):
        return {}
    schema = json_body.get("schema")
    if not isinstance(schema, dict):
        return {}
    return _resolve_refs(schema, components)


def _extract_response_schema(
    operation: dict[str, Any],
    components: dict[str, Any],
) -> dict[str, Any]:
    responses = operation.get("responses")
    if not isinstance(responses, dict):
        return {}
    preferred_codes = ["200", "201", "202", "default"]
    for code in preferred_codes + list(responses):
        response = responses.get(code)
        if not isinstance(response, dict):
            continue
        resolved_response = _resolve_refs(response, components)
        content = resolved_response.get("content")
        if not isinstance(content, dict):
            continue
        json_body = content.get("application/json")
        if not isinstance(json_body, dict):
            continue
        schema = json_body.get("schema")
        if not isinstance(schema, dict):
            continue
        return _resolve_refs(schema, components)
    return {}


def _resolve_refs(
    payload: dict[str, Any],
    components: dict[str, Any],
    seen_refs: set[str] | None = None,
) -> dict[str, Any]:
    active_refs = seen_refs or set()
    if "$ref" in payload:
        ref_value = payload["$ref"]
        if isinstance(ref_value, str) and ref_value.startswith("#/components/"):
            if ref_value in active_refs:
                return {"$ref": ref_value, "x-cyclic-ref": True}
            resolved_ref = _lookup_ref(ref_value, components)
            if resolved_ref is not None:
                return _resolve_refs(resolved_ref, components, active_refs | {ref_value})
        return {}

    resolved: dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(value, dict):
            resolved[key] = _resolve_refs(value, components, active_refs)
        elif isinstance(value, list):
            resolved[key] = [
                _resolve_refs(item, components, active_refs) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            resolved[key] = value
    return resolved


def _lookup_ref(ref_value: str, components: dict[str, Any]) -> dict[str, Any] | None:
    parts = ref_value.removeprefix("#/components/").split("/")
    current: Any = components
    for part in parts:
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current if isinstance(current, dict) else None


def _categorize_endpoint(path: str, operation: dict[str, Any]) -> EndpointCategory:
    tokens = " ".join(
        [
            path.lower(),
            str(operation.get("summary", "")).lower(),
            str(operation.get("description", "")).lower(),
            " ".join(str(tag).lower() for tag in operation.get("tags", [])),
        ]
    )
    rules: list[tuple[EndpointCategory, list[str]]] = [
        (EndpointCategory.STOCKS, ["stock", "warehouse remains"]),
        (EndpointCategory.PRICES, ["price", "pricing"]),
        (EndpointCategory.ORDERS, ["posting", "order", "delivery", "shipment", "posting"]),
        (EndpointCategory.ANALYTICS, ["analytics", "report"]),
        (EndpointCategory.FINANCE, ["finance", "transaction", "receipt", "commission"]),
        (EndpointCategory.RETURNS, ["return", "cancellation"]),
        (EndpointCategory.REVIEWS, ["review", "question", "answer"]),
        (EndpointCategory.FBO, ["fbo", "supply"]),
        (EndpointCategory.FBS, ["fbs", "rfbs", "fbswarehouse"]),
        (EndpointCategory.PRODUCTS, ["product", "category", "barcode", "brand"]),
    ]
    for category, keywords in rules:
        if any(keyword in tokens for keyword in keywords):
            return category
    return EndpointCategory.OTHER
