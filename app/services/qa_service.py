# app/services/qa_service.py

from __future__ import annotations

import os
import json
import re
from datetime import date, timedelta

from app.models import db, QaChunkSummary, Task, Project, WorkSession, Milestone
from app.services.project_stats_service import get_project_time_stats

from typing import Any, Dict, List, Optional, Tuple, Callable
from sqlalchemy.exc import IntegrityError

import requests

from app.services.sentiment_service import (
    CommentItem,
    collect_project_comments,
    filter_relevant_comments,
)


def _as_int(v: Any, default: int) -> int:
    try:
        return int(v)
    except Exception:
        return default


def _as_float(v: Any, default: float) -> float:
    try:
        return float(v)
    except Exception:
        return default


def _truncate(s: str, max_chars: int) -> str:
    s = (s or "").strip()
    if max_chars <= 0:
        return s
    if len(s) <= max_chars:
        return s
    return s[: max_chars - 1].rstrip() + "…"


def _ollama_chat(messages: List[Dict[str, str]], *, timeout_override_s: Optional[float] = None, num_predict_override: Optional[int] = None, retries: int = 3, ) -> Tuple[Optional[str], Dict[str, Any]]:
    """
    Llama a Ollama /api/chat y devuelve (answer, meta).
    Si falla, devuelve (None, meta con error).
    """
    base_url = (os.getenv("OLLAMA_BASE_URL") or "").strip()
    model = (os.getenv("OLLAMA_QA_MODEL") or "qwen2.5:3b").strip()
    timeout_s = _as_float(os.getenv("OLLAMA_QA_TIMEOUT_SECS") or "60", 60.0)

    temperature = _as_float(os.getenv("QA_TEMPERATURE") or "0.2", 0.2)

    if not base_url:
        return None, {"provider": "ollama", "mode": "disabled", "reason": "OLLAMA_BASE_URL no configurado"}

    url = base_url.rstrip("/") + "/api/chat"

    num_predict = _as_int(os.getenv("OLLAMA_QA_NUM_PREDICT") or "450", 450)
    hard_cap = _as_float(os.getenv("OLLAMA_QA_HARD_TIMEOUT_SECS") or "240", 240.0)
    if num_predict_override is not None:
        num_predict = int(num_predict_override)

    if timeout_override_s is not None:
        timeout_s = float(timeout_override_s)

    if hard_cap and hard_cap >0:
        timeout_s = min(timeout_s, hard_cap)

    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": num_predict,
        },
    }

    try:
        last_err = None
        for _try in range(max(1, int(retries))):
            try:
                r = requests.post(url, json=payload, timeout=(5, timeout_s))
                last_err = None
                break
            except Exception as e:
                last_err = e
        if last_err is not None:
            raise last_err
        if r.status_code != 200:
            return None, {
                "provider": "ollama",
                "mode": "error",
                "http_status": r.status_code,
                "body": (r.text[:500] if r.text else ""),
                "model": model,
            }
        data = r.json()
        msg = data.get("message") or {}
        content = (msg.get("content") or "").strip()
        if not content:
            return None, {"provider": "ollama", "mode": "error", "reason": "Respuesta vacía", "model": model}
        return content, {"provider": "ollama", "mode": "ok", "model": model}
    except Exception as e:
        return None, {"provider": "ollama", "mode": "error", "reason": str(e), "model": model}


def _item_to_evidence(it: CommentItem) -> Dict[str, Any]:
    return {
        "source": it.source,
        "source_id": it.source_id,
        "task_id": it.task_id,
        "date": it.created_date.isoformat() if it.created_date else None,
        "text": it.text,
        "pre_text": it.pre_text,
        "post_text": it.post_text,
    }


def _fast_v2_query_profile(question: str) -> Dict[str, Any]:
    ql = (question or "").strip().lower()
    return {
        "question": (question or "").strip(),
        "is_recent": any(k in ql for k in ("reciente", "últim", "ultim")),
        "is_current": any(k in ql for k in ("actual", "ahora", "ahora mismo", "en este momento")),
        "is_status": any(k in ql for k in ("estado", "cómo va", "como va", "en qué punto", "en que punto", "resumen")),
        "is_client": any(k in ql for k in ("cliente", "clientes")),
        "is_human": any(k in ql for k in ("equipo", "persona", "personas", "ánimo", "animo", "estrés", "estres", "frustr", "motiv")),
        "is_technical": any(k in ql for k in (
            "fast", "deep", "qa", "q&a", "ui", "frontend", "backend", "deploy", "desplieg",
            "rollout", "login", "ingress", "cache", "fallback", "llm", "ollama", "timeout",
            "bug", "bloque", "bloqueo", "error", "fix", "arregl", "correg", "prueba", "pruebas",
            "análisis", "analisis", "sentim", "kubernetes", "minikube", "api", "endpoint"
        )),
        "is_positive": any(k in ql for k in ("positivo", "positiva", "buen", "mejor", "avance", "avances")),
        "is_negative": any(k in ql for k in ("negativo", "negativa", "problema", "problemas", "riesgo", "riesgos", "bloque", "bloqueo")),
        "is_beginning": any(k in ql for k in ("principio", "inicio", "comienzo", "primeras semanas", "al principio")),
    }


def _fast_v2_clean_text(raw: str) -> str:
    txt = _truncate((raw or "").replace("\n", " "), 240)
    txt = re.sub(r"\s+", " ", txt).strip(" -")
    if not txt:
        return ""
    parts = [p.strip() for p in re.split(r'(?<=[.!?])\s+', txt) if p.strip()]
    intent_prefixes = (
        "objetivo", "hoy quiero", "voy a", "intentar", "espero",
        "quiero", "necesito", "me gustaría", "debo", "tengo que"
    )
    while len(parts) >= 2:
        first = parts[0].lower().lstrip(" -")
        if any(first.startswith(k) for k in intent_prefixes):
            parts = parts[1:]
        else:
            break
    txt = " ".join(parts).strip() if parts else txt
    txt = re.sub(r'(?i)^objetivo\s*:\s*', '', txt).strip()
    txt = re.sub(r"\s+", " ", txt).strip(" -")
    low = txt.lower()
    if any(low.startswith(k) for k in intent_prefixes):
        return ""
    if any(low.startswith(k) for k in ("resolver ", "resolver un ", "resolver una ", "si me bloqueo", "pediré ", "pedire ", "intentaré ", "intentare ")):
        return ""
    if any(k in low for k in ("estoy un poco neutro", "terminé de mal humor", "termine de mal humor", "me frustré", "me frustre", "fue negativo", "sensación negativa", "sensacion negativa")):
        return ""
    return txt


def _fast_v2_score_text(txt: str, profile: Dict[str, Any]) -> int:
    ltxt = txt.lower()
    score = 0

    technical_keys = (
        "fast", "deep", "qa", "q&a", "ui", "frontend", "backend", "deploy", "desplieg",
        "rollout", "login", "ingress", "cache", "fallback", "llm", "ollama", "timeout",
        "bug", "bloque", "bloqueo", "error", "fix", "arregl", "correg", "prueba", "pruebas",
        "análisis", "analisis", "sentim", "kubernetes", "minikube", "api", "endpoint"
    )
    human_keys = ("estrés", "estres", "frustr", "motiv", "cansancio", "agobi", "ánimo", "animo")
    client_keys = ("cliente", "clientes", "reunión", "reunion", "queja", "satisfecho", "satisfecha", "comunicación", "comunicacion")
    progress_keys = ("avance", "avances", "progreso", "se corrig", "se añadió", "se anadió", "se ajustó", "se ajusto", "se verificó", "se verifico", "se probó", "se probo", "desbloque")
    negative_keys = ("problema", "problemas", "riesgo", "riesgos", "bloque", "bloqueo", "error", "fallo", "incidencia")

    if any(k in ltxt for k in progress_keys):
        score += 2
    if any(k in ltxt for k in technical_keys):
        score += 3
    if any(k in ltxt for k in client_keys):
        score += 1
    if any(k in ltxt for k in human_keys):
        score += 1
    if any(k in ltxt for k in negative_keys):
        score += 2

    if profile.get("is_technical") and any(k in ltxt for k in technical_keys):
        score += 4
    if profile.get("is_client") and any(k in ltxt for k in client_keys):
        score += 4
    if profile.get("is_human") and any(k in ltxt for k in human_keys):
        score += 4
    if profile.get("is_positive") and any(k in ltxt for k in progress_keys + ("satisfecho", "bien", "positivo")):
        score += 2
    if profile.get("is_negative") and any(k in ltxt for k in negative_keys + human_keys):
        score += 2

    if profile.get("is_status") or profile.get("is_recent") or profile.get("is_current"):
        if any(k in ltxt for k in technical_keys):
            score += 3
        if any(k in ltxt for k in client_keys):
            score -= 2
        if any(k in ltxt for k in human_keys):
            score -= 2
        if any(k in ltxt for k in ("frustrado", "frustrada", "mal humor", "neutro", "neutral", "negativo", "negativa")) and not any(k in ltxt for k in technical_keys):
            score -= 3

    if len(txt) >= 45:
        score += 1

    return score


def _fast_v2_select_context_lines(all_items: List[CommentItem], d_to: Optional[date], question: str) -> List[str]:
    profile = _fast_v2_query_profile(question)

    recent_days = 14
    if profile["is_recent"]:
        recent_days = 21
    elif profile["is_status"] or profile["is_current"]:
        recent_days = 30
    if profile["is_beginning"]:
        recent_days = 60

    cutoff = (d_to - timedelta(days=recent_days)) if (d_to and recent_days > 0) else None
    items_sorted = sorted(all_items, key=lambda it: getattr(it, "created_date", None) or date.min, reverse=True)

    scored = []
    for idx, it in enumerate(items_sorted):
        d = getattr(it, "created_date", None)
        if cutoff and d and d < cutoff and not profile["is_beginning"]:
            continue
        txt = _fast_v2_clean_text(getattr(it, "text", "") or "")
        if not txt:
            continue
        score = _fast_v2_score_text(txt, profile)
        if score <= 0:
            continue
        prefix = f"{d.isoformat()} " if d else ""
        scored.append((score, idx, f"- {prefix}{txt}"))

    if not scored and cutoff is not None:
        for idx, it in enumerate(items_sorted[:30]):
            d = getattr(it, "created_date", None)
            txt = _fast_v2_clean_text(getattr(it, "text", "") or "")
            if not txt:
                continue
            score = _fast_v2_score_text(txt, profile)
            if score <= 0:
                continue
            prefix = f"{d.isoformat()} " if d else ""
            scored.append((score, idx, f"- {prefix}{txt}"))

    seen = set()
    out: List[str] = []
    for _, _, line in sorted(scored, key=lambda x: (-x[0], x[1])):
        line_wo_date = re.sub(r'^-\s*\d{4}-\d{2}-\d{2}\s+', '- ', line)
        norm = re.sub(r'[^a-z0-9áéíóúñ]+', ' ', line_wo_date.lower()).strip()
        norm = " ".join(norm.split()[:12])
        if not norm or norm in seen:
            continue
        seen.add(norm)
        out.append(_truncate(line, 220))
        if len(out) >= 7:
            break

    return out


def answer_project_question(
    project_id: int,
    user_id: int,
    query: str,
    scope: str = "all",
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    include_items: bool = False,
    items_limit: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Q&A basado en evidencias.
    - Reutiliza el retrieval existente (keyword + embeddings).
    - Llama a Ollama para redactar respuesta larga.
    - No inventa: si no hay evidencias suficientes, lo indica.
    """
    all_items = collect_project_comments(
        project_id=project_id,
        user_id=user_id,
        scope=scope,
        date_from=date_from,
        date_to=date_to,
    )

    # FAST: cobertura completa con resúmenes semanales (sin selección top-N)
    prj = Project.query.filter_by(id=project_id, user_id=user_id).first()
    if not prj:
        raise ValueError("Proyecto no encontrado o sin permisos.")

    dated = [it.created_date for it in all_items if getattr(it, "created_date", None)]
    if dated:
        d_from = min(dated)
        d_to = max(dated)
    else:
        base = getattr(prj, "created_at", None) or date.today()
        d_from = base
        d_to = base

    weeks = _daterange_weeks(d_from, d_to)
    algo_version = _as_int(os.getenv("QA_DEEP_ALGO_VERSION") or "1", 1)

    weekly_summaries: List[Dict[str, Any]] = []
    cache_hits = 0

    for ws, we in weeks:
        items_week = [
            it for it in all_items
            if it.created_date and (it.created_date >= ws) and (it.created_date <= we)
        ]

        if not items_week:
            weekly_summaries.append(
                {
                    "week_start": ws.isoformat(),
                    "week_end": we.isoformat(),
                    "summary": "Semana sin notas registradas.",
                    "from_cache": True,
                }
            )
            continue

        summary_text, meta, from_cache = _load_or_build_week_summary(
            project_id=project_id,
            user_id=user_id,
            scope=scope,
            algo_version=algo_version,
            week_start=ws,
            week_end=we,
            items=items_week,
        )
        if from_cache:
            cache_hits += 1

        weekly_summaries.append(
            {
                "week_start": ws.isoformat(),
                "week_end": we.isoformat(),
                "summary": summary_text or "",
                "llm": meta,
                "from_cache": from_cache,
            }
        )

    def _strip_ids(s: str) -> str:
        s = s or ""
        s = re.sub(r"\[\s*id\s*=\s*[^\]]+\]", "", s, flags=re.IGNORECASE)
        s = re.sub(r"\bid\s*=\s*\d+\b", "", s, flags=re.IGNORECASE)
        s = re.sub(r"\btask_id\s*=\s*\d+\b", "", s, flags=re.IGNORECASE)
        s = re.sub(r"[ \t]{2,}", " ", s)
        s = re.sub(r"[ \t]*\n[ \t]*", "\n", s)
        return s.strip()

    max_week_chars = _as_int(os.getenv("QA_FAST_WEEK_SUMMARY_MAX_CHARS") or "1400", 1400)

    if not query or not str(query).strip():
        question = ""
    else:
        question = str(query).strip()
    ql = (question or "").lower()
    recent_weeks = _as_int(os.getenv("QA_FAST_RECENT_WEEKS") or "4", 4)
    weekly_summaries_for_prompt = weekly_summaries
    if any(k in ql for k in ("ultim", "últim", "recient")) and recent_weeks > 0 and len(weekly_summaries) > recent_weeks:
        weekly_summaries_for_prompt = weekly_summaries[-recent_weeks:]

    max_total_week_chars = _as_int(os.getenv("QA_FAST_SUMMARIES_TOTAL_MAX_CHARS") or "14000", 14000)

    total_chars = 0
    summary_lines: List[str] = []
    for w in weekly_summaries_for_prompt:
        ws = w.get("week_start")
        we = w.get("week_end")
        raw = _strip_ids(str(w.get("summary") or ""))
        raw = _truncate(raw, max_week_chars)
        if not raw:
            continue
        if total_chars + len(raw) > max_total_week_chars:
            break
        total_chars += len(raw)
        summary_lines.append(f"- (semana {ws} a {we}) {raw}")

    use_fast_v2 = (os.getenv("QA_FAST_V2_ENABLED") or "1").strip().lower() not in ("0", "false", "no")
    if use_fast_v2:
        fast_v2_lines = _fast_v2_select_context_lines(all_items, d_to, question)
        if fast_v2_lines:
            summary_lines = fast_v2_lines

    relevant_items = all_items
    filter_meta = {
        "fast_mode": "weekly_summaries",
        "algo_version": algo_version,
        "weeks_total": len(weeks),
        "cache_hits": cache_hits,
        "summaries_used": len(summary_lines),
        "summaries_char_budget": max_total_week_chars,
        "recent_weeks_used": len(weekly_summaries_for_prompt),
    }
    if use_fast_v2 and summary_lines and not summary_lines[0].startswith("- (semana "):
        filter_meta["fast_mode"] = "fast_v2_recent_context"
        filter_meta["selected_context_lines"] = len(summary_lines)

    if not summary_lines:
        return {
            "query": query,
            "scope": scope,
            "date_from": date_from,
            "date_to": date_to,
            "total_items": len(all_items),
            "relevant_items": len(relevant_items),
            "filter": filter_meta,
            "status": "no_data",
            "answer_mode": "no_data",
            "is_fallback": False,
            "message": "No hay información suficiente para responder a la pregunta.",
            "answer": "",
            "evidences": [],
        }

    project_desc = (getattr(prj, "description", None) or "").strip()

    task_context_lines: List[str] = []
    if scope in ("all", "tasks"):
        for tsk in Task.query.filter_by(project_id=project_id, user_id=user_id).all():
            titulo = (
                getattr(tsk, "titulo", None)
                or getattr(tsk, "title", None)
                or getattr(tsk, "name", None)
                or ""
            ).strip()
            desc = (getattr(tsk, "descripcion", None) or "").strip()
            estado = (getattr(tsk, "estado", None) or "").strip()
            if desc:
                head = titulo or "Tarea sin título"
                if estado:
                    task_context_lines.append(f"- {head} ({estado}): {_truncate(desc, 240)}")
                else:
                    task_context_lines.append(f"- {head}: {_truncate(desc, 240)}")

    stats: Dict[str, Any] = {}
    try:
        stats = get_project_time_stats(project_id, user_id)
    except Exception:
        stats = {}

    include_project_desc = any(k in ql for k in (
        "objetivo", "objetivos", "alcance", "contexto", "descrip", "descripción",
        "de que va", "de qué va", "trata", "resumen general del proyecto"
    ))
    include_task_context = any(k in ql for k in (
        "tarea", "tareas", "cliente", "equipo", "bloque", "bloqueo", "bloqueos",
        "problema", "problemas", "riesgo", "riesgos", "incidencia", "incidencias"
    ))
    include_stats = any(k in ql for k in (
        "tiempo", "tiempos", "hora", "horas", "progreso", "avance", "estimad",
        "real", "desviación", "desviacion", "porcentaje", "stats"
    ))
    is_summary_question = any(k in ql for k in (
        "resumen", "estado", "situacion", "situación", "reciente", "cómo va", "como va"
    ))

    status_lines: List[str] = []
    if is_summary_question:
        status_recent_days = _as_int(os.getenv("QA_FAST_STATUS_RECENT_DAYS") or "30", 30)
        status_limit = _as_int(os.getenv("QA_FAST_STATUS_LINES") or "6", 6)
        status_cutoff = (d_to - timedelta(days=status_recent_days)) if (d_to and status_recent_days > 0) else None
        status_keywords = (
            "fast", "deep", "qa", "q&a", "ui", "frontend", "backend", "deploy", "desplieg",
            "rollout", "login", "ingress", "cache", "fallback", "llm", "ollama", "timeout",
            "bug", "bloque", "bloqueo", "error", "fix", "arregl", "correg", "prueba", "pruebas",
            "análisis", "analisis", "sentim", "kubernetes", "minikube", "api", "endpoint"
        )
        intent_prefixes = (
            "objetivo", "hoy quiero", "voy a", "intentar", "espero",
            "quiero", "necesito", "me gustaría", "debo", "tengo que"
        )
        scored_status: List[Tuple[int, int, str]] = []
        items_sorted = sorted(all_items, key=lambda it: getattr(it, "created_date", None) or date.min, reverse=True)
        for idx, it in enumerate(items_sorted):
            d = getattr(it, "created_date", None)
            if status_cutoff and d and d < status_cutoff:
                continue
            txt = (getattr(it, "text", None) or "").strip()
            if not txt:
                continue
            txt = re.sub(r"\s+", " ", txt).strip(" -")
            parts = [pp.strip() for pp in re.split(r'(?<=[.!?])\s+', txt) if pp.strip()]
            while len(parts) >= 2:
                first = parts[0].lower().lstrip(" -")
                if any(first.startswith(k) for k in intent_prefixes):
                    parts = parts[1:]
                else:
                    break
            txt = " ".join(parts).strip() if parts else txt
            txt = re.sub(r'(?i)^objetivo\s*:\s*', '', txt).strip()
            txt = re.sub(r"\s+", " ", txt).strip(" -")
            if not txt:
                continue
            ltxt = txt.lower()
            score = 0
            if any(k in ltxt for k in status_keywords):
                score += 3
            if any(k in ltxt for k in ("se corrig", "se añadió", "se anadió", "se ajustó", "se ajusto", "se verificó", "se verifico", "se probó", "se probo")):
                score += 2
            if any(k in ltxt for k in ("cliente", "satisfecho", "frustr", "estres", "estrés")):
                score -= 1
            if len(txt) >= 50:
                score += 1
            if score > 0:
                scored_status.append((score, idx, txt))

        seen_status = set()
        for _, _, txt in sorted(scored_status, key=lambda x: (-x[0], x[1]))[: max(status_limit * 3, status_limit)]:
            norm = re.sub(r'[^a-z0-9áéíóúñ]+', ' ', txt.lower()).strip()
            norm = " ".join(norm.split()[:12])
            if not norm or norm in seen_status:
                continue
            seen_status.add(norm)
            status_lines.append(f"- {_truncate(txt, 180)}")
            if len(status_lines) >= status_limit:
                break

    system = (
        "Eres un analista de progreso de proyectos. Responde usando SOLO la información proporcionada.\n"
        "Este es el modo FAST: un vistazo rápido para situarse, como leer el resumen de una presentación justo antes de exponerla.\n"
        "La respuesta debe ser breve, clara y útil para entender en qué punto está el proyecto, sin entrar en detalle fino.\n"
        "La fuente principal es el contexto reciente y priorizado para la pregunta; la descripción del proyecto, las tareas y las stats son contexto auxiliar y pueden ignorarse si no aportan a la pregunta. Si también hay resúmenes semanales útiles, tómalos solo como apoyo.\n"
        "PROHIBIDO: citas o referencias (no uses [1], [2]..., ni [id=...]) y no menciones ids (ni 'id=...', ni números de tarea/sesión/hito).\n"
        "Usa lenguaje natural. No inventes. Si falta evidencia para algo, dilo de forma breve y clara.\n"
        "Habla siempre como analista externo del proyecto, nunca en primera persona, aunque las notas de entrada estén redactadas en primera persona.\n"
        "No escribas frases como 'necesito', 'quiero', 'me quedé', 'pediré ayuda', 'cumplimos' o similares salvo que estés citando literalmente, y en FAST no debes citar literalmente.\n"
        "Prioriza estado actual, avances relevantes, bloqueos relevantes y pruebas/cambios importantes si aparecen en el material.\n"
        "No conviertas la respuesta en un análisis profundo ni en una lista de detalles menores.\n"
        "Evita frases vacías o de plantilla como 'la situación es mixta', 'hubo avances y riesgos' o similares.\n"
        "No centres la respuesta en tono emocional salvo que afecte claramente al progreso del proyecto.\n"
        "Si la pregunta pide un resumen o estado, responde en 3 a 5 frases como máximo: 1 frase para situar el estado, 2 o 3 ideas clave y 1 conclusión breve final.\n"
        "No incluyas recomendaciones ni siguientes pasos salvo que el usuario lo pida explícitamente.\n"
    )

    user_parts: List[str] = []
    user_parts.append(f"Pregunta: {question}")
    user_parts.append("")
    if is_summary_question:
        user_parts.append("Instrucción específica: responde como un vistazo rápido de situación. Sitúa primero en qué punto está el proyecto, menciona 2 o 3 ideas clave realmente útiles y cierra con una conclusión breve. Redacta siempre como analista externo, no como si fueras quien escribió las notas.")
        user_parts.append("")
    if status_lines:
        user_parts.append("Señales recientes del proyecto (priorizadas):")
        user_parts.extend(status_lines)
        user_parts.append("")
    if include_project_desc and project_desc:
        user_parts.append("Contexto auxiliar del proyecto:")
        user_parts.append(_truncate(project_desc, 800))
        user_parts.append("")
    if include_task_context and task_context_lines:
        user_parts.append("Contexto auxiliar de tareas (descripciones):")
        user_parts.extend(task_context_lines[:80])
        user_parts.append("")
    if include_stats and stats:
        user_parts.append("Stats auxiliares (estimado vs real / progreso):")
        user_parts.append(json.dumps(stats, ensure_ascii=False))
        user_parts.append("")

        # FAST: si preguntan por problemas/riesgos/bloqueos, añadir extractos literales recientes (scan completo)
    neg_lines: List[str] = []
    if any(k in ql for k in ("problema","riesgo","bloque","retras","atras","tension","tensión","estres","estrés","frustr","caotic","caótic","descontrol","malentend","molesto","descontent","scope creep")):
        neg_limit = _as_int(os.getenv("QA_FAST_NEG_SNIPPETS_LIMIT") or "12", 12)
        recent_days = _as_int(os.getenv("QA_FAST_RECENT_DAYS") or "60", 60)
        cutoff = (d_to - timedelta(days=recent_days)) if (d_to and recent_days > 0) else None

        neg_keys = (
            "scope creep","tension","tensión","tenso","tensa",
            "molesto","molesta","descontent","descontento","queja",
            "malentend","estres","estrés","agob",
            "frustr","caotic","caótic","descontrol","caos",
            "retras","atras","bloque","bug","crít","crit",
            "cansad","agotad","cansancio",
            "reunión tensa","cliente molesto","presión","presion"
        )
        neutral_phrases = ("sin novedades","sin incidencias","sin problemas","ningún problema","ningun problema","todo ok","todo bien")

        items_sorted = sorted(all_items, key=lambda it: getattr(it, "created_date", None) or date.min, reverse=True)
        for it in items_sorted:
            d = getattr(it, "created_date", None)
            if cutoff and d and d < cutoff:
                continue
            txt = (getattr(it, "text", None) or "").strip()
            if not txt:
                continue
            ltxt = txt.lower()
            if any(p in ltxt for p in neutral_phrases):
                continue
            if any(k in ltxt for k in neg_keys):
                prefix = f"{d.isoformat()} " if d else ""
                neg_lines.append(f"- {prefix}{_truncate(txt, 220)}")
                if len(neg_lines) >= neg_limit:
                    break

        filter_meta["neg_snippets"] = len(neg_lines)
        filter_meta["neg_recent_days"] = recent_days

    if neg_lines:
        user_parts.append("Señales negativas recientes (extractos literales):")
        user_parts.extend(neg_lines)
        user_parts.append("")

    user_parts.append("Contexto principal para esta pregunta:")
    user_parts.extend(summary_lines)
    user_parts.append("")
    user_parts.append("Redacta una respuesta FAST siguiendo las reglas (sin citas/IDs).")

    user_msg = "\n".join(user_parts)

    answer, llm_meta = _ollama_chat(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_msg},
        ],
        timeout_override_s=_as_float(os.getenv("QA_FAST_LLM_TIMEOUT_SECS") or "25", 25.0),
        num_predict_override=_as_int(os.getenv("QA_FAST_LLM_NUM_PREDICT") or "220", 220),
        retries=1,
    )

    if answer is None:
        fallback_lines: List[str] = []

        # Si venían señales negativas, usarlas como respuesta base
        if neg_lines:
            fallback_lines.append("No he podido generar una respuesta completa a tiempo, pero en las notas recientes aparecen estas señales:")
            fallback_lines.extend(neg_lines[:8])
        else:
            fallback_lines.append("No he podido generar una respuesta completa a tiempo y no he encontrado señales claras en las notas recientes para esta pregunta.")

        #Cierre único
        fallback_lines.append("")
        if filter_meta.get("neg_snippets", 0):
            fallback_lines.append("En resumen, hay señales de tensión/riesgos recientes según las notas disponibles.")
        else:
            fallback_lines.append("En resumen, no hay señales destacables recientes según las notas disponibles.")
        return {
            "query": query,
            "scope": scope,
            "date_from": date_from,
            "date_to": date_to,
            "total_items": len(all_items),
            "relevant_items": len(relevant_items),
            "filter": filter_meta,
            "status": "ok",
            "message": "Respuesta rápida (fallback) por timeout del LLM.",
            "answer_mode": "fallback",
            "is_fallback": True,
            "llm": llm_meta,
            "answer": "\n". join(fallback_lines).strip(),
            "evidences": [],
        }

    def _clean_fast_answer(text: str) -> str:
        text = text or ""
        text = re.sub(r"\[\s*\d+\s*\]", "", text)
        text = re.sub(r"\[\s*id\s*=\s*[^\]]+\]", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\bid\s*=\s*\d+\b", "", text, flags=re.IGNORECASE)
        text = re.sub(
            r'(?im)^\s*\*{0,2}\s*(HECHOS CLAVE(?: DEL PERIODO RECIENTE)?|ESTADO/TONO GENERAL|RIESGOS/CAMBIOS|RESUMEN ESTÁTICO Y CONCRETO|ESTADO RECIENTE|SITUACIÓN ACTUAL)\s*:?\s*\*{0,2}\s*$',
            '',
            text,
        )
        text = re.sub(r'(?im)^\s*[-*]\s*Sin evidencia[^\n]*$', '', text)
        if filter_meta.get("neg_snippets", 0):
            text = re.sub(r'(?i)\bSin evidencia de [^.\n]*\.', '', text).strip()
        text = re.sub(r'(?i)\b(el estado general es|la situación general es)\s+(positivo|negativo|mixto)(?:\s+generalizado)?\b\s*;?\s*', '', text)
        text = re.sub(r"[ \t]{2,}", " ", text)
        text = re.sub(r"[ \t]*\n[ \t]*", "\n", text)
        text = re.sub(r'(?m)\n{3,}', '\n\n', text).strip()
        return text

    def _fast_answer_needs_repair(text: str) -> bool:
        txt = (text or "").strip()
        if not txt:
            return True
        if re.search(r'(?im)^\s*\*{0,2}\s*[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ0-9 /_-]{6,}\s*:?\s*\*{0,2}\s*$', txt):
            return True
        if is_summary_question and re.search(r'(?i)\b(el estado general es|la situación general es|negativo generalizado|positivo generalizado|mixto|el último periodo muestra|punto intermedio|se requiere más tiempo y recursos)\b', txt):
            return True
        if is_summary_question:
            concrete_markers = re.findall(
                r'(?i)\b(se corrigió|se añadió|se eliminó|se verificó|se probó|se desplegó|se reconstruyó|se ajustó|se marcó|timeout|fallback|answer_mode|is_fallback|fast|deep|ui|login|ingress|ollama|rollout|minikube|kubernetes)\b',
                txt,
            )
            if len(txt) < 320 and len(concrete_markers) < 2:
                return True
        return False

    def _repair_fast_answer(text: str) -> Tuple[str, Dict[str, Any]]:
        repair_system = (
            "Reescribe una respuesta FAST de progreso de proyectos.\n"
            "Devuelve SOLO la respuesta final en español.\n"
            "Objetivo: que sirva como vistazo rápido para situarse, no como análisis profundo.\n"
            "Sin encabezados, sin bullets, sin Markdown y sin etiquetas globales de tono como positivo/negativo/mixto.\n"
            "Escribe siempre como analista externo en tercera persona o en forma impersonal; nunca en primera persona del singular o plural.\n"
            "Debe tener 3 a 5 frases como máximo: una para situar el estado, dos o tres ideas clave y una conclusión breve final.\n"
            "Prioriza avances relevantes, bloqueos relevantes y cambios o pruebas importantes si aparecen en el material.\n"
            "No inventes, no cites ids ni referencias y evita frases vacías o demasiado genéricas.\n"
            "No uses expresiones vagas como 'punto intermedio' ni cierres tipo 'se requiere más tiempo y recursos'.\n"
            "La conclusión debe decir de forma breve qué está condicionando ahora mismo el avance de lo preguntado.\n"
        )
        repair_user = (
            user_msg
            + "\n\nRespuesta original a reparar:\n"
            + (text or "")
            + "\n\nReescribe ahora SOLO la respuesta final siguiendo todas las reglas."
        )
        repaired, repaired_meta = _ollama_chat(
            messages=[
                {"role": "system", "content": repair_system},
                {"role": "user", "content": repair_user},
            ],
            timeout_override_s=min(_as_float(os.getenv("QA_FAST_LLM_TIMEOUT_SECS") or "25", 25.0), 60.0),
            num_predict_override=_as_int(os.getenv("QA_FAST_LLM_NUM_PREDICT") or "220", 220),
            retries=1,
        )
        return (repaired or text or "", repaired_meta or {})

    answer = _clean_fast_answer(answer if isinstance(answer, str) else "")
    if _fast_answer_needs_repair(answer):
        repaired_answer, repaired_meta = _repair_fast_answer(answer)
        answer = _clean_fast_answer(repaired_answer)
        if repaired_meta:
            llm_meta = dict(llm_meta or {})
            llm_meta["fast_repair"] = repaired_meta

    # FAST: no forzamos un cierre determinista; el modelo (wrapper) ya incluye conclusión.
    answer = (answer or "").strip()
    if not answer:
        answer = "No hay evidencia suficiente en los apuntes para responder con fiabilidad a esta pregunta."

    result: Dict[str, Any] = {
        "query": query,
        "scope": scope,
        "date_from": date_from,
        "date_to": date_to,
        "total_items": len(all_items),
        "relevant_items": len(relevant_items),
        "filter": filter_meta,
        "status": "ok",
        "answer_mode": "llm",
        "is_fallback": False,
        "llm": llm_meta,
        "answer": answer,
        "evidences": [],
    }

    # Opcional: devolver items completos (igual que sentiment)
    if include_items:
        items_payload = [_item_to_evidence(it) for it in relevant_items]
        if items_limit is not None:
            try:
                lim = int(items_limit)
            except Exception:
                lim = None
            if lim is not None and lim >= 0:
                items_payload = items_payload[:lim]
        result["items"] = items_payload

    return result


def _week_start(d: date) -> date:
    # Semana ISO: lunes como inicio
    return d - timedelta(days=d.weekday())


def _week_end(d: date) -> date:
    ws = _week_start(d)
    return ws + timedelta(days=6)


def _daterange_weeks(d_from: date, d_to: date) -> List[Tuple[date, date]]:
    """
    Devuelve lista de semanas (lunes..domingo) que cubren [d_from, d_to].
    """
    if d_from > d_to:
        return []
    cur = _week_start(d_from)
    last = _week_start(d_to)
    out: List[Tuple[date, date]] = []
    while cur <= last:
        out.append((cur, cur + timedelta(days=6)))
        cur += timedelta(days=7)
    return out


def _load_or_build_week_summary(
    *,
    project_id: int,
    user_id: int,
    scope: str,
    algo_version: int,
    week_start: date,
    week_end: date,
    items: List[CommentItem],
) -> Tuple[str, Dict[str, Any], bool]:
    """
    Devuelve (summary_text, meta, from_cache)
    """
    existing = QaChunkSummary.query.filter_by(
        project_id=project_id,
        user_id=user_id,
        scope=scope,
        algo_version=algo_version,
        week_start=week_start,
    ).first()

    if existing and existing.summary:
        meta = {}
        if existing.meta_json:
            try:
                meta = json.loads(existing.meta_json)
            except Exception:
                meta = {}
        return existing.summary, meta, True

    # Construir resumen semanal (MAP)
    max_items = _as_int(os.getenv("QA_CHUNK_MAX_ITEMS") or "120", 120)
    max_chars_item = _as_int(os.getenv("QA_CHUNK_MAX_CHARS_ITEM") or "280", 280)

    lines: List[str] = []
    for it in items[:max(max_items, 1)]:
        txt = _truncate(it.text, max_chars_item)
        if not txt:
            continue
        meta_bits = []
        if it.created_date:
            meta_bits.append(f"date={it.created_date.isoformat()}")
        meta_bits.append(f"source={it.source}")
        meta_bits.append(f"id={it.source_id}")
        if it.task_id:
            meta_bits.append(f"task_id={it.task_id}")
        lines.append(f"- ({' '.join(meta_bits)}) {txt}")

    system = (
        "Eres un analista de progreso de proyectos. Debes resumir SOLO hechos verificables que aparezcan en las notas de la semana.\n"
        "Objetivo: producir un resumen semanal útil para responder después preguntas FAST y DEEP sobre el proyecto.\n"
        "Conserva trazabilidad: cada bullet debe terminar con una o más citas al final usando EXACTAMENTE ids presentes en las notas, con formato [id=123] o [id=123, id=456].\n"
        "Devuelve entre 3 y 6 bullets como máximo, cada uno con una frase completa, concreta y útil.\n"
        "Cada bullet debe describir un hecho, avance, bloqueo, incidencia, decisión o resultado de esa semana.\n"
        "PROHIBIDO: bullets vacíos, bullets que sean solo citas, secciones fijas tipo HECHOS/TONO/RIESGOS, texto 'Sin evidencia' y generalidades vacías.\n"
        "Prioriza lo específico sobre el tono. Solo menciona estados emocionales si explican un bloqueo, un riesgo o un avance real en el trabajo.\n"
        "No inventes. Si una idea no está en las notas, no la pongas.\n"
        "La última línea debe empezar EXACTAMENTE por 'En resumen,' y cerrar la semana con una frase factual breve que también lleve cita(s).\n"
    )

    user_msg = (
        f"Semana: {week_start.isoformat()} a {week_end.isoformat()}\n"
        f"Scope: {scope}\n\n"
        "Notas de la semana:\n"
        + "\n".join(lines)
        + "\n\n"
        "Redacta el resumen semanal. Recuerda: 3 a 6 bullets concretos, sin secciones fijas, sin bullets vacíos y con una línea final que empiece por 'En resumen,'."
    )

    summary_text, llm_meta = _ollama_chat(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_msg},
        ]
    )

    def _week_summary_invalid(text: str) -> bool:
        txt = (text or "").strip()
        if not txt:
            return True
        if re.search(r'(?im)^\s*(HECHOS CLAVE|ESTADO/TONO GENERAL|RIESGOS/CAMBIOS)\s*:?\s*$', txt):
            return True
        if re.search(r'(?i)\bSin evidencia\b', txt):
            return True
        bullets = re.findall(r'(?m)^\s*-\s+.+$', txt)
        if not bullets:
            return True
        for b in bullets:
            core = re.sub(r'\[id=[^\]]+\]', '', b)
            core = re.sub(r'^\s*-\s*', '', core).strip()
            if len(core) < 12:
                return True
        if not re.search(r'(?m)^En resumen,\s+.+\[id=[^\]]+\]\s*$', txt):
            return True
        return False

    def _fallback_week_summary(items: List[CommentItem]) -> str:
        def _clean_item_text(raw: str) -> str:
            txt = _truncate((raw or "").replace("\n", " "), 220)
            txt = re.sub(r"\s+", " ", txt).strip(" -")
            if not txt:
                return ""
            parts = [p.strip() for p in re.split(r'(?<=[.!?])\s+', txt) if p.strip()]
            intent_prefixes = (
                "objetivo", "hoy quiero", "voy a", "intentar", "espero",
                "quiero", "necesito", "me gustaría", "debo", "tengo que"
            )
            while len(parts) >= 2:
                first = parts[0].lower().lstrip(" -")
                if any(first.startswith(k) for k in intent_prefixes):
                    parts = parts[1:]
                else:
                    break
            txt = " ".join(parts).strip() if parts else txt
            txt = re.sub(r'(?i)^objetivo\s*:\s*', '', txt).strip()
            txt = re.sub(r"\s+", " ", txt).strip(" -")
            return txt

        def _score_text(txt: str) -> int:
            ltxt = txt.lower()
            score = 0
            if any(k in ltxt for k in (
                "cliente", "reunión", "reunion", "bug", "bloque", "bloqueo",
                "frustr", "estrés", "estres", "agobi", "queja", "satisfe",
                "avance", "cumpl", "problema", "incidencia", "análisis",
                "analisis", "sentim", "qa", "fast", "deep", "ui", "backend",
                "frontend", "deploy", "desplieg", "fallback", "llm", "cache",
                "login", "ingress", "prueba", "pruebas"
            )):
                score += 2
            if any(k in ltxt for k in (
                "se corrig", "se añadió", "se anadió", "se ajustó", "se ajusto",
                "se verificó", "se verifico", "se probó", "se probo", "éxito",
                "exito", "quedó satisfecho", "quedo satisfecho"
            )):
                score += 1
            if any(ltxt.startswith(k) for k in ("espero", "quiero", "voy a", "intentar", "necesito")):
                score -= 1
            if len(txt) >= 40:
                score += 1
            return score

        candidates: List[Tuple[int, int, str, int]] = []
        for idx, it in enumerate(items[:12]):
            txt = _clean_item_text(getattr(it, "text", "") or "")
            if not txt:
                continue
            sid = int(getattr(it, "source_id", 0) or 0)
            candidates.append((_score_text(txt), idx, txt, sid))

        if not candidates:
            return "No se pudo generar resumen semanal (sin contenido útil)."

        candidates.sort(key=lambda x: (-x[0], x[1]))
        out: List[str] = []
        seen = set()
        used_ids: List[int] = []
        pos = 0
        neg = 0

        for _, _, txt, sid in candidates:
            norm = re.sub(r'[^a-z0-9áéíóúñ]+', ' ', txt.lower()).strip()
            norm = " ".join(norm.split()[:12])
            if norm in seen:
                continue
            seen.add(norm)
            out.append(f"- {txt} [id={sid}]")
            used_ids.append(sid)

            ltxt = txt.lower()
            if any(k in ltxt for k in ("bloque", "bloqueo", "bug", "frustr", "estrés", "estres", "agobi", "queja", "problema", "incidencia", "cansancio")):
                neg += 1
            if any(k in ltxt for k in ("avance", "satisfe", "cumpl", "fluida", "éxito", "exito", "positivo", "bien", "se corrig", "se añadió", "se ajustó", "se verificó", "se probó")):
                pos += 1

            if len(out) >= 4:
                break

        if not out:
            return "No se pudo generar resumen semanal (sin contenido útil)."

        cite = ", ".join(f"id={sid}" for sid in used_ids[:3] if sid)
        if pos and neg:
            closing = f"En resumen, la semana combina avances concretos con incidencias o bloqueos relevantes según las notas disponibles [{cite}]."
        elif neg:
            closing = f"En resumen, en la semana predominan incidencias o bloqueos relevantes según las notas disponibles [{cite}]."
        elif pos:
            closing = f"En resumen, en la semana predominan avances concretos según las notas disponibles [{cite}]."
        else:
            closing = f"En resumen, la semana recoge actividad concreta del proyecto según las notas disponibles [{cite}]."

        out.append(closing)
        return "\n".join(out)

    if summary_text is None or _week_summary_invalid(summary_text):
        summary_text = _fallback_week_summary(items)
        llm_meta = dict(llm_meta or {})
        llm_meta["week_summary_fallback"] = True

    rec = QaChunkSummary(
        project_id=project_id,
        user_id=user_id,
        week_start=week_start,
        week_end=week_end,
        scope=scope,
        algo_version=algo_version,
        summary=summary_text,
        meta_json=json.dumps(llm_meta, ensure_ascii=False),
    )
    db.session.add(rec)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        existing2 = QaChunkSummary.query.filter_by(
            project_id=project_id,
            user_id=user_id,
            scope=scope,
            algo_version=algo_version,
            week_start=week_start,
        ).first()
        if existing2 and existing2.summary:
            meta2 = {}
            if existing2.meta_json:
                try:
                    meta2 = json.loads(existing2.meta_json)
                except Exception:
                    meta2 = {}
            return existing2.summary, meta2, True
        # si no existe por lo que sea, propagamos
        raise

    return summary_text, llm_meta, False


def answer_project_question_deep(
    project_id: int,
    user_id: int,
    query: str,
    scope: str = "all",
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    progress_cb: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    """
    Modo DEEP: full scan por semanas (MAP) + fusión (REDUCE).
    - Recorre TODAS las semanas del intervalo.
    - Cachea resúmenes semanales en qa_chunk_summaries.
    - Reduce final responde a la pregunta usando:
        - resúmenes semanales
        - stats estimado vs real del proyecto
    """
    # Verificar permisos proyecto
    prj = Project.query.filter_by(id=project_id, user_id=user_id).first()
    if not prj:
        raise ValueError("Proyecto no encontrado o sin permisos.")

    # Rango temporal: si no hay date_from/date_to, inferimos del proyecto/sesiones/hitos
    d_from = None
    d_to = None

    if date_from:
        try:
            d_from = date.fromisoformat(date_from)
        except Exception:
            d_from = None
    if date_to:
        try:
            d_to = date.fromisoformat(date_to)
        except Exception:
            d_to = None

    if d_from is None or d_to is None:
        # Inferencia simple: min/max entre sesiones y hitos del proyecto.
        task_ids = [t.id for t in Task.query.filter_by(project_id=project_id, user_id=user_id).all()]
        sess_dates: List[date] = []
        if task_ids:
            sess_dates = [s.fecha for s in WorkSession.query.filter(WorkSession.tarea_id.in_(task_ids)).all() if s.fecha]
        ms_dates = [m.fecha for m in Milestone.query.filter_by(project_id=project_id).all() if m.fecha]

        all_dates = [d for d in (sess_dates + ms_dates) if d]
        # fallback si no hay nada
        if not all_dates:
            base = prj.created_at or date.today()
            d_from = d_from or base
            d_to = d_to or base
        else:
            d_from = d_from or min(all_dates)
            d_to = d_to or max(all_dates)

    weeks = _daterange_weeks(d_from, d_to)

    total_weeks = len(weeks)
    if progress_cb:
        progress_cb({"stage": "map", "done": 0, "total": total_weeks + 1})

    algo_version = _as_int(os.getenv("QA_DEEP_ALGO_VERSION") or "1", 1)

    weekly_summaries: List[Dict[str, Any]] = []
    cache_hits = 0

    # Generar items por semana según scope
    # Importante: para chunk semanal, tomamos solo elementos con fecha (sesiones + hitos).
    # Project.description y Task.descripcion se consideran "contexto global" (no semanal) y se meterán en reduce.
    task_ids = [t.id for t in Task.query.filter_by(project_id=project_id, user_id=user_id).all()]
    tasks_by_id: Dict[int, Task] = {t.id: t for t in Task.query.filter_by(project_id=project_id, user_id=user_id).all()}

    had_any_items = False

    for ws, we in weeks:
        if progress_cb:
            progress_cb({
                "stage": "map",
                "done": len(weekly_summaries),
                "total": total_weeks + 1,
                "week_start": ws.isoformat(),
                "week_end": we.isoformat(),
            })
        items_week: List[CommentItem] = []

        if scope in ("all", "sessions"):
            if task_ids:
                q = WorkSession.query.filter(WorkSession.tarea_id.in_(task_ids))
                q = q.filter(WorkSession.fecha >= ws).filter(WorkSession.fecha <= we)
                for s in q.all():
                    pre, post = ("", "")
                    # reutilizamos parser de sentiment_service indirectamente: ya viene en text si usamos collect_project_comments,
                    # pero aquí no lo importamos para no acoplar más. Tomamos notas crudas.
                    raw = (getattr(s, "notas", None) or "").strip()
                    if raw:
                        items_week.append(
                            CommentItem(
                                source="session",
                                source_id=s.id,
                                text=raw,
                                created_date=s.fecha,
                                task_id=getattr(s, "tarea_id", None),
                                pre_text=None,
                                post_text=None,
                            )
                        )

        if scope in ("all", "milestones"):
            q = Milestone.query.filter_by(project_id=project_id)
            q = q.filter(Milestone.fecha >= ws).filter(Milestone.fecha <= we)
            for m in q.all():
                txt = (getattr(m, "descripcion", None) or "").strip()
                if txt:
                    items_week.append(
                        CommentItem(
                            source="milestone",
                            source_id=m.id,
                            text=txt,
                            created_date=m.fecha,
                            task_id=None,
                        )
                    )

        # Si semana sin items, seguimos; opcionalmente cacheamos vacío
        if not items_week:
            weekly_summaries.append(
                {
                    "week_start": ws.isoformat(),
                    "week_end": we.isoformat(),
                    "summary": "Semana sin notas registradas.",
                    "from_cache": True,
                }
            )
            continue

        had_any_items = True

        summary_text, meta, from_cache = _load_or_build_week_summary(
            project_id=project_id,
            user_id=user_id,
            scope=scope,
            algo_version=algo_version,
            week_start=ws,
            week_end=we,
            items=items_week,
        )
        if items_week and ("Sin evidencia" in (summary_text or "")):
            summary_text = "HECHOS CLAVE:\n" + "\n".join([f"- [id={it.source_id}] {_truncate(it.text, 220)}" for it in items_week[:10]]) + "\n\nESTADO/TONO GENERAL:\n- Evidencias presentes.\n\nRIESGOS/CAMBIOS:\n- Según notas disponibles."
            meta = {"mode": "fallback", "reason": "llm_week_summary_missing_evidence"}

        if from_cache:
            cache_hits += 1

        weekly_summaries.append(
            {
                "week_start": ws.isoformat(),
                "week_end": we.isoformat(),
                "summary": summary_text,
                "llm": meta,
                "from_cache": from_cache,
            }
        )

    # Contexto global no semanal (Project.description + Task.descripcion + stats)
    project_desc = (getattr(prj, "description", None) or "").strip()

    task_context_lines: List[str] = []
    if scope in ("all", "tasks"):
        for t in tasks_by_id.values():
            if getattr(t, "descripcion", None):
                task_context_lines.append(f"- Tarea {t.id} ({t.estado}): {_truncate(str(t.descripcion), 220)}")

    stats = {}
    try:
        stats = get_project_time_stats(project_id, user_id)
    except Exception:
        stats = {}


    reduce_system = (
        "Eres un analista que responde preguntas sobre un proyecto usando SOLO la información proporcionada.\n"
        "Objetivo: respuesta humana y fluida.\n"
        "Reglas:\n"
        "- No inventes.\n"
        "- Si hay contradicciones, explícitalas.\n"
        "- Si la pregunta menciona evolución/final, describe progresión de forma natural (al principio..., después..., hacia el final...).\n"
        "- NO uses títulos tipo INICIO/MEDIO/FINAL/EVOLUCIÓN ni bullets/listas.\n"
        "- No escribas 'Párrafo 1', 'Párrafo 2', etc. No numeres párrafos.\n"
        "- CITAS OBLIGATORIAS: incluye al menos 2 citas [id=...] en total y al menos 1 párrafo con cita, pegadas a la frase que justifican.\n"
        "- Usa SOLO ids existentes en 'IDs permitidos'. No inventes ids.\n"
        "- Prohibido listar ids sueltos.\n"
        "Formato: 1 a 5 párrafos cortos (separados por una línea en blanco).\n"
    )

    reduce_user_parts: List[str] = []
    reduce_user_parts.append(f"Pregunta: {(query or '').strip()}")
    reduce_user_parts.append("")
    if project_desc:
        reduce_user_parts.append("Descripción del proyecto:")
        reduce_user_parts.append(project_desc)
        reduce_user_parts.append("")

    if task_context_lines:
        reduce_user_parts.append("Contexto de tareas (descripciones):")
        reduce_user_parts.extend(task_context_lines[:80])
        reduce_user_parts.append("")

    if stats:
        reduce_user_parts.append("Stats (estimado vs real / progreso):")
        reduce_user_parts.append(json.dumps(stats, ensure_ascii=False))
        reduce_user_parts.append("")

    # Incluir chart_context solo cuando la pregunta lo requiere (reduce tokens y evita truncado)
    _q = (query or "").lower()
    include_chart_context = any(k in _q for k in (
        "gantt", "árbol", "arbol", "jerarqu", "rama", "depend", "ruta crítica", "ruta critica",
        "desvi", "planific", "estimado vs real", "fecha plan", "timeline", "slippage"
    ))

    if (not had_any_items) and (not project_desc) and (not task_context_lines) and (not include_chart_context):
        msg = "No hay evidencias suficientes para responder a la pregunta."
        return {
            "status": "ok",
            "answer": msg,
            "message": msg,
            "query": (query or "").strip(),
            "scope": scope,
            "date_from": d_from.isoformat() if d_from else None,
            "date_to": d_to.isoformat() if d_to else None,
            "evidences": [],
            "filter": {"mode": "embedding", "reason": "no hay textos para comparar", "relevant": 0, "total": 0},
            "relevant_items": 0,
            "total_items": 0,
        }

    # Contexto de gráficos (Gantt/Árbol): snapshot estructurado (no render)
    chart_allowed_ids = set()
    chart_context = {}
    try:
        def _iso(v):
            try:
                return v.isoformat() if v is not None else None
            except Exception:
                return None

        gantt_tasks = []
        tree_edges = []
        for t in tasks_by_id.values():
            tid = getattr(t, "id", None)
            if tid is None:
                continue
            try:
                chart_allowed_ids.add(int(tid))
            except Exception:
                pass
            parent_id = getattr(t, "parent_task_id", None)
            if parent_id is not None:
                try:
                    tree_edges.append({"parent": int(parent_id), "child": int(tid)})
                except Exception:
                    pass
            titulo = (getattr(t, "titulo", None) or getattr(t, "title", None) or getattr(t, "name", None) or f"Tarea #{tid}")
            gantt_tasks.append({
                "id": int(tid) if str(tid).isdigit() else tid,
                "titulo": str(titulo),
                "estado": getattr(t, "estado", None),
                "parent_task_id": parent_id,
                "fecha_plan_inicio": _iso(getattr(t, "fecha_plan_inicio", None)),
                "fecha_plan_fin": _iso(getattr(t, "fecha_plan_fin", None)),
                "minutos_estimados": getattr(t, "minutos_estimados", None),
            })

        gantt_milestones = []
        try:
            for m in Milestone.query.filter_by(project_id=project_id).all():
                mid = getattr(m, "id", None)
                if mid is not None:
                    try:
                        chart_allowed_ids.add(int(mid))
                    except Exception:
                        pass
                mtxt = (getattr(m, "titulo", None) or getattr(m, "name", None) or getattr(m, "descripcion", None) or "Hito")
                gantt_milestones.append({
                    "id": int(mid) if (mid is not None and str(mid).isdigit()) else mid,
                    "titulo": str(mtxt),
                    "fecha": _iso(getattr(m, "fecha", None)),
                })
        except Exception:
            pass

        chart_context = {
            "semantica": {
                "gantt.tasks": "barras de planificación/ejecución por tarea (fechas plan + estimado)",
                "gantt.milestones": "hitos por fecha",
                "tree.edges": "jerarquía parent->child entre tareas",
            },
            "gantt": {"tasks": gantt_tasks, "milestones": gantt_milestones},
            "tree": {"edges": tree_edges},
        }
    except Exception:
        chart_allowed_ids = set()
        chart_context = {}

    if include_chart_context and chart_context:
        reduce_user_parts.append("Contexto de gráficos (Gantt/Árbol):")
        reduce_user_parts.append(json.dumps(chart_context, ensure_ascii=False))
        reduce_user_parts.append("")

    reduce_user_parts.append("Resúmenes semanales:")
    for w in weekly_summaries:
        reduce_user_parts.append(f"[{w['week_start']}..{w['week_end']}] {w['summary']}")

    # IDs permitidos (extraídos de los resúmenes semanales) para evitar invención en el REDUCE
    allowed_ids = set()
    for w in weekly_summaries:
        for m in re.findall(r'id=(\d+)', (w.get("summary") or "")):
            try:
                allowed_ids.add(int(m))
            except Exception:
                pass
    if include_chart_context:
        allowed_ids.update(chart_allowed_ids)
    allowed_ids_sorted = sorted(allowed_ids)
    # NOTA: no volcamos la lista de IDs al prompt (es muy larga y ralentiza el REDUCE).
    # Los IDs se usan internamente para validar y evitar invenciones.
    val = (os.getenv("QA_INCLUDE_ALLOWED_IDS_IN_PROMPT") or "").strip().lower()
    include_ids_prompt = val not in ("0","false","no")
    if include_ids_prompt and allowed_ids_sorted:
        ids_limit = _as_int(os.getenv("QA_ALLOWED_IDS_PROMPT_LIMIT") or "120", 120)
        joined = ", ".join(str(i) for i in allowed_ids_sorted[:ids_limit])
        if len(allowed_ids_sorted) > ids_limit:
            joined = joined + " (truncado)"
        reduce_user_parts.append("")
        reduce_user_parts.append("IDs permitidos (usa SOLO estos en [id=...]): " + joined)

    reduce_user_parts.append("")
    reduce_user_parts.append("Redacta la respuesta final.")

    final_answer = None

    # reduce_fallback_on_none
    if final_answer is None:
        try:
            ev = []
            for w in (weekly_summaries or []):
                s = str((w or {}).get("summary", "") or "")
                for ln in s.splitlines():
                    ln = (ln or "").strip()
                    if ln.startswith("- [id="):
                        ev.append(ln[2:].strip())
            if ev:
                first = ev[0]
                cite = first.split("]")[0] + "]" if "]" in first else ""
                final_answer = "Según las notas registradas, " + first
                if cite:
                    final_answer = final_answer + " " + cite
                try:
                    final_llm_meta = final_llm_meta or {}
                    final_llm_meta["reduce_warning"] = final_llm_meta.get("reduce_warning") or "reduce_fallback_none"
                except Exception:
                    pass
            else:
                final_answer = "No hay evidencias suficientes para responder a la pregunta."
        except Exception:
            pass


    if progress_cb:
        progress_cb({"stage": "reduce", "done": total_weeks, "total": total_weeks + 1})

    final_answer, final_llm_meta = _ollama_chat(
        messages=[
            {"role": "system", "content": reduce_system},
            {"role": "user", "content": "\n".join(reduce_user_parts)},
        ]
    )

    def _reduce_answer_valid(ans: str, allowed_ids: set[int]) -> bool:
        if not ans or not str(ans).strip():
            return False

        # No permitir formato esquematizado
        import re as _re
        if _re.search(r'^\s*(INICIO|MEDIO|FINAL|EVOLUCI\u00d3N)\s*:', ans, flags=_re.M):
            return False
        if _re.search(r'^\s*-\s', ans, flags=_re.M):
            return False

        paras = [pp for pp in _re.split(r'\n\s*\n', ans.strip()) if pp.strip()]
        if len(paras) < 2 or len(paras) > 5:
            return False

        used = [int(x) for x in _re.findall(r'id=(\d+)', ans)]
        if len(used) < 2:
            return False
        if allowed_ids and any(x not in allowed_ids for x in used):
            return False

        # Citas: exigimos al menos 2 citas en total, pero no forzamos 1 por párrafo
        cited_paras = 0
        for ptxt in paras:
            if "[id=" in ptxt or "(id=" in ptxt:
                cited_paras += 1
                pos = ptxt.find("[id=")
                if pos < 0:
                    pos = ptxt.find("(id=")
                if pos < 15:
                    return False

        if len(used) < 2:
            return False
        if cited_paras < 1:
            return False

        return True

    if final_answer is not None and not _reduce_answer_valid(final_answer, allowed_ids):
        retry_user = (
            "Tu respuesta anterior es INVÁLIDA.\n"
            "REESCRIBE: 1 a 5 párrafos cortos, sin títulos fijos y sin bullets.\n"
            "Incluye al menos 2 citas [id=...] en total y al menos 1 párrafo con cita, pegadas a la frase correspondiente.\n"
            "No inventes ids: usa SOLO los de 'IDs permitidos'.\n"
            "No listes ids.\n\n"
            + "\n".join(reduce_user_parts)
        )
        final_answer2, final_llm_meta2 = _ollama_chat(
            messages=[
                {"role": "system", "content": reduce_system},
                {"role": "user", "content": retry_user},
            ]
        )
        if final_answer2 is not None:
            final_answer = final_answer2
            if final_llm_meta2:
                final_llm_meta = final_llm_meta2

        if final_answer is not None and not _reduce_answer_valid(final_answer, allowed_ids):
            repair_user = (
                "Tu respuesta sigue siendo INVÁLIDA. DEVUELVE SOLO la respuesta final corregida.\n"
                "Reglas obligatorias:\n"
                "- 1 a 5 párrafos cortos (separados por una línea en blanco).\n"
                "- Sin títulos fijos (INICIO/MEDIO/FINAL/EVOLUCIÓN) y sin bullets.\n"
                "- Incluye al menos 2 citas [id=...] en total y al menos 1 párrafo con cita.\n"
                "- Antes de la primera cita, escribe al menos 15 caracteres de texto.\n"
                "- Usa SOLO IDs permitidos. No listes ids sueltos.\n\n"
                "\n"
                + "\n".join(reduce_user_parts)
            )
            final_answer3, final_llm_meta3 = _ollama_chat(
                messages=[
                    {"role": "system", "content": reduce_system},
                    {"role": "user", "content": repair_user},
                ]
            )
            if final_answer3 is not None:
                final_answer = final_answer3
                if final_llm_meta3:
                    final_llm_meta = final_llm_meta3

        if final_answer is not None and not _reduce_answer_valid(final_answer, allowed_ids):
            try:
                final_llm_meta = final_llm_meta or {}
                final_llm_meta["reduce_warning"] = "reduce_answer_invalid_after_retry"
            except Exception:
                pass
    # Si tras los reintentos sigue inválida, devolvemos fallback basado en evidencias disponibles (no error).
    if final_answer is not None and not _reduce_answer_valid(final_answer, allowed_ids):
        try:
            ev = []
            for w in (weekly_summaries or []):
                s = str((w or {}).get("summary", "") or "")
                for ln in s.splitlines():
                    ln = (ln or "").strip()
                    if ln.startswith("- [id="):
                        ev.append(ln[2:].strip())
            if ev:
                first = ev[0]
                cite = first.split("]")[0] + "]" if "]" in first else ""
                final_answer = "Según las notas registradas, " + first
                if cite:
                    final_answer = final_answer + " " + cite
            else:
                final_answer = "No hay evidencias suficientes para responder a la pregunta."
            try:
                final_llm_meta = final_llm_meta or {}
                final_llm_meta["reduce_warning"] = final_llm_meta.get("reduce_warning") or "reduce_fallback"
            except Exception:
                pass
        except Exception:
            final_answer = "No hay evidencias suficientes para responder a la pregunta."


    if progress_cb:
        # Reduce completado (paso extra respecto a semanas)
        progress_cb({"stage": "reduce", "done": total_weeks + 1, "total": total_weeks + 1})

    if final_answer is None:





        return {
            "query": query,
            "scope": scope,
            "date_from": d_from.isoformat() if d_from else None,
            "date_to": d_to.isoformat() if d_to else None,
            "status": "llm_error",
            "message": "No se pudo generar respuesta (error en LLM).",
            "llm": final_llm_meta,
            "weeks": len(weeks),
            "cache_hits": cache_hits,
            "weekly_summaries": weekly_summaries,
        }

    def _extract_session_name(raw: str) -> str:
        raw = (raw or "").strip()
        if not raw:
            return ""
        # 1) campo directo si existiera (no lo sabemos, pero no rompe)
        return ""

    def _try_parse_session_name_from_notas(notas: str) -> str:
        notas = (notas or "").strip()
        if not notas:
            return ""
        if not notas.startswith("{"):
            return ""
        try:
            obj = json.loads(notas)
        except Exception:
            return ""
        if not isinstance(obj, dict):
            return ""
        for key in ("name", "nombre", "title", "titulo", "sessionName", "session_name", "session"):
            v = obj.get(key)
            if isinstance(v, str) and v.strip():
                return v.strip()
        return ""

    def _render_answer_refs(ans: str) -> str:
        if not ans:
            return ans

        def resolve_one(id_int: int) -> str:
            # Preferir sesión (si pertenece al proyecto)
            srec = WorkSession.query.filter_by(id=id_int).first()
            if srec is not None:
                tid = getattr(srec, "tarea_id", None)
                if tid in tasks_by_id:
                    t = tasks_by_id[tid]
                    ttitle = (getattr(t, "titulo", None) or getattr(t, "title", None) or getattr(t, "name", None) or f"Tarea #{tid}")
                    sname = (getattr(srec, "nombre", None) or getattr(srec, "name", None) or _try_parse_session_name_from_notas(getattr(srec, "notas", "") or ""))
                    parts = [f'Tarea: "{str(ttitle).strip()}"']
                    if sname:
                        parts.append(f'Sesión: "{str(sname).strip()}"')
                    return "(" + "; ".join(parts) + ")"

            mrec = Milestone.query.filter_by(id=id_int, project_id=project_id).first()
            if mrec is not None:
                mtxt = (getattr(mrec, "titulo", None) or getattr(mrec, "name", None) or getattr(mrec, "descripcion", None) or "Hito")
                mdate = getattr(mrec, "fecha", None)
                parts = [f'Hito: "{str(mtxt).strip()}"']
                if mdate:
                    try:
                        parts.append(f"fecha={mdate.isoformat()}")
                    except Exception:
                        pass
                return "(" + "; ".join(parts) + ")"

            return "(Referencia no encontrada)"

        def repl(m):
            ids = [int(x) for x in re.findall(r'id=(\d+)', m.group(0))]
            refs = [resolve_one(i) for i in ids]
            # Ocultar id=... cuando ya hay referencia humana (Tarea/Hito/Sesión)
            cleaned = []
            for r in refs:
                rr = r
                if ('Tarea:' in rr) or ('Hito:' in rr) or ('Sesión:' in rr):
                    rr = re.sub(r';\s*id=\d+\s*\)', ')', rr)
                    rr = re.sub(r'\s*;\s*id=\d+\s*$', '', rr)
                cleaned.append(rr)
            refs = cleaned
            if len(refs) == 1:
                return refs[0]
            # Combinar varias refs en un solo paréntesis
            inner = " | ".join(r.strip("()") for r in refs)
            return "(" + inner + ")"

        ans2 = re.sub(r'\[id=\d+(?:,\s*id=\d+)*\]', repl, ans)
        ans2 = re.sub(r'\(id=\d+\)', repl, ans2)
        return ans2


    # Post-procesado: convertir [id=..] a referencias humanas (tarea/sesión/hito)
    final_answer = _render_answer_refs(final_answer)
    # Limpieza final: eliminar fragmentos incompletos de citas
    final_answer = re.sub(r'\[id[^\]]*$', '', final_answer).rstrip()
    final_answer = re.sub(r'\(id[^\)]*$', '', final_answer).rstrip()

    return {
        "query": query,
        "scope": scope,
        "date_from": d_from.isoformat() if d_from else None,
        "date_to": d_to.isoformat() if d_to else None,
        "status": "ok",
        "llm": final_llm_meta,
        "weeks": len(weeks),
        "cache_hits": cache_hits,
        "weekly_summaries": weekly_summaries,
        "answer": final_answer,
    }
