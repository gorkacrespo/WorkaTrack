# Imagen base: Python 3.12 ligera
FROM python:3.12-slim

# Evitar que Python genere .pyc y buffer de stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# ---------------------------------------------------------
# Instalar dependencias del sistema que podrían necesitarse
# (psycopg2, etc.)
# ---------------------------------------------------------
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    git \
 && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------
# Copiar requirements e instalar dependencias de Python
# ---------------------------------------------------------
COPY requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

# ---------------------------------------------------------
# Copiar el código de la aplicación al contenedor
# ---------------------------------------------------------
COPY app /app/app
COPY config.py /app/config.py
# Copiar las migraciones de Alembic (Flask-Migrate)
COPY migrations /app/migrations

# ---------------------------------------------------------
# Variables de entorno para Flask dentro del contenedor
# ---------------------------------------------------------
ENV FLASK_APP="app:create_app"
ENV FLASK_RUN_HOST=0.0.0.0

# Puerto interno donde escuchará Flask
EXPOSE 5000

# ---------------------------------------------------------
# Comando por defecto: arrancar la app Flask
# (en modo desarrollo; ya pasaremos a gunicorn si queremos
# algo más “producción”)
# ---------------------------------------------------------
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
