from questdb.ingress import Sender, IngressError
import pandas as pd
from tqdm import tqdm
import logging
from .qdb_config import *

logger = logging.getLogger(__name__)

class qdbInterface:
    def __init__(self):
        """Initialize QuestDB interface with its own config"""
        self.qdb_connection_string = QUESTDB_CONNECTION_STRING



    async def df_to_qdb(self, df, table_name, symbols, at):
        try:
            with Sender.from_conf(self.qdb_connection_string) as sender:
                sender.dataframe(
                    df,
                    table_name=table_name,
                    symbols=symbols,
                    at=at)
            return True
        except IngressError as e:
            tqdm.write(f"\033[91mQuestDB Error when inserting {symbols}: {e}\033[0m")
            return False

    async def dump_ohlcv(self, ohlcv_table_name, ohlcv, ticker, time, exchange_name):
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
        df['ticker'] = ticker
        df['interval'] = time
        df['exchange'] = exchange_name
        
        success = await self.df_to_qdb(df, ohlcv_table_name, ['ticker', 'interval', 'exchange'], 'timestamp') 
        
        if success:
            tqdm.write(f"\033[92mSuccessfully inserted data into {ohlcv_table_name}\033[0m")
        return success