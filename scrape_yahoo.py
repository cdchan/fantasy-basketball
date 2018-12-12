"""
Scrape projections from Yahoo (at the moment, just for players currently on a roster)

"""

import datetime
import lxml.html
import pandas
import requests
import time


from config import YAHOO_COOKIE_STRING, YAHOO_LEAGUE_ID


def main():
    yahoo_session = requests.Session()
    yahoo_session.headers.update({
        'cookie': YAHOO_COOKIE_STRING,
    })

    projections = scrape_yahoo(yahoo_session)

    today = datetime.datetime.today()

    projections.to_csv("yahoo_projections.csv", encoding='utf8', index=False)
    projections.to_csv("historical/yahoo_projections_{:%Y-%m-%d}.csv".format(today), encoding='utf8', index=False)


def scrape_yahoo(session):
    """
    On Yahoo, the player projections are paginated to 25 players at a time. Loop over the pages.

    """
    # initialize loop
    players = []
    count = 0

    get_next = True

    while get_next:
        print count

        x = session.get("https://basketball.fantasysports.yahoo.com/nba/{league}/players?&sort=AR&sdir=1&status=T&pos=P&stat1=S_PSR&jsenabled=0&count={count}".format(league=YAHOO_LEAGUE_ID, count=count))

        root = lxml.html.fromstring(x.content)

        # take all the table rows that represent players
        player_table_rows = root.cssselect('div.players tbody tr')

        # mapping between column number and the stat on Yahoo's page
        stats_mapping = {
            6: 'gtp',
            11: 'pts',
            12: 'treb',
            13: 'ast',
            14: 'blk',
            15: 'stl',
            16: 'to'
        }

        # loop over the player table rows to extract the projections player by player
        # this is finicky and could break if Yahoo changes their formatting
        for player_tr in player_table_rows:
            player = {}

            player['abbr_name'] = player_tr.cssselect('.ysf-player-name a')[0].text_content()

            player['yahoo_id'] = player_tr.cssselect('.ysf-player-name a')[0].get('href').split('/')[-1]

            for index, stat in stats_mapping.iteritems():
                player[stat] = player_tr.cssselect('td')[index].text_content()

            players.append(player)

        # check if the "next page" text links to the next page
        # if not, end while loop
        if not root.cssselect('ul#playerspagenav1 li')[1].getchildren():
            get_next = False
        else:
            count += 25

        time.sleep(1)  # be respectful of possible rate limits

    projections = pandas.DataFrame(players)

    return projections


if __name__ == '__main__':
    main()
