import streamlit as st
import json
from datetime import datetime

from src.dashboard.utils_data import load_last_update,save_last_update#,load_data, load_gameweeks, assign_gameweek
from src.pipeline.run_pipeline import run_all_leagues

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
DATA_DIR = "/data/exports"
METADATA_DIR = "/config"

# --- SIDEBAR NAV ---
pages = ["Load Data","Sorare League & Gameweek", "Favorable Calendar"]
page = st.sidebar.radio("Go to", pages)

# --- LEAGUE SELECTION ---
with open("config/fbref_leagues.json", "r") as f:
    leagues = json.load(f)

available_leagues = [league["Sorare League"] for league in leagues]
available_competitions = list(dict.fromkeys(league["Sorare competition"] for league in leagues))

# --- Page Load Data ---
if "running" not in st.session_state:
    st.session_state.running = False
if "stop_pipeline" not in st.session_state:
    st.session_state.stop_pipeline = False
if "last_update" not in st.session_state:
    st.session_state.last_update = load_last_update()


if page == "Scraping Data":
    col1, col2, col3 = st.columns([1, 1, 1.5])
    with col1:
        load_clicked = st.button(
            "⚽ Scraping Data",
            help="It can take up to 15 minutes"
        )
    with col2:
        if st.session_state.get("last_update"):
            st.markdown(
                f"**Last update :** {st.session_state['last_update'].strftime('%d/%m/%Y %H:%M')}"
            )
        else:
            st.markdown("**Last update :** —")
    with col3:
        stop_clicked = st.button(
            "🛑 Stop"
        )

    status_ph = st.empty()

    if load_clicked :
        st.session_state.stop_pipeline = False
        st.session_state.running = True
        status_ph.text("Uploading…")
        run_all_leagues()
        st.session_state.last_update = datetime.now()
        save_last_update(st.session_state.last_update) 
        st.session_state.running = False

    if stop_clicked :
        st.session_state.stop_pipeline = True
