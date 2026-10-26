from pathlib import Path
import json
from collections import defaultdict


ROOT = Path(__file__).resolve().parents[1]

GRAPH_FILE = ROOT / "graphify-out" / "graph.json"
OUTPUT_FILE = ROOT / "context" / "generated" / "graph_context.md"


COMPONENTS = {
    "Extraction Pipeline": [
        "reality/extraction/",
    ],

    "Classification Layer": [
        "reality/classification/",
    ],

    "Reality Engine": [
        "reality/engine.py",
    ],

    "Orchestrator": [
        "reality/orchestrator.py",
    ],

    "Repository Layer": [
        "reality/repository.py",
    ],

    "Domain Schemas": [
        "reality/schemas.py",
    ],

    "Database Layer": [
        "reality/db.py",
    ],
}

COMPONENT_LOOKUP = {}


for component, patterns in COMPONENTS.items():
    for pattern in patterns:
        COMPONENT_LOOKUP[pattern] = component

def load_graph():
    with open(GRAPH_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def is_test_node(node):
    text = " ".join(
        str(node.get(k, ""))
        for k in (
            "name",
            "path",
            "file",
            "type",
        )
    ).lower()

    return (
        "test" in text
        or "tests/" in text
        or "tests\\" in text
    )


def node_text(node):

    parts = []

    for key in (
        "id",
        "label",
        "source_file",
        "community_name",
        "file_type",
    ):

        value = node.get(key)

        if value:
            parts.append(str(value))

    return " ".join(parts)


def match_component(node, patterns):

    source = node.get("source_file", "")

    return any(
        source.startswith(pattern)
        or source == pattern
        for pattern in patterns
    )


def extract_nodes(graph):
    """
    Supports common graph formats.
    """
    if isinstance(graph, dict):
        if "nodes" in graph:
            return graph["nodes"]

    return []


def extract_edges(graph):
    if isinstance(graph, dict):
        return graph.get("links", [])

    return []


def collect_component_nodes(nodes):
    result = {}

    for component, patterns in COMPONENTS.items():
        matched = [
            n for n in nodes
            if match_component(n, patterns)
        ]

        result[component] = matched

    return result


def summarize_nodes(nodes):

    files = set()
    symbols = set()

    for node in nodes:

        source = node.get("source_file")

        if not source:
            continue

        if source.startswith("tests/"):
            continue


        files.add(source)


        label = node.get("label")

        if not label:
            continue


        if not node.get("_callable"):
            continue


        # حذف private/internal
        if (
            label.startswith("_")
            or label.startswith(".")
        ):
            continue


        # حذف test symbols
        if label.startswith("test_"):
            continue


        label = label.lstrip(".")

        symbols.add(label)


    return {
        "files": sorted(files),
        "symbols": sorted(symbols),
    }



def find_related_edges(component_nodes, edges, node_index):
    """Return unique component-level relationships for a component."""
    component_ids = {
        node.get("id")
        for node in component_nodes
        if node.get("id") is not None
    }

    current_components = {
        name
        for node in component_nodes
        if (name := component_for_node(node)) is not None
    }

    related_components = set()

    for edge in edges:
        source = edge.get("source")
        target = edge.get("target")

        if source in component_ids:
            related_node = node_index.get(target)
        elif target in component_ids:
            related_node = node_index.get(source)
        else:
            continue

        if related_node is None:
            continue

        related_component = component_for_node(related_node)

        if related_component is None:
            continue

        if related_component in current_components:
            continue

        related_components.add(related_component)

    return sorted(related_components)


def write_component(md, name, nodes, edges, node_index):
    summary = summarize_nodes(nodes)

    related_components = find_related_edges(
        nodes,
        edges,
        node_index,
    )

    md.append(f"### {name}\n\n")

    md.append("Purpose:\n")
    md.append(
        "- Structural component extracted from Graphify.\n"
    )

    md.append("\nFiles:\n")
    for file_path in summary["files"][:15]:
        md.append(f"- {file_path}\n")

    md.append("\nCore Symbols:\n")
    for symbol in summary["symbols"][:20]:
        md.append(f"- {symbol}\n")

    md.append("\nRelated Components:\n")
    if related_components:
        for component in related_components:
            md.append(f"- {component}\n")
    else:
        md.append("- None detected\n")

    md.append("\nTests:\n")
    md.append("- See Test Coverage Map.\n\n")


def build_test_section(nodes):

    tests = [
        n for n in nodes
        if is_test_node(n)
    ]

    md = []

    md.append("## Test Coverage Map\n\n")

    grouped = defaultdict(list)

    for test in tests:

        path = (
            test.get("path")
            or test.get("file")
            or test.get("name")
        )

        grouped[path].append(test)


    for path in sorted(grouped):

        md.append(f"### {path}\n")

        for node in grouped[path][:5]:

            name = node.get("name")

            if name:
                md.append(f"- {name}\n")

        md.append("\n")

    return md

def filter_architecture_edges(edges):
    ignored_targets = {
        "json",
        "math",
        "hashlib",
        "sqlite3",
        "datetime",
        "typing",
        "pathlib",
        "os",
        "sys",
    }

    filtered = []

    for edge in edges:
        source = edge.get("source")
        target = edge.get("target")

        if not source or not target:
            continue

        # Remove self loops
        if source == target:
            continue

        # Remove standard library noise
        if target in ignored_targets:
            continue

        # Remove test-only edges
        if "test" in source.lower() or "test" in target.lower():
            continue

        filtered.append(edge)

    return filtered

def build():

    graph = load_graph()

    nodes = extract_nodes(graph)
    edges = extract_edges(graph)
    edges = filter_architecture_edges(edges)

    node_index = {
        node["id"]: node
        for node in nodes
        if "id" in node
    }

    components = collect_component_nodes(nodes)

    md = []

    md.append("# Zehn Graph Context\n\n")

    md.append(
        "Generated from Graphify. "
        "Component-based retrieval context.\n\n"
    )


    md.append("## Overview\n\n")

    md.append(
        f"- Total graph nodes: {len(nodes)}\n"
    )

    md.append(
        f"- Total graph edges: {len(edges)}\n\n"
    )


    md.append("## Components\n\n")

    for name, component_nodes in components.items():

        write_component(
            md,
            name,
            component_nodes,
            edges,
            node_index,
        )


    md.extend(
        build_test_section(nodes)
    )


    md.append("## Architecture Edges\n\n")

    for edge in edges[:50]:

        source = edge.get("source")
        target = edge.get("target")

        md.append(
            f"- {source} → {target}\n"
        )


    md.append("\n## Graph Rules\n\n")

    md.append(
        "- Graph is navigation layer only.\n"
    )

    md.append(
        "- Runtime reality remains authoritative.\n"
    )

    md.append(
        "- Generated context must not modify architecture.\n"
    )


    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            "".join(md)
        )


    print(
        f"Generated: {OUTPUT_FILE}"
    )

def clean_node_id(value):

    if not value:
        return None

    value = value.replace("_", "/")

    return value

def is_noise_dependency(value):

    if not value:
        return True

    noise = (
        "rationale/",
        "/to/",
        "rationale",
        "ast",
        "baseexception",
        "contextlib",
        "collections",
        "datetime",
        "dataclasses",
        "copy",
    )

    return any(
        x in value
        for x in noise
    )

def component_for_node(node):

    source = node.get("source_file", "")

    for pattern, component in COMPONENT_LOOKUP.items():

        if (
            source.startswith(pattern)
            or source == pattern
        ):
            return component

    return None

if __name__ == "__main__":
    build()