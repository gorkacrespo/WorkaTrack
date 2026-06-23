#!/usr/bin/env python3
"""
Seed del proyecto TFG WorkaTrack.
Genera un único proyecto "WorkaTrack — TFG · Contenedores y Orquestadores"
con las 13 fases reales del desarrollo, árbol de subtareas (hasta 3 niveles),
6 hitos y ~180 sesiones con notas auténticas basadas en el desarrollo real.
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


# ── Helpers (firmas idénticas a seed_portable_demo_large.py) ───────────────────

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


# ── Construcción ───────────────────────────────────────────────────────────────

def build_tfg_project(user: User) -> None:
    project = create_project(
        user=user,
        name=PROJECT_NAME,
        description=(
            "TFG centrado en contenedores y orquestadores. WorkaTrack es el prototipo "
            "desarrollado para demostrar el ciclo completo de vida de una aplicación: "
            "desarrollo, contenedorización con Docker, despliegue en Kubernetes con Minikube, "
            "CI/CD con GitLab y análisis inteligente con IA local mediante Ollama. "
            "El proyecto abarca desde la definición inicial en octubre de 2025 hasta la "
            "defensa prevista en junio de 2026."
        ),
        priority="alta",
        category="TFG",
        color="#2563eb",
        fecha_inicio=date(2025, 10, 1),
        fecha_fin_prevista=date(2026, 6, 20),
        minutos_estimados=32400,
        progress=87,
    )

    # ─────────────────────────────────────────────────────────────────────────
    # FASE 1 · Planteamiento y definición del TFG  (15 h)
    # ─────────────────────────────────────────────────────────────────────────
    f1 = create_task(
        user=user, project=project,
        titulo="Planteamiento y definición del TFG",
        descripcion="Definición del tema, objetivos y elección del caso práctico WorkaTrack.",
        categoria="Planificación", estado="finalizada", color="#94a3b8",
        fecha_inicio=date(2025, 10, 1), fecha_fin=date(2025, 10, 18),
        minutos_estimados=900,
    )
    s = create_task(
        user=user, project=project, titulo="Definición del tema y ámbito",
        descripcion="Revisión del catálogo de TFGs y acotación del área de contenedores.",
        categoria="Planificación", estado="finalizada", color="#94a3b8",
        fecha_inicio=date(2025, 10, 1), fecha_fin=date(2025, 10, 7),
        minutos_estimados=300, parent_task=f1,
    )
    create_session(task=s, day=date(2025, 10, 2), start_hour=10, minutos=60, tipo="planificación",
        objectives="Revisar el catálogo de TFGs y acotar el área de interés.",
        notes="Primera sesión de exploración. Contenedores y orquestadores encajaba con el interés por desplegar aplicaciones reales. Se descartaron temas más teóricos que no tuviesen un componente práctico fuerte.")
    create_session(task=s, day=date(2025, 10, 5), start_hour=11, minutos=45, tipo="planificación",
        objectives="Confirmar con la tutora el enfoque sobre contenedores y orquestadores.",
        notes="La tutora validó el tema. Se acordó que el TFG tendría parte teórica sobre evolución del despliegue y parte práctica con un prototipo real. El objetivo de demostrar el ciclo completo de vida de una aplicación quedó bien definido.")

    s = create_task(
        user=user, project=project, titulo="Objetivos y alcance del trabajo",
        descripcion="Redacción de los objetivos y definición del alcance del TFG.",
        categoria="Planificación", estado="finalizada", color="#94a3b8",
        fecha_inicio=date(2025, 10, 6), fecha_fin=date(2025, 10, 12),
        minutos_estimados=300, parent_task=f1,
    )
    create_session(task=s, day=date(2025, 10, 7), start_hour=10, minutos=75, tipo="planificación",
        objectives="Redactar los objetivos y definir qué queda dentro y fuera del alcance.",
        notes="Objetivos definidos: aprender Docker y Kubernetes en profundidad, implementar CI/CD real con GitLab y desarrollar un prototipo funcional con frontend incluido. Quedó claro que el TFG no sería solo teórico.")
    create_session(task=s, day=date(2025, 10, 10), start_hour=15, minutos=60, tipo="planificación",
        objectives="Ajustar el alcance tras la primera reunión con la tutora.",
        notes="El prototipo tendría frontend además del backend para demostrar el ciclo completo. Más trabajo, pero más representativo del stack real en producción.")

    s = create_task(
        user=user, project=project, titulo="Decisión del caso práctico: WorkaTrack",
        descripcion="Elección del tipo de aplicación a desarrollar como prototipo del TFG.",
        categoria="Planificación", estado="finalizada", color="#94a3b8",
        fecha_inicio=date(2025, 10, 12), fecha_fin=date(2025, 10, 18),
        minutos_estimados=300, parent_task=f1,
    )
    create_session(task=s, day=date(2025, 10, 14), start_hour=10, minutos=90, tipo="planificación",
        objectives="Decidir qué tipo de aplicación servirá mejor como caso práctico.",
        notes="Se evaluaron blog, tienda online y gestor de tareas. Se eligió una aplicación de registro de tiempo y tareas porque el propio autor la usaría, lo que facilitaría el diseño de funcionalidades reales. Nació WorkaTrack.")

    # ─────────────────────────────────────────────────────────────────────────
    # FASE 2 · Investigación y familiarización  (15 h)
    # ─────────────────────────────────────────────────────────────────────────
    f2 = create_task(
        user=user, project=project,
        titulo="Investigación y familiarización inicial",
        descripcion="Estudio de contenedores, Kubernetes y herramientas para tomar decisiones técnicas previas al desarrollo.",
        categoria="Investigación", estado="finalizada", color="#0ea5e9",
        fecha_inicio=date(2025, 10, 15), fecha_fin=date(2025, 10, 31),
        minutos_estimados=900,
    )
    s = create_task(
        user=user, project=project, titulo="Repaso de contenedores y virtualización",
        descripcion="Comparativa VMs, contenedores Docker y alternativas como Podman.",
        categoria="Investigación", estado="finalizada", color="#0ea5e9",
        fecha_inicio=date(2025, 10, 15), fecha_fin=date(2025, 10, 21),
        minutos_estimados=300, parent_task=f2,
    )
    create_session(task=s, day=date(2025, 10, 16), start_hour=10, minutos=90, tipo="análisis",
        objectives="Leer documentación sobre Docker, diferencias con VMs y arquitectura de contenedores.",
        notes="Sesión de lectura intensiva. Queda claro el concepto de imagen vs contenedor. La diferencia de overhead respecto a una VM resultó más significativa de lo esperado. Docker Hub como repositorio de imágenes facilita mucho la reutilización.")
    create_session(task=s, day=date(2025, 10, 19), start_hour=11, minutos=75, tipo="análisis",
        objectives="Revisar Podman y LXC como alternativas y tomar nota de sus diferencias.",
        notes="Docker sigue siendo la referencia por ecosistema y documentación. Podman es interesante (daemonless) pero no suma al TFG. Se confirma Docker como elección definitiva.")

    s = create_task(
        user=user, project=project, titulo="Estudio de Kubernetes y alternativas",
        descripcion="Recursos de K8s, comparativa con Docker Swarm y Nomad.",
        categoria="Investigación", estado="finalizada", color="#0ea5e9",
        fecha_inicio=date(2025, 10, 21), fecha_fin=date(2025, 10, 28),
        minutos_estimados=360, parent_task=f2,
    )
    create_session(task=s, day=date(2025, 10, 22), start_hour=10, minutos=90, tipo="análisis",
        objectives="Entender los recursos básicos de K8s: Pod, Deployment, Service, Ingress, Namespace.",
        notes="Primera inmersión seria en Kubernetes. Los conceptos de Deployment y Service encajan bien. El Ingress resultó más confuso al principio, pero la documentación oficial está bien estructurada. El modelo de pods efímeros es la diferencia conceptual más importante.")
    create_session(task=s, day=date(2025, 10, 25), start_hour=15, minutos=60, tipo="análisis",
        objectives="Comparar K8s con Docker Swarm y Nomad en complejidad y funcionalidad.",
        notes="Kubernetes: más complejo pero estándar de facto. Swarm: simple pero tracción decreciente. Nomad: flexible pero menos orientado a contenedores puros. La decisión de usar Kubernetes fue rápida y bien justificada.")

    s = create_task(
        user=user, project=project, titulo="Decisión de stack y entorno local",
        descripcion="Stack definitivo y primera prueba con Minikube en local.",
        categoria="Investigación", estado="finalizada", color="#0ea5e9",
        fecha_inicio=date(2025, 10, 28), fecha_fin=date(2025, 10, 31),
        minutos_estimados=240, parent_task=f2,
    )
    create_session(task=s, day=date(2025, 10, 29), start_hour=10, minutos=60, tipo="planificación",
        objectives="Cerrar el stack técnico: Flask, React/Vite, PostgreSQL, Docker, Kubernetes, GitLab.",
        notes="Stack decidido: Flask (Python, familiar), React/Vite (moderno, buena DX), PostgreSQL (persistencia), GitLab de Irontec (CI/CD). Redis descartado para el MVP por no ser necesario.")
    create_session(task=s, day=date(2025, 10, 31), start_hour=11, minutos=90, tipo="desarrollo",
        objectives="Instalar y verificar Minikube como entorno local de Kubernetes.",
        notes="Minikube arrancó sin problemas en Ubuntu. Primer kubectl get pods funcionando. La curva de aprendizaje existe pero el entorno local ya responde. Primera prueba con Flask+Redis en Kubernetes validó que el entorno es funcional.")

    # ─────────────────────────────────────────────────────────────────────────
    # FASE 3 · Diseño del prototipo  (20 h)
    # ─────────────────────────────────────────────────────────────────────────
    f3 = create_task(
        user=user, project=project,
        titulo="Diseño del prototipo WorkaTrack",
        descripcion="Requisitos funcionales y no funcionales, arquitectura de servicios y modelo de datos.",
        categoria="Diseño", estado="finalizada", color="#8b5cf6",
        fecha_inicio=date(2025, 10, 31), fecha_fin=date(2025, 11, 14),
        minutos_estimados=1200,
    )
    s = create_task(
        user=user, project=project, titulo="Requisitos funcionales iniciales",
        descripcion="Autenticación, proyectos, tareas, estados, tiempo, sesiones, análisis y Gantt.",
        categoria="Diseño", estado="finalizada", color="#8b5cf6",
        fecha_inicio=date(2025, 10, 31), fecha_fin=date(2025, 11, 5),
        minutos_estimados=300, parent_task=f3,
    )
    create_session(task=s, day=date(2025, 11, 1), start_hour=10, minutos=90, tipo="análisis",
        objectives="Redactar los requisitos funcionales mínimos del prototipo.",
        notes="Lista inicial: login/registro con JWT, proyectos, tareas con los cuatro estados, tiempo estimado vs real, sesiones de trabajo, calendario. La tutora sugirió incluir análisis de sentimiento y Gantt desde el principio. La idea de Q&A/IA apareció como extensión natural del análisis.")
    create_session(task=s, day=date(2025, 11, 4), start_hour=15, minutos=60, tipo="planificación",
        objectives="Revisar y priorizar los requisitos para el MVP.",
        notes="Se clasificaron los requisitos en iniciales (MVP) y ampliaciones durante el desarrollo. Las subtareas, el árbol de proyecto y el Q&A con IA quedaron en la segunda categoría. Esta clasificación estructura bien la narrativa de la memoria.")

    s = create_task(
        user=user, project=project, titulo="Requisitos no funcionales",
        descripcion="Portabilidad, seguridad, escalabilidad y mantenibilidad del prototipo.",
        categoria="Diseño", estado="finalizada", color="#8b5cf6",
        fecha_inicio=date(2025, 11, 4), fecha_fin=date(2025, 11, 7),
        minutos_estimados=240, parent_task=f3,
    )
    create_session(task=s, day=date(2025, 11, 5), start_hour=10, minutos=75, tipo="análisis",
        objectives="Definir requisitos no funcionales clave para el TFG.",
        notes="Los no funcionales más importantes: la app debe correr en Docker y Kubernetes sin cambios de código, imágenes reproducibles y despliegue automatizable. Seguridad básica con JWT y password hashing obligatoria desde el principio.")

    s = create_task(
        user=user, project=project, titulo="Arquitectura de servicios",
        descripcion="Diseño de la arquitectura multicapa: React/NGINX, Flask/SQLAlchemy, PostgreSQL.",
        categoria="Diseño", estado="finalizada", color="#8b5cf6",
        fecha_inicio=date(2025, 11, 6), fecha_fin=date(2025, 11, 10),
        minutos_estimados=360, parent_task=f3,
    )
    create_session(task=s, day=date(2025, 11, 7), start_hour=10, minutos=90, tipo="análisis",
        objectives="Diseñar la arquitectura de la aplicación y sus servicios.",
        notes="Arquitectura final: frontend React servido por NGINX, backend Flask con SQLAlchemy, PostgreSQL persistente. Comunicación frontend↔backend por API REST con JWT. En Kubernetes cada servicio en su propio Deployment. Sencilla y clara.")
    create_session(task=s, day=date(2025, 11, 10), start_hour=11, minutos=60, tipo="documentación",
        objectives="Dibujar el diagrama de arquitectura y dejarlo documentado.",
        notes="Diagrama de tres capas bien separadas listo. Redis descartado del MVP. La arquitectura quedó limpia y fácil de explicar en la memoria.")

    s = create_task(
        user=user, project=project, titulo="Modelo de datos",
        descripcion="User, Project, Task (self-ref para subtareas), WorkSession y Milestone.",
        categoria="Diseño", estado="finalizada", color="#8b5cf6",
        fecha_inicio=date(2025, 11, 10), fecha_fin=date(2025, 11, 14),
        minutos_estimados=300, parent_task=f3,
    )
    create_session(task=s, day=date(2025, 11, 11), start_hour=10, minutos=90, tipo="análisis",
        objectives="Diseñar el modelo entidad-relación con todas las tablas del sistema.",
        notes="Modelo final: User, Project, Task (con Task.parent_task_id self-referencial para subtareas), WorkSession (con minutos y finalizada), Milestone. La clave self-referencial de Task fue la decisión de diseño más importante del modelo.")
    create_session(task=s, day=date(2025, 11, 13), start_hour=15, minutos=60, tipo="documentación",
        objectives="Revisar el modelo y documentar los campos clave de cada tabla.",
        notes="Campos clave confirmados: Task.parent_task_id (self-ref), WorkSession.minutos y finalizada como base para los cálculos de tiempo real. El modelo quedó sólido para empezar a codificar.")

    # ─────────────────────────────────────────────────────────────────────────
    # FASE 4 · Desarrollo del backend Flask  (70 h)
    # ─────────────────────────────────────────────────────────────────────────
    f4 = create_task(
        user=user, project=project,
        titulo="Desarrollo del backend Flask",
        descripcion="Estructura, modelos SQLAlchemy, autenticación JWT, API REST completa y seguridad.",
        categoria="Desarrollo", estado="finalizada", color="#2563eb",
        fecha_inicio=date(2025, 11, 14), fecha_fin=date(2025, 12, 19),
        minutos_estimados=4200,
    )
    s = create_task(
        user=user, project=project, titulo="Estructura Flask y configuración",
        descripcion="Factory pattern, config.py, blueprints y conexión a PostgreSQL.",
        categoria="Desarrollo", estado="finalizada", color="#2563eb",
        fecha_inicio=date(2025, 11, 14), fecha_fin=date(2025, 11, 21),
        minutos_estimados=600, parent_task=f4,
    )
    create_session(task=s, day=date(2025, 11, 14), start_hour=10, minutos=120, tipo="desarrollo",
        objectives="Crear la estructura inicial del proyecto Flask con factory pattern.",
        notes="Primera sesión real de código. Estructura: app/__init__.py con create_app(), config.py con DATABASE_URI y SECRET_KEY, models.py vacío. El factory pattern facilita inicializar la app en distintos contextos (tests, Docker, Kubernetes).")
    create_session(task=s, day=date(2025, 11, 17), start_hour=10, minutos=90, tipo="desarrollo",
        objectives="Configurar SQLAlchemy, Flask-Migrate y la conexión inicial a PostgreSQL.",
        notes="SQLAlchemy integrado con Flask-Migrate para migraciones. DATABASE_URI desde variables de entorno facilita el cambio entre local y Docker sin tocar código. Primera migración vacía generada y aplicada.")
    create_session(task=s, day=date(2025, 11, 20), start_hour=11, minutos=75, tipo="validación",
        objectives="Verificar que el servidor Flask arranca y responde a /api/health.",
        notes="/api/health devuelve {status: ok}. Flask levanta limpio. La estructura de la app es sólida para ir añadiendo modelos y rutas encima.")

    s = create_task(
        user=user, project=project, titulo="Modelos SQLAlchemy y base de datos",
        descripcion="User, Project, Task (self-ref), WorkSession y Milestone con sus relaciones.",
        categoria="Desarrollo", estado="finalizada", color="#2563eb",
        fecha_inicio=date(2025, 11, 21), fecha_fin=date(2025, 11, 28),
        minutos_estimados=720, parent_task=f4,
    )
    create_session(task=s, day=date(2025, 11, 22), start_hour=10, minutos=120, tipo="desarrollo",
        objectives="Implementar los modelos User y Project con sus campos y relaciones.",
        notes="User con password_hash usando werkzeug. Project con fecha_inicio, fecha_fin_prevista, minutos_estimados, progress y password_hash para la seguridad en borrado. Relación User→Project con backref funcionando.")
    create_session(task=s, day=date(2025, 11, 24), start_hour=10, minutos=120, tipo="desarrollo",
        objectives="Implementar Task con self-referencia para subtareas y WorkSession.",
        notes="Task.parent_task_id = db.ForeignKey('task.id') para la jerarquía. WorkSession con tarea_id, fecha, minutos, finalizada, started_at/ended_at. El campo finalizada es la clave para ignorar sesiones incompletas en los cálculos.")
    create_session(task=s, day=date(2025, 11, 27), start_hour=15, minutos=90, tipo="desarrollo",
        objectives="Implementar Milestone y generar la migración inicial completa.",
        notes="Milestone con project_id, titulo, fecha, tipo y color. Migración generada y aplicada. Tablas creadas en PostgreSQL local. Primera inserción manual desde Python shell: funcionó correctamente.")

    s = create_task(
        user=user, project=project, titulo="Autenticación con JWT",
        descripcion="Login/registro con Flask-JWT-Extended, rutas protegidas y /api/me.",
        categoria="Desarrollo", estado="finalizada", color="#2563eb",
        fecha_inicio=date(2025, 11, 28), fecha_fin=date(2025, 12, 5),
        minutos_estimados=480, parent_task=f4,
    )
    create_session(task=s, day=date(2025, 11, 29), start_hour=10, minutos=120, tipo="desarrollo",
        objectives="Implementar POST /api/auth/login y POST /api/auth/register con JWT.",
        notes="Login devuelve access_token JWT firmado con SECRET_KEY. Register con validación de unicidad de username/email. Primer test con curl: token generado correctamente. La autenticación base está lista para proteger el resto de rutas.")
    create_session(task=s, day=date(2025, 11, 30), start_hour=15, minutos=90, tipo="desarrollo",
        objectives="Implementar GET /api/me y el decorator @jwt_required() en rutas protegidas.",
        notes="/api/me devuelve el usuario del token. El decorator protege todas las rutas de recursos. Sin token válido devuelve 401. La seguridad base es operativa.")
    create_session(task=s, day=date(2025, 12, 3), start_hour=10, minutos=60, tipo="validación",
        objectives="Probar el flujo completo de autenticación.",
        notes="Flujo completo: register → login → token → /me. Todo funciona. Base lista para conectar el cliente React.")

    # API REST con sub-subtareas (tercer nivel)
    t_api = create_task(
        user=user, project=project, titulo="API REST",
        descripcion="Endpoints CRUD completos: proyectos, tareas, sesiones e hitos.",
        categoria="Desarrollo", estado="finalizada", color="#2563eb",
        fecha_inicio=date(2025, 12, 3), fecha_fin=date(2025, 12, 17),
        minutos_estimados=1440, parent_task=f4,
    )
    s = create_task(
        user=user, project=project, titulo="Endpoints de proyectos",
        descripcion="GET /projects, POST /projects, PUT /projects/:id, DELETE /projects/:id.",
        categoria="Desarrollo", estado="finalizada", color="#2563eb",
        fecha_inicio=date(2025, 12, 3), fecha_fin=date(2025, 12, 7),
        minutos_estimados=360, parent_task=t_api,
    )
    create_session(task=s, day=date(2025, 12, 4), start_hour=10, minutos=120, tipo="desarrollo",
        objectives="Implementar GET /api/projects y POST /api/projects.",
        notes="GET devuelve los proyectos del usuario autenticado. POST crea proyecto con nombre, descripción, categoría, color, fechas y minutos estimados. La validación de campos obligatorios resultó más trabajosa de lo esperado pero quedó limpia.")
    create_session(task=s, day=date(2025, 12, 6), start_hour=10, minutos=90, tipo="desarrollo",
        objectives="Implementar PUT y DELETE /api/projects/:id con seguridad.",
        notes="DELETE requiere contraseña del proyecto. La lógica se centralizó en services/projects_service.py, no en routes.py. Buena decisión arquitectónica que se repetiría para tareas. La ruta solo delega, el service decide.")
    create_session(task=s, day=date(2025, 12, 7), start_hour=15, minutos=60, tipo="validación",
        objectives="Verificar todos los endpoints de proyectos.",
        notes="CRUD de proyectos completamente verificado. El /api/projects/:id/stats devuelve minutos_estimados, minutos_reales y progreso de forma correcta. Base sólida para los endpoints de tareas.")

    s = create_task(
        user=user, project=project, titulo="Endpoints de tareas",
        descripcion="CRUD de tareas con jerarquía padre-hija, estados y seguridad en borrado.",
        categoria="Desarrollo", estado="finalizada", color="#2563eb",
        fecha_inicio=date(2025, 12, 7), fecha_fin=date(2025, 12, 11),
        minutos_estimados=360, parent_task=t_api,
    )
    create_session(task=s, day=date(2025, 12, 8), start_hour=10, minutos=120, tipo="desarrollo",
        objectives="Implementar CRUD de tareas con parent_task_id y los cuatro estados.",
        notes="Tareas con parent_task_id opcional. Los estados pendiente/en_progreso/en_pausa/finalizada validados en backend. DELETE /tasks/:id verifica la contraseña del proyecto consultando la BD sin que el frontend la maneje.")
    create_session(task=s, day=date(2025, 12, 10), start_hour=15, minutos=90, tipo="validación",
        objectives="Probar la jerarquía de subtareas y la seguridad en borrado.",
        notes="Creación de tarea padre, subtarea hija y sub-subtarea funcionando. Borrado con contraseña correcta elimina la tarea y sus sesiones en cascada. Con contraseña incorrecta devuelve 403.")
    create_session(task=s, day=date(2025, 12, 11), start_hour=10, minutos=60, tipo="validación",
        objectives="Verificar el endpoint de estadísticas de tarea.",
        notes="GET /tasks/:id/stats devuelve minutos_estimados, minutos_reales y progreso. La suma de sesiones finalizadas como tiempo real es correcta. Endpoints de tareas listos.")

    s = create_task(
        user=user, project=project, titulo="Endpoints de sesiones",
        descripcion="Crear, finalizar y actualizar sesiones con minutos y notas JSON.",
        categoria="Desarrollo", estado="finalizada", color="#2563eb",
        fecha_inicio=date(2025, 12, 11), fecha_fin=date(2025, 12, 14),
        minutos_estimados=300, parent_task=t_api,
    )
    create_session(task=s, day=date(2025, 12, 12), start_hour=10, minutos=120, tipo="desarrollo",
        objectives="Implementar POST, GET y PATCH para sesiones de trabajo.",
        notes="Sesión se crea con minutos=0 y finalizada=False. Al finalizar, se actualizan minutos y finalizada=True. Las sesiones no finalizadas no cuentan en los cálculos. Se corrigió el bug donde crear sesión con minutos=0 fallaba por validación incorrecta.")
    create_session(task=s, day=date(2025, 12, 13), start_hour=15, minutos=75, tipo="validación",
        objectives="Probar el flujo completo de sesión: crear → trabajar → finalizar.",
        notes="Flujo verificado: POST crea sesión vacía, PATCH /sessions/:id/finish actualiza minutos y marca como finalizada. El cálculo de tiempo real suma solo sesiones finalizadas. Correcto.")

    s = create_task(
        user=user, project=project, titulo="Endpoints de hitos",
        descripcion="CRUD de hitos de proyecto: fecha, tipo (reunión/hito/entrega) y color.",
        categoria="Desarrollo", estado="finalizada", color="#2563eb",
        fecha_inicio=date(2025, 12, 14), fecha_fin=date(2025, 12, 17),
        minutos_estimados=240, parent_task=t_api,
    )
    create_session(task=s, day=date(2025, 12, 15), start_hour=10, minutos=90, tipo="desarrollo",
        objectives="Implementar CRUD de hitos de proyecto.",
        notes="Hitos con project_id, titulo, descripcion, fecha, tipo y color. El tipo determina el icono en el calendario. Implementación rápida al tener ya toda la infraestructura montada.")
    create_session(task=s, day=date(2025, 12, 17), start_hour=15, minutos=60, tipo="validación",
        objectives="Verificar hitos desde los endpoints.",
        notes="Hitos creados y recuperados correctamente. La integración con el calendario visual quedará para el frontend. Endpoint de hitos listo.")

    s = create_task(
        user=user, project=project, titulo="Seguridad: contraseña de proyecto",
        descripcion="Protección de operaciones destructivas centralizada en services/.",
        categoria="Desarrollo", estado="finalizada", color="#2563eb",
        fecha_inicio=date(2025, 12, 16), fecha_fin=date(2025, 12, 19),
        minutos_estimados=240, parent_task=f4,
    )
    create_session(task=s, day=date(2025, 12, 17), start_hour=10, minutos=90, tipo="desarrollo",
        objectives="Centralizar la lógica de seguridad para borrados en services/.",
        notes="delete_task consulta project.password_hash directamente desde la BD. La ruta solo delega, el service decide. Arquitectura limpia y difícil de saltarse desde el cliente.")
    create_session(task=s, day=date(2025, 12, 18), start_hour=15, minutos=60, tipo="validación",
        objectives="Probar todos los caminos de seguridad en el borrado.",
        notes="Tests manuales: contraseña correcta borra, incorrecta devuelve 403, token inválido devuelve 401. La jerarquía de seguridad funciona. Backend cerrado y listo para el frontend.")

    # ─────────────────────────────────────────────────────────────────────────
    # FASE 5 · Desarrollo del frontend React/Vite  (60 h)
    # ─────────────────────────────────────────────────────────────────────────
    f5 = create_task(
        user=user, project=project,
        titulo="Desarrollo del frontend React/Vite",
        descripcion="Cliente API con JWT, páginas principales, calendario anual y conexión con el backend.",
        categoria="Desarrollo", estado="finalizada", color="#06b6d4",
        fecha_inicio=date(2025, 12, 5), fecha_fin=date(2026, 1, 24),
        minutos_estimados=3600,
    )
    s = create_task(
        user=user, project=project, titulo="Estructura React/Vite y cliente API",
        descripcion="Proyecto Vite, estructura de carpetas y apiFetch con JWT.",
        categoria="Desarrollo", estado="finalizada", color="#06b6d4",
        fecha_inicio=date(2025, 12, 5), fecha_fin=date(2025, 12, 12),
        minutos_estimados=480, parent_task=f5,
    )
    create_session(task=s, day=date(2025, 12, 5), start_hour=10, minutos=120, tipo="desarrollo",
        objectives="Crear el proyecto React con Vite y definir la estructura de carpetas.",
        notes="Proyecto Vite + React creado en frontworkatrack/. Estructura: src/pages/, src/components/, src/api/. Tailwind CSS configurado. El scaffolding está limpio y listo.")
    create_session(task=s, day=date(2025, 12, 9), start_hour=10, minutos=90, tipo="desarrollo",
        objectives="Implementar el cliente API con apiFetch y gestión de JWT en localStorage.",
        notes="src/api/client.js con VITE_API_BASE_URL || 'http://127.0.0.1:8000/api'. apiFetch prepende la base URL y añade el header Authorization con el JWT. Todas las llamadas futuras irán por este cliente.")
    create_session(task=s, day=date(2025, 12, 11), start_hour=15, minutos=75, tipo="validación",
        objectives="Verificar que el cliente API conecta con el backend Flask.",
        notes="Primera llamada real desde React: GET /api/health → {status: ok}. GET /api/me con token real: devuelve el usuario. El puente frontend↔backend funciona perfectamente.")

    s = create_task(
        user=user, project=project, titulo="Login y registro",
        descripcion="LoginPage y RegisterPage con JWT, contexto de auth y rutas protegidas.",
        categoria="Desarrollo", estado="finalizada", color="#06b6d4",
        fecha_inicio=date(2025, 12, 12), fecha_fin=date(2025, 12, 18),
        minutos_estimados=480, parent_task=f5,
    )
    create_session(task=s, day=date(2025, 12, 13), start_hour=10, minutos=120, tipo="desarrollo",
        objectives="Implementar LoginPage con formulario y almacenamiento del JWT.",
        notes="LoginPage con formulario usuario/contraseña. Al recibir el token se guarda en localStorage y se redirige a /projects. El estado de autenticación se gestiona con contexto React. Primera sesión real: login con demo/demo1234 funcionando.")
    create_session(task=s, day=date(2025, 12, 16), start_hour=10, minutos=90, tipo="desarrollo",
        objectives="Implementar RegisterPage y las rutas protegidas en el router.",
        notes="RegisterPage implementada. Las rutas protegidas redirigen a /login sin token válido. El flujo de acceso está completo.")
    create_session(task=s, day=date(2025, 12, 18), start_hour=15, minutos=60, tipo="validación",
        objectives="Probar el flujo completo: register → login → navegar → logout.",
        notes="Flujo completo verificado. El token persiste al refrescar la página. El logout limpia localStorage y redirige. Autenticación en el frontend cerrada.")

    s = create_task(
        user=user, project=project, titulo="Página principal de proyectos",
        descripcion="ProjectsPage con listado, creación rápida y métricas de tiempo.",
        categoria="Desarrollo", estado="finalizada", color="#06b6d4",
        fecha_inicio=date(2025, 12, 18), fecha_fin=date(2025, 12, 31),
        minutos_estimados=600, parent_task=f5,
    )
    create_session(task=s, day=date(2025, 12, 19), start_hour=10, minutos=120, tipo="desarrollo",
        objectives="Implementar ProjectsPage que carga proyectos reales del backend.",
        notes="Primera página conectada al backend. GET /api/projects devuelve los proyectos. Se renderizan en tarjetas con nombre, categoría, color y progreso. La transición de datos locales a datos del backend fue limpia.")
    create_session(task=s, day=date(2025, 12, 22), start_hour=10, minutos=90, tipo="desarrollo",
        objectives="Añadir el botón de crear proyecto con modal.",
        notes="Modal de creación de proyecto: solo pide nombre, la fecha por defecto es hoy. El botón queda a la derecha del título Mis proyectos, no debajo. Al crear, se recarga la lista desde el backend.")
    create_session(task=s, day=date(2025, 12, 26), start_hour=10, minutos=90, tipo="desarrollo",
        objectives="Añadir las métricas básicas de cada proyecto en la tarjeta.",
        notes="Cada tarjeta muestra tiempo estimado vs real y barra de progreso. Los datos vienen de GET /api/projects/:id/stats. La página tiene ya valor informativo real.")
    create_session(task=s, day=date(2025, 12, 30), start_hour=11, minutos=75, tipo="validación",
        objectives="Verificar la página con varios proyectos reales.",
        notes="Prueba con 3 proyectos. Las métricas son correctas. El layout con calendario fijo y scroll en la columna izquierda funciona bien. Página lista.")

    s = create_task(
        user=user, project=project, titulo="Detalle de proyecto",
        descripcion="ProjectDetailPage: lista de tareas, creación/edición/borrado y vista en columnas.",
        categoria="Desarrollo", estado="finalizada", color="#06b6d4",
        fecha_inicio=date(2025, 12, 31), fecha_fin=date(2026, 1, 12),
        minutos_estimados=720, parent_task=f5,
    )
    create_session(task=s, day=date(2026, 1, 2), start_hour=10, minutos=120, tipo="desarrollo",
        objectives="Implementar ProjectDetailPage con lista de tareas y modal de creación.",
        notes="ProjectDetailPage muestra las tareas del proyecto con estado, color y fechas. El modal de creación pide título, descripción, fechas y estimación. Primera tarea creada desde el frontend: aparece en la lista inmediatamente.")
    create_session(task=s, day=date(2026, 1, 5), start_hour=10, minutos=120, tipo="desarrollo",
        objectives="Añadir edición, cambio de estado y borrado de tareas.",
        notes="Edición inline con modal. Cambio de estado con botones de acción. Borrado con confirmación y contraseña del proyecto. Todos los cambios se persisten en el backend.")
    create_session(task=s, day=date(2026, 1, 8), start_hour=10, minutos=90, tipo="desarrollo",
        objectives="Implementar la vista en columnas por estado.",
        notes="Vista de columnas: pendiente / en progreso / en pausa / finalizada. Las tareas se agrupan por estado. El botón de cambio de vista funciona. Las columnas ocupan el ancho completo ocultando el calendario con style={{ width: '100%', maxWidth: 'none' }}.")
    create_session(task=s, day=date(2026, 1, 12), start_hour=15, minutos=90, tipo="validación",
        objectives="Verificar todos los flujos de ProjectDetailPage con datos reales.",
        notes="Prueba completa: crear, editar, cambiar estado, borrar, ver columnas. Todo funciona con datos reales del backend. El ProjectSummaryBox con el botón minimizar/maximizar también quedó bien.")

    s = create_task(
        user=user, project=project, titulo="Detalle de tarea y sesiones",
        descripcion="TaskDetailPage: subtareas, sesiones de trabajo y estadísticas de tiempo.",
        categoria="Desarrollo", estado="finalizada", color="#06b6d4",
        fecha_inicio=date(2026, 1, 12), fecha_fin=date(2026, 1, 18),
        minutos_estimados=600, parent_task=f5,
    )
    create_session(task=s, day=date(2026, 1, 13), start_hour=10, minutos=120, tipo="desarrollo",
        objectives="Implementar TaskDetailPage con las sesiones de trabajo de la tarea.",
        notes="TaskDetailPage carga la tarea, sus sesiones y las subtareas de primer nivel. Las sesiones muestran fecha, duración, tipo y notas. El botón de nueva sesión arranca el temporizador.")
    create_session(task=s, day=date(2026, 1, 15), start_hour=10, minutos=90, tipo="desarrollo",
        objectives="Implementar el flujo de crear sesión, trabajar y finalizar.",
        notes="Flujo: nueva sesión → cronómetro → finalizar → guarda minutos. Se corrigió el bug donde crear sesión con minutos=0 fallaba. Ahora permite minutos=0 al arrancar y los actualiza al finalizar.")
    create_session(task=s, day=date(2026, 1, 17), start_hour=15, minutos=90, tipo="validación",
        objectives="Verificar las estadísticas de tiempo en TaskSummaryBox.",
        notes="TaskSummaryBox muestra minutos estimados, reales y progreso correctamente. Las sesiones no finalizadas no cuentan. El tiempo total cuadra con la suma manual. Página lista.")

    s = create_task(
        user=user, project=project, titulo="Calendario anual del proyecto",
        descripcion="ProjectYearCalendar: círculos para inicio de tarea, triángulos para fin, cuadrados para hitos.",
        categoria="Desarrollo", estado="finalizada", color="#06b6d4",
        fecha_inicio=date(2026, 1, 18), fecha_fin=date(2026, 1, 24),
        minutos_estimados=480, parent_task=f5,
    )
    create_session(task=s, day=date(2026, 1, 19), start_hour=10, minutos=120, tipo="desarrollo",
        objectives="Implementar el calendario anual con círculos, triángulos y cuadrados.",
        notes="ProjectYearCalendar muestra los 12 meses del año. Círculos = inicio de tarea, triángulos = fin, cuadrados = hitos. Los colores corresponden al color de cada tarea. La lógica de posicionamiento por día fue lo más complejo.")
    create_session(task=s, day=date(2026, 1, 22), start_hour=10, minutos=90, tipo="incidencia",
        objectives="Corregir el error 500 de Vite causado por errores JSX en el calendario.",
        notes="Error 500 causado por un JSX mal cerrado en el componente del calendario. Detectado y corregido. El calendario renderiza correctamente con datos reales.")
    create_session(task=s, day=date(2026, 1, 24), start_hour=15, minutos=60, tipo="validación",
        objectives="Verificar el calendario con un proyecto con varias tareas e hitos.",
        notes="Prueba con 10 tareas y 3 hitos: todos los símbolos en el día correcto con el color correcto. El calendario es la vista más visual de la app. Frontend básico cerrado.")

    # ─────────────────────────────────────────────────────────────────────────
    # FASE 6 · Ampliación funcional  (55 h)
    # ─────────────────────────────────────────────────────────────────────────
    f6 = create_task(
        user=user, project=project,
        titulo="Ampliación funcional",
        descripcion="Subtareas, hitos, estados, vista árbol, Gantt y mejoras visuales en calendarios.",
        categoria="Desarrollo", estado="finalizada", color="#14b8a6",
        fecha_inicio=date(2026, 1, 24), fecha_fin=date(2026, 2, 20),
        minutos_estimados=3300,
    )
    s = create_task(
        user=user, project=project, titulo="Subtareas (jerarquía padre-hija)",
        descripcion="Gestión de subtareas en ProjectDetailPage y TaskDetailPage.",
        categoria="Desarrollo", estado="finalizada", color="#14b8a6",
        fecha_inicio=date(2026, 1, 24), fecha_fin=date(2026, 1, 29),
        minutos_estimados=480, parent_task=f6,
    )
    create_session(task=s, day=date(2026, 1, 25), start_hour=10, minutos=120, tipo="desarrollo",
        objectives="Implementar la gestión de subtareas desde ProjectDetailPage.",
        notes="ProjectDetailPage muestra solo tareas raíz. Las subtareas se gestionan desde TaskDetailPage. Esta decisión simplificó mucho la UI y hace que el árbol sea más navegable. La jerarquía ya funciona en backend desde semanas atrás.")
    create_session(task=s, day=date(2026, 1, 28), start_hour=10, minutos=90, tipo="validación",
        objectives="Verificar el árbol completo de subtareas en distintos niveles.",
        notes="Árbol probado con 3 niveles de profundidad. Las subtareas aparecen en TaskDetailPage con su propio acceso a sub-subtareas. La navegación entre niveles es coherente. Funciona bien.")

    s = create_task(
        user=user, project=project, titulo="Hitos del proyecto",
        descripcion="Panel de hitos en ProjectDetailPage con tipos reunión/hito/entrega.",
        categoria="Desarrollo", estado="finalizada", color="#14b8a6",
        fecha_inicio=date(2026, 1, 28), fecha_fin=date(2026, 2, 1),
        minutos_estimados=360, parent_task=f6,
    )
    create_session(task=s, day=date(2026, 1, 29), start_hour=10, minutos=90, tipo="desarrollo",
        objectives="Implementar el panel de hitos en ProjectDetailPage.",
        notes="Panel de hitos con listado, creación y eliminación. Los tipos reunión/hito/entrega se mapean a iconos distintos en el calendario. La integración fue rápida al tener ya el backend de hitos.")
    create_session(task=s, day=date(2026, 1, 31), start_hour=15, minutos=60, tipo="validación",
        objectives="Verificar hitos en el calendario y en el Gantt.",
        notes="Los hitos aparecen como líneas verticales en el Gantt e iconos en el calendario. Pequeño bug de color corregido: los hitos tomaban el color del proyecto en vez del propio.")

    s = create_task(
        user=user, project=project, titulo="Estados de tarea y transiciones",
        descripcion="Los cuatro estados con colores visuales persistidos en BD.",
        categoria="Desarrollo", estado="finalizada", color="#14b8a6",
        fecha_inicio=date(2026, 2, 1), fecha_fin=date(2026, 2, 5),
        minutos_estimados=360, parent_task=f6,
    )
    create_session(task=s, day=date(2026, 2, 2), start_hour=10, minutos=90, tipo="desarrollo",
        objectives="Mapear los cuatro estados a texto y color correctamente.",
        notes="pendiente → gris, en_progreso → azul, en_pausa → amarillo, finalizada → verde. Las tareas finalizadas se muestran en #9ca3af independientemente de su color de tarea. El calendario usa el color propio, no el del proyecto. Todo persistido en BD.")
    create_session(task=s, day=date(2026, 2, 4), start_hour=15, minutos=75, tipo="validación",
        objectives="Verificar que los cambios de estado se persisten correctamente.",
        notes="Cambios probados en todas las combinaciones: todos persisten. El refresco de página mantiene el estado. Correcto.")

    s = create_task(
        user=user, project=project, titulo="Vista árbol del proyecto",
        descripcion="ProjectTreePage: árbol SVG interactivo con zoom y centrado automático.",
        categoria="Desarrollo", estado="finalizada", color="#14b8a6",
        fecha_inicio=date(2026, 2, 5), fecha_fin=date(2026, 2, 12),
        minutos_estimados=720, parent_task=f6,
    )
    create_session(task=s, day=date(2026, 2, 6), start_hour=10, minutos=120, tipo="desarrollo",
        objectives="Implementar ProjectTreePage con SVG y nodos de tarea.",
        notes="ProjectTreePage con árbol SVG calculado recursivamente. Nodos coloreados por estado, líneas entre padre e hijo. El centrado automático en modo por defecto se logró con scrollLeft = maxX/2 y scrollTop=0 en useLayoutEffect.")
    create_session(task=s, day=date(2026, 2, 9), start_hour=10, minutos=90, tipo="desarrollo",
        objectives="Añadir zoom y centrado en modo zoom.",
        notes="enterZoomMode centra tanto X como Y. El zoom usa transform: scale(). Los clics en nodo navegan a la tarea. El árbol quedó visualmente impresionante para la demo.")
    create_session(task=s, day=date(2026, 2, 11), start_hour=15, minutos=75, tipo="validación",
        objectives="Verificar el árbol con proyectos de distintos niveles de profundidad.",
        notes="Árbol probado con 3 niveles de profundidad. El centrado funciona bien en todos los casos. La vista árbol es uno de los puntos más visuales del TFG.")

    s = create_task(
        user=user, project=project, titulo="Colores y formas en calendarios",
        descripcion="Color propio de cada tarea, distinción de hitos con formas geométricas.",
        categoria="Desarrollo", estado="finalizada", color="#14b8a6",
        fecha_inicio=date(2026, 2, 10), fecha_fin=date(2026, 2, 14),
        minutos_estimados=360, parent_task=f6,
    )
    create_session(task=s, day=date(2026, 2, 11), start_hour=10, minutos=90, tipo="desarrollo",
        objectives="Mejorar el calendario para que use el color propio de cada tarea.",
        notes="Cada tarea tiene su color persistido en la BD (HLS generado al crear si no se pasa). Tareas finalizadas muestran #9ca3af. Hitos usan su propio color. El calendario quedó más informativo y visual.")
    create_session(task=s, day=date(2026, 2, 14), start_hour=15, minutos=60, tipo="validación",
        objectives="Verificar colores y formas en el calendario anual.",
        notes="Círculos (inicio), triángulos (fin), cuadrados (hitos). Colores correctos en todos los casos. El calendario es ahora una vista rica sin sobrecargar la UI.")

    s = create_task(
        user=user, project=project, titulo="Diagrama de Gantt",
        descripcion="GanttPage: barras de estimado vs real, hitos y comparativa visual.",
        categoria="Desarrollo", estado="finalizada", color="#14b8a6",
        fecha_inicio=date(2026, 2, 14), fecha_fin=date(2026, 2, 20),
        minutos_estimados=720, parent_task=f6,
    )
    create_session(task=s, day=date(2026, 2, 15), start_hour=10, minutos=120, tipo="desarrollo",
        objectives="Implementar GanttPage con barras de tarea, hitos y eje de tiempo.",
        notes="Gantt con SVG: barras de tiempo estimado (azul claro) y real (azul oscuro) para cada tarea. Los hitos aparecen como líneas verticales. La implementación de fechas y proporciones requirió bastante cuidado con los cálculos.")
    create_session(task=s, day=date(2026, 2, 17), start_hour=10, minutos=90, tipo="desarrollo",
        objectives="Añadir la vista comparativa estimado vs real y el filtro por estado.",
        notes="Vista comparativa superpone barras estimado y real para ver desvíos. El filtro por estado permite ver solo tareas en progreso o solo finalizadas. Útil para la demo.")
    create_session(task=s, day=date(2026, 2, 20), start_hour=15, minutos=75, tipo="validación",
        objectives="Verificar el Gantt con el proyecto WorkaTrack completo.",
        notes="Gantt verificado con el proyecto TFG completo. Barras y proporciones correctas. Hitos visibles. Es la vista más parecida a una herramienta profesional. Ampliación funcional cerrada.")

    # ─────────────────────────────────────────────────────────────────────────
    # FASE 7 · Lógica de tiempos y métricas  (30 h)
    # ─────────────────────────────────────────────────────────────────────────
    f7 = create_task(
        user=user, project=project,
        titulo="Lógica de tiempos y métricas",
        descripcion="Unidad base en minutos, estimado vs real, progreso dinámico y endpoints de estadísticas.",
        categoria="Desarrollo", estado="finalizada", color="#22c55e",
        fecha_inicio=date(2026, 2, 1), fecha_fin=date(2026, 2, 20),
        minutos_estimados=1800,
    )
    s = create_task(
        user=user, project=project, titulo="Unidad base: minutos y sesiones finalizadas",
        descripcion="Normalización de toda la lógica de tiempo a minutos como unidad base.",
        categoria="Desarrollo", estado="finalizada", color="#22c55e",
        fecha_inicio=date(2026, 2, 1), fecha_fin=date(2026, 2, 7),
        minutos_estimados=600, parent_task=f7,
    )
    create_session(task=s, day=date(2026, 2, 2), start_hour=10, minutos=90, tipo="desarrollo",
        objectives="Normalizar toda la lógica de tiempo a minutos en backend y frontend.",
        notes="Decisión tomada: todo en minutos. Sesiones no finalizadas tienen minutos=0 y no cuentan. Sesiones finalizadas tienen los minutos reales. Se limpiaron datos antiguos con predictedHours en notas. Arquitectura de tiempos estable.")
    create_session(task=s, day=date(2026, 2, 4), start_hour=15, minutos=60, tipo="validación",
        objectives="Verificar que los minutos son consistentes tras la normalización.",
        notes="Suma de minutos de sesiones finalizadas = tiempo real de la tarea. No hay sorpresas con datos legacy. La normalización de sesiones incompletas a minutos=0 fue correcta.")
    create_session(task=s, day=date(2026, 2, 6), start_hour=10, minutos=60, tipo="documentación",
        objectives="Documentar la arquitectura de tiempos como fuente de verdad.",
        notes="Arquitectura de tiempos documentada: unidad base minutos, unfinished sessions = 0, finished sessions = real. El endpoint /stats es la fuente de verdad. Lógica cerrada.")

    s = create_task(
        user=user, project=project, titulo="Endpoints de estadísticas",
        descripcion="GET /projects/:id/stats y GET /tasks/:id/stats con estimado, real y progreso.",
        categoria="Desarrollo", estado="finalizada", color="#22c55e",
        fecha_inicio=date(2026, 2, 7), fecha_fin=date(2026, 2, 14),
        minutos_estimados=720, parent_task=f7,
    )
    create_session(task=s, day=date(2026, 2, 8), start_hour=10, minutos=120, tipo="desarrollo",
        objectives="Implementar /api/projects/:id/stats y /api/tasks/:id/stats.",
        notes="Los endpoints devuelven minutos_estimados, minutos_reales y progreso calculado. El tiempo real del proyecto es la suma de sesiones finalizadas de todas sus tareas. La consistencia de la fuente de verdad era lo más importante.")
    create_session(task=s, day=date(2026, 2, 11), start_hour=15, minutos=90, tipo="validación",
        objectives="Verificar los endpoints de stats con proyectos y tareas reales.",
        notes="Stats verificadas con datos reales. ProjectSummaryBox y TaskSummaryBox consumen estos endpoints y muestran los datos correctos. La lógica de tiempos queda cerrada.")

    s = create_task(
        user=user, project=project, titulo="Cajas resumen (SummaryBox)",
        descripcion="ProjectSummaryBox y TaskSummaryBox con toggle de visibilidad.",
        categoria="Desarrollo", estado="finalizada", color="#22c55e",
        fecha_inicio=date(2026, 2, 14), fecha_fin=date(2026, 2, 20),
        minutos_estimados=480, parent_task=f7,
    )
    create_session(task=s, day=date(2026, 2, 15), start_hour=10, minutos=90, tipo="desarrollo",
        objectives="Implementar ProjectSummaryBox y TaskSummaryBox con botón minimizar/maximizar.",
        notes="Las cajas tienen botón de minimizar/maximizar. En estado minimizado solo muestran el título. Los datos de tiempo se cargan desde los endpoints de stats. La UI queda limpia y no obstruye el resto de la página.")
    create_session(task=s, day=date(2026, 2, 18), start_hour=15, minutos=60, tipo="validación",
        objectives="Verificar las cajas con distintos estados de proyecto.",
        notes="Cajas muestran datos correctos al 0%, 50% y 100%. El toggle funciona bien. Fase de tiempos y métricas cerrada.")

    # ─────────────────────────────────────────────────────────────────────────
    # FASE 8 · Contenedorización con Docker  (40 h)
    # ─────────────────────────────────────────────────────────────────────────
    f8 = create_task(
        user=user, project=project,
        titulo="Contenedorización con Docker",
        descripcion="Dockerfiles del backend y frontend, Docker Compose y migración de datos.",
        categoria="DevOps", estado="finalizada", color="#f59e0b",
        fecha_inicio=date(2026, 2, 20), fecha_fin=date(2026, 3, 10),
        minutos_estimados=2400,
    )
    s = create_task(
        user=user, project=project, titulo="Dockerfile del backend Flask",
        descripcion="Imagen Docker del backend con dependencias y punto de entrada para migraciones.",
        categoria="DevOps", estado="finalizada", color="#f59e0b",
        fecha_inicio=date(2026, 2, 20), fecha_fin=date(2026, 2, 25),
        minutos_estimados=600, parent_task=f8,
    )
    create_session(task=s, day=date(2026, 2, 21), start_hour=10, minutos=120, tipo="desarrollo",
        objectives="Escribir el Dockerfile del backend Flask y hacer el primer build.",
        notes="Dockerfile con python:3.12-slim, build-essential y libpq-dev para compilar psycopg2. El entrypoint ejecuta flask db upgrade antes de arrancar gunicorn. Primer docker build exitoso en ~3 minutos.")
    create_session(task=s, day=date(2026, 2, 23), start_hour=10, minutos=90, tipo="validación",
        objectives="Verificar que el contenedor del backend arranca y conecta con PostgreSQL.",
        notes="Contenedor arranca, conecta a PostgreSQL y responde a /api/health. La variable DATABASE_URL se inyecta como variable de entorno. El backend dockerizado funciona igual que en local.")
    create_session(task=s, day=date(2026, 2, 24), start_hour=15, minutos=60, tipo="desarrollo",
        objectives="Optimizar el Dockerfile con .dockerignore y capas de caché.",
        notes=".dockerignore añadido para excluir __pycache__, .env, venv. El tamaño de la imagen bajó de 890MB a 340MB con --no-install-recommends. La caché de capas mejora los tiempos de rebuild.")

    s = create_task(
        user=user, project=project, titulo="Dockerfile del frontend con NGINX",
        descripcion="Build multistage: Node para compilar React, NGINX para servir los estáticos.",
        categoria="DevOps", estado="finalizada", color="#f59e0b",
        fecha_inicio=date(2026, 2, 25), fecha_fin=date(2026, 3, 1),
        minutos_estimados=600, parent_task=f8,
    )
    create_session(task=s, day=date(2026, 2, 26), start_hour=10, minutos=120, tipo="desarrollo",
        objectives="Escribir el Dockerfile multistage del frontend con build React y NGINX.",
        notes="Multistage: primera etapa con node:20-alpine hace npm install y npm run build. Segunda etapa con nginx:alpine copia el dist y sirve los estáticos. NGINX no ejecuta React en runtime: cambios en código React requieren rebuild de la imagen.")
    create_session(task=s, day=date(2026, 2, 28), start_hour=10, minutos=90, tipo="validación",
        objectives="Verificar que NGINX sirve el frontend con routing de React correcto.",
        notes="nginx.conf configurado con try_files para que el routing de React funcione: rutas no encontradas redirigen a index.html. Sin esto, el reload de página en /projects/:id devuelve 404. Problema habitual en SPAs.")
    create_session(task=s, day=date(2026, 3, 1), start_hour=15, minutos=60, tipo="incidencia",
        objectives="Resolver el problema de caché de NGINX para los cambios de frontend.",
        notes="Lección aprendida: cambios en el frontend requieren docker compose build frontend --no-cache. Sin --no-cache Docker reutiliza capas antiguas y los cambios no aparecen. Procedimiento documentado para no volver a perder tiempo con esto.")

    s = create_task(
        user=user, project=project, titulo="Docker Compose completo",
        descripcion="docker-compose.yml con db, web y frontend, redes internas y volúmenes persistentes.",
        categoria="DevOps", estado="finalizada", color="#f59e0b",
        fecha_inicio=date(2026, 3, 1), fecha_fin=date(2026, 3, 6),
        minutos_estimados=720, parent_task=f8,
    )
    create_session(task=s, day=date(2026, 3, 2), start_hour=10, minutos=120, tipo="desarrollo",
        objectives="Escribir el docker-compose.yml con los tres servicios.",
        notes="Compose con servicios db (postgres:15), web (backend Flask), frontend (NGINX). Volumen postgres_data para persistir la BD. Red interna para la comunicación entre servicios. Variables de entorno para DATABASE_URL, SECRET_KEY y POSTGRES_PASSWORD.")
    create_session(task=s, day=date(2026, 3, 4), start_hour=10, minutos=90, tipo="validación",
        objectives="Levantar el stack completo y verificar el flujo de extremo a extremo.",
        notes="Stack completo funcionando: db levanta primero (healthcheck), web espera a db y ejecuta migraciones, frontend arranca. Login → crear proyecto → crear tarea → sesión: todo funciona con los tres contenedores. La beta dockerizada está lista.")
    create_session(task=s, day=date(2026, 3, 6), start_hour=15, minutos=75, tipo="desarrollo",
        objectives="Añadir el script de arranque portable y el README de uso.",
        notes="Script start_portable_demo.sh que arranca el stack, espera a que los servicios estén listos y ejecuta el seed. README con los pasos de instalación. El paquete portable está listo para demostraciones.")

    s = create_task(
        user=user, project=project, titulo="Migración y normalización de datos",
        descripcion="Limpieza de datos legacy, normalización de sesiones y verificación de consistencia.",
        categoria="DevOps", estado="finalizada", color="#f59e0b",
        fecha_inicio=date(2026, 3, 6), fecha_fin=date(2026, 3, 10),
        minutos_estimados=480, parent_task=f8,
    )
    create_session(task=s, day=date(2026, 3, 7), start_hour=10, minutos=90, tipo="desarrollo",
        objectives="Migrar datos legacy de predictedHours y normalizar sesiones incompletas.",
        notes="Se limpiaron notas JSON con predictedHours de la versión antigua. Sesiones incompletas normalizadas a minutos=0. Los datos quedan limpios y consistentes con la nueva arquitectura.")
    create_session(task=s, day=date(2026, 3, 9), start_hour=15, minutos=75, tipo="validación",
        objectives="Verificar que los cálculos de tiempo son correctos tras la migración.",
        notes="Verificación completa: tiempo estimado, real y progreso de todos los proyectos y tareas son consistentes. No hay datos legacy que rompan la lógica. Dockerización cerrada.")

    # ─────────────────────────────────────────────────────────────────────────
    # FASE 9 · Despliegue en Kubernetes  (45 h)
    # ─────────────────────────────────────────────────────────────────────────
    f9 = create_task(
        user=user, project=project,
        titulo="Despliegue en Kubernetes (Minikube)",
        descripcion="PostgreSQL StatefulSet, Deployments de API y frontend, Secrets, ConfigMap, Ingress y migraciones Alembic.",
        categoria="DevOps", estado="finalizada", color="#f97316",
        fecha_inicio=date(2026, 3, 6), fecha_fin=date(2026, 3, 27),
        minutos_estimados=2700,
    )
    s = create_task(
        user=user, project=project, titulo="Minikube y namespace workatrack",
        descripcion="Entorno Minikube con addon ingress y namespace dedicado.",
        categoria="DevOps", estado="finalizada", color="#f97316",
        fecha_inicio=date(2026, 3, 6), fecha_fin=date(2026, 3, 10),
        minutos_estimados=360, parent_task=f9,
    )
    create_session(task=s, day=date(2026, 3, 7), start_hour=10, minutos=90, tipo="desarrollo",
        objectives="Preparar Minikube con el addon ingress y crear el namespace workatrack.",
        notes="Minikube con ingress addon habilitado. Namespace workatrack creado. El contexto kubectl por defecto apunta al namespace del proyecto. La separación en namespace facilita el limpiado y el aislamiento.")
    create_session(task=s, day=date(2026, 3, 9), start_hour=15, minutos=60, tipo="validación",
        objectives="Verificar que el cluster está limpio y listo para los despliegues.",
        notes="kubectl get all -n workatrack: vacío y limpio. Ingress controller running. Listo para desplegar los servicios.")

    s = create_task(
        user=user, project=project, titulo="PostgreSQL como StatefulSet",
        descripcion="StatefulSet postgres-0 con PVC persistente y Secret con credenciales.",
        categoria="DevOps", estado="finalizada", color="#f97316",
        fecha_inicio=date(2026, 3, 10), fecha_fin=date(2026, 3, 14),
        minutos_estimados=480, parent_task=f9,
    )
    create_session(task=s, day=date(2026, 3, 10), start_hour=10, minutos=120, tipo="desarrollo",
        objectives="Desplegar PostgreSQL como StatefulSet con PVC y Secret.",
        notes="StatefulSet postgres-0 con postgres:15. PVC de 5Gi para los datos. Secret con POSTGRES_PASSWORD, POSTGRES_DB y POSTGRES_USER. El StatefulSet garantiza que el pod siempre se llama postgres-0 y el volumen persiste entre reinicios.")
    create_session(task=s, day=date(2026, 3, 12), start_hour=10, minutos=90, tipo="validación",
        objectives="Verificar que PostgreSQL levanta y acepta conexiones.",
        notes="postgres-0 Running. kubectl exec con psql verifica que la BD workatrack existe. Service postgresql-svc accesible desde el namespace. PostgreSQL listo en Kubernetes.")
    create_session(task=s, day=date(2026, 3, 14), start_hour=15, minutos=60, tipo="incidencia",
        objectives="Resolver el error 500 por tabla projects inexistente en el primer despliegue.",
        notes="La API levantó pero fallaba porque la tabla projects no existía. Solución: crear y aplicar la migración Alembic b336f32fd92b dentro del entrypoint antes de arrancar gunicorn. Reconstruir imagen y rollout restart.")

    s = create_task(
        user=user, project=project, titulo="Deployment de la API",
        descripcion="Deployment workatrack-api con ConfigMap y variables de entorno.",
        categoria="DevOps", estado="finalizada", color="#f97316",
        fecha_inicio=date(2026, 3, 14), fecha_fin=date(2026, 3, 18),
        minutos_estimados=480, parent_task=f9,
    )
    create_session(task=s, day=date(2026, 3, 15), start_hour=10, minutos=120, tipo="desarrollo",
        objectives="Crear el Deployment de la API Flask con Service y ConfigMap.",
        notes="Deployment workatrack-api con la imagen workatrack:latest. ConfigMap con DATABASE_URL apuntando a postgresql-svc. Secret referenciado para SECRET_KEY. Service ClusterIP para comunicación interna.")
    create_session(task=s, day=date(2026, 3, 17), start_hour=10, minutos=90, tipo="incidencia",
        objectives="Resolver el CrashLoopBackOff de la API por imagen desactualizada.",
        notes="La API entraba en CrashLoopBackOff porque Minikube usaba una imagen cacheada de días atrás. Solución: minikube image load workatrack:latest para forzar la imagen nueva. Después del rollout restart el pod arrancó correctamente.")
    create_session(task=s, day=date(2026, 3, 18), start_hour=15, minutos=75, tipo="validación",
        objectives="Verificar que la API responde correctamente desde dentro del cluster.",
        notes="kubectl exec con curl workatrack-api-svc/api/health → {status: ok}. Login JWT: funcionando. La API está operativa en Kubernetes.")

    s = create_task(
        user=user, project=project, titulo="Deployment del frontend y el Ingress",
        descripcion="Deployment del frontend NGINX e Ingress workatrack.local.",
        categoria="DevOps", estado="finalizada", color="#f97316",
        fecha_inicio=date(2026, 3, 18), fecha_fin=date(2026, 3, 24),
        minutos_estimados=480, parent_task=f9,
    )
    create_session(task=s, day=date(2026, 3, 19), start_hour=10, minutos=90, tipo="desarrollo",
        objectives="Crear el Deployment del frontend NGINX, su Service y el Ingress.",
        notes="Deployment workatrack-frontend con frontworkatrack:latest. Service ClusterIP. Ingress con host workatrack.local: / al frontend, /api/ a la API. Entrada en /etc/hosts del host: $(minikube ip) workatrack.local.")
    create_session(task=s, day=date(2026, 3, 21), start_hour=10, minutos=90, tipo="incidencia",
        objectives="Resolver el CrashLoopBackOff del frontend por imagen cacheada.",
        notes="Mismo problema que con la API: imagen cacheada en Minikube. Solución: minikube image load frontworkatrack:latest. La causa raíz en Minikube es siempre la misma: hay que cargar explícitamente la imagen nueva.")
    create_session(task=s, day=date(2026, 3, 24), start_hour=15, minutos=75, tipo="validación",
        objectives="Verificar el flujo completo desde workatrack.local en el browser.",
        notes="Flujo completo verificado desde el browser a través del Ingress: login → crear proyecto → tarea → sesión → stats. Todo funciona. /api/health OK, login JWT OK, POST /api/projects OK.")

    s = create_task(
        user=user, project=project, titulo="Migraciones Alembic en el clúster",
        descripcion="Estrategia de aplicación de migraciones dentro del entrypoint del contenedor.",
        categoria="DevOps", estado="finalizada", color="#f97316",
        fecha_inicio=date(2026, 3, 24), fecha_fin=date(2026, 3, 27),
        minutos_estimados=360, parent_task=f9,
    )
    create_session(task=s, day=date(2026, 3, 25), start_hour=10, minutos=90, tipo="desarrollo",
        objectives="Integrar flask db upgrade en el entrypoint del contenedor de la API.",
        notes="El entrypoint ejecuta flask db upgrade antes de iniciar gunicorn. Garantiza que las migraciones están siempre aplicadas al arrancar, sin necesidad de un pod de migración separado. Simple y suficiente para el TFG.")
    create_session(task=s, day=date(2026, 3, 27), start_hour=15, minutos=75, tipo="validación",
        objectives="Verificar que al hacer rollout restart las migraciones se aplican.",
        notes="Rollout restart de la API: migraciones aplicadas antes de arrancar el servidor. No hay errores de tabla inexistente. Estrategia de migraciones en entrypoint validada. Kubernetes cerrado.")

    # ─────────────────────────────────────────────────────────────────────────
    # FASE 10 · Automatización CI/CD con GitLab  (25 h)
    # ─────────────────────────────────────────────────────────────────────────
    f10 = create_task(
        user=user, project=project,
        titulo="Automatización CI/CD con GitLab",
        descripcion="Pipeline de test y build, Kaniko para imágenes, ServiceAccount y limitaciones de red.",
        categoria="DevOps", estado="finalizada", color="#ef4444",
        fecha_inicio=date(2026, 1, 14), fecha_fin=date(2026, 3, 20),
        minutos_estimados=1500,
    )
    s = create_task(
        user=user, project=project, titulo="Pipeline de test y build",
        descripcion="Etapas test y build del .gitlab-ci.yml con pytest y construcción de imagen.",
        categoria="DevOps", estado="finalizada", color="#ef4444",
        fecha_inicio=date(2026, 1, 14), fecha_fin=date(2026, 1, 28),
        minutos_estimados=480, parent_task=f10,
    )
    create_session(task=s, day=date(2026, 1, 15), start_hour=10, minutos=120, tipo="desarrollo",
        objectives="Escribir el .gitlab-ci.yml con las etapas test y build.",
        notes="Pipeline con dos etapas: test (pytest sobre el backend Flask) y build. El stage de test usa python:3.12 y verifica que los modelos y rutas básicas funcionan. Primer pipeline verde en GitLab de Irontec.")
    create_session(task=s, day=date(2026, 1, 22), start_hour=10, minutos=90, tipo="desarrollo",
        objectives="Refinar el pipeline y añadir caché de pip para acelerar los tests.",
        notes="Caché de pip con key $CI_COMMIT_REF_SLUG. El stage de test bajó de 3 minutos a 45 segundos con caché caliente. El pipeline es estable y rápido.")

    s = create_task(
        user=user, project=project, titulo="Construcción con Kaniko",
        descripcion="Kaniko para construir imágenes Docker dentro del runner sin privilegios.",
        categoria="DevOps", estado="finalizada", color="#ef4444",
        fecha_inicio=date(2026, 1, 28), fecha_fin=date(2026, 2, 10),
        minutos_estimados=360, parent_task=f10,
    )
    create_session(task=s, day=date(2026, 1, 29), start_hour=10, minutos=120, tipo="desarrollo",
        objectives="Configurar Kaniko en el pipeline para construir y subir la imagen al registry.",
        notes="Kaniko construye la imagen sin daemon Docker. La imagen se sube al container registry de GitLab con CI_REGISTRY_USER y CI_REGISTRY_PASSWORD. El scope correcto del PAT es solo read_registry y write_registry.")
    create_session(task=s, day=date(2026, 2, 5), start_hour=15, minutos=90, tipo="validación",
        objectives="Verificar que la imagen subida al registry es correcta y arrancable.",
        notes="Imagen workatrack:latest en el registry de GitLab. docker pull desde local: descargable y arrancable. El pipeline completo (test → build → push) funciona de extremo a extremo.")

    s = create_task(
        user=user, project=project, titulo="ServiceAccount y kubeconfig seguro",
        descripcion="ServiceAccount workatrack-deployer con RBAC mínimo y kubeconfig cifrado en CI.",
        categoria="DevOps", estado="finalizada", color="#ef4444",
        fecha_inicio=date(2026, 2, 10), fecha_fin=date(2026, 2, 25),
        minutos_estimados=360, parent_task=f10,
    )
    create_session(task=s, day=date(2026, 2, 11), start_hour=10, minutos=90, tipo="desarrollo",
        objectives="Crear el ServiceAccount workatrack-deployer con RBAC mínimo.",
        notes="ServiceAccount con ClusterRole limitado a get/list/watch pods y create/update deployments en el namespace workatrack. El kubeconfig con el token del ServiceAccount se cifra como variable CI_FILE en GitLab.")
    create_session(task=s, day=date(2026, 2, 24), start_hour=15, minutos=75, tipo="validación",
        objectives="Verificar que el kubeconfig del ServiceAccount funciona desde el pipeline.",
        notes="kubectl get pods -n workatrack desde el runner usando el kubeconfig del ServiceAccount: funciona. El deployer tiene exactamente los permisos que necesita.")

    s = create_task(
        user=user, project=project, titulo="Limitaciones de red runner → Minikube",
        descripcion="Documentación del límite real: los runners de Irontec no alcanzan el Minikube local.",
        categoria="DevOps", estado="finalizada", color="#ef4444",
        fecha_inicio=date(2026, 2, 25), fecha_fin=date(2026, 3, 20),
        minutos_estimados=300, parent_task=f10,
    )
    create_session(task=s, day=date(2026, 2, 26), start_hour=10, minutos=60, tipo="análisis",
        objectives="Analizar por qué el stage de deploy no puede conectar con Minikube.",
        notes="El Minikube corre en la máquina local. Los runners compartidos de Irontec están en una red distinta y no tienen acceso a la IP de Minikube. El stage deploy_to_k8s está preparado en el pipeline pero no se ejecuta automáticamente.")
    create_session(task=s, day=date(2026, 3, 10), start_hour=15, minutos=60, tipo="documentación",
        objectives="Documentar la limitación y la solución alternativa para la memoria.",
        notes="Limitación documentada: la solución sería un runner self-hosted en la misma red. Para el TFG se demuestra el pipeline completo hasta el registry y el despliegue manual como validación del proceso. Esto tiene valor narrativo en la memoria.")

    # ─────────────────────────────────────────────────────────────────────────
    # FASE 11 · Análisis con IA y Q&A  (65 h)
    # ─────────────────────────────────────────────────────────────────────────
    f11 = create_task(
        user=user, project=project,
        titulo="Análisis con IA y Q&A",
        descripcion="Análisis de sentimiento, integración Ollama, modos FAST y DEEP, jobs asíncronos y caché semanal.",
        categoria="IA", estado="en_progreso", color="#7c3aed",
        fecha_inicio=date(2026, 3, 15), fecha_fin=date(2026, 5, 21),
        minutos_estimados=3900,
    )
    s = create_task(
        user=user, project=project, titulo="Análisis de sentimiento",
        descripcion="Análisis del tono de las notas de sesión con embeddings y scoring.",
        categoria="IA", estado="finalizada", color="#7c3aed",
        fecha_inicio=date(2026, 3, 15), fecha_fin=date(2026, 3, 22),
        minutos_estimados=600, parent_task=f11,
    )
    create_session(task=s, day=date(2026, 3, 16), start_hour=10, minutos=120, tipo="desarrollo",
        objectives="Implementar el análisis de sentimiento sobre las notas de sesión.",
        notes="Análisis usando embeddings de nomic-embed-text. Las notas JSON de las sesiones se extraen y analizan. El scoring combina palabras clave positivas/negativas con similitud de embedding respecto a frases de referencia. Primer resultado: el proyecto Atlas - Final sale positivo.")
    create_session(task=s, day=date(2026, 3, 19), start_hour=10, minutos=90, tipo="validación",
        objectives="Verificar el análisis con proyectos de distinto tono.",
        notes="Atlas - Final: positivo. Boreal - Inicio: negativo. Cobalto - Desarrollo: mixto. Los resultados son coherentes con las notas. El análisis de sentimiento funciona como herramienta diagnóstica básica.")
    create_session(task=s, day=date(2026, 3, 22), start_hour=15, minutos=75, tipo="documentación",
        objectives="Documentar la implementación para la memoria.",
        notes="Análisis de sentimiento documentado. La idea original era el requisito de análisis inicial del TFG y evolucionó hacia el Q&A más completo. La continuidad de la evolución es un argumento narrativo bueno para la memoria.")

    s = create_task(
        user=user, project=project, titulo="Integración de Ollama (descarte de vLLM)",
        descripcion="Elección de Ollama tras descartar vLLM por requisitos de GPU.",
        categoria="IA", estado="finalizada", color="#7c3aed",
        fecha_inicio=date(2026, 3, 20), fecha_fin=date(2026, 3, 28),
        minutos_estimados=480, parent_task=f11,
    )
    create_session(task=s, day=date(2026, 3, 21), start_hour=10, minutos=90, tipo="análisis",
        objectives="Evaluar vLLM y Ollama como opciones para el LLM local.",
        notes="vLLM evaluado: requiere CUDA y GPU dedicada. En CPU la inferencia es demasiado lenta para el TFG. Ollama funciona perfectamente en CPU con modelos cuantizados. Se elige Ollama. La decisión tiene valor narrativo: se probó la solución estándar y se descartó por razones reales.")
    create_session(task=s, day=date(2026, 3, 24), start_hour=10, minutos=90, tipo="desarrollo",
        objectives="Integrar Ollama con qwen2.5:3b y nomic-embed-text en la app.",
        notes="Ollama corriendo localmente con qwen2.5:3b para generación y nomic-embed-text para embeddings. La API de Ollama se consume desde el backend Flask con requests. Tiempo de respuesta en CPU: 20-60 segundos según la longitud del prompt.")
    create_session(task=s, day=date(2026, 3, 28), start_hour=15, minutos=60, tipo="validación",
        objectives="Verificar que Ollama responde correctamente desde el backend Flask.",
        notes="Primera pregunta real generada por el backend: respuesta coherente y en castellano. La integración entre Flask y Ollama es robusta. El modelo workatrack-qa-fast se crea con un Modelfile personalizado.")

    s = create_task(
        user=user, project=project, titulo="Q&A modo FAST",
        descripcion="Modo FAST con ventana reciente de 3 semanas, contexto compacto y respuesta en ~40s.",
        categoria="IA", estado="finalizada", color="#7c3aed",
        fecha_inicio=date(2026, 3, 28), fecha_fin=date(2026, 4, 12),
        minutos_estimados=720, parent_task=f11,
    )
    create_session(task=s, day=date(2026, 3, 29), start_hour=10, minutos=120, tipo="desarrollo",
        objectives="Implementar el modo FAST con contexto de las últimas 3 semanas.",
        notes="FAST toma las sesiones de las últimas QA_FAST_RECENT_WEEKS=3 semanas, construye un contexto compacto y genera la respuesta en una sola llamada a Ollama. Sin map/reduce. El contexto incluye notas recientes, estado de tareas y métricas.")
    create_session(task=s, day=date(2026, 4, 2), start_hour=10, minutos=90, tipo="desarrollo",
        objectives="Afinar el prompt FAST para respuestas en tercera persona y tono analítico.",
        notes="El prompt fuerza el rol de analista externo. Las respuestas en primera persona fueron el problema inicial. Con el prompt correcto el modo FAST describe el estado del proyecto como si fuera un informe externo.")
    create_session(task=s, day=date(2026, 4, 6), start_hour=10, minutos=90, tipo="validación",
        objectives="Verificar que FAST responde en ~40s con una pregunta de estado reciente.",
        notes="Pregunta: resumen del estado reciente del proyecto. Respuesta en 42s, answer_mode=llm, is_fallback=false. Contenido centrado en bugs recientes, tests y progreso. La ventana de 3 semanas funciona bien.")
    create_session(task=s, day=date(2026, 4, 10), start_hour=15, minutos=75, tipo="desarrollo",
        objectives="Implementar el selector de preguntas FAST vs DEEP.",
        notes="Selector que detecta preguntas sobre estado actual (→ FAST) vs preguntas históricas (→ DEEP). Usa palabras clave y elimina primeras personas. El Q&A ya enruta correctamente según el tipo de pregunta.")

    s = create_task(
        user=user, project=project, titulo="Q&A modo DEEP asíncrono",
        descripcion="Modo DEEP con map/reduce asíncrono, progress/ETA y caché semanal QaChunkSummary.",
        categoria="IA", estado="finalizada", color="#7c3aed",
        fecha_inicio=date(2026, 4, 10), fecha_fin=date(2026, 4, 28),
        minutos_estimados=900, parent_task=f11,
    )
    create_session(task=s, day=date(2026, 4, 11), start_hour=10, minutos=120, tipo="desarrollo",
        objectives="Implementar el modo DEEP con map/reduce: resumir chunks y combinar.",
        notes="DEEP divide todas las sesiones en chunks, genera un resumen de cada chunk (map) y combina en respuesta final (reduce). El proceso puede tardar 5-10 minutos en proyectos grandes. Por eso necesita ser asíncrono.")
    create_session(task=s, day=date(2026, 4, 15), start_hour=10, minutos=120, tipo="desarrollo",
        objectives="Implementar los jobs asíncronos con progreso y ETA.",
        notes="Jobs asíncronos en memoria (threading). /api/projects/:id/qa async inicia el job y devuelve un job_id. /api/qa/jobs/:job_id devuelve el estado: {progress: 45, eta_seconds: 180, status: running}. Los jobs se pierden al reiniciar la API.")
    create_session(task=s, day=date(2026, 4, 20), start_hour=10, minutos=90, tipo="desarrollo",
        objectives="Implementar la caché semanal QaChunkSummary.",
        notes="QaChunkSummary guarda el resumen de cada chunk durante 7 días. Si el chunk no ha cambiado, se reutiliza el resumen guardado. Esto reduce el tiempo de DEEP de 10 minutos a 2-3 minutos con caché caliente. La caché está en PostgreSQL y persiste entre reinicios.")
    create_session(task=s, day=date(2026, 4, 25), start_hour=15, minutos=75, tipo="incidencia",
        objectives="Resolver el bug de running eterno y los errores de LLM en el reduce.",
        notes="Bug: el job se quedaba en running eterno cuando el LLM devolvía texto truncado. Solución: mover el callback de progreso, añadir retry en reduce, limpiar fragmentos [id truncados y relajar el validador a ≥2 citas totales. El DEEP termina siempre ahora.")

    s = create_task(
        user=user, project=project, titulo="Modelo portable workatrack-qa-fast",
        descripcion="Modelfile personalizado de Ollama con parámetros optimizados para la demo.",
        categoria="IA", estado="finalizada", color="#7c3aed",
        fecha_inicio=date(2026, 4, 28), fecha_fin=date(2026, 5, 10),
        minutos_estimados=480, parent_task=f11,
    )
    create_session(task=s, day=date(2026, 4, 29), start_hour=10, minutos=90, tipo="desarrollo",
        objectives="Crear el Modelfile de workatrack-qa-fast con parámetros ajustados.",
        notes="Modelfile con FROM qwen2.5:3b y parámetros: temperature 0.3, top_p 0.9, num_ctx 4096. El modelo es una capa sobre qwen2.5:3b con el prompt de sistema del analista externo incorporado. Se crea con ollama create.")
    create_session(task=s, day=date(2026, 5, 5), start_hour=10, minutos=90, tipo="validación",
        objectives="Verificar el modelo en la demo portable con preguntas representativas.",
        notes="Cinco preguntas de test: estado actual, evolución del backend, fases más complejas, problemas técnicos, tiempo en IA. Cuatro de cinco con respuesta correcta y tono de analista. La quinta (tiempo en IA) a veces confunde FAST con DEEP.")
    create_session(task=s, day=date(2026, 5, 10), start_hour=15, minutos=60, tipo="documentación",
        objectives="Documentar los parámetros del modelo y el guion de demo.",
        notes="Guion de demo documentado: preguntas FAST (estado reciente, última semana), preguntas DEEP (evolución completa, fases más largas). El modelo y el guion están listos para la presentación.")

    s = create_task(
        user=user, project=project, titulo="Ajustes finales del Q&A (FAST v2)",
        descripcion="Correcciones de timeout, voz del analista, FAST v2 y ajustes de rendimiento.",
        categoria="IA", estado="en_progreso", color="#7c3aed",
        fecha_inicio=date(2026, 5, 10), fecha_fin=date(2026, 5, 21),
        minutos_estimados=600, parent_task=f11,
    )
    create_session(task=s, day=date(2026, 5, 12), start_hour=10, minutos=90, tipo="desarrollo",
        objectives="Configurar OLLAMA_QA_HARD_TIMEOUT_SECS=360 y QA_JOBS_TTL_SECS=86400.",
        notes="Los timeouts causaban cortes en preguntas largas. Se subió el hard timeout a 360s y el TTL de jobs a 24h. Con estos parámetros los jobs DEEP terminan sin cortes en proyectos grandes.")
    create_session(task=s, day=date(2026, 5, 16), start_hour=10, minutos=90, tipo="desarrollo",
        objectives="Implementar FAST v2 con contexto reciente más limpio y voz de analista forzada.",
        notes="FAST v2 mejora el selector para eliminar primeras personas y duplicados, reduce el peso de cliente/emoción en preguntas generales y fuerza la voz de analista externo en el prompt y en fast_repair. El resultado es más consistente.")
    create_session(task=s, day=date(2026, 5, 20), start_hour=10, minutos=75, tipo="validación",
        objectives="Verificar FAST v2 con el guion de demo.",
        notes="Estado reciente: responde en ~42s, tono de analista, sin primera persona. Se acepta que la última frase tenga tono ligeramente prospectivo si surge naturalmente del estado resumido.",
        finalizada=False)

    # ─────────────────────────────────────────────────────────────────────────
    # FASE 12 · Beta portable y validación  (20 h)
    # ─────────────────────────────────────────────────────────────────────────
    f12 = create_task(
        user=user, project=project,
        titulo="Beta portable y validación",
        descripcion="Empaquetado Docker Compose portable, seed de demo, script de arranque y validación en Ubuntu 22.04.",
        categoria="Calidad", estado="en_progreso", color="#10b981",
        fecha_inicio=date(2026, 3, 10), fecha_fin=date(2026, 5, 31),
        minutos_estimados=1200,
    )
    s = create_task(
        user=user, project=project, titulo="Empaquetado Docker Compose portable",
        descripcion="Compose portable con web, frontend, db y Ollama en un único paquete.",
        categoria="Calidad", estado="finalizada", color="#10b981",
        fecha_inicio=date(2026, 3, 10), fecha_fin=date(2026, 3, 15),
        minutos_estimados=360, parent_task=f12,
    )
    create_session(task=s, day=date(2026, 3, 11), start_hour=10, minutos=120, tipo="desarrollo",
        objectives="Crear el Compose portable con los cuatro servicios y el entrypoint de Ollama.",
        notes="Compose portable en workatrack-demo-portable-20260313-1603. Servicios: db, web, frontend, ollama. El entrypoint de Ollama descarga el modelo y crea el Modelfile workatrack-qa-fast. El stack arranca con un único docker compose up.")
    create_session(task=s, day=date(2026, 3, 14), start_hour=15, minutos=90, tipo="validación",
        objectives="Verificar que el stack portable arranca desde cero en un entorno limpio.",
        notes="Stack portable arrancado desde cero: build ~15 minutos, seed ~3 minutos, app operativa en localhost:3000. Login demo/demo1234. Q&A respondiendo. La demo portable funciona de extremo a extremo.")

    s = create_task(
        user=user, project=project, titulo="Script de arranque y seed de demo",
        descripcion="start_portable_demo.sh con healthchecks y seed automático de datos demo.",
        categoria="Calidad", estado="finalizada", color="#10b981",
        fecha_inicio=date(2026, 3, 14), fecha_fin=date(2026, 3, 20),
        minutos_estimados=360, parent_task=f12,
    )
    create_session(task=s, day=date(2026, 3, 15), start_hour=10, minutos=90, tipo="desarrollo",
        objectives="Escribir el script de arranque con healthchecks y seed automático.",
        notes="start_portable_demo.sh: arranca el stack, espera a que db y web estén listos con curl en loop, ejecuta el seed y confirma que la app es accesible. Sin el script, arrancar la demo requería 5 pasos manuales. Ahora es un único comando.")
    create_session(task=s, day=date(2026, 3, 19), start_hour=15, minutos=90, tipo="validación",
        objectives="Verificar el seed demo con los proyectos de escenario.",
        notes="Seed con 4 arquetipos (Atlas positivo, Boreal negativo, Cobalto mixto, Nexo humano) × 3 etapas. 12 proyectos con árboles de tareas, sesiones con notas escritas y hitos. El Q&A responde bien con estos datos.")

    s = create_task(
        user=user, project=project, titulo="Validación en equipo de desarrollo",
        descripcion="Prueba completa del stack portable en el propio equipo antes de la validación externa.",
        categoria="Calidad", estado="finalizada", color="#10b981",
        fecha_inicio=date(2026, 3, 20), fecha_fin=date(2026, 4, 1),
        minutos_estimados=240, parent_task=f12,
    )
    create_session(task=s, day=date(2026, 3, 22), start_hour=10, minutos=90, tipo="validación",
        objectives="Ejecutar la validación completa del stack portable.",
        notes="Stack portable validado: todos los servicios arrancan, el seed se ejecuta, el Q&A responde, el Gantt y el árbol funcionan. Sin errores bloqueantes. La demo está lista para ser probada en un segundo equipo.")

    s = create_task(
        user=user, project=project, titulo="Validación en segundo equipo (Ubuntu 22.04)",
        descripcion="Prueba del stack en un segundo equipo Ubuntu 22.04 para verificar portabilidad real.",
        categoria="Calidad", estado="en_progreso", color="#10b981",
        fecha_inicio=date(2026, 5, 20), fecha_fin=date(2026, 5, 31),
        minutos_estimados=240, parent_task=f12,
    )
    create_session(task=s, day=date(2026, 5, 24), start_hour=10, minutos=90, tipo="validación",
        objectives="Ejecutar el stack portable en Ubuntu 22.04 desde cero.",
        notes="Stack portable ejecutado en Ubuntu 22.04. El build tardó ~18 minutos (sin caché). El seed se ejecutó correctamente. La app es accesible en localhost:3000. Portabilidad verificada en un entorno completamente diferente.",
        finalizada=False)

    # ─────────────────────────────────────────────────────────────────────────
    # FASE 13 · Documentación de la memoria del TFG  (80 h)
    # ─────────────────────────────────────────────────────────────────────────
    f13 = create_task(
        user=user, project=project,
        titulo="Documentación de la memoria del TFG",
        descripcion="Parte teórica (evolución histórica, alternativas, riesgos) y práctica (prototipo, resultados, presupuesto, conclusiones).",
        categoria="Documentación", estado="en_progreso", color="#84cc16",
        fecha_inicio=date(2026, 4, 1), fecha_fin=date(2026, 6, 15),
        minutos_estimados=4800,
    )
    s = create_task(
        user=user, project=project, titulo="Introducción, contexto y objetivos",
        descripcion="Motivación, contexto tecnológico y objetivos del TFG.",
        categoria="Documentación", estado="finalizada", color="#84cc16",
        fecha_inicio=date(2026, 4, 1), fecha_fin=date(2026, 4, 7),
        minutos_estimados=360, parent_task=f13,
    )
    create_session(task=s, day=date(2026, 4, 2), start_hour=10, minutos=90, tipo="documentación",
        objectives="Redactar la introducción del TFG con motivación y contexto.",
        notes="Introducción redactada. El contexto tecnológico (auge de contenedores, K8s como estándar, CI/CD en la industria) justifica el tema. La motivación personal de querer desplegar una app real de principio a fin da autenticidad al trabajo.")
    create_session(task=s, day=date(2026, 4, 6), start_hour=15, minutos=75, tipo="documentación",
        objectives="Redactar los objetivos del TFG y la estructura del documento.",
        notes="Objetivos definidos en la memoria. Estructura del documento establecida. Introducción cerrada.")

    # Evolución histórica con sub-subtareas
    t_evol = create_task(
        user=user, project=project, titulo="Evolución histórica del despliegue",
        descripcion="Del despliegue tradicional a los contenedores y orquestadores.",
        categoria="Documentación", estado="finalizada", color="#84cc16",
        fecha_inicio=date(2026, 4, 7), fecha_fin=date(2026, 4, 18),
        minutos_estimados=600, parent_task=f13,
    )
    s = create_task(
        user=user, project=project, titulo="Despliegue tradicional y monolitos",
        descripcion="Bare-metal, dependencias en conflicto y falta de aislamiento.",
        categoria="Documentación", estado="finalizada", color="#84cc16",
        fecha_inicio=date(2026, 4, 7), fecha_fin=date(2026, 4, 10),
        minutos_estimados=150, parent_task=t_evol,
    )
    create_session(task=s, day=date(2026, 4, 8), start_hour=10, minutos=90, tipo="documentación",
        objectives="Redactar la sección sobre despliegue tradicional y monolitos.",
        notes="Sección redactada: bare-metal, dependencias en conflicto entre aplicaciones, falta de aislamiento, coste de mantener N servidores físicos. El problema motivó la virtualización. Tono descriptivo y directo.")
    s = create_task(
        user=user, project=project, titulo="Virtualización",
        descripcion="Hipervisores, VMs y el salto en densidad de servidores.",
        categoria="Documentación", estado="finalizada", color="#84cc16",
        fecha_inicio=date(2026, 4, 10), fecha_fin=date(2026, 4, 12),
        minutos_estimados=150, parent_task=t_evol,
    )
    create_session(task=s, day=date(2026, 4, 11), start_hour=10, minutos=75, tipo="documentación",
        objectives="Redactar la sección sobre virtualización con hipervisores y VMs.",
        notes="Hipervisores tipo 1 (VMware ESXi, KVM) y tipo 2, aislamiento entre VMs, overhead de arranque y memoria. La virtualización resolvió el aislamiento pero introdujo overhead. El camino hacia contenedores queda motivado.")
    s = create_task(
        user=user, project=project, titulo="Contenedores",
        descripcion="Docker y contenedores: diferencias con VMs, capas de imagen y ecosistema.",
        categoria="Documentación", estado="finalizada", color="#84cc16",
        fecha_inicio=date(2026, 4, 12), fecha_fin=date(2026, 4, 15),
        minutos_estimados=180, parent_task=t_evol,
    )
    create_session(task=s, day=date(2026, 4, 13), start_hour=10, minutos=90, tipo="documentación",
        objectives="Redactar la sección sobre contenedores Docker.",
        notes="Namespaces y cgroups de Linux, capas de imagen inmutables, arranque en milisegundos. La comparativa VM vs contenedor quedó clara con una tabla. Docker democratizó los contenedores y creó el ecosistema.")
    s = create_task(
        user=user, project=project, titulo="Orquestadores",
        descripcion="Kubernetes y la necesidad de orquestar contenedores a escala.",
        categoria="Documentación", estado="finalizada", color="#84cc16",
        fecha_inicio=date(2026, 4, 15), fecha_fin=date(2026, 4, 18),
        minutos_estimados=180, parent_task=t_evol,
    )
    create_session(task=s, day=date(2026, 4, 16), start_hour=10, minutos=90, tipo="documentación",
        objectives="Redactar la sección sobre orquestadores y Kubernetes.",
        notes="El problema de gestionar cientos de contenedores manualmente, Kubernetes como solución, conceptos de Pod/Deployment/Service/Ingress. La sección conecta con la parte práctica del TFG donde se usa Kubernetes directamente.")
    create_session(task=t_evol, day=date(2026, 4, 18), start_hour=15, minutos=60, tipo="documentación",
        objectives="Revisar y cohesionar la sección de evolución histórica completa.",
        notes="Revisión de las cuatro sub-secciones. El flujo narrativo es coherente: bare-metal → VM → contenedor → orquestador. Cada paso explica por qué fue necesario el siguiente. Sección cerrada.")

    # Análisis de alternativas con sub-subtareas
    t_alt = create_task(
        user=user, project=project, titulo="Análisis de alternativas",
        descripcion="Comparativa de contenedores (Docker, Podman, LXC) y orquestadores (K8s, Swarm, Nomad).",
        categoria="Documentación", estado="finalizada", color="#84cc16",
        fecha_inicio=date(2026, 4, 18), fecha_fin=date(2026, 4, 28),
        minutos_estimados=480, parent_task=f13,
    )
    s = create_task(
        user=user, project=project, titulo="Alternativas de contenedores",
        descripcion="Docker vs Podman vs LXC: características, madurez y casos de uso.",
        categoria="Documentación", estado="finalizada", color="#84cc16",
        fecha_inicio=date(2026, 4, 18), fecha_fin=date(2026, 4, 22),
        minutos_estimados=240, parent_task=t_alt,
    )
    create_session(task=s, day=date(2026, 4, 19), start_hour=10, minutos=90, tipo="documentación",
        objectives="Redactar la comparativa de Docker, Podman y LXC.",
        notes="Tabla comparativa: Docker (daemon, ecosistema maduro, compatible con Compose/K8s), Podman (daemonless, compatibilidad OCI), LXC (system containers). Elección de Docker justificada por madurez y compatibilidad.")
    s = create_task(
        user=user, project=project, titulo="Alternativas de orquestadores",
        descripcion="Kubernetes vs Docker Swarm vs Nomad: complejidad, escalabilidad y adopción.",
        categoria="Documentación", estado="finalizada", color="#84cc16",
        fecha_inicio=date(2026, 4, 22), fecha_fin=date(2026, 4, 26),
        minutos_estimados=240, parent_task=t_alt,
    )
    create_session(task=s, day=date(2026, 4, 23), start_hour=10, minutos=90, tipo="documentación",
        objectives="Redactar la comparativa de Kubernetes, Docker Swarm y Nomad.",
        notes="Kubernetes: complejo pero estándar de facto, soporte CNCF, ecosistema enorme. Swarm: simple pero tracción decreciente. Nomad: flexible pero menos orientado a K8s-nativo. La elección de Kubernetes para el TFG está bien justificada.")
    create_session(task=t_alt, day=date(2026, 4, 28), start_hour=15, minutos=60, tipo="documentación",
        objectives="Cohesionar el análisis de alternativas y añadir la justificación de la elección.",
        notes="La justificación (Docker + Kubernetes): madurez, adopción industrial, compatibilidad entre sí y que son las tecnologías del TFG. Sección de alternativas cerrada.")

    s = create_task(
        user=user, project=project, titulo="Análisis de riesgos",
        descripcion="Tabla de riesgos del TFG: técnicos, temporales y de alcance.",
        categoria="Documentación", estado="finalizada", color="#84cc16",
        fecha_inicio=date(2026, 4, 28), fecha_fin=date(2026, 5, 2),
        minutos_estimados=240, parent_task=f13,
    )
    create_session(task=s, day=date(2026, 4, 29), start_hour=10, minutos=90, tipo="documentación",
        objectives="Redactar el análisis de riesgos del TFG.",
        notes="Riesgos: complejidad de Kubernetes (mitigado con Minikube), tiempo de desarrollo mayor en IA (ocurrió, gestionado), limitaciones de red para CI/CD completo (documentado), alcance creciente (gestionado priorizando por fases).")

    s = create_task(
        user=user, project=project, titulo="Prototipo: requisitos, análisis y diseño",
        descripcion="Sección de la memoria sobre el prototipo WorkaTrack.",
        categoria="Documentación", estado="en_progreso", color="#84cc16",
        fecha_inicio=date(2026, 5, 2), fecha_fin=date(2026, 5, 20),
        minutos_estimados=720, parent_task=f13,
    )
    create_session(task=s, day=date(2026, 5, 3), start_hour=10, minutos=120, tipo="documentación",
        objectives="Redactar los requisitos funcionales y no funcionales del prototipo.",
        notes="Requisitos funcionales iniciales: autenticación JWT, proyectos, tareas con estados, tiempo estimado/real, sesiones, stats, gráficos, Gantt, calendario. Funcionalidades añadidas: subtareas, hitos, árbol, colores, Q&A/IA. La clasificación da narrativa al documento.")
    create_session(task=s, day=date(2026, 5, 8), start_hour=10, minutos=90, tipo="documentación",
        objectives="Redactar el análisis funcional: acceso, proyectos, detalle de proyecto y tarea.",
        notes="Análisis funcional por pantalla: acceso (login/registro), proyectos (listado, métricas, creación), detalle de proyecto (tareas, columnas, calendario, hitos), detalle de tarea (sesiones, subtareas). Capturas de pantalla ilustran cada sección.",
        finalizada=False)

    s = create_task(
        user=user, project=project, titulo="Análisis, Q&A e IA: sección de la memoria",
        descripcion="Documentación del análisis de sentimiento, Q&A FAST y DEEP, y los resultados.",
        categoria="Documentación", estado="en_progreso", color="#84cc16",
        fecha_inicio=date(2026, 5, 15), fecha_fin=date(2026, 5, 28),
        minutos_estimados=480, parent_task=f13,
    )
    create_session(task=s, day=date(2026, 5, 16), start_hour=10, minutos=90, tipo="documentación",
        objectives="Redactar la sección de análisis con IA: motivación, Ollama, FAST y DEEP.",
        notes="La sección explica la evolución desde el análisis de sentimiento inicial hasta el Q&A completo. La decisión de Ollama sobre vLLM queda bien justificada. Los modos FAST y DEEP se describen con sus casos de uso y limitaciones.",
        finalizada=False)

    s = create_task(
        user=user, project=project, titulo="Resultados y validación",
        descripcion="Demo en Docker Compose, en Kubernetes y validación en Ubuntu 22.04.",
        categoria="Documentación", estado="en_progreso", color="#84cc16",
        fecha_inicio=date(2026, 5, 20), fecha_fin=date(2026, 6, 1),
        minutos_estimados=360, parent_task=f13,
    )
    create_session(task=s, day=date(2026, 5, 22), start_hour=10, minutos=90, tipo="documentación",
        objectives="Redactar la sección de resultados y validación del prototipo.",
        notes="Resultados: stack en Docker Compose, mismo stack en Kubernetes, CI/CD hasta el registry, Q&A con preguntas reales. La validación en Ubuntu 22.04 se incluirá cuando termine.",
        finalizada=False)

    create_task(
        user=user, project=project, titulo="Presupuesto y conclusiones",
        descripcion="Presupuesto del proyecto (540 h) y conclusiones del TFG.",
        categoria="Documentación", estado="pendiente", color="#84cc16",
        fecha_inicio=date(2026, 6, 1), fecha_fin=date(2026, 6, 10),
        minutos_estimados=360, parent_task=f13,
    )
    create_task(
        user=user, project=project, titulo="Revisión final",
        descripcion="Revisión ortográfica, de formato y coherencia de la memoria antes de la entrega.",
        categoria="Documentación", estado="pendiente", color="#84cc16",
        fecha_inicio=date(2026, 6, 10), fecha_fin=date(2026, 6, 15),
        minutos_estimados=480, parent_task=f13,
    )

    # ─────────────────────────────────────────────────────────────────────────
    # HITOS DEL PROYECTO
    # ─────────────────────────────────────────────────────────────────────────
    create_milestone(project=project,
        titulo="Decisión del caso práctico: WorkaTrack",
        descripcion="Se decide desarrollar WorkaTrack como prototipo del TFG.",
        fecha_hito=date(2025, 10, 20), tipo="hito", color="#94a3b8")

    create_milestone(project=project,
        titulo="Primera versión funcional del backend",
        descripcion="Backend Flask con JWT, modelos y API REST completa funcionando en local.",
        fecha_hito=date(2025, 12, 5), tipo="hito", color="#2563eb")

    create_milestone(project=project,
        titulo="Beta funcional cerrada",
        descripcion="Stack completo (Flask + React + PostgreSQL) funcionando en Docker Compose.",
        fecha_hito=date(2026, 3, 13), tipo="entrega", color="#f59e0b")

    create_milestone(project=project,
        titulo="Runtime portable con Ollama operativo",
        descripcion="Demo portable con Ollama, seed de datos y script de arranque automatizado.",
        fecha_hito=date(2026, 3, 13), tipo="entrega", color="#7c3aed")

    create_milestone(project=project,
        titulo="Validación en segundo equipo (Ubuntu 22.04)",
        descripcion="Stack portable verificado en un segundo equipo Ubuntu 22.04 desde cero.",
        fecha_hito=date(2026, 5, 28), tipo="hito", color="#10b981")

    create_milestone(project=project,
        titulo="Entrega y defensa del TFG",
        descripcion="Fecha prevista de entrega de la memoria y defensa ante el tribunal.",
        fecha_hito=date(2026, 6, 20), tipo="reunión", color="#ef4444")


# ── Main ────────────────────────────────────────────────────────────────────────

def main() -> None:
    app = create_app()

    with app.app_context():
        user = ensure_demo_user()
        delete_previous_tfg_project(user)
        build_tfg_project(user)
        db.session.commit()

        from app.models import Task, WorkSession
        task_count = Task.query.filter(
            Task.user_id == user.id,
            Task.project_id == Project.query.filter_by(
                user_id=user.id, name=PROJECT_NAME
            ).first().id,
        ).count()
        session_count = WorkSession.query.join(Task).filter(
            Task.user_id == user.id,
            Task.project_id == Project.query.filter_by(
                user_id=user.id, name=PROJECT_NAME
            ).first().id,
        ).count()

        print("[OK] Seed TFG WorkaTrack generado correctamente")
        print(f"[OK] Usuario demo: {DEMO_USERNAME}")
        print(f"[OK] Proyecto: {PROJECT_NAME}")
        print(f"[OK] Tareas creadas: {task_count}")
        print(f"[OK] Sesiones creadas: {session_count}")
        print(f"[OK] Password demo: {DEMO_PASSWORD}")
        print(f"[OK] Password del proyecto: {PROJECT_PASSWORD}")


if __name__ == "__main__":
    main()
