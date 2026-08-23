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
    
    def test_get_collection_not_found(self, client: TestClient):
        response = client.get("/collections/nonexistent-id")
        assert response.status_code == 404
    
    def test_delete_collection_not_found(self, client: TestClient):
        response = client.delete("/collections/nonexistent-id")
        assert response.status_code == 404

    def test_delete_collection_without_prompts(self, client: TestClient, sample_collection_data):
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
        collection_id = client.post("/collections", json=sample_collection_data).json()["id"]
        assert client.delete(f"/collections/{collection_id}").status_code == 204
        assert client.delete(f"/collections/{collection_id}").status_code == 404

    def test_cannot_create_prompt_in_deleted_collection(self, client: TestClient, sample_collection_data, sample_prompt_data):
        collection_id = client.post("/collections", json=sample_collection_data).json()["id"]
        client.delete(f"/collections/{collection_id}")

        response = client.post("/prompts", json={**sample_prompt_data, "collection_id": collection_id})
        assert response.status_code == 400


class TestSoftDelete:
    """Soft-delete behaviour shared by prompts and collections."""

    def test_deleted_on_is_null_by_default(self, client: TestClient, sample_prompt_data, sample_collection_data):
        prompt = client.post("/prompts", json=sample_prompt_data).json()
        collection = client.post("/collections", json=sample_collection_data).json()
        assert prompt["deleted_on"] is None
        assert collection["deleted_on"] is None

    def test_delete_prompt_is_soft(self, client: TestClient, sample_prompt_data):
        prompt_id = client.post("/prompts", json=sample_prompt_data).json()["id"]

        assert client.delete(f"/prompts/{prompt_id}").status_code == 204
        assert client.get(f"/prompts/{prompt_id}").status_code == 404
        assert client.get("/prompts").json()["total"] == 0

        from app.storage import storage
        assert storage.get_prompt(prompt_id) is None
        kept = storage.get_prompt(prompt_id, include_deleted=True)
        assert kept is not None and kept.deleted_on is not None

    def test_delete_prompt_twice_returns_404(self, client: TestClient, sample_prompt_data):
        prompt_id = client.post("/prompts", json=sample_prompt_data).json()["id"]
        assert client.delete(f"/prompts/{prompt_id}").status_code == 204
        assert client.delete(f"/prompts/{prompt_id}").status_code == 404

    def test_cannot_update_deleted_prompt(self, client: TestClient, sample_prompt_data):
        prompt_id = client.post("/prompts", json=sample_prompt_data).json()["id"]
        client.delete(f"/prompts/{prompt_id}")

        response = client.put(f"/prompts/{prompt_id}", json=sample_prompt_data)
        assert response.status_code == 404

    def test_clients_cannot_set_deleted_on(self, client: TestClient, sample_prompt_data):
        response = client.post("/prompts", json={**sample_prompt_data, "deleted_on": "2026-01-01T00:00:00"})
        assert response.status_code == 201
        assert response.json()["deleted_on"] is None
