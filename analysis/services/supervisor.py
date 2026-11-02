import re
import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from pydantic import BaseModel, Field

from matches.models import Match
from analysis.models import Article
from analysis.schemas import EditorialArticleSchema

logger = logging.getLogger(__name__)


class SupervisorAuditResult(BaseModel):
    passed: bool = Field(..., description="Whether article passed all editorial quality supervisor gates")
    completeness_passed: bool = Field(default=True, description="Whether all 11 mandatory sections and density checks passed")
    anti_repetition_passed: bool = Field(default=True, description="Whether anti-repetition / similarity checks passed")
    tone_passed: bool = Field(default=True, description="Whether tone and speculation checks passed")
    missing_sections: List[str] = Field(default_factory=list, description="List of mandatory sections missing from text")
    word_count: int = Field(default=0, description="Total word count in article markdown")
    analytical_density_score: int = Field(default=0, description="Count of distinct tactical/analytical concepts identified")
    max_similarity_score: float = Field(default=0.0, description="Highest trigram Jaccard similarity against recent 5 articles")
    most_similar_article_id: Optional[int] = Field(default=None, description="ID of article with highest similarity")
    flagged_phrases: List[str] = Field(default_factory=list, description="Banned sensationalist or speculative phrases detected")
    supervisor_notes: List[str] = Field(default_factory=list, description="Actionable editorial supervisor notes for human review")
    details: Dict[str, Any] = Field(default_factory=dict, description="Detailed diagnostic telemetry")


class EditorialSupervisorAgent:
    """
    Agent 8: Editorial Quality Supervisor.
    Enforces high-density editorial integrity:
    1. Completeness Gate: All 11 mandatory match review sections present, min word count, analytical density.
    2. Anti-Repetition Check: Trigram / Jaccard similarity against last 5 published articles (threshold 0.65).
    3. Tone & Speculation Filter: Scans for sensationalist clickbait and unverified medical/video claims.
    """

    MIN_TOTAL_WORDS: int = 250
    MIN_ANALYTICAL_CONCEPTS: int = 3
    SIMILARITY_THRESHOLD: float = 0.65

    MANDATORY_SECTIONS: List[Tuple[str, re.Pattern]] = [
        ("1. Executive Summary & Tactical Narrative", re.compile(r"(executive\s+summary|tactical\s+narrative|match\s+overview)", re.IGNORECASE)),
        ("2. Team Lineups & Tactical Formations", re.compile(r"(lineup|tactical\s+formation|starting\s+xi|system\s+shape)", re.IGNORECASE)),
        ("3. First-Half Dynamic & Early Dominance", re.compile(r"(first-half|first\s+half|opening\s+45|early\s+dominance)", re.IGNORECASE)),
        ("4. Second-Half Tactical Adjustments", re.compile(r"(second-half|second\s+half|closing\s+45|tactical\s+adjustment)", re.IGNORECASE)),
        ("5. Build-Up Phase & High-Press Mechanics", re.compile(r"(build-up|buildup|pressing|high-press|counter-press)", re.IGNORECASE)),
        ("6. Expected Goals (xG) & Statistical Context", re.compile(r"(expected\s+goals|xg|statistical\s+context|metrics\s+breakdown)", re.IGNORECASE)),
        ("7. Turning Points & Decisive Moments", re.compile(r"(turning\s+point|decisive\s+moment|key\s+moment|crucial\s+sequence)", re.IGNORECASE)),
        ("8. Key Tactical Strengths", re.compile(r"(tactical\s+strength|strengths\s+shown|core\s+strengths)", re.IGNORECASE)),
        ("9. Structural Vulnerabilities", re.compile(r"(structural\s+vulnerabilit|vulnerabilit|tactical\s+weakness|defensive\s+flaw)", re.IGNORECASE)),
        ("10. Player Ratings & Performance Matrix", re.compile(r"(player\s+rating|performance\s+matrix|ratings\s+summary)", re.IGNORECASE)),
        ("11. Final Strategic Verdict & Title Implications", re.compile(r"(final\s+strategic\s+verdict|final\s+verdict|strategic\s+verdict|title\s+implication)", re.IGNORECASE)),
    ]

    ANALYTICAL_KEYWORDS: List[str] = [
        "xg", "expected goals", "possession", "press", "pressing", "counter-press",
        "formation", "pivot", "rest-defense", "progression", "transition",
        "half-space", "block", "compactness", "verticality", "duel"
    ]

    BANNED_PHRASES: List[str] = [
        "shocking revelation",
        "you won't believe",
        "humiliating collapse",
        "career ending injury",
        "unconfirmed leaked video",
        "scandalous leak",
        "furious row",
        "dressing room brawl",
        "secret medical report",
        "insider caught on tape",
        "conspiracy against barca",
        "referee was paid",
        "bizarre meltdown",
        "bombshell rumor",
        "explosive feud",
    ]

    @classmethod
    def _extract_words(cls, text: str) -> List[str]:
        return re.findall(r"\b[a-zA-Z0-9_\'\-]+\b", text.lower())

    @classmethod
    def _build_trigrams(cls, words: List[str]) -> Set[Tuple[str, str, str]]:
        if len(words) < 3:
            return set()
        return {tuple(words[i:i+3]) for i in range(len(words) - 2)}

    @classmethod
    def _compute_jaccard_similarity(cls, set_a: Set[Any], set_b: Set[Any]) -> float:
        if not set_a or not set_b:
            return 0.0
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        return float(intersection) / float(union) if union > 0 else 0.0

    @classmethod
    def evaluate_article(
        cls,
        article_data: EditorialArticleSchema,
        match: Optional[Match] = None,
        exclude_article_id: Optional[int] = None
    ) -> SupervisorAuditResult:
        """
        Executes complete Agent 8 editorial supervision evaluation.
        Returns SupervisorAuditResult with pass/fail and actionable notes.
        """
        notes: List[str] = []
        full_text = f"{article_data.headline}\n{article_data.subtitle}\n{article_data.markdown_body}"
        body_text = article_data.markdown_body
        words = cls._extract_words(body_text)
        word_count = len(words)

        # ---------------------------------------------------------
        # 1. COMPLETENESS GATE
        # ---------------------------------------------------------
        missing_sections: List[str] = []
        for name, pattern in cls.MANDATORY_SECTIONS:
            if not pattern.search(body_text):
                missing_sections.append(name)

        # Check analytical concepts density
        body_lower = body_text.lower()
        found_concepts = {kw for kw in cls.ANALYTICAL_KEYWORDS if kw in body_lower}
        analytical_density_score = len(found_concepts)

        completeness_passed = True
        if missing_sections:
            completeness_passed = False
            notes.append(f"Completeness Gate Failed: Missing {len(missing_sections)} of 11 mandatory sections: {', '.join(missing_sections)}.")

        if word_count < cls.MIN_TOTAL_WORDS:
            completeness_passed = False
            notes.append(f"Completeness Gate Failed: Word count ({word_count}) below minimum threshold ({cls.MIN_TOTAL_WORDS} words).")

        if analytical_density_score < cls.MIN_ANALYTICAL_CONCEPTS:
            completeness_passed = False
            notes.append(f"Completeness Gate Failed: Analytical density ({analytical_density_score} concepts) below required minimum ({cls.MIN_ANALYTICAL_CONCEPTS}).")

        # ---------------------------------------------------------
        # 2. ANTI-REPETITION CHECK
        # ---------------------------------------------------------
        anti_repetition_passed = True
        max_similarity = 0.0
        most_similar_id: Optional[int] = None

        candidate_trigrams = cls._build_trigrams(words)
        recent_qs = Article.objects.filter(status=Article.STATUS_PUBLISHED)
        if exclude_article_id:
            recent_qs = recent_qs.exclude(id=exclude_article_id)

        recent_articles = list(recent_qs.order_by('-published_at')[:5])

        for prev in recent_articles:
            prev_words = cls._extract_words(prev.content or "")
            prev_trigrams = cls._build_trigrams(prev_words)
            sim = cls._compute_jaccard_similarity(candidate_trigrams, prev_trigrams)
            if sim > max_similarity:
                max_similarity = round(sim, 4)
                most_similar_id = prev.id

        if max_similarity >= cls.SIMILARITY_THRESHOLD:
            anti_repetition_passed = False
            notes.append(
                f"Anti-Repetition Gate Failed: Trigram similarity {max_similarity:.2%} exceeds threshold {cls.SIMILARITY_THRESHOLD:.2%} "
                f"against published article #{most_similar_id}."
            )

        # ---------------------------------------------------------
        # 3. TONE & SPECULATION FILTER
        # ---------------------------------------------------------
        tone_passed = True
        flagged_phrases: List[str] = []
        full_lower = full_text.lower()

        for phrase in cls.BANNED_PHRASES:
            if phrase in full_lower:
                flagged_phrases.append(phrase)

        if flagged_phrases:
            tone_passed = False
            notes.append(f"Tone & Speculation Gate Failed: Detected banned phrases: {', '.join(flagged_phrases)}.")

        # ---------------------------------------------------------
        # FINAL STATUS
        # ---------------------------------------------------------
        overall_passed = completeness_passed and anti_repetition_passed and tone_passed

        return SupervisorAuditResult(
            passed=overall_passed,
            completeness_passed=completeness_passed,
            anti_repetition_passed=anti_repetition_passed,
            tone_passed=tone_passed,
            missing_sections=missing_sections,
            word_count=word_count,
            analytical_density_score=analytical_density_score,
            max_similarity_score=max_similarity,
            most_similar_article_id=most_similar_id,
            flagged_phrases=flagged_phrases,
            supervisor_notes=notes,
            details={
                "analytical_concepts_found": list(found_concepts),
                "inspected_recent_article_count": len(recent_articles),
            }
        )

