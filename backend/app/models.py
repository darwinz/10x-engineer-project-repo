"""Pydantic models for PromptLab"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from uuid import uuid4


def generate_id() -> str:
    return str(uuid4())


def get_current_time() -> datetime:
    return datetime.utcnow()


# ============== Prompt Models ==============

class PromptBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    description: Optional[str] = Field(None, max_length=500)
    collection_id: Optional[str] = None


class PromptCreate(PromptBase):
    pass


class PromptUpdate(PromptBase):
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
        from_attributes = True


# ============== Collection Models ==============

class CollectionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class CollectionCreate(CollectionBase):
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
        from_attributes = True


# ============== Response Models ==============

class PromptList(BaseModel):
    prompts: List[Prompt]
    total: int


class CollectionList(BaseModel):
    collections: List[Collection]
    total: int


class HealthResponse(BaseModel):
    status: str
    version: str
