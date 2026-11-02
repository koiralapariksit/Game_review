import os
from django.conf import settings
from django.utils import timezone
from matches.models import Match
from analysis.models import Article, AIWorkflowExecution
from analysis.schemas import EditorialArticleSchema
from analysis.services.fact_checker import DeterministicFactChecker


def publish_article_with_policy(
    article_data: EditorialArticleSchema,
    match: Match,
    execution: AIWorkflowExecution,
    auto_publish_mode: bool = True
) -> Article:
    """
    Validates article against database facts and publishes or routes to REVIEW_REQUIRED.
    Supports Mode A (Auto-Publish on valid check) and Mode B (Always require human review).
    """
    validation_res = DeterministicFactChecker.verify_match_report(article_data, match)
    
    execution.stage = AIWorkflowExecution.STAGE_FACT_CHECKED
    execution.validation_report = validation_res.model_dump()
    execution.save()

    if not validation_res.is_valid:
        execution.stage = AIWorkflowExecution.STAGE_REVIEW_REQUIRED
        execution.save()

        article, _ = Article.objects.update_or_create(
            match=match,
            category=Article.CATEGORY_MATCH_REVIEW,
            defaults={
                'title': article_data.headline[:200],
                'subtitle': article_data.subtitle[:255],
                'content': article_data.markdown_body,
                'status': Article.STATUS_REVIEW_REQUIRED,
                'is_ai_generated': True,
            }
        )
        return article

    # Fact checks passed
    if auto_publish_mode:
        status = Article.STATUS_PUBLISHED
        published_at = timezone.now()
        execution.stage = AIWorkflowExecution.STAGE_PUBLISHED
    else:
        status = Article.STATUS_APPROVED
        published_at = None
        execution.stage = AIWorkflowExecution.STAGE_APPROVED

    execution.completed_at = timezone.now()
    execution.save()

    article, _ = Article.objects.update_or_create(
        match=match,
        category=Article.CATEGORY_MATCH_REVIEW,
        defaults={
            'title': article_data.headline[:200],
            'subtitle': article_data.subtitle[:255],
            'content': article_data.markdown_body,
            'status': status,
            'published_at': published_at,
            'is_ai_generated': True,
        }
    )
    return article
