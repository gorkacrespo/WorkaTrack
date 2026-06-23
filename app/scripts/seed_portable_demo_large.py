#!/usr/bin/env python3
from __future__ import annotations

import json
import random
from datetime import date, datetime, time, timedelta

from werkzeug.security import generate_password_hash

from app import create_app
from app.models import db, User, Project, Task, Milestone, WorkSession, QaChunkSummary

RANDOM_SEED = 20260313

DEMO_USERNAME = "demo"
DEMO_EMAIL = "demo@workatrack.local"
DEMO_PASSWORD = "demo1234"
DEMO_NOMBRE = "Tutora Demo"
PROJECT_PASSWORD = "proyecto1234"

TASK_COLORS = [
    "#2563eb", "#0ea5e9", "#14b8a6", "#22c55e", "#84cc16", "#f59e0b",
    "#f97316", "#ef4444", "#ec4899", "#8b5cf6", "#7c3aed", "#06b6d4",
]

TEAM_MEMBERS = [
    "Marta", "Iñigo", "Leire", "Ane", "Unai", "Nora", "Jon", "Maialen",
    "Aitor", "Lucía", "Irati", "Gorka",
]

CLIENT_NAMES = [
    "cliente principal",
    "dirección del cliente",
    "responsable de operaciones",
    "equipo de compras",
    "patrocinador del proyecto",
    "responsable técnico del cliente",
    "equipo funcional del cliente",
]

POSITIVE_FACTORS = [
    "mejor coordinación entre áreas",
    "cliente más receptivo que en semanas anteriores",
    "mejor estimación de tiempos",
    "menos interrupciones y más foco",
    "ayuda puntual entre compañeros",
    "reducción de incidencias repetidas",
    "más confianza del equipo tras cerrar varios hitos",
    "mejor reparto de carga entre compañeros",
]

NEGATIVE_FACTORS = [
    "sobrecarga de trabajo",
    "baja laboral de una persona clave",
    "cliente que tarda en responder",
    "cambios de alcance de última hora",
    "enfado entre compañeros por prioridades",
    "olvido puntual de una entrega comprometida",
    "bloqueo técnico difícil de reproducir",
    "dependencia externa sin resolver",
    "retrabajo por definición incompleta",
]

SESSION_TYPES = [
    "análisis", "desarrollo", "seguimiento", "reunión", "documentación",
    "soporte", "planificación", "validación", "incidencia", "coordinación",
]

ARCHETYPES = [
    {
        "key": "atlas",
        "base_name": "Programa Atlas",
        "category": "Transformación operativa",
        "color": "#2563eb",
        "tone": "positive",
        "start_date": date(2025, 5, 12),
        "description": (
            "Programa amplio de transformación operativa con fuerte componente de gobierno, "
            "cliente e integración. Evoluciona de un arranque exigente a una situación mucho "
            "más ordenada y sirve para probar escenarios de avance sano."
        ),
        "epics": [
            {
                "title": "Gobierno y PMO",
                "category": "Gestión",
                "branches": [
                    {
                        "title": "Planificación maestra",
                        "chain": [
                            "Roadmap trimestral",
                            "Dependencias críticas",
                            "Replanificación por hitos",
                            "Seguimiento de compromisos",
                        ],
                        "extra": ["Presupuesto operativo", "Capacidad del equipo"],
                    },
                    {
                        "title": "Seguimiento ejecutivo",
                        "chain": [
                            "Comité quincenal",
                            "KPIs operativos",
                            "Riesgos y mitigaciones",
                            "Alineación con dirección",
                        ],
                        "extra": ["Resumen semanal", "Escalados puntuales"],
                    },
                ],
            },
            {
                "title": "Relación con cliente",
                "category": "Cliente",
                "branches": [
                    {
                        "title": "Cuenta principal",
                        "chain": [
                            "Seguimiento semanal",
                            "Gestión de expectativas",
                            "Cambios de alcance",
                            "Cierre de compromisos",
                        ],
                        "extra": ["Feedback funcional", "Validación de entregables"],
                    },
                    {
                        "title": "Patrocinio y adopción",
                        "category": "Cliente",
                        "chain": [
                            "Aprobaciones",
                            "Bloqueos institucionales",
                            "Escalados",
                            "Soporte a patrocinio",
                        ],
                        "extra": ["Usuarios clave", "Priorización de mejoras"],
                    },
                ],
            },
            {
                "title": "Tecnología y datos",
                "category": "Tecnología",
                "branches": [
                    {
                        "title": "Integraciones",
                        "chain": [
                            "API de terceros",
                            "Errores de sincronización",
                            "Dependencias externas",
                            "Normalización de contratos",
                        ],
                        "extra": ["Pruebas de intercambio", "Trazas de error"],
                    },
                    {
                        "title": "Calidad de datos",
                        "chain": [
                            "Depuración de fuentes",
                            "Reglas de validación",
                            "Monitorización",
                            "Ajuste de alarmas",
                        ],
                        "extra": ["Registros incompletos", "Cuadros de seguimiento"],
                    },
                ],
            },
        ],
    },
    {
        "key": "boreal",
        "base_name": "Proyecto Boreal",
        "category": "Recuperación de servicio",
        "color": "#dc2626",
        "tone": "negative",
        "start_date": date(2025, 4, 7),
        "description": (
            "Proyecto amplio de recuperación de servicio, con crisis inicial, cliente exigente, "
            "equipo tensionado y recuperación parcial. Ideal para probar preguntas complejas sobre "
            "bloqueos, conflictos, sobrecarga y cambio de conducta."
        ),
        "epics": [
            {
                "title": "Recuperación de servicio",
                "category": "Incidencias",
                "branches": [
                    {
                        "title": "Estabilización inicial",
                        "chain": [
                            "Incidentes críticos",
                            "Paradas no previstas",
                            "Priorización caótica",
                            "Contención manual",
                        ],
                        "extra": ["Guardias de urgencia", "Seguimiento diario"],
                    },
                    {
                        "title": "Análisis de causa",
                        "chain": [
                            "Logs incompletos",
                            "Hipótesis fallidas",
                            "Errores difíciles de reproducir",
                            "Hallazgos de raíz",
                        ],
                        "extra": ["Revisión de trazas", "Matriz de impacto"],
                    },
                ],
            },
            {
                "title": "Cliente y presión externa",
                "category": "Cliente",
                "branches": [
                    {
                        "title": "Comité de crisis",
                        "chain": [
                            "Reclamaciones",
                            "Exigencia de plazos",
                            "Cambios contradictorios",
                            "Negociación de prioridades",
                        ],
                        "extra": ["Compromisos semanales", "Respuestas pendientes"],
                    },
                    {
                        "title": "Relación deteriorada",
                        "chain": [
                            "Pérdida de confianza",
                            "Tensión en reuniones",
                            "Promesas incumplidas",
                            "Recuperación parcial del tono",
                        ],
                        "extra": ["Cambio de interlocutor", "Aprobaciones tardías"],
                    },
                ],
            },
            {
                "title": "Equipo tensionado",
                "category": "Equipo",
                "branches": [
                    {
                        "title": "Sobrecarga",
                        "chain": [
                            "Horas extra",
                            "Tareas simultáneas",
                            "Fatiga acumulada",
                            "Redistribución de carga",
                        ],
                        "extra": ["Cobertura urgente", "Foco interrumpido"],
                    },
                    {
                        "title": "Conflictos internos",
                        "chain": [
                            "Choques de prioridades",
                            "Enfados entre compañeros",
                            "Olvidos puntuales",
                            "Intentos de reconducción",
                        ],
                        "extra": ["Bajas y cobertura", "Onboarding improvisado"],
                    },
                ],
            },
        ],
    },
    {
        "key": "cobalto",
        "base_name": "Iniciativa Cobalto",
        "category": "Modernización técnica",
        "color": "#0ea5e9",
        "tone": "mixed",
        "start_date": date(2025, 3, 17),
        "description": (
            "Proyecto técnico de modernización de plataforma con mucha dependencia externa, "
            "integraciones complejas y picos de bloqueo. Da contexto rico para Q&A técnico y para "
            "ver árboles profundos de tareas tecnológicas."
        ),
        "epics": [
            {
                "title": "Arquitectura objetivo",
                "category": "Arquitectura",
                "branches": [
                    {
                        "title": "Diseño de plataforma",
                        "chain": [
                            "Estado actual",
                            "Arquitectura objetivo",
                            "Brechas técnicas",
                            "Plan de transición",
                        ],
                        "extra": ["Capacidad de entorno", "Decisiones técnicas"],
                    },
                    {
                        "title": "Seguridad y gobierno",
                        "chain": [
                            "Controles base",
                            "Revisión de permisos",
                            "Excepciones y riesgos",
                            "Validación final",
                        ],
                        "extra": ["Cumplimiento", "Dependencias de auditoría"],
                    },
                ],
            },
            {
                "title": "Integraciones y despliegue",
                "category": "Tecnología",
                "branches": [
                    {
                        "title": "Integración con terceros",
                        "chain": [
                            "Contratos de API",
                            "Errores de mapping",
                            "Retry y resiliencia",
                            "Cierre de incidencias",
                        ],
                        "extra": ["Sandbox inestable", "Validación de flujos"],
                    },
                    {
                        "title": "Cadena de despliegue",
                        "chain": [
                            "Pipelines",
                            "Rollback y recovery",
                            "Observabilidad",
                            "Checklist de release",
                        ],
                        "extra": ["Alertas ruidosas", "Despliegues fallidos"],
                    },
                ],
            },
            {
                "title": "Datos y explotación",
                "category": "Datos",
                "branches": [
                    {
                        "title": "Calidad de datos",
                        "chain": [
                            "Fuentes inconsistentes",
                            "Reglas de negocio",
                            "Consolidación",
                            "Seguimiento de calidad",
                        ],
                        "extra": ["Etiquetas de error", "Cuadros de control"],
                    },
                    {
                        "title": "Soporte a usuarios",
                        "chain": [
                            "Casos de uso",
                            "Pruebas funcionales",
                            "Ajustes de adopción",
                            "Cierre de feedback",
                        ],
                        "extra": ["Documentación útil", "Formación rápida"],
                    },
                ],
            },
        ],
    },
    {
        "key": "nexo",
        "base_name": "Programa Nexo",
        "category": "Coordinación transversal",
        "color": "#7c3aed",
        "tone": "human",
        "start_date": date(2025, 6, 2),
        "description": (
            "Proyecto transversal con mucha coordinación entre áreas, alto componente humano y "
            "dependencia fuerte del cliente. Sirve para probar preguntas sobre clima, comunicación, "
            "alineación y evolución de relaciones."
        ),
        "epics": [
            {
                "title": "Coordinación transversal",
                "category": "Coordinación",
                "branches": [
                    {
                        "title": "Roles y responsabilidades",
                        "chain": [
                            "Mapa de actores",
                            "Vacíos de responsabilidad",
                            "Ajustes de ownership",
                            "Seguimiento de acuerdos",
                        ],
                        "extra": ["Cobertura de vacaciones", "Puntos de bloqueo"],
                    },
                    {
                        "title": "Cadencia de trabajo",
                        "chain": [
                            "Rituales semanales",
                            "Interrupciones frecuentes",
                            "Nuevas reglas de coordinación",
                            "Estabilización de la cadencia",
                        ],
                        "extra": ["Actas incompletas", "Priorización cruzada"],
                    },
                ],
            },
            {
                "title": "Relación con cliente y negocio",
                "category": "Cliente",
                "branches": [
                    {
                        "title": "Gestión de expectativas",
                        "chain": [
                            "Promesas iniciales",
                            "Ajuste de alcance",
                            "Negociación de prioridades",
                            "Cierre de expectativas",
                        ],
                        "extra": ["Respuesta comercial", "Validación intermedia"],
                    },
                    {
                        "title": "Feedback y adopción",
                        "chain": [
                            "Usuarios clave",
                            "Fricciones de adopción",
                            "Cambios de criterio",
                            "Aceptación gradual",
                        ],
                        "extra": ["Dudas recurrentes", "Soporte cercano"],
                    },
                ],
            },
            {
                "title": "Equipo y clima",
                "category": "Equipo",
                "branches": [
                    {
                        "title": "Carga y motivación",
                        "chain": [
                            "Sobrecarga percibida",
                            "Desgaste emocional",
                            "Reconducción del ánimo",
                            "Recuperación de confianza",
                        ],
                        "extra": ["Ayuda entre compañeros", "Reconocimiento"],
                    },
                    {
                        "title": "Conflicto y aprendizaje",
                        "chain": [
                            "Roce entre áreas",
                            "Escalada puntual",
                            "Mediación interna",
                            "Aprendizaje conjunto",
                        ],
                        "extra": ["Olvidos puntuales", "Mejora de comunicación"],
                    },
                ],
            },
        ],
    },
]

STAGES = [
    {
        "name": "Inicio",
        "progress": 12,
        "window_days": 65,
        "session_profile": {1: 2, 2: 2, 3: 2, 4: 1, 5: 0, 6: 0},
        "status_weights": {
            "positive": [("pendiente", 0.55), ("en_progreso", 0.35), ("en_pausa", 0.10)],
            "negative": [("pendiente", 0.60), ("en_progreso", 0.25), ("en_pausa", 0.15)],
            "mixed": [("pendiente", 0.55), ("en_progreso", 0.30), ("en_pausa", 0.15)],
            "human": [("pendiente", 0.50), ("en_progreso", 0.30), ("en_pausa", 0.20)],
        },
    },
    {
        "name": "Desarrollo",
        "progress": 58,
        "window_days": 210,
        "session_profile": {1: 6, 2: 7, 3: 8, 4: 8, 5: 6, 6: 5},
        "status_weights": {
            "positive": [("finalizada", 0.25), ("en_progreso", 0.55), ("en_pausa", 0.15), ("pendiente", 0.05)],
            "negative": [("finalizada", 0.12), ("en_progreso", 0.45), ("en_pausa", 0.28), ("pendiente", 0.15)],
            "mixed": [("finalizada", 0.18), ("en_progreso", 0.50), ("en_pausa", 0.20), ("pendiente", 0.12)],
            "human": [("finalizada", 0.20), ("en_progreso", 0.45), ("en_pausa", 0.22), ("pendiente", 0.13)],
        },
    },
    {
        "name": "Final",
        "progress": 100,
        "window_days": 330,
        "session_profile": {1: 12, 2: 14, 3: 16, 4: 16, 5: 14, 6: 12},
        "status_weights": {
            "positive": [("finalizada", 1.0)],
            "negative": [("finalizada", 1.0)],
            "mixed": [("finalizada", 1.0)],
            "human": [("finalizada", 1.0)],
        },
    },
]

LEGACY_PROJECT_NAMES = {
    "Programa Atlas - Transformación Operativa",
    "Proyecto Boreal - Recuperación de Servicio",
}


TARGET_PROGRESS_BY_SCENARIO = {
    ("atlas", "Inicio"): 0.12,
    ("atlas", "Desarrollo"): 0.58,
    ("atlas", "Final"): 1.00,
    ("boreal", "Inicio"): 0.08,
    ("boreal", "Desarrollo"): 0.42,
    ("boreal", "Final"): 0.97,
    ("cobalto", "Inicio"): 0.10,
    ("cobalto", "Desarrollo"): 0.51,
    ("cobalto", "Final"): 1.00,
    ("nexo", "Inicio"): 0.14,
    ("nexo", "Desarrollo"): 0.63,
    ("nexo", "Final"): 1.00,
}


def make_notes(objectives: str, notes: str) -> str:
    return json.dumps({"objectives": objectives, "notes": notes}, ensure_ascii=False)


def dt_from_day(base_day: date, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(base_day, time(hour, minute))


def rand_color(idx: int) -> str:
    return TASK_COLORS[idx % len(TASK_COLORS)]


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
        t.id for t in Task.query.filter_by(project_id=project.id, user_id=project.user_id).all()
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


def scenario_project_names() -> set[str]:
    names = set(LEGACY_PROJECT_NAMES)
    for archetype in ARCHETYPES:
        for stage in STAGES:
            names.add(f"{archetype['base_name']} - {stage['name']}")
    return names


def delete_previous_scenario_projects(user: User) -> None:
    for name in scenario_project_names():
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
    *, project: Project, titulo: str, descripcion: str, fecha_hito: date, tipo: str, color: str
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
    day: date,
    start_hour: int,
    minutos: int,
    tipo: str,
    objectives: str,
    notes: str,
    finalizada: bool = True,
) -> WorkSession:
    started_at = dt_from_day(day, start_hour, 0)
    ended_at = started_at + timedelta(minutes=minutos if finalizada else 0)
    session = WorkSession(
        tarea_id=task.id,
        fecha=day,
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


def weighted_choice(options: list[tuple[str, float]], rng: random.Random) -> str:
    roll = rng.random()
    acc = 0.0
    for value, weight in options:
        acc += weight
        if roll <= acc:
            return value
    return options[-1][0]


def build_objective(task_title: str, factor: str, member: str, client_name: str) -> str:
    return (
        f"Objetivo de la sesión: avanzar en {task_title.lower()}, "
        f"coordinar a {member} y aclarar dependencias con {client_name}. "
        f"Punto sensible del día: {factor}."
    )


def build_note(
    tone: str,
    stage_name: str,
    task_title: str,
    factor: str,
    member: str,
    client_name: str,
    rng: random.Random,
) -> str:
    good = rng.choice(POSITIVE_FACTORS)
    bad = rng.choice(NEGATIVE_FACTORS)

    if tone == "positive":
        if stage_name == "Inicio":
            return (
                f"El proyecto acaba de arrancar y todavía se está asentando la forma de trabajo en {task_title.lower()}. "
                f"Apareció {factor}, pero {member} ayudó a ordenar prioridades y hubo {good}. "
                f"El contacto con {client_name} fue correcto y dejó margen para seguir avanzando."
            )
        if stage_name == "Desarrollo":
            return (
                f"En esta fase intermedia se notó {factor}, aunque el equipo ya tiene más oficio para absorberlo. "
                f"Pesó {good} y la coordinación mejoró respecto a semanas anteriores. "
                f"La relación con {client_name} fue bastante más estable de lo que era al inicio."
            )
        return (
            f"La tarea quedó cerrada dentro de un contexto mucho más sano. "
            f"Ahora pesa más {good} que cualquier fricción puntual y el trabajo en {task_title.lower()} quedó bien rematado. "
            f"{client_name.capitalize()} percibió una mejora clara del proyecto y el ambiente del equipo terminó siendo bueno."
        )

    if tone == "negative":
        if stage_name == "Inicio":
            return (
                f"El arranque estuvo muy marcado por {factor} y además apareció {bad}. "
                f"{member} acabó bastante cargado y {client_name} no respondió con claridad. "
                f"El tono general fue tenso y se perdió tiempo intentando coordinar lo urgente."
            )
        if stage_name == "Desarrollo":
            return (
                f"El proyecto sigue en una fase dura y {factor} continúa frenando el avance. "
                f"Se sumó {bad}, hubo desgaste entre compañeros y sensación de cansancio acumulado. "
                f"{client_name.capitalize()} pidió cambios sin cerrar prioridades y eso empeoró el clima."
            )
        return (
            f"El cierre llega después de mucha fricción. "
            f"Aunque quedaron secuelas de {factor} y de {bad}, el equipo consiguió ordenar el trabajo y documentar mejor lo ocurrido. "
            f"La relación con {client_name} no terminó brillante, pero sí mucho más controlada que en mitad del proyecto."
        )

    if tone == "mixed":
        if stage_name == "Inicio":
            return (
                f"El arranque técnico de {task_title.lower()} combinó interés por avanzar con un primer golpe de realidad por {factor}. "
                f"Hubo {good}, pero también bastante dependencia de terceros. "
                f"{client_name.capitalize()} mantuvo el foco, aunque dejó varias decisiones abiertas."
            )
        if stage_name == "Desarrollo":
            return (
                f"En plena ejecución aparecieron tanto señales buenas como malas. "
                f"Por un lado se vio {good}; por otro, {factor} siguió rompiendo el ritmo y obligó a rehacer parte del trabajo. "
                f"{member} sostuvo bien la parte técnica, aunque el equipo notó fatiga."
            )
        return (
            f"El proyecto acabó con un cierre razonablemente sólido. "
            f"Persistió algún rastro de {factor}, pero el equipo logró consolidar {good} y cerrar mejor la parte técnica. "
            f"La percepción final de {client_name} fue positiva, aunque con aprendizaje claro sobre lo que costó más."
        )

    if stage_name == "Inicio":
        return (
            f"La sesión estuvo muy condicionada por relaciones humanas y coordinación. "
            f"Apareció {factor}, pero también {good}, y eso dejó una sensación ambigua. "
            f"{member} tuvo que mediar bastante con {client_name} para que la tarea no se desviara desde tan pronto."
        )
    if stage_name == "Desarrollo":
        return (
            f"La mitad del proyecto está siendo especialmente sensible a la coordinación. "
            f"Se notó {factor}, hubo cierta tensión entre áreas y costó mantener el foco. "
            f"Aun así, {good} ayudó a que la sesión no terminara peor."
        )
    return (
        f"En el tramo final ya se ve una lectura más madura de lo que pasó. "
        f"Persistieron recuerdos de {factor}, pero también una mejora real en comunicación, confianza y reparto de carga. "
        f"{client_name.capitalize()} terminó percibiendo más estabilidad de la que había al principio."
    )


def pick_status(stage: dict, tone: str, rng: random.Random) -> str:
    return weighted_choice(stage["status_weights"][tone], rng)


def build_milestones(project: Project, stage_name: str, color: str) -> list[tuple[str, str, date, str, str]]:
    base = project.fecha_inicio
    if stage_name == "Inicio":
        return [
            ("Kickoff", "Inicio formal y primer encaje de alcance.", base + timedelta(days=7), "reunión", color),
            ("Primer plan operativo", "Se fija una primera hoja de ruta.", base + timedelta(days=25), "hito", "#0ea5e9"),
        ]
    if stage_name == "Desarrollo":
        return [
            ("Kickoff", "Inicio formal y primeros acuerdos.", base + timedelta(days=7), "reunión", color),
            ("Primer hito relevante", "Se cierra una primera tanda de trabajo material.", base + timedelta(days=65), "hito", "#10b981"),
            ("Pico de complejidad", "Fase de máxima presión, cambios o bloqueos.", base + timedelta(days=130), "hito", "#f59e0b"),
            ("Recuperación parcial", "El proyecto empieza a estabilizarse.", base + timedelta(days=180), "hito", "#8b5cf6"),
        ]
    return [
        ("Kickoff", "Inicio formal del proyecto.", base + timedelta(days=7), "reunión", color),
        ("Hito intermedio", "Se consolida el grueso del trabajo.", base + timedelta(days=90), "hito", "#10b981"),
        ("Validación principal", "Cliente y equipo revisan el resultado acumulado.", base + timedelta(days=180), "hito", "#0ea5e9"),
        ("Aceptación final", "Se valida la entrega final.", base + timedelta(days=260), "entrega", "#8b5cf6"),
        ("Cierre y transferencia", "Se documenta el cierre y el aprendizaje.", base + timedelta(days=320), "entrega", "#22c55e"),
    ]


def project_timeframe(archetype: dict, stage: dict) -> tuple[date, date]:
    start = archetype["start_date"]
    end = start + timedelta(days=stage["window_days"])
    return start, end


def build_scenario_project(archetype: dict, stage: dict, user: User) -> Project:
    fecha_inicio, fecha_fin_prevista = project_timeframe(archetype, stage)

    stage_hint = {
        "Inicio": "Escenario de arranque, con estructura creada y primeras evidencias reales de trabajo.",
        "Desarrollo": "Escenario de ejecución media, con volumen relevante, hitos intermedios y tensión operativa realista.",
        "Final": "Escenario de cierre, con mucho trabajo acumulado, árbol rico y base suficiente para validar el resultado final.",
    }[stage["name"]]

    return create_project(
        user=user,
        name=f"{archetype['base_name']} - {stage['name']}",
        description=(
            f"{archetype['description']} {stage_hint}"
        ),
        priority="alta",
        category=archetype["category"],
        color=archetype["color"],
        fecha_inicio=fecha_inicio,
        fecha_fin_prevista=fecha_fin_prevista,
        minutos_estimados=72900,
        progress=stage["progress"],
    )


def target_progress_ratio(archetype_key: str, stage_name: str) -> float:
    return TARGET_PROGRESS_BY_SCENARIO[(archetype_key, stage_name)]


def rebalance_task_estimates(
    *,
    project: Project,
    created: list[tuple[Task, int]],
    target_ratio: float,
) -> None:
    tasks = [task for task, _ in created]
    actual_pairs: list[tuple[Task, int]] = []
    actual_total = 0

    for task in tasks:
        actual = sum(ws.minutos for ws in (task.work_sessions or []) if ws.finalizada)
        if actual <= 0:
            actual = 30 if target_ratio >= 0.99 else 60
        actual_pairs.append((task, actual))
        actual_total += actual

    if actual_total <= 0:
        for task in tasks:
            task.minutos_estimados = 60
        project.minutos_estimados = sum(task.minutos_estimados or 0 for task in tasks)
        return

    if target_ratio >= 0.999:
        estimated_values = [actual for _, actual in actual_pairs]
    else:
        target_est_total = max(int(round(actual_total / target_ratio)), actual_total + 60)
        weights = [actual for _, actual in actual_pairs]
        weight_total = sum(weights)
        estimated_values = [
            max(60, int(round(target_est_total * weight / weight_total)))
            for weight in weights
        ]
        diff = target_est_total - sum(estimated_values)
        if estimated_values:
            estimated_values[-1] += diff
            if estimated_values[-1] < 60:
                estimated_values[-1] = 60

    for (task, _actual), estimated in zip(actual_pairs, estimated_values):
        task.minutos_estimados = max(estimated, 30)

    project.minutos_estimados = sum(task.minutos_estimados or 0 for task in tasks)


def branch_schedule(
    project: Project,
    epic_idx: int,
    branch_idx: int,
    total_epics: int,
    total_branches: int,
) -> tuple[date, date]:
    total_days = max(60, (project.fecha_fin_prevista - project.fecha_inicio).days)
    epic_span = max(28, total_days // max(1, total_epics))
    branch_span = max(18, epic_span - 8)
    start = project.fecha_inicio + timedelta(days=epic_idx * epic_span + branch_idx * 8)
    end = min(project.fecha_fin_prevista, start + timedelta(days=branch_span))
    return start, end


def task_minutes_for_depth(depth: int) -> int:
    if depth == 1:
        return 5400
    if depth == 2:
        return 2400
    if depth == 3:
        return 900
    if depth == 4:
        return 600
    if depth == 5:
        return 360
    return 180


def populate_scenario_project(
    project: Project,
    archetype: dict,
    stage: dict,
    user: User,
    rng: random.Random,
) -> tuple[int, int]:
    created: list[tuple[Task, int]] = []

    for epic_idx, epic_spec in enumerate(archetype["epics"]):
        epic_start, epic_end = branch_schedule(
            project, epic_idx, 0, len(archetype["epics"]), 1
        )
        epic_task = create_task(
            user=user,
            project=project,
            titulo=epic_spec["title"],
            descripcion=f"Épica principal de {epic_spec['category'].lower()} en {project.name}.",
            categoria=epic_spec["category"],
            estado=pick_status(stage, archetype["tone"], rng),
            color=rand_color(epic_idx),
            fecha_inicio=epic_start,
            fecha_fin=epic_end,
            minutos_estimados=task_minutes_for_depth(1),
        )
        created.append((epic_task, 1))

        for branch_idx, branch in enumerate(epic_spec["branches"]):
            branch_start, branch_end = branch_schedule(
                project, epic_idx, branch_idx, len(archetype["epics"]), len(epic_spec["branches"])
            )
            branch_task = create_task(
                user=user,
                project=project,
                titulo=branch["title"],
                descripcion=f"Rama de trabajo de {branch['title'].lower()} dentro de {epic_spec['title'].lower()}.",
                categoria=epic_spec["category"],
                estado=pick_status(stage, archetype["tone"], rng),
                color=rand_color(epic_idx * 3 + branch_idx + 1),
                fecha_inicio=branch_start,
                fecha_fin=branch_end,
                minutos_estimados=task_minutes_for_depth(2),
                parent_task=epic_task,
            )
            created.append((branch_task, 2))

            current_parent = branch_task
            chain_start = branch_start + timedelta(days=3)
            chain_span = max(10, (branch_end - branch_start).days)
            for chain_idx, chain_title in enumerate(branch["chain"]):
                node_start = chain_start + timedelta(days=chain_idx * max(4, chain_span // 8))
                node_end = min(project.fecha_fin_prevista, node_start + timedelta(days=max(8, chain_span // 3)))
                node_task = create_task(
                    user=user,
                    project=project,
                    titulo=chain_title,
                    descripcion=f"Cadena profunda de {chain_title.lower()} dentro de {branch['title'].lower()}.",
                    categoria=epic_spec["category"],
                    estado=pick_status(stage, archetype["tone"], rng),
                    color=rand_color(epic_idx * 10 + branch_idx * 4 + chain_idx + 2),
                    fecha_inicio=node_start,
                    fecha_fin=node_end,
                    minutos_estimados=task_minutes_for_depth(chain_idx + 3),
                    parent_task=current_parent,
                )
                created.append((node_task, chain_idx + 3))
                current_parent = node_task

            for extra_idx, extra_title in enumerate(branch["extra"]):
                extra_start = branch_start + timedelta(days=5 + extra_idx * 7)
                extra_end = min(project.fecha_fin_prevista, extra_start + timedelta(days=20))
                extra_task = create_task(
                    user=user,
                    project=project,
                    titulo=extra_title,
                    descripcion=f"Tarea lateral de {extra_title.lower()} asociada a {branch['title'].lower()}.",
                    categoria=epic_spec["category"],
                    estado=pick_status(stage, archetype["tone"], rng),
                    color=rand_color(epic_idx * 20 + branch_idx * 5 + extra_idx + 7),
                    fecha_inicio=extra_start,
                    fecha_fin=extra_end,
                    minutos_estimados=task_minutes_for_depth(3),
                    parent_task=branch_task,
                )
                created.append((extra_task, 3))

    sessions_created = 0
    for idx, (task, depth) in enumerate(created):
        count = stage["session_profile"].get(depth, 1)
        if count <= 0:
            continue
        span = max(6, (task.fecha_plan_fin - task.fecha_plan_inicio).days)
        for session_idx in range(count):
            offset = (session_idx + 1) / (count + 1)
            day = task.fecha_plan_inicio + timedelta(days=min(span, int(span * offset)))
            member = rng.choice(TEAM_MEMBERS)
            client_name = rng.choice(CLIENT_NAMES)
            factor_pool = NEGATIVE_FACTORS + POSITIVE_FACTORS
            if archetype["tone"] == "positive" and stage["name"] != "Inicio":
                factor_pool = POSITIVE_FACTORS + NEGATIVE_FACTORS
            elif archetype["tone"] == "negative" and stage["name"] != "Final":
                factor_pool = NEGATIVE_FACTORS + NEGATIVE_FACTORS + POSITIVE_FACTORS
            factor = rng.choice(factor_pool)
            objectives = build_objective(task.titulo, factor, member, client_name)
            notes = build_note(
                archetype["tone"], stage["name"], task.titulo, factor, member, client_name, rng
            )
            minutes = rng.choice([45, 60, 75, 90, 105, 120]) if depth >= 3 else rng.choice(
                [60, 90, 120, 150]
            )
            finalizada = stage["name"] == "Final" or session_idx < count - 1 or depth <= 3
            create_session(
                task=task,
                day=day,
                start_hour=9 + ((idx + session_idx) % 7),
                minutos=minutes,
                tipo=rng.choice(SESSION_TYPES),
                objectives=objectives,
                notes=notes,
                finalizada=finalizada,
            )
            sessions_created += 1

    for titulo, descripcion, fecha_hito, tipo, color in build_milestones(
        project, stage["name"], archetype["color"]
    ):
        create_milestone(
            project=project,
            titulo=titulo,
            descripcion=descripcion,
            fecha_hito=fecha_hito,
            tipo=tipo,
            color=color,
        )

    rebalance_task_estimates(
        project=project,
        created=created,
        target_ratio=target_progress_ratio(archetype["key"], stage["name"]),
    )

    return len(created), sessions_created


def main() -> None:
    rng = random.Random(RANDOM_SEED)
    app = create_app()

    with app.app_context():
        user = ensure_demo_user()
        delete_previous_scenario_projects(user)

        total_projects = 0
        total_tasks = 0
        total_sessions = 0

        for archetype in ARCHETYPES:
            for stage in STAGES:
                project = build_scenario_project(archetype, stage, user)
                task_count, session_count = populate_scenario_project(
                    project, archetype, stage, user, rng
                )
                total_projects += 1
                total_tasks += task_count
                total_sessions += session_count

        db.session.commit()

        print("[OK] Seed portable de escenarios generado correctamente")
        print(f"[OK] Usuario demo: {DEMO_USERNAME}")
        print(f"[OK] Proyectos creados: {total_projects}")
        print(f"[OK] Tareas creadas: {total_tasks}")
        print(f"[OK] Sesiones creadas: {total_sessions}")
        print(f"[OK] Password demo: {DEMO_PASSWORD}")
        print(f"[OK] Password del proyecto: {PROJECT_PASSWORD}")


if __name__ == "__main__":
    main()
