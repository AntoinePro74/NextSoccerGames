import pandas as pd
import numpy as np
from scipy.stats import poisson

def compute_lambda(home_team: str, away_team: str, df_stats: pd.DataFrame) -> tuple[float, float]:
    """
    Compute the λ_home and λ_away parameters with realistic promotion management.

    Args:
        home_team (str): Home team
        away_team (str): Away team
        df_stats (pd.DataFrame): Team statistics from the previous season
            (required columns: Team, GF_home, GA_home, GF_away, GA_away, MP_home, MP_away)

    Returns:
        tuple[float, float]: λ_home, λ_away
    """
    # Average league
    league_avg_home_goals = df_stats["GF_home"].sum() / max(df_stats["MP_home"].sum(), 1)
    league_avg_away_goals = df_stats["GF_away"].sum() / max(df_stats["MP_away"].sum(), 1)
    home_advantage_factor = league_avg_home_goals / max(league_avg_away_goals, 1e-6)

    # Stats teams
    home_stats = df_stats[df_stats["Team"] == home_team].iloc[0]
    away_stats = df_stats[df_stats["Team"] == away_team].iloc[0]

    # Lambdas
    lambda_home = (home_stats["GF_per_home"] * away_stats["GA_per_away"]) / max(league_avg_home_goals, 1e-6) * home_advantage_factor
    lambda_away = (away_stats["GF_per_away"] * home_stats["GA_per_home"]) / max(league_avg_away_goals, 1e-6)

    return lambda_home, lambda_away

def get_match_probabilities(lambda_home, lambda_away, max_goals=6):
    """
    Compute the probabilities of all possible scores in a match
    as well as the probabilities of a win, a clean sheet, three goals or more, and the most likely score.

    Args:
        lambda_home (float): expected home goals
        lambda_away (float): expected away goals
        max_goals (int): maximum score to consider (e.g., 6 = 0 to 6)

    Returns:
        dict: all useful probabilities (win, CS, 3GS, etc.)
    """
    score_matrix = np.zeros((max_goals + 1, max_goals + 1))

    for home_goals in range(max_goals + 1):
        for away_goals in range(max_goals + 1):
            p_home = poisson.pmf(home_goals, lambda_home)
            p_away = poisson.pmf(away_goals, lambda_away)
            score_matrix[home_goals, away_goals] = p_home * p_away

    # Probabilities global
    home_win = np.tril(score_matrix, -1).sum()
    draw = np.trace(score_matrix)
    away_win = np.triu(score_matrix, 1).sum()

    # Clean sheet
    home_CS = score_matrix[:, 0].sum()
    away_CS = score_matrix[0, :].sum()

    # 3 goals or more
    home_3GS = score_matrix[3:, :].sum()
    away_3GS = score_matrix[:, 3:].sum()

    # Most probable score
    max_prob = score_matrix.max()
    most_probable_score = np.unravel_index(np.argmax(score_matrix), score_matrix.shape)

    return {
        "score_matrix": score_matrix,
        "prob_home_win": home_win,
        "prob_draw": draw,
        "prob_away_win": away_win,
        "prob_home_CS": home_CS,
        "prob_away_CS": away_CS,
        "prob_home_3GS": home_3GS,
        "prob_away_3GS": away_3GS,
        "most_probable_score": most_probable_score,
        "prob_most_likely_score": max_prob
    }

def analyze_gameweek(matches: list[tuple[str, str,str]],
                     df_stats: pd.DataFrame,
                     max_goals: int = 6) -> list[dict]:
    """
    Analyzes all matches in a gameweek and returns useful probabilities.
    If a promoted team has no stats, the opponent's stats are used (reversing home/away if necessary).
    
    Args:
        matches (list): list of tuples (home_team, away_team)
        df_stats (pd.DataFrame): table of team stats
        league_avg_goals (float): average goals per match in the league
        max_goals (int): maximum score to consider

    Returns:
        list[dict]: a list of dictionaries of results per match
    """
    results = []

    for date,home_team, away_team in matches:
        try:
            λ_home, λ_away = compute_lambda(home_team, away_team, df_stats)
            probas = get_match_probabilities(λ_home, λ_away, max_goals)

            home_goals = int(probas['most_probable_score'][0])
            away_goals = int(probas['most_probable_score'][1])

            results.append({
                "Date": date,
                "Home": home_team,
                "Away": away_team,
                "lambda_home": λ_home,
                "lambda_away": λ_away,
                "%Home": probas["prob_home_win"],
                "%Draw": probas["prob_draw"],
                "%Away": probas["prob_away_win"],
                "%H_CS": probas["prob_home_CS"],
                "%A_CS": probas["prob_away_CS"],
                "%H_3GS": probas["prob_home_3GS"],
                "%A_3GS": probas["prob_away_3GS"],
                "S_P": f"{home_goals}-{away_goals}",
                "%S_P": probas["prob_most_likely_score"]
            })

        except Exception as e:
            print(f"[ERROR] Match {home_team} vs {away_team} : {e}")

    return results