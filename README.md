# Fantasy basketball analysis

Head to head points

## Environment

To use Docker:

```sh
docker-compose build
docker-compose run fbball bash
```

## Configuration

Rename `config_sample.py` to `config.py`.

### Set up Yahoo OAUth for access to rosters state

1. [Create a Yahoo app](https://developer.yahoo.com/apps/create/)
1. Update `config.py`
1. Run `get_refresh_token.py` to go through authorization code flow to get access token
1. Save refresh token in `config.py`

### League settings

Update `config.py` with the following league settings:

1. Set the sport / season id in `YAHOO_SPORT_ID`
    * `python yahoo.util.py` will print the sport / season id.
1. Set the league id in `YAHOO_LEAGUE_ID`
1. (optional if scraping from Yahoo)
    * Set a Yahoo cookie in `YAHOO_COOKIE_STRING`
    * Set the column number of stats in the player projections page in `YAHOO_STATS_MAPPING`

## Run order

1. `retrieve_roster.py`
    * Retrieves the current rosters of all teams (using the Yahoo API).
1. `scrape_hashtagbasketball.py`
    * Scrapes hashtagbasketball.com for the latest rest of season projections.

### For head to head

1. If head to head, enter the Monday of the first week of the season in `SEASON_START`
    * These scripts assume that weekly scoring starts on Mondays
1. Update `schedule_{current year}.csv` with the correct schedule for the current season.
    * Update `calc_h2h_points.py` to use the right schedule.
1. `calc_h2h_points.py`
    * Assigns values to players for a head to head points league based on projections and game schedule for the next few weeks and rest of season.

### For roto

1. `scrape_yahoo.py`
    * Using a Yahoo cookie, scrape the Yahoo rest of season projections for all players currently on a roster.
1. `retrieve_standings.py`
    * Get current roto standings in league
1. `calc_roto.py`
    * Outputs player valuations and which players to acquire
