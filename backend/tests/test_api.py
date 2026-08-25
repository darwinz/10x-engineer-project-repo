"""API tests for PromptLab

These tests verify the API endpoints work correctly.
Students should expand these tests significantly in Week 3.
"""

import pytest
from fastapi.testclient import TestClient


class TestHealth:
    """Tests for health endpoint."""
    
    def test_health_check(self, client: TestClient):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


class TestPrompts:
    """Tests for prompt endpoints."""
    
    def test_create_prompt(self, client: TestClient, sample_prompt_data):
        response = client.post("/prompts", json=sample_prompt_data)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == sample_prompt_data["title"]
        assert data["content"] == sample_prompt_data["content"]
        assert "id" in data
        assert "created_at" in data
    
    def test_list_prompts_empty(self, client: TestClient):
        response = client.get("/prompts")
        assert response.status_code == 200
        data = response.json()
        assert data["prompts"] == []
        assert data["total"] == 0
    
    def test_list_prompts_with_data(self, client: TestClient, sample_prompt_data):
        # Create a prompt first
        client.post("/prompts", json=sample_prompt_data)
        
        response = client.get("/prompts")
        assert response.status_code == 200
        data = response.json()
        assert len(data["prompts"]) == 1
        assert data["total"] == 1
    
    def test_get_prompt_success(self, client: TestClient, sample_prompt_data):
        # Create a prompt first
        create_response = client.post("/prompts", json=sample_prompt_data)
        prompt_id = create_response.json()["id"]
        
        response = client.get(f"/prompts/{prompt_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == prompt_id
    
    def test_get_prompt_not_found(self, client: TestClient):
        """Test that getting a non-existent prompt returns 404.
        
        NOTE: This test currently FAILS due to Bug #1!
        The API returns 500 instead of 404.
        """
        response = client.get("/prompts/nonexistent-id")
        # This should be 404, but there's a bug...
        assert response.status_code == 404  # Will fail until bug is fixed
    
    def test_delete_prompt(self, client: TestClient, sample_prompt_data):
        """DELETE returns 204 and the prompt is then 404 on GET (404, not 500, after the Bug #1 fix)."""
        # Create a prompt first
        create_response = client.post("/prompts", json=sample_prompt_data)
        prompt_id = create_response.json()["id"]
        
        # Delete it
        response = client.delete(f"/prompts/{prompt_id}")
        assert response.status_code == 204
        
        # Verify it's gone
        get_response = client.get(f"/prompts/{prompt_id}")
        assert get_response.status_code == 404
    
    def test_update_prompt(self, client: TestClient, sample_prompt_data):
        """PUT replaces the fields, moves updated_at forward and leaves created_at alone (Bug #2 fix)."""
        # Create a prompt first
        create_response = client.post("/prompts", json=sample_prompt_data)
        prompt_id = create_response.json()["id"]
        original_updated_at = create_response.json()["updated_at"]
        
        # Update it
        updated_data = {
            "title": "Updated Title",
            "content": "Updated content for the prompt",
            "description": "Updated description"
        }
        
        import time
        time.sleep(0.1)  # Small delay to ensure timestamp would change
        
        response = client.put(f"/prompts/{prompt_id}", json=updated_data)
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        
        # updated_at must move forward on every update (Bug #2)
        assert data["updated_at"] != original_updated_at
        assert data["updated_at"] > original_updated_at
        assert data["created_at"] == create_response.json()["created_at"]

    def test_update_prompt_not_found(self, client: TestClient, sample_prompt_data):
        """PUT on an id that was never created returns 404."""
        response = client.put("/prompts/nonexistent-id", json=sample_prompt_data)
        assert response.status_code == 404
    
    def test_sorting_order(self, client: TestClient):
        """Test that prompts are sorted newest first.
        
        NOTE: This test might fail due to Bug #3!
        """
        import time
        
        # Create prompts with delay
        prompt1 = {"title": "First", "content": "First prompt content"}
        prompt2 = {"title": "Second", "content": "Second prompt content"}
        
        client.post("/prompts", json=prompt1)
        time.sleep(0.1)
        client.post("/prompts", json=prompt2)
        
        response = client.get("/prompts")
        prompts = response.json()["prompts"]
        
        # Newest (Second) should be first
        assert prompts[0]["title"] == "Second"  # Will fail until Bug #3 fixed

    def test_list_prompts_search_matches_title(self, client: TestClient):
        client.post("/prompts", json={"title": "Security review", "content": "Look for issues"})
        client.post("/prompts", json={"title": "Code review", "content": "Something else"})

        response = client.get("/prompts?search=security")
        titles = [p["title"] for p in response.json()["prompts"]]
        assert titles == ["Security review"]

    def test_list_prompts_search_matches_description(self, client: TestClient):
        client.post(
            "/prompts",
            json={"title": "Untitled", "content": "content", "description": "Helps with OWASP audits"},
        )
        response = client.get("/prompts?search=owasp")
        assert response.json()["total"] == 1

    def test_list_prompts_search_no_match_returns_empty(self, client: TestClient, sample_prompt_data):
        client.post("/prompts", json=sample_prompt_data)
        response = client.get("/prompts?search=nonexistent-term-xyz")
        assert response.status_code == 200
        assert response.json() == {"prompts": [], "total": 0}

    def test_list_prompts_collection_and_search_combine(self, client: TestClient, sample_collection_data):
        collection_id = client.post("/collections", json=sample_collection_data).json()["id"]
        client.post(
            "/prompts",
            json={"title": "Security review", "content": "c", "collection_id": collection_id},
        )
        client.post("/prompts", json={"title": "Security review", "content": "c"})  # no collection

        response = client.get(f"/prompts?collection_id={collection_id}&search=security")
        assert response.json()["total"] == 1

    def test_list_prompts_unknown_collection_id_returns_empty_not_error(self, client: TestClient, sample_prompt_data):
        """An unmatched collection_id filter is not a validation error — just no results."""
        client.post("/prompts", json=sample_prompt_data)
        response = client.get("/prompts?collection_id=nonexistent-collection")
        assert response.status_code == 200
        assert response.json() == {"prompts": [], "total": 0}

    def test_create_prompt_missing_title_returns_422(self, client: TestClient):
        response = client.post("/prompts", json={"content": "content only"})
        assert response.status_code == 422

    def test_create_prompt_missing_content_returns_422(self, client: TestClient):
        response = client.post("/prompts", json={"title": "title only"})
        assert response.status_code == 422

    def test_create_prompt_empty_title_returns_422(self, client: TestClient):
        response = client.post("/prompts", json={"title": "", "content": "content"})
        assert response.status_code == 422

    def test_create_prompt_title_too_long_returns_422(self, client: TestClient):
        response = client.post("/prompts", json={"title": "x" * 201, "content": "content"})
        assert response.status_code == 422

    def test_create_prompt_description_too_long_returns_422(self, client: TestClient):
        response = client.post(
            "/prompts", json={"title": "T", "content": "content", "description": "x" * 501}
        )
        assert response.status_code == 422

    def test_create_prompt_unknown_collection_returns_400(self, client: TestClient, sample_prompt_data):
        response = client.post("/prompts", json={**sample_prompt_data, "collection_id": "nonexistent"})
        assert response.status_code == 400
        assert response.json() == {"detail": "Collection not found"}

    def test_create_prompt_with_valid_collection_succeeds(
        self, client: TestClient, sample_prompt_data, sample_collection_data
    ):
        collection_id = client.post("/collections", json=sample_collection_data).json()["id"]
        response = client.post("/prompts", json={**sample_prompt_data, "collection_id": collection_id})
        assert response.status_code == 201
        assert response.json()["collection_id"] == collection_id

    def test_update_prompt_unknown_collection_returns_400(self, client: TestClient, sample_prompt_data):
        prompt_id = client.post("/prompts", json=sample_prompt_data).json()["id"]
        response = client.put(
            f"/prompts/{prompt_id}", json={**sample_prompt_data, "collection_id": "nonexistent"}
        )
        assert response.status_code == 400
        assert response.json() == {"detail": "Collection not found"}

    def test_update_prompt_missing_content_returns_422(self, client: TestClient, sample_prompt_data):
        """PUT requires the full PromptUpdate shape; a missing required field is 422, not silently kept."""
        prompt_id = client.post("/prompts", json=sample_prompt_data).json()["id"]
        response = client.put(f"/prompts/{prompt_id}", json={"title": "Only title"})
        assert response.status_code == 422

    def test_update_prompt_omitted_optional_fields_are_cleared(self, client: TestClient, sample_prompt_data):
        """PUT is a full replace: description isn't resent, so it's cleared rather than kept."""
        prompt_id = client.post("/prompts", json=sample_prompt_data).json()["id"]
        response = client.put(f"/prompts/{prompt_id}", json={"title": "T", "content": "New content"})
        assert response.status_code == 200
        assert response.json()["description"] is None

    def test_update_prompt_preserves_id(self, client: TestClient, sample_prompt_data):
        prompt_id = client.post("/prompts", json=sample_prompt_data).json()["id"]
        response = client.put(f"/prompts/{prompt_id}", json=sample_prompt_data)
        assert response.json()["id"] == prompt_id


class TestPatchPrompt:
    """Tests for PATCH /prompts/{id} (partial updates)."""

    def _create(self, client: TestClient, sample_prompt_data, **extra):
        """Create a prompt through the API and return the response body."""
        return client.post("/prompts", json={**sample_prompt_data, **extra}).json()

    def test_patch_single_field_leaves_others_unchanged(self, client: TestClient, sample_prompt_data):
        """Patching only the title changes the title and updated_at; every other field, the id and created_at are untouched, and the change is persisted."""
        import time
        original = self._create(client, sample_prompt_data)
        time.sleep(0.05)

        response = client.patch(f"/prompts/{original['id']}", json={"title": "Patched Title"})
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Patched Title"
        assert data["content"] == original["content"]
        assert data["description"] == original["description"]
        assert data["collection_id"] == original["collection_id"]
        assert data["id"] == original["id"]
        assert data["created_at"] == original["created_at"]
        assert data["updated_at"] > original["updated_at"]

        # The change is persisted, not just echoed
        assert client.get(f"/prompts/{original['id']}").json()["title"] == "Patched Title"

    def test_patch_multiple_fields(self, client: TestClient, sample_prompt_data):
        """Several fields can be patched in one request without touching the rest."""
        original = self._create(client, sample_prompt_data)
        response = client.patch(
            f"/prompts/{original['id']}", json={"content": "New content", "description": "New description"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "New content"
        assert data["description"] == "New description"
        assert data["title"] == original["title"]

    def test_patch_not_found(self, client: TestClient):
        """PATCH on an id that was never created returns 404."""
        response = client.patch("/prompts/nonexistent-id", json={"title": "x"})
        assert response.status_code == 404

    def test_patch_deleted_prompt_returns_404(self, client: TestClient, sample_prompt_data):
        """A soft-deleted prompt is not patchable; it behaves as if it does not exist."""
        prompt_id = self._create(client, sample_prompt_data)["id"]
        client.delete(f"/prompts/{prompt_id}")
        assert client.patch(f"/prompts/{prompt_id}", json={"title": "x"}).status_code == 404

    def test_patch_null_clears_optional_fields(self, client: TestClient, sample_prompt_data, sample_collection_data):
        """Sending null for description and collection_id clears both while leaving the title alone."""
        collection_id = client.post("/collections", json=sample_collection_data).json()["id"]
        original = self._create(client, sample_prompt_data, collection_id=collection_id)
        assert original["description"] is not None and original["collection_id"] == collection_id

        response = client.patch(
            f"/prompts/{original['id']}", json={"description": None, "collection_id": None}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["description"] is None
        assert data["collection_id"] is None
        assert data["title"] == original["title"]

    def test_patch_null_required_field_returns_400(self, client: TestClient, sample_prompt_data):
        """Sending null for title or content is rejected with 400 naming the field, and the prompt is left exactly as it was."""
        original = self._create(client, sample_prompt_data)

        for field in ("title", "content"):
            response = client.patch(f"/prompts/{original['id']}", json={field: None})
            assert response.status_code == 400, field
            assert field in response.json()["detail"]

        # Nothing was changed by the rejected requests
        current = client.get(f"/prompts/{original['id']}").json()
        assert current["title"] == original["title"]
        assert current["content"] == original["content"]
        assert current["updated_at"] == original["updated_at"]

    def test_patch_invalid_value_returns_422(self, client: TestClient, sample_prompt_data):
        """A value that breaks a field constraint (empty title) is a validation error, 422, like POST and PUT."""
        original = self._create(client, sample_prompt_data)
        response = client.patch(f"/prompts/{original['id']}", json={"title": ""})
        assert response.status_code == 422

    def test_patch_unknown_collection_returns_400(self, client: TestClient, sample_prompt_data):
        """Moving a prompt into a collection that does not exist is rejected with 400."""
        original = self._create(client, sample_prompt_data)
        response = client.patch(f"/prompts/{original['id']}", json={"collection_id": "nonexistent-id"})
        assert response.status_code == 400

    def test_patch_can_move_prompt_to_collection(self, client: TestClient, sample_prompt_data, sample_collection_data):
        """Patching collection_id attaches the prompt to that collection and it shows up in the collection filter."""
        collection_id = client.post("/collections", json=sample_collection_data).json()["id"]
        original = self._create(client, sample_prompt_data)

        response = client.patch(f"/prompts/{original['id']}", json={"collection_id": collection_id})
        assert response.status_code == 200
        assert response.json()["collection_id"] == collection_id
        assert client.get(f"/prompts?collection_id={collection_id}").json()["total"] == 1

    def test_patch_empty_body_changes_nothing_but_timestamp(self, client: TestClient, sample_prompt_data):
        """An empty body is a valid no-op patch that still bumps updated_at."""
        import time
        original = self._create(client, sample_prompt_data)
        time.sleep(0.05)

        response = client.patch(f"/prompts/{original['id']}", json={})
        assert response.status_code == 200
        data = response.json()
        for field in ("title", "content", "description", "collection_id", "created_at"):
            assert data[field] == original[field]
        assert data["updated_at"] > original["updated_at"]

    def test_patch_ignores_server_managed_fields(self, client: TestClient, sample_prompt_data):
        """id, created_at and deleted_on in a PATCH body are ignored rather than applied or rejected."""
        original = self._create(client, sample_prompt_data)
        response = client.patch(
            f"/prompts/{original['id']}",
            json={"id": "forged", "created_at": "2000-01-01T00:00:00", "deleted_on": "2000-01-01T00:00:00"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == original["id"]
        assert data["created_at"] == original["created_at"]
        assert data["deleted_on"] is None

class TestCollections:
    """Tests for collection endpoints."""
    
    def test_create_collection(self, client: TestClient, sample_collection_data):
        response = client.post("/collections", json=sample_collection_data)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == sample_collection_data["name"]
        assert "id" in data
    
    def test_list_collections(self, client: TestClient, sample_collection_data):
        client.post("/collections", json=sample_collection_data)

        response = client.get("/collections")
        assert response.status_code == 200
        data = response.json()
        assert len(data["collections"]) == 1

    def test_list_collections_empty(self, client: TestClient):
        response = client.get("/collections")
        assert response.status_code == 200
        assert response.json() == {"collections": [], "total": 0}

    def test_get_collection_success(self, client: TestClient, sample_collection_data):
        created = client.post("/collections", json=sample_collection_data).json()
        response = client.get(f"/collections/{created['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == created["id"]
        assert data["name"] == sample_collection_data["name"]

    def test_get_collection_not_found(self, client: TestClient):
        response = client.get("/collections/nonexistent-id")
        assert response.status_code == 404
        assert response.json() == {"detail": "Collection not found"}

    def test_create_collection_empty_name_returns_422(self, client: TestClient):
        response = client.post("/collections", json={"name": ""})
        assert response.status_code == 422

    def test_create_collection_name_too_long_returns_422(self, client: TestClient):
        response = client.post("/collections", json={"name": "x" * 101})
        assert response.status_code == 422

    def test_create_collection_description_too_long_returns_422(self, client: TestClient):
        response = client.post("/collections", json={"name": "N", "description": "x" * 501})
        assert response.status_code == 422
    
    def test_delete_collection_not_found(self, client: TestClient):
        """DELETE on a collection id that was never created returns 404."""
        response = client.delete("/collections/nonexistent-id")
        assert response.status_code == 404

    def test_delete_collection_without_prompts(self, client: TestClient, sample_collection_data):
        """A collection with no prompts can be deleted and then disappears from GET by id and from the list."""
        collection_id = client.post("/collections", json=sample_collection_data).json()["id"]

        response = client.delete(f"/collections/{collection_id}")
        assert response.status_code == 204
        assert client.get(f"/collections/{collection_id}").status_code == 404
        assert client.get("/collections").json()["total"] == 0

    def test_delete_collection_with_prompts(self, client: TestClient, sample_collection_data, sample_prompt_data):
        """Deleting a collection soft-deletes the collection and cascades to its prompts (Bug #4)."""
        collection_id = client.post("/collections", json=sample_collection_data).json()["id"]
        prompt_id = client.post(
            "/prompts", json={**sample_prompt_data, "collection_id": collection_id}
        ).json()["id"]

        response = client.delete(f"/collections/{collection_id}")
        assert response.status_code == 204

        # Neither the collection nor its prompt is visible through the API any more
        assert client.get(f"/collections/{collection_id}").status_code == 404
        assert client.get(f"/prompts/{prompt_id}").status_code == 404
        assert client.get("/prompts").json()["total"] == 0
        assert client.get(f"/prompts?collection_id={collection_id}").json()["total"] == 0

        # ...but both records still exist underneath, stamped with the same deletion time,
        # and the prompt keeps its collection_id so the grouping could be restored.
        from app.storage import storage
        collection = storage.get_collection(collection_id, include_deleted=True)
        prompt = storage.get_prompt(prompt_id, include_deleted=True)
        assert collection is not None and collection.deleted_on is not None
        assert prompt is not None and prompt.deleted_on == collection.deleted_on
        assert prompt.collection_id == collection_id

    def test_delete_collection_leaves_other_prompts_alone(self, client: TestClient, sample_prompt_data):
        """Cascade only touches the deleted collection's prompts; prompts in other collections or in none are still listed."""
        doomed_id = client.post("/collections", json={"name": "Doomed"}).json()["id"]
        kept_id = client.post("/collections", json={"name": "Kept"}).json()["id"]
        client.post("/prompts", json={**sample_prompt_data, "title": "In doomed", "collection_id": doomed_id})
        client.post("/prompts", json={**sample_prompt_data, "title": "In kept", "collection_id": kept_id})
        client.post("/prompts", json={**sample_prompt_data, "title": "No collection"})

        client.delete(f"/collections/{doomed_id}")

        titles = {p["title"] for p in client.get("/prompts").json()["prompts"]}
        assert titles == {"In kept", "No collection"}
        assert client.get("/collections").json()["total"] == 1

    def test_delete_collection_twice_returns_404(self, client: TestClient, sample_collection_data):
        """A second DELETE on the same collection returns 404 because the first soft-deleted it."""
        collection_id = client.post("/collections", json=sample_collection_data).json()["id"]
        assert client.delete(f"/collections/{collection_id}").status_code == 204
        assert client.delete(f"/collections/{collection_id}").status_code == 404

    def test_cannot_create_prompt_in_deleted_collection(self, client: TestClient, sample_collection_data, sample_prompt_data):
        """A soft-deleted collection is not a valid target for a new prompt (400)."""
        collection_id = client.post("/collections", json=sample_collection_data).json()["id"]
        client.delete(f"/collections/{collection_id}")

        response = client.post("/prompts", json={**sample_prompt_data, "collection_id": collection_id})
        assert response.status_code == 400


class TestSoftDelete:
    """Soft-delete behaviour shared by prompts and collections."""

    def test_deleted_on_is_null_by_default(self, client: TestClient, sample_prompt_data, sample_collection_data):
        """Newly created prompts and collections come back with deleted_on null."""
        prompt = client.post("/prompts", json=sample_prompt_data).json()
        collection = client.post("/collections", json=sample_collection_data).json()
        assert prompt["deleted_on"] is None
        assert collection["deleted_on"] is None

    def test_delete_prompt_is_soft(self, client: TestClient, sample_prompt_data):
        """DELETE hides the prompt from the API but the record remains, stamped with deleted_on, reachable with include_deleted=True."""
        prompt_id = client.post("/prompts", json=sample_prompt_data).json()["id"]

        assert client.delete(f"/prompts/{prompt_id}").status_code == 204
        assert client.get(f"/prompts/{prompt_id}").status_code == 404
        assert client.get("/prompts").json()["total"] == 0

        from app.storage import storage
        assert storage.get_prompt(prompt_id) is None
        kept = storage.get_prompt(prompt_id, include_deleted=True)
        assert kept is not None and kept.deleted_on is not None

    def test_delete_prompt_twice_returns_404(self, client: TestClient, sample_prompt_data):
        """A second DELETE on the same prompt returns 404."""
        prompt_id = client.post("/prompts", json=sample_prompt_data).json()["id"]
        assert client.delete(f"/prompts/{prompt_id}").status_code == 204
        assert client.delete(f"/prompts/{prompt_id}").status_code == 404

    def test_cannot_update_deleted_prompt(self, client: TestClient, sample_prompt_data):
        """PUT on a soft-deleted prompt returns 404."""
        prompt_id = client.post("/prompts", json=sample_prompt_data).json()["id"]
        client.delete(f"/prompts/{prompt_id}")

        response = client.put(f"/prompts/{prompt_id}", json=sample_prompt_data)
        assert response.status_code == 404

    def test_clients_cannot_set_deleted_on(self, client: TestClient, sample_prompt_data):
        """deleted_on in a POST body is ignored; the created prompt still has deleted_on null."""
        response = client.post("/prompts", json={**sample_prompt_data, "deleted_on": "2026-01-01T00:00:00"})
        assert response.status_code == 201
        assert response.json()["deleted_on"] is None
