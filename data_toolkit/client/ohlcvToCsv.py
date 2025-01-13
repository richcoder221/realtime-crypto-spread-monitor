import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from facade.exportDataFacade import exportDataFacade
import asyncio
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Config:
    # Database settings inherited from subsystem config
    
    # Export settings
    EXCHANGE_NAME = 'bybit'
    TICKERS_FILE = 'tickers.txt'
    TIMEFRAME = ['4h', '1d']
    
    START_DATE = '2023-01-01'
    END_DATE = '2024-12-31'
    
    # Output directory in home directory
    OUTPUT_DIR = str(Path.home() / "exported_data")
    
    def load_tickers(self):
        with open(self.TICKERS_FILE, 'r') as file:
            tickers = [line.strip() for line in file]
        return tickers 


def main():
    config = Config()
    facade = exportDataFacade(config)
    
    try:
        asyncio.run(facade.export_ohlcv_data(
            exchange_name=config.EXCHANGE_NAME,
            tickers=config.load_tickers(),
            timeframes=config.TIMEFRAME,
            start_date=config.START_DATE,
            end_date=config.END_DATE,
            output_dir=config.OUTPUT_DIR
        ))
    except KeyboardInterrupt:
        logger.info("Export interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")

if __name__ == "__main__":
    main() 