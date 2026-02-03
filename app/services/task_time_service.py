from sqlalchemy import func, and_
from sqlalchemy.sql import text

from app.models import db, Task, WorkSession


def get_tasks_with_time(user_id: int):
    """
    Devuelve las tareas del usuario con tiempo real calculado
    a partir de sus sesiones.

    - No falla aunque no haya sesiones
    - Compatible con project_id NULL o definido
    - Evita errores de GROUP BY
    """

    # Subquery: minutos reales por tarea
    minutos_por_tarea = (
        db.session.query(
            WorkSession.tarea_id.label("tarea_id"),
            func.coalesce(func.sum(WorkSession.minutos), 0).label("total_minutos"),
        )
        .filter(
            WorkSession.finalizada.is_(True)
        )
        .group_by(WorkSession.tarea_id)
        .subquery()
    )

    # Query principal: tareas + minutos reales
    results = (
        db.session.query(
            Task,
            func.coalesce(minutos_por_tarea.c.total_minutos, 0).label("minutos_reales"),
        )
        .outerjoin(
            minutos_por_tarea,
            minutos_por_tarea.c.tarea_id == Task.id,
        )
        .filter(Task.user_id == user_id)
        .order_by(Task.id.asc())
        .all()
    )

    tasks_data = []

    for task, minutos_reales in results:
        tasks_data.append(
            {
                "id": task.id,
                "titulo": task.titulo,
                "descripcion": task.descripcion,
                "categoria": task.categoria,
                "estado": task.estado,
                "project_id": task.project_id,
                "parent_task_id": task.parent_task_id,
                "fecha_plan_inicio": (
                    task.fecha_plan_inicio.isoformat()
                    if task.fecha_plan_inicio
                    else None
                ),
                "fecha_plan_fin": (
                    task.fecha_plan_fin.isoformat()
                    if task.fecha_plan_fin
                    else None
                ),
                "minutos_estimados": task.minutos_estimados,
                "minutos_reales": int(minutos_reales),
                "color": task.color,
            }
        )
    return tasks_data

def get_task_time_stats(task_id: int, user_id: int):
    """
    Devuelve estadísticas de UNA tarea:
    - minutos_estimados (Task.minutos_estimados)
    - minutos_reales (suma de WorkSession.minutos SOLO finalizadas)
    - progreso (%) con base en estimado (capado a 100)
    """

    task = (
            db.session.query(Task)
            .filter(Task.id == task_id, Task.user_id == user_id)
            .first()
            )

    if not task:
        raise ValueError("Tarea no encontrada")

    minutos_estimados = int(task.minutos_estimados or 0)

    minutos_reales = (
            db.session.query(func.coalesce(func.sum(WorkSession.minutos), 0))
            .filter(
                WorkSession.tarea_id == task.id,
                WorkSession.finalizada.is_(True),
                )
            .scalar()
            )

    minutos_reales = int(minutos_reales or 0)

    progreso = 0
    if minutos_estimados > 0:
        progreso = int(round((minutos_reales / minutos_estimados) * 100))
        progreso = min(progreso, 100)

    return {
            "task_id": task.id,
            "minutos_estimados": minutos_estimados,
            "minutos_reales": minutos_reales,
            "progreso": progreso,
            }

