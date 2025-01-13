import threading
import ccxt.pro as ccxtpro
import asyncio
from typing import List, Optional, Any, Dict
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ccxtProInterface:
    _instance_lock = threading.Lock()
    _unique_instance = None

    def __new__(cls):
        with cls._instance_lock:
            if cls._unique_instance is None:
                cls._unique_instance = super(ccxtProInterface, cls).__new__(cls)
                cls._unique_instance._init_interface()
        return cls._unique_instance

    def _init_interface(self):
        """Initialize the interface attributes"""
        self._exchange = None
        self._subscriptions = []
        self._initialized = False

    async def initialize_exchange(self, exchange_name: str, newUpdates: bool) -> Any:
        """Initialize and return exchange instance"""
        try:
            if self._exchange is not None:
                return self._exchange

            # Get exchange class and create instance
            exchange_class = getattr(ccxtpro, exchange_name.lower())
            exchange_params = {
                'newUpdates': True
            } if newUpdates else {
                'enableRateLimit': True,
                'options': {
                    'tradesLimit': 1000,
                    'OHLCVLimit': 1000,
                    'ordersLimit': 1000,
                }
            }

            self._exchange = exchange_class(exchange_params)
            await self._exchange.load_markets()
            
            logger.info(f"Successfully initialized {exchange_name} exchange with CCXT Pro version {ccxtpro.__version__}")
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

    async def watch_multiple_ohlcv(self, symbols: List[str], timeframes: List[str]):
        
        # Format subscriptions for bulk watching
        subscriptions = [[symbol, timeframe] for symbol in symbols for timeframe in timeframes]
        logger.info(f"Creating subscriptions: {subscriptions}")
        
        
        while True:
            try:
                # Watch all symbols at once using watch_ohlcv_for_symbols
                candles = await self._exchange.watch_ohlcv_for_symbols(subscriptions)

                # Format and yield results
                yield candles
                
                
            except Exception as loop_error:
                logger.error(f"Loop error: {str(loop_error)}")
                logger.error(f"Error type: {type(loop_error)}")
                await asyncio.sleep(1)
                    
            except Exception as e:
                logger.error(f"Fatal error: {str(e)}")
                logger.error(f"Error type: {type(e)}")
                raise

    async def close(self):
        """Close the exchange connection and cleanup resources"""
        try:
            if self._exchange is not None:
                await self._exchange.close()
                self._exchange = None
                logger.info("Successfully closed exchange connection")
        except Exception as e:
            logger.error(f"Error closing exchange: {str(e)}")
            raise