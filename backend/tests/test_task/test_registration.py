"""Guard against the Celery task registry losing its pipeline tasks.

Importing `app.celery_app` must transitively import `app.tasks` (via the
explicit `import app.tasks` side-effect line in celery_app.py), which is what
registers every saga task with the Celery app. That import line is a
side-effect import with no referenced name, so linters and editor "remove
unused import" actions have repeatedly stripped it, leaving only the inline
`ping` task registered and every upload stuck at QUEUED.

This test fails loudly if that ever happens again, turning a silent runtime
outage into an obvious test failure.
"""

from __future__ import annotations

from app.celery_app import celery_app

# Every task the saga pipeline dispatches. If any is missing from the Celery
# registry, the pipeline cannot run end to end.
EXPECTED_TASKS = {
    "app.tasks.parse.parse_document_task",
    "app.tasks.classify.classify_clauses_task",
    "app.tasks.dispatchers.dispatch_analysis_task",
    "app.tasks.dispatchers.dispatch_redlines_task",
    "app.tasks.score.analyze_one_clause_task",
    "app.tasks.score.score_contract_task",
    "app.tasks.redline.generate_one_redline_task",
    "app.tasks.redline.redlines_complete_task",
    "app.tasks.finalize.finalize_contract_task",
}


def test_pipeline_tasks_are_registered() -> None:
    """Every saga task must be registered on the Celery app.

    Regression guard for the `import app.tasks` side-effect line in
    celery_app.py being removed, which silently leaves the worker able to
    register only the inline `ping` task and wedges every upload at QUEUED.
    """
    registered = set(celery_app.tasks.keys())
    missing = EXPECTED_TASKS - registered
    assert not missing, (
        f"Celery is missing pipeline tasks: {sorted(missing)}. "
        "This usually means the `import app.tasks` line in app/celery_app.py "
        "was removed (linter or editor 'remove unused import'). Restore it."
    )