import os
import pandas as pd
import streamlit as st
import json
import time

from src.scraping.api_sorare import fetch_gameweeks
from src.scraping.utils_scraping import get_season, get_urls
from src.scraping.fbref_scraper import extract_fbref_schedule_table
from src.processing.utils_processing import clean_fbref_matches, calculate_poisson_metrics, extract_future_matches,extract_french_time,combine_date_time
from src.processing.blend_season_stats import blend_season_stats
from src.processing.compute_probabilities import analyze_gameweek

def process_league(league):
    # Create directories if missing
    os.makedirs("data/raw", exist_ok=True)
    os.makedirs("data/processed", exist_ok=True)
    os.makedirs("data/team_stats", exist_ok=True)
    os.makedirs("data/upcoming_matches", exist_ok=True)
    os.makedirs("data/analysis", exist_ok=True)
    os.makedirs("data/exports", exist_ok=True)

    fetch_gameweeks()

    url_current, url_previous = get_urls(league)
    season, last_season = get_season(league)

    # Scraping
    df_matches_current = extract_fbref_schedule_table(url_current)
    df_matches_current.to_csv(f"data/raw/{league['Sorare League']}_{season}_matches_raw_data.csv", index=False)

    df_matches_previous = extract_fbref_schedule_table(url_previous)
    df_matches_previous.to_csv(f"data/raw/{league['Sorare League']}_{last_season}_matches_raw_data.csv", index=False)

    # Cleaning
    df_clean_current = clean_fbref_matches(df_matches_current)
    df_clean_current.to_csv(f"data/processed/{league['Sorare League']}_{season}_matches.csv", index=False)

    df_clean_previous = clean_fbref_matches(df_matches_previous)
    df_clean_previous.to_csv(f"data/processed/{league['Sorare League']}_{last_season}_matches.csv", index=False)

    # Stats
    df_current = calculate_poisson_metrics(df_clean_current)
    df_previous = calculate_poisson_metrics(df_clean_previous)

    df_current.to_csv(f"data/team_stats/team_stats_{league['Sorare League']}_{season}.csv", index=False)
    df_previous.to_csv(f"data/team_stats/team_stats_{league['Sorare League']}_{last_season}.csv", index=False)

    # Future matches
    df_future = extract_future_matches(df_matches_current)
    if not df_future.empty:
        df_future['Time'] = df_future['Time'].apply(extract_french_time)
        df_future=combine_date_time(df_future)
        df_future.to_csv(f"data/upcoming_matches/upcoming_{league['Sorare League']}_{season}.csv", index=False)

    # Promotions/relegations
    previous_teams = set(df_previous["Team"])
    if not df_current.empty:
        current_teams = set(df_current["Team"]).union(df_future["Home"]).union(df_future["Away"])
    else:
        current_teams = set(df_future["Home"]).union(df_future["Away"])

    promoted_teams = list(current_teams - previous_teams)
    relegated_teams = list(previous_teams - current_teams)

    # Blended stats
    df_stats_blended = blend_season_stats(df_previous, df_current, df_clean_current, promoted_teams) 

    # Analyze future matches
    matches = list(df_future[["Date","Home", "Away"]].itertuples(index=False, name=None))
    results = analyze_gameweek(matches, df_stats_blended, max_goals=6)

    df_results = pd.DataFrame(results)
    df_results.to_csv(f"data/analysis/results_{league['Sorare League']}_{season}.csv", index=False)
    df_proba = df_future.merge(df_results, how="left", on=["Date","Home", "Away"])
    df_proba = df_proba.drop(columns=["lambda_home", "lambda_away"], errors="ignore")
    df_proba["Sorare Competition"] = league["Sorare competition"]
    df_proba["league"] = league["Sorare League"]
    df_proba["season"] = season
    df_proba.to_csv(f"data/exports/probas_{league['Sorare League']}_{season}.csv", index=False)

 
def run_all_leagues():
    st.session_state["stop_pipeline"] = False
    with open("config/fbref_leagues.json", "r") as f:
        leagues = json.load(f)

    active_leagues = [lg for lg in leagues if lg.get("Active", False)]
    total = len(active_leagues)

    progress_bar = st.progress(0)
    status_text = st.empty()

    with st.expander("📜 Live logs", expanded=True):
        log_area = st.empty()

    logs = []
    st.write(f"🚀 Starting pipeline for **{total}** active leagues...")

    for idx, league in enumerate(active_leagues, start=1):
        if st.session_state.get("stop_pipeline", False):
            status_text.write("⏹ Process stopped by user.")
            break

        league_name = league.get("Sorare league", league.get("FBref slug"))
        status_text.text(f"Processing league {idx}/{total} : {league_name}")

        try:
            process_league(league)
            msg = f"✅ {league_name} processed successfully."
        except Exception as e:
            msg = f"❌ {league_name} failed: {e}"

        logs.append(msg)
        log_area.text("\n".join(logs))
        progress_bar.progress(idx / total)

        # 👇 Keep Streamlit refreshing the UI (important for the button Stop)
        time.sleep(0.1)

    status_text.text("✅ All leagues processed")
    st.success("Pipeline finished for all active leagues.")