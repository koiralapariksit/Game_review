from typing import Dict, Any, List, Optional
from decimal import Decimal
from django.db.models import Q
from matches.models import Match, MatchStatistic, MatchEvent


def compute_match_metrics(match_id: int) -> Dict[str, Any]:
    """
    Deterministically pre-computes tactical and performance metrics for a given match.
    Enforces the Zero-Prompt-Arithmetic rule: All math is calculated in pure Python.
    Safely handles missing statistics, zero possession, and zero shots without ZeroDivisionError.
    """
    match = Match.objects.select_related('home_team', 'away_team', 'competition').get(pk=match_id)
    statistic = getattr(match, 'statistic', None)
    events = list(match.events.all().order_by('minute'))

    is_barca_home = (
        match.home_team.name == "FC Barcelona"
        or match.home_team.short_name in ("Barcelona", "Barça")
        or (match.home_team.provider_id in (81, 529))
    )

    home_score = match.home_score if match.home_score is not None else 0
    away_score = match.away_score if match.away_score is not None else 0

    barca_goals = home_score if is_barca_home else away_score
    opp_goals = away_score if is_barca_home else home_score

    # Determine Result
    if match.status != Match.STATUS_FINISHED and match.home_score is None:
        result_type = "PENDING"
    elif barca_goals > opp_goals:
        result_type = "WIN"
    elif barca_goals < opp_goals:
        result_type = "LOSS"
    else:
        result_type = "DRAW"

    # Pre-compute Possession
    possession_difference: Optional[int] = None
    barca_possession: Optional[int] = None
    opp_possession: Optional[int] = None

    if statistic and statistic.possession_home is not None and statistic.possession_away is not None:
        barca_possession = statistic.possession_home if is_barca_home else statistic.possession_away
        opp_possession = statistic.possession_away if is_barca_home else statistic.possession_home
        possession_difference = barca_possession - opp_possession

    # Pre-compute Shots and Accuracy
    barca_shots: Optional[int] = None
    barca_shots_on_target: Optional[int] = None
    shot_conversion_rate: Optional[float] = None
    shot_accuracy: Optional[float] = None

    if statistic:
        barca_shots = statistic.shots_home if is_barca_home else statistic.shots_away
        barca_shots_on_target = statistic.shots_on_target_home if is_barca_home else statistic.shots_on_target_away

        if barca_shots is not None and barca_shots > 0:
            shot_conversion_rate = round(float(barca_goals) / float(barca_shots), 3)
            if barca_shots_on_target is not None:
                shot_accuracy = round(float(barca_shots_on_target) / float(barca_shots), 3)
        elif barca_shots == 0:
            shot_conversion_rate = 0.0
            shot_accuracy = 0.0

    # Pre-compute xG overperformance
    xg_overperformance: Optional[float] = None
    barca_xg: Optional[float] = None
    if statistic:
        raw_xg = statistic.xg_home if is_barca_home else statistic.xg_away
        if raw_xg is not None:
            barca_xg = float(raw_xg)
            xg_overperformance = round(float(barca_goals) - barca_xg, 2)

    # Disciplinary Points: Yellows * 1 + Reds * 3
    yellow_count = 0
    red_count = 0
    goal_chronology: List[Dict[str, Any]] = []

    for event in events:
        if event.event_type == MatchEvent.EVENT_CARD:
            detail_lower = event.detail.lower()
            if 'red' in detail_lower or 'second yellow' in detail_lower:
                red_count += 1
            else:
                yellow_count += 1
        elif event.event_type == MatchEvent.EVENT_GOAL:
            goal_chronology.append({
                "minute": event.minute,
                "scorer": event.player_name,
                "detail": event.detail
            })

    disciplinary_points = (yellow_count * 1) + (red_count * 3)

    return {
        "match_id": match.id,
        "is_barca_home": is_barca_home,
        "barca_score": barca_goals,
        "opp_score": opp_goals,
        "result_type": result_type,
        "barca_possession": barca_possession,
        "opp_possession": opp_possession,
        "possession_difference": possession_difference,
        "barca_shots": barca_shots,
        "barca_shots_on_target": barca_shots_on_target,
        "shot_conversion_rate": shot_conversion_rate,
        "shot_accuracy": shot_accuracy,
        "barca_xg": barca_xg,
        "xg_overperformance": xg_overperformance,
        "yellow_cards": yellow_count,
        "red_cards": red_count,
        "disciplinary_points": disciplinary_points,
        "goal_chronology": goal_chronology,
    }


def compute_team_form(competition_code: Optional[str] = None, limit: int = 5) -> Dict[str, Any]:
    """
    Calculates Barcelona's recent form sequence (e.g., 'W-W-D-W-L'),
    clean sheet count, average goals scored, and average goals conceded
    across the last N completed matches.
    """
    query = Match.objects.filter(
        status=Match.STATUS_FINISHED,
        home_score__isnull=False,
        away_score__isnull=False
    ).select_related('home_team', 'away_team', 'competition')

    if competition_code:
        query = query.filter(competition__code=competition_code)

    # Filter to FC Barcelona matches
    barca_query = query.filter(
        Q(home_team__name__icontains="Barcelona") |
        Q(home_team__short_name__icontains="Barça") |
        Q(home_team__provider_id__in=[81, 529]) |
        Q(away_team__name__icontains="Barcelona") |
        Q(away_team__short_name__icontains="Barça") |
        Q(away_team__provider_id__in=[81, 529])
    ).order_by('-match_date')[:limit]

    matches = list(barca_query)

    if not matches:
        return {
            "form_sequence": "",
            "matches_analyzed": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "clean_sheets": 0,
            "goals_scored": 0,
            "goals_conceded": 0,
            "avg_goals_scored": 0.0,
            "avg_goals_conceded": 0.0,
        }

    form_chars = []
    clean_sheets = 0
    total_goals_scored = 0
    total_goals_conceded = 0
    wins = 0
    draws = 0
    losses = 0

    for m in matches:
        is_home = (
            "barcelona" in m.home_team.name.lower() or
            "barça" in m.home_team.short_name.lower() or
            m.home_team.provider_id in (81, 529)
        )
        barca_g = m.home_score if is_home else m.away_score
        opp_g = m.away_score if is_home else m.home_score

        total_goals_scored += barca_g
        total_goals_conceded += opp_g

        if opp_g == 0:
            clean_sheets += 1

        if barca_g > opp_g:
            form_chars.append("W")
            wins += 1
        elif barca_g == opp_g:
            form_chars.append("D")
            draws += 1
        else:
            form_chars.append("L")
            losses += 1

    count = len(matches)
    return {
        "form_sequence": "-".join(form_chars),
        "matches_analyzed": count,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "clean_sheets": clean_sheets,
        "goals_scored": total_goals_scored,
        "goals_conceded": total_goals_conceded,
        "avg_goals_scored": round(total_goals_scored / count, 2) if count > 0 else 0.0,
        "avg_goals_conceded": round(total_goals_conceded / count, 2) if count > 0 else 0.0,
    }
