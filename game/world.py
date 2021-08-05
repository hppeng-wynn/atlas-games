# Type annotations without import
from __future__ import annotations
from typing import List
from game.players import Player, Team

class World:
    def __init__(self, world_data: dict):
        """
        Populate the game world object.
        Its just a graph.
        """
        self._nodes = dict()
        for node_id, node_name in world_data["nodes"].items():
            edges = world_data["connections"][node_id]
            node_id = int(node_id)
            self._nodes[node_id] = GraphNode(node_id, node_name, edges, self)

class GraphNode:
    def __init__(self, node_id: int, name: str, edges: List[int], graph: World):
        self._graph = graph
        self._id = node_id
        self._name = name
        self._edges = edges

