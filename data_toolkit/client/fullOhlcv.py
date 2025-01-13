import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Now import using absolute import
from facade.importDataFacade import importDataFacade
import asyncio
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Config:

    EXCHANGE_NAME = 'bybit'
    TICKERS_FILE = 'tickers.txt'
    TIMEFRAME = ['4h', '1d']
    
    BYBIT_FOUNDING_DATE = '2023-01-01'

    SINCE = BYBIT_FOUNDING_DATE
    END = None

    def load_tickers(self):
        with open(self.TICKERS_FILE, 'r') as file:
            tickers = [line.strip() for line in file]
        return tickers 

def main():
    config = Config()
    facade = importDataFacade(config)
    
    try:
        asyncio.run(facade.import_ohlcv_data(
            exchange_name=config.EXCHANGE_NAME,
            tickers=config.load_tickers(),
            timeframes=config.TIMEFRAME,
            start_date=config.SINCE,
            end_date=config.END
        ))
    except KeyboardInterrupt:
        logger.info("Import interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")

if __name__ == "__main__":
    main()