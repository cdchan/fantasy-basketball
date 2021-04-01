"""
Calculate valuations for the rest of season and the next few weeks, based on the game schedule

"""

import datetime
import math
import pandas


from config import SEASON_START, LAST_WEEK, MY_TEAM_ID
from utils import load_projections, load_rosters


NEXT_WEEK = int(math.ceil((datetime.datetime.today() - SEASON_START).days / 7.0) + 1)
WEEKS_AHEAD = 3


def main():
    rosters = load_rosters()

    projections = load_projections()

    valuation = projections.merge(rosters, on='name', how='left')

    schedule = load_schedule()

    valuation = valuation.merge(schedule, on='team')

    valuation = add_weekly_valuation(valuation)

    valuation = check_if_top_n(valuation)

    output_csv(valuation)





def load_schedule():
    """
    Load rest of year schedule

    """
    schedule = pandas.read_csv("schedule_{}.csv".format(SEASON_START.year))

    schedule['ros'] = 0

    for i in range(NEXT_WEEK, LAST_WEEK + 1):
        schedule['ros'] += schedule['W{}'.format(i)]

    return schedule


def add_weekly_valuation(valuation):
    """
    Based on the next few weeks, calculate the projected points

    """
    for week_num in range(NEXT_WEEK, LAST_WEEK + 1):
        valuation['W{} fpoints'.format(week_num)] = valuation['W{}'.format(week_num)] * valuation['fpoints']

    # assume each player plays a projected % of games
    # apply that % to the remaining games on schedule
    valuation['ros gtp'] = valuation['gp'] / valuation['team_gtp'] * valuation['ros']

    valuation['ros fpoints'] = valuation['ros gtp'] * valuation['fpoints']

    valuation['ros pct'] = valuation['ros fpoints'] / valuation['ros fpoints'].max()

    return valuation


def check_if_top_n(valuation):
    """
    For each remaining week, check if the player would rank in the top N per week for your team

    """
    top_n_data = []

    current_team = valuation[valuation['team_id'] == MY_TEAM_ID].copy()

    for i in range(len(valuation)):
        playable_weeks = []
        playable_points = 0

        if any(valuation.iloc[i]['name'] == current_team['name']):
            consider = current_team
        else:
            consider = current_team.copy().append(valuation.iloc[i])

        for week_num in range(NEXT_WEEK, LAST_WEEK + 1):
            consider.sort_values(['W{} fpoints'.format(week_num), 'fpoints'], ascending=False, inplace=True)

            if any(valuation.iloc[i]['name'] == consider.head(10)['name']):
                playable_weeks.append('{}'.format(week_num))

                playable_points += valuation.iloc[i]['W{} fpoints'.format(week_num)]

        top_n_data.append({
            'playable_weeks': ','.join(playable_weeks),
            'n_playable_weeks': len(playable_weeks),
            'playable_points': playable_points
        })

    valuation['n_playable_weeks'] = [x['n_playable_weeks'] for x in top_n_data]
    valuation['playable_weeks'] = [x['playable_weeks'] for x in top_n_data]
    valuation['playable_points'] = [x['playable_points'] for x in top_n_data]

    return valuation


def output_csv(valuation):
    """
    Export valuations to CSV

    """
    csv_columns = [
        'name',
        'team',
        'pos',
        'team_id',
        'fpoints',
        # 'gtp',
        'mpg',
    ]

    weekly_columns_base = ['W{}'.format(i) for i in range(NEXT_WEEK, NEXT_WEEK + WEEKS_AHEAD)]
    weekly_columns_base += ['ros']

    weekly_columns = ['{} fpoints'.format(x) for x in weekly_columns_base]

    csv_columns += weekly_columns_base
    csv_columns += weekly_columns

    csv_columns += [
        'ros gtp',
        'ros pct',
        'yahoo_id',
        'n_playable_weeks',
        'playable_weeks',
        'playable_points',
    ]

    valuation.sort_values(weekly_columns[0], ascending=False, inplace=True)

    valuation[csv_columns].to_csv('valuation.csv', encoding='utf8', index=False)


if __name__ == '__main__':
    main()
