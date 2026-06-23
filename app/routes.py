"""
Rutas / endpoints de la API WorkaTrack.
"""

from datetime import date, datetime

from flask import Blueprint, jsonify, request, g, Response, current_app

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
from app.services.sentiment_service import analyze_project_sentiment
from app.services.qa_service import answer_project_question, answer_project_question_deep

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
# Análisis de sentimientos (proyecto)
# --------------------------------------------------------------------

@api_bp.route("/projects/<int:project_id>/sentiment", methods=["POST"])
@jwt_required
def project_sentiment_route(project_id: int):
    user_id = g.current_user_id
    data = request.get_json() or {}

    # Si no viene la clave 'query' -> error. Si viene vacía -> análisis global (sin filtro por query).
    if "query" not in data:
        return jsonify({"error": "Falta 'query' (texto a analizar)"}), 400
    query = (data.get("query") or "").strip()

    scope = data.get("scope", "all")
    mode = data.get("mode", "general")
    date_from = data.get("date_from")
    date_to = data.get("date_to")
    resp_format = (data.get("format") or request.args.get("format") or "json").strip().lower()

    def _as_bool(v):
        if isinstance(v, bool):
            return v
        if v is None:
            return False
        if isinstance(v, (int, float)):
            return v != 0
        return str(v).strip().lower() in {"1","true","t","yes","y","on"}
    is_async = _as_bool(data.get("async") or request.args.get("async"))

    include_items = _as_bool(data.get("include_items") or request.args.get("include_items"))
    items_limit_raw = data.get("items_limit") or request.args.get("items_limit")
    try:
        items_limit = int(items_limit_raw) if items_limit_raw is not None else None
    except Exception:
        items_limit = None


    include_pairs = _as_bool(data.get("include_pairs") or request.args.get("include_pairs"))
    pairs_limit_raw = data.get("pairs_limit") or request.args.get("pairs_limit")
    try:
        pairs_limit = int(pairs_limit_raw) if pairs_limit_raw is not None else None
    except Exception:
        pairs_limit = None

    try:
        result = analyze_project_sentiment(
            project_id=project_id,
            user_id=user_id,
            query=query,
            scope=scope,
            date_from=date_from,
            date_to=date_to,
            mode=mode,
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 404

    # Reducir payload por defecto (ahorro de tokens). Solo incluir items/pairs si se pide explícitamente.
    if isinstance(result, dict):
        if not include_items and "items" in result:
            del result["items"]
        elif include_items and items_limit is not None and items_limit >= 0 and isinstance(result.get("items"), list):
            result["items"] = result["items"][:items_limit]

        if not include_pairs and "pairs" in result:
            del result["pairs"]
        elif include_pairs and pairs_limit is not None and pairs_limit >= 0 and isinstance(result.get("pairs"), list):
            result["pairs"] = result["pairs"][:pairs_limit]

    if resp_format in {"toon", "tool", "tool-format", "toon-format"}:
        try:
            from toon_format import encode
            body = encode(result)
        except Exception as e:
            return jsonify({"error": f"TOON encode failed: {e}"}), 500
        return Response(body, status=200, mimetype="text/plain")

    return jsonify(result), 200

# --------------------------------------------------------------------
# Q&A (proyecto)
# --------------------------------------------------------------------

# Jobs async en memoria (suficiente para 1 réplica). Se pierden al reiniciar el pod.
import threading
import time
import uuid
import os

_QA_JOBS = {}
_QA_JOBS_LOCK = threading.Lock()
_QA_JOBS_TTL_SECS = int(os.getenv("QA_JOBS_TTL_SECS") or "3600")  # default 1h


def _qa_prune_jobs():
    now = time.time()
    with _QA_JOBS_LOCK:
        dead = [jid for jid, j in _QA_JOBS.items() if (now - j.get("created_at", now)) > _QA_JOBS_TTL_SECS]
        for jid in dead:
            _QA_JOBS.pop(jid, None)


def _qa_job_get(job_id: str):
    _qa_prune_jobs()
    with _QA_JOBS_LOCK:
        return _QA_JOBS.get(job_id)


def _qa_job_update(job_id: str, **fields):
    with _QA_JOBS_LOCK:
        j = _QA_JOBS.get(job_id)
        if not j:
            return
        j.update(fields)


@api_bp.route("/qa/jobs/<job_id>", methods=["GET"])
@jwt_required
def qa_job_status_route(job_id: str):
    user_id = g.current_user_id
    j = _qa_job_get(job_id)
    if not j or j.get("user_id") != user_id:
        return jsonify({"error": "Job no encontrado"}), 404

    include_result = str(request.args.get("include_result") or "").strip().lower() in {"1","true","t","yes","y","on"}

    out = {k: v for k, v in j.items() if k not in ("result",)}
    if include_result:
        out["result"] = j.get("result")
    elif j.get("status") == "done":
        res = j.get("result") or {}
        out["answer"] = res.get("answer")
        out["weeks"] = res.get("weeks")
        out["cache_hits"] = res.get("cache_hits")

    elif j.get("status") == "error":
        res = j.get("result")
        if isinstance(res, dict):
            out["message"] = res.get("message") or res.get("error")
            out["llm_error"] = res.get("llm_error") or res.get("error")
            out["llm"] = res.get("llm")
            out["weeks"] = res.get("weeks")
            out["cache_hits"] = res.get("cache_hits")

    if out.get("status") in ("done", "error"):
        out["eta_seconds"] = None

    # Recalcular ETA en REDUCE aunque el worker no emita más callbacks (reduce puede tardar minutos)
    if out.get("status") == "running":
        try:
            now = time.time()
            if out.get("stage") == "reduce" and out.get("reduce_started_at") and out.get("reduce_eta_default") is not None:
                rem = float(out["reduce_eta_default"]) - (now - float(out["reduce_started_at"]))
                out["eta_seconds"] = int(rem) if rem > 0 else None
        except Exception:
            pass

    return jsonify(out), 200


@api_bp.route("/projects/<int:project_id>/qa", methods=["POST"])
@jwt_required
def project_qa_route(project_id: int):
    user_id = g.current_user_id
    data = request.get_json() or {}

    if "query" not in data:
        return jsonify({"error": "Falta 'query' (pregunta)"}), 400

    query = (data.get("query") or "").strip()
    scope = data.get("scope", "all")
    date_from = data.get("date_from")
    date_to = data.get("date_to")
    resp_format = (data.get("format") or request.args.get("format") or "json").strip().lower()
    mode = (data.get("mode") or request.args.get("mode") or "fast").strip().lower()



    def _as_bool(v):
        if isinstance(v, bool):
            return v
        if v is None:
            return False
        if isinstance(v, (int, float)):
            return v != 0
        return str(v).strip().lower() in {"1","true","t","yes","y","on"}
    is_async = _as_bool(data.get("async") or request.args.get("async"))


    include_items = _as_bool(data.get("include_items") or request.args.get("include_items"))
    items_limit_raw = data.get("items_limit") or request.args.get("items_limit")
    try:
        items_limit = int(items_limit_raw) if items_limit_raw is not None else None
    except Exception:
        items_limit = None

    try:
        if mode == "deep" and is_async:
            job_id = str(uuid.uuid4())
            created_at = time.time()
            with _QA_JOBS_LOCK:
                _QA_JOBS[job_id] = {
                    "job_id": job_id,
                    "project_id": project_id,
                    "user_id": user_id,
                    "mode": mode,
                    "scope": scope,
                    "query": query,
                    "status": "running",
                    "stage": "starting",
                    "done": 0,
                    "total": 0,
                    "eta_seconds": None,
                    "map_started_at": None,
                    "reduce_started_at": None,
                    "reduce_eta_default": int(os.getenv("QA_DEEP_REDUCE_ETA_SECS") or "180"),
                    "created_at": created_at,
                    "updated_at": created_at,
                    "result": None,
                    "error": None,
                }

            # callback de progreso desde qa_service
            started = {
                "t": created_at,
                "map_started_at": None,
                "reduce_started_at": None,
                "reduce_eta_default": int(os.getenv("QA_DEEP_REDUCE_ETA_SECS") or "180"),
            }
            app_obj = current_app._get_current_object()

            def progress_cb(info):
                now = time.time()
                stage = (info.get("stage") or "running").strip().lower() or "running"
                done = int(info.get("done") or 0)
                total = int(info.get("total") or 0)
                eta = None

                if stage == "reduce":
                    if started.get("reduce_started_at") is None:
                        started["reduce_started_at"] = now
                    reduce_elapsed = max(0.0, now - float(started.get("reduce_started_at") or now))
                    rem = float(started.get("reduce_eta_default") or 180) - reduce_elapsed
                    eta = int(rem) if rem > 0 else None
                else:
                    if started.get("map_started_at") is None:
                        started["map_started_at"] = now
                    if total > 0 and done > 0:
                        elapsed = max(0.001, now - float(started.get("map_started_at") or now))
                        rate = elapsed / max(1, done)
                        total_weeks = max(0, total - 1)  # total = semanas + 1 (reduce)
                        remaining_weeks = max(0, total_weeks - done)
                        eta = int(remaining_weeks * rate + int(started.get("reduce_eta_default") or 180))

                _qa_job_update(
                    job_id,
                    stage=stage,
                    done=done,
                    total=total,
                    eta_seconds=eta,
                    updated_at=now,
                    week_start=info.get("week_start"),
                    week_end=info.get("week_end"),
                    map_started_at=started.get("map_started_at"),
                    reduce_started_at=started.get("reduce_started_at"),
                    reduce_eta_default=started.get("reduce_eta_default"),
                )


            def worker():
                with app_obj.app_context():
                    try:
                        _qa_job_update(job_id, stage="running", updated_at=time.time())
                        res = answer_project_question_deep(
                            project_id=project_id,
                            user_id=user_id,
                            query=query,
                            scope=scope,
                            date_from=date_from,
                            date_to=date_to,
                            progress_cb=progress_cb,
                        )
                        if isinstance(res, dict) and res.get("status") == "ok":
                            _qa_job_update(job_id, status="done", stage="done", result=res, updated_at=time.time())
                        else:
                            msg = None
                            try:
                                msg = res.get("message") if isinstance(res, dict) else None
                            except Exception:
                                msg = None
                            _qa_job_update(
                                job_id,
                                status="error",
                                stage="error",
                                result=res,
                                error=(msg or "qa_deep_failed"),
                                updated_at=time.time(),
                            )
                    except Exception as e:
                        _qa_job_update(job_id, status="error", stage="error", error=str(e), updated_at=time.time())
                    finally:
                        try:
                            from app.models import db as _db
                            _db.session.remove()
                        except Exception:
                            pass

            t = threading.Thread(target=worker, daemon=True)
            t.start()

            return jsonify({"status": "accepted", "job_id": job_id}), 202

        if mode == "deep":
            result = answer_project_question_deep(
                project_id=project_id,
                user_id=user_id,
                query=query,
                scope=scope,
                date_from=date_from,
                date_to=date_to,
            )
        else:
            result = answer_project_question(
                project_id=project_id,
                user_id=user_id,
                query=query,
                scope=scope,
                date_from=date_from,
                date_to=date_to,
                include_items=include_items,
                items_limit=items_limit,
            )

    except ValueError as e:
        return jsonify({"error": str(e)}), 404

    if resp_format in {"toon", "tool", "tool-format", "toon-format"}:
        try:
            from toon_format import encode
            body = encode(result)
        except Exception as e:
            return jsonify({"error": f"TOON encode failed: {e}"}), 500
        return Response(body, status=200, mimetype="text/plain")

    return jsonify(result), 200

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
                "started_at": s.started_at.isoformat() if getattr(s, "started_at", None) else None,
                "ended_at": s.ended_at.isoformat() if getattr(s, "ended_at", None) else None,
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
            started_at=datetime.fromisoformat(data["started_at"].replace("Z","+00:00")) if data.get("started_at") else None,
            ended_at=datetime.fromisoformat(data["ended_at"].replace("Z","+00:00")) if data.get("ended_at") else None,
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
            started_at=datetime.fromisoformat(data["started_at"].replace("Z","+00:00")) if data.get("started_at") else None,
            ended_at=datetime.fromisoformat(data["ended_at"].replace("Z","+00:00")) if data.get("ended_at") else None,
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
