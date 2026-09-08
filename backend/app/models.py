"""Pydantic models for PromptLab"""

from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def generate_id() -> str:
    """Generate a new unique identifier for a prompt or collection.

    Returns:
        A random uuid4 value rendered as a string.
    """
    return str(uuid4())


def get_current_time() -> datetime:
    """Return the current time for timestamping records.

    Returns:
        A naive (timezone-unaware) UTC datetime.
    """
    return datetime.utcnow()


# ============== Prompt Models ==============

class PromptBase(BaseModel):
    """Fields common to every prompt request body.

    Attributes:
        title: Prompt title, 1-200 characters.
        content: The template text, at least 1 character. May contain
            `{{variable}}` placeholders.
        description: Optional description, up to 500 characters.
        collection_id: Id of the collection this prompt belongs to, or
            None if it is not grouped into a collection.
    """
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    description: Optional[str] = Field(None, max_length=500)
    collection_id: Optional[str] = None


class PromptCreate(PromptBase):
    """Request body for POST /prompts. Same fields as PromptBase."""
    pass


class PromptUpdate(PromptBase):
    """Request body for PUT /prompts/{id}.

    All fields inherited from PromptBase are required, so a PUT always
    replaces the full set of editable values on the target prompt.
    """
    pass


class PromptPatch(BaseModel):
    """Request body for PATCH /prompts/{id}.

    Every field is optional so a client can send only what it wants to
    change. When a value is given it must satisfy the same constraints as
    PromptBase. Whether a field was sent at all is recovered with
    model_dump(exclude_unset=True), which is how the handler tells an omitted
    field from one explicitly set to null.

    Attributes:
        title: New title, 1-200 characters. Cannot be cleared to null.
        content: New template text, at least 1 character. Cannot be cleared
            to null.
        description: New description up to 500 characters, or null to clear.
        collection_id: Id of an existing collection to move the prompt into,
            or null to remove it from its collection.
    """
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = Field(None, max_length=500)
    collection_id: Optional[str] = None


class Prompt(PromptBase):
    """A stored prompt, and the response body for every prompt endpoint.

    Attributes:
        id: Server-generated uuid4 string.
        created_at: Naive UTC time the prompt was created.
        updated_at: Naive UTC time of the last PUT or PATCH; equals
            created_at until then.
        deleted_on: Naive UTC time the prompt was soft-deleted, or None
            while it is active. Never settable by clients.
    """
    id: str = Field(default_factory=generate_id)
    created_at: datetime = Field(default_factory=get_current_time)
    updated_at: datetime = Field(default_factory=get_current_time)
    deleted_on: Optional[datetime] = None

    class Config:
        """Allow building a Prompt from attribute access, not just a dict."""
        from_attributes = True


# ============== Collection Models ==============

class CollectionBase(BaseModel):
    """Fields common to every collection request body.

    Attributes:
        name: Collection name, 1-100 characters.
        description: Optional description, up to 500 characters.
    """
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class CollectionCreate(CollectionBase):
    """Request body for POST /collections. Same fields as CollectionBase."""
    pass


class Collection(CollectionBase):
    """A stored collection, and the response body for every collection endpoint.

    Attributes:
        id: Server-generated uuid4 string.
        created_at: Naive UTC time the collection was created.
        deleted_on: Naive UTC time the collection was soft-deleted, or None
            while it is active. Never settable by clients.
    """
    id: str = Field(default_factory=generate_id)
    created_at: datetime = Field(default_factory=get_current_time)
    deleted_on: Optional[datetime] = None

    class Config:
        """Allow building a Collection from attribute access, not just a dict."""
        from_attributes = True


# ============== Prompt Version Models ==============

class PromptVersion(BaseModel):
    """An immutable snapshot of a prompt's editable content at one point in time.

    Attributes:
        id: Server-generated uuid4 string, unique across all versions.
        prompt_id: The id of the Prompt this version belongs to.
        version_number: 1-based, increasing per prompt. 1 is always the
            state at creation.
        title: The prompt's title at this version.
        content: The prompt's template text at this version.
        description: The prompt's description at this version, or None.
        created_at: When this version was captured.
    """
    id: str = Field(default_factory=generate_id)
    prompt_id: str
    version_number: int
    title: str
    content: str
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=get_current_time)


class PromptVersionList(BaseModel):
    """Response body for GET /prompts/{id}/versions.

    Attributes:
        versions: The prompt's versions.
        total: The number of versions in `versions`.
    """
    versions: List[PromptVersion]
    total: int


# ============== Response Models ==============

class PromptList(BaseModel):
    """Response body for GET /prompts.

    Attributes:
        prompts: The matching prompts, in the order returned by the endpoint.
        total: The number of prompts in `prompts`.
    """
    prompts: List[Prompt]
    total: int


class CollectionList(BaseModel):
    """Response body for GET /collections.

    Attributes:
        collections: The active collections, in the order returned by the
            endpoint.
        total: The number of collections in `collections`.
    """
    collections: List[Collection]
    total: int


class HealthResponse(BaseModel):
    """Response body for GET /health.

    Attributes:
        status: Literal "healthy" when the service is up.
        version: The running application's version string.
    """
    status: str
    version: str
