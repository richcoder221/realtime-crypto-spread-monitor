import logging
from typing import List, Dict, Any, Optional
from .dbConnector import dbConnector
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)

class dbManager:
    def __init__(self):
        self._pool = None

    async def initialize(self):
        """Initialize the connection pool"""
        try:
            self._pool = await dbConnector.get_pool()
            logger.info("Database connection pool initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {str(e)}")
            raise
    
    async def close_connection_pool(self):
        """Close the database connection pool"""
        try:
            # Close the pool
            await dbConnector.close_pool()
            self._pool = None
            logger.info("Database connection pool closed")
            
            # Give time for SSL cleanup
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"Failed to close database connection pool: {str(e)}")
            raise

    async def create_table(self, ticker: str, timeframe: str, exchange: str) -> str:
        """Create table if it doesn't exist"""
        try:
            transfrom_ticker = ticker.replace('/', '-').replace(':', '-')
            ohlcv_table_name = f"ohlcv_{transfrom_ticker}_{timeframe}_{exchange}"
            query = f"""
                CREATE TABLE IF NOT EXISTS "{ohlcv_table_name}" (
                ticker SYMBOL capacity 256 CACHE,
                interval SYMBOL capacity 256 CACHE,
                exchange SYMBOL capacity 256 CACHE,
                open DOUBLE,
                high DOUBLE,
                low DOUBLE,
                close DOUBLE,
                volume DOUBLE,
                timestamp TIMESTAMP
                ) timestamp (timestamp) PARTITION BY YEAR WAL DEDUP UPSERT KEYS(timestamp)
            """
            
            await dbConnector.execute_query_with_retry(query)
            logger.info(f"Successfully create ohlcv table for {ticker} {timeframe} on {exchange}")
            return ohlcv_table_name
        except Exception as e:
            logger.error(f"Failed to create table: {str(e)}")
            return None

    async def copy_data_to_ohlcv(self, original_table: str, new_table: str):
        """Copy data from original table to new OHLCV table."""
        try:
            insert_query = f"""
            INSERT INTO "{new_table}"
            SELECT * FROM "{original_table}"
            """
            await dbConnector.execute_query_with_retry(insert_query)
            logger.info(f"Copied data from {original_table} to {new_table}")
        except Exception as e:
            logger.error(f"Error copying data to {new_table}: {str(e)}")
            raise

    async def drop_tables_by_prefix(self, prefix: str):
        """Drop all tables that start with the given prefix."""
        try:
            tables = await self.get_all_tables()
            tables_to_drop = [table for table in tables if table.startswith(prefix)]
            
            for table in tables_to_drop:
                drop_query = f'DROP TABLE IF EXISTS "{table}"'
                await dbConnector.execute_query_with_retry(drop_query)
                logger.info(f"Dropped table: {table}")
            
            return len(tables_to_drop)
        except Exception as e:
            logger.error(f"Error dropping tables with prefix {prefix}: {str(e)}")
            raise

    async def drop_tables_by_pattern(self, pattern: str):
        """Drop all tables that match the given pattern using LIKE operator."""
        try:
            query = f"SELECT table_name FROM Tables() WHERE table_name LIKE '{pattern}'"
            records = await dbConnector.fetch_query_with_retry(query)
            tables_to_drop = [record['table_name'] for record in records]
            
            for table in tables_to_drop:
                drop_query = f'DROP TABLE IF EXISTS "{table}"'
                await dbConnector.execute_query_with_retry(drop_query)
                logger.info(f"Dropped table: {table}")
            
            return len(tables_to_drop)
        except Exception as e:
            logger.error(f"Error dropping tables matching pattern {pattern}: {str(e)}")
            raise

    async def drop_tables_exclude_prefix(self, exclude_prefixes: List[str]):
        """Drop all tables that don't start with any of the given prefixes."""
        try:
            tables = await self.get_all_tables()
            tables_to_drop = []
            
            for table in tables:
                should_keep = any(table.startswith(prefix) for prefix in exclude_prefixes)
                if not should_keep:
                    tables_to_drop.append(table)
            
            for table in tables_to_drop:
                drop_query = f'DROP TABLE IF EXISTS "{table}"'
                await dbConnector.execute_query_with_retry(drop_query)
                logger.info(f"Dropped table: {table}")
            
            return len(tables_to_drop)
        except Exception as e:
            logger.error(f"Error dropping tables excluding prefixes {exclude_prefixes}: {str(e)}")
            raise

    async def fetch_ohlcv_data(
        self,
        ticker: str,
        timeframe: str,
        exchange: str,
        start_date: str,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Fetch OHLCV data from database"""
        try:
            # Transform ticker for table name
            transform_ticker = ticker.replace('/', '-').replace(':', '-')
            table_name = f"ohlcv_{transform_ticker}_{timeframe}_{exchange}"
            
            # Convert dates to proper timestamp format
            start_ts = datetime.fromisoformat(start_date)
            end_ts = datetime.fromisoformat(end_date) if end_date else datetime.utcnow()
            
            # Build query with proper field selection
            query = f"""
                SELECT 
                    ticker,
                    interval,
                    exchange,
                    open,
                    high,
                    low,
                    close,
                    volume,
                    timestamp
                FROM "{table_name}"
                WHERE timestamp >= $1
                AND timestamp <= $2
                ORDER BY timestamp ASC
            """
            
            # Let dbConnector handle the batch fetching with its configured settings
            records = await dbConnector.fetch_in_batches(
                query=query,
                params=[start_ts, end_ts]
            )
            
            return records
            
        except Exception as e:
            logger.error(f"Failed to fetch OHLCV data: {str(e)}")
            return []