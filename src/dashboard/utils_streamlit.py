import pandas as pd
import numpy as np

def get_top5_teams(df, col_home, col_away, metric_name):
    """
    Creates a top 5 based on a metric for teams at home and away
    
    Args:
        df (pd.DataFrame): The DataFrame of matches.
        col_home (str): Name of the column for the metric of teams at home.
        col_away (str): Name of the column for the metric of teams at away.
        metric_name (str): Name of the column for the metric (ex: 'CS_Prob').

    Returns:
        pd.DataFrame: Top 5 of teams with the best value for the given metric.
    """
    # Home data
    df_home = df[["Home", "Away", col_home]].rename(columns={
        "Home": "Team",
        "Away": "Opponent",
        col_home: metric_name
    })
    df_home["Stadium"] = "Home"

    # Away data
    df_away = df[["Away", "Home", col_away]].rename(columns={
        "Away": "Team",
        "Home": "Opponent",
        col_away: metric_name
    })
    df_away["Stadium"] = "Away"

    # Merge
    df_all = pd.concat([df_home, df_away])

    # Top 5 based on the best probability
    top5 = (
        df_all.loc[df_all.groupby("Team")[metric_name].idxmax()]
        .drop_duplicates(subset=["Team"])
        .sort_values(metric_name, ascending=False)
        .head(5)
        .reset_index(drop=True)
    )

    return top5


def get_dynamic_threshold(df: pd.DataFrame, home_col: str, away_col: str, percentile: float = 70, min_threshold: float = 0.25):
    """
    Calculate a dynamic threshold for favorable matches based on percentiles.

    Parameters:
    ----------
    df : pd.DataFrame
        DataFrame containing match data.
    home_col : str
        Column name for home team probabilities.
    away_col : str
        Column name for away team probabilities.
    percentile : float
        Percentile to use for threshold calculation (default: 70).
    min_threshold : float
        Minimum threshold to avoid values that are too low in very defensive leagues.

    Returns:
    -------
    float
        The calculated dynamic threshold.
    """
    probs = pd.concat([df[home_col], df[away_col]]).dropna()
    threshold = np.percentile(probs, percentile)
    return max(threshold, min_threshold)
