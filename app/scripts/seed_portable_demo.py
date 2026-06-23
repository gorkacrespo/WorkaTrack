#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta

from werkzeug.security import generate_password_hash

from app import create_app
from app.models import (
    db,
    User,
    Project,
    Task,
    Milestone,
    WorkSession,
    QaChunkSummary,
)

DEMO_USERNAME = "demo"
DEMO_EMAIL = "demo@workatrack.local"
DEMO_PASSWORD = "demo1234"
DEMO_NOMBRE = "Tutora Demo"

PRIMARY_PROJECT_NAME = "WorkaTrack Demo Portátil"
SECONDARY_PROJECT_NAME = "Preparación de entrega TFG"
PROJECT_PASSWORD = "proyecto1234"


def make_notes(objectives: str, notes: str) -> str:
    return json.dumps(
        {
            "objectives": objectives,
            "notes": notes,
        },
        ensure_ascii=False,
    )


def d(days_ago: int) -> date:
    return date.today() - timedelta(days=days_ago)


def dt(days_ago: int, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(d(days_ago), time(hour, minute))


def ensure_demo_user() -> User:
    user = User.query.filter_by(username=DEMO_USERNAME).first()

    if not user:
        user = User(
            username=DEMO_USERNAME,
            email=DEMO_EMAIL,
            nombre=DEMO_NOMBRE,
        )
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
    task_ids = [t.id for t in Task.query.filter_by(project_id=project.id, user_id=project.user_id).all()]

    if task_ids:
        WorkSession.query.filter(WorkSession.tarea_id.in_(task_ids)).delete(synchronize_session=False)
        Task.query.filter(Task.id.in_(task_ids)).delete(synchronize_session=False)

    Milestone.query.filter_by(project_id=project.id).delete(synchronize_session=False)
    QaChunkSummary.query.filter_by(project_id=project.id, user_id=project.user_id).delete(synchronize_session=False)
    db.session.delete(project)
    db.session.flush()


def delete_previous_demo_projects(user: User) -> None:
    for name in (PRIMARY_PROJECT_NAME, SECONDARY_PROJECT_NAME):
        project = Project.query.filter_by(user_id=user.id, name=name).first()
        if project:
            wipe_project(project)


def create_project(
    *,
    user: User,
    name: str,
    description: str,
    priority: str,
    category: str,
    color: str,
    fecha_inicio: date,
    fecha_fin_prevista: date,
    minutos_estimados: int,
    progress: int,
) -> Project:
    project = Project(
        user_id=user.id,
        name=name,
        description=description,
        priority=priority,
        category=category,
        color=color,
        fecha_inicio=fecha_inicio,
        fecha_fin_prevista=fecha_fin_prevista,
        minutos_estimados=minutos_estimados,
        progress=progress,
    )
    project.password_hash = generate_password_hash(PROJECT_PASSWORD)
    db.session.add(project)
    db.session.flush()
    return project


def create_task(
    *,
    user: User,
    project: Project,
    titulo: str,
    descripcion: str,
    categoria: str,
    estado: str,
    color: str,
    fecha_inicio: date,
    fecha_fin: date,
    minutos_estimados: int,
    parent_task: Task | None = None,
) -> Task:
    task = Task(
        user_id=user.id,
        project_id=project.id,
        parent_task_id=parent_task.id if parent_task else None,
        titulo=titulo,
        descripcion=descripcion,
        categoria=categoria,
        estado=estado,
        color=color,
        fecha_plan_inicio=fecha_inicio,
        fecha_plan_fin=fecha_fin,
        minutos_estimados=minutos_estimados,
    )
    db.session.add(task)
    db.session.flush()
    return task


def create_milestone(
    *,
    project: Project,
    titulo: str,
    descripcion: str,
    fecha_hito: date,
    tipo: str,
    color: str,
) -> Milestone:
    milestone = Milestone(
        project_id=project.id,
        titulo=titulo,
        descripcion=descripcion,
        fecha=fecha_hito,
        tipo=tipo,
        color=color,
    )
    db.session.add(milestone)
    db.session.flush()
    return milestone


def create_session(
    *,
    task: Task,
    days_ago: int,
    start_hour: int,
    minutos: int,
    tipo: str,
    objectives: str,
    notes: str,
    finalizada: bool = True,
) -> WorkSession:
    started_at = dt(days_ago, start_hour, 0)
    ended_at = started_at + timedelta(minutes=minutos if finalizada else 0)

    session = WorkSession(
        tarea_id=task.id,
        fecha=d(days_ago),
        minutos=minutos if finalizada else 0,
        tipo=tipo,
        notas=make_notes(objectives, notes),
        finalizada=finalizada,
        started_at=started_at,
        ended_at=ended_at if finalizada else None,
    )
    db.session.add(session)
    db.session.flush()
    return session


def main() -> None:
    app = create_app()

    with app.app_context():
        user = ensure_demo_user()
        delete_previous_demo_projects(user)

        primary = create_project(
            user=user,
            name=PRIMARY_PROJECT_NAME,
            description=(
                "Proyecto demo de WorkaTrack preparado para una ejecución portable completa. "
                "Incluye portabilización con Docker Compose, validación funcional de la beta, "
                "métricas, Gantt, árbol de tareas, charts y material semántico suficiente para "
                "probar Q&A FAST y DEEP."
            ),
            priority="alta",
            category="Demo portable",
            color="#2563eb",
            fecha_inicio=d(35),
            fecha_fin_prevista=d(-7),
            minutos_estimados=3360,
            progress=72,
        )

        secondary = create_project(
            user=user,
            name=SECONDARY_PROJECT_NAME,
            description=(
                "Proyecto secundario de apoyo para que el listado de proyectos no quede vacío "
                "y para que la tutora vea un caso adicional más sencillo."
            ),
            priority="media",
            category="Entrega",
            color="#7c3aed",
            fecha_inicio=d(18),
            fecha_fin_prevista=d(-12),
            minutos_estimados=720,
            progress=38,
        )

        epic_portable = create_task(
            user=user,
            project=primary,
            titulo="Portabilización completa de la beta",
            descripcion="Bloque principal para convertir la beta validada en una demo local portable y reproducible.",
            categoria="Portabilidad",
            estado="en_progreso",
            color="#2563eb",
            fecha_inicio=d(30),
            fecha_fin=d(-5),
            minutos_estimados=1140,
        )

        runtime = create_task(
            user=user,
            project=primary,
            titulo="Runtime portable con Docker Compose",
            descripcion="Separación del runtime local frente al despliegue en Kubernetes.",
            categoria="Portabilidad",
            estado="finalizada",
            color="#0ea5e9",
            fecha_inicio=d(30),
            fecha_fin=d(12),
            minutos_estimados=420,
            parent_task=epic_portable,
        )

        proxy = create_task(
            user=user,
            project=primary,
            titulo="Proxy frontend hacia API local",
            descripcion="Configuración específica de NGINX para Compose sin depender de workatrack-service de Kubernetes.",
            categoria="Frontend",
            estado="finalizada",
            color="#06b6d4",
            fecha_inicio=d(30),
            fecha_fin=d(22),
            minutos_estimados=120,
            parent_task=runtime,
        )

        isolation = create_task(
            user=user,
            project=primary,
            titulo="Aislamiento de volúmenes y migraciones",
            descripcion="Separación del stack portable para evitar colisiones con volúmenes previos y asegurar una base limpia.",
            categoria="Backend",
            estado="finalizada",
            color="#0891b2",
            fecha_inicio=d(21),
            fecha_fin=d(12),
            minutos_estimados=180,
            parent_task=runtime,
        )

        ollama = create_task(
            user=user,
            project=primary,
            titulo="Ollama y modelo FAST reproducible",
            descripcion="Reconstrucción portable del modelo FAST a partir de qwen2.5:3b y preparación de nomic-embed-text.",
            categoria="IA",
            estado="finalizada",
            color="#10b981",
            fecha_inicio=d(16),
            fecha_fin=d(8),
            minutos_estimados=300,
            parent_task=epic_portable,
        )

        seed = create_task(
            user=user,
            project=primary,
            titulo="Seed demo reproducible",
            descripcion="Dataset genérico para una usuaria externa, sin hardcodes ligados a gcrespo ni a proyectos internos.",
            categoria="Datos demo",
            estado="en_progreso",
            color="#22c55e",
            fecha_inicio=d(7),
            fecha_fin=d(-2),
            minutos_estimados=240,
            parent_task=epic_portable,
        )

        epic_validation = create_task(
            user=user,
            project=primary,
            titulo="Validación funcional de la beta",
            descripcion="Bloque de verificación real de login, navegación, CRUD, Gantt, árbol, charts y Q&A.",
            categoria="QA",
            estado="en_progreso",
            color="#f59e0b",
            fecha_inicio=d(24),
            fecha_fin=d(-3),
            minutos_estimados=1320,
        )

        ui_validation = create_task(
            user=user,
            project=primary,
            titulo="Verificación UI y navegación",
            descripcion="Pruebas de login, proyectos, tareas, sesiones, persistencia y navegación entre vistas.",
            categoria="UI",
            estado="finalizada",
            color="#f97316",
            fecha_inicio=d(24),
            fecha_fin=d(9),
            minutos_estimados=420,
            parent_task=epic_validation,
        )

        qa_validation = create_task(
            user=user,
            project=primary,
            titulo="Validación Q&A FAST y DEEP",
            descripcion="Pruebas de preguntas de estado, bloqueos y cliente, con control de progreso y ETA en DEEP.",
            categoria="IA",
            estado="en_progreso",
            color="#fb7185",
            fecha_inicio=d(15),
            fecha_fin=d(-1),
            minutos_estimados=480,
            parent_task=epic_validation,
        )

        epic_delivery = create_task(
            user=user,
            project=primary,
            titulo="Entrega a tutora y documentación",
            descripcion="Preparación del arranque simple, credenciales demo y paquete final para evaluación.",
            categoria="Entrega",
            estado="pendiente",
            color="#8b5cf6",
            fecha_inicio=d(5),
            fecha_fin=d(-10),
            minutos_estimados=900,
        )

        readme_task = create_task(
            user=user,
            project=primary,
            titulo="Guía de arranque y credenciales demo",
            descripcion="Documento corto para que una usuaria externa pueda levantar y usar la beta portable.",
            categoria="Entrega",
            estado="pendiente",
            color="#a855f7",
            fecha_inicio=d(4),
            fecha_fin=d(-10),
            minutos_estimados=240,
            parent_task=epic_delivery,
        )

        package_task = create_task(
            user=user,
            project=primary,
            titulo="Paquete final para la tutora",
            descripcion="Empaquetado final de la demo portable con datos de ejemplo, Q&A y acceso listo para pruebas.",
            categoria="Entrega",
            estado="pendiente",
            color="#9333ea",
            fecha_inicio=d(3),
            fecha_fin=d(-10),
            minutos_estimados=240,
            parent_task=epic_delivery,
        )

        create_milestone(
            project=primary,
            titulo="Beta funcional cerrada",
            descripcion="La beta queda validada en UI antes de iniciar la portabilización.",
            fecha_hito=d(14),
            tipo="entrega",
            color="#2563eb",
        )
        create_milestone(
            project=primary,
            titulo="Runtime portable operativo",
            descripcion="El stack local con db, api, frontend y ollama arranca correctamente.",
            fecha_hito=d(2),
            tipo="hito",
            color="#10b981",
        )
        create_milestone(
            project=primary,
            titulo="Entrega demo a tutora",
            descripcion="Objetivo de cierre para la demo portable completa.",
            fecha_hito=d(-10),
            tipo="entrega",
            color="#8b5cf6",
        )

        create_session(
            task=proxy,
            days_ago=29,
            start_hour=9,
            minutos=85,
            tipo="configuración",
            objectives="Separar la configuración del frontend para que no dependa de Kubernetes.",
            notes="El frontend seguía apuntando a workatrack-service y eso impedía una demo local portable. Se abrió una variante específica para Compose y quedó bien encaminado.",
        )
        create_session(
            task=proxy,
            days_ago=25,
            start_hour=10,
            minutos=70,
            tipo="integración",
            objectives="Verificar que el proxy del frontend resuelva /api contra la API local.",
            notes="El proxy frontend hacia la API local quedó funcionando y la navegación básica respondió bien. Fue un avance claro y dio bastante seguridad sobre la portabilidad.",
        )
        create_session(
            task=isolation,
            days_ago=20,
            start_hour=11,
            minutos=95,
            tipo="diagnóstico",
            objectives="Levantar una base limpia y evitar choques con volúmenes anteriores.",
            notes="Apareció un DuplicateTable porque el volumen previo reutilizaba tablas viejas. El problema no estaba en la app sino en la persistencia compartida, y eso quedó identificado con bastante claridad.",
        )
        create_session(
            task=isolation,
            days_ago=17,
            start_hour=16,
            minutos=80,
            tipo="corrección",
            objectives="Aislar definitivamente el stack portable para que use su propia red y sus propios volúmenes.",
            notes="Se separó el stack con nombre propio y las migraciones ya corren sobre una base limpia. Desde ahí el arranque se volvió estable y reproducible.",
        )
        create_session(
            task=ollama,
            days_ago=14,
            start_hour=9,
            minutos=90,
            tipo="IA",
            objectives="Revisar por qué el modelo FAST no era portable fuera del entorno original.",
            notes="El Modelfile anterior apuntaba a un blob interno de Ollama y no servía para otra máquina. Quedó claro que había que reconstruirlo desde un modelo base portable.",
        )
        create_session(
            task=ollama,
            days_ago=11,
            start_hour=12,
            minutos=110,
            tipo="IA",
            objectives="Construir el modelo FAST portable a partir de qwen2.5:3b y dejar listos los embeddings.",
            notes="Se dejó workatrack-qa-fast:latest construido desde qwen2.5:3b y se preparó también nomic-embed-text. El runtime con Ollama ya no depende de blobs internos y responde bien.",
        )
        create_session(
            task=ui_validation,
            days_ago=18,
            start_hour=10,
            minutos=75,
            tipo="pruebas_ui",
            objectives="Comprobar login, proyectos, tareas, sesiones y persistencia tras recarga.",
            notes="La navegación principal, el login y la persistencia tras recarga quedaron correctos. La beta ya se sentía sólida como producto usable.",
        )
        create_session(
            task=ui_validation,
            days_ago=9,
            start_hour=17,
            minutos=95,
            tipo="pruebas_ui",
            objectives="Validar Gantt, árbol, charts y navegación entre páginas sin romper el estado.",
            notes="Gantt, árbol y charts se comportaron bien en pruebas reales. También quedó validado que salir de charts corta la consulta y volver desde otra pestaña no rompe la UI.",
        )
        create_session(
            task=qa_validation,
            days_ago=13,
            start_hour=11,
            minutos=100,
            tipo="qa_fast",
            objectives="Comprobar que FAST responde bien a preguntas de estado reciente y bloqueos.",
            notes="FAST ya devuelve resúmenes rápidos útiles sobre el estado reciente del proyecto y los bloqueos técnicos. La voz quedó bastante alineada con un análisis externo, sin perder concisión.",
        )
        create_session(
            task=qa_validation,
            days_ago=7,
            start_hour=15,
            minutos=105,
            tipo="qa_deep",
            objectives="Verificar progreso, ETA y respuestas largas en DEEP con trazabilidad suficiente.",
            notes="DEEP ofrece respuestas más profundas con progreso y ETA visibles, y eso mejora mucho la experiencia. Al principio hubo algún timeout puntual, pero el comportamiento general quedó bastante controlado.",
        )
        create_session(
            task=qa_validation,
            days_ago=2,
            start_hour=16,
            minutos=85,
            tipo="qa_semántico",
            objectives="Probar preguntas sobre cliente, bloqueos y estado general usando el material del proyecto.",
            notes="Las preguntas sobre cliente, bloqueos y estado general ya responden con bastante coherencia. Aun así conviene cerrar el seed demo para que una usuaria externa tenga datos claros desde el primer minuto.",
        )
        create_session(
            task=seed,
            days_ago=6,
            start_hour=9,
            minutos=90,
            tipo="datos_demo",
            objectives="Diseñar un seed limpio para demo externa sin depender de gcrespo ni de proyectos concretos.",
            notes="Los seeds anteriores servían para pruebas internas, pero no para una entrega portable de cara a la tutora. Era necesario rehacer esa capa para tener un caso realmente reproducible.",
        )
        create_session(
            task=seed,
            days_ago=3,
            start_hour=12,
            minutos=95,
            tipo="datos_demo",
            objectives="Preparar una usuaria demo y un proyecto semánticamente útil para Gantt, árbol, charts y Q&A.",
            notes="Se ha empezado a construir un dataset genérico con jerarquía de tareas, hitos y sesiones con contenido positivo, neutral y negativo. Queda bastante cerca de ser un seed listo para demo real.",
        )
        create_session(
            task=readme_task,
            days_ago=1,
            start_hour=18,
            minutos=45,
            tipo="documentación",
            objectives="Esbozar la guía de arranque para que una usuaria externa pueda entrar sin ayuda.",
            notes="La parte técnica principal ya está resuelta, pero todavía falta cerrar la guía corta de arranque y dejar muy claras las credenciales demo y la contraseña del proyecto.",
        )

        sec_root = create_task(
            user=user,
            project=secondary,
            titulo="Checklist de entrega del TFG",
            descripcion="Pequeño proyecto de apoyo para mostrar un segundo caso de uso en la lista de proyectos.",
            categoria="TFG",
            estado="en_progreso",
            color="#7c3aed",
            fecha_inicio=d(16),
            fecha_fin=d(-8),
            minutos_estimados=420,
        )

        sec_review = create_task(
            user=user,
            project=secondary,
            titulo="Revisar memoria y anexos",
            descripcion="Revisión de estructura, capturas y explicación técnica de la solución.",
            categoria="TFG",
            estado="en_progreso",
            color="#8b5cf6",
            fecha_inicio=d(16),
            fecha_fin=d(4),
            minutos_estimados=180,
            parent_task=sec_root,
        )

        sec_meeting = create_task(
            user=user,
            project=secondary,
            titulo="Preparar reunión con tutora",
            descripcion="Lista de puntos a enseñar en la demo y dudas abiertas para la revisión final.",
            categoria="TFG",
            estado="pendiente",
            color="#a855f7",
            fecha_inicio=d(5),
            fecha_fin=d(-8),
            minutos_estimados=120,
            parent_task=sec_root,
        )

        create_milestone(
            project=secondary,
            titulo="Revisión con tutora",
            descripcion="Punto de control previo a la entrega final.",
            fecha_hito=d(-6),
            tipo="reunión",
            color="#7c3aed",
        )

        create_session(
            task=sec_review,
            days_ago=8,
            start_hour=10,
            minutos=70,
            tipo="revisión",
            objectives="Revisar memoria y anexos para detectar huecos antes de la entrega.",
            notes="La estructura general está bien, pero conviene dejar más claro el valor de la portabilidad y la parte de contenedores.",
        )

        db.session.commit()

        print("[OK] Seed portable generado correctamente")
        print(f"[OK] Usuario demo: {DEMO_USERNAME}")
        print(f"[OK] Password demo: {DEMO_PASSWORD}")
        print(f"[OK] Proyecto principal: {PRIMARY_PROJECT_NAME}")
        print(f"[OK] Password del proyecto: {PROJECT_PASSWORD}")


if __name__ == "__main__":
    main()
