'''
Represents a player. 
author: ferricles
'''

#TODO:
'''
 * change the location field's graphNode type is correct
'''


class Player:

    #Constructs a player.
    def __init__(self, name: str, location: GraphNode, team: int = -1, img_path: str = "", alive: bool = True, kills: int = 0, deathmsg: str = ""):
        '''Mandatory'''
        self.name = name
        self.location = location
        '''Recommended but Optional'''
        self.team = team
        self.img_path = img_path
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