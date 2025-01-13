import logging
from typing import List, Dict, Any, AsyncGenerator
from subsystem.ccxt.ccxtProInterface import ccxtProInterface
from subsystem.kafka.kafkaProducer import KafkaProducerWrapper

logger = logging.getLogger(__name__)

class streamingDataFacade:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.ccxt_pro = ccxtProInterface()
        self.kafka_producer = KafkaProducerWrapper()
        self._running = True

    async def cleanup(self):
        """Cleanup resources"""
        self._running = False
        if hasattr(self, 'ccxt_pro'):
            await self.ccxt_pro.close()
        if hasattr(self, 'kafka_producer'):
            self.kafka_producer.close()
        
    async def watch_multiple_ohlcv(
        self,
        exchange_name: str,
        tickers: List[str],
        timeframes: List[str]
    ) -> AsyncGenerator[Dict, None]:
        try:
            await self.ccxt_pro.initialize_exchange(exchange_name, newUpdates=True)
            logger.info(f"Starting data streaming for {len(tickers)} symbols...")
            
            # Validate symbols and timeframes
            available_symbols = await self.ccxt_pro.get_available_symbols()
            available_timeframes = await self.ccxt_pro.get_available_timeframes()

            logger.info(f"Available timeframes: {available_timeframes}")
            
            invalid_symbols = [s for s in tickers if s not in available_symbols]
            invalid_timeframes = [t for t in timeframes if t not in available_timeframes]
            
            if invalid_symbols or invalid_timeframes:
                logger.error(f"Invalid symbols: {invalid_symbols}")
                logger.error(f"Invalid timeframes: {invalid_timeframes}")
                await self.cleanup()
                return
            
            while self._running:
                async for candles in self.ccxt_pro.watch_multiple_ohlcv(tickers, timeframes):
                    if not self._running:
                        break
                    
                    # Send to Kafka before yielding
                    self.kafka_producer.send_ohlcv_data(candles)
                    yield candles
                    
        except KeyboardInterrupt:
            logger.info("Stream interrupted by user")
            await self.cleanup()
        except Exception as e:
            logger.error(f"Streaming failed: {str(e)}")
            await self.cleanup()
            raise
