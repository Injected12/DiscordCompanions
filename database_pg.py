"""
PostgreSQL Database implementation for D10 Discord Bot for Linux environments
"""

import os
import datetime
import json
import logging
import uuid
import psycopg2
import psycopg2.extras
from typing import Dict, List, Any, Optional

logger = logging.getLogger('d10-bot')

class Database:
    """
    PostgreSQL database manager for D10 Discord Bot
    """
    def __init__(self):
        """Initialize database connection"""
        self.conn = None
        self._connect()
        self._setup_database()

    def _get_connection_params(self) -> Dict[str, Any]:
        """
        Get database connection parameters from environment variables
        """
        # Check if we have a full DATABASE_URL (common in cloud environments)
        database_url = os.getenv('DATABASE_URL')
        if database_url:
            # For Neon.tech and similar cloud PostgreSQL providers that use SSL
            return {
                'dsn': database_url,
                'sslmode': 'require'
            }
        else:
            # Fallback to individual parameters for local development
            return {
                'dbname': os.getenv('PGDATABASE', 'discord_bot'),
                'user': os.getenv('PGUSER', 'postgres'),
                'password': os.getenv('PGPASSWORD', ''),
                'host': os.getenv('PGHOST', 'localhost'),
                'port': os.getenv('PGPORT', '5432')
            }

    def _connect(self):
        """
        Create a new database connection
        """
        try:
            if self.conn is None or self.conn.closed:
                params = self._get_connection_params()
                self.conn = psycopg2.connect(**params)
                self.conn.autocommit = True
                logger.info("Connected to PostgreSQL database")
        except Exception as e:
            logger.error(f"Database connection error: {e}", exc_info=True)
            raise

    def _setup_database(self) -> None:
        """
        Set up database tables
        """
        try:
            self._connect()
            with self.conn.cursor() as cur:
                # Create tables for collections
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS reports (
                        id VARCHAR(36) PRIMARY KEY,
                        guild_id BIGINT,
                        reporter_id BIGINT,
                        target_id BIGINT,
                        reason TEXT,
                        timestamp TIMESTAMP,
                        status VARCHAR(20),
                        reviewer_id BIGINT,
                        reviewed_at TIMESTAMP,
                        review_note TEXT,
                        data JSONB
                    )
                """)
                
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS moderation (
                        id VARCHAR(36) PRIMARY KEY,
                        guild_id BIGINT,
                        user_id BIGINT,
                        moderator_id BIGINT,
                        action VARCHAR(20),
                        reason TEXT,
                        timestamp TIMESTAMP,
                        expires_at TIMESTAMP,
                        active BOOLEAN,
                        data JSONB
                    )
                """)
                
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS config (
                        id VARCHAR(36) PRIMARY KEY,
                        guild_id BIGINT,
                        key VARCHAR(255),
                        value JSONB,
                        updated_at TIMESTAMP
                    )
                """)
                
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS tickets (
                        id VARCHAR(36) PRIMARY KEY,
                        guild_id BIGINT,
                        channel_id BIGINT,
                        user_id BIGINT,
                        created_at TIMESTAMP,
                        closed_at TIMESTAMP,
                        closed_by BIGINT,
                        closed_reason TEXT,
                        active BOOLEAN,
                        data JSONB
                    )
                """)
                
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS giveaways (
                        id VARCHAR(36) PRIMARY KEY,
                        guild_id BIGINT,
                        channel_id BIGINT,
                        message_id BIGINT,
                        creator_id BIGINT,
                        prize TEXT,
                        winners_count INTEGER,
                        created_at TIMESTAMP,
                        ends_at TIMESTAMP,
                        ended BOOLEAN,
                        winner_ids JSONB,
                        participants JSONB,
                        data JSONB
                    )
                """)
                
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS welcome (
                        id VARCHAR(36) PRIMARY KEY,
                        guild_id BIGINT,
                        channel_id BIGINT,
                        message TEXT,
                        enabled BOOLEAN,
                        created_by BIGINT,
                        created_at TIMESTAMP,
                        updated_at TIMESTAMP,
                        data JSONB
                    )
                """)
                
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS status_tracking (
                        id VARCHAR(36) PRIMARY KEY,
                        guild_id BIGINT,
                        user_id BIGINT,
                        status TEXT,
                        first_detected_at TIMESTAMP,
                        last_updated_at TIMESTAMP,
                        streak_days INTEGER,
                        data JSONB
                    )
                """)
                
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS slot_channels (
                        id VARCHAR(36) PRIMARY KEY,
                        guild_id BIGINT,
                        channel_id BIGINT,
                        user_id BIGINT,
                        category_id BIGINT,
                        created_at TIMESTAMP,
                        expires_at TIMESTAMP,
                        closed_at TIMESTAMP,
                        closed_reason TEXT,
                        everyone_pings INTEGER,
                        everyone_pings_used INTEGER,
                        here_pings INTEGER,
                        here_pings_used INTEGER,
                        active BOOLEAN,
                        data JSONB
                    )
                """)
                
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS voice_channels (
                        id VARCHAR(36) PRIMARY KEY,
                        guild_id BIGINT,
                        channel_id BIGINT,
                        creator_id BIGINT,
                        created_at TIMESTAMP,
                        type VARCHAR(20),
                        parent_id BIGINT,
                        active BOOLEAN,
                        data JSONB
                    )
                """)
                
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS vouches (
                        id VARCHAR(36) PRIMARY KEY,
                        guild_id BIGINT,
                        user_id BIGINT,
                        voucher_id BIGINT,
                        reason TEXT,
                        timestamp TIMESTAMP,
                        data JSONB
                    )
                """)
                
                logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Database setup error: {e}", exc_info=True)
            raise

    def get(self, collection: str, filter_dict: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Get items from a collection with optional filtering
        """
        try:
            self._connect()
            with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                query = f"SELECT * FROM {collection}"
                params = []
                
                if filter_dict and len(filter_dict) > 0:
                    conditions = []
                    for i, (key, value) in enumerate(filter_dict.items()):
                        conditions.append(f"{key} = %s")
                        params.append(value)
                    
                    query += " WHERE " + " AND ".join(conditions)
                
                cur.execute(query, params)
                results = cur.fetchall()
                
                # Convert to regular dictionaries and handle JSON fields
                processed_results = []
                for row in results:
                    row_dict = dict(row)
                    for key, value in row_dict.items():
                        if key in ['data', 'value', 'winner_ids', 'participants']:
                            if value and isinstance(value, str):
                                try:
                                    row_dict[key] = json.loads(value)
                                except:
                                    pass
                    processed_results.append(row_dict)
                
                return processed_results
        except Exception as e:
            logger.error(f"Database get error ({collection}): {e}", exc_info=True)
            return []

    def get_one(self, collection: str, filter_dict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Get a single item from a collection with filtering
        """
        try:
            results = self.get(collection, filter_dict)
            return results[0] if results else None
        except Exception as e:
            logger.error(f"Database get_one error ({collection}): {e}", exc_info=True)
            return None

    def insert(self, collection: str, data: Dict[str, Any]) -> str:
        """
        Insert a new item into a collection
        """
        try:
            self._connect()
            
            # Ensure we have an ID
            if 'id' not in data:
                data['id'] = str(uuid.uuid4())
            
            # Convert timestamp fields
            for key, value in list(data.items()):
                if isinstance(value, datetime.datetime):
                    data[key] = value
                elif key.endswith('_at') and isinstance(value, (int, float)):
                    data[key] = datetime.datetime.fromtimestamp(value)
            
            # Extract JSON fields
            json_fields = ['data', 'value', 'winner_ids', 'participants']
            for field in json_fields:
                if field in data and (isinstance(data[field], (dict, list))):
                    data[field] = json.dumps(data[field])
            
            with self.conn.cursor() as cur:
                # Build the query
                columns = list(data.keys())
                placeholders = ["%s"] * len(columns)
                values = [data[col] for col in columns]
                
                sql = f"INSERT INTO {collection} ({', '.join(columns)}) VALUES ({', '.join(placeholders)}) RETURNING id"
                cur.execute(sql, values)
                
                # Get the ID
                id_value = cur.fetchone()[0]
                return id_value
                
        except Exception as e:
            logger.error(f"Database insert error ({collection}): {e}", exc_info=True)
            raise

    def update(self, collection: str, id_value: str, data: Dict[str, Any]) -> bool:
        """
        Update an existing item in a collection
        """
        try:
            self._connect()
            
            # Convert timestamp fields
            for key, value in list(data.items()):
                if isinstance(value, datetime.datetime):
                    data[key] = value
                elif key.endswith('_at') and isinstance(value, (int, float)):
                    data[key] = datetime.datetime.fromtimestamp(value)
            
            # Extract JSON fields
            json_fields = ['data', 'value', 'winner_ids', 'participants']
            for field in json_fields:
                if field in data and (isinstance(data[field], (dict, list))):
                    data[field] = json.dumps(data[field])
            
            with self.conn.cursor() as cur:
                # Build the query
                updates = [f"{key} = %s" for key in data.keys() if key != 'id']
                values = [data[key] for key in data.keys() if key != 'id']
                values.append(id_value)  # For the WHERE clause
                
                sql = f"UPDATE {collection} SET {', '.join(updates)} WHERE id = %s"
                cur.execute(sql, values)
                
                return cur.rowcount > 0
                
        except Exception as e:
            logger.error(f"Database update error ({collection}): {e}", exc_info=True)
            return False

    def delete(self, collection: str, id_value: str) -> bool:
        """
        Delete an item from a collection
        """
        try:
            self._connect()
            
            with self.conn.cursor() as cur:
                sql = f"DELETE FROM {collection} WHERE id = %s"
                cur.execute(sql, [id_value])
                
                return cur.rowcount > 0
                
        except Exception as e:
            logger.error(f"Database delete error ({collection}): {e}", exc_info=True)
            return False

    def delete_many(self, collection: str, filter_dict: Dict[str, Any]) -> int:
        """
        Delete multiple items from a collection with filtering
        """
        try:
            self._connect()
            
            with self.conn.cursor() as cur:
                conditions = []
                values = []
                
                for key, value in filter_dict.items():
                    conditions.append(f"{key} = %s")
                    values.append(value)
                
                sql = f"DELETE FROM {collection} WHERE {' AND '.join(conditions)}"
                cur.execute(sql, values)
                
                return cur.rowcount
                
        except Exception as e:
            logger.error(f"Database delete_many error ({collection}): {e}", exc_info=True)
            return 0