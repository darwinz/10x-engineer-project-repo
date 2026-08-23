"""Unit tests for helper functions in app.utils."""

from datetime import datetime, timedelta

from app.models import Prompt
from app.utils import sort_prompts_by_date


def _prompt(title: str, created_at: datetime) -> Prompt:
    return Prompt(title=title, content="content", created_at=created_at, updated_at=created_at)


def _three_prompts():
    base = datetime(2026, 1, 1, 12, 0, 0)
    return [
        _prompt("oldest", base),
        _prompt("middle", base + timedelta(minutes=1)),
        _prompt("newest", base + timedelta(minutes=2)),
    ]


class TestSortPromptsByDate:
    def test_default_is_newest_first(self):
        result = sort_prompts_by_date(_three_prompts())
        assert [p.title for p in result] == ["newest", "middle", "oldest"]

    def test_descending_false_is_oldest_first(self):
        result = sort_prompts_by_date(_three_prompts(), descending=False)
        assert [p.title for p in result] == ["oldest", "middle", "newest"]

    def test_does_not_mutate_input(self):
        prompts = _three_prompts()
        sort_prompts_by_date(prompts)
        assert [p.title for p in prompts] == ["oldest", "middle", "newest"]
