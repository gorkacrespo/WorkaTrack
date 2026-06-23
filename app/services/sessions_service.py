"""
Servicios relacionados con sesiones de trabajo (WorkSession).
"""

from datetime import date, datetime
from typing import Optional
from werkzeug.security import check_password_hash

from app.models import db, Task, WorkSession, Project


def get_sessions_by_user(user_id: int):
    """
    Devuelve todas las sesiones de trabajo del usuario.
    """
    return (
        db.session.query(WorkSession)
        .join(Task, Task.id == WorkSession.tarea_id)
        .filter(Task.user_id == user_id)
        .order_by(WorkSession.fecha.asc(), WorkSession.id.asc())
        .all()
    )


def create_session(
    tarea_id: int,
    fecha: Optional[date],
    minutos: int,
    tipo: Optional[str] = None,
    notas: Optional[str] = None,
    started_at: Optional[datetime] = None,
    ended_at: Optional[datetime] = None,
) -> WorkSession:
    """
    Crea una nueva sesión de trabajo para una tarea.
    """
    task = Task.query.get(tarea_id)
    if task is None:
        raise ValueError("Tarea no encontrada")
    if task.project_id is None:
        raise ValueError("La tarea no pertenece a ningún proyecto")

    project = Project.query.get(task.project_id)
    if project is None:
        raise ValueError("Proyecto no encontrado")

    if minutos < 0:
        raise ValueError("Los minutos no pueden ser negativos")

    if fecha:
        fecha_to_store = fecha
    else:
        fecha_to_store = task.fecha_plan_inicio or date.today()

    if task.fecha_plan_inicio and fecha_to_store < task.fecha_plan_inicio:
        raise ValueError(
            "No se puede crear una sesión antes de la fecha de inicio de la tarea"
        )

    ws = WorkSession(
        tarea_id=tarea_id,
        fecha=fecha_to_store,
        minutos=minutos if minutos > 0 else 0,
        tipo=tipo,
        notas=notas,
        finalizada=True if minutos > 0 else False,
        started_at=started_at,
        ended_at=ended_at,
    )

    db.session.add(ws)
    db.session.commit()
    return ws


def update_session(
    session_id: int,
    user_id: int,
    tarea_id: int,
    fecha: Optional[date],
    minutos: int,
    tipo: Optional[str] = None,
    notas: Optional[str] = None,
    started_at: Optional[datetime] = None,
    ended_at: Optional[datetime] = None,
) -> WorkSession:
    """
    Actualiza una sesión existente.
    """
    ws = WorkSession.query.get(session_id)
    if ws is None:
        raise ValueError("Sesión no encontrada")

    task = Task.query.get(ws.tarea_id)
    if task is None or task.user_id != user_id:
        raise ValueError("No autorizado para modificar esta sesión")

    if minutos < 0:
        raise ValueError("Los minutos no pueden ser negativos")

    ws.tarea_id = tarea_id
    ws.fecha = fecha or ws.fecha
    ws.tipo = tipo
    ws.notas = notas

    ws.started_at = started_at
    ws.ended_at = ended_at

    if minutos > 0:
        ws.minutos = minutos
        ws.finalizada = True
    else:
        ws.minutos = 0
        ws.finalizada = False

    db.session.commit()
    return ws


def delete_session(session_id: int, user_id: int, password: Optional[str]) -> None:
    """
    Elimina una sesión.
    Requiere SIEMPRE contraseña del proyecto.
    """

    ws = WorkSession.query.get(session_id)
    if ws is None:
        raise ValueError("Sesión no encontrada")

    task = Task.query.filter_by(id=ws.tarea_id, user_id=user_id).first()
    if task is None:
        raise ValueError("No autorizado para eliminar esta sesión")

    if task.project_id is None:
        raise ValueError("Sesión sin proyecto asociado")

    project = Project.query.get(task.project_id)
    if project is None:
        raise ValueError("Proyecto no encontrado")

    if not password or not check_password_hash(project.password_hash, password):
        raise ValueError("Contraseña incorrecta")

    db.session.delete(ws)
    db.session.commit()
