"""
Configuración principal de la aplicación WorkaTrack.

Este archivo define las variables que Flask necesita:
- SECRET_KEY: clave para sesiones y seguridad.
- SQLALCHEMY_DATABASE_URI: ruta de conexión a la base de datos.
- SQLALCHEMY_TRACK_MODIFICATIONS: desactivada para evitar warnings.

Más adelante, Docker y Kubernetes podrán sobreescribir estos valores
mediante variables de entorno.
"""

import os

# Carpeta base del proyecto (donde está este archivo)
BASEDIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # -----------------------------------------------------
    # Clave secreta de Flask
    # -----------------------------------------------------
    # Se usa para gestionar sesiones, cookies seguras,
    # proteger formularios, etc.
    # En producción NUNCA debe ser fija: usaremos variables
    # de entorno o secretos de Kubernetes.
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")

    # -----------------------------------------------------
    # Configuración de la base de datos (SQLAlchemy)
    # -----------------------------------------------------
    # Variable de entorno recomendada: DATABASE_URL
    #   Ejemplo PostgreSQL:
    #   postgresql+psycopg2://usuario:password@host:5432/workatrack
    #
    # Si no hay DATABASE_URL, usamos una base de datos SQLite local
    # llamada 'workatrack.db' en la carpeta del proyecto.
    # -----------------------------------------------------
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(BASEDIR, "workatrack.db"),
    )

    # Desactiva el sistema de seguimiento de cambios de SQLAlchemy
    # (consume memoria y no lo necesitamos).
    SQLALCHEMY_TRACK_MODIFICATIONS = False
