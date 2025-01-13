import ccxt.async_support as ccxt_async
from datetime import datetime
from typing import List, Optional, Any, Dict
import logging
from tqdm import tqdm
import asyncio

logger = logging.getLogger(__name__)

class ccxtInterface:
    def __init__(self):
        """Initialize CCXT interface"""
        self._exchange = None
        
    async def initialize_exchange(self, exchange_name: str) -> Any:
        """Initialize and return exchange instance for reuse"""
        try:
            if self._exchange is not None:
                return self._exchange
                
            # Get exchange class and create instance
            exchange_class = getattr(ccxt_async, exchange_name.lower())
            self._exchange = exchange_class({
                'enableRateLimit': True,  # Enable built-in rate limiting
            })
            
            # Load markets
            await self._exchange.load_markets()
            
            # Check if exchange supports OHLCV
            if not self._exchange.has['fetchOHLCV']:
                raise RuntimeError(f"Exchange {exchange_name} does not support OHLCV data fetching")
                
            logger.info(f"Successfully initialized {exchange_name} exchange")
            return self._exchange
            
        except Exception as e:
            logger.error(f"Failed to initialize exchange: {str(e)}")
            raise

    async def get_available_symbols(self) -> List[str]:
        """Get list of available trading pairs"""
        if not self._exchange:
            raise RuntimeError("Exchange not initialized")
        return list(self._exchange.markets.keys())

    async def get_available_timeframes(self) -> List[str]:
        """Get list of supported timeframes"""
        if not self._exchange:
            raise RuntimeError("Exchange not initialized")
        return list(self._exchange.timeframes.keys())

    def _calculate_progress(self, current: int, start: int, end: int) -> float:
        """Calculate progress percentage"""
        total_range = end - start
        current_progress = current - start
        return (current_progress / total_range) * 100 if total_range > 0 else 0

    def timeframe_to_milliseconds(self, timeframe: str) -> int:
        """Convert timeframe string to milliseconds"""
        unit = timeframe[-1]
        number = int(timeframe[:-1])
        
        units = {
            'm': 60 * 1000,
            'h': 60 * 60 * 1000,
            'd': 24 * 60 * 60 * 1000,
            'w': 7 * 24 * 60 * 60 * 1000,
        }
        
        return number * units[unit]

    async def fetch_ohlcv(self, 
                         symbol: str, 
                         timeframe: str, 
                         since: int, 
                         end: Optional[int] = None, 
                         limit: int = 1000) -> List[List[float]]:
        """Fetch OHLCV data with proper progress tracking"""
        try:
            ohlcv = []
            current_since = since
            end_time = end if end else int(datetime.now().timestamp() * 1000)
            
            # Create progress bar without position parameter
            pbar = tqdm(total=100, desc=f"Fetching {symbol} {timeframe}", 
                       bar_format='{l_bar}{bar}| {n:.2f}/{total:.2f} [{elapsed}<{remaining}]')
            
            while current_since < end_time:
                try:
                    batch = await self._exchange.fetch_ohlcv(
                        symbol, timeframe, current_since, limit
                    )
                    
                    if not batch:
                        break
                        
                    batch = [candle for candle in batch if candle[0] <= end_time]
                    if not batch:
                        break
                        
                    ohlcv.extend(batch)
                    
                    # Update progress
                    current_since = batch[-1][0] + self.timeframe_to_milliseconds(timeframe)
                    progress = min(100, (current_since - since) / (end_time - since) * 100)
                    pbar.n = progress
                    pbar.refresh()
                    
                except Exception as e:
                    logger.error(f"Error in batch fetch: {str(e)}")
                    raise
                    
            pbar.close()
            return ohlcv
            
        except Exception as e:
            logger.error(f"Error fetching OHLCV data for {symbol} {timeframe}: {str(e)}")
            raise

    async def close(self):
        """Properly close exchange connection"""
        if self._exchange:
            await self._exchange.close()

