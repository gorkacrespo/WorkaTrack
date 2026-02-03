"""
Servicios relacionados con proyectos (Project).
"""

from typing import Optional
from datetime import date
from app.models import db, Project, User
from werkzeug.security import generate_password_hash, check_password_hash


def create_project(
    user_id: int,
    name: str,
    description: Optional[str] = None,
    priority: Optional[str] = None,
    category: Optional[str] = None,
    color: Optional[str] = None,
    minutos_estimados: Optional[int] = None,
    fecha_inicio: Optional[date] = None,
    fecha_fin_prevista: Optional[date] = None,
    password: Optional[str] = None,
) -> Project:
    """
    Crea un nuevo proyecto para un usuario.
    """

    user = User.query.get(user_id)
    if user is None:
        raise ValueError("Usuario no encontrado")

    project = Project(
        user_id=user_id,
        name=name,
        description=description,
        priority=priority,
        category=category,
        color=color or "#2563eb",
        minutos_estimados=minutos_estimados,
        fecha_inicio=fecha_inicio,
        fecha_fin_prevista=fecha_fin_prevista,
    )
    if password:
        project.password_hash = generate_password_hash(password)
    db.session.add(project)
    db.session.commit()

    return project


def get_projects_by_user(user_id: int):
    """
    Devuelve todos los proyectos de un usuario.
    """
    return (
        Project.query
        .filter_by(user_id=user_id)
        .order_by(Project.created_at.asc(), Project.id.asc())
        .all()
    )


def get_project_by_id(project_id: int, user_id: int) -> Project:
    """
    Devuelve un proyecto concreto del usuario.
    """
    project = Project.query.get(project_id)

    if project is None or project.user_id != user_id:
        raise ValueError("Proyecto no encontrado")

    return project


def delete_project(project_id: int, user_id: int, password: Optional[str] = None) -> None:
    """
    Elimina un proyecto del usuario.
    """
    project = Project.query.get(project_id)

    if project is None or project.user_id != user_id:
        raise ValueError("Proyecto no encontrado")

    if project.password_hash:
        if not password or not check_password_hash(project.password_hash, password):
            raise ValueError("Contraseña incorrecta")

    db.session.delete(project)
    db.session.commit()
