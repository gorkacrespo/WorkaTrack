#!/usr/bin/env python3
"""
Borra tareas concretas por ID exacto, junto con sus sesiones si las tuvieran.
No toca ninguna otra tarea del proyecto.

Uso (dentro del contenedor web):
    python3 /app/borrar_tareas_por_id.py
"""
from app import create_app
from app.models import db, Task, WorkSession

TASK_IDS_TO_DELETE = [3655, 3656, 3657]  # prueba1, prueba2, prueba3


def main() -> None:
    app = create_app()
    with app.app_context():
        tasks = Task.query.filter(Task.id.in_(TASK_IDS_TO_DELETE)).all()
        found_ids = {t.id for t in tasks}
        missing = set(TASK_IDS_TO_DELETE) - found_ids

        if missing:
            print(f"[AVISO] No se han encontrado estos IDs (se ignoran): {sorted(missing)}")

        if not tasks:
            print("[AVISO] Ninguna de las tareas indicadas existe. No se borra nada.")
            return

        print(f"[INFO] Tareas a borrar ({len(tasks)}):")
        for t in tasks:
            print(f"  - id={t.id} | {t.titulo!r} | parent_task_id={t.parent_task_id}")

        WorkSession.query.filter(WorkSession.tarea_id.in_(found_ids)).delete(synchronize_session=False)
        Task.query.filter(Task.id.in_(found_ids)).delete(synchronize_session=False)
        db.session.commit()

        print(f"[OK] Borradas {len(tasks)} tareas y sus sesiones asociadas.")


if __name__ == "__main__":
    main()
