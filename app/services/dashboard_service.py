"""
Servicio para construir el dashboard del usuario.

Aquí juntamos en UNA sola respuesta:
- Tareas activas (no terminadas).
- Sesiones recientes.
- Estadísticas por tarea.
- Estadísticas por categoría.
- Resumen de hoy y últimos 7 días.
"""

from datetime import date, timedelta
from typing import Any, Dict, List

from app.models import db, Task, WorkSession, User
from app.services.stats_service import (
    get_time_stats_by_task,
    get_time_stats_by_category,
    get_time_stats_by_day,
)


def build_dashboard_for_user(user_id: int) -> Dict[str, Any]:
    """
    Construye el objeto (dict) con toda la información del dashboard
    para un usuario concreto identificado por su user_id.

    Estructura general de la respuesta:

    {
        "user_id": 1,
        "email": "prueba1@example.com",

        "tareas_activas": [...],
        "sesiones_recientes": [...],

        "stats": {
            "tiempo_por_tarea": {...},
            "tiempo_por_categoria": {...}
        },

        "resumen": {
            "hoy": {...},
            "ultimos_7_dias": {...}
        }
    }
    """

    # ------------------------------------------------------------------
    # 0) Comprobar que el usuario existe
    # ------------------------------------------------------------------
    user = User.query.get(user_id)
    if user is None:
        raise ValueError("Usuario no encontrado")

    # ------------------------------------------------------------------
    # 1) TAREAS ACTIVAS (NO TERMINADAS)
    # ------------------------------------------------------------------
    # Consideramos "activas" todas las tareas cuyo estado NO es "terminada".
    # (pendiente, en_progreso, etc.)
    tareas_activas_query = (
        Task.query
        .filter(Task.user_id == user.id, Task.estado != "finalizada")
        .order_by(Task.id.asc())
    )

    tareas_activas_data: List[Dict[str, Any]] = []

    for task in tareas_activas_query.all():
        tareas_activas_data.append(
            {
                "id": task.id,
                "titulo": task.titulo,
                "descripcion": task.descripcion,
                "categoria": task.categoria,
                "estado": task.estado,
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
                "horas_estimadas": (
                    float(task.horas_estimadas)
                    if task.horas_estimadas is not None
                    else None
                ),
                # Totales reales trabajados (derivan de las WorkSession)
                "minutos_totales": task.minutos_totales,
                "horas_totales": task.horas_totales,
            }
        )

    # ------------------------------------------------------------------
    # 2) SESIONES RECIENTES
    # ------------------------------------------------------------------
    # Tomamos las últimas 10 sesiones del usuario.
    # OJO: WorkSession no tiene user_id; filtramos por Task.user_id.
    sesiones_query = (
        db.session.query(WorkSession)
        .join(Task, WorkSession.tarea_id == Task.id)
        .filter(Task.user_id == user.id)
        .order_by(WorkSession.fecha.desc(), WorkSession.id.desc())
        .limit(10)
    )

    sesiones_recientes_data: List[Dict[str, Any]] = []

    for ws in sesiones_query.all():
        tarea = ws.tarea  # relación definida en el modelo

        sesiones_recientes_data.append(
            {
                "id": ws.id,
                "tarea_id": ws.tarea_id,
                "fecha": ws.fecha.isoformat() if ws.fecha else None,
                "minutos": ws.minutos,
                "tipo": ws.tipo,
                "notas": ws.notas,
                "titulo_tarea": tarea.titulo if tarea else None,
                "categoria_tarea": tarea.categoria if tarea else None,
                "estado_tarea": tarea.estado if tarea else None,
            }
        )

    # ------------------------------------------------------------------
    # 3) ESTADÍSTICAS (REUTILIZANDO stats_service)
    # ------------------------------------------------------------------
    time_stats = get_time_stats_by_task(user.id)
    category_stats = get_time_stats_by_category(user.id)

    # ------------------------------------------------------------------
    # 4) RESUMEN HOY / ÚLTIMOS 7 DÍAS (A PARTIR DE get_time_stats_by_day)
    # ------------------------------------------------------------------
    # Usamos tu función existente que agrupa por fecha y calcula minutos/horas.
    day_stats = get_time_stats_by_day(user.id)
    fechas_stats = day_stats.get("fechas", [])

    today = date.today()
    today_str = today.isoformat()
    start_7 = today - timedelta(days=6)

    # Minutos de HOY
    minutos_hoy = 0
    for entry in fechas_stats:
        if entry.get("fecha") == today_str:
            minutos_hoy = entry.get("minutos", 0)
            break

    # Minutos de los ÚLTIMOS 7 DÍAS
    minutos_7 = 0
    for entry in fechas_stats:
        fecha_str = entry.get("fecha")
        if not fecha_str:
            continue
        try:
            fecha_obj = date.fromisoformat(fecha_str)
        except ValueError:
            continue

        if start_7 <= fecha_obj <= today:
            minutos_7 += entry.get("minutos", 0)

    resumen = {
        "hoy": {
            "fecha": today_str,
            "minutos": minutos_hoy,
            "horas": minutos_hoy / 60.0,
        },
        "ultimos_7_dias": {
            "fecha_inicio": start_7.isoformat(),
            "fecha_fin": today_str,
            "minutos": minutos_7,
            "horas": minutos_7 / 60.0,
        },
    }

    # ------------------------------------------------------------------
    # 5) Construir objeto final de dashboard
    # ------------------------------------------------------------------
    dashboard: Dict[str, Any] = {
        "user_id": user.id,
        "email": user.email,
        "tareas_activas": tareas_activas_data,
        "sesiones_recientes": sesiones_recientes_data,
        "stats": {
            "tiempo_por_tarea": time_stats,
            "tiempo_por_categoria": category_stats,
        },
        "resumen": resumen,
    }

    return dashboard
