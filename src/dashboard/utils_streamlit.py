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

def get_best_teams(df, home_col, away_col, metric_name, top_n=5, method="mixed"):
    team_scores = compute_team_scores(df, home_col, away_col, method=method)
    return (
        team_scores
        .sort_values("Score", ascending=False)
        .head(top_n)
        .rename(columns={"Score": metric_name})
        .reset_index(drop=True)
    )


def compute_team_scores(df, prob_home_col, prob_away_col, method="average", min_matches=1, threshold=None):
    """
    Compute team scores using different aggregation methods and probability distribution.
    """

    # Build a unified DataFrame
    df_home = df[["Home", prob_home_col,"league"]].rename(columns={"Home": "Team", prob_home_col: "Prob"})
    df_away = df[["Away", prob_away_col,"league"]].rename(columns={"Away": "Team", prob_away_col: "Prob"})
    df_all = pd.concat([df_home, df_away])

    # Group by team
    grouped = df_all.groupby("Team")["Prob"]

    results = []

    # Precompute threshold for "mixed" method
    dynamic_threshold = None
    if method == "mixed":
        dynamic_threshold = get_dynamic_threshold(df, prob_home_col, prob_away_col, percentile=70, min_threshold=0.25)

    for team, probs in grouped:
        n_matches = len(probs)
        if n_matches < min_matches:
            continue

        # === SCORING ===
        if method == "average":
            score = probs.mean()

        elif method == "weighted":
            score = probs.mean() * (n_matches / max(n_matches, min_matches))

        elif method == "cumulative":
            score = probs.sum()

        elif method == "mixed":
            score = probs.mean() * (1 + np.log1p(n_matches))
            favorable_count = (probs > dynamic_threshold).sum()
            score += favorable_count * 0.5

        elif method == "favorable":
            if threshold is None:
                raise ValueError("Threshold must be provided for 'favorable' method")
            favorable_matches = (probs >= threshold).sum()
            score = favorable_matches + probs[probs >= threshold].mean() if favorable_matches > 0 else 0

        else:
            raise ValueError(f"Unknown method: {method}")

        # === PROBABILITY DISTRIBUTION ===
        bins = [0, 0.25, 0.35, 0.45, 0.55, 0.70, 1.01]  # last bin includes 100%
        labels = ["<25%", "25-35%", "35-45%", "45-55%", "55-70%", ">70%"]
        distribution = pd.cut(probs, bins=bins, labels=labels, include_lowest=True)
        dist_counts = distribution.value_counts().reindex(labels, fill_value=0).to_dict()

        results.append({
            "Team": team,
            "Score": score,
            "Matches": n_matches,
            **dist_counts
        })

    return pd.DataFrame(results).sort_values("Score", ascending=False).reset_index(drop=True)

def get_team_matches_details(df, team, home_col, away_col, metric_name):
    """
    Get the match details for a specific team.
    Returns matches with date, opponent, stadium, and metric value.
    """
    # Matches when the team is at home
    home_matches = df[df["Home"] == team][["Date", "Away", home_col]].copy()
    home_matches["Stadium"] = "Home"
    home_matches.rename(columns={"Away": "Opponent", home_col: metric_name}, inplace=True)

    # Matches when the team is away
    away_matches = df[df["Away"] == team][["Date", "Home", away_col]].copy()
    away_matches["Stadium"] = "Away"
    away_matches.rename(columns={"Home": "Opponent", away_col: metric_name}, inplace=True)

    # Combine
    matches = pd.concat([home_matches, away_matches])
    matches["Date"] = pd.to_datetime(matches["Date"], format="%d/%m/%Y")
    matches = matches.sort_values("Date").reset_index(drop=True)
    matches["Date"] = matches["Date"].dt.strftime("%d/%m/%Y")

    return matches