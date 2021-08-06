# Type annotations without import
from __future__ import annotations
from typing import List

from game.game_constants import MAX_TEAM_SIZE, TEAM_CHANGE_CHANCE

'''
Represents a player. 
author: ferricles
'''

class Player:
    """
    Class representing a player.
    Holds info like name, id, kills, aliveness, etc
    Also more dynamic stuff like team/location
    """

    #Constructs a player.
    def __init__(self, name: str, img_path: str = "", team: Team=None, location: GraphNode=None, kills: int = 0, deathmsg: str = ""):
        self.name = name

        self.img_path = img_path
        if location is not None:
            location.active_players[self.name] = self
        self.location = location
        self.team = team

        '''Probably don't touch these'''
        self.kills = kills
        self.alive = True
        self.deathmsg = deathmsg #probably shouldn't initialize them dead
        self._active = True

    def move_to(self, new_location: GraphNode):
        if self.location is not None:
            del self.location.active_players[self.name]
        self.location = new_location
        new_location.active_players[self.name] = self
        #print(f"{self.name} move to {self.location.name}")

    def pretty_info(self):
        retval = f"Player name={self.name} [{self.team.get_display_name()}]:\nKills: {self.kills}\nLocation: {self.location.name}\nAlive: {self.alive}"
        if self.alive:
            return retval
        else:
            return retval + f"\nDeath: [{self.deathmsg}]"

    def __str__(self):
        return f"Player(name={self.name},location={self.location.name})"

    def __repr__(self):
        return self.__str__()

    def move_teams(self, new_team: Team):
        del self.team.players[self.name]
        new_team.players[self.name] = self
        self.team = new_team

    def remove(self):
        del self.team.players[self.name]
        del self.location.active_players[self.name]
        self.team = Team(-1)
        self.alive = False
        
class Team:
    """
    Class representing a team. Probably more of a container than anything meaningful.
    """
    def __init__(self, team_id: int, name: str=None, player_map: dict=None, location: GraphNode=None):
        self.id = team_id
        self.name = name
        if player_map is None:
            self.players = dict()
        else:
            self.players = player_map
        if location is not None:
            location.active_teams[self.id] = self
        self.location = location
        self.hunt = 0

    def get_display_name(self):
        if self.name is None:
            return '+'.join(p.name for p in self.players.values())
        return self.name

    def move_to(self, new_location: GraphNode):
        if self.location is not None:
            del self.location.active_teams[self.id]
        self.location = new_location
        new_location.active_teams[self.id] = self

    def player_count(self):
        return len(self.players)

    def active_player_count(self):
        return sum(p._active for p in self.players.values())

    def active_players(self):
        return [p for p in self.players.values() if p._active]

    def merge_into(self, parent_team):
        parent_team.players.update(self.players)
        for player in self.players.values():
            player.team = parent_team
        if self.location is not None:
            del self.location.active_teams[self.id]
        self.players = dict()

    def __str__(self):
        return f"Team(display_name={self.get_display_name()},location={self.location.name},size={self.player_count()},id={self.id},players=[{','.join(p.name for p in self.players.values())}])"

    def __repr__(self):
        return self.__str__()

def try_merge_teams(players: List[Player], random: Random):
    """
    Try to merge the teams of this subset of players.
    In order:
    1) Smallest teams will try to merge.
    2) Player from smallest team will try to move to second smallest team.
    """

    # Collect unique teams among the players, sort by size in ascending order.
    team_ids = set()
    team_pool = []
    for p in players:
        if p.team.id not in team_ids:
            team_ids.add(p.team.id)
            team_pool.append(p.team)
    team_pool.sort(key=lambda t: (t.player_count(), -t.id))

    while len(team_pool) > 1:
        # If the team is full remove it.
        if team_pool[-1].player_count() == MAX_TEAM_SIZE:
            team_pool.pop(-1)
            continue
        # From this point on no teams are full.

        # Case 1: Smallest two teams can merge.
        # Do it. Resort list and continue
        if team_pool[0].player_count() + team_pool[1].player_count() < MAX_TEAM_SIZE:
            team_pool[0].merge_into(team_pool[1])
            team_pool.pop(0)
            team_pool.append(team_pool.pop(0))
            team_pool.sort(key=lambda t: (t.player_count(), -t.id))
            continue

        # Case 2: Smallest two teams can't merge (over team size cap).
        # Remove smallest team from pool. Optionally a player from the smallest
        # team merges into the second smallest team.
        smallest = team_pool.pop(0)
        for player in random.sample(players, len(players)):
            if player.name in smallest.players:
                if random.random() < TEAM_CHANGE_CHANCE:
                    player.move_teams(team_pool[0])
                    team_pool.sort(key=lambda t: (t.player_count(), -t.id))
                    break
