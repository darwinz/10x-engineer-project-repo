"""Unit tests for the Storage class in app.storage, in isolation from the API.

These construct Prompt/Collection objects directly and call Storage methods
on a fresh instance, rather than going through the HTTP layer — the API
tests in test_api.py already cover the routes; these cover the storage
behaviors an API test can't reach directly, like update_prompt's return
value for an unknown id, or that lookups return the live stored object
rather than a copy.
"""

from datetime import datetime

import pytest

from app.models import Collection, Prompt
from app.storage import Storage


@pytest.fixture
def store():
    """A fresh Storage instance, independent of the app-wide singleton."""
    return Storage()


def _prompt(**overrides) -> Prompt:
    """Build a Prompt with sensible defaults, overridable per test."""
    defaults = {"title": "Title", "content": "Some content"}
    return Prompt(**{**defaults, **overrides})


def _collection(**overrides) -> Collection:
    """Build a Collection with sensible defaults, overridable per test."""
    defaults = {"name": "Collection"}
    return Collection(**{**defaults, **overrides})


class TestPromptCRUD:
    """create_prompt / get_prompt / update_prompt / delete_prompt."""

    def test_create_and_get_prompt(self, store):
        prompt = _prompt()
        store.create_prompt(prompt)
        assert store.get_prompt(prompt.id) is prompt

    def test_create_prompt_returns_the_same_object(self, store):
        prompt = _prompt()
        assert store.create_prompt(prompt) is prompt

    def test_get_prompt_unknown_id_returns_none(self, store):
        assert store.get_prompt("nonexistent") is None

    def test_get_prompt_excludes_soft_deleted_by_default(self, store):
        prompt = _prompt()
        store.create_prompt(prompt)
        store.delete_prompt(prompt.id)
        assert store.get_prompt(prompt.id) is None

    def test_get_prompt_include_deleted_returns_soft_deleted(self, store):
        prompt = _prompt()
        store.create_prompt(prompt)
        store.delete_prompt(prompt.id)
        found = store.get_prompt(prompt.id, include_deleted=True)
        assert found is prompt
        assert found.deleted_on is not None

    def test_update_prompt_replaces_stored_object(self, store):
        original = _prompt(title="Original")
        store.create_prompt(original)

        replacement = _prompt(id=original.id, title="Replaced")
        result = store.update_prompt(original.id, replacement)

        assert result is replacement
        assert store.get_prompt(original.id).title == "Replaced"

    def test_update_prompt_unknown_id_returns_none_and_does_not_insert(self, store):
        """Calling update_prompt for an id that was never created is a no-op, not an insert."""
        replacement = _prompt(id="ghost", title="Should not be stored")
        assert store.update_prompt("ghost", replacement) is None
        assert store.get_prompt("ghost") is None

    def test_update_prompt_on_soft_deleted_id_returns_none(self, store):
        """update_prompt treats a soft-deleted prompt as not existing, same as get_prompt."""
        prompt = _prompt()
        store.create_prompt(prompt)
        store.delete_prompt(prompt.id)

        replacement = _prompt(id=prompt.id, title="New")
        assert store.update_prompt(prompt.id, replacement) is None

    def test_delete_prompt_marks_deleted_on_and_returns_true(self, store):
        prompt = _prompt()
        store.create_prompt(prompt)
        assert prompt.deleted_on is None

        assert store.delete_prompt(prompt.id) is True
        assert prompt.deleted_on is not None
        assert isinstance(prompt.deleted_on, datetime)

    def test_delete_prompt_unknown_id_returns_false(self, store):
        assert store.delete_prompt("nonexistent") is False

    def test_delete_prompt_already_deleted_returns_false(self, store):
        prompt = _prompt()
        store.create_prompt(prompt)
        assert store.delete_prompt(prompt.id) is True
        assert store.delete_prompt(prompt.id) is False

    def test_delete_prompt_accepts_an_explicit_timestamp(self, store):
        """delete_collection relies on this to stamp a prompt with the collection's own deletion time."""
        prompt = _prompt()
        store.create_prompt(prompt)
        fixed_time = datetime(2020, 1, 1, 0, 0, 0)

        store.delete_prompt(prompt.id, deleted_on=fixed_time)
        assert prompt.deleted_on == fixed_time


class TestGetAllPrompts:
    """get_all_prompts."""

    def test_empty_store_returns_empty_list(self, store):
        assert store.get_all_prompts() == []

    def test_returns_only_active_prompts(self, store):
        active = _prompt(title="Active")
        deleted = _prompt(title="Deleted")
        store.create_prompt(active)
        store.create_prompt(deleted)
        store.delete_prompt(deleted.id)

        result = store.get_all_prompts()
        assert result == [active]

    def test_returns_a_new_list_each_call(self, store):
        """Mutating the returned list must not affect storage's internal state."""
        store.create_prompt(_prompt())
        result = store.get_all_prompts()
        result.clear()
        assert len(store.get_all_prompts()) == 1


class TestCollectionCRUD:
    """create_collection / get_collection / delete_collection."""

    def test_create_and_get_collection(self, store):
        collection = _collection()
        store.create_collection(collection)
        assert store.get_collection(collection.id) is collection

    def test_create_collection_returns_the_same_object(self, store):
        collection = _collection()
        assert store.create_collection(collection) is collection

    def test_get_collection_unknown_id_returns_none(self, store):
        assert store.get_collection("nonexistent") is None

    def test_get_collection_excludes_soft_deleted_by_default(self, store):
        collection = _collection()
        store.create_collection(collection)
        store.delete_collection(collection.id)
        assert store.get_collection(collection.id) is None

    def test_get_collection_include_deleted_returns_soft_deleted(self, store):
        collection = _collection()
        store.create_collection(collection)
        store.delete_collection(collection.id)
        found = store.get_collection(collection.id, include_deleted=True)
        assert found is collection
        assert found.deleted_on is not None

    def test_delete_collection_unknown_id_returns_false(self, store):
        assert store.delete_collection("nonexistent") is False

    def test_delete_collection_already_deleted_returns_false(self, store):
        collection = _collection()
        store.create_collection(collection)
        assert store.delete_collection(collection.id) is True
        assert store.delete_collection(collection.id) is False

    def test_delete_collection_cascades_to_its_active_prompts(self, store):
        collection = _collection()
        store.create_collection(collection)
        in_collection = _prompt(title="In", collection_id=collection.id)
        other = _prompt(title="Other")
        store.create_prompt(in_collection)
        store.create_prompt(other)

        store.delete_collection(collection.id)

        assert in_collection.deleted_on is not None
        assert other.deleted_on is None  # untouched — not in this collection

    def test_delete_collection_cascade_uses_one_shared_timestamp(self, store):
        collection = _collection()
        store.create_collection(collection)
        prompt = _prompt(collection_id=collection.id)
        store.create_prompt(prompt)

        store.delete_collection(collection.id)

        assert prompt.deleted_on == collection.deleted_on

    def test_delete_collection_leaves_collection_id_on_cascaded_prompts(self, store):
        """The prompt keeps pointing at the (now deleted) collection, so the grouping is recoverable."""
        collection = _collection()
        store.create_collection(collection)
        prompt = _prompt(collection_id=collection.id)
        store.create_prompt(prompt)

        store.delete_collection(collection.id)

        assert prompt.collection_id == collection.id

    def test_delete_collection_does_not_touch_already_deleted_prompts_in_it(self, store):
        """A prompt deleted before its collection keeps its own original deleted_on."""
        collection = _collection()
        store.create_collection(collection)
        prompt = _prompt(collection_id=collection.id)
        store.create_prompt(prompt)
        store.delete_prompt(prompt.id)
        first_deletion = prompt.deleted_on

        store.delete_collection(collection.id)

        assert prompt.deleted_on == first_deletion


class TestGetAllCollections:
    """get_all_collections."""

    def test_empty_store_returns_empty_list(self, store):
        assert store.get_all_collections() == []

    def test_returns_only_active_collections(self, store):
        active = _collection(name="Active")
        deleted = _collection(name="Deleted")
        store.create_collection(active)
        store.create_collection(deleted)
        store.delete_collection(deleted.id)

        assert store.get_all_collections() == [active]


class TestGetPromptsByCollection:
    """get_prompts_by_collection."""

    def test_returns_matching_active_prompts_only(self, store):
        collection_id = "c1"
        matching = _prompt(title="Match", collection_id=collection_id)
        deleted_match = _prompt(title="Deleted match", collection_id=collection_id)
        other = _prompt(title="Other", collection_id="c2")
        store.create_prompt(matching)
        store.create_prompt(deleted_match)
        store.create_prompt(other)
        store.delete_prompt(deleted_match.id)

        assert store.get_prompts_by_collection(collection_id) == [matching]

    def test_no_matching_prompts_returns_empty_list(self, store):
        store.create_prompt(_prompt(collection_id="other"))
        assert store.get_prompts_by_collection("nonexistent-collection") == []

    def test_does_not_check_whether_the_collection_itself_exists(self, store):
        """get_prompts_by_collection matches purely on the field value — no lookup against _collections."""
        store.create_prompt(_prompt(collection_id="never-created"))
        assert len(store.get_prompts_by_collection("never-created")) == 1


class TestClear:
    """clear."""

    def test_clear_empties_both_stores(self, store):
        store.create_prompt(_prompt())
        store.create_collection(_collection())

        store.clear()

        assert store.get_all_prompts() == []
        assert store.get_all_collections() == []

    def test_clear_also_removes_soft_deleted_records(self, store):
        prompt = _prompt()
        store.create_prompt(prompt)
        store.delete_prompt(prompt.id)

        store.clear()

        assert store.get_prompt(prompt.id, include_deleted=True) is None


class TestLiveObjectSemantics:
    """Storage returns the stored objects themselves, not copies (documented in Storage's docstring)."""

    def test_mutating_a_returned_prompt_mutates_the_stored_record(self, store):
        prompt = _prompt(title="Before")
        store.create_prompt(prompt)

        fetched = store.get_prompt(prompt.id)
        fetched.title = "After"

        assert store.get_prompt(prompt.id).title == "After"

    def test_mutating_a_returned_collection_mutates_the_stored_record(self, store):
        collection = _collection(name="Before")
        store.create_collection(collection)

        fetched = store.get_collection(collection.id)
        fetched.name = "After"

        assert store.get_collection(collection.id).name == "After"
