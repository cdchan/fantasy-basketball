"""
Config file SAMPLE

"""

import datetime

# the Monday of the first week of the season
SEASON_START = datetime.datetime(2000, 1, 1)
# the last week of scoring
LAST_WEEK = 24
# how many players are activer per week
TOP_N = 10
# total non-IL roster size
ROSTER_SIZE = 13
# your team id
MY_TEAM_ID = 1
# number of teams
N_TEAMS = 12

# Yahoo app client id and secret
YAHOO_CLIENT_ID = ''
YAHOO_CLIENT_SECRET = ''

# go through authorization flow to get refresh token
yahoo_refresh_token = ''

# ids for identify league for Yahoo API
# SPORT_ID is the season of fantasy basketball (Yahoo refers to this as the game id)
# find this through https://fantasysports.yahooapis.com/fantasy/v2/game/nba
YAHOO_SPORT_ID = ''
# LEAGUE_ID is the id for your league
YAHOO_LEAGUE_ID = ''

# mapping between Yahoo stat name and our stat name
YAHOO_STATS_TRANSLATION = {
    'GP*': 'gtp',
    'Current': 'rank',
    'PTS': 'pts',
    'REB': 'treb',
    'AST': 'ast',
    'ST': 'stl',
    'BLK': 'blk',
    'TO': 'to',
    'MPG': 'mpg',
}

# Yahoo cookie to enable scraping of league data
YAHOO_COOKIE_STRING = r''''''
