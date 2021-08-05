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

    #Constructs a player.
    def __init__(self, name: str, img_path: str = "", team: Team=None, location: GraphNode=None, alive: bool = True, kills: int = 0, deathmsg: str = ""):
        self.name = name

        self.img_path = img_path
        self.location = location
        self.team = team

        '''Probably don't touch these'''
        self.alive = alive
        self.kills = kills
        self.deathmsg = deathmsg #probably shouldn't initialize them dead

    def move(location: GraphNode):
        self.location = location

    #Kills the player and prints their deathmsg. If a deathmsg is provided, it will print that.
    def die(self, deathmsg: str = None):
        if deathmsg is not None:
            self.deathmsg = deathmsg
        print(self.deathmsg)
        self.alive = False

class Team:
    """
    Class representing a team. Probably more of a container than anything meaningful.
    """
    def __init__(self, name: str, player_list: List[Player]):
        self.name = name
        self.players = player_list

