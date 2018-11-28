"""
Use Yahoo API to get rosters for today

"""

import datetime
import json
import pandas


from lxml import etree
from rauth import OAuth2Service


from config import YAHOO_CLIENT_ID, YAHOO_CLIENT_SECRET, yahoo_refresh_token


def main():
    today = "{:%Y-%m-%d}".format(datetime.datetime.today())

    session = get_yahoo_session()

    ns = {'f': 'http://fantasysports.yahooapis.com/fantasy/v2/base.rng'}

    # https://developer.yahoo.com/fantasysports/guide/#id47

    players = []

    url = "https://fantasysports.yahooapis.com/fantasy/v2/team/385.l.139091.t.{team_id}/roster;date={date}"

    for team_id in range(1, 9):
        r = session.get(url.format(team_id=team_id, date=today))

        root = etree.fromstring(r.content)

        for player in root.xpath("//f:player", namespaces=ns):
            players.append({
                'team_id': team_id,
                'yahoo_id': player.findtext("f:player_id", namespaces=ns),
                'name': player.findtext("f:name/f:full", namespaces=ns).replace('.', '')
            })

    rosters = pandas.DataFrame(players)

    rosters.to_csv('rosters.csv'.format(today), encoding='utf8', index=False)
    rosters.to_csv('historical/rosters_{}.csv'.format(today), encoding='utf8', index=False)


def get_yahoo_session():
    """
    Set up OAuth to get an authorized session

    This uses rauth but hope to change to requests_oauthlib if I can get that to work

    """
    yahoo = OAuth2Service(
        client_id=YAHOO_CLIENT_ID,
        client_secret=YAHOO_CLIENT_SECRET,
        name='yahoo',
        authorize_url='https://api.login.yahoo.com/oauth2/request_auth',
        access_token_url='https://api.login.yahoo.com/oauth2/get_token',
        base_url='https://api.login.yahoo.com/'
    )

    session = yahoo.get_auth_session(
        data={
            'refresh_token': yahoo_refresh_token,
            'redirect_uri': 'oob',
            'grant_type': 'refresh_token',
        },
        decoder=json.loads
    )

    return session


if __name__ == '__main__':
    main()
