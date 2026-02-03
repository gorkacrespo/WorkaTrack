"""
Servicios relacionados con hitos de proyecto (Milestone).
"""

from datetime import date
from typing import Optional, List

from app.models import db, Milestone, Project


def create_milestone(
    project_id: int,
    titulo: str,
    fecha: date,
    descripcion: Optional[str] = None,
    tipo: Optional[str] = None,
    color: Optional[str] = None,
) -> Milestone:
    """
    Crea un nuevo hito para un proyecto.
    """

    project = Project.query.get(project_id)
    if project is None:
        raise ValueError("Proyecto no encontrado")
    project = Project.query.get(project_id)
    if project is None:
        raise ValueError("Proyecto no encontrado")

    if project.fecha_inicio and fecha < project.fecha_inicio:
        raise ValueError(
             "No se puede crear un hito antes de la fecha de inicio del proyecto"
        )


    milestone = Milestone(
        project_id=project_id,
        titulo=titulo,
        descripcion=descripcion,
        fecha=fecha,
        tipo=tipo,
        color=color,
    )

    db.session.add(milestone)
    db.session.commit()

    return milestone


def get_milestones_by_project(project_id: int) -> List[Milestone]:
    """
    Devuelve todos los hitos de un proyecto ordenados por fecha.
    """

    project = Project.query.get(project_id)
    if project is None:
        raise ValueError("Proyecto no encontrado")

    return (
        Milestone.query
        .filter_by(project_id=project_id)
        .order_by(Milestone.fecha.asc(), Milestone.id.asc())
        .all()
    )


def update_milestone(
    milestone_id: int,
    titulo: Optional[str] = None,
    descripcion: Optional[str] = None,
    fecha: Optional[date] = None,
    tipo: Optional[str] = None,
    color: Optional[str] = None,
) -> Milestone:
    """
    Actualiza un hito existente.
    """

    milestone = Milestone.query.get(milestone_id)
    if milestone is None:
        raise ValueError("Hito no encontrado")

    if titulo is not None:
        milestone.titulo = titulo

    if descripcion is not None:
        milestone.descripcion = descripcion

    if fecha is not None:
        milestone.fecha = fecha

    if tipo is not None:
        milestone.tipo = tipo

    if color is not None:
        milestone.color = color

    db.session.commit()

    return milestone


def delete_milestone(milestone_id: int) -> None:
    """
    Elimina un hito.
    """

    milestone = Milestone.query.get(milestone_id)
    if milestone is None:
        raise ValueError("Hito no encontrado")

    db.session.delete(milestone)
    db.session.commit()
