import sys
import json

# Event Text|NumPlayers|Death List|TeamList|Solo|Complement|Radius|type|Special Location Req
#   0           1           2       3       4       5        6      7           8

"""
Parse event from gdoc to json.

Usage: python3 event_parse.py [fname]
"""


def strToLst(string):
    lst = []
    if string == '':
        return []
    teststring = string.translate({ord(" "): None, ord('['): " ", ord(']'): " "})
    lst_of_strings = teststring.split(" ")
    for item in lst_of_strings:
        if item not in ['',',']:
            midway = []
            for x in item.split(','):
                    if x.isnumeric():
                        midway.append(int(x))
            lst.append(midway)
    return lst

events_by_type = dict()

with open(sys.argv[1], 'r') as input_file:
    for number,line in enumerate(input_file):
        if line.endswith('\n'):
            line = line[:-1]
        parts = line.split('\t')
        event_type = parts[7]
        event_data = {
            "text": parts[0],
            "num_players": int(parts[1]),
            "deaths": strToLst(parts[2])[0] if parts[2] != '' else [],
            "team_list": strToLst(parts[3]),
            "complement_list": strToLst(parts[5]),
            "radius": int(parts[6]),
        }

        if parts[8]:
            event_data["location"] = parts[8]
        if event_type in events_by_type:
            events_by_type[event_type].append(event_data)
        else:
            events_by_type[event_type] = [event_data]

        '''
        Data Validation section
        '''
        event_line_number = number + 1

        teamlist = []
        complist = []
        deathlist = []
        teamset = set()
        compset = set()
        deathset = set()

        for team in event_data['team_list']:
            for player in team:
                teamlist.append(player)
                teamset.add(player)
        for team in event_data['complement_list']:
            for player in team:
                complist.append(player)
                compset.add(player)
        for player in event_data['deaths']:
            deathlist.append(player)
            deathset.add(player)

        # Data Validation - checks if the number of players given is equal to TeamList + Solo + Complement
        if event_data['num_players'] != len(teamset | compset) + int(parts[4]):
            print(f">>> num_players != TeamList + Solo + Complement in line {event_line_number}\n")

        # Data Validation - checks for duplicates in the different lists
        if len(teamlist) != len(teamset) or len(complist) != len(compset) or len(deathlist) != len(deathset):
            print(f">>> a certain list has duplicates in line {event_line_number}\n")

        # Data Validation - checks for TeamList and ComplementList intersection
        if len(teamset & compset) != 0:
            print(f">>> team_list and complement_list intersect in line {event_line_number}\n")

        # Data Validation - checks list indices
        for i in (teamset | compset | deathset):
            if event_data['num_players'] <= i:
                print(f">>> list indice is bigger than num_players in line {event_line_number}\n")

        # Data Validation - checks location existence
        with open('world_data.json') as f:
            world_data = json.load(f)
            if 'location' in event_data:
                for loc in event_data['location'].split(','):
                    if loc.strip(' ') not in world_data['nodes'].values():
                        print(f">>> WARNING: {loc} is not a valid location (line {event_line_number})\n")


with open("event_data.json", 'w') as outfile:
    json.dump(events_by_type, outfile)
