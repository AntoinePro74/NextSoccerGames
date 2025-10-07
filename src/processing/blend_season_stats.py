import pandas as pd

def calculate_dynamic_weights(matchday: int, transition_start: int = 5, transition_end: int = 10) -> int:
    """
    Calculate the weights for blending previous and current season stats.

    Parameters
    ----------
    matchday : int
        Current matchday of the season.
    transition_start : int, optional
        Matchday when we start blending current season data (default is 5).
    transition_end : int, optional
        Matchday when we fully switch to current season data (default is 10).

    Returns
    -------
    dict
        A dictionary with the weights for 'previous' and 'current' season.
    """
    if matchday <= transition_start:
        return 0.0
    elif matchday >= transition_end:
        return 1.0
    else:
        return (matchday - transition_start) / (transition_end - transition_start)
    
def get_matchday(df_current: pd.DataFrame) -> int:
    """
    Estimate the current matchday based on the max number of matches played (home + away).
    If df_current is empty, returns 0.
    """
    if df_current.empty:
        return 0  # or raise ValueError("df_current is empty")

    if "MP_home" not in df_current.columns or "MP_away" not in df_current.columns:
        raise ValueError("Missing MP_home or MP_away columns in df_current")
    
    return int((df_current["MP_home"] + df_current["MP_away"]).max())

def compute_recent_form(df_matches: pd.DataFrame, last_n: int = 5) -> pd.DataFrame:
    """
    Compute recent form (GF and GA) per team over last N matches.
    Assumes df_matches has columns: ['Date', 'Home', 'Away', 'home_goal', 'away_goal']
    """
    if df_matches.empty:
        # Return an empty DataFrame with all expected columns
        return pd.DataFrame(columns=[
            'Team',
            'GF_home_form', 'GA_home_form', 'GF_away_form', 'GA_away_form',
            'MP_home_form', 'MP_away_form',
            'GF_per_home_form', 'GA_per_home_form',
            'GF_per_away_form', 'GA_per_away_form'
        ])

    recent_data = []

    teams = pd.unique(df_matches[['Home', 'Away']].values.ravel())
    df_matches = df_matches.sort_values('Date')

    for team in teams:
        # Matches played by the team
        mask = (df_matches['Home'] == team) | (df_matches['Away'] == team)
        team_matches = df_matches[mask].tail(last_n)

        gf_home = team_matches.loc[team_matches['Home'] == team, 'home_goal'].sum()
        ga_home = team_matches.loc[team_matches['Home'] == team, 'away_goal'].sum()
        mp_home = team_matches.loc[team_matches['Home'] == team].shape[0]

        gf_away = team_matches.loc[team_matches['Away'] == team, 'away_goal'].sum()
        ga_away = team_matches.loc[team_matches['Away'] == team, 'home_goal'].sum()
        mp_away = team_matches.loc[team_matches['Away'] == team].shape[0]

        form_stats = {
            'Team': team,
            'GF_home_form': gf_home,
            'GA_home_form': ga_home,
            'GF_away_form': gf_away,
            'GA_away_form': ga_away,
            'MP_home_form': mp_home,
            'MP_away_form': mp_away,
        }
        recent_data.append(form_stats)

    df_form = pd.DataFrame(recent_data)

    # Avoid division by zero
    df_form['GF_per_home_form'] = df_form['GF_home_form'] / df_form['MP_home_form'].replace(0, 1)
    df_form['GA_per_home_form'] = df_form['GA_home_form'] / df_form['MP_home_form'].replace(0, 1)
    df_form['GF_per_away_form'] = df_form['GF_away_form'] / df_form['MP_away_form'].replace(0, 1)
    df_form['GA_per_away_form'] = df_form['GA_away_form'] / df_form['MP_away_form'].replace(0, 1)

    return df_form

def blend_season_stats(
    df_previous: pd.DataFrame,
    df_current: pd.DataFrame,
    df_matches: pd.DataFrame,
    promoted_teams: list,
    current_weight: float = None,
    promoted_weight: float = 0.7,
    form_weight: float = 0.5
) -> pd.DataFrame:
    """
    Blend stats from previous and current season with promoted teams handling.
    Handles the case where df_current is empty.
    """

    # Detect matchday and weight
    if current_weight is None and not df_current.empty:
        matchday = get_matchday(df_current)
        current_weight = calculate_dynamic_weights(matchday)
        print(f"[INFO] Matchday detected: {matchday}, dynamic weight applied: {current_weight:.2f}")
    else:
        current_weight = current_weight or 0
        print(f"[INFO] No current season data -> weight set to 0")

    # Ensure required columns exist
    required_columns = ["Team", "GF_home", "GA_home", "GF_away", "GA_away", "MP_home", "MP_away"]
    for df in [df_previous, df_current]:
        for col in required_columns:
            if col not in df.columns:
                df[col] = 0

    # League and bottom stats for promoted teams
    league_avg = {
        "GF_home": df_previous["GF_home"].sum() / max(df_previous["MP_home"].sum(), 1),
        "GA_home": df_previous["GA_home"].sum() / max(df_previous["MP_home"].sum(), 1),
        "GF_away": df_previous["GF_away"].sum() / max(df_previous["MP_away"].sum(), 1),
        "GA_away": df_previous["GA_away"].sum() / max(df_previous["MP_away"].sum(), 1),
    }

    bottom_teams = df_previous.nsmallest(3, "GF_home")
    bottom_stats = {
        "GF_home": bottom_teams["GF_home"].sum() / max(bottom_teams["MP_home"].sum(), 1),
        "GA_home": bottom_teams["GA_home"].sum() / max(bottom_teams["MP_home"].sum(), 1),
        "GF_away": bottom_teams["GF_away"].sum() / max(bottom_teams["MP_away"].sum(), 1),
        "GA_away": bottom_teams["GA_away"].sum() / max(bottom_teams["MP_away"].sum(), 1),
    }

    # Merge previous and current season
    df_merged = pd.merge(df_previous, df_current, on="Team", how="outer", suffixes=("_prev", "_curr"))

    df_form = compute_recent_form(df_matches, last_n=5)
    df_merged = pd.merge(df_merged, df_form, on="Team", how="left")

    # Add promoted teams if missing (when df_current is empty)
    for team in promoted_teams:
        if team not in df_merged["Team"].values:
            df_merged = pd.concat([df_merged, pd.DataFrame([{"Team": team}])], ignore_index=True)

    blended_rows = []
    for _, row in df_merged.iterrows():
        team = row["Team"]

        if team in promoted_teams:
            if df_current.empty or pd.isna(row.get("GF_home_curr", None)):
                # Promoted and no matches played
                blended_stats = {
                    "Team": team,
                    "GF_home": promoted_weight * league_avg["GF_home"] + (1 - promoted_weight) * bottom_stats["GF_home"],
                    "GA_home": promoted_weight * league_avg["GA_home"] + (1 - promoted_weight) * bottom_stats["GA_home"],
                    "GF_away": promoted_weight * league_avg["GF_away"] + (1 - promoted_weight) * bottom_stats["GF_away"],
                    "GA_away": promoted_weight * league_avg["GA_away"] + (1 - promoted_weight) * bottom_stats["GA_away"],
                    "MP_home": 1,
                    "MP_away": 1,
                }
            else:
                # Promoted with matches played
                # Retrieve form stats
                gf_home_form = row.get("GF_per_home_form", row["GF_home_curr"] / max(row["MP_home_curr"], 1))
                ga_home_form = row.get("GA_per_home_form", row["GA_home_curr"] / max(row["MP_home_curr"], 1))
                gf_away_form = row.get("GF_per_away_form", row["GF_away_curr"] / max(row["MP_away_curr"], 1))
                ga_away_form = row.get("GA_per_away_form", row["GA_away_curr"] / max(row["MP_away_curr"], 1))

                # Combine current season and recent form
                gf_home_combined = form_weight * gf_home_form + (1 - form_weight) * (row["GF_home_curr"] / max(row["MP_home_curr"], 1))
                ga_home_combined = form_weight * ga_home_form + (1 - form_weight) * (row["GA_home_curr"] / max(row["MP_home_curr"], 1))
                gf_away_combined = form_weight * gf_away_form + (1 - form_weight) * (row["GF_away_curr"] / max(row["MP_away_curr"], 1))
                ga_away_combined = form_weight * ga_away_form + (1 - form_weight) * (row["GA_away_curr"] / max(row["MP_away_curr"], 1))

                blended_stats = {
                    "Team": team,
                    "GF_home": current_weight * gf_home_combined * max(row["MP_home_curr"], 1) + (1 - current_weight) * (
                        promoted_weight * league_avg["GF_home"] + (1 - promoted_weight) * bottom_stats["GF_home"]),
                    "GA_home": current_weight * ga_home_combined * max(row["MP_home_curr"], 1) + (1 - current_weight) * (
                        promoted_weight * league_avg["GA_home"] + (1 - promoted_weight) * bottom_stats["GA_home"]),
                    "GF_away": current_weight * gf_away_combined * max(row["MP_away_curr"], 1) + (1 - current_weight) * (
                        promoted_weight * league_avg["GF_away"] + (1 - promoted_weight) * bottom_stats["GF_away"]),
                    "GA_away": current_weight * ga_away_combined * max(row["MP_away_curr"], 1) + (1 - current_weight) * (
                        promoted_weight * league_avg["GA_away"] + (1 - promoted_weight) * bottom_stats["GA_away"]),
                    "MP_home": max(1, row["MP_home_curr"]),
                    "MP_away": max(1, row["MP_away_curr"]),
                }
        elif pd.isna(row.get("GF_home_curr", None)):
            # No match this season yet
            blended_stats = {
                "Team": team,
                "GF_home": row["GF_home_prev"],
                "GA_home": row["GA_home_prev"],
                "GF_away": row["GF_away_prev"],
                "GA_away": row["GA_away_prev"],
                "MP_home": row["MP_home_prev"],
                "MP_away": row["MP_away_prev"],
            }
        else:
            # Regular team with matches
            # Retrieve form stats
            gf_home_form = row.get("GF_per_home_form", row["GF_home_curr"] / max(row["MP_home_curr"], 1))
            ga_home_form = row.get("GA_per_home_form", row["GA_home_curr"] / max(row["MP_home_curr"], 1))
            gf_away_form = row.get("GF_per_away_form", row["GF_away_curr"] / max(row["MP_away_curr"], 1))
            ga_away_form = row.get("GA_per_away_form", row["GA_away_curr"] / max(row["MP_away_curr"], 1))

            # Combine current season and recent form
            gf_home_combined = form_weight * gf_home_form + (1 - form_weight) * (row["GF_home_curr"] / max(row["MP_home_curr"], 1))
            ga_home_combined = form_weight * ga_home_form + (1 - form_weight) * (row["GA_home_curr"] / max(row["MP_home_curr"], 1))
            gf_away_combined = form_weight * gf_away_form + (1 - form_weight) * (row["GF_away_curr"] / max(row["MP_away_curr"], 1))
            ga_away_combined = form_weight * ga_away_form + (1 - form_weight) * (row["GA_away_curr"] / max(row["MP_away_curr"], 1))

            # Final blend with previous season
            blended_stats = {
                "Team": team,
                "GF_home": (1 - current_weight) * row["GF_home_prev"] + current_weight * gf_home_combined * max(row["MP_home_curr"], 1),
                "GA_home": (1 - current_weight) * row["GA_home_prev"] + current_weight * ga_home_combined * max(row["MP_home_curr"], 1),
                "GF_away": (1 - current_weight) * row["GF_away_prev"] + current_weight * gf_away_combined * max(row["MP_away_curr"], 1),
                "GA_away": (1 - current_weight) * row["GA_away_prev"] + current_weight * ga_away_combined * max(row["MP_away_curr"], 1),
                "MP_home": max(1, (1 - current_weight) * row["MP_home_prev"] + current_weight * row["MP_home_curr"]),
                "MP_away": max(1, (1 - current_weight) * row["MP_away_prev"] + current_weight * row["MP_away_curr"]),
            }

        blended_rows.append(blended_stats)

    df_blend = pd.DataFrame(blended_rows)
    df_blend.fillna(0, inplace=True)

    df_blend["GF_per_home"] = df_blend["GF_home"] / df_blend["MP_home"]
    df_blend["GA_per_home"] = df_blend["GA_home"] / df_blend["MP_home"]
    df_blend["GF_per_away"] = df_blend["GF_away"] / df_blend["MP_away"]
    df_blend["GA_per_away"] = df_blend["GA_away"] / df_blend["MP_away"]

    return df_blend

