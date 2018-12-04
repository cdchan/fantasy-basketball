"""
Calculate valuations for the rest of season and the next few weeks, based on the game schedule

"""

import datetime
import lxml.html
import pandas


from config import SEASON_START


NEXT_WEEK = (datetime.datetime.today() - SEASON_START).days / 7 + 1
WEEKS_AHEAD = 3


def main():
    rosters = load_rosters()

    projections = load_projections()

    valuation = projections.merge(rosters, on='name', how='left')

    schedule = load_schedule()

    valuation = valuation.merge(schedule, on='team')

    valuation, weekly_columns = add_weekly_valuation(valuation)

    output_csv(valuation, weekly_columns)


def load_rosters():
    """
    Load current rosters

    """
    rosters = pandas.read_csv('rosters.csv')

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


def calc_team_games_to_play(projections):
    """
    Assume that each team has a player projected to play in every remaining game. Use that player's games to play as the team's.

    """
    team_gtp = projections.groupby('team', as_index=False).aggregate({
        'gtp': 'max'
    })

    team_gtp.rename(columns={'gtp': 'team_gtp'}, inplace=True)

    return team_gtp


def load_schedule():
    """
    Load rest of year schedule

    """
    schedule = pandas.read_csv("schedule_2018.csv")

    schedule['ros'] = 0

    for i in range(NEXT_WEEK, 25):
        schedule['ros'] += schedule['W{}'.format(i)]

    return schedule


def add_weekly_valuation(valuation):
    """
    Based on the next few weeks, calculate the projected points

    """
    weekly_columns_base = []

    for week_num in range(NEXT_WEEK, NEXT_WEEK + WEEKS_AHEAD):
        valuation['W{} fpoints'.format(week_num)] = valuation['W{}'.format(week_num)] * valuation['fpoints']
        weekly_columns_base.append('W{}'.format(week_num))

    valuation['ros gtp'] = valuation['gtp'] / valuation['team_gtp'] * valuation['ros']

    valuation['ros fpoints'] = valuation['ros gtp'] * valuation['fpoints']

    valuation['ros pct'] = valuation['ros fpoints'] / valuation['ros fpoints'].max()

    weekly_columns = ['{} fpoints'.format(x) for x in weekly_columns_base]

    return valuation, weekly_columns_base + weekly_columns


def output_csv(valuation, weekly_columns):
    """
    Export valuations to CSV

    """
    csv_columns = [
        'name',
        'team',
        'pos',
        'team_id',
        'gtp',
        'fpoints',
    ]

    csv_columns += weekly_columns

    csv_columns += [
        'ros',
        'ros gtp',
        'ros fpoints',
        'ros pct'
    ]

    valuation.sort_values(weekly_columns[WEEKS_AHEAD], ascending=False, inplace=True)

    valuation.to_csv('valuation.csv', encoding='utf8', index=False, columns=csv_columns)


if __name__ == '__main__':
    main()
