"""Semantic JSON-LD regression checks."""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any

from .models import Finding, Severity


def schema_nodes(values: Iterable[Any]) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    for value in values:
        if isinstance(value, list):
            nodes.extend(schema_nodes(value))
        elif isinstance(value, dict):
            graph = value.get("@graph")
            if isinstance(graph, list):
                context = value.get("@context")
                for node in schema_nodes(graph):
                    if context is not None and "@context" not in node:
                        node = {"@context": context, **node}
                    nodes.append(node)
            else:
                nodes.append(value)
    return nodes


def _types(node: dict[str, Any]) -> set[str]:
    value = node.get("@type", [])
    if isinstance(value, str):
        return {value}
    if isinstance(value, list):
        return {str(item) for item in value}
    return set()


def _base_identity(node: dict[str, Any], index: int) -> str:
    if node.get("@id"):
        return f"id:{node['@id']}"
    label = node.get("name") or node.get("headline")
    types = ",".join(sorted(_types(node))) or "untyped"
    return f"type:{types}|label:{label}" if label else f"type:{types}|index:{index}"


def _index_nodes(nodes: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for index, node in enumerate(nodes):
        base = _base_identity(node, index)
        identity = base
        suffix = 2
        while identity in indexed:
            identity = f"{base}#{suffix}"
            suffix += 1
        indexed[identity] = node
    return indexed


def _flatten(value: Any, prefix: str = "$") -> dict[str, Any]:
    if isinstance(value, dict):
        flattened: dict[str, Any] = {}
        for key in sorted(value):
            flattened.update(_flatten(value[key], f"{prefix}.{key}"))
        return flattened
    if isinstance(value, list):
        return {
            prefix: json.dumps(
                value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            )
        }
    return {prefix: value}


def compare_jsonld(
    before: Iterable[Any], after: Iterable[Any], *, source: str
) -> list[Finding]:
    before_nodes = _index_nodes(schema_nodes(before))
    after_nodes = _index_nodes(schema_nodes(after))
    findings: list[Finding] = []

    if not before_nodes:
        findings.append(
            Finding(
                "jsonld_diff.baseline_empty",
                Severity.ERROR,
                "baseline contains no JSON-LD nodes",
                source,
            )
        )
        return findings
    if not after_nodes:
        findings.append(
            Finding(
                "jsonld_diff.all_nodes_removed",
                Severity.ERROR,
                "candidate contains no JSON-LD nodes",
                source,
                suggestion="Restore the structured-data graph before publication.",
            )
        )
        return findings

    for identity in sorted(before_nodes.keys() - after_nodes.keys()):
        findings.append(
            Finding(
                "jsonld_diff.node_removed",
                Severity.ERROR,
                f"JSON-LD node was removed: {identity}",
                source,
                evidence=identity,
            )
        )
    for identity in sorted(after_nodes.keys() - before_nodes.keys()):
        findings.append(
            Finding(
                "jsonld_diff.node_added",
                Severity.INFO,
                f"JSON-LD node was added: {identity}",
                source,
                evidence=identity,
            )
        )

    for identity in sorted(before_nodes.keys() & after_nodes.keys()):
        old_node = before_nodes[identity]
        new_node = after_nodes[identity]
        removed_types = sorted(_types(old_node) - _types(new_node))
        if removed_types:
            findings.append(
                Finding(
                    "jsonld_diff.type_removed",
                    Severity.ERROR,
                    f"node {identity} lost @type values: {', '.join(removed_types)}",
                    source,
                    evidence=identity,
                )
            )
        old_values = _flatten(old_node)
        new_values = _flatten(new_node)
        for pointer in sorted(old_values.keys() - new_values.keys()):
            if pointer in {"$.@type", "$.@context"}:
                continue
            findings.append(
                Finding(
                    "jsonld_diff.property_removed",
                    Severity.WARNING,
                    f"node {identity} lost property {pointer}",
                    source,
                    evidence=f"{identity} {pointer}",
                )
            )
        for pointer in sorted(old_values.keys() & new_values.keys()):
            if old_values[pointer] != new_values[pointer] and pointer not in {
                "$.@context",
                "$.@type",
            }:
                findings.append(
                    Finding(
                        "jsonld_diff.value_changed",
                        Severity.INFO,
                        f"node {identity} changed {pointer}",
                        source,
                        evidence=f"{old_values[pointer]!r} -> {new_values[pointer]!r}",
                    )
                )
    return findings
