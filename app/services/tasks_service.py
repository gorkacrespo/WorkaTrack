"""
Servicios relacionados con tareas (Task).
"""

from datetime import date
from typing import Optional
from werkzeug.security import check_password_hash
from app.models import db, Task, User, Project

import random
import colorsys

def generate_random_color():
    # Elegimos un tono entre sectores bien separados (12 sectores)
    sector = random.randint(0, 11)
    h = sector / 12.0

    # Saturación y luminosidad controladas para buena visibilidad
    s = random.uniform(0.65, 0.9)
    l = random.uniform(0.45, 0.6)

    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return "#{:02x}{:02x}{:02x}".format(
        int(r * 255),
        int(g * 255),
        int(b * 255),
    )



def create_task(
    user_id: int,
    titulo: str,
    descripcion: Optional[str] = None,
    categoria: Optional[str] = None,
    project_id: Optional[int] = None,
    parent_task_id: Optional[int] = None,
    estado: str = "pendiente",
    fecha_plan_inicio: Optional[date] = None,
    fecha_plan_fin: Optional[date] = None,
    minutos_estimados: Optional[int] = None,
    color: Optional[str] = None,
) -> Task:
    """
    Crea una nueva tarea para un usuario.

    Valida:
    - Que el usuario exista.
    - Que el estado sea uno de los permitidos.
    - Si parent_task_id está definido, que exista y sea del mismo proyecto.
    """
    if project_id is None:
        raise ValueError("La tarea debe pertenecer a un proyecto")
    project = Project.query.get(project_id)
    if project is None:
        raise ValueError("Proyecto no encontrado")

    if fecha_plan_inicio and project.fecha_inicio and fecha_plan_inicio < project.fecha_inicio:
        raise ValueError(
            "No se puede crear una tarea antes de la fecha de inicio del proyecto"
        )


    # Comprobamos que el usuario exista
    user = User.query.get(user_id)
    if user is None:
        raise ValueError("Usuario no encontrado")

    # Validación sencilla de estado

    if estado not in {"pendiente", "en_progreso", "en_pausa", "finalizada"}:
        raise ValueError("Estado de tarea no válido")

    # Validación de jerarquía (si hay parent_task_id)
    if parent_task_id is not None:
        parent_task = Task.query.filter_by(id=parent_task_id, user_id=user_id).first()
        if parent_task is None:
            raise ValueError("Tarea padre no encontrada")
        if parent_task.project_id != project_id:
            raise ValueError("La tarea padre debe pertenecer al mismo proyecto")

    # Asignar color automático si no viene definido
    if color is None:
        color = generate_random_color()

    task = Task(
        user_id=user_id,
        titulo=titulo,
        descripcion=descripcion,
        categoria=categoria,
        project_id=project_id,
        parent_task_id=parent_task_id,
        estado=estado,
        fecha_plan_inicio=fecha_plan_inicio,
        fecha_plan_fin=fecha_plan_fin,
        minutos_estimados=minutos_estimados,
        color=color,
    )

    db.session.add(task)
    db.session.commit()

    return task
def update_task(
    task_id: int,
    user_id: int,
    titulo: Optional[str] = None,
    descripcion: Optional[str] = None,
    categoria: Optional[str] = None,
    estado: Optional[str] = None,
    parent_task_id: Optional[int] = None,
    fecha_plan_inicio: Optional[date] = None,
    fecha_plan_fin: Optional[date] = None,
    minutos_estimados: Optional[int] = None,
    color: Optional[str] = None,
) -> Task:
    """
    Actualiza una tarea existente.
    Solo permite modificar campos enviados.
    """

    task = Task.query.filter_by(id=task_id, user_id=user_id).first()
    if task is None:
        raise ValueError("Tarea no encontrada")

    if estado is not None and estado not in {"pendiente", "en_progreso","en_pausa", "finalizada"}:
        raise ValueError("Estado de tarea no válido")

    # Validación de jerarquía (si parent_task_id se envía)
    # Nota: aquí permitimos "desvincular" si parent_task_id viene como None.
    if parent_task_id is not None:
        if parent_task_id == task.id:
            raise ValueError("Una tarea no puede ser su propia tarea padre")

        parent_task = Task.query.filter_by(id=parent_task_id, user_id=user_id).first()
        if parent_task is None:
            raise ValueError("Tarea padre no encontrada")
        if parent_task.project_id != task.project_id:
            raise ValueError("La tarea padre debe pertenecer al mismo proyecto")

        task.parent_task_id = parent_task_id

    if titulo is not None:
        task.titulo = titulo
    if descripcion is not None:
        task.descripcion = descripcion
    if categoria is not None:
        task.categoria = categoria
    if estado is not None:
        task.estado = estado
    if fecha_plan_inicio is not None:
        task.fecha_plan_inicio = fecha_plan_inicio
    if fecha_plan_fin is not None:
        task.fecha_plan_fin = fecha_plan_fin
    if minutos_estimados is not None:
        task.minutos_estimados = minutos_estimados
    if color is not None:
        task.color = color

    db.session.commit()
    return task


def delete_task(task_id: int, user_id: int, password: Optional[str]) -> None:
    """
    Elimina una tarea del usuario.
    Requiere SIEMPRE contraseña del proyecto (porque en WorkaTrack es obligatoria).
    """

    task = Task.query.filter_by(id=task_id, user_id=user_id).first()
    if task is None:
        raise ValueError("Tarea no encontrada")

    # Si no hay project_id, no se puede validar contraseña → bloquear
    if task.project_id is None:
        raise ValueError("Tarea sin proyecto asociado (no se puede validar contraseña)")

    project = Project.query.get(task.project_id)
    if project is None:
        raise ValueError("Proyecto no encontrado")

    # Password del proyecto: obligatoria siempre
    if not password or not check_password_hash(project.password_hash, password):
        raise ValueError("Contraseña incorrecta")

    db.session.delete(task)
    db.session.commit()
