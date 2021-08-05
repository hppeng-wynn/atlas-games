# Type annotations without import
from __future__ import annotations
from typing import List
'''
Represents a player. 
author: ferricles
'''

'''
 * change the location field's graphNode type is correct
'''


class Player:
    """
    Probably just another data class
    everything is a data class

    nvm
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
        self.deathmsg = deathmsg #probably shouldn't initialize them dead
        self._active = True

    def move_to(self, new_location: GraphNode):
        if self.location is not None:
            del self.location.active_players[self.name]
        self.location = new_location
        new_location.active_players[self.name] = self
        #print(f"{self.name} move to {self.location.name}")

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
