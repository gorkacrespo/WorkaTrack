"""
Servicios de estadísticas de proyectos.
Este módulo se encarga de calcular métricas reales de un proyecto
a partir de sus tareas y sesiones de trabajo.
Reglas:
- El progreso NO se guarda como verdad en Project.progress.
- Se calcula dinámicamente a partir de:
    - minutos_estimados (Task)
    - minutos reales (WorkSession)
"""
from sqlalchemy import func
from app.models import db, Project, Task, WorkSession


def get_project_time_stats(project_id: int, user_id: int) -> dict:
    """
    Devuelve estadísticas reales de tiempo de un proyecto.
    Calcula:
    - minutos_estimados: suma de minutos_estimados de las tareas del proyecto
    - minutos_reales: suma de minutos reales de las sesiones finalizadas del proyecto
    - progreso: porcentaje (0..100) basado en estimado vs real
    Solo se tienen en cuenta:
    - Tareas del proyecto indicado
    - Tareas pertenecientes al usuario indicado
    """
    # Comprobamos que el proyecto exista y pertenezca al usuario
    project = Project.query.filter_by(id=project_id, user_id=user_id).first()
    if project is None:
        raise ValueError("Proyecto no encontrado o no autorizado")
    # Minutos estimados (solo tareas con estimación)
    minutos_estimados = (
        db.session.query(func.coalesce(func.sum(Task.minutos_estimados), 0))
        .filter(
            Task.project_id == project_id,
            Task.user_id == user_id,
            Task.minutos_estimados.isnot(None),
        )
        .scalar()
        or 0
    )
    # Minutos reales: suma directa de sesiones finalizadas de todas las tareas
    # del proyecto. Se consulta WorkSession directamente para evitar el doble
    # conteo que produce la agregación recursiva de task_time_service.
    task_ids = db.session.query(Task.id).filter(
        Task.project_id == project_id,
        Task.user_id == user_id,
    )
    minutos_reales = (
        db.session.query(func.coalesce(func.sum(WorkSession.minutos), 0))
        .filter(
            WorkSession.tarea_id.in_(task_ids),
            WorkSession.finalizada.is_(True),
        )
        .scalar()
        or 0
    )
    # Cálculo del progreso
    if minutos_estimados > 0:
        progreso = int(min(100, round((minutos_reales / minutos_estimados) * 100)))
    else:
        progreso = 0
    return {
        "project_id": project_id,
        "minutos_estimados": int(minutos_estimados),
        "minutos_reales": int(minutos_reales),
        "progreso": progreso,
    }
