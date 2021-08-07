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
    teststring = string.translate({ord(" "): "", ord('['): " ", ord(']'): " "})
    lst_of_strings = teststring.split(" ")
    for item in lst_of_strings:
        if item.isnumeric() and item not in ['', ',']:
            lst.append([int(item)])
        else:
            if item not in ['', ',']:
                midway = []
                for x in item:
                    if x.isnumeric():
                        midway.append(int(x))
                lst.append(midway)
    return lst


events_by_type = dict()

with open(sys.argv[1], 'r') as input_file:
    for line in input_file:
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

with open("event_data.json", 'w') as outfile:
    json.dump(events_by_type, outfile)
