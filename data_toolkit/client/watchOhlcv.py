import sys
import os
import signal
import logging
import asyncio
from typing import List

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from facade.streamingDataFacade import streamingDataFacade

logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Config:
    def __init__(self, market_type: str = 'spot'):
        self.EXCHANGE_NAME = 'bybit'
        self.TICKERS_FILE = 'tickers.txt'
        self.TIMEFRAME = ['1m']
        self.MARKET_TYPE = market_type  # 'spot' or 'perp'

    def load_tickers(self) -> List[str]:
        with open(self.TICKERS_FILE, 'r') as file:
            if self.MARKET_TYPE == 'spot':
                return [line.strip().split(':')[0] for line in file]
            return [line.strip() for line in file]

async def main(market_type: str):
    config = Config(market_type)
    facade = streamingDataFacade(config)
    running = True

    def signal_handler(signum, frame):
        nonlocal running
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
                await facade.cleanup()
                break
            print(candles)
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")

if __name__ == "__main__":
    market_type = sys.argv[1] if len(sys.argv) > 1 else 'spot'
    asyncio.run(main(market_type))
