"""
Get OAuth refresh token from Yahoo

"""

import json


from rauth import OAuth2Service


from config import YAHOO_CLIENT_ID, YAHOO_CLIENT_SECRET


def main():
    # https://rauth.readthedocs.io/en/latest/api/#oauth-2-0-sessions
    yahoo = OAuth2Service(
        client_id=YAHOO_CLIENT_ID,
        client_secret=YAHOO_CLIENT_SECRET,
        name='yahoo',
        authorize_url='https://api.login.yahoo.com/oauth2/request_auth',
        access_token_url='https://api.login.yahoo.com/oauth2/get_token',
        base_url='https://api.login.yahoo.com/'
    )

    params = {
        'response_type': 'code',
        'redirect_uri': 'oob'
    }

    url = yahoo.get_authorize_url(**params)

    print "Go to url: {}".format(url)

    auth_code = raw_input("Please enter code: ")

    session = yahoo.get_auth_session(
        data={
            'code': auth_code,
            'redirect_uri': 'oob',
            'grant_type': 'authorization_code',
        },
        decoder=json.loads
    )

    print "Set refresh token in config.py: {}".format(session.access_token_response.json()['refresh_token'])


if __name__ == '__main__':
    main()
