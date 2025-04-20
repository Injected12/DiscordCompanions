"""
In-memory database implementation for D10 Discord Bot
"""
import uuid
import logging
import datetime
import copy
from typing import Dict, List, Any, Optional

# Set up logging
logger = logging.getLogger('d10-bot')

class MemoryDatabase:
    """
    In-memory database manager for D10 Discord Bot
    """
    def __init__(self):
        """Initialize the in-memory database"""
        self.collections = {
            'tickets': [],
            'welcome': [],
            'status': [],
            'roles': [],
            'voice_channels': [],
            'temp_voice_channels': [],
            'reports': [],
            'giveaways': [],
            'vouches': [],
            'slot_channels': []
        }
        logger.info("In-memory database initialized")

    def _setup_database(self) -> None:
        """
        No setup needed for in-memory database
        """
        pass

    def get(self, collection: str, filter_dict: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Get items from a collection with optional filtering
        """
        try:
            if collection not in self.collections:
                self.collections[collection] = []
                
            # Return all items if no filter
            if not filter_dict:
                return copy.deepcopy(self.collections.get(collection, []))
            
            # Filter the items
            results = []
            for item in self.collections.get(collection, []):
                match = True
                for key, value in filter_dict.items():
                    if key not in item or item[key] != value:
                        match = False
                        break
                if match:
                    results.append(copy.deepcopy(item))
            
            return results
                
        except Exception as e:
            logger.error(f"In-memory database get error ({collection}): {e}", exc_info=True)
            return []

    def get_one(self, collection: str, filter_dict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Get a single item from a collection with filtering
        """
        try:
            if collection not in self.collections:
                self.collections[collection] = []
                
            # Filter the items
            for item in self.collections.get(collection, []):
                match = True
                for key, value in filter_dict.items():
                    if key not in item or item[key] != value:
                        match = False
                        break
                if match:
                    return copy.deepcopy(item)
            
            return None
                
        except Exception as e:
            logger.error(f"In-memory database get_one error ({collection}): {e}", exc_info=True)
            return None

    def insert(self, collection: str, data: Dict[str, Any]) -> str:
        """
        Insert a new item into a collection
        """
        try:
            if collection not in self.collections:
                self.collections[collection] = []
            
            # Create a deep copy to avoid modifying the original
            item_data = copy.deepcopy(data)
            
            # Ensure we have an ID
            if 'id' not in item_data:
                item_data['id'] = str(uuid.uuid4())
            
            # Add the item to the collection
            self.collections[collection].append(item_data)
            
            return item_data['id']
                
        except Exception as e:
            logger.error(f"In-memory database insert error ({collection}): {e}", exc_info=True)
            raise

    def update(self, collection: str, id_value: str, data: Dict[str, Any]) -> bool:
        """
        Update an existing item in a collection
        """
        try:
            if collection not in self.collections:
                return False
            
            # Create a deep copy to avoid modifying the original
            update_data = copy.deepcopy(data)
            
            # Find the item by ID
            for i, item in enumerate(self.collections[collection]):
                if item.get('id') == id_value:
                    # Update all fields except ID
                    for key, value in update_data.items():
                        if key != 'id':
                            item[key] = value
                    return True
            
            return False
                
        except Exception as e:
            logger.error(f"In-memory database update error ({collection}): {e}", exc_info=True)
            return False

    def delete(self, collection: str, id_value: str) -> bool:
        """
        Delete an item from a collection
        """
        try:
            if collection not in self.collections:
                return False
            
            # Find the item by ID
            for i, item in enumerate(self.collections[collection]):
                if item.get('id') == id_value:
                    del self.collections[collection][i]
                    return True
            
            return False
                
        except Exception as e:
            logger.error(f"In-memory database delete error ({collection}): {e}", exc_info=True)
            return False

    def delete_many(self, collection: str, filter_dict: Dict[str, Any]) -> int:
        """
        Delete multiple items from a collection with filtering
        """
        try:
            if collection not in self.collections:
                return 0
            
            # Find items to delete
            items_to_delete = []
            for i, item in enumerate(self.collections[collection]):
                match = True
                for key, value in filter_dict.items():
                    if key not in item or item[key] != value:
                        match = False
                        break
                if match:
                    items_to_delete.append(i)
            
            # Delete the items (in reverse order to avoid index issues)
            items_to_delete.sort(reverse=True)
            for i in items_to_delete:
                del self.collections[collection][i]
            
            return len(items_to_delete)
                
        except Exception as e:
            logger.error(f"In-memory database delete_many error ({collection}): {e}", exc_info=True)
            return 0