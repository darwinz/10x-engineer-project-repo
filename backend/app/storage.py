"""In-memory storage for PromptLab

This module provides simple in-memory storage for prompts and collections.
In a production environment, this would be replaced with a database.
"""

from datetime import datetime
from typing import Dict, List, Optional
from app.models import Prompt, Collection, get_current_time


class Storage:
    """In-memory store for prompts and collections, keyed by id.

    Deletion is soft: records are stamped with deleted_on and hidden from
    every read, rather than removed. Lookups return the stored objects
    themselves, not copies. Everything is lost when the process exits.
    """

    def __init__(self):
        """Initialize empty prompt and collection stores."""
        self._prompts: Dict[str, Prompt] = {}
        self._collections: Dict[str, Collection] = {}

    # ============== Prompt Operations ==============

    def create_prompt(self, prompt: Prompt) -> Prompt:
        """Store a new prompt, keyed by its id.

        Any existing prompt with the same id is overwritten.

        Args:
            prompt: The Prompt object to store.

        Returns:
            The same Prompt object that was passed in.
        """
        self._prompts[prompt.id] = prompt
        return prompt

    def get_prompt(self, prompt_id: str, include_deleted: bool = False) -> Optional[Prompt]:
        """Look up a prompt by id.

        Args:
            prompt_id: The id of the prompt.
            include_deleted: If True, a soft-deleted prompt is returned as
                well. Defaults to False, which hides deleted prompts.

        Returns:
            The stored Prompt object itself (not a copy), or None if there is
            no prompt with that id or it is soft-deleted and include_deleted
            is False.
        """
        prompt = self._prompts.get(prompt_id)
        if prompt is None or (prompt.deleted_on is not None and not include_deleted):
            return None
        return prompt
    
    def get_all_prompts(self) -> List[Prompt]:
        """Return every prompt that has not been soft-deleted.

        Returns:
            A new list of the active Prompt objects, in insertion order.
        """
        return [p for p in self._prompts.values() if p.deleted_on is None]
    
    def update_prompt(self, prompt_id: str, prompt: Prompt) -> Optional[Prompt]:
        """Replace the stored prompt with the given id.

        Args:
            prompt_id: The id of the prompt to replace.
            prompt: The new Prompt object to store under that id.

        Returns:
            The stored prompt (the same object that was passed in), or None
            if there is no active prompt with that id.
        """
        if self.get_prompt(prompt_id) is None:
            return None
        self._prompts[prompt_id] = prompt
        return prompt
    
    def delete_prompt(self, prompt_id: str, deleted_on: Optional[datetime] = None) -> bool:
        """Soft-delete a prompt by stamping its deleted_on field.

        The record stays in storage and can still be read with
        get_prompt(..., include_deleted=True).

        Args:
            prompt_id: The id of the prompt to delete.
            deleted_on: The deletion timestamp to record. Defaults to the
                current time. delete_collection passes its own timestamp so
                a collection and its prompts share one value.

        Returns:
            True if an active prompt was found and marked deleted; False if
            there is no prompt with that id or it was already deleted.
        """
        prompt = self.get_prompt(prompt_id)
        if prompt is None:
            return False
        prompt.deleted_on = deleted_on or get_current_time()
        return True
    
    # ============== Collection Operations ==============
    
    def create_collection(self, collection: Collection) -> Collection:
        """Store a new collection, keyed by its id.

        Any existing collection with the same id is overwritten.

        Args:
            collection: The Collection object to store.

        Returns:
            The same Collection object that was passed in.
        """
        self._collections[collection.id] = collection
        return collection

    def get_collection(self, collection_id: str, include_deleted: bool = False) -> Optional[Collection]:
        """Look up a collection by id.

        Args:
            collection_id: The id of the collection.
            include_deleted: If True, a soft-deleted collection is returned
                as well. Defaults to False, which hides deleted collections.

        Returns:
            The stored Collection object itself (not a copy), or None if
            there is no collection with that id or it is soft-deleted and
            include_deleted is False.
        """
        collection = self._collections.get(collection_id)
        if collection is None or (collection.deleted_on is not None and not include_deleted):
            return None
        return collection
    
    def get_all_collections(self) -> List[Collection]:
        """Return every collection that has not been soft-deleted.

        Returns:
            A new list of the active Collection objects, in insertion order.
        """
        return [c for c in self._collections.values() if c.deleted_on is None]
    
    def delete_collection(self, collection_id: str) -> bool:
        """Soft-delete a collection and cascade to its active prompts.

        The collection and each of its prompts receive the same deleted_on
        timestamp. Prompts keep their collection_id so the grouping survives
        and could be restored.

        Args:
            collection_id: The id of the collection to delete.

        Returns:
            True if an active collection was found and marked deleted; False
            if there is no collection with that id or it was already deleted.
        """
        collection = self.get_collection(collection_id)
        if collection is None:
            return False
        deleted_on = get_current_time()
        collection.deleted_on = deleted_on
        # Cascade: soft-delete the collection's active prompts with the same timestamp,
        # leaving collection_id in place so the grouping can be restored later.
        for prompt in self.get_prompts_by_collection(collection_id):
            self.delete_prompt(prompt.id, deleted_on)
        return True
    
    def get_prompts_by_collection(self, collection_id: str) -> List[Prompt]:
        """Return the active prompts whose collection_id matches.

        Args:
            collection_id: The collection id to match exactly.

        Returns:
            A new list of the matching Prompt objects that have not been
            soft-deleted. Empty if the collection has no prompts or does not
            exist; the collection itself is not checked.
        """
        return [
            p for p in self._prompts.values()
            if p.collection_id == collection_id and p.deleted_on is None
        ]
    
    # ============== Utility ==============

    def clear(self):
        """Remove every prompt and collection, active or soft-deleted.

        Intended for test isolation; there is no equivalent API endpoint.
        """
        self._prompts.clear()
        self._collections.clear()


# Global storage instance
storage = Storage()
