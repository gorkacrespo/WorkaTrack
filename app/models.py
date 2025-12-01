"""
Modelos de base de datos para WorkaTrack.

Aquí definimos:
- El objeto 'db' de SQLAlchemy (el ORM que usaremos).
- El modelo User (usuarios de la app).
- El modelo Task (tareas/bloques del TFG o proyecto).
- El modelo WorkSession (sesiones de trabajo que registras).
"""

from datetime import date

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# --------------------------------------------------------------------
# Instancia global de SQLAlchemy
# --------------------------------------------------------------------
# 'db' será el objeto que se conecta a la base de datos y que usamos
# para definir las tablas (modelos) y hacer consultas.
#
# La app Flask lo inicializará en app/__init__.py con: db.init_app(app)
db = SQLAlchemy()


class User(db.Model):
    """
    Modelo de usuario.

    De momento es muy sencillo:
    - email: lo usaremos como login.
    - password_hash: guardamos el hash de la contraseña (no en texto plano).
    - nombre: opcional, para mostrarlo en la interfaz.
    - username: identificador público único dentro de WorkaTrack
    """

    __tablename__ = "users"  # Nombre de la tabla en la base de datos

    id = db.Column(db.Integer, primary_key=True)

    # NUEVO: nombre de usuario público y único (tipo GitHub, Instagram, etc.)
    # Lo usaremos más adelante para identificar al usuario en la interfaz y en la API.
    username = db.Column(db.String(80), unique=True, nullable=True)

    # Usamos email como identificador único de inicio de sesión
    email = db.Column(db.String(255), unique=True, nullable=False)

    # Nunca guardamos la contraseña en claro, solo su hash
    password_hash = db.Column(db.String(255), nullable=False)

    # Nombre del usuario (opcional)
    nombre = db.Column(db.String(255))

    # Relación: un usuario tiene muchas tareas
    # back_populates hace que user.tasks y task.user estén sincronizados
    tasks = db.relationship("Task", back_populates="user", cascade="all, delete-orphan")

    # ---------------- Métodos de ayuda para la contraseña ----------------

    def set_password(self, password: str) -> None:
        """
        Recibe la contraseña en texto plano, genera el hash
        y lo guarda en password_hash.
        """
        self.password_hash = generate_password_hash(password)
    def check_password(self, password: str) -> bool:
        """
        Comprueba si la contraseña dada coincide con el hash almacenado.
        Se usará al hacer login.
        """
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:
        # Representación útil para depuración/logs
        return f"<User id={self.id} email={self.email!r}>"


class Task(db.Model):
    """
    Modelo de tarea del TFG / proyecto.

    Cada Task representa un bloque de trabajo:
    - "1.1 Introducción"
    - "2.1 Estado del arte"
    - "Diseño de la API"
    etc.

    Estas tareas luego se usarán para tu diagrama de Gantt y estadísticas.
    """

    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)

    # Usuario dueño de la tarea (relación con User)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Datos principales de la tarea
    titulo = db.Column(db.String(255), nullable=False)   # Ej: "1.1 Introducción"
    descripcion = db.Column(db.Text)                     # Detalles opcionales

    # Clasificación de la tarea (teoría, desarrollo, investigación, etc.)
    # Ejemplos de valores: "redaccion_teorica", "desarrollo_app", "investigacion"
    categoria = db.Column(db.String(100))

    # Estado de la tarea: 'pendiente', 'en_progreso' o 'terminada'
    estado = db.Column(db.String(50), nullable=False, default="pendiente")

    # Fechas planificadas de inicio y fin (para el Gantt planificado)
    fecha_plan_inicio = db.Column(db.Date)
    fecha_plan_fin = db.Column(db.Date)

    # Horas estimadas para completar la tarea (ej: 12.5 horas)
    horas_estimadas = db.Column(db.Numeric(6, 2))

    # Relación inversa con User (user.tasks)
    user = db.relationship("User", back_populates="tasks")

    # Relación: una tarea tiene muchas sesiones de trabajo
    work_sessions = db.relationship(
        "WorkSession",
        back_populates="tarea",
        cascade="all, delete-orphan",
        order_by="WorkSession.fecha",
    )

    # ---------------- Propiedades de ayuda ----------------

    @property
    def minutos_totales(self) -> int:
        """
        Suma y devuelve todos los minutos trabajados en esta tarea,
        usando las WorkSessions asociadas.
        """
        return sum(ws.minutos for ws in (self.work_sessions or []))

    @property
    def horas_totales(self) -> float:
        """
        Devuelve el total de horas trabajadas (minutos_totales / 60).
        """
        return self.minutos_totales / 60.0

    def __repr__(self) -> str:
        return f"<Task id={self.id} titulo={self.titulo!r}>"


class WorkSession(db.Model):
    """
    Modelo de sesión de trabajo.

    Cada vez que te sientas a trabajar en una tarea,
    crearás una WorkSession:

    - Para qué tarea es.
    - Qué día has trabajado.
    - Cuántos minutos.
    - Qué tipo de trabajo (lectura, escritura, código...).
    - Notas sobre lo que has hecho.
    """

    __tablename__ = "work_sessions"

    id = db.Column(db.Integer, primary_key=True)

    # A qué tarea pertenece esta sesión (relación con Task)
    tarea_id = db.Column(
        db.Integer,
        db.ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Fecha de la sesión (por defecto, el día de hoy)
    fecha = db.Column(db.Date, nullable=False, default=date.today)

    # Duración en minutos (más fácil de sumar y procesar)
    minutos = db.Column(db.Integer, nullable=False)

    # Tipo de trabajo realizado: 'lectura', 'escritura', 'codigo', 'revision', etc.
    tipo = db.Column(db.String(100))

    # Notas libres: qué has hecho exactamente en esta sesión
    notas = db.Column(db.Text)

    # Relación inversa con Task (task.work_sessions)
    tarea = db.relationship("Task", back_populates="work_sessions")

    def __repr__(self) -> str:
        return (
            f"<WorkSession id={self.id} tarea_id={self.tarea_id} "
            f"fecha={self.fecha} minutos={self.minutos}>"
        )
