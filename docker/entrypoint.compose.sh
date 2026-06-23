#!/bin/sh
set -eu

echo "[workatrack] esperando a PostgreSQL..."

python - <<'PY'
import os
import time
import psycopg2
from sqlalchemy.engine import make_url

raw_url = os.environ["DATABASE_URL"]
url = make_url(raw_url)
last_error = None

for _ in range(60):
    try:
        conn = psycopg2.connect(
            dbname=url.database,
            user=url.username,
            password=url.password,
            host=url.host or "db",
            port=url.port or 5432,
        )
        conn.close()
        print("[workatrack] PostgreSQL disponible")
        break
    except Exception as e:
        last_error = e
        time.sleep(2)
else:
    raise SystemExit(f"[workatrack] no se pudo conectar a PostgreSQL: {last_error}")
PY

echo "[workatrack] aplicando migraciones..."
flask db upgrade

echo "[workatrack] arrancando API..."
exec flask run --host=0.0.0.0 --port=5000
