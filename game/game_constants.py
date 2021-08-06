"""
Default event happening probabilities (day 0), by category
Uniform chance in each category
"""
EVENT_PROBABILITY = {
        "idle": 0.42,
        "accident": 0.03,
        "combat": 0.05,
        "bond": 0.3,
        "team": 0.19,
        "team-accident": 0.01
    }
EVENT_NUM_TRIES = 3

MOVE_CHANCE = 0.7
FOLLOW_TEAM_CHANCE = 0.97

MAX_TEAM_SIZE = 4
TEAM_CHANGE_CHANCE = 0.3

