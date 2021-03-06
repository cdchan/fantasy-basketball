"""
Retrieve the roto standings from Yahoo

"""

import datetime

import pandas
from lxml import etree

from config import YAHOO_LEAGUE_ID, YAHOO_SPORT_ID 
from yahoo_util import get_yahoo_session, NS


STATS_TYPES = {
    'gp': 'int',
    'fg%': 'float',
    'ft%': 'float',
    '3ptm': 'int',
    'pts': 'int',
    'reb': 'int',
    'ast': 'int',
    'st': 'int',
    'blk': 'int',
    'to': 'int',
}


def get_stats(session):
    url = f'https://fantasysports.yahooapis.com/fantasy/v2/league/{YAHOO_SPORT_ID}.l.{YAHOO_LEAGUE_ID}/settings'

    r = session.get(url)

    root = etree.fromstring(r.content)

    stats_mapping = {}

    for stat in root.xpath("//f:stat", namespaces=NS):
        stats_mapping[stat.findtext("f:stat_id", namespaces=NS)] = stat.findtext("f:display_name", namespaces=NS)
    
    stats_mapping['0'] = 'GP'

    return stats_mapping


def get_standings(session, stats_mapping):
    url = f'https://fantasysports.yahooapis.com/fantasy/v2/league/{YAHOO_SPORT_ID}.l.{YAHOO_LEAGUE_ID}/standings'

    r = session.get(url)

    root = etree.fromstring(r.content)

    standings = []

    for team in root.xpath("//f:team", namespaces=NS):
        stats = {}
        for stat in team.xpath("f:team_stats//f:stat", namespaces=NS):
            stats[
                stats_mapping.get(stat.findtext("f:stat_id", namespaces=NS), 'unknown').lower()
            ] = stat.findtext("f:value", namespaces=NS)
        
        stats['team_id'] = team.findtext("f:team_id", namespaces=NS)
        standings.append(stats)
    
    standings = pandas.DataFrame(standings)

    for stat_name, value_type in STATS_TYPES.items():
        standings[stat_name] =  standings[stat_name].astype(value_type)
    
    fg = standings['fgm/a'].str.split('/', n=1, expand=True)
    standings['fgm'] = fg[0]
    standings['fga'] = fg[1]

    ft = standings['ftm/a'].str.split('/', n=1, expand=True)
    standings['ftm'] = ft[0]
    standings['fta'] = ft[1]

    standings.drop('fgm/a', axis=1, inplace=True)  
    standings.drop('ftm/a', axis=1, inplace=True)  
    
    return standings


def main():
    session = get_yahoo_session()

    stats_mapping = get_stats(session)

    standings = get_standings(session, stats_mapping)

    today = datetime.datetime.today()

    standings.to_csv("standings.csv", encoding='utf8', index=False)
    standings.to_csv("historical/standings_{:%Y-%m-%d}.csv".format(today), encoding='utf8', index=False)


if __name__ == '__main__':
    main()
