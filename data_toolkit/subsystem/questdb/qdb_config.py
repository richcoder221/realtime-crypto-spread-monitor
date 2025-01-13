import os

QUESTDB_URL = os.getenv('QUESTDB_URL', '127.0.0.1')
QUESTDB_CONNECTION_STRING = f'http::addr={QUESTDB_URL}:9000;'
#QUESTDB_CONNECTION_STRING = f'https::addr={QUESTDB_URL}:9000;tls_verify=unsafe_off;'

