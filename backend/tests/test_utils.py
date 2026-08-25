"""Unit tests for helper functions in app.utils."""

from datetime import datetime, timedelta

from app.models import Prompt
from app.utils import (
    extract_variables,
    filter_prompts_by_collection,
    search_prompts,
    sort_prompts_by_date,
    validate_prompt_content,
)


def _prompt(title: str, created_at: datetime = None, **overrides) -> Prompt:
    """Build a Prompt with a fixed creation time for sort tests, overridable for others."""
    created_at = created_at or datetime(2026, 1, 1)
    return Prompt(title=title, content="content", created_at=created_at, updated_at=created_at, **overrides)


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

    def test_empty_list_returns_empty_list(self):
        assert sort_prompts_by_date([]) == []


class TestFilterPromptsByCollection:
    """Unit tests for filter_prompts_by_collection in isolation from the API."""

    def test_returns_only_matching_prompts(self):
        matching = _prompt("Match", collection_id="c1")
        other = _prompt("Other", collection_id="c2")
        result = filter_prompts_by_collection([matching, other], "c1")
        assert result == [matching]

    def test_prompt_with_no_collection_never_matches(self):
        uncategorized = _prompt("Uncategorized")
        assert filter_prompts_by_collection([uncategorized], "c1") == []

    def test_no_matches_returns_empty_list(self):
        other = _prompt("Other", collection_id="c2")
        assert filter_prompts_by_collection([other], "c1") == []

    def test_empty_input_returns_empty_list(self):
        assert filter_prompts_by_collection([], "c1") == []

    def test_does_not_mutate_input(self):
        prompts = [_prompt("Match", collection_id="c1"), _prompt("Other", collection_id="c2")]
        filter_prompts_by_collection(prompts, "c1")
        assert len(prompts) == 2


class TestSearchPrompts:
    """Unit tests for search_prompts in isolation from the API."""

    def test_matches_title_substring(self):
        prompt = _prompt("Code Review Prompt")
        assert search_prompts([prompt], "review") == [prompt]

    def test_matches_description_substring(self):
        prompt = _prompt("Untitled", description="Helps with security audits")
        assert search_prompts([prompt], "security") == [prompt]

    def test_match_is_case_insensitive(self):
        prompt = _prompt("SECURITY review")
        assert search_prompts([prompt], "security") == [prompt]

    def test_prompt_with_no_description_does_not_error(self):
        """description is None on some prompts; the search must not raise on that."""
        prompt = _prompt("Title only", description=None)
        assert search_prompts([prompt], "nomatch") == []

    def test_no_match_returns_empty_list(self):
        prompt = _prompt("Code Review")
        assert search_prompts([prompt], "nonexistent term") == []

    def test_preserves_input_order(self):
        first = _prompt("Alpha review")
        second = _prompt("Beta review")
        assert search_prompts([first, second], "review") == [first, second]

    def test_empty_query_matches_every_prompt(self):
        """An empty string is a substring of every string, so this is expected, not a bug."""
        prompt = _prompt("Anything")
        assert search_prompts([prompt], "") == [prompt]

    def test_does_not_mutate_input(self):
        prompts = [_prompt("Match review"), _prompt("No match here")]
        search_prompts(prompts, "review")
        assert len(prompts) == 2


class TestValidatePromptContent:
    """Unit tests for validate_prompt_content."""

    def test_content_of_at_least_10_chars_is_valid(self):
        assert validate_prompt_content("0123456789") is True

    def test_content_of_exactly_9_chars_is_invalid(self):
        assert validate_prompt_content("012345678") is False

    def test_empty_string_is_invalid(self):
        assert validate_prompt_content("") is False

    def test_whitespace_only_is_invalid(self):
        assert validate_prompt_content("          ") is False

    def test_length_is_measured_after_stripping_whitespace(self):
        """Leading/trailing whitespace shouldn't count toward the 10-character minimum."""
        assert validate_prompt_content("   1234   ") is False  # 4 real chars
        assert validate_prompt_content("   0123456789   ") is True  # 10 real chars

    def test_none_is_invalid(self):
        assert validate_prompt_content(None) is False


class TestExtractVariables:
    """Unit tests for extract_variables."""

    def test_no_variables_returns_empty_list(self):
        assert extract_variables("Plain text, no placeholders.") == []

    def test_single_variable(self):
        assert extract_variables("Review this: {{code}}") == ["code"]

    def test_multiple_distinct_variables_in_order(self):
        assert extract_variables("{{first}} then {{second}}") == ["first", "second"]

    def test_duplicate_variable_appears_once_per_occurrence(self):
        assert extract_variables("{{code}} ... {{code}}") == ["code", "code"]

    def test_variable_name_with_digits_and_underscore(self):
        assert extract_variables("{{user_input_2}}") == ["user_input_2"]

    def test_single_braces_are_not_matched(self):
        assert extract_variables("{code}") == []

    def test_unmatched_double_brace_is_not_matched(self):
        assert extract_variables("{{code} and {code}}") == []

    def test_empty_string_returns_empty_list(self):
        assert extract_variables("") == []

    def test_variable_with_hyphen_is_not_matched(self):
        """Only \\w (letters, digits, underscore) is a valid variable-name character."""
        assert extract_variables("{{user-input}}") == []
