"""
Modelos de base de datos para WorkaTrack.

Aquí definimos:
- El objeto 'db' de SQLAlchemy (el ORM que usaremos).
- El modelo User (usuarios de la app).
- El modelo Project (proyectos del usuario).
- El modelo Task (tareas).
- El modelo Milestone (hitos).
- El modelo WorkSession (sesiones de trabajo).
"""

from datetime import date, datetime

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# --------------------------------------------------------------------
# Instancia global de SQLAlchemy
# --------------------------------------------------------------------
db = SQLAlchemy()


class User(db.Model):
    """
    Modelo de usuario.
    """

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    # Nombre de usuario público y único
    username = db.Column(db.String(80), unique=True, nullable=True)

    # Usamos email como identificador único de inicio de sesión
    email = db.Column(db.String(255), unique=True, nullable=False)

    # Nunca guardamos la contraseña en claro, solo su hash
    password_hash = db.Column(db.String(255), nullable=False)

    # Nombre del usuario (opcional)
    nombre = db.Column(db.String(255))

    # Relación: un usuario tiene muchos proyectos
    projects = db.relationship(
        "Project",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="Project.id",
    )

    # Relación: un usuario tiene muchas tareas
    tasks = db.relationship(
        "Task",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="Task.id",
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"


class Project(db.Model):
    """
    Modelo de proyecto.
    """

    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)

    # Fechas del proyecto
    fecha_inicio = db.Column(db.Date, nullable=True)
    fecha_fin_prevista = db.Column(db.Date, nullable=True)

    # Tiempo estimado total del proyecto (minutos)
    minutos_estimados = db.Column(db.Integer, nullable=True)

    # Contraseña del proyecto (hash)
    password_hash = db.Column(db.String(255), nullable=True)

    # Dueño del proyecto
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Datos principales
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)

    # Campos que ya usa tu frontend
    priority = db.Column(db.String(50), nullable=True)   # "baja" | "media" | "alta"
    category = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.Date, nullable=False, default=date.today)
    progress = db.Column(db.Integer, nullable=False, default=0)  # 0..100
    color = db.Column(db.String(20), nullable=False, default="#2563eb")

    # Relación inversa
    user = db.relationship("User", back_populates="projects")

    # Relación: un proyecto tiene muchos hitos
    milestones = db.relationship(
        "Milestone",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="Milestone.fecha",
    )

    def __repr__(self) -> str:
        return f"<Project id={self.id} name={self.name!r} user_id={self.user_id}>"


class Task(db.Model):
    """
    Modelo de tarea.
    """

    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)

    # Usuario dueño de la tarea
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Proyecto al que pertenece la tarea (relación REAL)
    project_id = db.Column(
        db.Integer,
        db.ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,  # ← IMPORTANTE: nullable por compatibilidad inicial
    )

    # Jerarquía: tarea padre (nullable). Si se borra el padre, las hijas se quedan sin padre.
    parent_task_id = db.Column(
        db.Integer,
        db.ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )


    # Datos principales de la tarea
    titulo = db.Column(db.String(255), nullable=False)
    descripcion = db.Column(db.Text)

    # Clasificación / vínculo lógico con proyecto (por ahora)
    categoria = db.Column(db.String(100))

    # Estado de la tarea
    estado = db.Column(db.String(50), nullable=False, default="pendiente")
    color = db.Column(db.String(20), nullable=False)

    # Fechas planificadas
    fecha_plan_inicio = db.Column(db.Date)
    fecha_plan_fin = db.Column(db.Date)

    # Tiempo estimado en minutos (fuente de verdad)
    minutos_estimados = db.Column(db.Integer)

    # Relación inversa con User
    user = db.relationship("User", back_populates="tasks")
    project = db.relationship("Project")

    # Relación jerárquica (self-referential)
    parent_task = db.relationship(
        "Task",
        remote_side=[id],
        back_populates="child_tasks",
    )

    child_tasks = db.relationship(
        "Task",
        back_populates="parent_task",
    )

    # Relación: una tarea tiene muchas sesiones
    work_sessions = db.relationship(
        "WorkSession",
        back_populates="tarea",
        cascade="all, delete-orphan",
        order_by="WorkSession.fecha",
    )

    @property
    def minutos_totales(self) -> int:
        return sum(ws.minutos for ws in (self.work_sessions or []))

    @property
    def horas_totales(self) -> float:
        return self.minutos_totales / 60.0

    def __repr__(self) -> str:
        return f"<Task id={self.id} titulo={self.titulo!r}>"


class Milestone(db.Model):
    """
    Modelo de hito de proyecto.
    """

    __tablename__ = "milestones"

    id = db.Column(db.Integer, primary_key=True)

    project_id = db.Column(
        db.Integer,
        db.ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )

    titulo = db.Column(db.String(255), nullable=False)
    descripcion = db.Column(db.Text)

    # Fecha clave del hito
    fecha = db.Column(db.Date, nullable=False)

    # Tipo de hito: reunion, entrega, presentacion, etc.
    tipo = db.Column(db.String(50))

    # Color opcional para UI
    color = db.Column(db.String(20))

    project = db.relationship("Project", back_populates="milestones")

    def __repr__(self) -> str:
        return f"<Milestone id={self.id} titulo={self.titulo!r} fecha={self.fecha}>"


class WorkSession(db.Model):
    """
    Modelo de sesión de trabajo.
    """

    __tablename__ = "work_sessions"

    id = db.Column(db.Integer, primary_key=True)

    tarea_id = db.Column(
        db.Integer,
        db.ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
    )

    fecha = db.Column(db.Date, nullable=False, default=date.today)

    minutos = db.Column(db.Integer, nullable=False)

    tipo = db.Column(db.String(100))

    notas = db.Column(db.Text)

    finalizada = db.Column(db.Boolean, nullable=False, default=False)

    tarea = db.relationship("Task", back_populates="work_sessions")

    def __repr__(self) -> str:
        return (
            f"<WorkSession id={self.id} tarea_id={self.tarea_id} "
            f"fecha={self.fecha} minutos={self.minutos}>"
        )
