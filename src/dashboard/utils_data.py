import os
import json
from datetime import datetime
import streamlit as st
import pandas as pd

def load_last_update():
    file_path = "config/last_update.json"
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            data = json.load(f)
            return datetime.strptime(data["last_update"], "%Y-%m-%d %H:%M:%S")
    return None

def save_last_update(dt):
    file_path = "config/last_update.json"
    with open(file_path, "w") as f:
        json.dump({"last_update": dt.strftime("%Y-%m-%d %H:%M:%S")}, f)

@st.cache_data
def load_data(league: str, season: str):
    file_path = f"data/exports/probas_{league}_{season}.csv"
    df = pd.read_csv(file_path)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Datetime"] = pd.to_datetime(df["Datetime"], errors="coerce")
    return df

@st.cache_data
def load_gameweeks(file_path,file_mtime):
    with open(file_path, "r", encoding="utf-8") as f:
        gw_data = json.load(f)
    for gw in gw_data:
        gw["startDate"] = pd.to_datetime(gw["startDate"])
        gw["endDate"] = pd.to_datetime(gw["endDate"])
    return gw_data


def assign_gameweek(date, gameweeks):
    date = pd.to_datetime(date)
    if date.tzinfo is not None:
        date = date.tz_localize(None)

    for gw in gameweeks:
        start = pd.to_datetime(gw["startDate"])
        end = pd.to_datetime(gw["endDate"])
        if start.tzinfo is not None:
            start = start.tz_localize(None)
        if end.tzinfo is not None:
            end = end.tz_localize(None)

        if start <= date <= end:
            return gw["gw"]
    return None