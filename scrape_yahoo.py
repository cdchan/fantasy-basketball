"""
Scrape player projections from Yahoo

"""
import argparse
import datetime

import lxml.html
import pandas
import requests
import time

from config import YAHOO_COOKIE_STRING, YAHOO_LEAGUE_ID, YAHOO_STATS_TRANSLATION


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ros", action="store_true", help="only scrape rest of season projections")
    parser.add_argument("--l14pt", action="store_true", help="only scrape recent stats in the past 14 days")
    args = parser.parse_args()

    today = datetime.datetime.today()

    yahoo_session = requests.Session()
    yahoo_session.headers.update({
        'cookie': YAHOO_COOKIE_STRING,
    })

    if not args.l14pt:
        # PSR = rest of season projections
        projections = scrape_yahoo_player_list(yahoo_session, 'PSR')

        projections.to_csv("yahoo_projections.csv", encoding='utf8', index=False)
        projections.to_csv("historical/yahoo_projections_{:%Y-%m-%d}.csv".format(today), encoding='utf8', index=False)

    if not args.ros:
        # AL14 = last 14 days
        playing_time = scrape_yahoo_player_list(yahoo_session, 'AL14')

        playing_time.to_csv("yahoo_playing_time.csv", encoding='utf8', index=False)
        playing_time.to_csv("historical/yahoo_playing_time_{:%Y-%m-%d}.csv".format(today), encoding='utf8', index=False)


def scrape_yahoo_player_list(session, list_code):
    """
    On Yahoo, the player projections are paginated to 25 players at a time. Loop over the pages.

    """
    # initialize loop
    players = []
    count = 0

    get_next = True

    while get_next:
        print(count)

        x = session.get(f"https://basketball.fantasysports.yahoo.com/nba/{YAHOO_LEAGUE_ID}/players?&sort=AR&sdir=1&status=ALL&pos=P&stat1=S_{list_code}&jsenabled=0&count={count}")

        root = lxml.html.fromstring(x.content)

        # maps from column number to stat
        header_index = parse_table_header(YAHOO_STATS_TRANSLATION, root)

        # take all the table rows that represent players
        player_table_rows = root.cssselect('div.players tbody tr')

        # loop over the player table rows to extract the projections player by player
        for player_tr in player_table_rows:
            player = {}

            player['abbr_name'] = player_tr.cssselect('.ysf-player-name a')[0].text_content()

            player['yahoo_id'] = player_tr.cssselect('.ysf-player-name a')[0].get('href').split('/')[-1]

            for index, stat in header_index.items():
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


def parse_table_header(stats_translation, root):
    """
    Use table headings to map from index position to stat

    This is finicky and could break when Yahoo changes their table headers.
    
    """
    header_index = {}
    
    header_row = root.cssselect('div.players thead tr.Last')[0]
    
    for i, header_cell in enumerate(header_row.cssselect('th')):
        text = header_cell.text_content()
        if text in stats_translation.keys():
            header_index[i] = stats_translation[text]
    
    return header_index


if __name__ == '__main__':
    main()
