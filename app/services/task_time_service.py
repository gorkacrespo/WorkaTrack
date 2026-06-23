from sqlalchemy import func, and_
from sqlalchemy.sql import text
from app.models import db, Task, WorkSession


def _build_subtree_minutes(direct_minutes: dict, children_map: dict, task_id: int, _visited=None) -> int:
    """
    Suma recursiva del tiempo real de una tarea y de todas sus descendientes.
    - direct_minutes: {task_id: minutos_reales_directos de esa tarea}
    - children_map: {parent_task_id: [child_id, ...]}
    El guard _visited evita recursión infinita ante datos con ciclos.
    """
    if _visited is None:
        _visited = set()
    if task_id in _visited:
        return 0
    _visited.add(task_id)

    total = direct_minutes.get(task_id, 0)
    for child_id in children_map.get(task_id, []):
        total += _build_subtree_minutes(direct_minutes, children_map, child_id, _visited)
    return total


def get_tasks_with_time(user_id: int):
    """
    Devuelve las tareas del usuario con tiempo real calculado
    a partir de sus sesiones.
    - No falla aunque no haya sesiones
    - Compatible con project_id NULL o definido
    - Evita errores de GROUP BY
    - El tiempo real de una tarea incluye el de todas sus subtareas (agregación recursiva)
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

    # Mapas para agregar en la tarea padre el tiempo real de sus subtareas.
    # direct_minutes guarda el tiempo directo de cada tarea (solo sus propias sesiones).
    # children_map relaciona cada tarea padre con sus hijas directas.
    direct_minutes = {task.id: int(minutos_reales) for task, minutos_reales in results}
    children_map = {}
    for task, _minutos in results:
        children_map.setdefault(task.parent_task_id, []).append(task.id)

    tasks_data = []
    for task, _minutos in results:
        minutos_reales_agregados = _build_subtree_minutes(
            direct_minutes, children_map, task.id
        )
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
                "minutos_reales": int(minutos_reales_agregados),
                "color": task.color,
            }
        )
    return tasks_data


def _collect_subtree_ids(task_id: int, user_id: int, _visited=None) -> list:
    """
    Devuelve el id de la tarea más los de todas sus descendientes (mismo usuario).
    El guard _visited evita recursión infinita ante datos con ciclos.
    """
    if _visited is None:
        _visited = set()
    if task_id in _visited:
        return []
    _visited.add(task_id)

    ids = [task_id]
    children = (
        db.session.query(Task.id)
        .filter(Task.parent_task_id == task_id, Task.user_id == user_id)
        .all()
    )
    for (child_id,) in children:
        ids.extend(_collect_subtree_ids(child_id, user_id, _visited))
    return ids


def get_task_time_stats(task_id: int, user_id: int):
    """
    Devuelve estadísticas de UNA tarea:
    - minutos_estimados (Task.minutos_estimados)
    - minutos_reales (suma de WorkSession.minutos finalizadas de la tarea y de todas sus subtareas)
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
    # Agregamos el tiempo real de la tarea y de todas sus subtareas.
    subtree_ids = _collect_subtree_ids(task.id, user_id)
    minutos_reales = (
            db.session.query(func.coalesce(func.sum(WorkSession.minutos), 0))
            .filter(
                WorkSession.tarea_id.in_(subtree_ids),
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
