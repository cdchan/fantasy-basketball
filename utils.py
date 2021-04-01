"""
Utility functions

"""

import pandas


def load_rosters():
    """
    Load current rosters

    """
    rosters = pandas.read_csv('rosters.csv', comment='#')

    return rosters


def load_projections():
    """
    Load projections

    """
    projections = pandas.read_csv('projections.csv')

    projections = projections.eval('fpoints = 1.0 * pts + 1.2 * treb + 1.5 * ast + 3.0 * blk + 3.0 * stl - 1.0 * to')

    team_gtp = calc_team_games_to_play(projections)

    projections = projections.merge(team_gtp, on='team', how='left')

    return projections


def load_recent_playing_time():
    pt = pandas.read_csv('yahoo_playing_time.csv', na_values=['-'])

    components = pt['mpg'].str.split(':', n=2, expand=True)

    pt['mpg_recent'] = components[[0]].astype(float).values + components[[1]].astype(float).values / 60

    pt['gp_recent'] = pt['gtp']

    return pt[['yahoo_id', 'gp_recent', 'mpg_recent']]


def calc_team_games_to_play(projections):
    """
    Assume that each team has a player projected to play in every remaining game. Use that player's games to play as the team's.

    """
    team_gtp = projections.groupby('team', as_index=False).aggregate({
        'gp': 'max'
    })

    team_gtp.rename(columns={'gp': 'team_gtp'}, inplace=True)

    return team_gtp
