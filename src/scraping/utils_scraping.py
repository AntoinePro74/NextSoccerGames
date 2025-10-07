def get_season(league:dict):
    if league["Season format"]=="european":
        season="2025-2026"
        last_season="2024-2025"
    else:
        season="2025"
        last_season="2024"

    return season,last_season

def get_urls(league:dict)->tuple:
    fbref_id = league["FBref id"]
    fbref_slug = league["FBref slug"]
    season,last_season = get_season(league)
    url_current = f"https://fbref.com/en/comps/{fbref_id}/{season}/schedule/{season}-{fbref_slug}-Scores-and-Fixtures"
    url_previous= f"https://fbref.com/en/comps/{fbref_id}/{last_season}/schedule/{last_season}-{fbref_slug}-Scores-and-Fixtures"

    return url_current,url_previous