#!/usr/bin/env python3
"""obs-graph.py — Build a knowledge graph from an Obsidian vault.

Scans .md files, extracts wikilinks + frontmatter, builds a NetworkX graph,
computes centrality/community metrics, and exports GraphML + JSON meta + vis.js HTML.

Usage:
    python obs-graph.py --vault ~/Obsidian/myWiki [--output ~/.graph] [--open]
"""

import argparse
import json
import os
import re
import subprocess
import sys
import webbrowser
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import community as community_louvain
import networkx as nx

# --- Constants ---

EXCLUDE_DIRS = {".obsidian", ".git", "templates", ".skills", ".graph", "node_modules"}

PARA_MAP = {
    "00-收件匣": "inbox",
    "10-專案": "project",
    "20-領域": "area",
    "30-資源": "resource",
    "40-標準流程": "sop",
    "90-歸檔": "archive",
}

WIKILINK_RE = re.compile(r"!?\[\[([^\]|#]+)(?:#[^\]|]*)?\s*(?:\|[^\]]+)?\]\]")

FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---", re.DOTALL)


# --- Frontmatter parsing (no pyyaml dependency) ---


def parse_frontmatter(text: str) -> dict:
    """Parse YAML frontmatter from markdown text without pyyaml."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    block = m.group(1)
    result = {}
    for line in block.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip()
        if not val:
            continue
        # Handle list in bracket format: [a, b, c]
        if val.startswith("[") and val.endswith("]"):
            items = [x.strip().strip("'\"") for x in val[1:-1].split(",") if x.strip()]
            result[key] = items
        # Handle boolean
        elif val.lower() in ("true", "false"):
            result[key] = val.lower() == "true"
        # Handle number
        elif re.match(r"^-?\d+(\.\d+)?$", val):
            result[key] = float(val) if "." in val else int(val)
        # Handle quoted string
        elif (val.startswith('"') and val.endswith('"')) or (
            val.startswith("'") and val.endswith("'")
        ):
            result[key] = val[1:-1]
        else:
            result[key] = val
    return result


def detect_para(rel_path: str) -> str:
    """Detect PARA category from relative path."""
    for prefix, category in PARA_MAP.items():
        if prefix in rel_path:
            return category
    return "unknown"


# --- Vault scanning ---


def scan_vault(vault_path: Path) -> list[dict]:
    """Scan vault for .md files and extract metadata."""
    notes = []
    for root, dirs, files in os.walk(vault_path):
        # Prune excluded directories
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for fname in files:
            if not fname.endswith(".md"):
                continue
            fpath = Path(root) / fname
            rel = str(fpath.relative_to(vault_path))
            title = fname[:-3]  # Remove .md
            try:
                text = fpath.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                text = ""

            fm = parse_frontmatter(text)
            wikilinks = WIKILINK_RE.findall(text)
            # Clean up wikilink targets
            wikilinks = [w.strip() for w in wikilinks if w.strip()]

            notes.append(
                {
                    "title": title,
                    "path": rel,
                    "para": fm.get("para_category", detect_para(rel)),
                    "quality_score": fm.get("quality_score", 0),
                    "compiled": fm.get("compiled", False),
                    "tags": fm.get("tags", []),
                    "connections": fm.get("connections", []),
                    "wikilinks": wikilinks,
                }
            )
    return notes


# --- Graph building ---


def build_graph(notes: list[dict]) -> nx.DiGraph:
    """Build a directed graph from vault notes."""
    G = nx.DiGraph()
    title_map = {}  # lowercase title -> canonical title

    # Add all real nodes first
    for note in notes:
        G.add_node(
            note["title"],
            path=note["path"],
            para=note["para"],
            quality_score=note["quality_score"],
            compiled=note["compiled"],
            exists=True,
        )
        title_map[note["title"].lower()] = note["title"]

    # Add edges
    for note in notes:
        src = note["title"]

        # Wikilink edges
        for target in note["wikilinks"]:
            resolved = title_map.get(target.lower())
            if resolved:
                if resolved != src:
                    G.add_edge(src, resolved, edge_type="wikilink")
            else:
                # Unresolved target — create ghost node
                if not G.has_node(target):
                    G.add_node(target, path="", para="unresolved", quality_score=0,
                               compiled=False, exists=False)
                    title_map[target.lower()] = target
                G.add_edge(src, target, edge_type="wikilink")

        # Connection edges (from frontmatter)
        for conn in note["connections"]:
            conn_str = str(conn).strip()
            if not conn_str:
                continue
            resolved = title_map.get(conn_str.lower())
            if resolved:
                if resolved != src:
                    G.add_edge(src, resolved, edge_type="connection")
            else:
                if not G.has_node(conn_str):
                    G.add_node(conn_str, path="", para="unresolved", quality_score=0,
                               compiled=False, exists=False)
                    title_map[conn_str.lower()] = conn_str
                G.add_edge(src, conn_str, edge_type="connection")

    return G


# --- Metrics ---


def compute_metrics(G: nx.DiGraph) -> dict:
    """Compute graph metrics and identify special nodes."""
    U = G.to_undirected()

    # Basic stats
    n_nodes = G.number_of_nodes()
    n_edges = G.number_of_edges()
    density = nx.density(G) if n_nodes > 1 else 0.0

    # Components
    components = list(nx.connected_components(U))
    n_components = len(components)
    largest_comp = max(len(c) for c in components) if components else 0

    # Centrality
    deg_cent = nx.degree_centrality(U) if n_nodes > 1 else {}
    bet_cent = nx.betweenness_centrality(U) if n_nodes > 1 else {}

    # Community detection (Louvain) — needs at least 1 edge
    if U.number_of_edges() > 0:
        partition = community_louvain.best_partition(U)
    else:
        partition = {node: 0 for node in U.nodes()}

    # Existing nodes only
    existing = [n for n, d in G.nodes(data=True) if d.get("exists", True)]

    # God Nodes: top 10 by degree centrality
    god_nodes = sorted(
        [(n, deg_cent.get(n, 0)) for n in existing],
        key=lambda x: x[1],
        reverse=True,
    )[:10]

    # Islands: degree == 0
    islands = [n for n in existing if U.degree(n) == 0]

    # Bridges: top 5 by betweenness
    bridges = sorted(
        [(n, bet_cent.get(n, 0)) for n in existing],
        key=lambda x: x[1],
        reverse=True,
    )[:5]

    # Communities summary
    comm_members = {}
    for node, comm_id in partition.items():
        comm_members.setdefault(comm_id, []).append(node)

    communities = []
    for comm_id, members in sorted(comm_members.items(), key=lambda x: -len(x[1])):
        # Top notes by degree within community
        top = sorted(members, key=lambda n: deg_cent.get(n, 0), reverse=True)[:3]
        communities.append({"id": comm_id, "size": len(members), "top_notes": top})

    # Reclassification suggestions
    reclass = []
    for n in existing:
        dc = deg_cent.get(n, 0)
        para = G.nodes[n].get("para", "unknown")
        if dc > 0.1 and para in ("resource", "inbox"):
            suggested = "area" if dc < 0.3 else "project"
            reclass.append(
                {
                    "name": n,
                    "current_para": para,
                    "suggested_para": suggested,
                    "reason": f"degree centrality {dc:.2f}, acts as knowledge hub",
                }
            )

    # PARA distribution
    para_dist = Counter()
    for n, d in G.nodes(data=True):
        para_dist[d.get("para", "unknown")] += 1

    # Bridge community info
    bridge_details = []
    for n, bc in bridges:
        node_comm = partition.get(n, -1)
        # Find communities of neighbors
        neighbor_comms = set()
        for nb in U.neighbors(n):
            c = partition.get(nb, -1)
            if c != node_comm:
                neighbor_comms.add(c)
        bridged = sorted(neighbor_comms)[:2] if neighbor_comms else [node_comm]
        bridge_details.append(
            {
                "name": n,
                "path": G.nodes[n].get("path", ""),
                "betweenness": round(bc, 4),
                "communities_bridged": bridged,
            }
        )

    return {
        "stats": {
            "nodes": n_nodes,
            "edges": n_edges,
            "density": round(density, 6),
            "connected_components": n_components,
            "largest_component_size": largest_comp,
        },
        "communities": communities,
        "god_nodes": [
            {
                "name": n,
                "path": G.nodes[n].get("path", ""),
                "degree": U.degree(n),
                "community": partition.get(n, -1),
                "para": G.nodes[n].get("para", "unknown"),
            }
            for n, _ in god_nodes
        ],
        "islands": [
            {
                "name": n,
                "path": G.nodes[n].get("path", ""),
                "para": G.nodes[n].get("para", "unknown"),
            }
            for n in islands
        ],
        "bridges": bridge_details,
        "reclassification_suggestions": reclass,
        "para_distribution": dict(para_dist),
        "partition": partition,
        "degree_centrality": deg_cent,
    }


# --- Export ---


def export_graph(G: nx.DiGraph, metrics: dict, vault_path: Path, output_dir: Path):
    """Export graph to GraphML, JSON meta, and HTML."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # GraphML
    graphml_path = output_dir / "knowledge-graph.graphml"
    nx.write_graphml(G, str(graphml_path))

    # JSON meta
    meta = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "vault_path": str(vault_path.resolve()),
        "stats": metrics["stats"],
        "communities": metrics["communities"],
        "god_nodes": metrics["god_nodes"],
        "islands": metrics["islands"],
        "bridges": metrics["bridges"],
        "reclassification_suggestions": metrics["reclassification_suggestions"],
        "para_distribution": metrics["para_distribution"],
    }
    meta_path = output_dir / "graph-meta.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    # HTML (via Jinja2 template)
    script_dir = Path(__file__).parent
    template_path = script_dir / "templates" / "graph-template.html"
    if template_path.exists():
        try:
            from jinja2 import Template

            template_text = template_path.read_text(encoding="utf-8")
            template = Template(template_text)

            # Prepare graph data for vis.js
            partition = metrics.get("partition", {})
            deg_cent = metrics.get("degree_centrality", {})
            nodes_data = []
            for n, d in G.nodes(data=True):
                nodes_data.append(
                    {
                        "id": n,
                        "label": n,
                        "para": d.get("para", "unknown"),
                        "path": d.get("path", ""),
                        "quality": d.get("quality_score", 0),
                        "exists": d.get("exists", True),
                        "community": partition.get(n, 0),
                        "centrality": round(deg_cent.get(n, 0), 4),
                        "degree": G.degree(n),
                    }
                )
            edges_data = []
            for u, v, d in G.edges(data=True):
                edges_data.append(
                    {"from": u, "to": v, "type": d.get("edge_type", "wikilink")}
                )

            html = template.render(
                nodes=json.dumps(nodes_data, ensure_ascii=False),
                edges=json.dumps(edges_data, ensure_ascii=False),
                meta=json.dumps(meta, ensure_ascii=False, indent=2),
                generated_at=meta["generated_at"],
            )
            html_path = output_dir / "knowledge-graph.html"
            html_path.write_text(html, encoding="utf-8")
        except Exception as e:
            print(f"Warning: HTML generation failed: {e}", file=sys.stderr)
    else:
        print(
            f"Warning: Template not found at {template_path}, skipping HTML generation.",
            file=sys.stderr,
        )

    return meta


# --- CLI ---


def print_summary(meta: dict):
    """Print terminal summary."""
    s = meta["stats"]
    print(f"\nKnowledge Graph Generated")
    print(f"  Nodes: {s['nodes']} | Edges: {s['edges']} | Density: {s['density']:.4f}")
    print(
        f"  Communities: {len(meta['communities'])} | Components: {s['connected_components']}"
    )

    if meta["god_nodes"]:
        gods = ", ".join(
            f"{g['name']} (degree {g['degree']})" for g in meta["god_nodes"][:5]
        )
        print(f"  God Nodes: {gods}")

    print(f"  Islands: {len(meta['islands'])} notes with no connections")

    if meta["bridges"]:
        br = ", ".join(
            f"{b['name']} (betweenness {b['betweenness']:.3f})"
            for b in meta["bridges"][:3]
        )
        print(f"  Bridges: {br}")

    if meta["reclassification_suggestions"]:
        print(f"  Reclassification suggestions: {len(meta['reclassification_suggestions'])}")

    print(f"  Output: {meta.get('_output_dir', 'N/A')}")


def main():
    parser = argparse.ArgumentParser(description="Build knowledge graph from Obsidian vault")
    parser.add_argument("--vault", required=True, help="Path to Obsidian vault root")
    parser.add_argument("--output", help="Output directory (default: {vault}/.graph/)")
    parser.add_argument("--open", action="store_true", help="Open HTML in browser")
    args = parser.parse_args()

    vault_path = Path(args.vault).expanduser().resolve()
    if not vault_path.is_dir():
        print(f"Error: Vault path does not exist: {vault_path}", file=sys.stderr)
        sys.exit(1)

    output_dir = Path(args.output).expanduser().resolve() if args.output else vault_path / ".graph"

    # Scan
    print(f"Scanning vault: {vault_path}")
    notes = scan_vault(vault_path)
    print(f"  Found {len(notes)} notes")

    # Build graph
    G = build_graph(notes)

    # Compute metrics
    metrics = compute_metrics(G)

    # Export
    meta = export_graph(G, metrics, vault_path, output_dir)
    meta["_output_dir"] = str(output_dir)

    # Summary
    print_summary(meta)

    # Open HTML
    if args.open:
        html_path = output_dir / "knowledge-graph.html"
        if html_path.exists():
            webbrowser.open(str(html_path))
        else:
            print("Warning: HTML file not generated, cannot open.", file=sys.stderr)


if __name__ == "__main__":
    main()
