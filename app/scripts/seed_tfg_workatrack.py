#!/usr/bin/env python3
"""
Seed del proyecto TFG WorkaTrack (versión reestructurada).

Genera un único proyecto "WorkaTrack — TFG · Contenedores y Orquestadores"
organizado en DOS RAMAS principales para que el árbol crezca en profundidad
y no a lo ancho:

  RAMA A · Desarrollo de la aplicación  (construir WorkaTrack)
  RAMA B · Memoria del TFG              (el documento, calcado del índice real)

Notas de sesión en tono estudiante (concretas, no exhaustivas), 6 hitos,
y un paso final de rebalanceo que ajusta el tiempo real de cada fase para
dejar el proyecto en ~87% global, con el desarrollo casi cerrado y la
memoria en curso.

Credenciales:  demo / demo1234   ·   contraseña de proyecto: proyecto1234
"""
from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta

from werkzeug.security import generate_password_hash

from app import create_app
from app.models import db, User, Project, Task, Milestone, WorkSession, QaChunkSummary

# ── Credenciales (idénticas al resto de seeds) ─────────────────────────────────
DEMO_USERNAME    = "demo"
DEMO_EMAIL       = "demo@workatrack.local"
DEMO_PASSWORD    = "demo1234"
DEMO_NOMBRE      = "Tutora Demo"
PROJECT_PASSWORD = "proyecto1234"

PROJECT_NAME = "WorkaTrack — TFG · Contenedores y Orquestadores"


# ── Helpers (firmas idénticas al seed que ya funcionaba) ───────────────────────

def make_notes(objectives: str, notes: str) -> str:
    return json.dumps({"objectives": objectives, "notes": notes}, ensure_ascii=False)


def dt_from_day(base_day: date, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(base_day, time(hour, minute))


def ensure_demo_user() -> User:
    user = User.query.filter_by(username=DEMO_USERNAME).first()
    if not user:
        user = User(username=DEMO_USERNAME, email=DEMO_EMAIL, nombre=DEMO_NOMBRE)
        user.set_password(DEMO_PASSWORD)
        db.session.add(user)
        db.session.flush()
        return user
    user.email = DEMO_EMAIL
    user.nombre = DEMO_NOMBRE
    user.set_password(DEMO_PASSWORD)
    db.session.flush()
    return user


def wipe_project(project: Project) -> None:
    task_ids = [
        t.id for t in Task.query.filter_by(
            project_id=project.id, user_id=project.user_id
        ).all()
    ]
    if task_ids:
        WorkSession.query.filter(WorkSession.tarea_id.in_(task_ids)).delete(
            synchronize_session=False
        )
        Task.query.filter(Task.id.in_(task_ids)).delete(synchronize_session=False)
    Milestone.query.filter_by(project_id=project.id).delete(synchronize_session=False)
    QaChunkSummary.query.filter_by(
        project_id=project.id, user_id=project.user_id
    ).delete(synchronize_session=False)
    db.session.delete(project)
    db.session.flush()


def create_project(
    *, user: User, name: str, description: str, priority: str, category: str,
    color: str, fecha_inicio: date, fecha_fin_prevista: date,
    minutos_estimados: int, progress: int,
) -> Project:
    project = Project(
        user_id=user.id, name=name, description=description, priority=priority,
        category=category, color=color, fecha_inicio=fecha_inicio,
        fecha_fin_prevista=fecha_fin_prevista,
        minutos_estimados=minutos_estimados, progress=progress,
    )
    project.password_hash = generate_password_hash(PROJECT_PASSWORD)
    db.session.add(project)
    db.session.flush()
    return project


def create_task(
    *, user: User, project: Project, titulo: str, descripcion: str,
    categoria: str, estado: str, color: str, fecha_inicio: date, fecha_fin: date,
    minutos_estimados: int, parent_task: "Task | None" = None,
) -> Task:
    task = Task(
        user_id=user.id, project_id=project.id,
        parent_task_id=parent_task.id if parent_task else None,
        titulo=titulo, descripcion=descripcion, categoria=categoria,
        estado=estado, color=color,
        fecha_plan_inicio=fecha_inicio, fecha_plan_fin=fecha_fin,
        minutos_estimados=minutos_estimados,
    )
    db.session.add(task)
    db.session.flush()
    return task


def create_milestone(
    *, project: Project, titulo: str, descripcion: str,
    fecha_hito: date, tipo: str, color: str,
) -> Milestone:
    milestone = Milestone(
        project_id=project.id, titulo=titulo, descripcion=descripcion,
        fecha=fecha_hito, tipo=tipo, color=color,
    )
    db.session.add(milestone)
    db.session.flush()
    return milestone


def create_session(
    *, task: Task, day: date, start_hour: int, minutos: int, tipo: str,
    objectives: str, notes: str, finalizada: bool = True,
) -> WorkSession:
    started_at = dt_from_day(day, start_hour, 0)
    ended_at = started_at + timedelta(minutes=minutos if finalizada else 0)
    session = WorkSession(
        tarea_id=task.id, fecha=day,
        minutos=minutos if finalizada else 0,
        tipo=tipo, notas=make_notes(objectives, notes),
        finalizada=finalizada, started_at=started_at,
        ended_at=ended_at if finalizada else None,
    )
    db.session.add(session)
    db.session.flush()
    return session


# ── Limpieza ───────────────────────────────────────────────────────────────────

def delete_previous_tfg_project(user: User) -> None:
    project = Project.query.filter_by(user_id=user.id, name=PROJECT_NAME).first()
    if project:
        wipe_project(project)


# ── Rebalanceo de tiempos ───────────────────────────────────────────────────────

def _collect_subtree_ids(task_id: int) -> list[int]:
    ids = [task_id]
    for child in Task.query.filter_by(parent_task_id=task_id).all():
        ids.extend(_collect_subtree_ids(child.id))
    return ids


def rebalance_phase(phase: Task, ratio: float) -> None:
    """Escala los minutos de las sesiones finalizadas de toda la subrama de
    'phase' para que el tiempo real se acerque a phase.minutos_estimados * ratio."""
    ids = _collect_subtree_ids(phase.id)
    sessions = (
        WorkSession.query
        .filter(WorkSession.tarea_id.in_(ids), WorkSession.finalizada.is_(True))
        .all()
    )
    current = sum(s.minutos for s in sessions)
    if current <= 0 or not sessions:
        return
    target = int(round(phase.minutos_estimados * ratio))
    factor = target / current
    for s in sessions:
        nuevo = int(round(s.minutos * factor))
        s.minutos = max(1, nuevo)
        if s.started_at is not None:
            s.ended_at = s.started_at + timedelta(minutes=s.minutos)


# ── Construcción del proyecto ────────────────────────────────────────────────────

# Estados válidos: pendiente · en_progreso · en_pausa · finalizada
EST_FIN = "finalizada"
EST_PROG = "en_progreso"
EST_PEND = "pendiente"

# Colores por rama / fase
C_DEV   = "#2563eb"
C_MEM   = "#7c3aed"
COL = {
    "f1": "#0ea5e9", "f2": "#06b6d4", "f3": "#2563eb", "f4": "#3b82f6",
    "f5": "#14b8a6", "f6": "#10b981", "f7": "#0d9488", "f8": "#6366f1",
    "f9": "#8b5cf6", "f10": "#a855f7", "f11": "#f59e0b",
    "m1": "#7c3aed", "m2": "#9333ea", "m3": "#c026d3", "m4": "#db2777", "m5": "#e11d48",
}


def build_tfg_project(user: User) -> list[tuple[Task, float]]:
    """Construye el árbol completo y devuelve la lista (fase, ratio) para rebalancear."""
    project = create_project(
        user=user,
        name=PROJECT_NAME,
        description=(
            "TFG centrado en contenedores y orquestadores. WorkaTrack es el prototipo "
            "desarrollado como caso práctico: una aplicación web por servicios "
            "(frontend React/Vite, backend Flask, PostgreSQL y Ollama) contenedorizada "
            "con Docker, desplegada en Kubernetes con Minikube y con automatización "
            "parcial mediante GitLab CI/CD. El proyecto se organiza en dos partes: el "
            "desarrollo de la aplicación y la redacción de la memoria. Va de octubre de "
            "2025 a la defensa prevista en junio de 2026."
        ),
        priority="alta",
        category="TFG",
        color=C_DEV,
        fecha_inicio=date(2025, 10, 1),
        fecha_fin_prevista=date(2026, 6, 20),
        minutos_estimados=32400,  # 540 h
        progress=87,
    )

    phase_targets: list[tuple[Task, float]] = []

    # ── Hitos reales ─────────────────────────────────────────────────────────────
    create_milestone(project=project,
        titulo="Elección del caso práctico (WorkaTrack)",
        descripcion="Se decide desarrollar una app propia por servicios como caso práctico del TFG.",
        fecha_hito=date(2025, 10, 15), tipo="decisión", color="#0ea5e9")
    create_milestone(project=project,
        titulo="Primera versión del backend operativa",
        descripcion="API Flask con autenticación JWT y CRUD básico funcionando.",
        fecha_hito=date(2025, 12, 17), tipo="hito", color="#2563eb")
    create_milestone(project=project,
        titulo="Beta funcional completa",
        descripcion="App con todas las vistas y el Q&A funcionando de extremo a extremo.",
        fecha_hito=date(2026, 3, 15), tipo="hito", color="#14b8a6")
    create_milestone(project=project,
        titulo="Stack portable operativo",
        descripcion="Demo portable con Docker Compose lista para arrancar en cualquier equipo.",
        fecha_hito=date(2026, 3, 20), tipo="entrega", color="#f59e0b")
    create_milestone(project=project,
        titulo="Validación en segundo equipo (Ubuntu 22.04)",
        descripcion="Stack portable verificado desde cero en un segundo equipo Ubuntu 22.04.",
        fecha_hito=date(2026, 5, 28), tipo="hito", color="#10b981")
    create_milestone(project=project,
        titulo="Entrega y defensa del TFG",
        descripcion="Fecha prevista de entrega de la memoria y defensa ante el tribunal.",
        fecha_hito=date(2026, 6, 20), tipo="reunión", color="#e11d48")

    # ════════════════════════════════════════════════════════════════════════════
    # RAMA A · DESARROLLO DE LA APLICACIÓN
    # ════════════════════════════════════════════════════════════════════════════
    rama_a = create_task(
        user=user, project=project,
        titulo="Desarrollo de la aplicación",
        descripcion="Todo el trabajo de ingeniería: construir WorkaTrack, contenedorizarlo, desplegarlo y validarlo.",
        categoria="Desarrollo", estado=EST_PROG, color=C_DEV,
        fecha_inicio=date(2025, 10, 1), fecha_fin=date(2026, 6, 1),
        minutos_estimados=27300,
    )

    # ── A1 · Planteamiento, definición e investigación previa (25 h) ────────────
    f1 = create_task(user=user, project=project,
        titulo="Planteamiento, definición e investigación previa",
        descripcion="Definición del TFG e investigación de las tecnologías antes de empezar a construir.",
        categoria="Investigación", estado=EST_FIN, color=COL["f1"],
        fecha_inicio=date(2025, 10, 1), fecha_fin=date(2025, 10, 20),
        minutos_estimados=1500, parent_task=rama_a)
    phase_targets.append((f1, 0.95))
    create_session(task=f1, day=date(2025, 10, 20), start_hour=10, minutos=60, tipo="planificación",
        objectives="Repasar todo lo investigado antes de pasar al diseño.",
        notes="Repaso de las notas de investigación de la semana. Con esto cierro el planteamiento inicial y paso al diseño del prototipo con una base clara.")

    t = create_task(user=user, project=project,
        titulo="Definición del tema y objetivos",
        descripcion="Acotar el tema (contenedores y orquestadores) y decidir el caso práctico.",
        categoria="Investigación", estado=EST_FIN, color=COL["f1"],
        fecha_inicio=date(2025, 10, 1), fecha_fin=date(2025, 10, 5),
        minutos_estimados=300, parent_task=f1)
    create_session(task=t, day=date(2025, 10, 2), start_hour=10, minutos=120, tipo="planificación",
        objectives="Decidir el enfoque del TFG con la tutora.",
        notes="Hablado con la tutora. El trabajo combina parte teórica y una app propia como caso práctico. Me cuadra hacer una app por servicios para que Docker y Kubernetes tengan sentido.")
    create_session(task=t, day=date(2025, 10, 4), start_hour=11, minutos=90, tipo="planificación",
        objectives="Definir objetivos y alcance.",
        notes="Anoto objetivos: estudiar la evolución hasta contenedores/orquestadores, comparar alternativas y demostrar con un caso real. La app será WorkaTrack, gestión de proyectos/tareas/sesiones.")

    inv = create_task(user=user, project=project,
        titulo="Investigación previa de tecnologías",
        descripcion="Familiarización con las tecnologías candidatas antes de elegir el stack.",
        categoria="Investigación", estado=EST_FIN, color=COL["f1"],
        fecha_inicio=date(2025, 10, 5), fecha_fin=date(2025, 10, 20),
        minutos_estimados=1200, parent_task=f1)

    t = create_task(user=user, project=project,
        titulo="Docker y contenedores",
        descripcion="Imágenes, contenedores, volúmenes y registries.",
        categoria="Investigación", estado=EST_FIN, color=COL["f1"],
        fecha_inicio=date(2025, 10, 5), fecha_fin=date(2025, 10, 8),
        minutos_estimados=300, parent_task=inv)
    create_session(task=t, day=date(2025, 10, 6), start_hour=10, minutos=120, tipo="investigación",
        objectives="Entender imagen vs contenedor y los Dockerfile.",
        notes="Repasado lo básico de Docker: imágenes por capas, contenedores como instancia, volúmenes para persistencia. Me queda claro por qué encaja con una app por servicios.")
    create_session(task=t, day=date(2025, 10, 8), start_hour=16, minutos=90, tipo="investigación",
        objectives="Comparar Docker con Podman y LXC.",
        notes="Miro alternativas: Podman (sin daemon, rootless) y LXC. Para aprender y por documentación me quedo con Docker como referencia.")

    t = create_task(user=user, project=project,
        titulo="Kubernetes y orquestación",
        descripcion="Pods, deployments, services, ingress y el concepto de orquestar.",
        categoria="Investigación", estado=EST_FIN, color=COL["f1"],
        fecha_inicio=date(2025, 10, 8), fecha_fin=date(2025, 10, 12),
        minutos_estimados=300, parent_task=inv)
    create_session(task=t, day=date(2025, 10, 10), start_hour=10, minutos=150, tipo="investigación",
        objectives="Entender la estructura de un clúster.",
        notes="Plano de control + nodos. Objetos clave: Pod, Deployment, Service, Ingress. Comparo Kubernetes con Swarm y Nomad; para el trabajo el más completo y didáctico es Kubernetes.")

    t = create_task(user=user, project=project,
        titulo="Flask y arquitectura backend",
        descripcion="Flask, SQLAlchemy, JWT y diseño de la API.",
        categoria="Investigación", estado=EST_FIN, color=COL["f1"],
        fecha_inicio=date(2025, 10, 12), fecha_fin=date(2025, 10, 15),
        minutos_estimados=240, parent_task=inv)
    create_session(task=t, day=date(2025, 10, 13), start_hour=11, minutos=120, tipo="investigación",
        objectives="Decidir el stack del backend.",
        notes="Flask + SQLAlchemy para la API y JWT para la auth. Ligero y suficiente para el alcance del prototipo.")

    t = create_task(user=user, project=project,
        titulo="React/Vite y frontend",
        descripcion="React por componentes y Vite para el build.",
        categoria="Investigación", estado=EST_FIN, color=COL["f1"],
        fecha_inicio=date(2025, 10, 15), fecha_fin=date(2025, 10, 18),
        minutos_estimados=180, parent_task=inv)
    create_session(task=t, day=date(2025, 10, 16), start_hour=16, minutos=90, tipo="investigación",
        objectives="Decidir el stack del frontend.",
        notes="React encaja porque hay muchas vistas (proyectos, tareas, sesiones, diagramas). Vite para desarrollo y build.")

    t = create_task(user=user, project=project,
        titulo="PostgreSQL y persistencia",
        descripcion="Modelo relacional y por qué encaja con los datos del proyecto.",
        categoria="Investigación", estado=EST_FIN, color=COL["f1"],
        fecha_inicio=date(2025, 10, 18), fecha_fin=date(2025, 10, 20),
        minutos_estimados=180, parent_task=inv)
    create_session(task=t, day=date(2025, 10, 19), start_hour=10, minutos=90, tipo="investigación",
        objectives="Confirmar PostgreSQL como base de datos.",
        notes="Los datos están relacionados (usuario→proyecto→tarea→sesión), así que una relacional como PostgreSQL es lo natural.")

    # ── A2 · Diseño del prototipo (20 h) ─────────────────────────────────────────
    f2 = create_task(user=user, project=project,
        titulo="Diseño del prototipo",
        descripcion="Planificación de cómo iba a ser la app, qué funciones tendría y cómo dividirla.",
        categoria="Diseño", estado=EST_FIN, color=COL["f2"],
        fecha_inicio=date(2025, 10, 20), fecha_fin=date(2025, 11, 2),
        minutos_estimados=1200, parent_task=rama_a)
    phase_targets.append((f2, 0.95))
    create_session(task=f2, day=date(2025, 11, 2), start_hour=11, minutos=90, tipo="planificación",
        objectives="Cerrar el diseño y dejar el documento de partida para empezar a programar.",
        notes="Repaso conjunto de objetivos, funcionalidades y modelo de datos para tener un único documento de diseño coherente antes de tocar código. Con esto doy por cerrado el diseño del prototipo.")

    t = create_task(user=user, project=project,
        titulo="Objetivos y alcance de la app",
        descripcion="Qué resuelve WorkaTrack y hasta dónde llega el prototipo.",
        categoria="Diseño", estado=EST_FIN, color=COL["f2"],
        fecha_inicio=date(2025, 10, 20), fecha_fin=date(2025, 10, 23),
        minutos_estimados=240, parent_task=f2)
    create_session(task=t, day=date(2025, 10, 21), start_hour=10, minutos=120, tipo="diseño",
        objectives="Fijar el alcance del prototipo.",
        notes="La app es para seguir trabajo dentro de proyectos: proyectos, tareas, sesiones y análisis. No busco un producto final, sino un caso práctico completo.")

    t = create_task(user=user, project=project,
        titulo="Funcionalidades principales",
        descripcion="Auth, proyectos, tareas, estados, sesiones, tiempos y visualizaciones.",
        categoria="Diseño", estado=EST_FIN, color=COL["f2"],
        fecha_inicio=date(2025, 10, 23), fecha_fin=date(2025, 10, 27),
        minutos_estimados=360, parent_task=f2)
    create_session(task=t, day=date(2025, 10, 24), start_hour=11, minutos=150, tipo="diseño",
        objectives="Listar las funciones del planteamiento inicial.",
        notes="Login, CRUD de proyectos y tareas, estados, tiempo estimado vs real con sesiones, stats, Gantt y calendario. Y un análisis de sentimiento sobre las notas.")

    t = create_task(user=user, project=project,
        titulo="Funcionalidades secundarias y líneas futuras",
        descripcion="Lo que podría ampliarse: subtareas, hitos, árbol, multiusuario.",
        categoria="Diseño", estado=EST_FIN, color=COL["f2"],
        fecha_inicio=date(2025, 10, 27), fecha_fin=date(2025, 10, 30),
        minutos_estimados=240, parent_task=f2)
    create_session(task=t, day=date(2025, 10, 28), start_hour=16, minutos=90, tipo="diseño",
        objectives="Anotar posibles ampliaciones.",
        notes="Dejo como posibles: subtareas, hitos, vista árbol y, más a futuro, proyectos por grupos de usuarios con roles. No todo entra en el alcance inicial.")

    t = create_task(user=user, project=project,
        titulo="División de la app y modelo de datos",
        descripcion="Frontend, backend, BD y servicio de IA. Modelo Project/Task/User/WorkSession/Milestone.",
        categoria="Diseño", estado=EST_FIN, color=COL["f2"],
        fecha_inicio=date(2025, 10, 30), fecha_fin=date(2025, 11, 2),
        minutos_estimados=360, parent_task=f2)
    create_session(task=t, day=date(2025, 10, 31), start_hour=10, minutos=150, tipo="diseño",
        objectives="Diseñar el modelo de datos y la separación por servicios.",
        notes="Cuatro partes: frontend, backend, PostgreSQL y servicio de IA. Modelo: User, Project, Task (con padre), WorkSession y Milestone. Esta separación es la que justifica usar contenedores.")

    # ── A3 · Backend Flask (60 h) ────────────────────────────────────────────────
    f3 = create_task(user=user, project=project,
        titulo="Desarrollo del backend Flask",
        descripcion="API REST, autenticación, servicios y conexión con la base de datos.",
        categoria="Desarrollo", estado=EST_FIN, color=COL["f3"],
        fecha_inicio=date(2025, 11, 3), fecha_fin=date(2025, 11, 30),
        minutos_estimados=3600, parent_task=rama_a)
    phase_targets.append((f3, 0.95))
    create_session(task=f3, day=date(2025, 11, 30), start_hour=16, minutos=90, tipo="validación",
        objectives="Repaso general del backend antes de empezar el frontend.",
        notes="Revisión de todos los endpoints juntos (auth, proyectos, tareas, sesiones, hitos) para confirmar que el backend está estable antes de empezar a consumirlo desde React. Backend base cerrado.")

    t = create_task(user=user, project=project,
        titulo="Configuración inicial del proyecto",
        descripcion="Estructura app/, models.py, config.py, SQLAlchemy.",
        categoria="Desarrollo", estado=EST_FIN, color=COL["f3"],
        fecha_inicio=date(2025, 11, 3), fecha_fin=date(2025, 11, 7),
        minutos_estimados=480, parent_task=f3)
    create_session(task=t, day=date(2025, 11, 4), start_hour=10, minutos=180, tipo="desarrollo",
        objectives="Montar el esqueleto del backend.",
        notes="Creada la estructura app/ con models.py y config.py. SQLAlchemy conectando a PostgreSQL. create_app() listo. Primer modelo User en marcha.")

    t = create_task(user=user, project=project,
        titulo="Autenticación y seguridad (JWT)",
        descripcion="Login, registro y rutas protegidas con JWT.",
        categoria="Desarrollo", estado=EST_FIN, color=COL["f3"],
        fecha_inicio=date(2025, 11, 7), fecha_fin=date(2025, 11, 14),
        minutos_estimados=720, parent_task=f3)
    create_session(task=t, day=date(2025, 11, 9), start_hour=10, minutos=180, tipo="desarrollo",
        objectives="Implementar login y registro.",
        notes="Login devuelve un JWT firmado. Registro con validación de usuario/email únicos. Probado con curl, el token sale bien.")
    create_session(task=t, day=date(2025, 11, 12), start_hour=11, minutos=150, tipo="desarrollo",
        objectives="Proteger las rutas con @jwt_required.",
        notes="/me devuelve el usuario del token y el decorator protege el resto. Sin token válido, 401. La base de seguridad ya está.")

    api = create_task(user=user, project=project,
        titulo="API REST",
        descripcion="Endpoints CRUD de proyectos, tareas, sesiones e hitos.",
        categoria="Desarrollo", estado=EST_FIN, color=COL["f3"],
        fecha_inicio=date(2025, 11, 14), fecha_fin=date(2025, 11, 26),
        minutos_estimados=1680, parent_task=f3)

    t = create_task(user=user, project=project,
        titulo="Endpoints de proyectos",
        descripcion="GET/POST/PUT/DELETE de proyectos con su contraseña.",
        categoria="Desarrollo", estado=EST_FIN, color=COL["f3"],
        fecha_inicio=date(2025, 11, 14), fecha_fin=date(2025, 11, 18),
        minutos_estimados=600, parent_task=api)
    create_session(task=t, day=date(2025, 11, 15), start_hour=10, minutos=180, tipo="desarrollo",
        objectives="CRUD de proyectos.",
        notes="GET devuelve los proyectos del usuario; POST crea con nombre, descripción, color y estimación. DELETE pide la contraseña del proyecto. La validación de campos dio algo de guerra.")

    t = create_task(user=user, project=project,
        titulo="Endpoints de tareas",
        descripcion="CRUD de tareas, estados y relación padre-hija.",
        categoria="Desarrollo", estado=EST_FIN, color=COL["f3"],
        fecha_inicio=date(2025, 11, 18), fecha_fin=date(2025, 11, 22),
        minutos_estimados=600, parent_task=api)
    create_session(task=t, day=date(2025, 11, 20), start_hour=11, minutos=180, tipo="desarrollo",
        objectives="CRUD de tareas con estados.",
        notes="Tareas con los 4 estados y parent_task_id para la jerarquía. POST exige título. El borrado vuelve a pedir contraseña, igual que proyectos.")

    t = create_task(user=user, project=project,
        titulo="Endpoints de sesiones e hitos",
        descripcion="Sesiones de trabajo y milestones del proyecto.",
        categoria="Desarrollo", estado=EST_FIN, color=COL["f3"],
        fecha_inicio=date(2025, 11, 22), fecha_fin=date(2025, 11, 26),
        minutos_estimados=480, parent_task=api)
    create_session(task=t, day=date(2025, 11, 24), start_hour=10, minutos=150, tipo="desarrollo",
        objectives="Crear sesiones e hitos.",
        notes="Sesiones asociadas a tarea_id, guardan minutos y si están finalizadas al crearse. Hitos con fecha y tipo. Arreglado un bug que no dejaba crear sesión con minutos=0 al arrancar.")

    t = create_task(user=user, project=project,
        titulo="Servicios y centralización de la seguridad",
        descripcion="Lógica en services/, las rutas solo delegan.",
        categoria="Desarrollo", estado=EST_FIN, color=COL["f3"],
        fecha_inicio=date(2025, 11, 26), fecha_fin=date(2025, 11, 30),
        minutos_estimados=720, parent_task=f3)
    create_session(task=t, day=date(2025, 11, 27), start_hour=10, minutos=180, tipo="desarrollo",
        objectives="Mover la seguridad a la capa de servicios.",
        notes="La validación de contraseña en borrados vive en services/, no en routes.py. Las rutas solo enrutan y delegan. Decisión que mantengo en todo el backend.")
    create_session(task=t, day=date(2025, 11, 29), start_hour=11, minutos=120, tipo="validación",
        objectives="Probar el CRUD completo de la API.",
        notes="Repaso con curl de todo el CRUD: proyectos, tareas, sesiones e hitos. Todo responde bien. Backend base cerrado.")

    # ── A4 · Frontend React/Vite (55 h) ──────────────────────────────────────────
    f4 = create_task(user=user, project=project,
        titulo="Desarrollo del frontend React/Vite",
        descripcion="Interfaz, conexión con la API y vistas principales.",
        categoria="Desarrollo", estado=EST_FIN, color=COL["f4"],
        fecha_inicio=date(2025, 11, 25), fecha_fin=date(2025, 12, 20),
        minutos_estimados=3300, parent_task=rama_a)
    phase_targets.append((f4, 0.95))
    create_session(task=f4, day=date(2025, 12, 20), start_hour=16, minutos=90, tipo="validación",
        objectives="Probar la navegación completa entre las pantallas ya conectadas al backend.",
        notes="Recorrido entero login → proyectos → detalle de proyecto → detalle de tarea → sesiones, todo contra datos reales del backend. Frontend base funcional.")

    t = create_task(user=user, project=project,
        titulo="Cliente API y login",
        descripcion="client.js, apiFetch y JWT en localStorage.",
        categoria="Desarrollo", estado=EST_FIN, color=COL["f4"],
        fecha_inicio=date(2025, 11, 25), fecha_fin=date(2025, 11, 30),
        minutos_estimados=600, parent_task=f4)
    create_session(task=t, day=date(2025, 11, 27), start_hour=16, minutos=180, tipo="desarrollo",
        objectives="Conectar el frontend con el backend.",
        notes="client.js con apiFetch que añade la base de la URL y el JWT de localStorage. Login/registro contra Flask funcionando. Dejo de usar datos locales.")

    t = create_task(user=user, project=project,
        titulo="ProjectsPage y ProjectDetailPage",
        descripcion="Lista de proyectos con métricas y detalle con tareas.",
        categoria="Desarrollo", estado=EST_FIN, color=COL["f4"],
        fecha_inicio=date(2025, 11, 30), fecha_fin=date(2025, 12, 10),
        minutos_estimados=1080, parent_task=f4)
    create_session(task=t, day=date(2025, 12, 2), start_hour=10, minutos=180, tipo="desarrollo",
        objectives="Página principal de proyectos.",
        notes="Tarjetas de proyecto a la izquierda con barra de progreso (estimado vs real) y calendario a la derecha. El control de crear proyecto a la derecha de 'Mis proyectos'.")
    create_session(task=t, day=date(2025, 12, 6), start_hour=11, minutos=180, tipo="desarrollo",
        objectives="Detalle de proyecto con sus tareas.",
        notes="ProjectDetailPage casi igual que la de proyectos pero con tareas. Crear/editar (sin contraseña) y borrar (con contraseña). Bloque de resumen del proyecto arriba a la derecha.")

    t = create_task(user=user, project=project,
        titulo="TaskDetailPage y sesiones",
        descripcion="Gestión de sesiones de trabajo de cada tarea.",
        categoria="Desarrollo", estado=EST_FIN, color=COL["f4"],
        fecha_inicio=date(2025, 12, 10), fecha_fin=date(2025, 12, 16),
        minutos_estimados=840, parent_task=f4)
    create_session(task=t, day=date(2025, 12, 12), start_hour=10, minutos=180, tipo="desarrollo",
        objectives="Pantalla de sesiones de la tarea.",
        notes="TaskDetailPage carga la tarea y sus sesiones. Flujo: comenzar sesión → cronómetro → finalizar → guarda minutos. El historial muestra fecha, nombre, objetivo y nota.")

    t = create_task(user=user, project=project,
        titulo="Calendario anual",
        descripcion="ProjectYearCalendar con círculos, triángulos y cuadrados.",
        categoria="Desarrollo", estado=EST_FIN, color=COL["f4"],
        fecha_inicio=date(2025, 12, 16), fecha_fin=date(2025, 12, 20),
        minutos_estimados=780, parent_task=f4)
    create_session(task=t, day=date(2025, 12, 18), start_hour=11, minutos=180, tipo="desarrollo",
        objectives="Calendario anual del proyecto.",
        notes="Círculo = inicio, triángulo = fin, cuadrado = hito, estrella = varios eventos el mismo día. Lo que más costó fue posicionar por día. Un JSX mal cerrado me dio un 500 de Vite, ya corregido.")

    # ── A5 · Ampliación funcional (50 h) ─────────────────────────────────────────
    f5 = create_task(user=user, project=project,
        titulo="Ampliación funcional",
        descripcion="Subtareas, estados/colores, vista árbol y Gantt.",
        categoria="Desarrollo", estado=EST_FIN, color=COL["f5"],
        fecha_inicio=date(2025, 12, 15), fecha_fin=date(2026, 1, 20),
        minutos_estimados=3000, parent_task=rama_a)
    phase_targets.append((f5, 0.95))
    create_session(task=f5, day=date(2026, 1, 20), start_hour=11, minutos=90, tipo="validación",
        objectives="Comprobar que subtareas, estados, árbol y Gantt funcionan juntos sin romperse entre sí.",
        notes="Probado con un proyecto con subtareas de varios niveles: el árbol respeta la jerarquía, el Gantt sigue las fechas correctas y los colores de estado se mantienen en todas las vistas. Ampliación funcional cerrada.")

    t = create_task(user=user, project=project,
        titulo="Subtareas y jerarquía padre-hija",
        descripcion="Relación entre tareas y desplegables en la UI.",
        categoria="Desarrollo", estado=EST_FIN, color=COL["f5"],
        fecha_inicio=date(2025, 12, 15), fecha_fin=date(2025, 12, 28),
        minutos_estimados=720, parent_task=f5)
    create_session(task=t, day=date(2025, 12, 20), start_hour=10, minutos=180, tipo="desarrollo",
        objectives="Permitir subtareas.",
        notes="Las tareas pueden tener padre. En la tarjeta, un desplegable muestra las hijas. Desde el detalle de una tarea se crean subtareas que toman esa tarea como padre.")

    t = create_task(user=user, project=project,
        titulo="Estados y colores persistidos",
        descripcion="Cuatro estados mapeados a color, guardados en BD.",
        categoria="Desarrollo", estado=EST_FIN, color=COL["f5"],
        fecha_inicio=date(2025, 12, 28), fecha_fin=date(2026, 1, 5),
        minutos_estimados=600, parent_task=f5)
    create_session(task=t, day=date(2025, 12, 30), start_hour=11, minutos=150, tipo="desarrollo",
        objectives="Mapear estados y colores.",
        notes="pendiente/gris, en_progreso/azul, en_pausa/amarillo, finalizada/verde. Las finalizadas se ven en gris en el calendario. Cada tarea tiene su color propio en BD (aleatorio si no se pasa).")

    t = create_task(user=user, project=project,
        titulo="Vista árbol del proyecto",
        descripcion="ProjectTreePage: árbol SVG con zoom y centrado.",
        categoria="Desarrollo", estado=EST_FIN, color=COL["f5"],
        fecha_inicio=date(2026, 1, 5), fecha_fin=date(2026, 1, 14),
        minutos_estimados=900, parent_task=f5)
    create_session(task=t, day=date(2026, 1, 7), start_hour=10, minutos=180, tipo="desarrollo",
        objectives="Pintar el árbol del proyecto.",
        notes="Árbol SVG calculado recursivamente. La raíz es el proyecto y los nodos las tareas. Cada nodo tiene botones para expandir, abrir la tarea, ver sesiones y focalizar.")
    create_session(task=t, day=date(2026, 1, 11), start_hour=11, minutos=150, tipo="desarrollo",
        objectives="Zoom y centrado automático.",
        notes="Lupa para moverse por el árbol y centrado automático. Es de las vistas más vistosas para enseñar.")

    t = create_task(user=user, project=project,
        titulo="Diagrama de Gantt",
        descripcion="Barras de estimado vs real, comparativa y foco por mes.",
        categoria="Desarrollo", estado=EST_FIN, color=COL["f5"],
        fecha_inicio=date(2026, 1, 14), fecha_fin=date(2026, 1, 20),
        minutos_estimados=780, parent_task=f5)
    create_session(task=t, day=date(2026, 1, 16), start_hour=10, minutos=180, tipo="desarrollo",
        objectives="Implementar el Gantt.",
        notes="Tres vistas: estimado, real y comparativa. Opción de focalizar un mes. Las proporciones de fechas dieron bastante trabajo, pero quedó como la vista más profesional.")

    # ── A6 · Lógica de tiempos y métricas (25 h) ─────────────────────────────────
    f6 = create_task(user=user, project=project,
        titulo="Lógica de tiempos y métricas",
        descripcion="Minutos como unidad, estimado vs real, stats y limpieza de datos.",
        categoria="Desarrollo", estado=EST_FIN, color=COL["f6"],
        fecha_inicio=date(2026, 1, 15), fecha_fin=date(2026, 1, 28),
        minutos_estimados=1500, parent_task=rama_a)
    phase_targets.append((f6, 0.95))
    create_session(task=f6, day=date(2026, 1, 28), start_hour=11, minutos=60, tipo="validación",
        objectives="Verificar que estimado, real y progreso cuadran en proyecto y tareas a la vez.",
        notes="Comprobados varios proyectos de prueba: el tiempo real de las tareas sube correctamente al proyecto y las barras de progreso reflejan bien la diferencia entre estimado y real. Lógica de tiempos cerrada.")

    t = create_task(user=user, project=project,
        titulo="Modelo de tiempos (estimado vs real)",
        descripcion="Minutos base, sesiones finalizadas suman tiempo real.",
        categoria="Desarrollo", estado=EST_FIN, color=COL["f6"],
        fecha_inicio=date(2026, 1, 15), fecha_fin=date(2026, 1, 20),
        minutos_estimados=600, parent_task=f6)
    create_session(task=t, day=date(2026, 1, 17), start_hour=10, minutos=180, tipo="desarrollo",
        objectives="Fijar la unidad de tiempo.",
        notes="Todo en minutos. Las sesiones no finalizadas valen 0 y no cuentan. El tiempo real de una tarea sale de sus sesiones finalizadas; el del proyecto, de la suma de tareas.")

    t = create_task(user=user, project=project,
        titulo="Stats de proyecto y tarea",
        descripcion="Endpoints de stats y los SummaryBox del frontend.",
        categoria="Desarrollo", estado=EST_FIN, color=COL["f6"],
        fecha_inicio=date(2026, 1, 20), fecha_fin=date(2026, 1, 25),
        minutos_estimados=540, parent_task=f6)
    create_session(task=t, day=date(2026, 1, 22), start_hour=11, minutos=150, tipo="desarrollo",
        objectives="Stats y cajas de resumen.",
        notes="/projects/<id>/stats y /tasks/<id>/stats devuelven estimado, real y progreso. ProjectSummaryBox y TaskSummaryBox los consumen. La lógica de tiempos queda cerrada.")

    t = create_task(user=user, project=project,
        titulo="Migración y limpieza de datos antiguos",
        descripcion="Normalizar sesiones viejas y limpiar notas heredadas.",
        categoria="Desarrollo", estado=EST_FIN, color=COL["f6"],
        fecha_inicio=date(2026, 1, 25), fecha_fin=date(2026, 1, 28),
        minutos_estimados=360, parent_task=f6)
    create_session(task=t, day=date(2026, 1, 26), start_hour=10, minutos=120, tipo="incidencia",
        objectives="Limpiar datos que rompían la lógica.",
        notes="Normalizadas las sesiones sin finalizar a minutos=0 y limpiados restos de notas viejas. Confirmo que los datos antiguos ya no descuadran las métricas.")

    # ── A7 · Contenedorización con Docker (35 h) ─────────────────────────────────
    f7 = create_task(user=user, project=project,
        titulo="Contenedorización con Docker",
        descripcion="Dockerfiles y Docker Compose de todos los servicios.",
        categoria="Despliegue", estado=EST_FIN, color=COL["f7"],
        fecha_inicio=date(2026, 1, 28), fecha_fin=date(2026, 2, 10),
        minutos_estimados=2100, parent_task=rama_a)
    phase_targets.append((f7, 0.95))
    create_session(task=f7, day=date(2026, 2, 10), start_hour=11, minutos=90, tipo="validación",
        objectives="Levantar los cuatro servicios juntos con un solo comando y comprobar el arranque completo.",
        notes="docker compose up levanta db, web, frontend y ollama en el orden correcto gracias al healthcheck. Probado un arranque limpio desde cero. Contenedorización cerrada.")

    t = create_task(user=user, project=project,
        titulo="Dockerfile del backend",
        descripcion="Imagen del backend Flask con sus dependencias.",
        categoria="Despliegue", estado=EST_FIN, color=COL["f7"],
        fecha_inicio=date(2026, 1, 28), fecha_fin=date(2026, 2, 1),
        minutos_estimados=600, parent_task=f7)
    create_session(task=t, day=date(2026, 1, 29), start_hour=10, minutos=180, tipo="despliegue",
        objectives="Contenedorizar el backend.",
        notes="Dockerfile del backend con Python y requirements. La imagen levanta Flask sin tener que instalar nada a mano. Primer servicio empaquetado.")

    t = create_task(user=user, project=project,
        titulo="Dockerfile del frontend (nginx)",
        descripcion="Build de Vite servido por NGINX.",
        categoria="Despliegue", estado=EST_FIN, color=COL["f7"],
        fecha_inicio=date(2026, 2, 1), fecha_fin=date(2026, 2, 5),
        minutos_estimados=600, parent_task=f7)
    create_session(task=t, day=date(2026, 2, 3), start_hour=11, minutos=180, tipo="despliegue",
        objectives="Servir el frontend compilado.",
        notes="Build de React con Vite y NGINX para servirlo. Aquí aprendí algo importante: con contenedores no basta con cambiar el código, hay que reconstruir la imagen para ver los cambios.")

    t = create_task(user=user, project=project,
        titulo="Docker Compose (Postgres + servicios)",
        descripcion="Orquestación local de db, backend, frontend y Ollama.",
        categoria="Despliegue", estado=EST_FIN, color=COL["f7"],
        fecha_inicio=date(2026, 2, 5), fecha_fin=date(2026, 2, 10),
        minutos_estimados=900, parent_task=f7)
    create_session(task=t, day=date(2026, 2, 7), start_hour=10, minutos=180, tipo="despliegue",
        objectives="Levantar todo con Compose.",
        notes="docker-compose con db (Postgres), backend, frontend y Ollama. Healthcheck en la base para que los demás esperen. Toda la app arranca con un comando.")

    # ── A8 · Despliegue en Kubernetes (45 h) ─────────────────────────────────────
    f8 = create_task(user=user, project=project,
        titulo="Despliegue en Kubernetes (Minikube)",
        descripcion="Manifiestos, persistencia, Ingress e incidencias del clúster.",
        categoria="Despliegue", estado=EST_FIN, color=COL["f8"],
        fecha_inicio=date(2026, 2, 8), fecha_fin=date(2026, 2, 22),
        minutos_estimados=2700, parent_task=rama_a)
    phase_targets.append((f8, 0.95))
    create_session(task=f8, day=date(2026, 2, 22), start_hour=11, minutos=90, tipo="validación",
        objectives="Confirmar que la app completa funciona dentro del clúster, no solo cada pod por separado.",
        notes="Recorrido completo dentro de Minikube: acceso por Ingress, login, creación de proyecto y persistencia tras reiniciar un pod. El despliegue en Kubernetes queda cerrado para el alcance del TFG.")

    t = create_task(user=user, project=project,
        titulo="Manifiestos (namespace, deployments, services)",
        descripcion="Recursos base del clúster en el namespace workatrack.",
        categoria="Despliegue", estado=EST_FIN, color=COL["f8"],
        fecha_inicio=date(2026, 2, 8), fecha_fin=date(2026, 2, 12),
        minutos_estimados=720, parent_task=f8)
    create_session(task=t, day=date(2026, 2, 9), start_hour=10, minutos=180, tipo="despliegue",
        objectives="Desplegar los servicios en Minikube.",
        notes="Namespace workatrack con deployments y services para api, frontend y postgres. Minikube arrancando. Empieza a verse la app dentro del clúster.")

    t = create_task(user=user, project=project,
        titulo="PostgreSQL y secretos",
        descripcion="Persistencia en el clúster y configuración sensible.",
        categoria="Despliegue", estado=EST_FIN, color=COL["f8"],
        fecha_inicio=date(2026, 2, 12), fecha_fin=date(2026, 2, 16),
        minutos_estimados=600, parent_task=f8)
    create_session(task=t, day=date(2026, 2, 13), start_hour=11, minutos=150, tipo="despliegue",
        objectives="Persistencia y secrets.",
        notes="Postgres como statefulset con su volumen y las credenciales en Secrets. La persistencia dentro del clúster es más delicada de lo que pensaba.")

    t = create_task(user=user, project=project,
        titulo="Ingress workatrack.local",
        descripcion="Acceso externo por host.",
        categoria="Despliegue", estado=EST_FIN, color=COL["f8"],
        fecha_inicio=date(2026, 2, 16), fecha_fin=date(2026, 2, 19),
        minutos_estimados=480, parent_task=f8)
    create_session(task=t, day=date(2026, 2, 17), start_hour=10, minutos=120, tipo="despliegue",
        objectives="Exponer la app con Ingress.",
        notes="Ingress-nginx resolviendo workatrack.local. La app accesible desde el navegador a través del clúster.")

    t = create_task(user=user, project=project,
        titulo="Incidencias de despliegue",
        descripcion="CrashLoopBackOff por imagen cacheada y migración Alembic.",
        categoria="Despliegue", estado=EST_FIN, color=COL["f8"],
        fecha_inicio=date(2026, 2, 19), fecha_fin=date(2026, 2, 22),
        minutos_estimados=900, parent_task=f8)
    create_session(task=t, day=date(2026, 2, 20), start_hour=10, minutos=180, tipo="incidencia",
        objectives="Resolver el 500 por tabla inexistente.",
        notes="500 porque faltaba la tabla projects. Creé y apliqué la migración Alembic b336f32fd92b, reconstruí la imagen y rollout restart. Resuelto.")
    create_session(task=t, day=date(2026, 2, 21), start_hour=11, minutos=150, tipo="incidencia",
        objectives="Arreglar el CrashLoopBackOff tras reiniciar Minikube.",
        notes="Tras reiniciar Minikube, el clúster seguía con una imagen cacheada vieja y daba CrashLoopBackOff. Aprendí a controlar qué imagen corre realmente. Reconstruido y desplegado.")

    # ── A9 · CI/CD con GitLab (30 h) ─────────────────────────────────────────────
    f9 = create_task(user=user, project=project,
        titulo="Automatización CI/CD con GitLab",
        descripcion="Pipeline de test/build, Kaniko y kubeconfig seguro.",
        categoria="Despliegue", estado=EST_FIN, color=COL["f9"],
        fecha_inicio=date(2026, 2, 20), fecha_fin=date(2026, 2, 28),
        minutos_estimados=1800, parent_task=rama_a)
    phase_targets.append((f9, 0.95))
    create_session(task=f9, day=date(2026, 2, 28), start_hour=11, minutos=60, tipo="validación",
        objectives="Lanzar el pipeline completo de principio a fin y revisar los logs.",
        notes="Pipeline test→build ejecutado de punta a punta sin fallos, con Kaniko construyendo la imagen final. El despliegue automático sobre Minikube queda fuera de alcance por la limitación de red del runner, documentado en la memoria.")

    t = create_task(user=user, project=project,
        titulo="Pipeline test/build",
        descripcion="Stages de test y build en GitLab CI.",
        categoria="Despliegue", estado=EST_FIN, color=COL["f9"],
        fecha_inicio=date(2026, 2, 20), fecha_fin=date(2026, 2, 23),
        minutos_estimados=600, parent_task=f9)
    create_session(task=t, day=date(2026, 2, 21), start_hour=16, minutos=150, tipo="despliegue",
        objectives="Montar el pipeline base.",
        notes="Pipeline con stages de test y build. La idea no es automatizar todo, sino ordenar el ciclo: validar cambios y construir imágenes sin hacerlo a mano.")

    t = create_task(user=user, project=project,
        titulo="Build de imágenes con Kaniko",
        descripcion="Construcción de imágenes dentro del runner.",
        categoria="Despliegue", estado=EST_FIN, color=COL["f9"],
        fecha_inicio=date(2026, 2, 23), fecha_fin=date(2026, 2, 26),
        minutos_estimados=720, parent_task=f9)
    create_session(task=t, day=date(2026, 2, 24), start_hour=10, minutos=180, tipo="incidencia",
        objectives="Construir imágenes en CI.",
        notes="La construcción de imágenes en el runner daba problemas, así que pasé a Kaniko. Con eso el build de imágenes en el pipeline ya funciona.")

    t = create_task(user=user, project=project,
        titulo="kubeconfig seguro y ServiceAccount",
        descripcion="Credenciales del clúster para el deploy.",
        categoria="Despliegue", estado=EST_FIN, color=COL["f9"],
        fecha_inicio=date(2026, 2, 26), fecha_fin=date(2026, 2, 28),
        minutos_estimados=480, parent_task=f9)
    create_session(task=t, day=date(2026, 2, 27), start_hour=11, minutos=120, tipo="despliegue",
        objectives="Preparar el despliegue automático.",
        notes="kubeconfig como variable segura y un ServiceAccount para el deploy. El despliegue directo desde el runner queda condicionado por la red hacia Minikube, pero la base está montada.")

    # ── A10 · Análisis con IA y Q&A (70 h) ───────────────────────────────────────
    f10 = create_task(user=user, project=project,
        titulo="Análisis con IA y Q&A",
        descripcion="De sentimiento a IA local con Ollama y Q&A en dos modos.",
        categoria="Desarrollo", estado=EST_PROG, color=COL["f10"],
        fecha_inicio=date(2026, 2, 25), fecha_fin=date(2026, 3, 25),
        minutos_estimados=4200, parent_task=rama_a)
    phase_targets.append((f10, 0.85))
    create_session(task=f10, day=date(2026, 3, 25), start_hour=11, minutos=60, tipo="validación",
        objectives="Probar FAST y DEEP juntos sobre el mismo proyecto para comparar respuestas.",
        notes="Comparadas las respuestas de FAST y DEEP sobre las mismas preguntas: FAST da el estado reciente en segundos, DEEP da más contexto pero tarda más sin caché. El comportamiento es el esperado, sigo afinando el reduce de DEEP en proyectos grandes.",
        finalizada=False)

    t = create_task(user=user, project=project,
        titulo="Análisis de sentimiento inicial",
        descripcion="Análisis sobre las notas de tareas y sesiones.",
        categoria="Análisis", estado=EST_FIN, color=COL["f10"],
        fecha_inicio=date(2026, 2, 25), fecha_fin=date(2026, 2, 28),
        minutos_estimados=600, parent_task=f10)
    create_session(task=t, day=date(2026, 2, 26), start_hour=10, minutos=180, tipo="desarrollo",
        objectives="Primer análisis de sentimiento.",
        notes="Análisis básico sobre las notas de las sesiones para sacar el tono del proyecto. Era la idea inicial; de aquí evoluciona hacia algo más potente con IA.")

    t = create_task(user=user, project=project,
        titulo="IA local (descarte de vLLM, Ollama)",
        descripcion="Servicio de IA local al que el backend llama por API.",
        categoria="Análisis", estado=EST_FIN, color=COL["f10"],
        fecha_inicio=date(2026, 2, 28), fecha_fin=date(2026, 3, 6),
        minutos_estimados=1080, parent_task=f10)
    create_session(task=t, day=date(2026, 3, 1), start_hour=10, minutos=180, tipo="incidencia",
        objectives="Elegir el motor de IA local.",
        notes="Probé vLLM pero sobre CPU daba problemas, así que lo descarté por Ollama. El backend le habla por su API, sin meter el modelo dentro de la app.")

    qa = create_task(user=user, project=project,
        titulo="Q&A sobre el proyecto",
        descripcion="Preguntas y respuestas con dos modos y caché.",
        categoria="Análisis", estado=EST_PROG, color=COL["f10"],
        fecha_inicio=date(2026, 3, 6), fecha_fin=date(2026, 3, 25),
        minutos_estimados=2520, parent_task=f10)

    t = create_task(user=user, project=project,
        titulo="Modo FAST",
        descripcion="Estado reciente, ventana de 3 semanas, respuesta rápida.",
        categoria="Análisis", estado=EST_FIN, color=COL["f10"],
        fecha_inicio=date(2026, 3, 6), fecha_fin=date(2026, 3, 12),
        minutos_estimados=840, parent_task=qa)
    create_session(task=t, day=date(2026, 3, 8), start_hour=10, minutos=180, tipo="desarrollo",
        objectives="Modo rápido de consulta.",
        notes="FAST mira solo las últimas 3 semanas: responde al '¿cómo voy ahora?'. Pocas llamadas al modelo, respuesta corta tipo apuntes.")

    t = create_task(user=user, project=project,
        titulo="Modo DEEP",
        descripcion="Retrospectiva completa, asíncrono con progreso y ETA.",
        categoria="Análisis", estado=EST_PROG, color=COL["f10"],
        fecha_inicio=date(2026, 3, 12), fecha_fin=date(2026, 3, 20),
        minutos_estimados=1080, parent_task=qa)
    create_session(task=t, day=date(2026, 3, 14), start_hour=11, minutos=180, tipo="desarrollo",
        objectives="Modo profundo asíncrono.",
        notes="DEEP analiza todo el historial y referencia tareas/sesiones. Va como job asíncrono con progreso y ETA para evitar el 'running eterno'. Si no hay datos, responde que no tiene información suficiente.")
    create_session(task=t, day=date(2026, 5, 30), start_hour=10, minutos=90, tipo="ajuste",
        objectives="Afinar tiempos de respuesta del DEEP.",
        notes="Sigo ajustando timeouts y la reparación del reduce para que no se quede colgado en proyectos grandes.",
        finalizada=False)

    t = create_task(user=user, project=project,
        titulo="Caché semanal (QaChunkSummary)",
        descripcion="Resúmenes semanales cacheados para acelerar las consultas.",
        categoria="Análisis", estado=EST_FIN, color=COL["f10"],
        fecha_inicio=date(2026, 3, 20), fecha_fin=date(2026, 3, 25),
        minutos_estimados=600, parent_task=qa)
    create_session(task=t, day=date(2026, 3, 22), start_hour=10, minutos=150, tipo="desarrollo",
        objectives="Cachear los resúmenes por semana.",
        notes="QaChunkSummary guarda los resúmenes por semana. Con la caché caliente, la primera consulta tarda pero las siguientes van rápidas porque no reprocesan todo.")

    # ── A11 · Beta portable y validación (40 h) ──────────────────────────────────
    f11 = create_task(user=user, project=project,
        titulo="Beta portable y validación",
        descripcion="Empaquetado portable, datos demo, validación y arreglos finales.",
        categoria="Validación", estado=EST_PROG, color=COL["f11"],
        fecha_inicio=date(2026, 3, 10), fecha_fin=date(2026, 6, 1),
        minutos_estimados=2400, parent_task=rama_a)
    phase_targets.append((f11, 0.80))
    create_session(task=f11, day=date(2026, 5, 28), start_hour=16, minutos=60, tipo="validación",
        objectives="Repasar el estado general de la beta tras la validación en el segundo equipo.",
        notes="Con la beta validada en el segundo equipo y el árbol arreglado, queda cerrar el seed de datos definitivo y rematar algún detalle visual. La beta está prácticamente lista para la presentación.",
        finalizada=False)

    t = create_task(user=user, project=project,
        titulo="Empaquetado portable (Compose + scripts)",
        descripcion="docker-compose.portable.yml y scripts de arranque/parada.",
        categoria="Validación", estado=EST_FIN, color=COL["f11"],
        fecha_inicio=date(2026, 3, 10), fecha_fin=date(2026, 3, 15),
        minutos_estimados=720, parent_task=f11)
    create_session(task=t, day=date(2026, 3, 12), start_hour=10, minutos=180, tipo="despliegue",
        objectives="Empaquetar la beta portable.",
        notes="docker-compose.portable.yml con db, ollama, web y frontend, más scripts de arranque y parada. Con un comando levanta todo y siembra los datos demo.")

    t = create_task(user=user, project=project,
        titulo="Seed de datos demo",
        descripcion="Datos de prueba con volumen suficiente para las vistas y el Q&A.",
        categoria="Validación", estado=EST_FIN, color=COL["f11"],
        fecha_inicio=date(2026, 3, 13), fecha_fin=date(2026, 3, 18),
        minutos_estimados=480, parent_task=f11)
    create_session(task=t, day=date(2026, 3, 14), start_hour=11, minutos=150, tipo="desarrollo",
        objectives="Generar datos demo realistas.",
        notes="Seed con proyectos, tareas con jerarquía, sesiones con notas coherentes e hitos, para que el Gantt, el árbol y el Q&A tengan contenido de verdad.")

    t = create_task(user=user, project=project,
        titulo="Validación en segundo equipo (Ubuntu 22.04)",
        descripcion="Arranque desde cero en un equipo ajeno al de desarrollo.",
        categoria="Validación", estado=EST_FIN, color=COL["f11"],
        fecha_inicio=date(2026, 5, 25), fecha_fin=date(2026, 5, 28),
        minutos_estimados=600, parent_task=f11)
    create_session(task=t, day=date(2026, 5, 27), start_hour=10, minutos=180, tipo="validación",
        objectives="Probar la portabilidad real.",
        notes="Levantada la demo en un Ubuntu 22.04 desde cero. Backend, frontend, base de datos, Ollama y datos demo, todo sin instalar nada a mano. La portabilidad deja de ser teoría.")

    t = create_task(user=user, project=project,
        titulo="Arreglos finales del árbol",
        descripcion="Centrado del árbol y ciclo padre-hijo en el render.",
        categoria="Validación", estado=EST_PROG, color=COL["f11"],
        fecha_inicio=date(2026, 5, 28), fecha_fin=date(2026, 6, 1),
        minutos_estimados=600, parent_task=f11)
    create_session(task=t, day=date(2026, 5, 29), start_hour=11, minutos=150, tipo="incidencia",
        objectives="Arreglar el árbol que se quedaba colgado.",
        notes="Un proyecto se quedaba en 'Cargando árbol...' por un ciclo padre-hijo en la recursión del render. Blindada la construcción y resuelto. El árbol entra entero y centrado.")
    create_session(task=t, day=date(2026, 6, 1), start_hour=10, minutos=60, tipo="ajuste",
        objectives="Pulir el centrado y los límites del scroll.",
        notes="Sigo afinando el centrado y los márgenes del scroll en modo lupa. Con el seed reducido se nota mucho menos.",
        finalizada=False)

    # ════════════════════════════════════════════════════════════════════════════
    # RAMA B · MEMORIA DEL TFG
    # ════════════════════════════════════════════════════════════════════════════
    rama_b = create_task(
        user=user, project=project,
        titulo="Memoria del TFG",
        descripcion="El documento que se corrige y sostiene la defensa, con su parte teórica y su parte práctica.",
        categoria="Documentación", estado=EST_PROG, color=C_MEM,
        fecha_inicio=date(2026, 4, 1), fecha_fin=date(2026, 6, 18),
        minutos_estimados=5100,
    )

    # ── B1 · Introducción y planteamiento (12 h) ─────────────────────────────────
    m1 = create_task(user=user, project=project,
        titulo="Introducción y planteamiento",
        descripcion="Introducción, contexto, objetivos y beneficios/ODS.",
        categoria="Documentación", estado=EST_FIN, color=COL["m1"],
        fecha_inicio=date(2026, 4, 1), fecha_fin=date(2026, 4, 15),
        minutos_estimados=720, parent_task=rama_b)
    phase_targets.append((m1, 0.85))
    create_session(task=m1, day=date(2026, 4, 15), start_hour=10, minutos=60, tipo="documentación",
        objectives="Repasar y unificar el estilo de los cuatro apartados de introducción.",
        notes="Releído introducción, contexto, objetivos y ODS de una sentada para que el tono sea coherente entre los cuatro. Bloque de introducción y planteamiento cerrado.")

    t = create_task(user=user, project=project,
        titulo="Introducción",
        descripcion="Presentación del problema y de la tecnología.",
        categoria="Documentación", estado=EST_FIN, color=COL["m1"],
        fecha_inicio=date(2026, 4, 1), fecha_fin=date(2026, 4, 4),
        minutos_estimados=180, parent_task=m1)
    create_session(task=t, day=date(2026, 4, 2), start_hour=16, minutos=120, tipo="documentación",
        objectives="Redactar la introducción.",
        notes="Escrita la introducción: por qué los contenedores y orquestadores son relevantes hoy y qué pretende el trabajo.")

    t = create_task(user=user, project=project,
        titulo="Contexto",
        descripcion="Del monolito a la necesidad de contenedores.",
        categoria="Documentación", estado=EST_FIN, color=COL["m1"],
        fecha_inicio=date(2026, 4, 4), fecha_fin=date(2026, 4, 8),
        minutos_estimados=180, parent_task=m1)
    create_session(task=t, day=date(2026, 4, 5), start_hour=11, minutos=120, tipo="documentación",
        objectives="Redactar el contexto.",
        notes="Contexto sobre la arquitectura monolítica y sus limitaciones, que lleva a la tecnología de contenedores.")

    t = create_task(user=user, project=project,
        titulo="Objetivos y alcance",
        descripcion="Objetivo principal y metas específicas.",
        categoria="Documentación", estado=EST_FIN, color=COL["m1"],
        fecha_inicio=date(2026, 4, 8), fecha_fin=date(2026, 4, 11),
        minutos_estimados=180, parent_task=m1)
    create_session(task=t, day=date(2026, 4, 9), start_hour=10, minutos=120, tipo="documentación",
        objectives="Redactar objetivos y alcance.",
        notes="Objetivo principal (analizar la tecnología y aplicarla) y las metas concretas, incluido el enfoque tipo Feynman para que se entienda.")

    t = create_task(user=user, project=project,
        titulo="Beneficios y relación con los ODS",
        descripcion="Aportación del trabajo y ODS 4, 9, 12 y 13.",
        categoria="Documentación", estado=EST_FIN, color=COL["m1"],
        fecha_inicio=date(2026, 4, 11), fecha_fin=date(2026, 4, 15),
        minutos_estimados=180, parent_task=m1)
    create_session(task=t, day=date(2026, 4, 12), start_hour=11, minutos=120, tipo="documentación",
        objectives="Redactar beneficios y ODS.",
        notes="Apartado obligatorio. Relaciono el trabajo con los ODS 4, 9, 12 y 13 (educación, innovación, consumo responsable y clima).")

    # ── B2 · Parte teórica (35 h) ────────────────────────────────────────────────
    m2 = create_task(user=user, project=project,
        titulo="Parte teórica",
        descripcion="Evolución, estado de la tecnología, alternativas, riesgos y selección.",
        categoria="Documentación", estado=EST_PROG, color=COL["m2"],
        fecha_inicio=date(2026, 4, 10), fecha_fin=date(2026, 5, 10),
        minutos_estimados=2100, parent_task=rama_b)
    phase_targets.append((m2, 0.80))
    create_session(task=m2, day=date(2026, 5, 9), start_hour=11, minutos=90, tipo="documentación",
        objectives="Repasar la parte teórica completa de un tirón para revisar coherencia y conectores.",
        notes="Lectura completa de evolución histórica, estado de la tecnología, alternativas, riesgos y selección de la solución. Corregidas algunas repeticiones entre apartados. Queda revisar la bibliografía asociada a cada cita.",
        finalizada=False)

    t = create_task(user=user, project=project,
        titulo="Evolución histórica",
        descripcion="Despliegue tradicional, virtualización, contenedores y orquestadores.",
        categoria="Documentación", estado=EST_FIN, color=COL["m2"],
        fecha_inicio=date(2026, 4, 10), fecha_fin=date(2026, 4, 18),
        minutos_estimados=600, parent_task=m2)
    create_session(task=t, day=date(2026, 4, 13), start_hour=10, minutos=180, tipo="documentación",
        objectives="Redactar la evolución histórica.",
        notes="Recorrido del despliegue tradicional a la virtualización, contenedores y orquestadores. Uso la analogía mascotas → rebaños → granja de pollos para que se entienda.")
    create_session(task=t, day=date(2026, 4, 16), start_hour=11, minutos=150, tipo="documentación",
        objectives="Completar contenedores y orquestadores.",
        notes="Detallado imagen vs contenedor, Dockerfile, volúmenes y registries; y en orquestación, Pods, Deployments, Services e Ingress.")

    t = create_task(user=user, project=project,
        titulo="Análisis del estado de la tecnología",
        descripcion="Cloud-native, microservicios, DevOps y CI/CD.",
        categoria="Documentación", estado=EST_FIN, color=COL["m2"],
        fecha_inicio=date(2026, 4, 18), fecha_fin=date(2026, 4, 24),
        minutos_estimados=480, parent_task=m2)
    create_session(task=t, day=date(2026, 4, 20), start_hour=10, minutos=180, tipo="documentación",
        objectives="Redactar el estado de la tecnología.",
        notes="Arquitecturas cloud-native, microservicios, DevOps y CI/CD, con la IA dentro de las aplicaciones como tendencia actual.")

    t = create_task(user=user, project=project,
        titulo="Análisis de alternativas",
        descripcion="Docker/Podman/LXC y Kubernetes/Swarm/Nomad con criterios.",
        categoria="Documentación", estado=EST_PROG, color=COL["m2"],
        fecha_inicio=date(2026, 4, 24), fecha_fin=date(2026, 5, 2),
        minutos_estimados=480, parent_task=m2)
    create_session(task=t, day=date(2026, 4, 26), start_hour=11, minutos=180, tipo="documentación",
        objectives="Comparar alternativas con tablas de criterios.",
        notes="Tablas comparando contenedores (Docker/Podman/LXC) y orquestadores (Kubernetes/Swarm/Nomad). Justifico la elección de Docker y Kubernetes.")

    t = create_task(user=user, project=project,
        titulo="Análisis de riesgos",
        descripcion="Curva de aprendizaje, seguridad, recursos compartidos e infraestructura.",
        categoria="Documentación", estado=EST_PROG, color=COL["m2"],
        fecha_inicio=date(2026, 5, 2), fecha_fin=date(2026, 5, 6),
        minutos_estimados=240, parent_task=m2)
    create_session(task=t, day=date(2026, 5, 4), start_hour=10, minutos=120, tipo="documentación",
        objectives="Redactar los riesgos y su mitigación.",
        notes="Tabla de riesgos: curva de aprendizaje, configuración insegura, imágenes vulnerables, reparto de recursos e infraestructura, con su mitigación.")

    t = create_task(user=user, project=project,
        titulo="Selección de la solución",
        descripcion="Tecnologías elegidas y arquitectura de WorkaTrack.",
        categoria="Documentación", estado=EST_PROG, color=COL["m2"],
        fecha_inicio=date(2026, 5, 6), fecha_fin=date(2026, 5, 10),
        minutos_estimados=300, parent_task=m2)
    create_session(task=t, day=date(2026, 5, 8), start_hour=11, minutos=120, tipo="documentación",
        objectives="Justificar el stack elegido.",
        notes="Descrita la solución: WorkaTrack como caso práctico con Docker, Kubernetes, Flask, React/Vite, PostgreSQL, Ollama y GitLab CI/CD.")

    # ── B3 · Parte práctica (prototipo) (20 h) ───────────────────────────────────
    m3 = create_task(user=user, project=project,
        titulo="Parte práctica (prototipo)",
        descripcion="Requisitos y diseño, fases y cronograma, y análisis de resultados.",
        categoria="Documentación", estado=EST_PROG, color=COL["m3"],
        fecha_inicio=date(2026, 5, 5), fecha_fin=date(2026, 6, 1),
        minutos_estimados=1200, parent_task=rama_b)
    phase_targets.append((m3, 0.50))
    create_session(task=m3, day=date(2026, 5, 26), start_hour=11, minutos=60, tipo="documentación",
        objectives="Revisar que la parte práctica de la memoria refleja bien lo que hace realmente la app.",
        notes="Comparado el texto de requisitos y diseño funcional con la app actual para no dejar nada desactualizado. Falta cerrar fechas reales del cronograma y el apartado de resultados.",
        finalizada=False)

    t = create_task(user=user, project=project,
        titulo="Requisitos y diseño funcional",
        descripcion="Requisitos funcionales/no funcionales y recorrido por las pantallas.",
        categoria="Documentación", estado=EST_PROG, color=COL["m3"],
        fecha_inicio=date(2026, 5, 5), fecha_fin=date(2026, 5, 14),
        minutos_estimados=480, parent_task=m3)
    create_session(task=t, day=date(2026, 5, 9), start_hour=10, minutos=180, tipo="documentación",
        objectives="Redactar requisitos y diseño funcional.",
        notes="Requisitos iniciales, funcionalidades añadidas y no funcionales. Recorrido por las pantallas: acceso, proyectos, detalle de proyecto, detalle de tarea y análisis.")

    t = create_task(user=user, project=project,
        titulo="Fases, procedimiento y cronograma",
        descripcion="Fases del trabajo, equipo, herramientas y cronograma.",
        categoria="Documentación", estado=EST_PROG, color=COL["m3"],
        fecha_inicio=date(2026, 5, 14), fecha_fin=date(2026, 5, 22),
        minutos_estimados=360, parent_task=m3)
    create_session(task=t, day=date(2026, 5, 18), start_hour=11, minutos=120, tipo="documentación",
        objectives="Redactar fases y cronograma.",
        notes="Fases principales, procedimiento incremental y cronograma octubre→junio. El Gantt definitivo lo dejo para el cierre con las horas reales.",
        finalizada=False)

    t = create_task(user=user, project=project,
        titulo="Análisis de resultados y validación",
        descripcion="Resultado general y técnico, beta funcional y limitaciones.",
        categoria="Documentación", estado=EST_PROG, color=COL["m3"],
        fecha_inicio=date(2026, 5, 22), fecha_fin=date(2026, 6, 1),
        minutos_estimados=360, parent_task=m3)
    create_session(task=t, day=date(2026, 5, 26), start_hour=10, minutos=120, tipo="documentación",
        objectives="Redactar resultados y validación.",
        notes="Resultado general y técnico, tabla de casos de prueba y limitaciones. Falta cerrar la descripción de los datos demo cuando estén definitivos.",
        finalizada=False)

    # ── B4 · Presupuesto del TFG (6 h) ───────────────────────────────────────────
    m4 = create_task(user=user, project=project,
        titulo="Presupuesto del TFG",
        descripcion="Horas, amortizaciones, software, otros costes y resumen.",
        categoria="Documentación", estado=EST_PROG, color=COL["m4"],
        fecha_inicio=date(2026, 5, 20), fecha_fin=date(2026, 6, 5),
        minutos_estimados=360, parent_task=rama_b)
    phase_targets.append((m4, 0.55))
    create_session(task=m4, day=date(2026, 5, 28), start_hour=11, minutos=45, tipo="documentación",
        objectives="Revisar que las cifras del presupuesto cuadran entre las distintas tablas.",
        notes="Repasada la suma de horas internas, amortizaciones y otros costes para que el coste directo y el total final cuadren bien en la tabla resumen.",
        finalizada=False)

    t = create_task(user=user, project=project,
        titulo="Horas y amortizaciones",
        descripcion="Horas internas (alumno y tutora) y amortización de equipos.",
        categoria="Documentación", estado=EST_PROG, color=COL["m4"],
        fecha_inicio=date(2026, 5, 20), fecha_fin=date(2026, 5, 28),
        minutos_estimados=240, parent_task=m4)
    create_session(task=t, day=date(2026, 5, 23), start_hour=16, minutos=120, tipo="documentación",
        objectives="Calcular horas y amortizaciones.",
        notes="Horas internas provisionales (540 h alumno, 25 h tutora) y amortización de los dos portátiles. Cifras orientativas hasta el cierre.",
        finalizada=False)

    t = create_task(user=user, project=project,
        titulo="Software, otros costes y resumen",
        descripcion="Coste de software (0€ por open source) y resumen final.",
        categoria="Documentación", estado=EST_PEND, color=COL["m4"],
        fecha_inicio=date(2026, 5, 28), fecha_fin=date(2026, 6, 5),
        minutos_estimados=120, parent_task=m4)

    # ── B5 · Conclusiones, líneas futuras y bibliografía (12 h) ──────────────────
    m5 = create_task(user=user, project=project,
        titulo="Conclusiones, líneas futuras y bibliografía",
        descripcion="Cierre del trabajo, líneas futuras, bibliografía y anexos.",
        categoria="Documentación", estado=EST_PROG, color=COL["m5"],
        fecha_inicio=date(2026, 5, 25), fecha_fin=date(2026, 6, 18),
        minutos_estimados=720, parent_task=rama_b)
    phase_targets.append((m5, 0.25))
    create_session(task=m5, day=date(2026, 6, 1), start_hour=10, minutos=45, tipo="documentación",
        objectives="Esbozar el cierre general antes de redactar las conclusiones definitivas.",
        notes="Apuntadas las ideas clave que quiero que queden en las conclusiones: lo aprendido con Docker y Kubernetes y las dificultades reales encontradas. Aún por desarrollar en texto final.",
        finalizada=False)

    t = create_task(user=user, project=project,
        titulo="Conclusiones y líneas futuras",
        descripcion="Cumplimiento de objetivos, dificultades y trabajo futuro.",
        categoria="Documentación", estado=EST_PROG, color=COL["m5"],
        fecha_inicio=date(2026, 5, 25), fecha_fin=date(2026, 6, 10),
        minutos_estimados=480, parent_task=m5)
    create_session(task=t, day=date(2026, 5, 31), start_hour=10, minutos=120, tipo="documentación",
        objectives="Empezar las conclusiones.",
        notes="Primer borrador de conclusiones: dificultades reales (imágenes cacheadas en Kubernetes, persistencia con Alembic, NGINX y rebuild, vLLM→Ollama, Kaniko) y líneas futuras como el multiusuario.",
        finalizada=False)

    t = create_task(user=user, project=project,
        titulo="Bibliografía",
        descripcion="Referencias citadas en la memoria.",
        categoria="Documentación", estado=EST_PEND, color=COL["m5"],
        fecha_inicio=date(2026, 6, 10), fecha_fin=date(2026, 6, 16),
        minutos_estimados=120, parent_task=m5)

    t = create_task(user=user, project=project,
        titulo="Anexos",
        descripcion="Material complementario opcional.",
        categoria="Documentación", estado=EST_PEND, color=COL["m5"],
        fecha_inicio=date(2026, 6, 16), fecha_fin=date(2026, 6, 18),
        minutos_estimados=120, parent_task=m5)

    return phase_targets


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    app = create_app()

    with app.app_context():
        user = ensure_demo_user()
        delete_previous_tfg_project(user)
        phase_targets = build_tfg_project(user)

        # Rebalanceo de tiempos reales por fase
        for phase, ratio in phase_targets:
            rebalance_phase(phase, ratio)

        db.session.commit()

        project = Project.query.filter_by(user_id=user.id, name=PROJECT_NAME).first()
        task_count = Task.query.filter_by(
            user_id=user.id, project_id=project.id
        ).count()
        session_count = WorkSession.query.join(Task).filter(
            Task.user_id == user.id, Task.project_id == project.id
        ).count()
        total_real = db.session.query(
            db.func.coalesce(db.func.sum(WorkSession.minutos), 0)
        ).join(Task).filter(
            Task.project_id == project.id, WorkSession.finalizada.is_(True)
        ).scalar() or 0
        progreso = round(100 * total_real / project.minutos_estimados) if project.minutos_estimados else 0

        print("[OK] Seed TFG WorkaTrack (dos ramas) generado correctamente")
        print(f"[OK] Usuario demo: {DEMO_USERNAME}")
        print(f"[OK] Proyecto: {PROJECT_NAME}")
        print(f"[OK] Tareas creadas: {task_count}")
        print(f"[OK] Sesiones creadas: {session_count}")
        print(f"[OK] Tiempo real: {total_real} min de {project.minutos_estimados} min estimados (~{progreso}%)")
        print(f"[OK] Password demo: {DEMO_PASSWORD}")
        print(f"[OK] Password del proyecto: {PROJECT_PASSWORD}")


if __name__ == "__main__":
    main()
