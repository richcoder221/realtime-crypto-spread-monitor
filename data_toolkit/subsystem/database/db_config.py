import os
from typing import List, Tuple
from pathlib import Path

# Database connection settings
DB_HOST = os.getenv('QDB_HOST', '127.0.0.1')
DB_PORT = int(os.getenv('QDB_PORT', '8812'))
DB_USER = os.getenv('QDB_USER', 'admin')  # Default fallback, should be configured in environment
DB_PASS = os.getenv('QDB_PASS', 'quest')  # Default fallback, should be configured in environment
DB_NAME = os.getenv('QDB_NAME', 'qdb')

# SSL settings for PostgreSQL
#PG_SSL_MODE = 'require'  # Require SSL but don't verify certificates
#PG_SSL_MIN_PROTOCOL_VERSION = 'TLSv1.3'  # Updated to TLS 1.3 for better security

PG_APPLICATION_NAME = 'qdb_to_qlib'

# Connection pool settings
POOL_MIN_SIZE = 5
POOL_MAX_SIZE = 10
POOL_MAX_QUERIES = 50000
POOL_TIMEOUT = 300
STATEMENT_CACHE_SIZE = 1000
MAX_INACTIVE_CONNECTION_LIFETIME = 300.0

# Query settings
CURSOR_PREFETCH = 5000  # Number of rows to prefetch in cursor
BATCH_SIZE = 25000     # Number of records to process in each batch
BATCH_TIMEOUT = 60     # Timeout for batch operations in seconds

MAX_RETRIES = 3
RETRY_DELAY = 1

