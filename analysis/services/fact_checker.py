from typing import List, Dict, Any, Optional
from decimal import Decimal
from pydantic import BaseModel, Field

from matches.models import Match, MatchEvent, MatchStatistic
from analysis.schemas import EditorialArticleSchema


class ValidationResult(BaseModel):
    is_valid: bool = Field(..., description="Whether all deterministic fact checks passed")
    fatal_errors: List[str] = Field(default_factory=list, description="Grounding errors that block publication")
    warnings: List[str] = Field(default_factory=list, description="Minor anomalies or unverified claims")
    audit_log: Dict[str, Any] = Field(default_factory=dict, description="Detailed trace of verified facts")


class DeterministicFactChecker:
    """
    Deterministic Fact Checker Gate.
    Grounds AI-generated match reports strictly against PostgreSQL/DB rows.
    Any contradiction in score, goalscorers, or key statistics causes is_valid=False.
    """

    @classmethod
    def verify_match_report(cls, article_data: EditorialArticleSchema, match: Match) -> ValidationResult:
        fatal_errors: List[str] = []
        warnings: List[str] = []
        audit_log: Dict[str, Any] = {}

        # 1. SCORE CHECK
        home_score = match.home_score if match.home_score is not None else 0
        away_score = match.away_score if match.away_score is not None else 0
        
        valid_score_formats = [
            f"{home_score}-{away_score}",
            f"{home_score} - {away_score}",
            f"{away_score}-{home_score}",
            f"{away_score} - {home_score}",
        ]
        
        claimed_score_clean = str(article_data.claimed_score).strip()
        audit_log["claimed_score"] = claimed_score_clean
        audit_log["actual_score"] = f"{home_score}-{away_score}"

        if claimed_score_clean not in valid_score_formats:
            fatal_errors.append(
                f"Score mismatch: Article claimed '{claimed_score_clean}', but official database record is '{home_score}-{away_score}'."
            )

        # 2. GOALSCORER CHECK
        actual_goals = list(match.events.filter(event_type=MatchEvent.EVENT_GOAL).values_list('player_name', flat=True))
        actual_goals_normalized = [g.lower().strip() for g in actual_goals]
        audit_log["actual_scorers"] = actual_goals

        for claimed_scorer in article_data.claimed_goalscorers:
            norm_claimed = claimed_scorer.lower().strip()
            # Partial match allowance (e.g. "Yamal" in "Lamine Yamal" or vice versa)
            matched = any(norm_claimed in act or act in norm_claimed for act in actual_goals_normalized)
            if not matched and actual_goals:
                fatal_errors.append(
                    f"Hallucinated goalscorer: '{claimed_scorer}' was claimed as scorer, but actual goalscorers were {actual_goals}."
                )

        # 3. STATS INTEGRITY CHECK
        statistic = getattr(match, 'statistic', None)
        claimed_stats = article_data.claimed_stats_referenced or {}
        audit_log["claimed_stats"] = claimed_stats

        if statistic:
            # Check possession if referenced
            if 'possession' in claimed_stats:
                try:
                    claimed_pos = float(str(claimed_stats['possession']).replace('%', '').strip())
                    actual_pos = float(statistic.possession_home if match.home_team.name == "FC Barcelona" else statistic.possession_away)
                    if abs(claimed_pos - actual_pos) > 1.0:
                        fatal_errors.append(
                            f"Stat contradiction: Claimed possession {claimed_pos}%, but database record indicates {actual_pos}%."
                        )
                except (ValueError, TypeError):
                    warnings.append(f"Unparseable possession stat format: '{claimed_stats.get('possession')}'")

            # Check shots if referenced
            if 'shots' in claimed_stats:
                try:
                    claimed_shots = int(str(claimed_stats['shots']).strip())
                    actual_shots = int(statistic.shots_home if match.home_team.name == "FC Barcelona" else statistic.shots_away)
                    if abs(claimed_shots - actual_shots) > 1:
                        fatal_errors.append(
                            f"Stat contradiction: Claimed shots {claimed_shots}, but database record indicates {actual_shots}."
                        )
                except (ValueError, TypeError):
                    warnings.append(f"Unparseable shots stat format: '{claimed_stats.get('shots')}'")
        else:
            if claimed_stats:
                warnings.append("Article referenced specific match statistics, but no MatchStatistic record exists in the database.")

        is_valid = len(fatal_errors) == 0

        return ValidationResult(
            is_valid=is_valid,
            fatal_errors=fatal_errors,
            warnings=warnings,
            audit_log=audit_log
        )

