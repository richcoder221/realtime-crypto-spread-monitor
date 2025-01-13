import json
import logging
from datetime import datetime, timezone
from confluent_kafka import Producer
from typing import Dict, Any

logger = logging.getLogger(__name__)

class KafkaProducerWrapper:
    def __init__(self, bootstrap_servers=['localhost:19092']):
        """Initialize Kafka producer with basic configuration"""
        try:
            conf = {
                'bootstrap.servers': ','.join(bootstrap_servers),
                'client.id': 'ohlcv-producer'
            }
            self.producer = Producer(conf)
            self.topic = 'ohlcv'
            logger.info(f'Initialized Kafka producer at {datetime.now(timezone.utc)}')
        except Exception as e:
            logger.error(f"Failed to initialize Kafka producer: {str(e)}")
            raise

    def delivery_callback(self, err, msg):
        if (err):
            logger.error(f'Message delivery failed: {err}')
        else:
            logger.debug(f'Message delivered to {msg.topic()}[{msg.partition()}] @ {msg.offset()}')

    def format_candle_message(self, symbol: str, timeframe: str, candle: list) -> Dict[str, Any]:
        """Format OHLCV data for QuestDB"""
        current_time = datetime.now(timezone.utc)
        formatted_time = current_time.strftime('%Y-%m-%dT%H:%M:%S')
        return {
            "symbol": symbol, 
            "timestamp": formatted_time,  # Will output like: 2024-01-15T10:30:45
            "open": float(candle[1]),
            "high": float(candle[2]),
            "low": float(candle[3]),
            "close": float(candle[4]),
            "volume": float(candle[5])
        }

  
    def send_ohlcv_data(self, candles: Dict[str, Dict[str, list]]):
        """Send OHLCV data to Kafka"""
        try:
            for symbol, timeframes in candles.items():
                # Sanitize symbol for use as table name
                table_name = symbol.replace('/', '_').replace(':', '_')
                for timeframe, ohlcv_data in timeframes.items():
                    for candle in ohlcv_data:
                        message = self.format_candle_message(symbol, timeframe, candle)
                        value = json.dumps(message).encode('utf-8')
                        self.producer.produce(
                            topic=self.topic,
                            value=value,
                            key=table_name.encode('utf-8')
                        )
            self.producer.flush()
            
        except Exception as e:
            logger.error(f"Error sending to Kafka: {str(e)}")
            raise

    def close(self):
        """Close the producer connection"""
        try:
            remaining = self.producer.flush(timeout=30)
            if remaining > 0:
                logger.warning(f"{remaining} messages still in queue during shutdown")
            logger.info("Kafka producer closed successfully")
        except Exception as e:
            logger.error(f"Error closing Kafka producer: {str(e)}")
