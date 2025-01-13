import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from datetime import datetime
from typing import List, Optional, Dict, Any

from subsystem.ccxt.ccxtInterface import ccxtInterface
from subsystem.questdb.qdbInterace import qdbInterface
from subsystem.database.dbManager import dbManager

import logging
import asyncio

logger = logging.getLogger(__name__)

MAX_CONCURRENT_OPS = 5

class importDataFacade:
    """
    Facade for handling data import operations between CCXT and QuestDB
    """
    def __init__(self, config: Dict[str, Any]):
        """Initialize facade with config"""
        self.config = config
        self.ccxt_interface = ccxtInterface()
        self.questdb_interface = qdbInterface()
        self.db_manager = dbManager()
        self.active_tasks = {}  # For tracking active tasks
        
        

    async def import_ohlcv_data(self, exchange_name: str, tickers: List[str],
                               timeframes: List[str], start_date: str,
                               end_date: Optional[str] = None) -> bool:
        """Main method to import OHLCV data with controlled concurrency"""
        
        try:
            logger.info(f"Starting data import for {len(tickers)} symbols...")
            start_time = datetime.now()

            # Initialize exchange and database
            await self.ccxt_interface.initialize_exchange(exchange_name)
        

            # Validate available symbols and timeframes
            available_symbols = await self.ccxt_interface.get_available_symbols()
            available_timeframes = await self.ccxt_interface.get_available_timeframes()

            # Quick validation
            invalid_symbols = [s for s in tickers if s not in available_symbols]
            invalid_timeframes = [t for t in timeframes if t not in available_timeframes]
            
            if invalid_symbols or invalid_timeframes:
                logger.error(f"Invalid symbols: {invalid_symbols}")
                logger.error(f"Invalid timeframes: {invalid_timeframes}")
                return False

            async def process_symbol_timeframe(ticker: str, timeframe: str) -> bool:
                """Process a single symbol-timeframe combination"""
                task_id = f"{ticker} {timeframe} {exchange_name}"
                try:
                    self.active_tasks[task_id] = "Fetching OHLCV"
                    logger.info(f"Processing {task_id}. Active tasks: {list(self.active_tasks.keys())}")
                    
                    # Sequential operations without individual semaphores
                    ohlcv_data = await self.ccxt_interface.fetch_ohlcv(
                        ticker,
                        timeframe,
                        int(datetime.strptime(start_date, '%Y-%m-%d').timestamp() * 1000),
                        None if not end_date else int(datetime.strptime(end_date, '%Y-%m-%d').timestamp() * 1000)
                    )
                    
                    if not ohlcv_data:
                        logger.info(f"No data for {task_id}")
                        return True

                    self.active_tasks[task_id] = "Creating table"
                    table_name = await self.db_manager.create_table(
                        ticker, timeframe, exchange_name
                    )
                    if not table_name:
                        return False

                    self.active_tasks[task_id] = "Writing to QuestDB"
                    success = await self.questdb_interface.dump_ohlcv(
                        table_name, ohlcv_data, ticker, timeframe, exchange_name
                    )
                    if not success:
                        return False

                    logger.info(f"Successfully processed {task_id}")
                    return True

                except Exception as e:
                    logger.error(f"Error processing {task_id}: {str(e)}")
                    return False
                finally:
                    if task_id in self.active_tasks:
                        del self.active_tasks[task_id]
                        logger.info(f"Completed {task_id}. Current tasks: {list(self.active_tasks.keys())}")

            # Single bounded semaphore for overall concurrency control
            sem = asyncio.BoundedSemaphore(MAX_CONCURRENT_OPS)
            
            async def bounded_process(ticker: str, timeframe: str) -> bool:
                async with sem:
                    return await process_symbol_timeframe(ticker, timeframe)

            tasks = [
                bounded_process(ticker, timeframe)
                for ticker in tickers
                for timeframe in timeframes
            ]

            results = await asyncio.gather(*tasks)
            success = all(results)

            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"Import completed in {duration:.2f} seconds")
            return success

        except Exception as e:
            logger.error(f"Import failed: {str(e)}")
            return False
        finally:
            await self.ccxt_interface.close()
            await self.db_manager.close_connection_pool()
