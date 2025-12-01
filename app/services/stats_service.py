"""
Servicios para calcular estadísticas de tiempo de trabajo
por tarea, categoría y día.
"""

from collections import defaultdict
from typing import Any, Dict, List

from app.models import Task, WorkSession, User


def get_time_stats_by_task(user_id: int) -> Dict[str, Any]:
    """
    Devuelve estadísticas de tiempo por tarea para un usuario:
    - total_minutos
    - total_horas
    - lista de tareas con sus minutos/horas
    """

    user = User.query.get(user_id)
    if user is None:
        raise ValueError("Usuario no encontrado")

    tareas_data: List[Dict[str, Any]] = []
    total_minutos = 0

    for task in user.tasks:
        minutos = task.minutos_totales
        total_minutos += minutos

        tareas_data.append(
            {
                "task_id": task.id,
                "titulo": task.titulo,
                "minutos": minutos,
                "horas": minutos / 60.0,
            }
        )

    return {
        "user_id": user.id,
        "email": user.email,
        "tareas": tareas_data,
        "total_minutos": total_minutos,
        "total_horas": total_minutos / 60.0,
    }


def get_time_stats_by_category(user_id: int) -> Dict[str, Any]:
    """
    Devuelve estadísticas agrupadas por categoría de tarea.
    """

    user = User.query.get(user_id)
    if user is None:
        raise ValueError("Usuario no encontrado")

    # Usamos un acumulador por categoría
    minutos_por_categoria: Dict[str, int] = defaultdict(int)

    for task in user.tasks:
        categoria = task.categoria or "sin_categoria"
        minutos_por_categoria[categoria] += task.minutos_totales

    categorias_data = [
        {
            "categoria": categoria,
            "minutos": minutos,
            "horas": minutos / 60.0,
        }
        for categoria, minutos in minutos_por_categoria.items()
    ]

    return {
        "user_id": user.id,
        "email": user.email,
        "categorias": categorias_data,
    }


def get_time_stats_by_day(user_id: int) -> Dict[str, Any]:
    """
    Devuelve estadísticas agrupadas por día (fecha de WorkSession).
    """

    user = User.query.get(user_id)
    if user is None:
        raise ValueError("Usuario no encontrado")

    # Acumulamos minutos por fecha
    minutos_por_fecha: Dict[str, int] = defaultdict(int)

    # Recorremos todas las sesiones del usuario
    for task in user.tasks:
        for ws in task.work_sessions:
            fecha_str = ws.fecha.isoformat()
            minutos_por_fecha[fecha_str] += ws.minutos

    fechas_data = [
        {
            "fecha": fecha,
            "minutos": minutos,
            "horas": minutos / 60.0,
        }
        for fecha, minutos in sorted(minutos_por_fecha.items())
    ]

    return {
        "user_id": user.id,
        "email": user.email,
        "fechas": fechas_data,
    }
