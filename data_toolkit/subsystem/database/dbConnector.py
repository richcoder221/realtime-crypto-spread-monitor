import asyncpg
import logging
import ssl
from typing import Optional, Any, List, Dict
from contextlib import asynccontextmanager
from datetime import datetime
from .db_config import *
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class dbConnector:
    _pool: Optional[asyncpg.Pool] = None

    @classmethod
    async def get_pool(cls) -> asyncpg.Pool:
        """Get or create the connection pool with optimized settings."""
        if cls._pool is None:
            try:
                # Create SSL context
                #ssl_context = ssl.create_default_context()
                #ssl_context.check_hostname = False
                #ssl_context.verify_mode = ssl.CERT_NONE

                # Initialize connection pool with optimized settings
                cls._pool = await asyncpg.create_pool(
                    host=DB_HOST,
                    port=DB_PORT,
                    user=DB_USER,
                    password=DB_PASS,
                    database=DB_NAME,
                    min_size=POOL_MIN_SIZE,
                    max_size=POOL_MAX_SIZE,
                    max_queries=POOL_MAX_QUERIES,
                    timeout=POOL_TIMEOUT,
                    command_timeout=POOL_TIMEOUT,
                    statement_cache_size=STATEMENT_CACHE_SIZE,
                    max_inactive_connection_lifetime=MAX_INACTIVE_CONNECTION_LIFETIME,
                    #ssl=ssl_context,
                    server_settings={
                        'application_name': PG_APPLICATION_NAME,
                        'statement_timeout': str(POOL_TIMEOUT * 1000),  # Convert to ms
                        'idle_in_transaction_session_timeout': '300000',  # 5 minutes
                        'tcp_keepalives_idle': '60',
                        'tcp_keepalives_interval': '10',
                        'tcp_keepalives_count': '3'
                    },
                    # Add timestamp codec during pool creation
                    init=cls._init_connection
                )
                logger.info(f"Created connection pool: size={POOL_MIN_SIZE}-{POOL_MAX_SIZE}")
            except Exception as e:
                logger.error(f"Failed to create connection pool: {str(e)}")
                raise
        return cls._pool

    @staticmethod
    async def _init_connection(conn):
        """Initialize connection with custom codecs."""
        try:
            # QuestDB only supports 'timestamp' type, not 'timestamptz'
            await conn.set_type_codec(
                'timestamp',
                encoder=lambda v: v.isoformat() if v else None,
                decoder=lambda v: datetime.fromisoformat(v) if v else None,
                schema='pg_catalog',
                format='text'
            )
        except Exception as e:
            logger.error(f"Error setting up connection codecs: {str(e)}")
            raise

    @classmethod
    @asynccontextmanager
    async def get_connection(cls):
        """Get a connection from the pool with automatic release."""
        if cls._pool is None:
            await cls.get_pool()
        
        async with cls._pool.acquire() as conn:
            try:
                yield conn
            except Exception as e:
                logger.error(f"Error with connection: {str(e)}")
                raise

 
    @classmethod
    async def close_pool(cls):
        """Properly close the connection pool"""
        if cls._pool:
            try:
                # Close all connections in the pool
                await cls._pool.close()
                cls._pool = None
                logger.info("Connection pool closed successfully")
            except Exception as e:
                logger.error(f"Error closing connection pool: {str(e)}")
                raise

    @classmethod
    async def execute_with_retry(cls, operation, max_retries: int = 3):
        """Execute operation with retry logic"""
        for attempt in range(max_retries):
            try:
                return await operation()
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning(f"Retry attempt {attempt + 1} due to: {str(e)}")
                await asyncio.sleep(1 * (attempt + 1))  # Exponential backoff

    @classmethod
    async def execute_query_with_retry(cls, query: str, *args):
        """Execute a single query with retry logic."""
        async def operation():
            async with cls.get_connection() as conn:
                return await conn.execute(query, *args)
        return await cls.execute_with_retry(operation)

    @classmethod
    async def fetch_query_with_retry(cls, query: str, *args):
        """Execute a query and fetch all results with retry logic."""
        async def operation():
            async with cls.get_connection() as conn:
                return await conn.fetch(query, *args)
        return await cls.execute_with_retry(operation)

    @classmethod
    async def fetch_one_with_retry(cls, query: str, *args):
        """Execute a query and fetch one result with retry logic."""
        async def operation():
            async with cls.get_connection() as conn:
                return await conn.fetchrow(query, *args)
        return await cls.execute_with_retry(operation)

    @classmethod
    async def fetch_in_batches(
        cls,
        query: str,
        params: List[Any],
        batch_size: int = BATCH_SIZE,
        timeout: int = BATCH_TIMEOUT
    ) -> List[Dict[str, Any]]:
        """Fetch large datasets in batches to avoid memory issues"""
        all_records = []
        
        async def fetch_batch():
            async with cls.get_connection() as conn:
                try:
                    # Set statement timeout for this operation
                    await conn.execute(f'SET statement_timeout = {timeout * 1000}')
                    
                    # Create a new prepared statement within this connection context
                    stmt = await conn.prepare(query)
                    records = await stmt.fetch(*params)
                    return [dict(r) for r in records]
                except Exception as e:
                    logger.error(f"Error in fetch_batch: {str(e)}")
                    raise
        
        try:
            records = await cls.execute_with_retry(fetch_batch)
            
            # Process records in batches
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                all_records.extend(batch)
                
            return all_records
            
        except Exception as e:
            logger.error(f"Error fetching in batches: {str(e)}")
            return []
