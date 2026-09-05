"""FastAPI routes for PromptLab"""

from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
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
    PromptVersion,
    PromptVersionList,
    get_current_time,
)
from app.storage import storage
from app.utils import filter_prompts_by_collection, search_prompts, sort_prompts_by_date

app = FastAPI(
    title="PromptLab API",
    description="AI Prompt Engineering Platform",
    version=__version__
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _snapshot_version_if_changed(
    prompt_id: str,
    existing: Prompt,
    new_title: str,
    new_content: str,
    new_description: Optional[str],
    updated_at: datetime,
) -> None:
    """Create a new prompt version, but only if the editable content actually changed.

    Shared by update_prompt (PUT) and patch_prompt (PATCH): both compute a candidate
    new title/content/description and must snapshot a version only when at least one
    of them differs from the prompt's current stored values (specs/prompt-versions.md,
    US-2/US-3) — a no-op edit must not create version noise.

    Args:
        prompt_id: The id of the prompt being updated.
        existing: The prompt's current stored state, before this update.
        new_title: The candidate new title.
        new_content: The candidate new content.
        new_description: The candidate new description.
        updated_at: The timestamp to record on the new version, if created.
    """
    if (new_title, new_content, new_description) != (existing.title, existing.content, existing.description):
        storage.create_prompt_version(prompt_id, new_title, new_content, new_description, updated_at)


# ============== Health Check ==============

@app.get("/health", response_model=HealthResponse)
def health_check():
    """Report that the service is running.

    Returns:
        A HealthResponse with status "healthy" and the running app version.
    """
    return HealthResponse(status="healthy", version=__version__)


# ============== Prompt Endpoints ==============

@app.get("/prompts", response_model=PromptList)
def list_prompts(
    collection_id: Optional[str] = None,
    search: Optional[str] = None
):
    """List active prompts, optionally filtered, newest first.

    Args:
        collection_id: Query parameter; if given, only prompts with this
            exact `collection_id` are returned.
        search: Query parameter; if given, only prompts whose title or
            description contain this text (case-insensitive) are returned.
            Applied after `collection_id` filtering.

    Returns:
        A PromptList of the matching active prompts, sorted by
        `created_at` descending, along with the count.
    """
    prompts = storage.get_all_prompts()

    # Filter by collection if specified
    if collection_id:
        prompts = filter_prompts_by_collection(prompts, collection_id)

    # Search if query provided
    if search:
        prompts = search_prompts(prompts, search)

    # Sort by date (newest first)
    # Note: There might be an issue with the sorting...
    prompts = sort_prompts_by_date(prompts, descending=True)

    return PromptList(prompts=prompts, total=len(prompts))


@app.get("/prompts/{prompt_id}", response_model=Prompt)
def get_prompt(prompt_id: str):
    """Return a single prompt by id.

    Args:
        prompt_id: Path parameter; the id of the prompt to fetch.

    Returns:
        The matching Prompt.

    Raises:
        HTTPException: 404 if no prompt has that id or the prompt has been
            soft-deleted.
    """
    prompt = storage.get_prompt(prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return prompt


@app.post("/prompts", response_model=Prompt, status_code=201)
def create_prompt(prompt_data: PromptCreate):
    """Create a new prompt.

    Args:
        prompt_data: The title, content, and optional description /
            collection_id for the new prompt.

    Returns:
        The newly created Prompt, with a server-generated id and
        timestamps.

    Raises:
        HTTPException: 400 if `prompt_data.collection_id` is set but no
            active collection has that id.
    """
    # Validate collection exists if provided
    if prompt_data.collection_id:
        collection = storage.get_collection(prompt_data.collection_id)
        if not collection:
            raise HTTPException(status_code=400, detail="Collection not found")

    prompt = Prompt(**prompt_data.model_dump())
    storage.create_prompt(prompt)
    storage.create_prompt_version(
        prompt.id, prompt.title, prompt.content, prompt.description, prompt.created_at
    )
    return prompt


@app.put("/prompts/{prompt_id}", response_model=Prompt)
def update_prompt(prompt_id: str, prompt_data: PromptUpdate):
    """Replace every editable field of a prompt (full update).

    All fields in PromptUpdate are required; a field left out of the body is
    rejected by validation before this function runs, and an optional field
    sent as null becomes null. The id and created_at are preserved and
    updated_at is set to the current time.

    Args:
        prompt_id: Path parameter; the id of the prompt to replace.
        prompt_data: The complete new set of field values.

    Returns:
        The stored Prompt after replacement.

    Raises:
        HTTPException: 404 if no active prompt has that id; 400 if
            prompt_data.collection_id is set but no active collection has
            that id.
    """
    existing = storage.get_prompt(prompt_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Prompt not found")

    # Validate collection if provided
    if prompt_data.collection_id:
        collection = storage.get_collection(prompt_data.collection_id)
        if not collection:
            raise HTTPException(status_code=400, detail="Collection not found")

    updated_prompt = Prompt(
        id=existing.id,
        title=prompt_data.title,
        content=prompt_data.content,
        description=prompt_data.description,
        collection_id=prompt_data.collection_id,
        created_at=existing.created_at,
        updated_at=get_current_time()
    )

    _snapshot_version_if_changed(
        prompt_id, existing, prompt_data.title, prompt_data.content, prompt_data.description,
        updated_prompt.updated_at,
    )

    return storage.update_prompt(prompt_id, updated_prompt)


@app.patch("/prompts/{prompt_id}", response_model=Prompt)
def patch_prompt(prompt_id: str, prompt_data: PromptPatch):
    """Apply a partial update to a prompt.

    Only fields present in the request body are changed. A field that is
    omitted keeps its current value; a field sent as null is cleared, except
    title and content, which must always have a value. The id and created_at
    are preserved and updated_at is set to the current time even if the body
    is empty.

    Args:
        prompt_id: Path parameter; the id of the prompt to update.
        prompt_data: The subset of fields to change. Unset fields are ignored.

    Returns:
        The stored Prompt after the update.

    Raises:
        HTTPException: 404 if no active prompt has that id; 400 if title or
            content is sent as null, or if collection_id is set to an id that
            does not belong to an active collection.
    """
    existing = storage.get_prompt(prompt_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Prompt not found")

    # Only fields present in the request body count — an omitted field is left
    # alone, an explicit null clears it.
    updates = prompt_data.model_dump(exclude_unset=True)

    # title and content are required on a prompt, so they can be changed but not cleared
    for field in ("title", "content"):
        if field in updates and updates[field] is None:
            raise HTTPException(status_code=400, detail=f"{field} cannot be null")

    # Validate collection if provided
    if updates.get("collection_id"):
        collection = storage.get_collection(updates["collection_id"])
        if not collection:
            raise HTTPException(status_code=400, detail="Collection not found")

    new_title = updates.get("title", existing.title)
    new_content = updates.get("content", existing.content)
    new_description = updates.get("description", existing.description)

    updated_prompt = Prompt(
        id=existing.id,
        title=new_title,
        content=new_content,
        description=new_description,
        collection_id=updates.get("collection_id", existing.collection_id),
        created_at=existing.created_at,
        updated_at=get_current_time()
    )

    _snapshot_version_if_changed(
        prompt_id, existing, new_title, new_content, new_description, updated_prompt.updated_at
    )

    return storage.update_prompt(prompt_id, updated_prompt)


@app.delete("/prompts/{prompt_id}", status_code=204)
def delete_prompt(prompt_id: str):
    """Soft-delete a prompt.

    Args:
        prompt_id: Path parameter; the id of the prompt to delete.

    Returns:
        None. The response is an empty 204.

    Raises:
        HTTPException: 404 if no active prompt has that id, including one
            that has already been deleted.
    """
    if not storage.delete_prompt(prompt_id):
        raise HTTPException(status_code=404, detail="Prompt not found")
    return None


# ============== Prompt Version Endpoints ==============

@app.get("/prompts/{prompt_id}/versions", response_model=PromptVersionList)
def list_prompt_versions(prompt_id: str):
    """List a prompt's saved versions, newest first.

    Args:
        prompt_id: Path parameter; the id of the prompt whose versions to list.

    Returns:
        A PromptVersionList of the prompt's versions, ordered by
        version_number descending, and a count.

    Raises:
        HTTPException: 404 if no prompt has that id or the prompt has been
            soft-deleted.
    """
    if not storage.get_prompt(prompt_id):
        raise HTTPException(status_code=404, detail="Prompt not found")

    versions = sorted(storage.get_prompt_versions(prompt_id), key=lambda v: v.version_number, reverse=True)
    return PromptVersionList(versions=versions, total=len(versions))


@app.get("/prompts/{prompt_id}/versions/{version_number}", response_model=PromptVersion)
def get_prompt_version(prompt_id: str, version_number: int):
    """Return one specific version of a prompt.

    Args:
        prompt_id: Path parameter; the id of the prompt.
        version_number: Path parameter; the version to fetch.

    Returns:
        The matching PromptVersion.

    Raises:
        HTTPException: 404 if no prompt has that id or it has been
            soft-deleted; 404 if the prompt exists but has no such version.
    """
    if not storage.get_prompt(prompt_id):
        raise HTTPException(status_code=404, detail="Prompt not found")

    version = storage.get_prompt_version(prompt_id, version_number)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    return version


@app.post("/prompts/{prompt_id}/versions/{version_number}/restore", response_model=Prompt)
def restore_prompt_version(prompt_id: str, version_number: int):
    """Make a past version the prompt's current content again.

    Sets the prompt's title/content/description to the given version's values
    and always appends a new version with that same content — even when
    restoring the prompt's own current version, this is never a no-op.
    collection_id is untouched: restoring content never moves a prompt
    between collections.

    Args:
        prompt_id: Path parameter; the id of the prompt to restore.
        version_number: Path parameter; the version to restore.

    Returns:
        The updated Prompt.

    Raises:
        HTTPException: 404 if no prompt has that id or it has been
            soft-deleted; 404 if the prompt exists but has no such version.
    """
    existing = storage.get_prompt(prompt_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Prompt not found")

    version = storage.get_prompt_version(prompt_id, version_number)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    restored_at = get_current_time()
    updated_prompt = Prompt(
        id=existing.id,
        title=version.title,
        content=version.content,
        description=version.description,
        collection_id=existing.collection_id,
        created_at=existing.created_at,
        updated_at=restored_at,
    )
    storage.create_prompt_version(prompt_id, version.title, version.content, version.description, restored_at)
    return storage.update_prompt(prompt_id, updated_prompt)


# ============== Collection Endpoints ==============

@app.get("/collections", response_model=CollectionList)
def list_collections():
    """List every active collection.

    Returns:
        A CollectionList of the active collections and the count.
    """
    collections = storage.get_all_collections()
    return CollectionList(collections=collections, total=len(collections))


@app.get("/collections/{collection_id}", response_model=Collection)
def get_collection(collection_id: str):
    """Return a single collection by id.

    Args:
        collection_id: Path parameter; the id of the collection to fetch.

    Returns:
        The matching Collection.

    Raises:
        HTTPException: 404 if no collection has that id or it has been
            soft-deleted.
    """
    collection = storage.get_collection(collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection


@app.post("/collections", response_model=Collection, status_code=201)
def create_collection(collection_data: CollectionCreate):
    """Create a new collection.

    Args:
        collection_data: The name and optional description for the new
            collection.

    Returns:
        The newly created Collection, with a server-generated id and
        timestamp.
    """
    collection = Collection(**collection_data.model_dump())
    return storage.create_collection(collection)


@app.delete("/collections/{collection_id}", status_code=204)
def delete_collection(collection_id: str):
    """Soft-delete a collection and every active prompt in it.

    Args:
        collection_id: Path parameter; the id of the collection to delete.

    Returns:
        None. The response is an empty 204.

    Raises:
        HTTPException: 404 if no active collection has that id, including a
            collection that has already been deleted.
    """
    # Soft delete with cascade (Bug #4). Deleting a collection is more destructive
    # than deleting a single prompt, so neither the collection nor its prompts are
    # removed: storage stamps deleted_on on all of them and reads filter them out.
    # The records, and each prompt's collection_id, survive so the collection could
    # be restored or its prompts moved elsewhere with a small amount of extra logic.
    if not storage.delete_collection(collection_id):
        raise HTTPException(status_code=404, detail="Collection not found")
    return None
