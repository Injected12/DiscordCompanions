"""
Database implementation for D10 Discord Bot using PostgreSQL
"""

import logging
import json
import uuid
import os
import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, List, Any, Optional, Union

logger = logging.getLogger("d10-bot")

class Database:
    """
    PostgreSQL database manager for D10 Discord Bot
    """
    
    def __init__(self):
        self.connection_params = self._get_connection_params()
        self._setup_database()
        
    def _get_connection_params(self) -> Dict[str, Any]:
        """
        Get database connection parameters from environment variables
        """
        # Get connection parameters from environment
        database_url = os.getenv("DATABASE_URL")
        
        if database_url:
            return {"dsn": database_url}
        else:
            # Fallback to individual parameters
            return {
                "host": os.getenv("PGHOST", "localhost"),
                "port": int(os.getenv("PGPORT", "5432")),
                "user": os.getenv("PGUSER", "postgres"),
                "password": os.getenv("PGPASSWORD", ""),
                "database": os.getenv("PGDATABASE", "d10bot")
            }
    
    def _connect(self):
        """
        Create a new database connection
        """
        try:
            return psycopg2.connect(**self.connection_params)
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise
            
    def _setup_database(self) -> None:
        """
        Set up database tables
        """
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    # Create tables for each collection
                    tables = [
                        """
                        CREATE TABLE IF NOT EXISTS tickets (
                            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                            guild_id BIGINT NOT NULL,
                            channel_id BIGINT,
                            user_id BIGINT NOT NULL,
                            ticket_type TEXT NOT NULL,
                            answers JSONB NOT NULL,
                            status TEXT NOT NULL,
                            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                            closed_at TIMESTAMP,
                            closed_by BIGINT,
                            staff_id BIGINT
                        )
                        """,
                        """
                        CREATE TABLE IF NOT EXISTS welcome (
                            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                            guild_id BIGINT NOT NULL,
                            channel_id BIGINT NOT NULL,
                            enabled BOOLEAN NOT NULL DEFAULT TRUE,
                            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                            created_by BIGINT,
                            updated_at TIMESTAMP,
                            updated_by BIGINT
                        )
                        """,
                        """
                        CREATE TABLE IF NOT EXISTS status_tracking (
                            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                            guild_id BIGINT NOT NULL,
                            user_id BIGINT NOT NULL,
                            status TEXT,
                            since TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                        )
                        """,
                        """
                        CREATE TABLE IF NOT EXISTS slot_channels (
                            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                            guild_id BIGINT NOT NULL,
                            channel_id BIGINT NOT NULL,
                            user_id BIGINT NOT NULL,
                            duration_days INTEGER NOT NULL,
                            everyone_pings INTEGER NOT NULL DEFAULT 0,
                            everyone_pings_used INTEGER NOT NULL DEFAULT 0,
                            here_pings INTEGER NOT NULL DEFAULT 0,
                            here_pings_used INTEGER NOT NULL DEFAULT 0,
                            category_id BIGINT,
                            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                            created_by BIGINT,
                            expires_at TIMESTAMP NOT NULL,
                            active BOOLEAN NOT NULL DEFAULT TRUE,
                            closed_at TIMESTAMP,
                            closed_reason TEXT
                        )
                        """,
                        """
                        CREATE TABLE IF NOT EXISTS voice_channels (
                            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                            guild_id BIGINT NOT NULL,
                            channel_id BIGINT NOT NULL,
                            user_id BIGINT,
                            category_id BIGINT,
                            type TEXT NOT NULL,
                            active BOOLEAN NOT NULL DEFAULT TRUE,
                            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                            created_by BIGINT,
                            updated_at TIMESTAMP,
                            updated_by BIGINT,
                            deleted_at TIMESTAMP
                        )
                        """,
                        """
                        CREATE TABLE IF NOT EXISTS reports (
                            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                            guild_id BIGINT NOT NULL,
                            user_id BIGINT NOT NULL,
                            reporter_id BIGINT NOT NULL,
                            reason TEXT NOT NULL,
                            type TEXT NOT NULL,
                            timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                            status TEXT NOT NULL,
                            reviewed_by BIGINT,
                            reviewed_at TIMESTAMP
                        )
                        """,
                        """
                        CREATE TABLE IF NOT EXISTS vouches (
                            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                            guild_id BIGINT NOT NULL,
                            user_id BIGINT NOT NULL,
                            voucher_id BIGINT NOT NULL,
                            reason TEXT NOT NULL,
                            timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                        )
                        """,
                        """
                        CREATE TABLE IF NOT EXISTS giveaways (
                            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                            guild_id BIGINT NOT NULL,
                            channel_id BIGINT NOT NULL,
                            message_id BIGINT NOT NULL,
                            host_id BIGINT NOT NULL,
                            prize TEXT NOT NULL,
                            winners_count INTEGER NOT NULL DEFAULT 1,
                            end_time TIMESTAMP NOT NULL,
                            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                            ended BOOLEAN NOT NULL DEFAULT FALSE,
                            ended_at TIMESTAMP,
                            winner_ids JSONB
                        )
                        """,
                        """
                        CREATE TABLE IF NOT EXISTS lockdown (
                            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                            guild_id BIGINT NOT NULL,
                            channel_id BIGINT NOT NULL,
                            send_messages BOOLEAN,
                            add_reactions BOOLEAN,
                            locked_by BIGINT NOT NULL,
                            locked_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                            reason TEXT
                        )
                        """,
                        """
                        CREATE TABLE IF NOT EXISTS moderation (
                            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                            guild_id BIGINT NOT NULL,
                            user_id BIGINT NOT NULL,
                            moderator_id BIGINT NOT NULL,
                            action TEXT NOT NULL,
                            reason TEXT,
                            timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                        )
                        """,
                        """
                        CREATE TABLE IF NOT EXISTS ticket_settings (
                            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                            guild_id BIGINT NOT NULL,
                            channel_id BIGINT NOT NULL,
                            category_id BIGINT,
                            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                            created_by BIGINT,
                            updated_at TIMESTAMP,
                            updated_by BIGINT
                        )
                        """,
                        """
                        CREATE TABLE IF NOT EXISTS config (
                            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                            guild_id BIGINT,
                            key TEXT NOT NULL,
                            value TEXT NOT NULL
                        )
                        """
                    ]
                    
                    for table_sql in tables:
                        cur.execute(table_sql)
                    
                    conn.commit()
                    logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Database setup error: {e}")
            raise
            
    def get(self, collection: str, filter_dict: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Get items from a collection with optional filtering
        """
        try:
            with self._connect() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    if not filter_dict:
                        # Get all items
                        cur.execute(f"SELECT * FROM {collection}")
                    else:
                        # Build WHERE clause for filtering
                        where_clauses = []
                        params = []
                        
                        for key, value in filter_dict.items():
                            # Handle JSON fields
                            if isinstance(value, dict) and key in ['answers', 'winner_ids']:
                                where_clauses.append(f"{key} @> %s")
                                params.append(json.dumps(value))
                            else:
                                where_clauses.append(f"{key} = %s")
                                params.append(value)
                                
                        where_clause = " AND ".join(where_clauses)
                        cur.execute(f"SELECT * FROM {collection} WHERE {where_clause}", params)
                        
                    results = cur.fetchall()
                    # Convert to list of dicts
                    return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Database get error ({collection}): {e}")
            return []
            
    def get_one(self, collection: str, filter_dict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Get a single item from a collection with filtering
        """
        results = self.get(collection, filter_dict)
        return results[0] if results else None
        
    def insert(self, collection: str, data: Dict[str, Any]) -> str:
        """
        Insert a new item into a collection
        """
        try:
            with self._connect() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Prepare column names and values
                    columns = []
                    placeholders = []
                    values = []
                    
                    for key, value in data.items():
                        columns.append(key)
                        placeholders.append("%s")
                        
                        # Handle timestamp conversions
                        if key.endswith('_at') and isinstance(value, (int, float)):
                            value = datetime.datetime.fromtimestamp(value)
                            
                        # Handle JSON data
                        if isinstance(value, (dict, list)) and key in ['answers', 'winner_ids']:
                            value = json.dumps(value)
                            
                        values.append(value)
                        
                    # Generate ID if not provided
                    if 'id' not in data:
                        columns.append('id')
                        placeholders.append('gen_random_uuid()')
                    
                    # Build SQL statement
                    sql = f"INSERT INTO {collection} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
                    if 'id' not in data:
                        sql += " RETURNING id"
                        
                    cur.execute(sql, values)
                    
                    # Get ID of inserted row
                    if 'id' in data:
                        return data['id']
                    else:
                        result = cur.fetchone()
                        return result['id']
        except Exception as e:
            logger.error(f"Database insert error ({collection}): {e}")
            raise
            
    def update(self, collection: str, id_value: str, data: Dict[str, Any]) -> bool:
        """
        Update an existing item in a collection
        """
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    # Prepare SET clause
                    set_parts = []
                    values = []
                    
                    for key, value in data.items():
                        # Skip ID field
                        if key == 'id':
                            continue
                            
                        # Handle timestamp conversions
                        if key.endswith('_at') and isinstance(value, (int, float)):
                            value = datetime.datetime.fromtimestamp(value)
                            
                        # Handle JSON data
                        if isinstance(value, (dict, list)) and key in ['answers', 'winner_ids']:
                            value = json.dumps(value)
                            
                        set_parts.append(f"{key} = %s")
                        values.append(value)
                        
                    # Add ID to values
                    values.append(id_value)
                    
                    # Build SQL statement
                    sql = f"UPDATE {collection} SET {', '.join(set_parts)} WHERE id = %s"
                    cur.execute(sql, values)
                    
                    return cur.rowcount > 0
        except Exception as e:
            logger.error(f"Database update error ({collection}): {e}")
            return False
            
    def delete(self, collection: str, id_value: str) -> bool:
        """
        Delete an item from a collection
        """
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"DELETE FROM {collection} WHERE id = %s", [id_value])
                    return cur.rowcount > 0
        except Exception as e:
            logger.error(f"Database delete error ({collection}): {e}")
            return False
            
    def delete_many(self, collection: str, filter_dict: Dict[str, Any]) -> int:
        """
        Delete multiple items from a collection with filtering
        """
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    # Build WHERE clause
                    where_clauses = []
                    params = []
                    
                    for key, value in filter_dict.items():
                        where_clauses.append(f"{key} = %s")
                        params.append(value)
                        
                    where_clause = " AND ".join(where_clauses)
                    cur.execute(f"DELETE FROM {collection} WHERE {where_clause}", params)
                    
                    return cur.rowcount
        except Exception as e:
            logger.error(f"Database delete_many error ({collection}): {e}")
            return 0
