"""Utility functions for PromptLab"""

from typing import List
from app.models import Prompt


def sort_prompts_by_date(prompts: List[Prompt], descending: bool = True) -> List[Prompt]:
    """Return the prompts ordered by their created_at timestamp.

    Args:
        prompts: The prompts to sort. The list is not modified.
        descending: If True (the default) the newest prompt comes first;
            if False the oldest comes first.

    Returns:
        A new list containing the same Prompt objects in sorted order.
    """
    return sorted(prompts, key=lambda p: p.created_at, reverse=descending)


def filter_prompts_by_collection(prompts: List[Prompt], collection_id: str) -> List[Prompt]:
    """Return only the prompts belonging to a given collection.

    Args:
        prompts: The prompts to filter. The list is not modified.
        collection_id: The collection id to match exactly against each
            prompt's `collection_id`.

    Returns:
        A new list containing the Prompt objects whose `collection_id`
        equals `collection_id`. Empty if none match.
    """
    return [p for p in prompts if p.collection_id == collection_id]


def search_prompts(prompts: List[Prompt], query: str) -> List[Prompt]:
    """Return the prompts whose title or description contain a query string.

    The match is case-insensitive and looks for `query` as a substring of
    the prompt's title, or of its description when one is set.

    Args:
        prompts: The prompts to search. The list is not modified.
        query: The text to search for.

    Returns:
        A new list containing the matching Prompt objects, in the order
        they appeared in `prompts`. Empty if none match.
    """
    query_lower = query.lower()
    return [
        p for p in prompts
        if query_lower in p.title.lower() or
           (p.description and query_lower in p.description.lower())
    ]


def validate_prompt_content(content: str) -> bool:
    """Check whether prompt content meets the minimum content requirements.

    Content is valid when, after stripping leading/trailing whitespace, it
    is non-empty and at least 10 characters long.

    Args:
        content: The prompt template text to validate.

    Returns:
        True if `content` is non-empty, is not just whitespace, and has at
        least 10 characters once stripped; False otherwise.
    """
    if not content or not content.strip():
        return False
    return len(content.strip()) >= 10


def extract_variables(content: str) -> List[str]:
    """Extract the names of template variables referenced in prompt content.

    Variables are written as `{{variable_name}}`, where `variable_name` is
    one or more word characters (letters, digits, underscore).

    Args:
        content: The prompt template text to scan.

    Returns:
        A list of variable names in the order they appear in `content`,
        including duplicates if a variable is referenced more than once.
        Empty if no variables are present.
    """
    import re
    pattern = r'\{\{(\w+)\}\}'
    return re.findall(pattern, content)
