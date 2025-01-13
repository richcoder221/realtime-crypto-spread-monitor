import sys
import os
import signal
from datetime import datetime
import logging
import asyncio

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from facade.streamingDataFacade import streamingDataFacade

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Config:
    EXCHANGE_NAME = 'bybit'
    TICKERS_FILE = 'tickers.txt'
    TIMEFRAME = ['1m']

    def load_tickers(self):
        with open(self.TICKERS_FILE, 'r') as file:
            tickers = [line.strip().split(':')[0] for line in file]
        return tickers



async def main():
    config = Config()
    facade = streamingDataFacade(config)
    running = True

    def signal_handler(signum, frame):
        nonlocal running
        logger.info("Stopping data collection...")
        running = False

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        async for candles in facade.watch_multiple_ohlcv(
            exchange_name=config.EXCHANGE_NAME,
            tickers=config.load_tickers(),
            timeframes=config.TIMEFRAME
        ):
            if not running:
                logger.info("Initiating graceful shutdown...")
                await facade.cleanup()
                break
            print(candles)

    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())