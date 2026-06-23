#!/usr/bin/env python3
"""
Borra TODOS los proyectos de la base de datos excepto el del TFG
("WorkaTrack — TFG · Contenedores y Orquestadores"), dejando ese intacto
con sus tareas, sesiones, hitos y caché de Q&A.

Uso (dentro del contenedor web):
    python3 /app/limpiar_proyectos_excepto_tfg.py
"""
from app import create_app
from app.models import db, Project, Task, WorkSession, Milestone, QaChunkSummary

KEEP_NAME = "WorkaTrack — TFG · Contenedores y Orquestadores"


def wipe_project(project: Project) -> None:
    task_ids = [t.id for t in Task.query.filter_by(project_id=project.id).all()]
    if task_ids:
        WorkSession.query.filter(WorkSession.tarea_id.in_(task_ids)).delete(synchronize_session=False)
        Task.query.filter(Task.id.in_(task_ids)).delete(synchronize_session=False)
    Milestone.query.filter_by(project_id=project.id).delete(synchronize_session=False)
    QaChunkSummary.query.filter_by(project_id=project.id).delete(synchronize_session=False)
    db.session.delete(project)


def main() -> None:
    app = create_app()
    with app.app_context():
        all_projects = Project.query.all()
        to_keep = [p for p in all_projects if p.name == KEEP_NAME]
        to_delete = [p for p in all_projects if p.name != KEEP_NAME]

        if not to_keep:
            print(f"[AVISO] No se ha encontrado ningún proyecto llamado exactamente: {KEEP_NAME}")
            print("No se borra nada por seguridad. Revisa el nombre antes de reintentar.")
            return

        print(f"[OK] Proyecto a conservar encontrado: '{to_keep[0].name}' (id={to_keep[0].id})")
        print(f"[INFO] Proyectos a borrar: {len(to_delete)}")
        for p in to_delete:
            print(f"  - id={p.id} | {p.name}")

        for p in to_delete:
            wipe_project(p)

        db.session.commit()
        print(f"[OK] Borrados {len(to_delete)} proyectos. Conservado: {to_keep[0].name}")


if __name__ == "__main__":
    main()
