# Fantasy basketball analysis

Head to head points

## Configuration

Rename `config_sample.py` to `config.py`.

### Set up Yahoo OAUth for access to rosters state

1. [Create a Yahoo app](https://developer.yahoo.com/apps/create/)
1. Update `config.py`
1. Go through authorization code flow to get access token
1. Save refresh token in `config.py`

### League settings

This project assumes that weekly scoring starts on Mondays.

1. Enter the Monday of the first week of the season in `config.py`

## Run order

1. `retrieve_roster.py`
    * Retrieves the current rosters of all teams (using the Yahoo API).
1. `scrape_hashtagbasketball.py`
    * Scrapes hashtagbasketball.com for the latest rest of season projections.
1. `calc_valuation.py`
    * Assigns values to players based on projections and game schedule for the next few weeks and rest of season.
