from __future__ import annotations

if __name__ == "__main__":
    import sys
    import os
    path = os.path.join(os.path.dirname(__file__), '..')
    sys.path.append(path)

from typing import List
import random

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
EVENT_NUM_TRIES = 3

MOVE_CHANCE = 0.7
FOLLOW_TEAM_CHANCE = 0.95

class GameState:
    def __init__(self, world_data: dict, player_data: dict, event_data: dict):
        self._world = World(world_data)
        self._event_data = event_data
        self._teams = []
        self._players = dict()
        self._dead_players = []

        teams_by_name = dict()
        for data in player_data:
            if "team" in data:
                team_name = data["team"]
            else:
                team_name = data["name"]
            if team_name in teams_by_name:
                player_team = teams_by_name[team_name]
            else:
                player_team = Team(len(self._teams), team_name)
                teams_by_name[team_name] = player_team
                self._teams.append(player_team)
                    
            new_player = Player(data["name"], data.get("img", ""), player_team)
            self._players[new_player.name] = new_player
            player_team.players[new_player.name] = new_player
        
        seed = 0# random.randrange(2**31)
        print(f"Random seed: {seed}")
        self._rng = random.Random(seed)

        # Distribute teams
        # TODO: distribute nicely
        start_points = self._world.get_starting_nodes()
        for team in self._teams:
            start_point = self._world.node(self._rng.choice(start_points))
            team.move_to(start_point)
            for player in team.players.values():
                player.move_to(start_point)

    def get_random_event(self):
        """
        Get a random event weighted by category then uniformly.
        """
        result = self._rng.random()
        event_type = None
        for etype, prob in EVENT_PROBABILITY.items():
            if result < prob:
                event_type = etype
                break
            result -= prob
        if event_type is None:
            # Unlikely event of floating point error
            return get_random_event(self)
        return self._rng.choice(self._event_data[event_type])

    def process_event(self, event, players):
        #TODO bind to frontend
        print(event['text'].format(*players))


    def turn(self):
        for team in self._teams:
            if self._rng.random() < MOVE_CHANCE:
                move_to = team.location.random_neighbor(self._rng)
                team.move_to(move_to)
        for player in self._players.values():
            if self._rng.random() < FOLLOW_TEAM_CHANCE:
                player.move_to(player.team.location)
            else:
                player.move_to(player.location.random_neighbor(self._rng))
                del player.team.players[player.name]
                solo_team = Team(len(self._teams), None, {player.name: player}, player.location)
                player.team = solo_team
                self._teams.append(solo_team)

        players_need_event = sorted(list(self._players.keys()))
        while len(players_need_event):
            event = self.get_random_event()
            player_set = self.fit_event(event, set(players_need_event))
            if player_set is not None:
                self.process_event(event, player_set)
                players_need_event = list(filter(lambda name: name not in player_set, players_need_event))
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

    def fit_event(self, event, remaining_player_set):
        # Select starting player
        if 'location' in event:
            # Location specified infinite radius unsupported.
            target_location = self._world.node_from_name(event['location'])
            if target_location is None:
                return None

            _localized = True
            player_pool = self._world.players_near(target_location, event['radius'],
                        filter_func = lambda p: p.name in remaining_player_set)
            team_pool = sorted([self._teams[i] for i in set(p.team.id for p in player_pool)], key=lambda t: t.id)
        else:
            _localized = event['radius'] == -1
            player_pool = [self._players[p_id] for p_id in remaining_player_set]
            team_pool = sorted(list(self._teams), key=lambda t: t.id) # Copy

        if len(player_pool) < event['num_players']:
            return None
        team_pool.sort(key=lambda team: team.player_count(), reverse=True)

        def pick_team(team_pool, teams_select, nplayer_min):
            index_last = 0
            while index_last < len(team_pool):
                if team_pool[index_last].player_count() < nplayer_min:
                    break
                index_last += 1
            if index_last == 0:
                # No team large enough...
                return None
            possibilities = team_pool[:index_last]
            self._rng.shuffle(possibilities)
            for team in possibilities:
                if team.id not in teams_select:
                    return team
            return None

        for k in range(EVENT_NUM_TRIES):
            localized = _localized
            remaining_players = player_pool
            i = event['num_players']
            player_select = [None]*i
            if len(event['team_list']) > 0:
                teams_select: List[int] = []
                if not localized:
                    team_idx = 1
                    source_team = pick_team(team_pool, teams_select, len(event['team_list'][0]))
                    if source_team is None:
                        # No teams large enough.
                        return None
                    teams_select.append(source_team.id)

                    localized = True
                    remaining_players = self._world.players_near(source_team.location, event['radius'],
                            filter_func = lambda p: p.name in remaining_player_set)
                    remaining_team_pool = sorted([self._teams[i] for i in set(p.team.id for p in remaining_players)], 
                                                    key=lambda t: t.id)
                else:
                    team_idx = 0
                    remaining_team_pool = team_pool
                while team_idx < len(event['team_list']):
                    team = pick_team(remaining_team_pool, teams_select, len(event['team_list'][team_idx]))
                    if team is None:
                        # No teams large enough in this subset.
                        break
                    teams_select.append(team.id)
                    team_idx += 1

                if len(teams_select) != len(event['team_list']):
                    continue
                for team_id, targets in zip(teams_select, event['team_list']):
                    team_players = self._rng.sample(sorted(list(self._teams[team_id].players.keys())), len(targets))
                    for player_name, spot in zip(team_players, targets):
                        try:
                            player_select[spot] = player_name
                        except Exception as e:
                            print(event)
                            raise e
                        i -= 1

                remaining_players = list(filter(lambda p: p.name not in player_select, remaining_players))
                
                complement_filled = 0
                for team_id, player_set in zip(teams_select, event['complement_list']):
                    filtered_player_pool = list(filter(lambda p: p.team.id != team_id, remaining_players))
                    if len(filtered_player_pool) < len(player_set):
                        # Not enough players in the complement set
                        break
                    select_set = (p.name for p in self._rng.sample(remaining_players, len(player_set)))
                    for player_name, spot in zip(select_set, player_set):
                        player_select[spot] = player_name
                        i -= 1
                    remaining_players = list(filter(lambda p: p.name not in select_set, remaining_players))
                    complement_filled += 1

                if complement_filled != len(event['complement_list']):
                    continue
            if len(remaining_players) < i:
                # Not enough players for solos
                continue

            if i > 0:
                solos_set = []
                if not localized:
                    solo_source = self._rng.choice(remaining_players)
                    remaining_players = self._world.players_near(solo_source.location, event['radius'],
                        filter_func = lambda p: p.name in remaining_player_set and p.name not in player_select and p.name != solo_source.name)
                    solos_set.append(solo_source)
                    i -= 1

                if i > 0:
                    if len(remaining_players) < i:
                        # Not enough players for solos
                        continue
                    solos_set = self._rng.sample(remaining_players, i) + solos_set

                for i, v in enumerate(player_select):
                    if v is None:
                        player_select[i] = solos_set.pop(-1).name

            return player_select
        return None

if __name__ == "__main__":
    import json
    #world_data = json.load(open("world_simple.json", 'r'))
    world_data = json.load(open("world_data.json", 'r'))
    event_data = json.load(open("event_data.json", 'r'))
    #player_data = json.load(open("players_simple.json", 'r'))
    player_data = json.load(open("players_full.json", 'r'))
    game = GameState(world_data, player_data, event_data)
    print(game._players)
    game.turn()
    print(game._players)
    game.turn()
