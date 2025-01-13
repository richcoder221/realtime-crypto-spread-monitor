# Realtime Crypto Spread Monitor
A real-time monitoring dashboard for cryptocurrency spot and perpetual price spreads.

## Technology Stack
- **Data Source**: CCXT Pro for cryptocurrency exchange WebSocket
- **Message Queue**: Apache Kafka with Redpanda for high-performance streaming
- **Database**: QuestDB for time-series data storage
- **Visualization**: Grafana for real-time dashboards
- **Containerization**: Docker and Docker Compose

## Data Flow
```
CCXT Pro Websocket → Kafka Connector → Redpanda → Kafka Connector → QuestDB → Grafana
```

## Prerequisites

### System Requirements
1. Install Java:
```bash
sudo apt install default-jdk
```

2. Install Python 3:
```bash
sudo apt install python3 python3-pip
```

3. Setup and Activate Python Environment in the data_toolkit folder:
```bash
./setup.sh
source ./venv/bin/activate
```

## Installation & Setup

1. Start the Infrastructure:
```bash
docker compose up -d
```

2. Start Kafka Connector:
```bash
cd kafka
./bin/connect-standalone.sh config/connect-standalone.properties config/questdb-connector.properties
```

3. Start Data Collection:
```bash
python watchOhlcvPerp.py   # For perpetual futures data
python watchOhlcvSpot.py   # For spot market data
```

## Grafana Dashboard Setup

1. Access Grafana:
   - URL: http://localhost:3000
   - Default credentials:
     - Username: admin
     - Password: quest

2. Configure QuestDB Data Source:
   - Go to: Connections -> Data Sources -> QuestDB -> Add new data source
   - Settings:
     - Server address: questdb
     - Port: 8812
     - Username: admin
     - Password: quest
     - TLS/SSL Mode: disable

3. Import Dashboard:
   - Import the provided JSON dashboard file (dashboard.json)
   - For each panel: Top right corner -> Press edit to refresh query -> Save to enable real-time data streaming

## Additional Features

### Historical Data Management
- `fullOhlcv.py`: Import historical OHLCV data via REST API
- `ohlcvToCsv.py`: Export data to CSV format


