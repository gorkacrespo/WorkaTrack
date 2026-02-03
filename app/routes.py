"""
Rutas / endpoints de la API WorkaTrack.
"""

from datetime import date

from flask import Blueprint, jsonify, request, g

from app.models import db, Task, WorkSession
from app.auth_utils import create_access_token, jwt_required

from app.services.users_service import (
    create_user,
    get_user_by_id,
    authenticate_user,
)

from app.services.projects_service import (
    create_project,
    get_projects_by_user,
    get_project_by_id,
    delete_project,
)

from app.services.sessions_service import (
    create_session,
    get_sessions_by_user,
    update_session,
    delete_session,
)

from app.services.task_time_service import get_task_time_stats
from app.services.tasks_service import create_task, update_task, delete_task
from app.services.sessions_service import create_session, get_sessions_by_user
from app.services.task_time_service import get_tasks_with_time
from app.services.project_stats_service import get_project_time_stats
from app.services.milestones_service import (
    create_milestone,
    get_milestones_by_project,
    update_milestone,
    delete_milestone,
)


api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/health")
def health():
    return jsonify({"status": "ok", "message": "WorkaTrack API funcionando"})


# --------------------------------------------------------------------
# Usuarios
# --------------------------------------------------------------------

@api_bp.route("/users", methods=["POST"])
def create_user_route():
    data = request.get_json() or {}

    try:
        user = create_user(
            email=data["email"],
            password=data["password"],
            nombre=data.get("nombre"),
            username=data["username"],
        )
    except (KeyError, ValueError) as e:
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
    data = request.get_json() or {}

    try:
        user = authenticate_user(
            username=data["username"],
            password=data["password"],
        )
    except (KeyError, ValueError) as e:
        return jsonify({"error": str(e)}), 401

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
    user_id = g.current_user_id

    try:
        user = get_user_by_id(user_id)
    except ValueError as e:
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
# Proyectos
# --------------------------------------------------------------------

@api_bp.route("/projects", methods=["GET"])
@jwt_required
def list_projects_route():
    user_id = g.current_user_id
    projects = get_projects_by_user(user_id)

    data = [
        {
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "priority": p.priority,
            "category": p.category,
            "created_at": p.created_at.isoformat(),
            "fecha_inicio": p.fecha_inicio.isoformat() if p.fecha_inicio else None,
            "fecha_fin_prevista": (
                p.fecha_fin_prevista.isoformat()
                if p.fecha_fin_prevista else None
            ),
            "minutos_estimados": p.minutos_estimados,
            "progress": p.progress,
            "color": p.color,
            "milestones": [
                {
                    "id": m.id,
                    "titulo": m.titulo,
                    "fecha": m.fecha.isoformat(),
                    "tipo": m.tipo,
                    "color": m.color,
                }
                for m in p.milestones
            ],
        }
        for p in projects
    ]

    return jsonify(data), 200


@api_bp.route("/projects", methods=["POST"])
@jwt_required
def create_project_route():
    data = request.get_json() or {}
    user_id = g.current_user_id

    try:
        project = create_project(
            user_id=user_id,
            name=data["name"],
            description=data.get("description"),
            priority=data.get("priority"),
            category=data.get("category"),
            color=data.get("color"),
            minutos_estimados=data.get("minutos_estimados"),
            fecha_inicio=date.fromisoformat(data["fecha_inicio"])
                if data.get("fecha_inicio") else None,
            fecha_fin_prevista=date.fromisoformat(data["fecha_fin_prevista"])
                if data.get("fecha_fin_prevista") else None,
            password=data.get("password"),
        )
    except (KeyError, ValueError) as e:
        return jsonify({"error": str(e)}), 400

    return jsonify(
        {
            "id": project.id,
            "name": project.name,
        }
    ), 201


@api_bp.route("/projects/<int:project_id>", methods=["GET"])
@jwt_required
def get_project_route(project_id: int):
    user_id = g.current_user_id

    try:
        project = get_project_by_id(project_id, user_id)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404

    return jsonify(
        {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "priority": project.priority,
            "category": project.category,
            "created_at": project.created_at.isoformat(),
            "progress": project.progress,
            "color": project.color,
        }
    ), 200

@api_bp.route("/projects/<int:project_id>", methods=["PUT"])
@jwt_required
def update_project_route(project_id: int):
    user_id = g.current_user_id
    data = request.get_json() or {}

    try:
        project = get_project_by_id(project_id, user_id)

        if "name" in data:
            project.name = data["name"]

        if "description" in data:
            project.description = data["description"]

        if "priority" in data:
            project.priority = data["priority"]

        if "category" in data:
            project.category = data["category"]

        if "color" in data:
            project.color = data["color"]

        db.session.commit()

    except ValueError as e:
        return jsonify({"error": str(e)}), 404

    return jsonify({"detail": "Proyecto actualizado correctamente"}), 200

@api_bp.route("/projects/<int:project_id>", methods=["DELETE"])
@jwt_required
def delete_project_route(project_id: int):
    user_id = g.current_user_id
    data = request.get_json() or {}

    try:
        delete_project(project_id, user_id, password=data.get("password"),)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404

    return jsonify({"detail": "Proyecto eliminado correctamente"}), 200


# --------------------------------------------------------------------
# Estadísticas de proyecto
# --------------------------------------------------------------------

@api_bp.route("/projects/<int:project_id>/stats", methods=["GET"])
@jwt_required
def project_stats_route(project_id: int):
    user_id = g.current_user_id

    try:
        stats = get_project_time_stats(project_id, user_id)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404

    return jsonify(stats), 200

# --------------------------------------------------------------------
# Estadísticas de tarea
# --------------------------------------------------------------------

@api_bp.route("/tasks/<int:task_id>/stats", methods=["GET"])
@jwt_required
def task_stats_route(task_id: int):
    user_id = g.current_user_id

    try:
        stats = get_task_time_stats(task_id, user_id)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404

    return jsonify(stats), 200


# --------------------------------------------------------------------
# Tareas
# --------------------------------------------------------------------

@api_bp.route("/tasks", methods=["POST"])
@jwt_required
def create_task_route():
    data = request.get_json() or {}
    user_id = g.current_user_id

    try:
        task = create_task(
            user_id=user_id,
            titulo=data["titulo"],
            descripcion=data.get("descripcion"),
            categoria=data.get("categoria"),
            project_id=data.get("project_id"),
            parent_task_id=int(data["parent_task_id"])
                if data.get("parent_task_id") is not None
                else None,
            estado=data.get("estado", "pendiente"),
            fecha_plan_inicio=date.fromisoformat(data["fecha_plan_inicio"])
                if data.get("fecha_plan_inicio")
                else None,
            fecha_plan_fin=date.fromisoformat(data["fecha_plan_fin"])
                if data.get("fecha_plan_fin")
                else None,
            minutos_estimados=int(data["minutos_estimados"])
                if data.get("minutos_estimados") is not None
                else None,
            color=data.get("color"),
        )
    except (KeyError, ValueError) as e:
        return jsonify({"error": str(e)}), 400

    return jsonify(
        {
            "id": task.id,
            "titulo": task.titulo,
            "estado": task.estado,
            "color": task.color,
        }
    ), 201

@api_bp.route("/tasks/<int:task_id>", methods=["PUT"])
@jwt_required
def update_task_route(task_id: int):
    data = request.get_json() or {}
    user_id = g.current_user_id

    try:
        task = update_task(
            task_id=task_id,
            user_id=user_id,
            titulo=data.get("titulo"),
            descripcion=data.get("descripcion"),
            categoria=data.get("categoria"),
            estado=data.get("estado"),
            parent_task_id=int(data["parent_task_id"])
            if data.get("parent_task_id") is not None
            else None,
            fecha_plan_inicio=date.fromisoformat(data["fecha_plan_inicio"])
            if data.get("fecha_plan_inicio")
            else None,
            fecha_plan_fin=date.fromisoformat(data["fecha_plan_fin"])
            if data.get("fecha_plan_fin")
            else None,
            minutos_estimados=data.get("minutos_estimados"),
            color=data.get("color"),
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({"id": task.id}), 200

@api_bp.route("/tasks/<int:task_id>/status", methods=["PUT"])
@jwt_required
def update_task_status_route(task_id: int):
    data = request.get_json() or {}
    user_id = g.current_user_id

    estado = data.get("estado")
    if estado not in {"pendiente", "en_progreso", "en_pausa", "finalizada"}:
        return jsonify({"error": "Estado de tarea no válido"}), 400

    try:
        task = update_task(
            task_id=task_id,
            user_id=user_id,
            estado=estado,
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 404

    return jsonify(
        {
            "id": task.id,
            "estado": task.estado,
        }
    ), 200


@api_bp.route("/tasks/<int:task_id>", methods=["DELETE"])
@jwt_required
def delete_task_route(task_id: int):
    user_id = g.current_user_id
    data = request.get_json() or {}
    password = data.get("password")

    try:
        delete_task(
            task_id=task_id,
            user_id=user_id,
            password=data.get("password"),
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({"detail": "Tarea eliminada correctamente"}), 200

@api_bp.route("/me/tasks/with-time", methods=["GET"])
@jwt_required
def list_my_tasks_with_time_route():
    return jsonify(get_tasks_with_time(g.current_user_id)), 200


# --------------------------------------------------------------------
# Sesiones
# --------------------------------------------------------------------

@api_bp.route("/me/sessions", methods=["GET"])
@jwt_required
def list_my_sessions_route():
    user_id = g.current_user_id
    sessions = get_sessions_by_user(user_id)

    return jsonify(
        [
            {
                "id": s.id,
                "tarea_id": s.tarea_id,
                "fecha": s.fecha.isoformat(),
                "minutos": s.minutos,
                "tipo": s.tipo,
                "notas": s.notas,
            }
            for s in sessions
        ]
    ), 200


@api_bp.route("/sessions", methods=["POST"])
@jwt_required
def create_session_route():
    data = request.get_json() or {}

    try:
        ws = create_session(
            tarea_id=int(data["tarea_id"]),
            fecha=date.fromisoformat(data["fecha"])
            if data.get("fecha")
            else None,
            minutos=int(data["minutos"]),
            tipo=data.get("tipo"),
            notas=data.get("notas"),
        )
    except (KeyError, ValueError) as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({"id": ws.id}), 201

@api_bp.route("/sessions/<int:session_id>", methods=["PUT"])
@jwt_required
def update_session_route(session_id: int):
    data = request.get_json() or {}
    user_id = g.current_user_id

    try:
        ws = update_session(
            session_id=session_id,
            user_id=user_id,
            tarea_id=int(data["tarea_id"]),
            fecha=date.fromisoformat(data["fecha"])
            if data.get("fecha")
            else None,
            minutos=int(data["minutos"]),
            tipo=data.get("tipo"),
            notas=data.get("notas"),
        )
    except (KeyError, ValueError) as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({"id": ws.id}), 200


@api_bp.route("/sessions/<int:session_id>", methods=["DELETE"])
@jwt_required
def delete_session_route(session_id: int):
    user_id = g.current_user_id
    data = request.get_json() or {}

    try:
        delete_session(session_id=session_id, user_id=user_id, password=data.get("password"),)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({"detail": "Sesión eliminada correctamente"}), 200


# --------------------------------------------------------------------
# Hitos
# --------------------------------------------------------------------

@api_bp.route("/projects/<int:project_id>/milestones", methods=["GET"])
@jwt_required
def list_milestones_route(project_id: int):
    milestones = get_milestones_by_project(project_id)

    return jsonify(
        [
            {
                "id": m.id,
                "titulo": m.titulo,
                "descripcion": m.descripcion,
                "fecha": m.fecha.isoformat(),
                "tipo": m.tipo,
                "color": m.color,
            }
            for m in milestones
        ]
    ), 200


@api_bp.route("/projects/<int:project_id>/milestones", methods=["POST"])
@jwt_required
def create_milestone_route(project_id: int):
    data = request.get_json() or {}

    try:
        milestone = create_milestone(
            project_id=project_id,
            titulo=data["titulo"],
            fecha=date.fromisoformat(data["fecha"]),
            descripcion=data.get("descripcion"),
            tipo=data.get("tipo"),
            color=data.get("color"),
        )
    except (KeyError, ValueError) as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({"id": milestone.id}), 201


@api_bp.route("/milestones/<int:milestone_id>", methods=["PUT"])
@jwt_required
def update_milestone_route(milestone_id: int):
    data = request.get_json() or {}

    milestone = update_milestone(
        milestone_id=milestone_id,
        titulo=data.get("titulo"),
        descripcion=data.get("descripcion"),
        fecha=date.fromisoformat(data["fecha"])
        if data.get("fecha")
        else None,
        tipo=data.get("tipo"),
        color=data.get("color"),
    )

    return jsonify({"id": milestone.id}), 200


@api_bp.route("/milestones/<int:milestone_id>", methods=["DELETE"])
@jwt_required
def delete_milestone_route(milestone_id: int):
    delete_milestone(milestone_id)
    return jsonify({"detail": "Hito eliminado correctamente"}), 200
