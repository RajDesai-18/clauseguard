"""Celery task definitions.

Per the Phase 1 learning, autodiscovery alone is unreliable on this
setup. Every task module must be imported explicitly here so the
Celery worker registers all task names at startup.
"""

from app.tasks.classify import classify_clauses_task  # noqa: F401
from app.tasks.dispatchers import (  # noqa: F401
    dispatch_analysis_task,
    dispatch_redlines_task,
)
from app.tasks.finalize import finalize_contract_task  # noqa: F401
from app.tasks.parse import parse_document_task  # noqa: F401
from app.tasks.pipeline import run_pipeline  # noqa: F401
from app.tasks.redline import (  # noqa: F401
    generate_one_redline_task,
    redlines_complete_task,
)
from app.tasks.score import (  # noqa: F401
    analyze_one_clause_task,
    score_contract_task,
)
