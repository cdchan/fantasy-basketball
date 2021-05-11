"""
Calculate roto league valuations for the rest of season

"""
import argparse
import itertools
from collections import namedtuple

import numpy
import pandas
from scipy.optimize import minimize_scalar
from scipy.stats import linregress

from utils import load_projections, load_recent_playing_time, load_rosters
from config import MY_TEAM_ID, N_TEAMS, ROSTER_SIZE, TOP_N


COUNTING_STATS = ['3pm', 'pts', 'treb', 'ast', 'stl', 'blk', 'to']
RATIO_STATS = ['fg%', 'ft%']
RATIO_STATS_PARTS = ['fga', 'fgm', 'fta', 'ftm']

IMPORTANT_CATS = ['treb', 'ast', 'stl', 'blk', 'to', 'fg%', 'ft%']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--optimize", action="store_true", help="run roster optimizer")
    args = parser.parse_args()

    ros = combine_projections()

    # add team id to projections
    rosters = load_rosters()
    ros = ros.merge(rosters[['yahoo_id', 'team_id']], on='yahoo_id', how='left')

    standings = load_standings()
    final_standings = calc_final_standings(standings, ros)
    print(final_standings[['team_id'] + COUNTING_STATS + RATIO_STATS + RATIO_STATS_PARTS].to_string(index=False))

    final_rank = calc_rankings(final_standings)
    print(final_rank)
    current_final_rank = final_rank.loc[final_rank['team_id'] == MY_TEAM_ID, 'total'].values[0]

    # since fg% and ft% are rate stats, we need to establish value above and below a threshold
    base_fga = final_standings[final_standings['team_id'] == MY_TEAM_ID]['fga'].values[0]
    base_fta = final_standings[final_standings['team_id'] == MY_TEAM_ID]['fta'].values[0]

    spg = calc_spg(final_standings, base_fga, base_fta)
    base_ratio_stats = {
        'fg%': final_standings['fg%'].min(),
        'ft%': final_standings['ft%'].min()
    }
    ros_values = calc_valuation(spg, base_ratio_stats, ros)

    # print team valuations
    cols = ['yahoo_name', 'yahoo_id', 'team_id', 'rank', 'gtp', 'p_mpg', 'total_value', 'mod_value', 'pts_value', '3pm_value', 'fg%_value', 'ft%_value', 'treb_value', 'ast_value', 'stl_value', 'blk_value', 'to_value']
    print(ros_values[ros_values['team_id'] == MY_TEAM_ID][cols])
    # print best available free agents
    print(ros_values[ros_values['team_id'].isna()].head(15)[cols])
    # output valuations
    ros_values[cols].to_csv("ros_values.csv", encoding='utf8', index=False)

    ros_by_team = ros_values.groupby('team_id').sum().reset_index()
    ros_by_team.sort_values('total_value', ascending=False, inplace=True)

    if args.optimize:
        optimize_roster(ros_values, standings)


def combine_projections():
    """
    Use rate projections from Hashtag Basketball, but games to play from Yahoo

    """
    id_mapping = pandas.read_csv('id_mapping.csv')

    htb = load_projections()
    htb.rename(columns={'name': 'htb_name'}, inplace=True)
    ros_rate = htb.merge(id_mapping, on='htb_name', how='left')
    # check that all players have been ID mapped
    print(ros_rate[ros_rate['yahoo_id'].isna()])

    yahoo = pandas.read_csv('yahoo_projections.csv')

    ros_rate = ros_rate.merge(yahoo[['yahoo_id', 'gtp', 'rank']], how='left')

    # override minutes per game projections with recent playing time
    pt = load_recent_playing_time()
    ros_rate = ros_rate.merge(pt, on='yahoo_id', how='left')

    # weight recent playing time by the number of games played recently
    ros_rate['p_mpg'] = ros_rate['mpg'].where(
        ros_rate['mpg_recent'].isna(),
        (
            (ros_rate['mpg'] * (14 - ros_rate['gp_recent'])) + 
            (ros_rate['mpg_recent'] * ros_rate['gp_recent'])
        ) / (14)
    )
    
    for stat in COUNTING_STATS + RATIO_STATS_PARTS:
        ros_rate[stat] = ros_rate[stat] / ros_rate['mpg'] * ros_rate['p_mpg']

    # override playing time projections with manual ones if necessary
    gtp_manual = pandas.read_csv('gtp_manual.csv', comment='#')
    gtp_manual.drop('name', axis=1, inplace=True)
    ros_rate = ros_rate.merge(gtp_manual, on='yahoo_id', how='left')
    ros_rate['gtp'] = ros_rate['gtp_override'].combine_first(ros_rate['gtp'])

    ros = ros_rate[['yahoo_name', 'yahoo_id', 'rank', 'gtp', 'p_mpg', 'fg%', 'ft%']].copy()
    # scale rate projections to total rest of season stats
    for stat in COUNTING_STATS + RATIO_STATS_PARTS:
        ros[stat] = ros_rate[stat] * ros_rate['gtp']

    return ros


def load_standings():
    """
    Load current roto standings

    """
    standings = pandas.read_csv('standings.csv')

    standings.rename(columns={
        '3ptm': '3pm',
        'reb': 'treb',
        'st': 'stl',
    }, inplace=True)
    standings.sort_values('team_id', inplace=True)
    standings = standings.reset_index()

    return standings


def calc_mult(mult, pct_played, max_games, gtp):
    """
    Objective function for minimizer

    """
    return numpy.abs(max_games - numpy.sum(numpy.clip(pct_played * mult, 0, 1) *  gtp))


def find_weights(pct_played, max_games, gtp):
    """
    Optimizing function that finds the % of games each player on the roster will start given a maximum number of games

    This assumes that the manager will start higher ranked players as much as possible.
    """
    result = minimize_scalar(calc_mult, bounds=(1, 20), method='bounded', args=(pct_played[:len(gtp)], max_games, gtp))

    return numpy.clip(pct_played[:len(gtp)] * result.x, 0, 1)


def sum_team(x, pct_played, max_games):
    """
    Given how often each player on the roster starts, sum the total rest of season stats

    """
    w = find_weights(pct_played, max_games, x['gtp'])

    return x[COUNTING_STATS + RATIO_STATS_PARTS].multiply(w, axis='index').sum()


def calc_team_projections(projections):
    """
    Calculate the total rest of season stats for every team

    """
    pct_played = numpy.array((100, 100, 100, 100, 100, 100, 100, 80, 70, 50, 40, 30, 10, 10, 5, 5, 0)) / 100

    ros_by_team = projections.groupby('team_id').apply(sum_team, pct_played, projections['gtp'].max())

    return ros_by_team.reset_index()


def calc_final_standings(standings, projections):
    """
    Given current standings and rest of season player projections, calculate the final standings

    This uses a weighted average of the players on the roster.

    """
    ros_by_team = calc_team_projections(projections)

    final_standings = pandas.DataFrame()
    final_standings['team_id'] = standings['team_id']

    for stat in COUNTING_STATS + RATIO_STATS_PARTS:
        final_standings[stat] = standings[stat] + ros_by_team[stat]
    
    final_standings['fg%'] = final_standings['fgm'] / final_standings['fga']
    final_standings['ft%'] = final_standings['ftm'] / final_standings['fta']

    return final_standings


def calc_spg(standings, base_fga, base_fta):
    """
    Calculate standing points gained based on given standings

    Uses a linear regression between the stat's value and the stat's standing points. The worst team has standing points = 1 and the best team has standing points = N_TEAMS + 1.

    """
    spg = {}

    for stat in COUNTING_STATS + RATIO_STATS:
        r = linregress(list(range(1, N_TEAMS + 1)), standings[stat].sort_values())

        spg[stat] = r.slope
    
    spg['to'] = -1 * spg['to']
    spg['fgp'] = spg['fg%'] * base_fga
    spg['ftp'] = spg['ft%'] * base_fta

    return spg


def calc_valuation(spg, base_ratio_stats, projections):
    """
    Based on standing points gained, calculate player total value.

    Mod value is the valuation if punting certain categories.

    """
    projections['total_value'] = 0

    for stat in COUNTING_STATS:
        projections[f"{stat}_value"] = projections[stat] / spg[stat]
    
        projections['total_value'] += projections[f"{stat}_value"]
    
    projections["fg%_value"] =  (projections['fg%'] - base_ratio_stats['fg%']) * projections['fga'] / spg['fgp']

    projections["ft%_value"] =  (projections['ft%'] - base_ratio_stats['ft%']) * projections['fta'] / spg['ftp']

    projections['total_value'] += projections["fg%_value"]
    projections['total_value'] += projections["ft%_value"]

    projections['mod_value'] = projections['total_value'] - projections['pts_value'] - projections['3pm_value']
    
    projections.sort_values('mod_value', ascending=False, inplace=True)
    
    return projections


def calc_rankings(standings):
    """
    Based on the given standings, calculate the standing points (rankings)

    """
    rankings = standings.rank()
    rankings['to'] = standings['to'].rank(ascending=False)
    rankings.drop(['fga', 'fgm', 'fta', 'ftm'], axis=1, inplace=True)
    rankings['total'] = rankings.sum(axis=1) - rankings['team_id']
    
    rankings.sort_values('total', ascending=False, inplace=True)

    return rankings


def calc_buffer(standings):
    """
    For each category, what % ahead is my team ahead of the next team?

    """
    standings = standings.copy()
    standings['to'] = -1 * standings['to']

    rankings = standings.rank()  # we don't want to reverse turnovers here

    behind_values = numpy.sort(numpy.array(standings[IMPORTANT_CATS]), axis=0)[
        (rankings[rankings['team_id'] == MY_TEAM_ID][IMPORTANT_CATS].values - 2).flatten().astype(int).tolist(),
        tuple(range(7))
    ]

    my_values = standings[standings['team_id'] == MY_TEAM_ID][IMPORTANT_CATS].values

    pct_behind = numpy.abs(1 - behind_values / my_values).flatten().tolist()

    return dict(zip(IMPORTANT_CATS, pct_behind))


def optimize_roster(projections, standings):
    """
    Swap every player on roster for another team's player and see if that improves the team rank

    """
    # current roster's standings
    final_standings = calc_final_standings(standings, projections)
    final_ranks = calc_rankings(final_standings)
    team_rank = final_ranks.loc[final_ranks['team_id'] == MY_TEAM_ID, 'total'].values[0]
    current_buffer = calc_buffer(final_standings)

    tryouts = []

    Player = namedtuple('Player', 'yahoo_id team_id rank')
    empty_player = Player(yahoo_id=0, team_id=None, rank=None)

    for drop_player in itertools.chain(projections[projections['team_id'] == MY_TEAM_ID].itertuples(), [empty_player]):
        for add_player in itertools.chain(projections[projections['team_id'].isna()].itertuples(), [empty_player]):
            if drop_player != empty_player or add_player != empty_player:
                new_final_ranks, new_final_standings = swap_players(drop_player, add_player, projections, standings)

                new_team_rank = new_final_ranks.loc[new_final_ranks['team_id'] == MY_TEAM_ID, 'total'].values[0]

                changes = (new_final_ranks[new_final_ranks['team_id'] == MY_TEAM_ID] - final_ranks[final_ranks['team_id'] == MY_TEAM_ID]).to_dict('records')[0]
                change_string = ','.join([f"{k}:{v}" for k, v in changes.items() if v != 0])

                if new_team_rank >= team_rank:
                    buffer = calc_buffer(new_final_standings)
                    min_buffer = min(buffer.values())
                    buffer_change = {k: buffer[k] - current_buffer[k] for k in buffer}
                else:
                    min_buffer = None
                    buffer_change = {}

                tryouts.append(dict({
                    'drop_player_id': drop_player.yahoo_id,
                    'add_player_id': add_player.yahoo_id,
                    'add_player_team_id': add_player.team_id,
                    'drop_player_rank': drop_player.rank,
                    'add_player_rank': add_player.rank,
                    'new_team_rank': new_team_rank,
                    'change': change_string,
                    'min_buffer': min_buffer,
                }, **buffer_change))
    
    id_mapping = pandas.read_csv('id_mapping.csv')
    tryouts = pandas.DataFrame(tryouts)
    tryouts = tryouts.merge(id_mapping.rename(columns={'yahoo_name': 'drop_name', 'yahoo_id': 'drop_player_id'})[['drop_player_id', 'drop_name']], on='drop_player_id', how='left')
    tryouts = tryouts.merge(id_mapping.rename(columns={'yahoo_name': 'add_name', 'yahoo_id': 'add_player_id'})[['add_player_id', 'add_name']], on='add_player_id', how='left')
    tryouts.sort_values(['new_team_rank', 'min_buffer'], ascending=[False, False], inplace=True)
    tryouts.to_csv("tryouts.csv", encoding='utf8', index=False, float_format='%.4f')


def swap_players(drop_player, add_player, projections, standings):
    """
    Calculate team ranks based on swapping players between teams

    """
    if add_player is not None:
        projections.loc[projections['yahoo_id'] == add_player.yahoo_id, 'team_id'] = MY_TEAM_ID
    
        if drop_player is not None:
            projections.loc[projections['yahoo_id'] == drop_player.yahoo_id, 'team_id'] = add_player.team_id
    else:  # just dropping a player
        projections.loc[projections['yahoo_id'] == drop_player.yahoo_id, 'team_id'] = None

    final_standings = calc_final_standings(standings, projections)

    final_rank = calc_rankings(final_standings)

    # reverse the team changes
    if add_player is not None:
        projections.loc[projections['yahoo_id'] == add_player.yahoo_id, 'team_id'] = add_player.team_id
    
        if drop_player is not None:
            projections.loc[projections['yahoo_id'] == drop_player.yahoo_id, 'team_id'] = MY_TEAM_ID
    else:
        projections.loc[projections['yahoo_id'] == drop_player.yahoo_id, 'team_id'] = MY_TEAM_ID

    return final_rank, final_standings


if __name__ == '__main__':
    main()
