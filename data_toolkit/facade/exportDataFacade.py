import asyncio
import logging
import csv
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from pathlib import Path

from subsystem.database.dbManager import dbManager

logger = logging.getLogger(__name__)

MAX_CONCURRENT_OPS = 5

class exportDataFacade:
    """Facade for handling data export operations from QuestDB to CSV"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize facade with config"""
        self.config = config
        self.db_manager = dbManager()
        self.active_tasks = {}
        
    async def export_ohlcv_data(
        self, 
        exchange_name: str,
        tickers: List[str],
        timeframes: List[str],
        start_date: str,
        end_date: Optional[str] = None,
        output_dir: Optional[str] = None
    ) -> bool:
        """Main method to export OHLCV data with controlled concurrency"""
        
        try:
            logger.info(f"Starting data export for {len(tickers)} symbols...")
            start_time = datetime.now()
            
            # Ensure output directory exists
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            async def process_symbol_timeframe(ticker: str, timeframe: str) -> bool:
                """Process a single symbol-timeframe combination"""
                task_id = f"{ticker} {timeframe} {exchange_name}"
                try:
                    self.active_tasks[task_id] = "Fetching OHLCV"
                    logger.info(f"Processing {task_id}")
                    
                    # Fetch data from database
                    ohlcv_data = await self.db_manager.fetch_ohlcv_data(
                        ticker=ticker,
                        timeframe=timeframe,
                        exchange=exchange_name,
                        start_date=start_date,
                        end_date=end_date
                    )
                    
                    if not ohlcv_data:
                        logger.info(f"No data for {task_id}")
                        return True
                    
                    # Convert to CSV
                    self.active_tasks[task_id] = "Writing CSV"

                    
                    success = await self._write_to_csv_with_factor(
                        data=ohlcv_data,
                        base_path=output_dir
                    )
                    
                    if success:
                        logger.info(f"Successfully exported {task_id} to {output_dir}")
                    return success
                    
                except Exception as e:
                    logger.error(f"Error processing {task_id}: {str(e)}")
                    return False
                finally:
                    if task_id in self.active_tasks:
                        del self.active_tasks[task_id]
            
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
            logger.info(f"Export completed in {duration:.2f} seconds")
            return success
            
        except Exception as e:
            logger.error(f"Export failed: {str(e)}")
            return False
        finally:
            await asyncio.sleep(0.2)
            await self.db_manager.close_connection_pool()
            await asyncio.sleep(0.2)

    async def _write_to_csv_with_factor(self, data: List[Dict[str, Any]], base_path: Union[str, Path]) -> bool:
        """Convert database results to CSV file with factor column added"""
        try:
            if not data:
                return False

            # Convert base_path to Path object if it's a string
            base_path = Path(base_path)

            # Get exchange, timeframe, and ticker from first row
            first_row = data[0]
            exchange = first_row['exchange'].lower()
            timeframe = first_row['interval'].lower()
            ticker = first_row['ticker'].replace('/', '-')

            # Construct directory structure: crypto_{timeframe}/{exchange}/
            timeframe_dir = f"crypto_{timeframe}"
            output_dir = base_path.joinpath(timeframe_dir).joinpath(exchange)
            output_dir.mkdir(parents=True, exist_ok=True)

            # Construct final filepath: crypto_{timeframe}/{exchange}/{ticker}.csv
            final_filepath = output_dir.joinpath(f"{ticker}.csv")
            
            # Check if file exists and remove it
            if final_filepath.exists():
                logger.info(f"Removing existing file: {final_filepath}")
                final_filepath.unlink()
                
            # Add factor column to the original data
            for row in data:
                row['factor'] = 1.0
                
            # Get fieldnames from first row and ensure factor is included
            fieldnames = list(data[0].keys())
            if 'factor' not in fieldnames:
                fieldnames.append('factor')
                
            # Write to CSV file
            with open(final_filepath, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)
                
            logger.info(f"Successfully wrote {len(data)} records to {final_filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to write CSV file: {str(e)}")
            return False
        

      
