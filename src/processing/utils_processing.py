import pandas as pd
import re

def clean_fbref_matches(df: pd.DataFrame) -> pd.DataFrame:
    # 1️⃣ Standardize column names
    df = df.rename(columns=lambda x: x.strip())
    
    # Remove repeated header rows
    df = df[df["Score"] != "Score"].copy()
    df.reset_index(drop=True, inplace=True)

    # 2️⃣ Ensure unique column names (important for xG duplicates)
    df.columns = [
        f"{col}_{j}" if df.columns.duplicated()[j] else col
        for j, col in enumerate(df.columns)
    ]

    # 3️⃣ Identify useful columns
    cols = ['Date','Time', 'Home', 'Away', 'Score']
    
    # Detect xG columns (now uniquely named)
    xg_candidates = [col for col in df.columns if 'xG' in col]
    cols += xg_candidates
    
    # Keep only relevant columns
    df = df[cols]

    # 4️⃣ Filter out future matches (empty Score)
    df = df[df['Score'].str.contains(r'\d+[–-]\d+', na=False)].copy()

    # 5️⃣ Split score into home and away goals (as integers)
    df[['home_goal', 'away_goal']] = (
        df['Score']
        .str.extract(r'(\d+)[–-](\d+)')
        .astype(int)
    )
    df.drop(columns='Score', inplace=True)

    # 6️⃣ Rename xG columns if present
    if len(xg_candidates) == 2:
        df = df.rename(columns={xg_candidates[0]: 'xG_home', xg_candidates[1]: 'xG_away'})

    # 7️⃣ Reorder columns
    ordered_cols = ['Date','Time', 'Home', 'Away', 'home_goal', 'away_goal']
    if 'xG_home' in df.columns and 'xG_away' in df.columns:
        ordered_cols += ['xG_home', 'xG_away']

    return df[ordered_cols]

def extract_future_matches(df: pd.DataFrame) -> pd.DataFrame:
    # 1️⃣ Standardize column names
    df = df.rename(columns=lambda x: x.strip())

    # Remove repeated header rows
    df = df[df["Score"] != "Score"].copy()
    df.reset_index(drop=True, inplace=True)

    # 2️⃣ Keep only relevant columns
    df_future = df[~df["Score"].str.contains(r'\d', na=False)].copy()
    df_future = df_future[['Date','Time', 'Home', 'Away']]

    # 3️⃣ Convert Date column to datetime
    df_future['Date'] = pd.to_datetime(df_future['Date'], errors='coerce')

    return df_future

def calculate_poisson_metrics(df: pd.DataFrame) -> pd.DataFrame:
    # 1️⃣ Home stats
    home_stats = df.groupby("Home").agg(
        GF_home=("home_goal", "sum"),
        GA_home=("away_goal", "sum"),
        MP_home=("home_goal", "count")
    )

    # 2️⃣ Away stats
    away_stats = df.groupby("Away").agg(
        GF_away=("away_goal", "sum"),
        GA_away=("home_goal", "sum"),
        MP_away=("away_goal", "count")
    )

    # 3️⃣ Merge home & away stats
    team_stats = pd.concat([home_stats, away_stats], axis=1).fillna(0)

    # 4️⃣ Calculate per match averages
    team_stats["GF_per_home"] = team_stats["GF_home"] / team_stats["MP_home"]
    team_stats["GA_per_home"] = team_stats["GA_home"] / team_stats["MP_home"]
    team_stats["GF_per_away"] = team_stats["GF_away"] / team_stats["MP_away"]
    team_stats["GA_per_away"] = team_stats["GA_away"] / team_stats["MP_away"]

    # 5️⃣ Replace NaN (teams with 0 home or away matches)
    team_stats = team_stats.fillna(0)

    return team_stats.reset_index().rename(columns={"index": "Team"})

def extract_french_time(value):
    if pd.isna(value) or value.strip() == "":
        return "à venir"
    
    # if format is "hh:mm (hh:mm)"
    match = re.match(r'^\d{2}:\d{2}\s*\((\d{2}:\d{2})\)$', value)
    if match:
        return match.group(1)  # Get time before parentheses
    
    # if it's just "hh:mm"
    match = re.match(r'^\d{2}:\d{2}$', value)
    if match:
        return value
    
    return "ongoing"  # Default

def combine_date_time(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize Date and Time columns to a single datetime column"""
    df = df.copy()
    df["Time"] = df["Time"].fillna("00:00")
    df.loc[df["Time"].str.strip().str.lower() == "ongoing", "Time"] = "00:00"
    df["Datetime"] = pd.to_datetime(
        df["Date"].astype(str) + " " + df["Time"].astype(str),
        errors="coerce"
    )
    return df