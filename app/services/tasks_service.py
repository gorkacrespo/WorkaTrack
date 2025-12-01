"""
Servicios relacionados con tareas (Task).
"""

from datetime import date
from decimal import Decimal
from typing import Optional

from app.models import db, Task, User


def create_task(
    user_id: int,
    titulo: str,
    descripcion: Optional[str] = None,
    categoria: Optional[str] = None,
    estado: str = "pendiente",
    fecha_plan_inicio: Optional[date] = None,
    fecha_plan_fin: Optional[date] = None,
    horas_estimadas: Optional[Decimal] = None,
) -> Task:
    """
    Crea una nueva tarea para un usuario.

    Valida:
    - Que el usuario exista.
    - Que el estado sea uno de los permitidos.
    """

    # Comprobamos que el usuario exista
    user = User.query.get(user_id)
    if user is None:
        raise ValueError("Usuario no encontrado")

    # Validación sencilla de estado
    if estado not in {"pendiente", "en_progreso", "terminada"}:
        raise ValueError("Estado de tarea no válido")

    task = Task(
        user_id=user_id,
        titulo=titulo,
        descripcion=descripcion,
        categoria=categoria,
        estado=estado,
        fecha_plan_inicio=fecha_plan_inicio,
        fecha_plan_fin=fecha_plan_fin,
        horas_estimadas=horas_estimadas,
    )

    db.session.add(task)
    db.session.commit()

    return task
