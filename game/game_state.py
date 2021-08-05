from __future__ import annotations

if __name__ == "__main__":
    import sys
    import os
    path = os.path.join(os.path.dirname(__file__), '..')
    sys.path.append(path)

from typing import List

from game.world import World
from game.players import Player, Team

"""
class Event:
    Properties:
    - text: event format text
    - num_players: number of players
    - deaths: list of dying player indices
    - team_list: list of indices that have to match
    - complement_list: list of indices that have to complement those in team_list
    - radius: event radius
    - location: Specific location
"""

EVENT_PROBABILITY = {
        "idle": 0.3,
        "combat": 0.3,
        "bond": 0.2,
        "team": 0.2
    }

class GameState:
    def __init__(self, world_data: dict, player_data: dict, event_data: dict):
        self._world = World(world_data)
        self._event_data = event_data
        self._teams_by_name = dict()
        self._players = []
        for data in player_data:
            player_team = None
            if "team" in player_data:
                team_name = player_data["team"]
                if team_name in self._teams_by_name:
                    player_team = self._teams_by_name[team_name]
                else:
                    player_team = Team(team_name)
                    self._teams_by_name[team_name] = player_team
                    
            new_player = Player(data["name"], data.get("image", ""), player_team)
            self._players.append(new_player)
            if player_team is not None:
                player_team.players.append(new_player)


if __name__ == "__main__":
    import json
    world_data = json.load(open("world_simple.json", 'r'))
    event_data = json.load(open("event_data.json", 'r'))
    player_data = json.load(open("players_simple.json", 'r'))
    game = GameState(world_data, player_data, event_data)
