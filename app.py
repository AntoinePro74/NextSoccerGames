import streamlit as st
import json
from datetime import datetime
import pandas as pd
import os

from src.dashboard.utils_data import load_last_update,save_last_update,load_data, load_gameweeks, assign_gameweek
#from src.pipeline.run_pipeline import run_all_leagues
from src.scraping.utils_scraping import get_season
from src.dashboard.utils_streamlit import get_top5_teams,get_dynamic_threshold ,get_best_teams,get_team_matches_details

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Next soccer games",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://docs.streamlit.io/",
        "Report a bug": "https://github.com/NextSoccerGames/issues",
        "About": "⚽ Next Soccer Games for Sorare- Created with Streamlit"
    }
)

st.title("⚽ Sorare Lineup Tool - Next Soccer Games")
st.sidebar.title("Navigation")

# Inject custom CSS
st.markdown(
    """
    <style>
    .css-1d391kg { 
        padding: 1rem;
        border-radius: 12px;
    }
    .stButton>button {
        background-color: #1DB954;
        color: white;
        border-radius: 8px;
        font-weight: bold;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- CONFIG ---
DATA_DIR = "data/exports"
METADATA_DIR = "config"

# --- SIDEBAR NAV ---
pages = ["Load Data","Sorare League & Gameweek", "Favorable Calendar"]
page = st.sidebar.radio("Go to", pages)

# --- LEAGUE SELECTION ---
with open("config/fbref_leagues.json", "r") as f:
    leagues = json.load(f)

available_leagues = [league["Sorare League"] for league in leagues]
available_competitions = list(dict.fromkeys(league["Sorare competition"] for league in leagues))

# # --- Page Load Data ---
# if "running" not in st.session_state:
#     st.session_state.running = False
# if "stop_pipeline" not in st.session_state:
#     st.session_state.stop_pipeline = False
# if "last_update" not in st.session_state:
#     st.session_state.last_update = load_last_update()


# if page == "Load Data":
#     col1, col2, col3 = st.columns([1, 1, 1.5])
#     with col1:
#         load_clicked = st.button(
#             "⚽ Scraping Data",
#             help="It can take up to 15 minutes"
#         )
#     with col2:
#         if st.session_state.get("last_update"):
#             st.markdown(
#                 f"**Last update :** {st.session_state['last_update'].strftime('%d/%m/%Y %H:%M')}"
#             )
#         else:
#             st.markdown("**Last update :** —")
#     with col3:
#         stop_clicked = st.button(
#             "🛑 Stop"
#         )

#     status_ph = st.empty()

#     if load_clicked :
#         st.session_state.stop_pipeline = False
#         st.session_state.running = True
#         status_ph.text("Uploading…")
#         run_all_leagues()
#         st.session_state.last_update = datetime.now()
#         save_last_update(st.session_state.last_update) 
#         st.session_state.running = False

#     if stop_clicked :
#         st.session_state.stop_pipeline = True

# --- Page Sorare League & Gameweek ---
if page == "Sorare League & Gameweek":
    st.header("Sorare League & Gameweek")
    if st.session_state.get("last_update"):
        st.markdown(f"**Last update :** {st.session_state['last_update'].strftime('%d/%m/%Y %H:%M')}")
    else:
        st.markdown("**Last update :** —")
    with st.sidebar:
        filter_type = st.radio("Filter by :", ["League", "Sorare Competition"])

    col1, col2 = st.columns(2)
    with col1:
        if filter_type == "League":
            league__or_competition = st.selectbox("Select a league", available_leagues)
            league_info = next((l for l in leagues if l["Sorare League"] == league__or_competition), None)
            season, last_season = get_season(league_info)
            df = load_data(league__or_competition, season)
        elif filter_type == "Sorare Competition":
            league__or_competition = st.selectbox("Select a competition", available_competitions)
            leagues_info = [league for league in leagues if (league["Sorare competition"] == league__or_competition) & (league["In-season"] ==True) ]
            dfs=[]
            for league_info in leagues_info:
                season, last_season = get_season(league_info)
                df_temp = load_data(league_info["Sorare League"], season)
                dfs.append(df_temp)
            if dfs:
                df = pd.concat(dfs,ignore_index=True)
            else:
                st.error("No data found")
                st.stop()        

    # Load gameweeks
    gw_path = METADATA_DIR+"/gameweeks.json"
    gameweeks = load_gameweeks(gw_path,os.path.getmtime(gw_path))

    # Assign gameweek
    df["gameweek"] = df["Datetime"].apply(lambda d: assign_gameweek(d, gameweeks))

    # --- FILTER BY GAMEWEEK ---
    available_gws = sorted(df["gameweek"].dropna().unique())
    with col2:
        selected_gw = st.selectbox("Filter by Gameweek", available_gws)
    df = df[df["gameweek"] == selected_gw]


    # =========================
    # CALCUL TOP 5
    # =========================

    df_cs_top5 = get_top5_teams(df, "%H_CS", "%A_CS", "CS_Prob")
    df_goals_top5 = get_top5_teams(df, "%H_3GS", "%A_3GS", "Goals_Prob")

    # =========================
    # DISPLAY ON 2 COLUMNS
    # =========================
    col1, col2 = st.columns(2)

    with col1:
        threshold_defense = get_dynamic_threshold(df, "%H_CS", "%A_CS", percentile=70, min_threshold=0.25)
        st.markdown("### 🛡️ Top 5 - Chance of clean sheet")
        st.dataframe(
            df_cs_top5[["Team", "Stadium", "CS_Prob","Opponent"]]
            .rename(columns={"CS_Prob": "%CS"})
            .style.format({"%CS": "{:.2%}"})
        )
        st.write(f"threshold : {threshold_defense:.2%}")

    with col2:
        threshold_attack = get_dynamic_threshold(df, "%H_3GS", "%A_3GS", percentile=70, min_threshold=0.25)
        st.markdown("### 🎯 Top 5 - Chance of 3+ goals")
        st.dataframe(
            df_goals_top5[["Team", "Stadium", "Goals_Prob","Opponent"]]
            .rename(columns={"Goals_Prob": "% 3+ goals"})
            .style.format({"% 3+ goals": "{:.2%}"})
        )
        st.write(f"threshold : {threshold_attack:.2%}")

    # --- DISPLAY ---
    st.subheader(f"Matches - {league__or_competition} - {selected_gw}")

    # Sort by date
    df = df.sort_values("Date")

    # Format date
    df["Date"] = df["Date"].dt.strftime("%d/%m/%Y")

    # Format probabilities
    prob_columns = ['%Home','%Draw','%Away','%H_CS','%A_CS','%H_3GS','%A_3GS','%S_P']
    if filter_type == "League":
        columns_to_display = ['Date','Time','Home','Away','%Home','%Draw','%Away','%H_CS','%A_CS','%H_3GS','%A_3GS','S_P','%S_P']
    elif filter_type == "Sorare Competition":
        columns_to_display = ['Date','Time','league','Home','Away','%Home','%Draw','%Away','%H_CS','%A_CS','%H_3GS','%A_3GS','S_P','%S_P']

    st.dataframe(
        df[columns_to_display].sort_values(by="%Home",ascending=False).style.format({col: "{:.2%}" for col in prob_columns if col in df.columns})
    )


# --- Page Favorable Calendar---
if page == "Favorable Calendar":
    st.header("Favorable Calendar")
    if st.session_state.get("last_update"):
        st.markdown(f"**Last update :** {st.session_state['last_update'].strftime('%d/%m/%Y %H:%M')}")
    else:
        st.markdown("**Last update :** —")
    with st.sidebar:
        filter_type = st.radio("Filter by :", ["League", "Sorare Competition"])

    col1, col2 = st.columns(2)
    with col1:
        if filter_type == "League":
            league__or_competition = st.selectbox("Select a league", available_leagues)
            league_info = next((l for l in leagues if l["Sorare League"] == league__or_competition), None)
            season, last_season = get_season(league_info)
            df = load_data(league__or_competition, season)
        elif filter_type == "Sorare Competition":
            league__or_competition = st.selectbox("Select a competition", available_competitions)
            leagues_info = [league for league in leagues if (league["Sorare competition"] == league__or_competition) & (league["In-season"] ==True) ]
            dfs=[]
            for league_info in leagues_info:
                season, last_season = get_season(league_info)
                df_temp = load_data(league_info["Sorare League"], season)
                dfs.append(df_temp)
            if dfs:
                df = pd.concat(dfs,ignore_index=True)
            else:
                st.error("No data found")
                st.stop()   

    # --- FILTER BY DATE ---
    with col2:
        date_range = st.date_input(
            "Select date range",
            value=(pd.Timestamp.today(), df["Date"].max()),
            format="DD/MM/YYYY"
        )

    start_date, end_date = date_range
    df_filtered = df[(df["Date"].dt.date >= start_date) & (df["Date"].dt.date <= end_date)]

    # --- GET BEST TEAMS ---
    df_best_defense = get_best_teams(df_filtered, "%H_CS", "%A_CS", "CS_Prob", method="mixed")
    df_best_attack = get_best_teams(df_filtered, "%H_3GS", "%A_3GS", "Goals_Prob", method="mixed")

    # === COLUMNS TO DISPLAY ===
    distribution_cols = ["<25%", "25-35%", "35-45%", "45-55%", "55-70%", ">70%"]

    # Display results side by side
    col1, col2 = st.columns(2)

    with col1:
        threshold_defense = get_dynamic_threshold(df, "%H_CS", "%A_CS", percentile=70, min_threshold=0.25)
        st.markdown(f"### 🛡️ Best defense - dynamic threshold: {threshold_defense:.2%}")

        # Format defense dataframe
        st.dataframe(
            df_best_defense.rename(columns={"CS_Prob": "Score"})
            .style.format({"Score": "{:.2f}"})  # Format score
        )

        # Details per team
        for _, row in df_best_defense.iterrows():
            with st.expander(f"📌 Details - {row['Team']}"):
                details = get_team_matches_details(df_filtered, row["Team"], "%H_CS", "%A_CS", "CS_Prob")
                st.dataframe(
                    details[["Date", "Opponent", "Stadium", "CS_Prob"]]
                    .style.format({"CS_Prob": "{:.2%}"})
                )

    with col2:
        threshold_attack = get_dynamic_threshold(df, "%H_3GS", "%A_3GS", percentile=70, min_threshold=0.25)
        st.markdown(f"### 🎯 Best attack - dynamic threshold: {threshold_attack:.2%}")

        # Format attack dataframe
        st.dataframe(
            df_best_attack.rename(columns={"Goals_Prob": "Score"})
            .style.format({"Score": "{:.2f}"})
        )

        # Details per team
        for _, row in df_best_attack.iterrows():
            with st.expander(f"📌 Details - {row['Team']}"):
                details = get_team_matches_details(df_filtered, row["Team"], "%H_3GS", "%A_3GS", "Goals_Prob")
                st.dataframe(
                    details[["Date", "Opponent", "Stadium", "Goals_Prob"]]
                    .style.format({"Goals_Prob": "{:.2%}"})
                )

