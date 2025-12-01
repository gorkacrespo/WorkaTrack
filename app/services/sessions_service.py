"""
Servicios relacionados con sesiones de trabajo (WorkSession).
"""

from datetime import date
from typing import Optional

from app.models import db, Task, WorkSession


def create_session(
    tarea_id: int,
    fecha: Optional[date],
    minutos: int,
    tipo: Optional[str] = None,
    notas: Optional[str] = None,
) -> WorkSession:
    """
    Crea una nueva sesión de trabajo para una tarea.

    Valida:
    - Que la tarea exista.
    - Que los minutos sean positivos.
    """

    task = Task.query.get(tarea_id)
    if task is None:
        raise ValueError("Tarea no encontrada")

    if minutos <= 0:
        raise ValueError("Los minutos deben ser mayores que 0")

    # Si no viene fecha, usamos date.today() (lo hace el modelo por defecto)
    ws = WorkSession(
        tarea_id=tarea_id,
        fecha=fecha,
        minutos=minutos,
        tipo=tipo,
        notas=notas,
    )

    db.session.add(ws)
    db.session.commit()

    return ws
