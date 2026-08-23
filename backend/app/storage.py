"""In-memory storage for PromptLab

This module provides simple in-memory storage for prompts and collections.
In a production environment, this would be replaced with a database.
"""

from datetime import datetime
from typing import Dict, List, Optional
from app.models import Prompt, Collection, get_current_time


class Storage:
    def __init__(self):
        self._prompts: Dict[str, Prompt] = {}
        self._collections: Dict[str, Collection] = {}
    
    # ============== Prompt Operations ==============
    
    def create_prompt(self, prompt: Prompt) -> Prompt:
        self._prompts[prompt.id] = prompt
        return prompt
    
    def get_prompt(self, prompt_id: str, include_deleted: bool = False) -> Optional[Prompt]:
        prompt = self._prompts.get(prompt_id)
        if prompt is None or (prompt.deleted_on is not None and not include_deleted):
            return None
        return prompt
    
    def get_all_prompts(self) -> List[Prompt]:
        return [p for p in self._prompts.values() if p.deleted_on is None]
    
    def update_prompt(self, prompt_id: str, prompt: Prompt) -> Optional[Prompt]:
        if self.get_prompt(prompt_id) is None:
            return None
        self._prompts[prompt_id] = prompt
        return prompt
    
    def delete_prompt(self, prompt_id: str, deleted_on: Optional[datetime] = None) -> bool:
        prompt = self.get_prompt(prompt_id)
        if prompt is None:
            return False
        prompt.deleted_on = deleted_on or get_current_time()
        return True
    
    # ============== Collection Operations ==============
    
    def create_collection(self, collection: Collection) -> Collection:
        self._collections[collection.id] = collection
        return collection
    
    def get_collection(self, collection_id: str, include_deleted: bool = False) -> Optional[Collection]:
        collection = self._collections.get(collection_id)
        if collection is None or (collection.deleted_on is not None and not include_deleted):
            return None
        return collection
    
    def get_all_collections(self) -> List[Collection]:
        return [c for c in self._collections.values() if c.deleted_on is None]
    
    def delete_collection(self, collection_id: str) -> bool:
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
        return [
            p for p in self._prompts.values()
            if p.collection_id == collection_id and p.deleted_on is None
        ]
    
    # ============== Utility ==============
    
    def clear(self):
        self._prompts.clear()
        self._collections.clear()


# Global storage instance
storage = Storage()
