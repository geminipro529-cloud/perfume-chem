"""Tests for engine.graphs.accord_graph."""

from __future__ import annotations
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.graphs.accord_graph import (
    AccordGraph,
    AccordNode,
    AccordEdge,
    build_functional_graph,
    rich_role_vector,
    REINFORCEMENT,
    TEMPORAL_HANDOFF,
)


def test_add_node():
    graph = AccordGraph()
    node = AccordNode("n1", "Iso E Super", "character", "base", 450, 450, 0.05, ("drydown",))
    graph.add_node(node)
    assert len(graph._nodes) == 1


def test_add_edge():
    graph = AccordGraph()
    n1 = AccordNode("n1", "Bergamot", "character", "top", 50, 50, 40.0, ("opening",))
    n2 = AccordNode("n2", "Hedione", "radiance", "heart", 300, 300, 0.09, ("heart",))
    graph.add_node(n1)
    graph.add_node(n2)
    edge = AccordEdge("e1", "n1", "n2", REINFORCEMENT, 0.5, "Both fresh")
    graph.add_edge(edge)
    assert len(graph._edges) == 1


def test_build_functional_graph():
    materials = [
        {
            "name": "Bergamot",
            "role": "character",
            "note": "citrus",
            "dose_ul": 50,
            "vp_pa": 40.0,
            "time_windows": ("opening",),
        },
        {
            "name": "Hedione",
            "role": "radiance",
            "note": "floral",
            "dose_ul": 300,
            "vp_pa": 0.09,
            "time_windows": ("top",),
        },
        {
            "name": "Iso E Super",
            "role": "structural",
            "note": "woody",
            "dose_ul": 450,
            "vp_pa": 0.15,
            "time_windows": ("heart",),
        },
    ]
    graph = build_functional_graph(materials)
    assert len(graph._nodes) == 3
    # Should create temporal handoff edges between adjacent time windows
    assert len(graph._edges) > 0


def test_rich_role_vector():
    rv = rich_role_vector("Hedione", "radiance amplifier", "heart", 300, 0.09)
    assert isinstance(rv, dict)
    assert len(rv) >= 4
    assert any(k.startswith("texture_") for k in rv)
    assert any(k.startswith("temporal_") for k in rv)


def test_cytoscape_export():
    graph = AccordGraph()
    n1 = AccordNode("n1", "A", "test", "top", 10, 10, 1.0, ("opening",))
    graph.add_node(n1)
    cyto = graph.to_cytoscape()
    assert "nodes" in cyto
    assert "edges" in cyto
    assert len(cyto["nodes"]) == 1
