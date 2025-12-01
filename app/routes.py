"""
Rutas / endpoints de la API WorkaTrack.

Esta capa SOLO debe encargarse de:
- Recibir peticiones HTTP.
- Leer parámetros / JSON.
- Llamar a los servicios correspondientes.
- Devolver una respuesta JSON (jsonify).
"""

from datetime import date
from decimal import Decimal

from flask import Blueprint, jsonify, request, g  # añadimos g

from app.models import db, Task, WorkSession
# Importamos los servicios de negocio
from app.services.users_service import (
    create_user,
    get_user_by_id,
    authenticate_user,
)
from app.services.tasks_service import create_task
from app.services.sessions_service import create_session
from app.services.stats_service import (
    get_time_stats_by_task,
    get_time_stats_by_category,
    get_time_stats_by_day,
)
from app.services.dashboard_service import build_dashboard_for_user
# Ahora importamos también el decorador para JWT
from app.auth_utils import create_access_token, jwt_required

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/health")
def health():
    """
    Endpoint sencillo para comprobar que la API está viva.
    """
    return jsonify({"status": "ok", "message": "WorkaTrack API funcionando"})


# --------------------------------------------------------------------
# Debug de token (solo para desarrollo)
# --------------------------------------------------------------------


@api_bp.route("/debug-token", methods=["GET"])
@jwt_required
def debug_token_route():
    """
    Devuelve lo que ve el backend cuando valida el JWT.
    Útil para depuración en desarrollo.
    """
    return jsonify(
        {
            "current_user_id": g.current_user_id,
            "current_username": g.current_username,
            "token_payload": g.current_token_payload,
        }
    ), 200


# --------------------------------------------------------------------
# Usuarios
# --------------------------------------------------------------------


@api_bp.route("/users", methods=["POST"])
def create_user_route():
    """
    Crea un nuevo usuario a partir de JSON.
    Espera:
    {
        "username": "...",
        "email": "...",
        "password": "...",
        "nombre": "..."
    }
    """
    data = request.get_json() or {}

    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    nombre = data.get("nombre")

    if not username or not email or not password:
        return jsonify({"error": "username, email y password son obligatorios"}), 400

    try:
        user = create_user(
            email=email,
            password=password,
            nombre=nombre,
            username=username,
        )
    except ValueError as e:
        # Por ejemplo, username o email duplicados
        return jsonify({"error": str(e)}), 400

    return jsonify(
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "nombre": user.nombre,
        }
    ), 201


@api_bp.route("/login", methods=["POST"])
def login_route():
    """
    Endpoint de login.

    Espera un JSON:
    {
        "username": "...",
        "password": "..."
    }

    Si las credenciales son correctas, devuelve un token JWT:
    {
        "access_token": "...",
        "token_type": "bearer",
        "user": {
            "id": ...,
            "username": "...",
            "email": "...",
            "nombre": "..."
        }
    }
    """
    data = request.get_json() or {}

    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "username y password son obligatorios"}), 400

    try:
        user = authenticate_user(username=username, password=password)
    except ValueError as e:
        # Credenciales incorrectas
        return jsonify({"error": str(e)}), 401

    # Generar token JWT
    token = create_access_token(user_id=user.id, username=user.username)

    return jsonify(
        {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "nombre": user.nombre,
            },
        }
    ), 200


@api_bp.route("/me", methods=["GET"])
@jwt_required
def get_me_route():
    """
    Devuelve la información del usuario autenticado.

    Usa el user_id que viene en el token (g.current_user_id)
    para obtener los datos desde la capa de servicio.
    """
    user_id = getattr(g, "current_user_id", None)
    if user_id is None:
        return jsonify({"error": "No se ha podido obtener el usuario del token"}), 401

    try:
        user = get_user_by_id(user_id)
    except ValueError as e:
        # Por si el usuario no existe (raro, pero mejor controlarlo)
        return jsonify({"error": str(e)}), 404

    return jsonify(
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "nombre": user.nombre,
        }
    ), 200


# --------------------------------------------------------------------
# Tareas
# --------------------------------------------------------------------


@api_bp.route("/me/tasks", methods=["GET"])
@jwt_required
def list_my_tasks_route():
    """
    Lista las tareas del usuario autenticado.

    Usa el user_id que viene en el token (g.current_user_id)
    para devolver solo SUS tareas.
    """
    user_id = getattr(g, "current_user_id", None)
    if user_id is None:
        return jsonify({"error": "No se ha podido obtener el usuario del token"}), 401

    # Obtenemos las tareas del usuario, ordenadas por id
    tasks = Task.query.filter_by(user_id=user_id).order_by(Task.id.asc()).all()

    # Las convertimos a una lista de diccionarios JSON-friendly
    tasks_data = [
        {
            "id": t.id,
            "user_id": t.user_id,
            "titulo": t.titulo,
            "descripcion": t.descripcion,
            "categoria": t.categoria,
            "estado": t.estado,
            "fecha_plan_inicio": t.fecha_plan_inicio.isoformat() if t.fecha_plan_inicio else None,
            "fecha_plan_fin": t.fecha_plan_fin.isoformat() if t.fecha_plan_fin else None,
            "horas_estimadas": float(t.horas_estimadas) if t.horas_estimadas is not None else None,
        }
        for t in tasks
    ]

    return jsonify(tasks_data), 200


@api_bp.route("/tasks", methods=["POST"])
@jwt_required  # ⬅️ protegemos la ruta con JWT
def create_task_route():
    """
    Crea una nueva tarea para el usuario autenticado.

    Ahora NO se envía user_id en el body.
    Se obtiene del token JWT (g.current_user_id).
    """
    data = request.get_json() or {}

    # Obtenemos el user_id desde el token validado por @jwt_required
    user_id = getattr(g, "current_user_id", None)
    if user_id is None:
        # En principio no debería pasar si el decorador funciona bien,
        # pero lo comprobamos por seguridad.
        return jsonify({"error": "No se ha podido obtener el usuario del token"}), 401

    titulo = data.get("titulo")
    if not titulo:
        return jsonify({"error": "titulo es obligatorio"}), 400

    descripcion = data.get("descripcion")
    categoria = data.get("categoria")
    estado = data.get("estado", "pendiente")

    # Parseo sencillo de fechas (strings ISO → date)
    fecha_plan_inicio = None
    if data.get("fecha_plan_inicio"):
        fecha_plan_inicio = date.fromisoformat(data["fecha_plan_inicio"])

    fecha_plan_fin = None
    if data.get("fecha_plan_fin"):
        fecha_plan_fin = date.fromisoformat(data["fecha_plan_fin"])

    horas_estimadas = None
    if data.get("horas_estimadas") is not None:
        horas_estimadas = Decimal(str(data["horas_estimadas"]))

    try:
        task = create_task(
            user_id=user_id,
            titulo=titulo,
            descripcion=descripcion,
            categoria=categoria,
            estado=estado,
            fecha_plan_inicio=fecha_plan_inicio,
            fecha_plan_fin=fecha_plan_fin,
            horas_estimadas=horas_estimadas,
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    return jsonify(
        {
            "id": task.id,
            "user_id": task.user_id,
            "titulo": task.titulo,
            "estado": task.estado,
        }
    ), 201


@api_bp.route("/tasks/<int:task_id>", methods=["GET"])
@jwt_required
def get_task_route(task_id: int):
    """
    Devuelve una tarea concreta del usuario autenticado.

    Solo se permite acceder a la tarea si pertenece al usuario
    del token. Si no, devolvemos 404 (no la exponemos).
    """
    user_id = getattr(g, "current_user_id", None)
    if user_id is None:
        return jsonify({"error": "No se ha podido obtener el usuario del token"}), 401

    task = Task.query.get(task_id)

    if task is None or task.user_id != user_id:
        # No existe o no es del usuario autenticado
        return jsonify({"error": "Tarea no encontrada"}), 404

    return jsonify(
        {
            "id": task.id,
            "user_id": task.user_id,
            "titulo": task.titulo,
            "descripcion": task.descripcion,
            "categoria": task.categoria,
            "estado": task.estado,
            "fecha_plan_inicio": task.fecha_plan_inicio.isoformat() if task.fecha_plan_inicio else None,
            "fecha_plan_fin": task.fecha_plan_fin.isoformat() if task.fecha_plan_fin else None,
            "horas_estimadas": float(task.horas_estimadas) if task.horas_estimadas is not None else None,
        }
    ), 200


@api_bp.route("/tasks/<int:task_id>", methods=["PUT"])
@jwt_required
def update_task_route(task_id: int):
    """
    Actualiza una tarea del usuario autenticado.

    Solo puede modificarse si la tarea pertenece al usuario
    del token. Se permiten cambios parciales en los campos:
    titulo, descripcion, categoria, estado,
    fecha_plan_inicio, fecha_plan_fin, horas_estimadas.
    """
    user_id = getattr(g, "current_user_id", None)
    if user_id is None:
        return jsonify({"error": "No se ha podido obtener el usuario del token"}), 401

    task = Task.query.get(task_id)

    if task is None or task.user_id != user_id:
        return jsonify({"error": "Tarea no encontrada"}), 404

    data = request.get_json() or {}

    # Actualizamos solo los campos presentes en el body
    if "titulo" in data:
        task.titulo = data["titulo"]

    if "descripcion" in data:
        task.descripcion = data["descripcion"]

    if "categoria" in data:
        task.categoria = data["categoria"]

    if "estado" in data:
        task.estado = data["estado"]

    if "fecha_plan_inicio" in data:
        value = data["fecha_plan_inicio"]
        task.fecha_plan_inicio = date.fromisoformat(value) if value else None

    if "fecha_plan_fin" in data:
        value = data["fecha_plan_fin"]
        task.fecha_plan_fin = date.fromisoformat(value) if value else None

    if "horas_estimadas" in data:
        value = data["horas_estimadas"]
        task.horas_estimadas = (
            Decimal(str(value)) if value is not None else None
        )

    db.session.commit()

    return jsonify(
        {
            "id": task.id,
            "user_id": task.user_id,
            "titulo": task.titulo,
            "descripcion": task.descripcion,
            "categoria": task.categoria,
            "estado": task.estado,
            "fecha_plan_inicio": task.fecha_plan_inicio.isoformat() if task.fecha_plan_inicio else None,
            "fecha_plan_fin": task.fecha_plan_fin.isoformat() if task.fecha_plan_fin else None,
            "horas_estimadas": float(task.horas_estimadas) if task.horas_estimadas is not None else None,
        }
    ), 200


@api_bp.route("/tasks/<int:task_id>", methods=["DELETE"])
@jwt_required
def delete_task_route(task_id: int):
    """
    Elimina una tarea del usuario autenticado.

    Solo se permite borrarla si pertenece al usuario
    del token.
    """
    user_id = getattr(g, "current_user_id", None)
    if user_id is None:
        return jsonify({"error": "No se ha podido obtener el usuario del token"}), 401

    task = Task.query.get(task_id)

    if task is None or task.user_id != user_id:
        return jsonify({"error": "Tarea no encontrada"}), 404

    db.session.delete(task)
    db.session.commit()

    # Podemos devolver 204 (sin contenido) o un mensaje simple:
    return jsonify({"detail": "Tarea eliminada correctamente"}), 200


# --------------------------------------------------------------------
# Sesiones de trabajo
# --------------------------------------------------------------------


@api_bp.route("/sessions", methods=["POST"])
@jwt_required  # ⬅️ también protegemos la creación de sesiones
def create_session_route():
    """
    Crea una sesión de trabajo para una tarea.

    De momento seguimos recibiendo tarea_id en el body.
    Aquí aún no comprobamos que la tarea sea del usuario,
    pero más adelante podríamos añadir esa validación extra.
    """
    data = request.get_json() or {}

    try:
        tarea_id = int(data.get("tarea_id"))
    except (TypeError, ValueError):
        return jsonify({"error": "tarea_id debe ser un entero"}), 400

    try:
        minutos = int(data.get("minutos"))
    except (TypeError, ValueError):
        return jsonify({"error": "minutos debe ser un entero"}), 400

    fecha = None
    if data.get("fecha"):
        fecha = date.fromisoformat(data["fecha"])

    tipo = data.get("tipo")
    notas = data.get("notas")

    try:
        ws = create_session(
            tarea_id=tarea_id,
            fecha=fecha,
            minutos=minutos,
            tipo=tipo,
            notas=notas,
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    return jsonify(
        {
            "id": ws.id,
            "tarea_id": ws.tarea_id,
            "fecha": ws.fecha.isoformat(),
            "minutos": ws.minutos,
            "tipo": ws.tipo,
            "notas": ws.notas,
        }
    ), 201


@api_bp.route("/me/sessions", methods=["GET"])
@jwt_required
def list_my_sessions_route():
    """
    Lista las sesiones de trabajo del usuario autenticado.

    Selecciona solo las sesiones cuya tarea asociada pertenece
    al usuario (Task.user_id == g.current_user_id).
    """
    user_id = getattr(g, "current_user_id", None)
    if user_id is None:
        return jsonify({"error": "No se ha podido obtener el usuario del token"}), 401

    sessions = (
        db.session.query(WorkSession)
        .join(Task, WorkSession.tarea_id == Task.id)
        .filter(Task.user_id == user_id)
        .order_by(WorkSession.fecha.asc(), WorkSession.id.asc())
        .all()
    )

    sessions_data = [
        {
            "id": s.id,
            "tarea_id": s.tarea_id,
            "fecha": s.fecha.isoformat() if s.fecha else None,
            "minutos": s.minutos,
            "tipo": s.tipo,
            "notas": s.notas,
        }
        for s in sessions
    ]

    return jsonify(sessions_data), 200


@api_bp.route("/sessions/<int:session_id>", methods=["GET"])
@jwt_required
def get_session_route(session_id: int):
    """
    Devuelve una sesión concreta del usuario autenticado.

    Solo se permite acceder si la sesión pertenece a una tarea
    cuyo user_id coincide con el del token.
    """
    user_id = getattr(g, "current_user_id", None)
    if user_id is None:
        return jsonify({"error": "No se ha podido obtener el usuario del token"}), 401

    ws = (
        db.session.query(WorkSession)
        .join(Task, WorkSession.tarea_id == Task.id)
        .filter(WorkSession.id == session_id, Task.user_id == user_id)
        .first()
    )

    if ws is None:
        return jsonify({"error": "Sesión no encontrada"}), 404

    return jsonify(
        {
            "id": ws.id,
            "tarea_id": ws.tarea_id,
            "fecha": ws.fecha.isoformat() if ws.fecha else None,
            "minutos": ws.minutos,
            "tipo": ws.tipo,
            "notas": ws.notas,
        }
    ), 200


@api_bp.route("/sessions/<int:session_id>", methods=["PUT"])
@jwt_required
def update_session_route(session_id: int):
    """
    Actualiza una sesión de trabajo del usuario autenticado.

    Solo se permite modificar si la sesión pertenece a una tarea
    cuyo user_id coincide con el del token.
    """
    user_id = getattr(g, "current_user_id", None)
    if user_id is None:
        return jsonify({"error": "No se ha podido obtener el usuario del token"}), 401

    ws = (
        db.session.query(WorkSession)
        .join(Task, WorkSession.tarea_id == Task.id)
        .filter(WorkSession.id == session_id, Task.user_id == user_id)
        .first()
    )

    if ws is None:
        return jsonify({"error": "Sesión no encontrada"}), 404

    data = request.get_json() or {}

    # Permitimos actualizar parcialmente algunos campos
    if "fecha" in data:
        value = data["fecha"]
        ws.fecha = date.fromisoformat(value) if value else None

    if "minutos" in data:
        value = data["minutos"]
        ws.minutos = int(value) if value is not None else ws.minutos

    if "tipo" in data:
        ws.tipo = data["tipo"]

    if "notas" in data:
        ws.notas = data["notas"]

    db.session.commit()

    return jsonify(
        {
            "id": ws.id,
            "tarea_id": ws.tarea_id,
            "fecha": ws.fecha.isoformat() if ws.fecha else None,
            "minutos": ws.minutos,
            "tipo": ws.tipo,
            "notas": ws.notas,
        }
    ), 200


@api_bp.route("/sessions/<int:session_id>", methods=["DELETE"])
@jwt_required
def delete_session_route(session_id: int):
    """
    Elimina una sesión de trabajo del usuario autenticado.

    Solo se permite borrarla si pertenece a una tarea cuyo
    user_id coincide con el del token.
    """
    user_id = getattr(g, "current_user_id", None)
    if user_id is None:
        return jsonify({"error": "No se ha podido obtener el usuario del token"}), 401

    ws = (
        db.session.query(WorkSession)
        .join(Task, WorkSession.tarea_id == Task.id)
        .filter(WorkSession.id == session_id, Task.user_id == user_id)
        .first()
    )

    if ws is None:
        return jsonify({"error": "Sesión no encontrada"}), 404

    db.session.delete(ws)
    db.session.commit()

    return jsonify({"detail": "Sesión eliminada correctamente"}), 200


# --------------------------------------------------------------------
# Estadísticas
# --------------------------------------------------------------------


@api_bp.route("/me/stats/time", methods=["GET"])
@jwt_required
def stats_time_me_route():
    """
    Estadísticas de tiempo por tarea para el usuario autenticado.

    Usa el user_id del token (g.current_user_id) y llama a la
    capa de servicio que ya teníamos (get_time_stats_by_task).
    """
    user_id = getattr(g, "current_user_id", None)
    if user_id is None:
        return jsonify({"error": "No se ha podido obtener el usuario del token"}), 401

    try:
        stats = get_time_stats_by_task(user_id)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404

    return jsonify(stats), 200


@api_bp.route("/me/stats/categories", methods=["GET"])
@jwt_required
def stats_categories_me_route():
    """
    Estadísticas agrupadas por categoría de tarea para el
    usuario autenticado.
    """
    user_id = getattr(g, "current_user_id", None)
    if user_id is None:
        return jsonify({"error": "No se ha podido obtener el usuario del token"}), 401

    try:
        stats = get_time_stats_by_category(user_id)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404

    return jsonify(stats), 200


@api_bp.route("/me/stats/dias", methods=["GET"])
@jwt_required
def stats_days_me_route():
    """
    Estadísticas agrupadas por día (fecha de sesión) para el
    usuario autenticado.
    """
    user_id = getattr(g, "current_user_id", None)
    if user_id is None:
        return jsonify({"error": "No se ha podido obtener el usuario del token"}), 401

    try:
        stats = get_time_stats_by_day(user_id)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404

    return jsonify(stats), 200


# --------------------------------------------------------------------
# Dashboard unificado del usuario
# --------------------------------------------------------------------


@api_bp.route("/me/dashboard", methods=["GET"])
@jwt_required
def dashboard_me_route():
    """
    Devuelve el "dashboard" del usuario autenticado:
    - Tareas activas (no terminadas).
    - Sesiones recientes.
    - Estadísticas por tarea.
    - Estadísticas por categoría.
    """
    user_id = getattr(g, "current_user_id", None)
    if user_id is None:
        return jsonify({"error": "No se ha podido obtener el usuario del token"}), 401

    try:
        dashboard = build_dashboard_for_user(user_id)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404

    return jsonify(dashboard), 200


# Endpoints antiguos, por si en algún momento quieres pasar un user_id
# concreto (por ejemplo, para administración). Se pueden eliminar más
# adelante si no los necesitas.


@api_bp.route("/users/<int:user_id>/stats/time", methods=["GET"])
def stats_time_route(user_id: int):
    """
    Estadísticas de tiempo por tarea para un usuario concreto (modo antiguo).
    """
    try:
        stats = get_time_stats_by_task(user_id)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404

    return jsonify(stats), 200


@api_bp.route("/users/<int:user_id>/stats/categories", methods=["GET"])
def stats_categories_route(user_id: int):
    """
    Estadísticas agrupadas por categoría de tarea para un usuario concreto (modo antiguo).
    """
    try:
        stats = get_time_stats_by_category(user_id)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404

    return jsonify(stats), 200


@api_bp.route("/users/<int:user_id>/stats/dias", methods=["GET"])
def stats_days_route(user_id: int):
    """
    Estadísticas agrupadas por día (fecha de sesión) para un usuario concreto (modo antiguo).
    """
    try:
        stats = get_time_stats_by_day(user_id)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404

    return jsonify(stats), 200
