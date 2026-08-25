"""Unit tests for the Pydantic models in app.models: field validation,
defaults, and serialization — independent of storage or the HTTP layer.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from app.models import (
    Collection,
    CollectionCreate,
    CollectionList,
    HealthResponse,
    Prompt,
    PromptCreate,
    PromptList,
    PromptPatch,
    PromptUpdate,
    generate_id,
    get_current_time,
)


class TestGenerateId:
    def test_returns_a_string(self):
        assert isinstance(generate_id(), str)

    def test_returns_a_unique_value_each_call(self):
        assert generate_id() != generate_id()

    def test_returns_a_valid_uuid4_format(self):
        # 8-4-4-4-12 hex groups, version nibble '4'
        value = generate_id()
        parts = value.split("-")
        assert [len(p) for p in parts] == [8, 4, 4, 4, 12]
        assert parts[2][0] == "4"


class TestGetCurrentTime:
    def test_returns_a_naive_datetime(self):
        """No tzinfo — the whole codebase treats timestamps as naive UTC."""
        result = get_current_time()
        assert isinstance(result, datetime)
        assert result.tzinfo is None


class TestPromptCreateValidation:
    """PromptCreate is used for POST /prompts; PromptBase's constraints apply."""

    def test_minimal_valid_payload(self):
        prompt = PromptCreate(title="T", content="C")
        assert prompt.description is None
        assert prompt.collection_id is None

    def test_title_is_required(self):
        with pytest.raises(ValidationError) as exc_info:
            PromptCreate(content="C")
        assert any(e["loc"] == ("title",) for e in exc_info.value.errors())

    def test_content_is_required(self):
        with pytest.raises(ValidationError) as exc_info:
            PromptCreate(title="T")
        assert any(e["loc"] == ("content",) for e in exc_info.value.errors())

    def test_empty_title_is_rejected(self):
        with pytest.raises(ValidationError):
            PromptCreate(title="", content="C")

    def test_empty_content_is_rejected(self):
        with pytest.raises(ValidationError):
            PromptCreate(title="T", content="")

    def test_title_over_200_chars_is_rejected(self):
        with pytest.raises(ValidationError):
            PromptCreate(title="x" * 201, content="C")

    def test_title_at_200_chars_is_accepted(self):
        prompt = PromptCreate(title="x" * 200, content="C")
        assert len(prompt.title) == 200

    def test_description_over_500_chars_is_rejected(self):
        with pytest.raises(ValidationError):
            PromptCreate(title="T", content="C", description="x" * 501)

    def test_description_at_500_chars_is_accepted(self):
        prompt = PromptCreate(title="T", content="C", description="x" * 500)
        assert len(prompt.description) == 500

    def test_id_is_not_a_field_and_is_silently_ignored(self):
        """A client can't forge an id through the create request body."""
        prompt = PromptCreate(title="T", content="C", id="forged")
        assert not hasattr(prompt, "id")


class TestPromptUpdateValidation:
    """PromptUpdate is used for PUT /prompts/{id}. title/content are required, same as
    PromptCreate; description/collection_id are optional and default to None — so
    omitting them from a PUT body has the same effect as sending them as null, which is
    what makes PUT a full replace: nothing you leave out survives the update.
    """

    def test_title_is_required(self):
        with pytest.raises(ValidationError):
            PromptUpdate(content="C")

    def test_content_is_required(self):
        with pytest.raises(ValidationError):
            PromptUpdate(title="T")

    def test_full_payload_is_valid(self):
        update = PromptUpdate(title="T", content="C", description=None, collection_id=None)
        assert update.title == "T"

    def test_omitting_optional_fields_defaults_them_to_none(self):
        """This is the mechanism that makes PUT a full replace rather than a partial update."""
        update = PromptUpdate(title="T", content="C")
        assert update.description is None
        assert update.collection_id is None

    def test_same_length_constraints_as_create(self):
        with pytest.raises(ValidationError):
            PromptUpdate(title="", content="C", description=None, collection_id=None)


class TestPromptPatchValidation:
    """PromptPatch is used for PATCH /prompts/{id} — every field is optional."""

    def test_empty_body_is_valid(self):
        patch = PromptPatch()
        assert patch.title is None
        assert patch.content is None

    def test_only_title_set_leaves_others_unset(self):
        patch = PromptPatch(title="New")
        dumped = patch.model_dump(exclude_unset=True)
        assert dumped == {"title": "New"}

    def test_explicit_null_is_distinguishable_from_omitted(self):
        """This is the mechanism patch_prompt relies on to tell 'leave alone' from 'clear it'."""
        omitted = PromptPatch(title="New")
        explicit_null = PromptPatch(title="New", description=None)

        assert "description" not in omitted.model_dump(exclude_unset=True)
        assert "description" in explicit_null.model_dump(exclude_unset=True)
        assert explicit_null.model_dump(exclude_unset=True)["description"] is None

    def test_title_length_constraints_still_apply_when_provided(self):
        with pytest.raises(ValidationError):
            PromptPatch(title="")

    def test_title_can_be_explicitly_null_at_the_model_level(self):
        """The model itself allows title=None; patch_prompt is what rejects it with a 400 — that's
        an API-layer business rule, not a schema constraint, so the model must accept it here."""
        patch = PromptPatch(title=None)
        assert "title" in patch.model_dump(exclude_unset=True)
        assert patch.model_dump(exclude_unset=True)["title"] is None


class TestPromptDefaults:
    """Prompt is the stored/response model — id, timestamps, and deleted_on are server-managed."""

    def test_id_defaults_to_a_generated_value(self):
        prompt = Prompt(title="T", content="C")
        assert prompt.id
        assert isinstance(prompt.id, str)

    def test_two_prompts_get_different_ids(self):
        a = Prompt(title="T", content="C")
        b = Prompt(title="T", content="C")
        assert a.id != b.id

    def test_created_at_and_updated_at_default_to_now(self):
        before = get_current_time()
        prompt = Prompt(title="T", content="C")
        after = get_current_time()
        assert before <= prompt.created_at <= after
        assert before <= prompt.updated_at <= after

    def test_deleted_on_defaults_to_none(self):
        assert Prompt(title="T", content="C").deleted_on is None

    def test_explicit_values_override_defaults(self):
        fixed_time = datetime(2020, 1, 1)
        prompt = Prompt(title="T", content="C", id="fixed-id", created_at=fixed_time, updated_at=fixed_time)
        assert prompt.id == "fixed-id"
        assert prompt.created_at == fixed_time

    def test_from_attributes_builds_from_an_object(self):
        """Config.from_attributes = True lets Prompt.model_validate read attributes off any object."""

        class FakeRow:
            title = "T"
            content = "C"
            description = None
            collection_id = None
            id = "row-id"
            created_at = datetime(2020, 1, 1)
            updated_at = datetime(2020, 1, 1)
            deleted_on = None

        prompt = Prompt.model_validate(FakeRow())
        assert prompt.id == "row-id"
        assert prompt.title == "T"


class TestCollectionValidation:
    def test_name_is_required(self):
        with pytest.raises(ValidationError):
            CollectionCreate()

    def test_empty_name_is_rejected(self):
        with pytest.raises(ValidationError):
            CollectionCreate(name="")

    def test_name_over_100_chars_is_rejected(self):
        with pytest.raises(ValidationError):
            CollectionCreate(name="x" * 101)

    def test_name_at_100_chars_is_accepted(self):
        collection = CollectionCreate(name="x" * 100)
        assert len(collection.name) == 100

    def test_description_over_500_chars_is_rejected(self):
        with pytest.raises(ValidationError):
            CollectionCreate(name="N", description="x" * 501)

    def test_description_is_optional(self):
        assert CollectionCreate(name="N").description is None


class TestCollectionDefaults:
    def test_id_defaults_to_a_generated_value(self):
        assert Collection(name="N").id

    def test_deleted_on_defaults_to_none(self):
        assert Collection(name="N").deleted_on is None

    def test_created_at_defaults_to_now(self):
        before = get_current_time()
        collection = Collection(name="N")
        after = get_current_time()
        assert before <= collection.created_at <= after


class TestResponseModelSerialization:
    """PromptList / CollectionList / HealthResponse — the response envelopes."""

    def test_prompt_list_round_trips_total_and_items(self):
        prompt = Prompt(title="T", content="C")
        listing = PromptList(prompts=[prompt], total=1)
        dumped = listing.model_dump()
        assert dumped["total"] == 1
        assert dumped["prompts"][0]["id"] == prompt.id

    def test_collection_list_round_trips_total_and_items(self):
        collection = Collection(name="N")
        listing = CollectionList(collections=[collection], total=1)
        assert listing.model_dump()["total"] == 1

    def test_health_response_fields(self):
        health = HealthResponse(status="healthy", version="0.1.0")
        assert health.model_dump() == {"status": "healthy", "version": "0.1.0"}

    def test_prompt_serializes_datetime_without_timezone_suffix(self):
        """Documented behavior (README/API_REFERENCE): naive UTC, no trailing 'Z' or offset."""
        prompt = Prompt(title="T", content="C", created_at=datetime(2026, 1, 1, 12, 30, 0))
        serialized = prompt.model_dump(mode="json")["created_at"]
        assert serialized == "2026-01-01T12:30:00"
