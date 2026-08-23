"""Unit tests for helper functions in app.utils."""

from datetime import datetime, timedelta

from app.models import Prompt
from app.utils import sort_prompts_by_date


def _prompt(title: str, created_at: datetime) -> Prompt:
    """Build a Prompt with a fixed creation time for sort tests."""
    return Prompt(title=title, content="content", created_at=created_at, updated_at=created_at)


def _three_prompts():
    """Return three prompts created one minute apart, in oldest-to-newest order."""
    base = datetime(2026, 1, 1, 12, 0, 0)
    return [
        _prompt("oldest", base),
        _prompt("middle", base + timedelta(minutes=1)),
        _prompt("newest", base + timedelta(minutes=2)),
    ]


class TestSortPromptsByDate:
    """Unit tests for sort_prompts_by_date in isolation from the API."""
    def test_default_is_newest_first(self):
        """With no arguments the newest prompt is first (Bug #3 fix)."""
        result = sort_prompts_by_date(_three_prompts())
        assert [p.title for p in result] == ["newest", "middle", "oldest"]

    def test_descending_false_is_oldest_first(self):
        """descending=False reverses the order to oldest first."""
        result = sort_prompts_by_date(_three_prompts(), descending=False)
        assert [p.title for p in result] == ["oldest", "middle", "newest"]

    def test_does_not_mutate_input(self):
        """Sorting returns a new list and leaves the caller's list in its original order."""
        prompts = _three_prompts()
        sort_prompts_by_date(prompts)
        assert [p.title for p in prompts] == ["oldest", "middle", "newest"]
