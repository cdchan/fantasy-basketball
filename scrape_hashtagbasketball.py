"""
Scrape projections from Hashtag Basketball

"""

import datefinder
import lxml.html
import pandas
import requests


from datetime import datetime


def main():
    projections_page = download_projections_page()

    root = lxml.html.fromstring(projections_page)  # parse HTML

    projections = extract_projections(root)

    updated_at_string = "{:%Y-%m-%d}".format(extract_updated_at(root))

    projections.to_csv("projections.csv".format(updated_at_string), encoding='utf8', index=False)
    projections.to_csv("historical/projections_{}.csv".format(updated_at_string), encoding='utf8', index=False)


def download_projections_page():
    """
    Download projections HTML page from Hashtag Basketball

    """
    r = requests.get('https://hashtagbasketball.com/fantasy-basketball-projections')

    return r.text


def extract_projections(root):
    """
    Given parsed HTML of projections page, extract the projections

    """
    players = []

    rows = root.cssselect('#ContentPlaceHolder1_GridView1 tr')

    # get column headers for each stat
    columns = []

    for col in rows[0].cssselect('th'):
        columns.append(col.text_content().lower())

    for row in rows:
        player = {}

        for cell, col in zip(row.cssselect('td'), columns):
            player[col] = cell.text_content().strip()

        if player and player['r#'] != 'R#':  # strip out tables rows that are just column headers
            players.append(player)

    projections = pandas.DataFrame(players)

    projections = projections.rename(columns={'player': 'name'})  # rename the 'player' column to 'name'

    projections['name'] = projections['name'].str.replace('.', '')  # take out any periods in a player name

    return projections


def extract_updated_at(root):
    """
    Get date when projections were last updated

    """
    updated_at_html = root.cssselect('#form1 > section > div > div.heading-pricing > span > small')

    possible_dates = datefinder.find_dates(updated_at_html[0].text_content().split('by')[0])  # the "by" is giving datefinder problems

    updated_at_datetime = next(possible_dates)

    return updated_at_datetime


if __name__ == '__main__':
    main()
