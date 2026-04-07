"""Celery task tests."""

from app.celery_app import ping


def test_ping_task():
    """Ping task should return pong."""
    result = ping()
    assert result == "pong"
