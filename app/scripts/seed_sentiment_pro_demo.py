import os
import random
from datetime import date, timedelta

from app import create_app
from app.models import db, User, Project, Task, WorkSession


PROJECT_NAME = "PruebaAnalisisPro"
USERNAME = "gcrespo"

# Semilla fija para que el dataset sea reproducible
RANDOM_SEED = 42

# Fechas del dataset (puedes ajustar)
START_DATE = date(2025, 12, 20)
END_DATE = date(2026, 2, 5)

# Estados que usamos
ESTADOS = ["pendiente", "en_progreso", "en_pausa", "finalizada"]

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def _rand_date(rng: random.Random, d0: date, d1: date) -> date:
    days = (d1 - d0).days
    if days <= 0:
        return d0
    return d0 + timedelta(days=rng.randint(0, days))


def _safe_set(obj, field: str, value):
    if hasattr(obj, field):
        setattr(obj, field, value)


def _task_label(task: Task) -> str:
    return f"Task(id={task.id}, titulo={task.titulo!r})"


def _project_label(p: Project) -> str:
    return f"Project(id={p.id}, name={getattr(p, 'name', None)!r})"


def _ensure_user() -> User:
    u = User.query.filter_by(username=USERNAME).first()
    if not u:
        raise RuntimeError(f"No encuentro el usuario '{USERNAME}'.")
    return u


def _ensure_project(user: User) -> Project:
    p = Project.query.filter_by(user_id=user.id, name=PROJECT_NAME).first()
    if not p:
        raise RuntimeError(f"No encuentro el proyecto '{PROJECT_NAME}' para el usuario {user.username}.")
    return p


def _delete_project_data(project_id: int, user_id: int):
    # Borramos sesiones y tareas del proyecto (solo de ese usuario/proyecto)
    tasks = Task.query.filter_by(project_id=project_id, user_id=user_id).all()
    task_ids = [t.id for t in tasks]
    if task_ids:
        WorkSession.query.filter(WorkSession.tarea_id.in_(task_ids)).delete(synchronize_session=False)
        Task.query.filter(Task.id.in_(task_ids)).delete(synchronize_session=False)
    db.session.commit()


def _create_task(
    user_id: int,
    project_id: int,
    titulo: str,
    parent_task_id=None,
    minutos_estimados: int | None = None,
    estado: str = "pendiente",
    categoria: str | None = None,
    color: str | None = None,
    fecha_plan_inicio: date | None = None,
    fecha_plan_fin: date | None = None,
    descripcion: str | None = None,
) -> Task:
    t = Task(
        user_id=user_id,
        project_id=project_id,
        parent_task_id=parent_task_id,
        titulo=titulo,
        descripcion=descripcion,
        categoria=categoria,
        estado=estado,
        color=color,
        fecha_plan_inicio=fecha_plan_inicio,
        fecha_plan_fin=fecha_plan_fin,
        minutos_estimados=minutos_estimados,
    )
    db.session.add(t)
    db.session.flush()  # para tener ID
    return t


def _create_session(
    tarea_id: int,
    fecha: date,
    minutos: int,
    tipo: str,
    text: str,
):
    # Guardamos todo en "notas" (string), que es lo que tu servicio ya analiza
    ws = WorkSession(
        tarea_id=tarea_id,
        fecha=fecha,
        minutos=minutos,
        tipo=tipo,
        notas=text,
    )

    # Si el modelo tiene "finalizada", la marcamos para que cuente como real
    if hasattr(ws, "finalizada"):
        ws.finalizada = True

    db.session.add(ws)
    return ws


# ------------------------------------------------------------
# Contenido semántico (pre/post) + casos
# ------------------------------------------------------------

def _build_pre_post(rng: random.Random, factor: str, polarity: str) -> str:
    """
    Devuelve un texto con estructura útil para mode=pre_post:
    - Primera frase/segmento = PRE (intención/objetivo)
    - Segunda/tercera frase = POST (resultado/sentimiento)
    """
    # PRE (objetivo)
    pre_map = {
        "cliente": [
            "Objetivo: preparar reunión con el cliente y alinear expectativas.",
            "Hoy quiero responder al cliente y dejar clara la propuesta. Espero que la relación sea fluida.",
            "Objetivo: cerrar puntos pendientes con el cliente sin generar tensión.",
        ],
        "sobrecarga": [
            "Objetivo: sacar mucho trabajo hoy, tengo bastante carga y necesito organizarme.",
            "Tengo muchas tareas acumuladas, intentaré priorizar para no agobiarme.",
            "Quiero avanzar pero estoy con demasiadas cosas a la vez, me preocupa el estrés.",
        ],
        "bloqueo": [
            "Objetivo: desbloquear el problema técnico y dejar el entorno estable.",
            "Hoy quiero arreglar el bug que bloquea el avance y dejarlo listo.",
            "Objetivo: hacer que CI/CD deje de fallar y que el despliegue sea estable.",
        ],
        "planificacion": [
            "Objetivo: estimación realista y buen control del tiempo.",
            "Quiero ajustar el alcance para que el plan sea realista.",
            "Objetivo: revisar prioridades para evitar retrasos por scope creep.",
        ],
        "comunicacion": [
            "Objetivo: comunicar bien el estado y evitar malentendidos.",
            "Hoy quiero dejar un update claro al equipo y coordinar próximos pasos.",
            "Objetivo: alinear dependencias con otros para no bloquear la rama.",
        ],
    }

    # POST (resultado)
    post_pos = {
        "cliente": [
            "La reunión con el cliente fue bien, quedó satisfecho y la comunicación fue muy fluida.",
            "Se resolvieron dudas del cliente sin fricción. Muy positivo.",
            "El cliente entendió los cambios y estuvo contento, hemos avanzado con buen tono.",
        ],
        "sobrecarga": [
            "Al final he gestionado bien la carga, me siento cómodo y satisfecho con el avance.",
            "He recuperado el control del plan y ahora voy tranquilo. Buen progreso.",
            "Se notó el esfuerzo, pero acabé contento porque salió mejor de lo esperado.",
        ],
        "bloqueo": [
            "Encontré la causa y quedó resuelto. Me deja muy buena sensación.",
            "Se estabilizó el despliegue y todo vuelve a estar bajo control. Muy positivo.",
            "El bug quedó cerrado y ya no bloquea la rama. Buen cierre.",
        ],
        "planificacion": [
            "Ajusté el alcance y ahora el plan es realista. Me siento cómodo.",
            "Las estimaciones quedaron coherentes y el proyecto respira mejor.",
            "Definí prioridades y el avance es claro. Positivo.",
        ],
        "comunicacion": [
            "La comunicación fue clara y se evitó fricción. Buen ambiente.",
            "Se alineó todo y la rama avanzó sin problemas. Muy bien.",
            "Quedaron acuerdos claros y eso reduce estrés. Positivo.",
        ],
    }

    post_neg = {
        "cliente": [
            "El cliente se mostró molesto, la reunión fue tensa y hay descontento.",
            "Hubo quejas del cliente y la comunicación fue difícil, me dejó frustrado.",
            "El cliente no aceptó la propuesta, ha sido negativo y estresante.",
        ],
        "sobrecarga": [
            "Demasiada carga de trabajo, terminé cansado y agobiado. Sensación negativa.",
            "No he llegado a todo, me he frustrado y el estrés fue alto.",
            "Me estoy quemando un poco, hoy ha sido pesado y con mal cuerpo.",
        ],
        "bloqueo": [
            "No conseguí desbloquearlo, perdí mucho tiempo y acabé bastante frustrado.",
            "Sigue fallando el despliegue y me está quemando. Muy mal día.",
            "El bug persiste y bloquea todo. Negativo y estresante.",
        ],
        "planificacion": [
            "Las estimaciones eran irreales y se fue el tiempo. Me estresé y terminé cansado.",
            "Scope creep y cambios constantes: se siente caótico y frustrante.",
            "Mala planificación hoy: retraso y sensación de descontrol.",
        ],
        "comunicacion": [
            "Hubo malentendidos y eso generó tensión. Día negativo.",
            "La comunicación fue confusa y acabé frustrado por el caos.",
            "No hubo alineación y la rama quedó bloqueada. Negativo.",
        ],
    }

    post_neu = {
        "cliente": [
            "Se avanzó un poco y quedó pendiente lo importante. Neutro.",
            "Hubo avance pero sin cierre claro. Neutral por ahora.",
            "",
        ],
        "sobrecarga": [
            "Avancé algo pero sin sensación clara. Neutral.",
            "Se hizo lo básico, no destaca. Neutro.",
            "",
        ],
        "bloqueo": [
            "Se investigó pero sin resolución completa. Neutral por ahora.",
            "Dejé logs y pruebas preparadas. Queda para mañana. Neutro.",
            "",
        ],
        "planificacion": [
            "Revisé estimaciones y dejé notas. Neutral.",
            "Definí un plan base, falta validarlo. Neutro.",
            "",
        ],
        "comunicacion": [
            "Dejé un update y sigo. Neutral.",
            "Se informó sin novedades relevantes. Neutro.",
            "",
        ],
    }

    pre = rng.choice(pre_map.get(factor, ["Objetivo: avanzar."]))
    if polarity == "positive":
        post = rng.choice(post_pos.get(factor, ["Muy bien."]))
    elif polarity == "negative":
        post = rng.choice(post_neg.get(factor, ["Mal día."]))
    else:
        post = rng.choice(post_neu.get(factor, [""]))

    # Pre + Post (2-3 frases). Esto encaja con tu split actual.
    if post:
        return f"{pre} {post}"
    return pre


# ------------------------------------------------------------
# Generación de árbol + tiempos
# ------------------------------------------------------------

def main():
    rng = random.Random(RANDOM_SEED)

    force = os.getenv("FORCE", "").strip() in {"1", "true", "TRUE", "yes", "YES"}

    app = create_app()
    with app.app_context():
        user = _ensure_user()
        project = _ensure_project(user)

        # Si ya hay tareas, no regeneramos salvo FORCE=1
        existing = Task.query.filter_by(project_id=project.id, user_id=user.id).count()
        if existing > 0 and not force:
            print(f"[SKIP] El proyecto ya tiene {existing} tareas. Si quieres regenerar, ejecuta con FORCE=1.")
            return

        if force and existing > 0:
            print(f"[FORCE] Borrando datos del proyecto {project.id} ({PROJECT_NAME})...")
            _delete_project_data(project.id, user.id)

        # Meta del proyecto (si existen campos)
        _safe_set(project, "fecha_inicio", START_DATE)
        _safe_set(project, "fecha_fin_prevista", END_DATE)
        _safe_set(project, "minutos_estimados", 0)  # lo recalculamos abajo si existe
        db.session.commit()

        print(f"[OK] Usuario: id={user.id} username={user.username} email={user.email}")
        print(f"[OK] Proyecto: {_project_label(project)}")

        # ----------------------------
        # Definimos una estructura "pro"
        # ----------------------------
        # Cada épica tendrá subtareas y algunas con sub-subtareas.
        # Además, metemos “contagio” de sentimiento por ramas:
        # - Rama A: empieza neutral -> se vuelve positiva (recuperación)
        # - Rama B: padre negativo arrastra hijos, pero un nieto revierte
        # - Rama C: padre positivo pero una hoja sale negativa (bloqueo aislado)
        # - Rama D: planificación neutra (on-track)

        tree = [
            {
                "epic": "Épica A — Planificación y alcance",
                "categoria": "planificacion",
                "tone": "neutral",
                "children": [
                    {
                        "title": "Definir alcance v1",
                        "tone": "neutral",
                        "leaf_scenarios": ["on_track", "under"],
                    },
                    {
                        "title": "Estimaciones iniciales",
                        "tone": "negative",  # al inicio mal estimado
                        "leaf_scenarios": ["over", "recovery"],  # recuperación
                    },
                    {
                        "title": "Riesgos y mitigación",
                        "tone": "positive",
                        "leaf_scenarios": ["under", "on_track"],
                    },
                ],
            },
            {
                "epic": "Épica B — Cliente y entregables",
                "categoria": "cliente",
                "tone": "negative",  # épica tensa
                "children": [
                    {
                        "title": "Preparar reunión con cliente",
                        "tone": "neutral",
                        "leaf_scenarios": ["on_track", "over"],
                    },
                    {
                        "title": "Cambios solicitados (scope creep)",
                        "tone": "negative",
                        "leaf_scenarios": ["over", "over"],
                        "sub": [
                            {
                                "title": "Revisar impacto en calendario",
                                "tone": "negative",
                                "leaf_scenarios": ["over"],
                            },
                            {
                                "title": "Proponer alternativa y negociar",
                                "tone": "positive",  # nieto salva
                                "leaf_scenarios": ["on_track", "under"],
                            },
                        ],
                    },
                    {
                        "title": "Entrega parcial y feedback",
                        "tone": "positive",
                        "leaf_scenarios": ["under", "on_track"],
                    },
                ],
            },
            {
                "epic": "Épica C — Bloqueos técnicos / CI-CD",
                "categoria": "bloqueo",
                "tone": "positive",
                "children": [
                    {
                        "title": "Estabilizar pipeline",
                        "tone": "positive",
                        "leaf_scenarios": ["on_track", "under"],
                    },
                    {
                        "title": "Bug crítico en producción",
                        "tone": "negative",  # hoja negativa aunque padre positivo
                        "leaf_scenarios": ["over", "over", "recovery"],
                        "sub": [
                            {
                                "title": "Reproducir bug y aislar causa",
                                "tone": "negative",
                                "leaf_scenarios": ["over"],
                            },
                            {
                                "title": "Hotfix y validación",
                                "tone": "positive",
                                "leaf_scenarios": ["under", "on_track"],
                            },
                        ],
                    },
                ],
            },
            {
                "epic": "Épica D — Comunicación y coordinación",
                "categoria": "comunicacion",
                "tone": "neutral",
                "children": [
                    {
                        "title": "Update semanal",
                        "tone": "neutral",
                        "leaf_scenarios": ["on_track", "neutral_only"],
                    },
                    {
                        "title": "Alinear dependencias externas",
                        "tone": "negative",
                        "leaf_scenarios": ["over", "on_track"],
                    },
                ],
            },
        ]

        # ----------------------------
        # Crear tareas y sesiones
        # ----------------------------
        created_tasks = 0
        created_sessions = 0
        total_project_est = 0

        def mk_color():
            # colores sencillos distintos por tarea, si no lo setea backend
            return rng.choice(["#60a5fa", "#34d399", "#fbbf24", "#f87171", "#a78bfa", "#fb7185", "#22c55e"])

        def scenario_minutes(est: int, scenario: str):
            """
            Devuelve minutos reales por sesión y número de sesiones, según escenario.
            - under: total ~ 60-85% del estimado
            - on_track: total ~ 90-110%
            - over: total ~ 130-190%
            - recovery: primeras sesiones over y últimas under para “recuperación”
            - neutral_only: poco tiempo, neutro
            """
            if est <= 0:
                est = 60

            if scenario == "under":
                total = int(est * rng.uniform(0.60, 0.85))
                n = rng.randint(2, 5)
                return total, n
            if scenario == "on_track":
                total = int(est * rng.uniform(0.90, 1.10))
                n = rng.randint(2, 6)
                return total, n
            if scenario == "over":
                total = int(est * rng.uniform(1.30, 1.90))
                n = rng.randint(3, 7)
                return total, n
            if scenario == "recovery":
                total = int(est * rng.uniform(1.05, 1.35))  # acaba algo por encima o cerca
                n = rng.randint(4, 8)
                return total, n
            if scenario == "neutral_only":
                total = int(est * rng.uniform(0.25, 0.45))
                n = rng.randint(1, 2)
                return total, n

            total = int(est * 1.0)
            n = 3
            return total, n

        def scenario_polarities(scenario: str):
            """
            Polaridades por sesión (para pre/post):
            - under / on_track: más positivo/neutral
            - over: más negativo
            - recovery: empieza negativo -> termina positivo
            - neutral_only: neutro
            """
            if scenario in ("under",):
                return ["neutral", "positive", "positive"]
            if scenario in ("on_track",):
                return ["neutral", "neutral", "positive"]
            if scenario in ("over",):
                return ["negative", "negative", "neutral"]
            if scenario in ("recovery",):
                return ["negative", "negative", "neutral", "positive", "positive"]
            if scenario in ("neutral_only",):
                return ["neutral", "neutral"]
            return ["neutral", "positive"]

        def pick_factor(epic_cat: str):
            # Factor principal de la épica pero metemos variaciones
            pool = [epic_cat, epic_cat, epic_cat, "sobrecarga", "planificacion", "comunicacion", "bloqueo", "cliente"]
            return rng.choice(pool)

        # Creamos el árbol
        for epic in tree:
            epic_cat = epic.get("categoria")
            epic_task = _create_task(
                user_id=user.id,
                project_id=project.id,
                titulo=epic["epic"],
                parent_task_id=None,
                minutos_estimados=None,
                estado="en_progreso",
                categoria=epic_cat,
                color=mk_color(),
                fecha_plan_inicio=START_DATE,
                fecha_plan_fin=END_DATE,
                descripcion="Tarea padre (épica) generada para dataset pro.",
            )
            created_tasks += 1

            for ch in epic["children"]:
                # Subtarea de epic
                est_child = rng.choice([180, 240, 300, 360, 420, 480])  # 3h-8h
                total_project_est += est_child

                child_task = _create_task(
                    user_id=user.id,
                    project_id=project.id,
                    titulo=ch["title"],
                    parent_task_id=epic_task.id,
                    minutos_estimados=est_child,
                    estado=rng.choice(["en_progreso", "en_pausa", "finalizada"]),
                    categoria=epic_cat,
                    color=mk_color(),
                    fecha_plan_inicio=_rand_date(rng, START_DATE, END_DATE - timedelta(days=10)),
                    fecha_plan_fin=_rand_date(rng, START_DATE + timedelta(days=5), END_DATE),
                    descripcion="Subtarea generada para simular trabajo real en proyecto.",
                )
                created_tasks += 1

                # Si tiene sub-subtareas: creamos esas y las sesiones van en las hojas (nietos)
                if "sub" in ch and ch["sub"]:
                    # Al padre le dejamos poco o nada de sesiones (para que el análisis vea hojas)
                    for sub in ch["sub"]:
                        est_leaf = rng.choice([90, 120, 150, 180, 210, 240])  # 1.5h-4h
                        total_project_est += est_leaf

                        leaf = _create_task(
                            user_id=user.id,
                            project_id=project.id,
                            titulo=sub["title"],
                            parent_task_id=child_task.id,
                            minutos_estimados=est_leaf,
                            estado=rng.choice(["en_progreso", "finalizada"]),
                            categoria=epic_cat,
                            color=mk_color(),
                            fecha_plan_inicio=_rand_date(rng, START_DATE, END_DATE - timedelta(days=5)),
                            fecha_plan_fin=_rand_date(rng, START_DATE + timedelta(days=3), END_DATE),
                            descripcion="Sub-subtarea (hoja) para análisis por ramas.",
                        )
                        created_tasks += 1

                        # Sesiones en hojas
                        for scen in sub.get("leaf_scenarios", ["on_track"]):
                            total_minutes, n_sessions = scenario_minutes(est_leaf, scen)
                            minutes_left = total_minutes
                            pols = scenario_polarities(scen)

                            for i in range(n_sessions):
                                # Reparto de minutos
                                if i == n_sessions - 1:
                                    m = max(10, minutes_left)
                                else:
                                    m = max(10, int(total_minutes / n_sessions * rng.uniform(0.7, 1.3)))
                                    m = min(m, minutes_left - 10) if minutes_left > 20 else m
                                minutes_left = max(0, minutes_left - m)

                                factor = pick_factor(epic_cat)
                                # Elegimos polaridad según el “patrón” del escenario
                                pol = pols[min(i, len(pols) - 1)]

                                text = _build_pre_post(rng, factor=factor, polarity=pol)
                                s_date = _rand_date(rng, START_DATE, END_DATE)
                                _create_session(
                                    tarea_id=leaf.id,
                                    fecha=s_date,
                                    minutos=m,
                                    tipo="work",
                                    text=text,
                                )
                                created_sessions += 1

                else:
                    # Si no hay sub-subtareas, esta child_task es una hoja (le ponemos sesiones)
                    leaf_scenarios = ch.get("leaf_scenarios", ["on_track"])
                    for scen in leaf_scenarios:
                        total_minutes, n_sessions = scenario_minutes(est_child, scen)
                        minutes_left = total_minutes
                        pols = scenario_polarities(scen)

                        for i in range(n_sessions):
                            if i == n_sessions - 1:
                                m = max(10, minutes_left)
                            else:
                                m = max(10, int(total_minutes / n_sessions * rng.uniform(0.7, 1.3)))
                                m = min(m, minutes_left - 10) if minutes_left > 20 else m
                            minutes_left = max(0, minutes_left - m)

                            factor = pick_factor(epic_cat)
                            pol = pols[min(i, len(pols) - 1)]
                            # “contagio” básico: si el padre es negativo, empujamos algo más a negativo
                            if epic.get("tone") == "negative" and pol == "neutral" and rng.random() < 0.35:
                                pol = "negative"

                            text = _build_pre_post(rng, factor=factor, polarity=pol)
                            s_date = _rand_date(rng, START_DATE, END_DATE)
                            _create_session(
                                tarea_id=child_task.id,
                                fecha=s_date,
                                minutos=m,
                                tipo="work",
                                text=text,
                            )
                            created_sessions += 1

        # Actualizamos estimado del proyecto si existe el campo
        _safe_set(project, "minutos_estimados", total_project_est)
        db.session.commit()

        print(f"[OK] Tareas creadas: {created_tasks}")
        print(f"[OK] Sesiones creadas: {created_sessions}")
        print(f"[OK] Minutos estimados del proyecto (sum tareas): {total_project_est}")
        print(f"[DONE] Dataset PRO listo en '{PROJECT_NAME}' (project_id={project.id}).")


if __name__ == "__main__":
    main()
