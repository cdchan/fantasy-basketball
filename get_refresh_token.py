"""
Get OAuth refresh token from Yahoo

"""
from config import YAHOO_CLIENT_ID, YAHOO_CLIENT_SECRET
from yahoo_util import create_yahoo_service, json_decoder


def main():
    yahoo = create_yahoo_service()

    params = {
        'response_type': 'code',
        'redirect_uri': 'oob'
    }

    url = yahoo.get_authorize_url(**params)

    print("Go to url: {}".format(url))

    auth_code = input("Please enter code: ")

    session = yahoo.get_auth_session(
        data={
            'code': auth_code,
            'redirect_uri': 'oob',
            'grant_type': 'authorization_code',
        },
        decoder=json_decoder
    )

    print("Set refresh token in config.py: {}".format(session.access_token_response.json()['refresh_token']))


if __name__ == '__main__':
    main()
