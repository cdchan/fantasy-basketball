"""
Calculate roto league valuations for the rest of season

"""

import pandas

from scipy.stats import linregress

from calc_h2h_points import load_rosters, load_projections
from config import MY_TEAM_ID, N_TEAMS


COUNTING_STATS = ['3pm', 'pts', 'treb', 'ast', 'stl', 'blk', 'to']
RATIO_STATS = ['fg%', 'ft%']
RATIO_STATS_PARTS = ['fga', 'fgm', 'fta', 'ftm']


def main():
    ros = combine_projections()

    # add team id to projections
    rosters = load_rosters()
    ros = ros.merge(rosters[['yahoo_id', 'team_id']], on='yahoo_id', how='left')

    standings = load_standings()
    final_standings = calc_final_standings(standings, ros)
    print(final_standings)

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
    cols = ['yahoo_name', 'yahoo_id', 'team_id', 'rank', 'gtp', 'mpg', 'total_value', 'mod_value', 'pts_value', '3pm_value', 'fg%_value', 'ft%_value', 'treb_value', 'ast_value', 'stl_value', 'blk_value', 'to_value']
    print(ros_values[ros_values['team_id'] == MY_TEAM_ID][cols])
    # print best available free agents
    print(ros_values[ros_values['team_id'].isna()].head(15)[cols])
    # output valuations
    ros_values[cols].to_csv("ros_values.csv", encoding='utf8', index=False)

    ros_by_team = ros_values.groupby('team_id').sum().reset_index()
    ros_by_team.sort_values('total_value', ascending=False, inplace=True)

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

    # override playing time projections with manual ones if necessary
    gtp_manual = pandas.read_csv('gtp_manual.csv')
    gtp_manual.drop('name', axis=1, inplace=True)
    ros_rate = ros_rate.merge(gtp_manual, on='yahoo_id', how='left')
    ros_rate['gtp'] = ros_rate['gtp_override'].combine_first(ros_rate['gtp'])

    ros = ros_rate[['yahoo_name', 'yahoo_id', 'rank', 'gtp', 'mpg', 'fg%', 'ft%']].copy()
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


def calc_final_standings(standings, projections):
    """
    Given current standings and rest of season player projections, calculate the final standings

    """
    ros_by_team = projections.groupby('team_id').sum().reset_index()

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
    rankings = pandas.DataFrame({'team_id': standings['team_id'], 'total': 0})

    for stat in COUNTING_STATS + RATIO_STATS:
        if stat != 'to':  # for turnovers, fewer is better
            ordered_stat = standings.sort_values(stat)[['team_id', stat]].copy()
        else:
            ordered_stat = standings.sort_values(stat, ascending=False)[['team_id', stat]].copy()
        
        ordered_stat[f"{stat}_ranking"] = list(range(1, N_TEAMS + 1))

        ordered_stat.drop(stat, axis=1, inplace=True)

        rankings = rankings.merge(ordered_stat, on='team_id')
    
        rankings['total'] += rankings[f"{stat}_ranking"]
    
    rankings.sort_values('total', ascending=False, inplace=True)

    return rankings


def optimize_roster(projections, standings):
    """
    Swap every player on roster for another team's player and see if that improves the team rank

    """
    tryouts = []

    for drop_player in projections[projections['team_id'] == MY_TEAM_ID].itertuples():
        for add_player in projections[projections['team_id'] != 7].itertuples():
            new_final_rank = swap_players(drop_player, add_player, projections, standings)

            tryouts.append({
                'drop_player_id': drop_player.yahoo_id,
                'add_player_id': add_player.yahoo_id,
                'add_player_team_id': add_player.team_id,
                'drop_player_rank': drop_player.rank,
                'add_player_rank': add_player.rank,
                'new_team_rank': new_final_rank.loc[new_final_rank['team_id'] == 7, 'total'].values[0],
            })
    
    id_mapping = pandas.read_csv('id_mapping.csv')
    tryouts = pandas.DataFrame(tryouts)
    tryouts = tryouts.merge(id_mapping.rename(columns={'yahoo_name': 'drop_name', 'yahoo_id': 'drop_player_id'})[['drop_player_id', 'drop_name']], on='drop_player_id', how='left')
    tryouts = tryouts.merge(id_mapping.rename(columns={'yahoo_name': 'add_name', 'yahoo_id': 'add_player_id'})[['add_player_id', 'add_name']], on='add_player_id', how='left')
    tryouts.sort_values('new_team_rank', ascending=False, inplace=True)
    tryouts.to_csv("tryouts.csv", encoding='utf8', index=False)


def swap_players(drop_player, add_player, projections, standings):
    """
    Calculate team ranks based on swapping players between teams

    """
    projections = projections.copy()

    projections.loc[projections['yahoo_id'] == drop_player.yahoo_id, 'team_id'] = add_player.team_id
    projections.loc[projections['yahoo_id'] == add_player.yahoo_id, 'team_id'] = MY_TEAM_ID

    final_standings = calc_final_standings(standings, projections)

    final_rank = calc_rankings(final_standings)

    return final_rank


if __name__ == '__main__':
    main()
