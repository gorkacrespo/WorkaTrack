"""
Inicialización de la aplicación Flask de WorkaTrack.

Aquí definimos la función create_app, que:
- Crea la instancia de Flask.
- Carga la configuración desde Config (config.py).
- Inicializa la base de datos (SQLAlchemy).
- (Más adelante) registrará blueprints, extensiones, etc.
"""

from flask import Flask
from flask_migrate import Migrate
from config import Config          # Clase de configuración (config.py)
from app.models import db          # Objeto SQLAlchemy definido en models.py
from app.routes import api_bp




def create_app(config_class: type[Config] = Config) -> Flask:
    """
    Factoría de aplicación.

    Esta función crea y configura la instancia de Flask.
    La usamos así para que sea fácil integrarla con:
    - tests
    - Docker
    - Gunicorn
    - Kubernetes
    """
    app = Flask(__name__)

    # Cargamos la configuración desde la clase Config
    app.config.from_object(config_class)

    # Inicializamos la extensión de base de datos con esta app
    db.init_app(app)
    migrate = Migrate(app,db)    #Inicializar migraciones
    app.register_blueprint(api_bp)   #Registrar el blueprint de la API
    # Importamos modelos (por si alguna herramienta de migraciones los necesita)
    # La importación es local para evitar problemas de importaciones circulares.
    from app import models  # noqa: F401  (se importa solo por los efectos secundarios)

    # ------------------------------------------------------------------
    # Ruta mínima de prueba (la quitaremos cuando tengamos vistas reales)
    # ------------------------------------------------------------------
    @app.route("/")
    def index():
        return "WorkaTrack está funcionando"

    return app
