# app/services/sentiment_service.py

from __future__ import annotations

import json
import math
import os
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

import requests

from app.models import Project, Task, WorkSession, Milestone


@dataclass
class CommentItem:
    source: str          # "project" | "task" | "session" | "milestone"
    source_id: int
    text: str
    created_date: Optional[date]
    task_id: Optional[int] = None
    # Para soporte pre/post sesión
    pre_text: Optional[str] = None
    post_text: Optional[str] = None


def _parse_date_yyyy_mm_dd(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None


def _norm_text(s: str) -> str:
    return (s or "").strip().lower()


def re_split_non_alnum(s: str) -> List[str]:
    return [x for x in re.split(r"[^a-z0-9áéíóúñü]+", s.lower()) if x]


def _extract_session_pre_post(notas_raw: Optional[str]) -> Tuple[str, str]:
    """
    Devuelve (pre_objectives, post_notes)
    - Si notas es JSON con objectives/notes: devuelve esos campos.
    - Si es texto plano: asumimos que es post_notes (pre vacío).
    """
    if not notas_raw:
        return "", ""

    raw = notas_raw.strip()
    if not raw:
        return "", ""

    if raw.startswith("{") and raw.endswith("}"):
        try:
            obj = json.loads(raw)
            if isinstance(obj, dict):
                pre = str(obj.get("objectives") or "").strip()
                post = str(obj.get("notes") or "").strip()
                return pre, post
        except Exception:
            pass

    return "", raw


def collect_project_comments(
    project_id: int,
    user_id: int,
    scope: str = "all",  # "all" | "project" | "tasks" | "sessions" | "milestones"
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> List[CommentItem]:
    project = Project.query.filter_by(id=project_id, user_id=user_id).first()
    if not project:
        raise ValueError("Proyecto no encontrado o sin permisos.")

    d_from = _parse_date_yyyy_mm_dd(date_from)
    d_to = _parse_date_yyyy_mm_dd(date_to)

    items: List[CommentItem] = []

    if scope in ("all", "project"):
        if getattr(project, "description", None):
            items.append(
                CommentItem(
                    source="project",
                    source_id=project.id,
                    text=str(project.description),
                    created_date=getattr(project, "created_at", None),
                )
            )

    tasks_q = Task.query.filter_by(project_id=project_id, user_id=user_id)
    tasks: List[Task] = tasks_q.all()

    if scope in ("all", "tasks"):
        for t in tasks:
            if getattr(t, "descripcion", None):
                created = getattr(t, "created_at", None)
                items.append(
                    CommentItem(
                        source="task",
                        source_id=t.id,
                        text=str(t.descripcion),
                        created_date=created,
                        task_id=t.id,
                    )
                )

    if scope in ("all", "sessions"):
        task_ids = [t.id for t in tasks]
        if task_ids:
            sess_q = WorkSession.query.filter(WorkSession.tarea_id.in_(task_ids))
            if d_from:
                sess_q = sess_q.filter(WorkSession.fecha >= d_from)
            if d_to:
                sess_q = sess_q.filter(WorkSession.fecha <= d_to)

            for s in sess_q.all():
                pre, post = _extract_session_pre_post(getattr(s, "notas", None))
                combined = " ".join([x for x in [pre, post] if x]).strip()
                if combined:
                    items.append(
                        CommentItem(
                            source="session",
                            source_id=s.id,
                            text=combined,
                            created_date=getattr(s, "fecha", None),
                            task_id=getattr(s, "tarea_id", None),
                            pre_text=pre,
                            post_text=post,
                        )
                    )

    if scope in ("all", "milestones"):
        ms_q = Milestone.query.filter_by(project_id=project_id)
        if d_from:
            ms_q = ms_q.filter(Milestone.fecha >= d_from)
        if d_to:
            ms_q = ms_q.filter(Milestone.fecha <= d_to)

        for m in ms_q.all():
            if getattr(m, "descripcion", None):
                items.append(
                    CommentItem(
                        source="milestone",
                        source_id=m.id,
                        text=str(m.descripcion),
                        created_date=getattr(m, "fecha", None),
                    )
                )

    if d_from or d_to:
        filtered: List[CommentItem] = []
        for it in items:
            if not it.created_date:
                filtered.append(it)
                continue
            if d_from and it.created_date < d_from:
                continue
            if d_to and it.created_date > d_to:
                continue
            filtered.append(it)
        items = filtered

    return items


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    denom = math.sqrt(na) * math.sqrt(nb)
    if denom <= 0.0:
        return 0.0
    return float(dot / denom)


def _ollama_embed_texts(texts: List[str]) -> Tuple[Optional[List[List[float]]], Dict[str, Any]]:
    """
    Llama a Ollama /api/embed (batch) y devuelve (embeddings, meta).
    Si falla, devuelve (None, meta con error).
    """
    base_url = (os.getenv("OLLAMA_BASE_URL") or "").strip()
    model = (os.getenv("OLLAMA_EMBED_MODEL") or "").strip()
    timeout_s = float(os.getenv("SENTIMENT_EMBED_TIMEOUT_SECS") or "10")

    if not base_url or not model:
        return None, {
            "provider": "ollama",
            "mode": "disabled",
            "reason": "OLLAMA_BASE_URL u OLLAMA_EMBED_MODEL no configurados",
        }

    url = base_url.rstrip("/") + "/api/embed"
    payload: Dict[str, Any] = {"model": model, "input": texts, "truncate": True}

    try:
        r = requests.post(url, json=payload, timeout=timeout_s)
        if r.status_code != 200:
            return None, {
                "provider": "ollama",
                "mode": "error",
                "http_status": r.status_code,
                "body": (r.text[:500] if r.text else ""),
            }
        data = r.json()
        embs = data.get("embeddings")
        if not isinstance(embs, list) or not embs:
            return None, {"provider": "ollama", "mode": "error", "reason": "Respuesta sin embeddings"}
        return embs, {
            "provider": "ollama",
            "mode": "ok",
            "endpoint": "/api/embed",
            "model": data.get("model") or model,
            "prompt_eval_count": data.get("prompt_eval_count"),
            "total_duration": data.get("total_duration"),
            "load_duration": data.get("load_duration"),
        }
    except Exception as e:
        return None, {"provider": "ollama", "mode": "error", "reason": str(e)}


def _vllm_embed_texts(texts: List[str]) -> Tuple[Optional[List[List[float]]], Dict[str, Any]]:
    """
    Llama a vLLM (OpenAI-compatible) /v1/embeddings y devuelve (embeddings, meta).
    Si falla, devuelve (None, meta con error).
    """
    base_url = (os.getenv("VLLM_BASE_URL") or "").strip()
    model = (os.getenv("VLLM_EMBED_MODEL") or os.getenv("VLLM_MODEL") or "").strip()
    timeout_s = float(os.getenv("SENTIMENT_EMBED_TIMEOUT_SECS") or "10")

    if not base_url or not model:
        return None, {
            "provider": "vllm",
            "mode": "disabled",
            "reason": "VLLM_BASE_URL o VLLM_EMBED_MODEL/VLLM_MODEL no configurados",
        }

    url = base_url.rstrip("/") + "/v1/embeddings"
    payload: Dict[str, Any] = {"model": model, "input": texts}

    try:
        r = requests.post(url, json=payload, timeout=timeout_s)
        if r.status_code != 200:
            return None, {
                "provider": "vllm",
                "mode": "error",
                "http_status": r.status_code,
                "body": (r.text[:500] if r.text else ""),
            }
        data = r.json()
        data_list = data.get("data")
        if not isinstance(data_list, list) or not data_list:
            return None, {"provider": "vllm", "mode": "error", "reason": "Respuesta sin data"}
        embs: List[List[float]] = []
        for it in data_list:
            vec = it.get("embedding") if isinstance(it, dict) else None
            if not isinstance(vec, list) or not vec:
                return None, {"provider": "vllm", "mode": "error", "reason": "Elemento sin embedding"}
            embs.append(vec)
        if len(embs) != len(texts):
            return None, {"provider": "vllm", "mode": "error", "reason": "len(embeddings) != len(texts)"}
        return embs, {
            "provider": "vllm",
            "mode": "ok",
            "endpoint": "/v1/embeddings",
            "model": model,
            "usage": data.get("usage"),
        }
    except Exception as e:
        return None, {"provider": "vllm", "mode": "error", "reason": str(e)}


def _filter_relevant_comments_keyword(items: List[CommentItem], query: str) -> Tuple[List[CommentItem], Dict[str, Any]]:
    q = _norm_text(query)
    if not q:
        return items, {"mode": "all", "reason": "query vacía -> todo relevante"}

    tokens = [t for t in re_split_non_alnum(q) if len(t) >= 3]
    if not tokens:
        return items, {"mode": "all", "reason": "query sin tokens útiles -> todo relevante"}

    relevant: List[CommentItem] = []
    for it in items:
        txt = _norm_text(it.text)
        if any(tok in txt for tok in tokens):
            relevant.append(it)

    meta = {"mode": "keyword_contains", "tokens": tokens, "total": len(items), "relevant": len(relevant)}
    return relevant, meta


def filter_relevant_comments(items: List[CommentItem], query: str, prefilter_top_n: Optional[int] = None) -> Tuple[List[CommentItem], Dict[str, Any]]:
    """
    Filtro semántico por embeddings (Ollama) con fallback keyword.
    - Si query vacía: todo relevante (como antes)
    - Si Ollama no está configurado o falla: fallback keyword (como antes)
    """
    q = _norm_text(query)
    if not q:
        return items, {"mode": "all", "reason": "query vacía -> todo relevante"}

    top_k = int(os.getenv("SENTIMENT_EMBED_TOP_K") or "40")
    min_sim = float(os.getenv("SENTIMENT_EMBED_MIN_SIM") or "0.35")
    min_sim_no_kw = float(os.getenv("SENTIMENT_EMBED_MIN_SIM_NO_KW") or "0.55")

    orig_index = {id(it): idx for idx, it in enumerate(items)}

    # Prefiltro barato para no embeddar cientos de textos en cada request.
    # Por defecto, limitamos candidatos para embeddings.
    if prefilter_top_n is None:
        prefilter_top_n = int(os.getenv("SENTIMENT_PREFILTER_TOP_N") or "60")

    candidates = items
    prefilter_meta: Dict[str, Any] = {"enabled": False}
    if prefilter_top_n is not None and prefilter_top_n > 0:
        kw_items, kw_meta = _filter_relevant_comments_keyword(items, query)
        if not kw_items:
            min_sim = max(min_sim, min_sim_no_kw)
        # Si keyword encuentra algo, recortamos a top N por orden original.
        if kw_items:
            candidates = kw_items[:prefilter_top_n]
            prefilter_meta = {"enabled": True, "mode": "keyword_prefilter", "top_n": prefilter_top_n, "kw": kw_meta}
        else:
            # Si keyword no encuentra nada, aún recortamos para evitar batch enorme.
            candidates = items[:prefilter_top_n]
            prefilter_meta = {"enabled": True, "mode": "truncate_prefilter", "top_n": prefilter_top_n, "kw": kw_meta}

    texts: List[str] = [q]
    idx_map: List[int] = []

    for i, it in enumerate(candidates):
        t = (it.text or "").strip()
        if not t:
            continue
        texts.append(t)
        idx_map.append(orig_index.get(id(it), i))

    if len(texts) <= 1:
        return [], {"mode": "embedding", "reason": "no hay textos para comparar", "total": len(items), "relevant": 0}

    provider = (os.getenv("SENTIMENT_EMBED_PROVIDER") or "ollama").strip().lower()
    if provider in {"ollama"}:
        embs, emb_meta = _ollama_embed_texts(texts)
    elif provider in {"vllm", "openai", "openai-compatible"}:
        embs, emb_meta = _vllm_embed_texts(texts)
    else:
        embs, emb_meta = None, {"provider": provider or "unknown", "mode": "disabled", "reason": "Proveedor no soportado"}
    if embs is None:
        relevant_kw, meta_kw = _filter_relevant_comments_keyword(items, query)
        meta_kw["fallback_from"] = "embedding"
        meta_kw["embedding"] = emb_meta
        return relevant_kw, meta_kw

    if not isinstance(embs, list) or len(embs) != len(texts):
        relevant_kw, meta_kw = _filter_relevant_comments_keyword(items, query)
        meta_kw["fallback_from"] = "embedding"
        meta_kw["embedding"] = {"provider": "ollama", "mode": "error", "reason": "len(embeddings) != len(texts)"}
        return relevant_kw, meta_kw

    q_vec = embs[0]
    scored: List[Tuple[float, int]] = []

    for pos, item_idx in enumerate(idx_map, start=1):
        sim = _cosine_similarity(q_vec, embs[pos])
        scored.append((sim, item_idx))

    scored.sort(key=lambda x: x[0], reverse=True)

    picked: List[CommentItem] = []
    picked_sims: List[float] = []

    for sim, item_idx in scored[: max(top_k, 1)]:
        if sim < min_sim:
            continue
        picked.append(items[item_idx])
        picked_sims.append(sim)

    meta = {
        "mode": "embedding_cosine_topk",
        "prefilter": prefilter_meta,
        "candidates": len(candidates),
        "query": query,
        "total": len(items),
        "relevant": len(picked),
        "top_k": top_k,
        "min_sim": min_sim,
        "avg_sim": (sum(picked_sims) / len(picked_sims)) if picked_sims else 0.0,
        "max_sim": max(picked_sims) if picked_sims else 0.0,
        "min_sim_observed": min(picked_sims) if picked_sims else 0.0,
        "embedding": emb_meta,
    }

    return picked, meta


_POS_WORDS = {
    "bien", "genial", "perfecto", "contento", "contenta", "satisfecho", "satisfecha",
    "mejor", "mejora", "rápido", "rapido", "eficiente", "gracias", "cómodo", "comodo",
    "fácil", "facil", "fluido", "ok", "excelente", "positivo", "motivación", "motivacion", "motivado"
}

_NEG_WORDS = {
    "mal", "fatal", "horrible", "lento", "estres", "estrés", "agobio", "agobiado", "agobiada",
    "bloqueo", "problema", "problemas", "queja", "quejas", "difícil", "dificil",
    "frustración", "frustracion", "frustrado", "frustrada", "negativo", "cansado", "cansada",
    "molesto", "molesta", "enfado", "enfadado", "enfadada", "tenso", "tensa"
}

_NEGATIONS = {"no", "nunca", "jamás", "jamas", "sin"}


def analyze_sentiment_rule_based(text: str) -> Tuple[str, float]:
    txt = _norm_text(text)
    if not txt:
        return "neutral", 0.0

    words = re_split_non_alnum(txt)
    pos = 0
    neg = 0

    for i, w in enumerate(words):
        prev = words[i - 1] if i - 1 >= 0 else ""
        prev2 = words[i - 2] if i - 2 >= 0 else ""
        negated = (prev in _NEGATIONS) or (prev2 in _NEGATIONS)

        if w in _POS_WORDS:
            if negated:
                neg += 1
            else:
                pos += 1
        elif w in _NEG_WORDS:
            if negated:
                pos += 1
            else:
                neg += 1

    total = pos + neg
    if total == 0:
        return "neutral", 0.0

    raw = (pos - neg) / max(total, 1)
    if raw >= 0.2:
        return "positive", float(max(-1.0, min(1.0, raw)))
    if raw <= -0.2:
        return "negative", float(max(-1.0, min(1.0, raw)))
    return "neutral", float(max(-1.0, min(1.0, raw)))


def _build_summary_text(dist: Dict[str, int], majority: str) -> str:
    total = sum(dist.values()) or 1
    maj_map = {"positive": "positivo", "neutral": "neutral", "negative": "negativo"}
    maj_es = maj_map.get(majority, majority)
    return (
        f"Resumen: tono mayoritariamente {maj_es}. "
        f"Positivos: {dist.get('positive', 0)}/{total}, "
        f"neutrales: {dist.get('neutral', 0)}/{total}, "
        f"negativos: {dist.get('negative', 0)}/{total}."
    )


def analyze_project_sentiment(
    project_id: int,
    user_id: int,
    query: str,
    scope: str = "all",
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    min_required: int = 1,
    mode: str = "general",  # "general" | "pre_post"
) -> Dict[str, Any]:
    all_items = collect_project_comments(
        project_id=project_id,
        user_id=user_id,
        scope=scope,
        date_from=date_from,
        date_to=date_to,
    )

    relevant_items, filter_meta = filter_relevant_comments(all_items, query)

    if len(relevant_items) < min_required:
        return {
            "query": query,
            "scope": scope,
            "date_from": date_from,
            "date_to": date_to,
            "total_items": len(all_items),
            "relevant_items": len(relevant_items),
            "filter": filter_meta,
            "mode": mode,
            "status": "no_data",
            "message": "No hay suficientes comentarios relacionados con la consulta para generar un análisis.",
            "distribution": {"positive": 0, "neutral": 0, "negative": 0},
            "items": [],
        }

    if mode == "pre_post":
        return _analyze_pre_post(relevant_items, query, scope, date_from, date_to, filter_meta, all_items)

    dist = {"positive": 0, "neutral": 0, "negative": 0}
    scored: List[Dict[str, Any]] = []

    for it in relevant_items:
        label, score = analyze_sentiment_rule_based(it.text)
        dist[label] += 1
        scored.append(
            {
                "source": it.source,
                "source_id": it.source_id,
                "task_id": it.task_id,
                "date": it.created_date.isoformat() if it.created_date else None,
                "sentiment": label,
                "score": score,
                "text": it.text,
            }
        )

    majority = max(dist.keys(), key=lambda k: dist[k])
    examples = _pick_examples(scored, majority)
    summary = _build_summary_text(dist, majority)

    return {
        "query": query,
        "scope": scope,
        "date_from": date_from,
        "date_to": date_to,
        "total_items": len(all_items),
        "relevant_items": len(relevant_items),
        "filter": filter_meta,
        "mode": mode,
        "status": "ok",
        "majority": majority,
        "distribution": dist,
        "summary": summary,
        "examples": examples,
        "items": scored,
    }


def _pick_examples(scored: List[Dict[str, Any]], majority: str) -> List[Dict[str, Any]]:
    examples: List[Dict[str, Any]] = []
    for target in (majority, "negative", "positive", "neutral"):
        for s in scored:
            if s["sentiment"] == target:
                examples.append(
                    {
                        "sentiment": s["sentiment"],
                        "score": s["score"],
                        "text": (s["text"][:220] + "…") if len(s["text"]) > 220 else s["text"],
                        "source": s["source"],
                        "source_id": s["source_id"],
                        "date": s["date"],
                    }
                )
            if len(examples) >= 5:
                break
        if len(examples) >= 5:
            break
    return examples


def _analyze_pre_post(
    relevant_items: List[CommentItem],
    query: str,
    scope: str,
    date_from: Optional[str],
    date_to: Optional[str],
    filter_meta: Dict[str, Any],
    all_items: List[CommentItem],
) -> Dict[str, Any]:
    # Solo tiene sentido para sesiones; si el scope no incluye sesiones, aún intentamos con lo que haya.
    pre_dist = {"positive": 0, "neutral": 0, "negative": 0}
    post_dist = {"positive": 0, "neutral": 0, "negative": 0}
    pairs: List[Dict[str, Any]] = []

    used = 0
    for it in relevant_items:
        pre = (it.pre_text or "").strip()
        post = (it.post_text or "").strip()

        # Si no es una sesión (sin pre/post), lo tratamos como post
        if not pre and not post:
            post = it.text

        pre_label, pre_score = analyze_sentiment_rule_based(pre) if pre else ("neutral", 0.0)
        post_label, post_score = analyze_sentiment_rule_based(post) if post else ("neutral", 0.0)

        pre_dist[pre_label] += 1
        post_dist[post_label] += 1
        used += 1

        pairs.append(
            {
                "source": it.source,
                "source_id": it.source_id,
                "task_id": it.task_id,
                "date": it.created_date.isoformat() if it.created_date else None,
                "pre": {"text": pre, "sentiment": pre_label, "score": pre_score},
                "post": {"text": post, "sentiment": post_label, "score": post_score},
                "delta": float(post_score - pre_score),
            }
        )

    # delta summary simple
    avg_delta = sum(p["delta"] for p in pairs) / max(used, 1)
    if avg_delta > 0.10:
        delta_summary = "En promedio, el tono mejora del pre al post."
    elif avg_delta < -0.10:
        delta_summary = "En promedio, el tono empeora del pre al post."
    else:
        delta_summary = "En promedio, el tono se mantiene estable del pre al post."

    return {
        "query": query,
        "scope": scope,
        "date_from": date_from,
        "date_to": date_to,
        "total_items": len(all_items),
        "relevant_items": len(relevant_items),
        "filter": filter_meta,
        "mode": "pre_post",
        "status": "ok",
        "pre_distribution": pre_dist,
        "post_distribution": post_dist,
        "avg_delta": avg_delta,
        "delta_summary": delta_summary,
        "pairs": pairs,
    }
