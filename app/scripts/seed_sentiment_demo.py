#!/usr/bin/env python3
# app/scripts/seed_sentiment_demo.py

"""
Seed de datos de prueba para análisis de sentimientos (WorkaTrack).

- Usa el usuario existente: username "gcrespo" (o email si no encuentra username).
- Usa el proyecto existente: "PruebaAnalisis".
- Crea tareas y sesiones con comentarios variados:
  - cliente, carga de trabajo, ánimo, bloqueos, motivación, comodidad
  - pre vs post (objectives vs notes) con cambios (mejora/empeora)
  - casos neutros
  - algunas sesiones NO finalizadas (minutos=0) con solo objetivos
"""

from __future__ import annotations

import json
import random
from datetime import date, timedelta

from app import create_app
from app.models import db, User, Project, Task, WorkSession


# -----------------------------
# Configuración editable rápida
# -----------------------------

TARGET_USERNAME = "gcrespo"
TARGET_EMAIL_FALLBACK = "gcrespo"  # por si no existe username, intenta email contiene esto
TARGET_PROJECT_NAME = "PruebaAnalisis"

NUM_TASKS = 14
SESSIONS_PER_TASK = 10

RANDOM_SEED = 1337  # para que sea reproducible


# -----------------------------
# Helpers
# -----------------------------

def rand_color() -> str:
    # genera color hex simple
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))


def make_notas_json(objectives: str, notes: str, started_at: str | None = None, ended_at: str | None = None) -> str:
    payload = {
        "objectives": objectives,
        "notes": notes,
        "startedAt": started_at,
        "endedAt": ended_at,
    }
    return json.dumps(payload, ensure_ascii=False)


def pick(seq):
    return random.choice(seq)


def maybe(prob: float) -> bool:
    return random.random() < prob


def ensure_user() -> User:
    # 1) busca por username exacto
    u = User.query.filter_by(username=TARGET_USERNAME).first()
    if u:
        return u

    # 2) fallback: busca por email que contenga "gcrespo" (por si el username está null)
    u = User.query.filter(User.email.ilike(f"%{TARGET_EMAIL_FALLBACK}%")).first()
    if u:
        return u

    raise RuntimeError(
        f"No encuentro usuario con username={TARGET_USERNAME!r} "
        f"ni email que contenga {TARGET_EMAIL_FALLBACK!r}. "
        f"Entra en BD y confirma users.username/email."
    )


def ensure_project(user: User) -> Project:
    p = Project.query.filter_by(user_id=user.id, name=TARGET_PROJECT_NAME).first()
    if p:
        return p

    raise RuntimeError(
        f"No encuentro el proyecto {TARGET_PROJECT_NAME!r} para el usuario {user.username or user.email}."
    )


# -----------------------------
# Generadores de texto (dataset)
# -----------------------------

CLIENTE_PRE = [
    "Hoy quiero responder al cliente y dejar clara la propuesta. Espero que la relación sea fluida.",
    "Objetivo: preparar reunión con el cliente y alinear expectativas.",
    "Voy a cerrar los puntos pendientes del cliente sin generar tensión.",
    "Quiero que el cliente quede satisfecho con el avance de hoy.",
]
CLIENTE_POST_POS = [
    "La reunión con el cliente fue bien, quedó satisfecho y la comunicación fue muy fluida.",
    "El cliente entendió los cambios y estuvo contento, hemos avanzado con buen tono.",
    "Se resolvieron dudas del cliente sin fricción. Muy positivo.",
]
CLIENTE_POST_NEG = [
    "El cliente se mostró molesto, la reunión fue tensa y hay descontento.",
    "Hubo quejas del cliente y la comunicación fue difícil, me dejó frustrado.",
    "El cliente no aceptó la propuesta, ha sido negativo y estresante.",
]

CARGA_PRE = [
    "Objetivo: sacar mucho trabajo hoy, tengo bastante carga y necesito organizarme.",
    "Quiero avanzar pero estoy con demasiadas cosas a la vez, me preocupa el estrés.",
    "Tengo muchas tareas acumuladas, intentaré priorizar para no agobiarme.",
]
CARGA_POST_POS = [
    "Al final he gestionado bien la carga, me siento cómodo y satisfecho con el avance.",
    "Ha sido intenso pero productivo, he salido motivado.",
]
CARGA_POST_NEG = [
    "Demasiada carga de trabajo, terminé cansado y agobiado. Sensación negativa.",
    "No he llegado a todo, me he frustrado y el estrés fue alto.",
]

BLOQUEO_PRE = [
    "Objetivo: resolver un bug; si me bloqueo, pediré ayuda rápido.",
    "Voy a intentar desbloquear el problema técnico sin perder demasiado tiempo.",
    "Quiero avanzar sin quedarme bloqueado, pero está difícil.",
]
BLOQUEO_POST_POS = [
    "Me bloqueé un rato pero lo resolví; acabé contento y con sensación positiva.",
    "Al final conseguí desbloquearlo y terminé bien.",
]
BLOQUEO_POST_NEG = [
    "Me quedé bloqueado, no lo resolví y terminé frustrado. Mal.",
    "No he podido avanzar, ha sido horrible y negativo.",
]

ANIMO_PRE = [
    "Hoy vengo motivado y con ganas, objetivo: avanzar con buen ritmo.",
    "Estoy un poco neutro, quiero simplemente cumplir el objetivo sin complicaciones.",
    "Me noto bajo de ánimo, intentaré hacer lo mínimo viable.",
]
ANIMO_POST_POS = [
    "Me siento genial, el día fue productivo y acabé contento.",
    "Salió perfecto, terminé motivado y satisfecho.",
]
ANIMO_POST_NEU = [
    "Sesión normal, ni bien ni mal. Resultado neutral.",
    "Cumplí lo justo, sensación neutra.",
]
ANIMO_POST_NEG = [
    "Terminé de mal humor, me frustré y fue negativo.",
    "Me sentí fatal, no avancé y acabé cansado.",
]

TIEMPO_PRE = [
    "Objetivo: estimación realista y buen control del tiempo.",
    "Quiero medir bien el tiempo y no alargarme.",
]
TIEMPO_POST_POS = [
    "Buena percepción del tiempo, fue eficiente y terminé a tiempo. Positivo.",
    "He gestionado el tiempo bien, sensación de control y comodidad.",
]
TIEMPO_POST_NEG = [
    "Se me fue el tiempo, acabé tarde y con sensación negativa.",
    "Mala gestión del tiempo, me estresé y terminé cansado.",
]


def build_task_catalog() -> list[dict]:
    """
    Catálogo de tareas con temática para asegurar variedad.
    """
    return [
        {"titulo": "Reuniones y cliente", "tema": "cliente"},
        {"titulo": "Soporte al cliente y cambios", "tema": "cliente"},
        {"titulo": "Planificación y carga de trabajo", "tema": "carga"},
        {"titulo": "Backlog y prioridades", "tema": "carga"},
        {"titulo": "Resolver bug crítico", "tema": "bloqueo"},
        {"titulo": "Depurar error en producción", "tema": "bloqueo"},
        {"titulo": "Trabajo rutinario / mantenimiento", "tema": "animo"},
        {"titulo": "Documentación y limpieza", "tema": "animo"},
        {"titulo": "Estimación y control de tiempos", "tema": "tiempo"},
        {"titulo": "Optimización de tiempos", "tema": "tiempo"},
        {"titulo": "Tarea mixta A", "tema": "mix"},
        {"titulo": "Tarea mixta B", "tema": "mix"},
        {"titulo": "Tarea mixta C", "tema": "mix"},
        {"titulo": "Tarea mixta D", "tema": "mix"},
    ]


def make_session_texts(tema: str) -> tuple[str, str, str]:
    """
    Devuelve (pre_objectives, post_notes, label_hint)
    label_hint es solo para depurar dataset (no se guarda)
    """
    # distribución de resultados: queremos variedad (pos/neu/neg) + cambios
    outcome = random.random()

    if tema == "cliente":
        pre = pick(CLIENTE_PRE)
        if outcome < 0.55:
            post = pick(CLIENTE_POST_POS)
            return pre, post, "positive"
        else:
            post = pick(CLIENTE_POST_NEG)
            return pre, post, "negative"

    if tema == "carga":
        pre = pick(CARGA_PRE)
        if outcome < 0.45:
            post = pick(CARGA_POST_POS)
            return pre, post, "positive"
        else:
            post = pick(CARGA_POST_NEG)
            return pre, post, "negative"

    if tema == "bloqueo":
        pre = pick(BLOQUEO_PRE)
        if outcome < 0.45:
            post = pick(BLOQUEO_POST_POS)
            return pre, post, "positive"
        else:
            post = pick(BLOQUEO_POST_NEG)
            return pre, post, "negative"

    if tema == "tiempo":
        pre = pick(TIEMPO_PRE)
        if outcome < 0.50:
            post = pick(TIEMPO_POST_POS)
            return pre, post, "positive"
        else:
            post = pick(TIEMPO_POST_NEG)
            return pre, post, "negative"

    # "animo" o "mix"
    pre = pick(ANIMO_PRE)
    if outcome < 0.40:
        post = pick(ANIMO_POST_POS)
        return pre, post, "positive"
    if outcome < 0.70:
        post = pick(ANIMO_POST_NEU)
        return pre, post, "neutral"
    post = pick(ANIMO_POST_NEG)
    return pre, post, "negative"


# -----------------------------
# Seed principal
# -----------------------------

def main() -> None:
    random.seed(RANDOM_SEED)

    app = create_app()
    with app.app_context():
        user = ensure_user()
        project = ensure_project(user)

        print(f"[OK] Usuario: id={user.id} username={user.username} email={user.email}")
        print(f"[OK] Proyecto: id={project.id} name={project.name}")

        catalog = build_task_catalog()

        # Creamos tareas adicionales si no existen ya (por titulo)
        created_tasks: list[Task] = []
        for i in range(NUM_TASKS):
            base = catalog[i % len(catalog)]
            titulo = f"{base['titulo']} #{i+1}"
            tema = base["tema"]

            existing = Task.query.filter_by(user_id=user.id, project_id=project.id, titulo=titulo).first()
            if existing:
                created_tasks.append(existing)
                continue

            descripcion = (
                f"Tarea de pruebas para análisis de sentimientos. Tema={tema}. "
                "Usaremos sesiones con objetivos (pre) y comentarios (post) para medir cambios."
            )

            t = Task(
                user_id=user.id,
                project_id=project.id,
                titulo=titulo,
                descripcion=descripcion,
                categoria="SentimentAnalisis",
                estado="pendiente",
                color=rand_color(),
                minutos_estimados=random.choice([60, 90, 120, 180, 240]),
            )
            db.session.add(t)
            db.session.flush()  # obtener id
            created_tasks.append(t)

        db.session.commit()
        print(f"[OK] Tareas en el proyecto: {len(created_tasks)}")

        # Generamos sesiones (si ya hay muchas, no duplicamos por fecha+tipo+minutos)
        today = date.today()
        total_created = 0

        for idx, task in enumerate(created_tasks):
            # tema se infiere del titulo por simplicidad
            titulo_l = (task.titulo or "").lower()
            if "cliente" in titulo_l or "reuniones" in titulo_l or "soporte" in titulo_l:
                tema = "cliente"
            elif "carga" in titulo_l or "backlog" in titulo_l or "prioridades" in titulo_l:
                tema = "carga"
            elif "bug" in titulo_l or "depurar" in titulo_l:
                tema = "bloqueo"
            elif "tiempo" in titulo_l or "estimación" in titulo_l or "estimacion" in titulo_l:
                tema = "tiempo"
            else:
                tema = "mix"

            for j in range(SESSIONS_PER_TASK):
                # distribuimos fechas en los últimos 45 días
                days_ago = random.randint(0, 45)
                fecha_sesion = today - timedelta(days=days_ago)

                # Algunas sesiones en curso
                in_progress = maybe(0.10)

                pre, post, _hint = make_session_texts(tema)

                if in_progress:
                    # sesión NO finalizada: solo objetivos, sin notes
                    notas = make_notas_json(
                        objectives=pre,
                        notes="",
                        started_at="09:00",
                        ended_at=None,
                    )
                    minutos = 0
                    finalizada = False
                else:
                    notas = make_notas_json(
                        objectives=pre,
                        notes=post,
                        started_at="09:00",
                        ended_at="10:00",
                    )
                    minutos = random.choice([20, 30, 45, 60, 75, 90])
                    finalizada = True

                tipo = random.choice(["Focus", "Meeting", "Dev", "Admin"])

                # Evitar duplicados exactos (tarea+fecha+tipo+minutos+finalizada)
                dup = WorkSession.query.filter_by(
                    tarea_id=task.id,
                    fecha=fecha_sesion,
                    tipo=tipo,
                    minutos=minutos,
                    finalizada=finalizada,
                ).first()
                if dup:
                    continue

                ws = WorkSession(
                    tarea_id=task.id,
                    fecha=fecha_sesion,
                    minutos=minutos,
                    tipo=tipo,
                    notas=notas,
                    finalizada=finalizada,
                )
                db.session.add(ws)
                total_created += 1

        db.session.commit()
        print(f"[OK] Sesiones creadas nuevas: {total_created}")
        print("[DONE] Dataset de pruebas listo en tu proyecto 'PruebaAnalisis'.")


if __name__ == "__main__":
    main()
