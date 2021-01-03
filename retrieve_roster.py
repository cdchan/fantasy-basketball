"""
Use Yahoo API to get rosters for Monday (whether today or the next closest Monday)

"""

import datetime
import pandas

from lxml import etree
from rauth import OAuth2Service

from config import YAHOO_SPORT_ID, YAHOO_LEAGUE_ID, N_TEAMS
from yahoo_util import get_yahoo_session


def main():
    monday = "{:%Y-%m-%d}".format(find_closest_monday())

    session = get_yahoo_session()

    ns = {'f': 'http://fantasysports.yahooapis.com/fantasy/v2/base.rng'}

    # https://developer.yahoo.com/fantasysports/guide/#id47

    players = []

    base_url = "https://fantasysports.yahooapis.com/fantasy/v2/team/{sport_id}.l.{league_id}".format(sport_id=YAHOO_SPORT_ID, league_id=YAHOO_LEAGUE_ID)
    url = base_url + ".t.{team_id}/roster;date={date}"

    for team_id in range(1, N_TEAMS + 1):
        r = session.get(url.format(team_id=team_id, date=monday))

        root = etree.fromstring(r.content)

        for player in root.xpath("//f:player", namespaces=ns):
            players.append({
                'team_id': team_id,
                'yahoo_id': player.findtext("f:player_id", namespaces=ns),
                'name': player.findtext("f:name/f:full", namespaces=ns).replace('.', '')
            })

    rosters = pandas.DataFrame(players)

    if len(rosters) == 0:
        raise Exception('Failed to retrieve roster')
    else:
        rosters.to_csv('rosters.csv', encoding='utf8', index=False)
        rosters.to_csv('historical/rosters_{}.csv'.format(monday), encoding='utf8', index=False)


def find_closest_monday():
    """
    Find the closest Monday for an accurate roster. Rosters are set at the beginning of each week.

    """
    today = datetime.datetime.today()

    days_ahead = 7 - today.weekday()  # Monday = 0

    if days_ahead == 7:
        return today
    else:
        return today + datetime.timedelta(days_ahead)


if __name__ == '__main__':
    main()
