from typing import List, Dict
from pydantic import BaseModel, Field


class MatchAnalysisSchema(BaseModel):
    overview: str = Field(..., description="High-level match narrative and context")
    first_half_tactics: str = Field(..., description="Detailed tactical dynamic during the first 45 minutes")
    second_half_tactics: str = Field(..., description="Tactical adjustments, substitutions, and momentum shifts in the second half")
    build_up_and_pressing: str = Field(..., description="Analysis of passing structures, buildup phases, counter-pressing, and defensive blocks")
    statistical_context: str = Field(..., description="Interpretation of possession, xG, shot accuracy, and defensive numbers")
    key_moments: List[str] = Field(default_factory=list, description="Crucial turning points, goals, saves, or controversial decisions")
    strengths: List[str] = Field(default_factory=list, description="Key operational strengths executed by Barcelona")
    weaknesses: List[str] = Field(default_factory=list, description="Tactical vulnerabilities exposed during the match")
    final_verdict: str = Field(..., description="Concluding assessment on team progress, coach management, and upcoming implications")
    editorial_rating: float = Field(..., ge=1.0, le=10.0, description="Overall performance score out of 10")
    rating_justification: str = Field(..., description="Concise rationale behind the editorial rating")


class PlayerPerformanceSchema(BaseModel):
    player_id: int = Field(..., description="Database player ID")
    player_name: str = Field(..., description="Full name of the player")
    rating: float = Field(..., ge=1.0, le=10.0, description="Player rating between 1.0 and 10.0")
    role_summary: str = Field(..., description="Brief synopsis of player tactical role and positioning")
    strengths_shown: List[str] = Field(default_factory=list, description="Notable strengths and positive contributions")
    areas_for_improvement: List[str] = Field(default_factory=list, description="Weaknesses or missed actions during the match")


class EditorialArticleSchema(BaseModel):
    headline: str = Field(..., description="Catchy, journalistic headline for the match report")
    subtitle: str = Field(..., description="Engaging subtitle expanding on the main theme")
    seo_meta_description: str = Field(..., description="Optimized meta description under 160 characters")
    markdown_body: str = Field(..., description="Full 11-section FC Barcelona editorial format in rich Markdown")
    claimed_score: str = Field(..., description="Final score in home-away format (e.g. '3-1')")
    claimed_goalscorers: List[str] = Field(default_factory=list, description="Names of goalscorers referenced in the text")
    claimed_stats_referenced: Dict[str, str] = Field(default_factory=dict, description="Key stats mentioned (e.g. {'possession': '62%', 'shots': '16'})")

