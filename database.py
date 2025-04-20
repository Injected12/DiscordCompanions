"""
Database implementation for D10 Discord Bot using Replit's built-in database
"""

import os
from replit import db
import datetime
import json
import logging
import uuid

logger = logging.getLogger('d10-bot')

class Database:
    def __init__(self):
        """Initialize database connection"""
        self._setup_database()

    def _setup_database(self):
        """Setup initial database tables and structure"""
        try:
            # Initialize collections if they don't exist
            collections = ['reports', 'moderation', 'config', 'tickets', 'giveaways', 'welcome', 'status_tracking', 'slot_channels', 'voice_channels', 'vouches']
            for collection in collections:
                if collection not in db.keys():
                    db[collection] = {}
            logger.info("Database setup complete")
        except Exception as e:
            logger.error(f"Database setup error: {e}", exc_info=True)
            raise

    def insert(self, collection: str, data: dict) -> str:
        """Insert a document into a collection"""
        try:
            if 'id' not in data:
                data['id'] = str(uuid.uuid4())

            # Handle timestamp conversions
            for key, value in data.items():
                if key.endswith('_at') and isinstance(value, (int, float)):
                    data[key] = str(datetime.datetime.fromtimestamp(value))

                # Handle JSON data
                if isinstance(value, (dict, list)) and key in ['answers', 'winner_ids']:
                    data[key] = json.dumps(value)

            collection_data = db[collection]
            collection_data[data['id']] = data
            db[collection] = collection_data

            return data['id']
        except Exception as e:
            logger.error(f"Error inserting document: {e}", exc_info=True)
            raise

    def get_one(self, collection: str, query: dict) -> dict:
        """Get one document from a collection"""
        try:
            collection_data = db[collection]
            for doc in collection_data.values():
                matches = all(doc.get(k) == v for k, v in query.items())
                if matches:
                    return doc
            return None
        except Exception as e:
            logger.error(f"Error getting document: {e}", exc_info=True)
            raise

    def update(self, collection: str, doc_id: str, data: dict) -> bool:
        """Update a document in a collection"""
        try:
            collection_data = db[collection]
            if doc_id in collection_data:
                collection_data[doc_id] = data
                db[collection] = collection_data
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating document: {e}", exc_info=True)
            raise

    def delete(self, collection: str, doc_id: str) -> bool:
        """Delete a document from a collection"""
        try:
            collection_data = db[collection]
            if doc_id in collection_data:
                del collection_data[doc_id]
                db[collection] = collection_data
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting document: {e}", exc_info=True)
            raise

    def get(self, collection: str, filter_dict: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Get items from a collection with optional filtering"""
        try:
            collection_data = db[collection]
            if not filter_dict:
                return list(collection_data.values())
            else:
                results = []
                for doc in collection_data.values():
                    matches = all(doc.get(k) == v for k, v in filter_dict.items())
                    if matches:
                        results.append(doc)
                return results
        except Exception as e:
            logger.error(f"Database get error ({collection}): {e}", exc_info=True)
            return []

    def delete_many(self, collection: str, filter_dict: Dict[str, Any]) -> int:
        """Delete multiple items from a collection with filtering"""
        try:
            deleted_count = 0
            collection_data = db[collection]
            keys_to_delete = []
            for key, value in collection_data.items():
                matches = all(value.get(k) == v for k, v in filter_dict.items())
                if matches:
                    keys_to_delete.append(key)

            for key in keys_to_delete:
                del collection_data[key]
                deleted_count += 1
            db[collection] = collection_data
            return deleted_count
        except Exception as e:
            logger.error(f"Database delete_many error ({collection}): {e}", exc_info=True)
            return 0