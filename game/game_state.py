from __future__ import annotations

if __name__ == "__main__":
    import sys
    import os
    path = os.path.join(os.path.dirname(__file__), '..')
    sys.path.append(path)

from typing import List, Mapping
import random
import copy
import threading
from PIL import Image
import requests
import math

from emojis import ATLOSS
from game.world import World
from game.players import Player, Team, try_merge_teams
from game.game_constants import *
from game.game_visualizer import render_map


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

class GameState:
    """
    Class holding the important info needed for the game.
    """
    def __init__(self, world_data: dict, player_data: dict, event_data: dict, output_function=print, seed: int=None):
        """
        world_data: World json
        player_data: player json
        event_data: event json
        output_function: thing to call when printing output
        seed: rng seed, or None
        """
        #TODO: output_function should be more customizable for different output types
        self._world = World(world_data)                 # World object.
        self._event_data = event_data                   # event data store (do not mutate)
        self._teams: List[Team] = []                    # List of teams, including inactive teams. Index in list is team id.
                                                        #   NOTE: Do not sort!
        self._players: Mapping[str, Player] = dict()    # Map (str, Player) of alive players.
                                                        #   NOTE: players must have unique names.
        self._dead_players: List[Player] = []           # List of dead players in order of death.
        self._turn_counter = 0                          # Turn counter (current day)
        self._event_probability = copy.copy(EVENT_PROBABILITY)      # Probability for each event. Changes over time
        self._hunt_chance = 0                           # Chance (0-1) that a team will decide to go hunting.
        self._print = output_function
        self._event_printer = lambda this, event_data: [print(event['text'].format(*(p.name for p in players))) for event, etype, players in event_data]

        img_map: Mapping[str, Image] = dict()
        def download_imgs(urlmap: Mapping[str, str], idx_low: int, idx_high: int) -> List[Image]:
            for i in range(idx_low, idx_high):
                image = Image.open(requests.get(name_url_data[i][1], stream=True).raw)
                image.thumbnail((64, 64), Image.ANTIALIAS)
                image = image.resize((64, 64))
                img_map[name_url_data[i][0]] = image

        name_url_data = []
        keys = sorted(player_data.keys())
        for k in keys:
            data = player_data[k]
            if 'active' in data and not data['active']:
                continue
            name_url_data.append([data['name'], data.get('img', '')])

        num_players = len(name_url_data)
        thread_objs = []
        NUM_THREADS = 4
        for i in range(NUM_THREADS):
            thread = threading.Thread(target = download_imgs, args = (name_url_data, round(i / NUM_THREADS * num_players), round((i+1) / NUM_THREADS * num_players), ) )
            thread_objs.append(thread)

        for t in thread_objs:
            t.start()
        for t in thread_objs:
            t.join()

        # Initialize players and teams.
        # Players always are on a team (if they are solo they are on their own team).
        # Players can start on the same team by specifying the "team" field, and that team will be named
        # Otherwise they start solo with an unnamed team.
        teams_by_name: Mapping[str, Team] = dict()      # Temp variable: Teams are associated with numeric ID instead of name.
        keys = sorted(player_data.keys())
        for k in keys:
            data = player_data[k]
            if 'active' in data and not data[active]:
                continue
            if "team" in data:
                team_name = data["team"]
            else:
                team_name = data["name"]
            if team_name in teams_by_name:
                player_team = teams_by_name[team_name]
            else:
                player_team = Team(len(self._teams), None)
                teams_by_name[team_name] = player_team
                self._teams.append(player_team)

            new_player = Player(data["name"], data.get("img", ""), player_team, img = img_map[data['name']])
            self._players[new_player.name] = new_player
            player_team.players[new_player.name] = new_player

        # Map for all players (dead or alive). Do not mutate
        self._players_static = copy.copy(self._players)

        # Generate a random seed if there is none.
        # Seed RNG so each atlas games is repeatable.
        if seed is None:
            seed = random.randrange(2**31)
        self._print(f"Random seed: {seed}")
        self._rng = random.Random(seed)

        # Distribute teams
        # Distribution method(subject to change): Uniform over world "starting nodes"
        start_points = self._world.get_starting_nodes()
        for team in self._teams:
            start_point = self._world.node(self._rng.choice(start_points))
            team.move_to(start_point)
            for player in team.players.values():
                player.move_to(start_point)

    def set_event_printer(self, print_func):
        """
        Set the "event printer".

        Should take 3 args:
            - 0: 'this' (to access player/map data structure)
            - 1: event (event dict, no type info..)
            - 2: player list (player objects!)
        """
        self._event_printer = print_func

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
            return self.get_random_event()
        return (self._rng.choice(self._event_data[event_type]), event_type)

    def process_event(self, event: Event, event_type: str, players: List[Player]):
        """
        Process the effects of an event.
        (deaths, team formation, special fx)

        Runs after all events for a turn have been selected.

        Parameters:
        - event:            Event to process
        - event_type:       event type (not stored with event since im a dumbass)
        - players:          List of players participating in this event, in order

        Return:
            List of killed players (may be empty)
        """
        if event_type == 'bond':
            try_merge_teams(players, self._rng)

        event_text = event['text'].format(*(p.name for p in players))
        killed_players = []
        if len(event['deaths']) > 0:
            kill_credit = [True] * len(players)
            for index in event['deaths']:
                killed_player = players[index]
                killed_player.deathmsg = event_text
                killed_player.remove()
                del self._players[killed_player.name]
                killed_players.append(killed_player)
                self._dead_players.append(killed_player)
                kill_credit[index] = False
            for i, alive in enumerate(kill_credit):
                if alive:
                    players[i].kills += len(event['deaths'])

        #TODO bind to frontend properly
        return killed_players


    def turn(self):
        """
        One day of the game simulation.

        Process:
        1) Increment turn counter
            - Additional logic (hostility increase, etc)
        2) Move teams
            - Teams move 1 square per turn with `MOVE_CHANCE` chance.
        3) Move players
            - Players stick with their team with `FOLLOW_TEAM_CHANCE` chance.
                - (solo players always stick with their team)
            - Players splitting off form their own new (nameless) team.
            - After day 3 teams can go 'hunting' (change their AI from random walk
                to pursuit of the nearest team)
        4) Pick events
            while there are players with no assigned events:
                Pick a random event distributed as self._event_probability
                Try to apply the event
        5) Resolve events
            - death, team formation, special fx, etc
        6) Wrap up
            - Recap of deaths, etc
        """
        self._print(f"Day {self._turn_counter}")
        if self._turn_counter == 3:
            self._event_probability.update({
                    "idle": 0.27,
                    "combat": 0.30,
                    "bond": 0.20
                })
        if self._turn_counter == 10:
            self._event_probability.update({
                    "idle": 0.17,
                    "combat": 0.50,
                    "bond": 0.10
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
                        }, 'hunt', team.players.values()))
                    continue;
                if self._rng.random() < MOVE_CHANCE:
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
                    move_to = team.location.random_neighbor(self._rng)
                    team.move_to(move_to)
        for player in sorted(self._players.values(), key=lambda p: p.name):
            if player.name in hunting_players:
                continue
            if self._rng.random() < FOLLOW_TEAM_CHANCE or player.team.player_count() == 1:
                player.move_to(player.team.location)
            else:
                player.move_to(player.location.random_neighbor(self._rng))
                del player.team.players[player.name]
                solo_team = Team(len(self._teams), None, {player.name: player}, player.location)
                player.location.active_teams[solo_team.id] = solo_team
                player.team = solo_team
                self._teams.append(solo_team)

        players_need_event = set(filter(lambda k: k not in hunting_players, self._players.keys()))
        n_players = len(self._players)
        n_deaths = 0
        while len(players_need_event):
            event, event_type = self.get_random_event()
            player_set = self._fit_event(event, players_need_event)
            if player_set is not None:
                event_list.append((event, event_type, player_set))
                for player in player_set:
                    player._active = False
                    players_need_event.remove(player.name)

        killed_players = []
        for event, event_type, player_set in event_list:
            killed_players += self.process_event(event, event_type, player_set)

        self._event_printer(self, event_list)

        self._print(f"{len(killed_players)} cannon shots can be heard in the distance.")
        for player in killed_players:
            self._print(f"{ATLOSS} {player.name}")
        for player in self._players.values():
            player._active = True


    def print_map(self, location_list: List(Team or Player)=None):
        coordlst = []
        obj_names = []
        if location_list:
            for obj in location_list:
                center_x = obj.location.coords[0]
                center_y = obj.location.coords[1]
                theta = random.uniform(0,2*math.pi)
                gamma = random.uniform(0,1)
                x = 200 * math.sqrt(gamma) * math.cos(theta)
                y = 100 * math.sqrt(gamma) * math.sin(theta)
                coords = [center_x+x,center_y+y]
                coordlst.append(coords)

                if type(obj) == Team:
                    if obj.active_player_count() != 0:
                        obj_names.append(obj.get_display_name())
                if type(obj) == Player:
                    obj_names.append(obj.name)

            worldmap = render_map(coordlst,obj_names)
            return worldmap

        else:
            teams_copy = self._teams.copy()
            teams_sorted = sorted(teams_copy,key=lambda team: team.active_player_count(),reverse = True)
            return self.print_map(teams_sorted)

    def _fit_event(self, event, remaining_player_set):
        """
        'Fit' an event into the set of remaining players.

        Parameters:
        - event: The event in question
        - remaining_player_set: set containing remaining player names (prefer actual set for fast "in" comparison)

        Picking process:
        0) Set up player pool and team pool, check preconditions
            - IF the event is localized, set player pool to players in radius, compute team pool.
            - OTHERWISE the player pool and team pool are just all players/teams still active this turn.
            - IF there aren't enough players left in total: return None.
        1) Pick a qualified team (team requiring event) or a player (solo only event) from the pool of all teams or players
                (skip this step if the event is already localized or is infinite range)
            - IF no qualified team exists for team events: We're permastuck, return None.
        2) Set this event to occur centered on the picked thing's location (skip this step if the event
                is already localized)
        3) Filter the player pool down to the players within specified radius of this location
                (skip this step if the event is already localized or is infinite range)
        4) Recompute the team pool using the player pool
                (skip this step if the event is already localized or is infinite range)
        5) Fill out event (randomly pick teams/players from the pool that satisfy the event's constraints)
            - IF we fail at this step: Retry from step 1) to `EVENT_NUM_TRIES` times
        """

        # Step 0
        if 'location' in event:
            # Location specified + infinite radius unsupported.
            target_location = self._world.node_from_name(event['location'])
            if target_location is None:
                return None

            _localized = True
            player_pool = self._world.players_near(target_location, event['radius'],
                        filter_func = lambda p: p.name in remaining_player_set)
            # Team pools are sorted in descending order of size for use later.
            team_pool = sorted([self._teams[i] for i in set(p.team.id for p in player_pool)],
                                    key=lambda t: (t.active_player_count(), t.id), reverse=True)
        else:
            _localized = event['radius'] == -1
            # player pool needs sorting to avoid uncontrollable randomness from set data structures..
            player_pool = sorted([self._players[p_id] for p_id in remaining_player_set], key=lambda p: p.name)
            team_pool = sorted([self._teams[i] for i in set(p.team.id for p in player_pool)],
                                    key=lambda t: (t.active_player_count(), t.id), reverse=True)

        # Step 0 (condition check)
        if len(player_pool) < event['num_players']:
            # Definitely not enough players for this event.
            return None

        def pick_team(team_pool, teams_select, nplayer_min):
            """
            Helper function to pick a team out of the team pool with at least `nplayer_min` players
            that are still "active" this turn.

            Parameters:
            - team_pool:    List of teams to pick from
            - teams_select: List of team ids that were already picked
            - nplayer_min:  Team size we're looking for
            """

            # Part 1: Grab subset of teams that have enough players.
            # NOTE: Team pool is sorted in descending order of active player count.
            index_last = 0
            while index_last < len(team_pool):
                if team_pool[index_last].active_player_count() < nplayer_min:
                    break
                index_last += 1
            if index_last == 0:
                return None     # No team large enough...

            # Part 2: Pick a random team out of the ones that match the player size
            # Take first `index_last` elements and return them shuffled
            possibilities = self._rng.sample(team_pool[:index_last], index_last)
            for team in possibilities:
                if team.id not in teams_select:
                    return team
            return None

        for k in range(EVENT_NUM_TRIES):
            localized = _localized
            remaining_players = player_pool
            i = event['num_players']    # Track how many slots are filled so far
            player_select = [None]*i    # Initialize return value
            # event['team_list'] is a list of lists of indices into the final `player_select` array
            #   Each sublist is (part of) a unique team -- players from different teams cannot fill
            #   spots in the same sublist, players on the same team cannot fill spots in different sublists.
            # EX: [ [0, 1], [2, 3] ] indicates that index 0 and 1 must be two players from the same team,
            #   while indices 2 and 3 must be two players from a different team.
            if len(event['team_list']) > 0:
                teams_select: List[int] = []
                if not localized:
                    team_idx = 1
                    # Step 1 (for team events): Pick one qualified team as the source.
                    source_team = pick_team(team_pool, teams_select, len(event['team_list'][0]))
                    if source_team is None:
                        # No teams large enough.
                        return None
                    teams_select.append(source_team.id)

                    # Step 2, 3, 4: Recompute player pool and team pool
                    localized = True
                    remaining_players = self._world.players_near(source_team.location, event['radius'],
                            filter_func = lambda p: p.name in remaining_player_set)
                    remaining_team_pool = sorted([self._teams[i] for i in set(p.team.id for p in remaining_players)],
                                                    key=lambda t: (t.active_player_count(), t.id))
                else:
                    team_idx = 0
                    remaining_team_pool = team_pool
                while team_idx < len(event['team_list']):
                    # Step 5: Fill remaining slots that need team grouping
                    team = pick_team(remaining_team_pool, teams_select, len(event['team_list'][team_idx]))
                    if team is None:
                        break   # No teams large enough in this subset.
                    teams_select.append(team.id)
                    team_idx += 1

                if len(teams_select) != len(event['team_list']):
                    continue
                for team_id, targets in zip(teams_select, event['team_list']):
                    team_players = self._rng.sample(self._teams[team_id].active_players(), len(targets))
                    for player, spot in zip(team_players, targets):
                        player_select[spot] = player
                        i -= 1

                remaining_players = list(filter(lambda p: p not in player_select, remaining_players))

                complement_filled = 0
                for team_id, player_set in zip(teams_select, event['complement_list']):
                    filtered_player_pool = list(filter(lambda p: p.team.id != team_id, remaining_players))
                    if len(filtered_player_pool) < len(player_set):
                        # Not enough players in the complement set
                        break
                    select_set = self._rng.sample(remaining_players, len(player_set))
                    for player, spot in zip(select_set, player_set):
                        try:
                            player_select[spot] = player
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
                        filter_func = lambda p: p.name in remaining_player_set and p not in player_select and p.name != solo_source.name)
                    solos_set.append(solo_source)
                    i -= 1

                if i > 0:
                    if len(remaining_players) < i:
                        # Not enough players for solos
                        continue
                    solos_set = self._rng.sample(remaining_players, i) + solos_set

                for i, v in enumerate(player_select):
                    if v is None:
                        player_select[i] = solos_set.pop(-1)

            return player_select
        return None

    def get_num_alive_players(self):
        return len(self._players)

    def get_num_dead_players(self):
        return len(self._dead_players)

    def player_info(self, player_name):
        if player_name in self._players_static:
            return self._players_static[player_name].pretty_info()
        return "No such player!"

if __name__ == "__main__":
    import json
    #world_data = json.load(open("world_simple.json", 'r'))
    world_data = json.load(open("world_data.json", 'r'))
    event_data = json.load(open("event_data.json", 'r'))
    #player_data = json.load(open("players_simple.json", 'r'))
    player_data = json.load(open("players_full.json", 'r'))
    game = GameState(world_data, player_data, event_data, seed=1644003087)
    while True:
        print(f"Alive: {len(game._players)}, Dead: {len(game._dead_players)}")
#         print("Active teams:")
#         for team in game._teams:
#             if team.player_count() > 0:
#                 print(team)
        input()
        game.turn()
