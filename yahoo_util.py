"""
Yahoo API utility functions

"""
import json

from lxml import etree
from rauth import OAuth2Service

from config import YAHOO_CLIENT_ID, YAHOO_CLIENT_SECRET, yahoo_refresh_token


NS = {'f': 'http://fantasysports.yahooapis.com/fantasy/v2/base.rng'}


def create_yahoo_service():
    """
    Set up Yahoo OAuth service

    See https://rauth.readthedocs.io/en/latest/api/#oauth-2-0-sessions
    """
    yahoo = OAuth2Service(
        client_id=YAHOO_CLIENT_ID,
        client_secret=YAHOO_CLIENT_SECRET,
        name='yahoo',
        authorize_url='https://api.login.yahoo.com/oauth2/request_auth',
        access_token_url='https://api.login.yahoo.com/oauth2/get_token',
        base_url='https://api.login.yahoo.com/'
    )

    return yahoo


def get_yahoo_session():
    """
    Set up OAuth to get an authorized session

    This uses rauth but hope to change to requests_oauthlib if I can get that to work

    """
    yahoo = create_yahoo_service()

    session = yahoo.get_auth_session(
        data={
            'refresh_token': yahoo_refresh_token,
            'redirect_uri': 'oob',
            'grant_type': 'refresh_token',
        },
        decoder=json_decoder
    )

    return session


def json_decoder(content):
    """
    Decodes bytestrings, then loads JSON
    """
    str_content = content.decode('utf-8')
    return json.loads(str_content)


def get_sport_id():
    session = get_yahoo_session()

    r = session.get('https://fantasysports.yahooapis.com/fantasy/v2/game/nba')

    root = etree.fromstring(r.content)

    game_id = root.xpath("//f:game_id", namespaces=NS)[0].text

    print(f"Yahoo game id = {game_id}")


if __name__ == '__main__':
    get_sport_id()
