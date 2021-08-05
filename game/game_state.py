from __future__ import annotations

if __name__ == "__main__":
    import sys
    import os
    path = os.path.join(os.path.dirname(__file__), '..')
    sys.path.append(path)

from typing import List
import random
import copy

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
        "idle": 0.42,
        "accident": 0.03,
        "combat": 0.25,
        "bond": 0.2,
        "team": 0.29,
        "team-accident": 0.1
    }
EVENT_NUM_TRIES = 3

MOVE_CHANCE = 0.7
FOLLOW_TEAM_CHANCE = 0.95

MAX_TEAM_SIZE = 4
TEAM_CHANGE_CHANCE = 0.3

class GameState:
    def __init__(self, world_data: dict, player_data: dict, event_data: dict):
        self._world = World(world_data)
        self._event_data = event_data
        self._teams = []
        self._players = dict()
        self._dead_players = []
        self._turn_counter = 0
        self._event_probability = copy.copy(EVENT_PROBABILITY)
        self._hunt_chance = 0

        teams_by_name = dict()
        for data in sorted(player_data, key = lambda d: d["name"]):
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
        
        seed = 542363412#random.randrange(2**31)
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
        for etype, prob in self._event_probability.items():
            if result < prob:
                event_type = etype
                break
            result -= prob
        if event_type is None:
            # Unlikely event of floating point error
            return get_random_event(self)
        return (self._rng.choice(self._event_data[event_type]), event_type)

    def try_merge_teams(self, players: List[Player]):
        team_pool = sorted([self._teams[i] for i in set(p.team.id for p in players)], key=lambda t: (t.player_count(), -t.id))
        while len(team_pool) > 1:
            if team_pool[-1].player_count() == MAX_TEAM_SIZE:
                team_pool.pop(-1)
                continue
            if team_pool[0].player_count() + team_pool[1].player_count() < MAX_TEAM_SIZE:
                team_pool[0].merge_into(team_pool[1])
                team_pool.pop(0)
                team_pool.append(team_pool.pop(0))
                team_pool.sort(key=lambda t: (t.player_count(), -t.id))
                continue
            smallest = team_pool.pop(0)
            for player in self._rng.sample(players, len(players)):
                if player.name in smallest.players:
                    if self._rng.random() < TEAM_CHANGE_CHANCE:
                        player.move_teams(team_pool[0])
                        team_pool.sort(key=lambda t: (t.player_count(), -t.id))
                        break

    def process_event(self, event, event_type, players: List[str]):
        if event_type == 'bond':
            self.try_merge_teams([self._players[n] for n in players])
        
        event_txt = event['text'].format(*players)
        if len(event['deaths']) > 0:
            kill_credit = [True] * len(players)
            for index in event['deaths']:
                killed_player = self._players[players[index]]
                killed_player.deathmsg = event_txt
                killed_player.remove()
                del self._players[players[index]]
                self._dead_players.append(killed_player)
                kill_credit[index] = False
            for i, alive in enumerate(kill_credit):
                if alive:
                    self._players[players[i]].kills += 1

        #TODO bind to frontend
        print(event_txt)


    def turn(self):
        print(f"Day {self._turn_counter}")
        if self._turn_counter == 3:
            self._event_probability.update({
                    "idle": 0.32,
                    "combat": 0.35,
                })
        if self._turn_counter == 10:
            self._event_probability.update({
                    "idle": 0.12,
                    "combat": 0.55,
                })
        if self._turn_counter >= 3:
            self._hunt_chance += 0.05
        self._turn_counter += 1

        event_list = []

        hunting_players = set()
        for team in self._teams:
            if len(team.players) > 0:
                if team.hunt == 0 and self._rng.random() < self._hunt_chance:
                    team.hunt += int(5*max(1, self._hunt_chance))
                    hunting_players.update(team.players.keys())
                    player_names = sorted(team.players.keys())
                    if len(team.players) == 1:
                        event_text = "{0} hunts for other tributes..."
                    elif len(team.players) == 2:
                        event_text = "{0} and {1} hunt for other tributes."
                    else:
                        event_text = "{"+"}, {".join(str(x) for x in range(len(player_names) - 1))+"}, and {"+str(len(player_names) - 1)+"} hunt for other tributes."
                    event_list.append(({
                            'text': event_text, 
                            'deaths': []
                        }, 'hunt', player_names))
                    continue;
                if team.hunt > 0:
                    def has_enemy(node):
                        for player in node.active_players.values():
                            if player.team.id != team.id:
                                return True
                        return False
                    hunt_path = self._world.path_to(team.location, has_enemy)
                    if hunt_path is not None and len(hunt_path) > 0:
                        move_to = hunt_path[0]
                        team.move_to(move_to)
                        team.hunt -= 1
                        continue
                if self._rng.random() < MOVE_CHANCE:
                    move_to = team.location.random_neighbor(self._rng)
                    team.move_to(move_to)
        for player in sorted(self._players.values(), key=lambda p: p.name):
            if self._rng.random() < FOLLOW_TEAM_CHANCE:
                player.move_to(player.team.location)
            else:
                player.move_to(player.location.random_neighbor(self._rng))
                del player.team.players[player.name]
                solo_team = Team(len(self._teams), None, {player.name: player}, player.location)
                player.location.active_teams[solo_team.id] = solo_team
                player.team = solo_team
                self._teams.append(solo_team)

        players_need_event = sorted(filter(lambda k: k not in hunting_players, self._players.keys()))
        while len(players_need_event):
            event, event_type = self.get_random_event()
            player_set = self.fit_event(event, set(players_need_event))
            if player_set is not None:
                event_list.append((event, event_type, player_set))
                for player in (self._players[n] for n in player_set):
                    player._active = False
                players_need_event = list(filter(lambda name: name not in player_set, players_need_event))

        for event, event_type, player_set in event_list:
            self.process_event(event, event_type, player_set)

        for player in self._players.values():
            player._active = True

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
            team_pool = sorted([self._teams[i] for i in set(p.team.id for p in player_pool)],
                                    key=lambda t: (t.active_player_count(), t.id), reverse=True)
        else:
            _localized = event['radius'] == -1
            player_pool = sorted([self._players[p_id] for p_id in remaining_player_set], key=lambda p: p.name)
            team_pool = sorted([self._teams[i] for i in set(p.team.id for p in player_pool)],
                                    key=lambda t: (t.active_player_count(), t.id), reverse=True)

        if len(player_pool) < event['num_players']:
            return None

        def pick_team(team_pool, teams_select, nplayer_min):
            index_last = 0
            while index_last < len(team_pool):
                if team_pool[index_last].active_player_count() < nplayer_min:
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
                                                    key=lambda t: (t.active_player_count(), t.id))
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
                    team_players = self._rng.sample(self._teams[team_id].active_players(), len(targets))
                    for player, spot in zip(team_players, targets):
                        try:
                            player_select[spot] = player.name
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
                        try:
                            player_select[spot] = player_name
                        except:
                            print(event)
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
    while True:
        print(f"Alive: {len(game._players)}, Dead: {len(game._dead_players)}")
        print("Active teams:")
        for team in game._teams:
            if team.player_count() > 0:
                print(team)
        input()
        game.turn()
