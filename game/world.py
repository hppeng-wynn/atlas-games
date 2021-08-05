# Type annotations without import
from __future__ import annotations
from typing import List
from queue import SimpleQueue
from game.players import Player, Team

class World:
    """
    Lol looks like this is gonna be a data class
    """

    def __init__(self, world_data: dict):
        """
        Populate the game world object.
        Its just a graph.
        """
        self._nodes = dict()
        self._name_nodes = dict()
        self._starting_nodes = world_data["starting"]
        for node_id, node_name in world_data["nodes"].items():
            edges = world_data["connections"][node_id]
            node_id = int(node_id)
            node = GraphNode(node_id, node_name, edges, self)
            self._nodes[node_id] = node
            self._name_nodes[node_name] = node

    def get_starting_nodes(self):
        return tuple(self._starting_nodes)

    def node(self, node_id):
        return self._nodes[node_id]

    def node_from_name(self, node_name):
        return self._name_nodes.get(node_name, None)

    def players_near(self, node: GraphNode, distance: int, 
                            filter_func = lambda player: True):
        q = SimpleQueue()
        q.put((node, 0))
        retval = []
        visited = set()
        while not q.empty():
            cur, dist = q.get()
            if cur.id in visited:
                continue
            retval += list(filter(filter_func, sorted(cur.active_players.values(), key=lambda p: p.name)))
            visited.add(cur.id)
            if dist < distance:
                for neighbor in cur.edges:
                    q.put((self.node(neighbor), dist+1))

        return retval

class GraphNode:
    def __init__(self, node_id: int, name: str, edges: List[int], graph: World):
        self._graph = graph
        self.id: int = node_id
        self.name: str = name
        self.edges: List[int] = edges
        self.active_players = dict()
        self.active_teams = dict()

    def random_neighbor(self, rand):
        return self._graph.node(rand.choice(self.edges))
