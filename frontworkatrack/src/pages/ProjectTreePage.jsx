import { useEffect, useMemo, useRef, useState, useLayoutEffect } from 'react';
import { Link, useParams } from 'react-router-dom';
import { apiFetch } from '../api/client';

function safeJsonParse(str) {
try {
return JSON.parse(str);
} catch {
return null;
}
}

function decodeNotas(notasRaw) {
if (!notasRaw) {
return { objectives: '', notes: '', startedAt: null, endedAt: null };
}

const parsed = safeJsonParse(notasRaw);

if (!parsed || typeof parsed !== 'object') {
return { objectives: notasRaw, notes: '', startedAt: null, endedAt: null };
}

return {
objectives: parsed.objectives || '',
notes: parsed.notes || '',
startedAt: parsed.startedAt || null,
endedAt: parsed.endedAt || null,
};
}

function formatMinutes(totalMinutes) {
const m = Number(totalMinutes) || 0;
if (m <= 0) return '0min';
const h = Math.floor(m / 60);
const mm = m % 60;
if (h > 0 && mm > 0) return `${h}h ${mm}min`;
if (h > 0) return `${h}h`;
return `${mm}min`;
}

function clamp(n, min, max) {
return Math.max(min, Math.min(max, n));
}

function round2(n) {
return Math.round((Number(n) || 0) * 100) / 100;
}

function ProjectTreePage() {
const { projectId } = useParams();

const [project, setProject] = useState(null);
const [tasks, setTasks] = useState([]);
const [sessionsRaw, setSessionsRaw] = useState([]);

const [loading, setLoading] = useState(false);
const [loadError, setLoadError] = useState('');

const [expandedTasks, setExpandedTasks] = useState({}); // taskId -> bool
const [expandedSessions, setExpandedSessions] = useState({}); // taskId -> bool

// Vista / modos
const [isZoomMode, setIsZoomMode] = useState(false); // "lupa"
const [fitScale, setFitScale] = useState(1); // auto-fit (modo default)
const [zoomScale, setZoomScale] = useState(1); // manual (modo lupa)
const [focusTaskId, setFocusTaskId] = useState(null); // si no es null, ese nodo es la raíz

// Refs de medida y scroll
const treeViewportRef = useRef(null);
const treeStageRef = useRef(null);

const projectName = project?.nombre || project?.name || `Proyecto #${projectId}`;
const projectColor = project?.color || '#2563eb';

useEffect(() => {
let cancelled = false;

async function loadAll() {
  setLoading(true);
  setLoadError('');

  try {
    const [p, allTasks, allSessions] = await Promise.all([
      apiFetch(`/projects/${projectId}`),
      apiFetch('/me/tasks/with-time'),
      apiFetch('/me/sessions'),
    ]);

    if (cancelled) return;

    setProject(p || null);

    const filteredTasks = Array.isArray(allTasks)
      ? allTasks.filter((t) => Number(t.project_id) === Number(projectId))
      : [];

    setTasks(filteredTasks);
    setSessionsRaw(Array.isArray(allSessions) ? allSessions : []);
  } catch (err) {
    if (cancelled) return;
    console.error('Error cargando árbol del proyecto:', err);
    setLoadError(err?.message || 'Error cargando datos del proyecto');
    setProject(null);
    setTasks([]);
    setSessionsRaw([]);
  } finally {
    if (!cancelled) setLoading(false);
  }
}

loadAll();

return () => {
  cancelled = true;
};


}, [projectId]);

const tasksById = useMemo(() => {
const map = {};
tasks.forEach((t) => {
map[String(t.id)] = t;
});
return map;
}, [tasks]);

const childrenMap = useMemo(() => {
const map = {};
tasks.forEach((t) => {
const key =
t.parent_task_id !== null &&
t.parent_task_id !== undefined &&
Number(t.parent_task_id) !== 0
? String(t.parent_task_id)
: 'root';

  if (!map[key]) map[key] = [];
  map[key].push(t);
});
return map;


}, [tasks]);

const rootTasks = useMemo(() => childrenMap.root || [], [childrenMap]);

const sessionsByTask = useMemo(() => {
const map = {};
sessionsRaw.forEach((s) => {
const tid = String(s.tarea_id);
if (!map[tid]) map[tid] = [];

  const meta = decodeNotas(s.notas);

  map[tid].push({
    id: s.id,
    plannedDate: s.fecha || null,
    title: s.tipo || '',
    minutes: Number(s.minutos) || 0,
    startedAt: meta.startedAt,
    endedAt: meta.endedAt,
    objectives: meta.objectives || '',
    notes: meta.notes || '',
  });
});

Object.keys(map).forEach((k) => {
  map[k].sort((a, b) => {
    const da = a.plannedDate || '';
    const db = b.plannedDate || '';
    if (da < db) return 1;
    if (da > db) return -1;
    return 0;
  });
});

return map;


}, [sessionsRaw]);

function getRootTask(task) {
let cur = task;
let guard = 0;

while (
  cur &&
  cur.parent_task_id !== null &&
  cur.parent_task_id !== undefined &&
  String(cur.parent_task_id) !== '' &&
  Number(cur.parent_task_id) !== 0 &&
  guard < 50
) {
  const parent = tasksById[String(cur.parent_task_id)];
  if (!parent) break;
  cur = parent;
  guard += 1;
}

return cur || task;


}

function getBranchColor(task) {
const isFinalized = String(task?.estado || '').toLowerCase() === 'finalizada';
if (isFinalized) return '#9ca3af';
const root = getRootTask(task);
return root?.color || projectColor;
}

const toggleTask = (taskId) => {
setExpandedTasks((prev) => ({ ...prev, [taskId]: !prev[taskId] }));
};

const toggleTaskSessions = (taskId) => {
setExpandedSessions((prev) => ({ ...prev, [taskId]: !prev[taskId] }));
};

const enterZoomMode = () => {
setIsZoomMode(true);
setZoomScale((prev) => {
const base = typeof prev === 'number' ? prev : 1;
const next = fitScale || base || 1;
return clamp(round2(next), 0.2, 2.5);
});

requestAnimationFrame(() => {
  requestAnimationFrame(() => {
    const viewport = treeViewportRef.current;
    if (!viewport) return;
    const stage = treeStageRef.current;
    const rootNode = stage ? stage.querySelector('.wt-tree-node') : null;
    if (!rootNode) {
      viewport.scrollLeft = 0;
      viewport.scrollTop = 0;
      return;
    }
    const vpRect = viewport.getBoundingClientRect();
    const nodeRect = rootNode.getBoundingClientRect();
    const delta = (nodeRect.left + nodeRect.right) / 2 - (vpRect.left + vpRect.right) / 2;
    viewport.scrollLeft = Math.max(0, viewport.scrollLeft + delta);
    viewport.scrollTop = 0;
  });
});

};

const exitZoomMode = () => {
setIsZoomMode(false);
};

const focusOnTask = (taskIdStr) => {
setFocusTaskId(taskIdStr);
setIsZoomMode(false);
setExpandedTasks((prev) => ({ ...prev, [taskIdStr]: true }));
};

const clearFocus = () => {
setFocusTaskId(null);
setIsZoomMode(false);
};

// Expandir por defecto las tareas raíz (solo cuando estamos en el árbol completo)
useEffect(() => {
if (focusTaskId) return;
if (!rootTasks || rootTasks.length === 0) return;

setExpandedTasks((prev) => {
  const next = { ...prev };
  rootTasks.forEach((t) => {
    const id = String(t.id);
    if (next[id] === undefined) next[id] = true;
  });
  return next;
});
// eslint-disable-next-line react-hooks/exhaustive-deps


}, [tasks, focusTaskId]);

// Auto-fit TOTAL (ancho + alto) en modo default
useLayoutEffect(() => {
if (isZoomMode) return;

const recompute = () => {
  const viewport = treeViewportRef.current;
  const stage = treeStageRef.current;
  if (!viewport || !stage) return;

  const viewportW = viewport.clientWidth || 0;
  const viewportH = viewport.clientHeight || 0;

  const stageW = stage.scrollWidth || 0;
  const stageH = stage.scrollHeight || 0;

  if (!viewportW || !viewportH || !stageW || !stageH) {
    setFitScale(1);
    return;
  }

  const ratioW = viewportW / stageW;
  const ratioH = viewportH / stageH;

  const raw = Math.min(ratioW, ratioH);

  const next = clamp(raw, 0.05, 1.15);
  setFitScale(round2(next));

  const resetViewportForFit = () => {
    viewport.scrollLeft = 0;
    viewport.scrollTop = 0;
  };

  requestAnimationFrame(() => {
    requestAnimationFrame(resetViewportForFit);
  });
};

recompute();
window.addEventListener('resize', recompute);
return () => window.removeEventListener('resize', recompute);


}, [isZoomMode, rootTasks, expandedTasks, expandedSessions, loading, focusTaskId]);

const actualScale = isZoomMode ? zoomScale : fitScale;

const pageWrap = {
height: '100vh',
overflowY: 'auto',
backgroundColor: '#f3f4f6',
padding: '1.5rem 1.25rem 2rem',
};

const container = { width: '100%', maxWidth: 'none', margin: '0 auto' };

const headerCard = {
backgroundColor: '#ffffff',
borderRadius: '0.9rem',
border: '1px solid #e5e7eb',
padding: '1rem 1.1rem',
boxShadow: '0 4px 16px rgba(15, 23, 42, 0.06)',
marginBottom: '1rem',
};

const treeCard = {
backgroundColor: '#ffffff',
borderRadius: '0.9rem',
border: '1px solid #e5e7eb',
padding: '1rem 1.1rem',
boxShadow: '0 4px 16px rgba(15, 23, 42, 0.06)',
};

const miniBtn = {
padding: '0.2rem 0.55rem',
borderRadius: '999px',
border: '1px solid #d1d5db',
backgroundColor: '#fff',
color: '#374151',
fontSize: '0.8rem',
cursor: 'pointer',
lineHeight: 1.2,
};

const toolBtn = {
...miniBtn,
fontSize: '0.78rem',
padding: '0.25rem 0.6rem',
};

const statusLabel = (estadoRaw) => {
const e = String(estadoRaw || '').toLowerCase();
if (e === 'finalizada') return 'Finalizada';
if (e === 'en_pausa') return 'En pausa';
if (e === 'pendiente') return 'Pendiente';
return 'En progreso';
};

const focusTask = focusTaskId ? tasksById[String(focusTaskId)] : null;
const focusChildren = focusTaskId ? (childrenMap[String(focusTaskId)] || []) : [];

const renderTreeTask = (task, ancestors) => {
const taskIdStr = String(task.id);
const seenPath = ancestors || new Set();
if (seenPath.has(taskIdStr)) return null;
const nextSeenPath = new Set(seenPath);
nextSeenPath.add(taskIdStr);
const childList = childrenMap[taskIdStr] || [];
const hasChildren = childList.length > 0;

const taskSessions = sessionsByTask[taskIdStr] || [];
const hasSessions = taskSessions.length > 0;

const isExpanded = !!expandedTasks[taskIdStr];
const areSessionsExpanded = !!expandedSessions[taskIdStr];

const branchColor = getBranchColor(task);

const spentMinutes = typeof task.minutos_reales === 'number' ? task.minutos_reales : 0;
const estimatedMinutes = typeof task.minutos_estimados === 'number' ? task.minutos_estimados : 0;

return (
  <li key={task.id}>
    <div className="wt-tree-node">
      <div className="wt-tree-node-bar" style={{ backgroundColor: branchColor }} />
      <div className="wt-tree-node-inner">
        <div className="wt-tree-node-top">
          <div className="wt-tree-node-title">{task.titulo}</div>
          <div className="wt-tree-node-status">{statusLabel(task.estado)}</div>
        </div>

        <div className="wt-tree-node-sub">
          {formatMinutes(spentMinutes)} / {estimatedMinutes ? formatMinutes(estimatedMinutes) : '—'}
          {task.fecha_plan_inicio ? ` · Inicio: ${task.fecha_plan_inicio}` : ''}
          {task.fecha_plan_fin ? ` · Fin: ${task.fecha_plan_fin}` : ''}
        </div>

        <div className="wt-tree-node-actions">
          {hasChildren ? (
            <button
              type="button"
              onClick={() => toggleTask(taskIdStr)}
              style={miniBtn}
              title={isExpanded ? 'Contraer rama' : 'Expandir rama'}
            >
              {isExpanded && hasChildren ? `Contraer (${childList.length})` : `Expandir (${childList.length})`}
            </button>
          ) : (
            <button type="button" style={{ ...miniBtn, opacity: 0.5, cursor: 'not-allowed' }} disabled>
              {`Expandir (${childList.length})`}
            </button>
          )}

          <button
            type="button"
            onClick={() => focusOnTask(taskIdStr)}
            style={miniBtn}
            title="Ver árbol desde esta tarea (ponerla como raíz)"
          >
            Foco
          </button>

          <Link
            to={`/projects/${projectId}/tasks/${task.id}`}
            state={{
              taskName: task.titulo,
              taskColor: branchColor,
              projectName,
              projectColor,
            }}
            style={{ ...miniBtn, textDecoration: 'none', display: 'inline-block' }}
          >
            Abrir
          </Link>

          <button
            type="button"
            onClick={() => toggleTaskSessions(taskIdStr)}
            disabled={!hasSessions}
            style={{
              ...miniBtn,
              opacity: hasSessions ? 1 : 0.5,
              cursor: hasSessions ? 'pointer' : 'not-allowed',
            }}
            title={hasSessions ? (areSessionsExpanded ? 'Ocultar sesiones' : 'Ver sesiones') : 'Sin sesiones'}
          >
            Sesiones {hasSessions ? `(${taskSessions.length})` : '(0)'}
          </button>
        </div>

        {areSessionsExpanded && hasSessions && (
          <div className="wt-tree-sessions">
            {taskSessions.map((s) => {
              const isActive = !s.endedAt;
              const dateLabel = s.plannedDate || '—';
              const titleLabel = s.title ? ` · ${s.title}` : '';
              const durationLabel = isActive ? 'En curso' : `Real: ${formatMinutes(s.minutes)}`;

              return (
                <div key={s.id} className="wt-tree-session-row">
                  <div className="wt-tree-session-left">
                    <div className="wt-tree-session-title">
                      {dateLabel}{titleLabel}
                    </div>
                    <div className="wt-tree-session-sub">{durationLabel}</div>
                  </div>

                  <div
                    className="wt-tree-session-badge"
                    style={{ color: isActive ? '#f97316' : '#16a34a' }}
                  >
                    {isActive ? 'En curso' : 'Finalizada'}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>

    {isExpanded && hasChildren && (
      <ul>
        {childList.map((child) => renderTreeTask(child, nextSeenPath))}
      </ul>
    )}
  </li>
);


};

const renderFocusRootNode = (task) => {
const taskIdStr = String(task.id);
const branchColor = getBranchColor(task);

const spentMinutes = typeof task.minutos_reales === 'number' ? task.minutos_reales : 0;
const estimatedMinutes = typeof task.minutos_estimados === 'number' ? task.minutos_estimados : 0;

return (
  <div className="wt-tree-node">
    <div className="wt-tree-node-bar" style={{ backgroundColor: branchColor }} />
    <div className="wt-tree-node-inner">
      <div className="wt-tree-node-top">
        <div className="wt-tree-node-title">{task.titulo}</div>
        <div className="wt-tree-node-status">Raíz (tarea)</div>
      </div>
      <div className="wt-tree-node-sub">
        {formatMinutes(spentMinutes)} / {estimatedMinutes ? formatMinutes(estimatedMinutes) : '—'}
        {task.fecha_plan_inicio ? ` · Inicio: ${task.fecha_plan_inicio}` : ''}
        {task.fecha_plan_fin ? ` · Fin: ${task.fecha_plan_fin}` : ''}
      </div>
      <div className="wt-tree-node-actions">
        <button
          type="button"
          onClick={clearFocus}
          style={miniBtn}
          title="Volver al árbol completo del proyecto"
        >
          Volver
        </button>

        <button
          type="button"
          onClick={() => focusOnTask(taskIdStr)}
          style={{ ...miniBtn, opacity: 0.7 }}
          title="Recentrar este foco (mantiene este nodo como raíz)"
        >
          Recentrar
        </button>

        <Link
          to={`/projects/${projectId}/tasks/${task.id}`}
          state={{
            taskName: task.titulo,
            taskColor: branchColor,
            projectName,
            projectColor,
          }}
          style={{ ...miniBtn, textDecoration: 'none', display: 'inline-block' }}
        >
          Abrir
        </Link>
      </div>
    </div>
  </div>
);


};

const viewportStyle = {
width: '100%',
height: 'calc(100vh - 320px)',
minHeight: '420px',
padding: '0.25rem 0.25rem 0.75rem',
borderRadius: '0.75rem',
backgroundColor: '#ffffff',
overflow: isZoomMode ? 'auto' : 'hidden',
display: 'flex',
justifyContent: isZoomMode ? 'flex-start' : 'center',
alignItems: 'flex-start',
};

return (
<div style={pageWrap}>
<style>{`
/* === Árbol tipo organigrama (genealógico) === */

    .wt-tree-stage {
      display: block;
      transform-origin: top center;
      transition: transform 160ms ease;
    }

    .wt-tree {
      display: inline-block;
    }

    .wt-tree ul {
      padding-top: 22px;
      position: relative;
      display: flex;
      justify-content: center;
      gap: 10px;
    }

    .wt-tree li {
      list-style-type: none;
      text-align: center;
      position: relative;
      padding: 22px 8px 0 8px;
      flex: 0 0 auto;
    }

    /* Líneas horizontales entre hermanos */
    .wt-tree li::before,
    .wt-tree li::after {
      content: '';
      position: absolute;
      top: 0;
      width: 50%;
      height: 22px;
      border-top: 2px solid #d1d5db;
    }

    .wt-tree li::before {
      right: 50%;
      border-right: 2px solid #d1d5db;
      border-top-right-radius: 10px;
    }

    .wt-tree li::after {
      left: 50%;
      border-left: 2px solid #d1d5db;
      border-top-left-radius: 10px;
    }

    /* Si solo hay un hijo, sin líneas laterales */
    .wt-tree li:only-child::before,
    .wt-tree li:only-child::after {
      display: none;
    }

    .wt-tree li:only-child {
      padding-top: 0;
    }

    /* Primer y último hijo: recortar línea externa */
    .wt-tree li:first-child::before {
      border: 0 none;
    }
    .wt-tree li:last-child::after {
      border: 0 none;
    }

    /* Línea vertical desde padre hacia el grupo de hijos */
    .wt-tree ul::before {
      content: '';
      position: absolute;
      top: 0;
      left: 50%;
      height: 22px;
      border-left: 2px solid #d1d5db;
      transform: translateX(-50%);
    }

    /* NODO */
    .wt-tree-node {
      display: inline-flex;
      align-items: stretch;
      background: #ffffff;
      border: 1px solid #e5e7eb;
      border-radius: 18px;
      box-shadow: 0 6px 18px rgba(15, 23, 42, 0.06);
      min-width: 280px;
      max-width: 340px;
      text-align: left;
      overflow: hidden;
    }

    .wt-tree-node:hover {
      box-shadow: 0 10px 26px rgba(15, 23, 42, 0.10);
      transform: translateY(-1px);
      transition: box-shadow 160ms ease, transform 160ms ease;
    }

    .wt-tree-node-bar {
      width: 6px;
      flex: 0 0 auto;
    }

    .wt-tree-node-inner {
      padding: 0.75rem 0.85rem;
      min-width: 0;
      flex: 1;
    }

    .wt-tree-node-top {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 0.75rem;
      margin-bottom: 0.25rem;
    }

    .wt-tree-node-title {
      font-size: 0.95rem;
      font-weight: 700;
      color: #111827;
      min-width: 0;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .wt-tree-node-status {
      font-size: 0.78rem;
      color: #6b7280;
      flex: 0 0 auto;
    }

    .wt-tree-node-sub {
      font-size: 0.8rem;
      color: #6b7280;
      margin-bottom: 0.6rem;
    }

    .wt-tree-node-actions {
      display: flex;
      gap: 0.4rem;
      flex-wrap: wrap;
    }

    .wt-tree-sessions {
      margin-top: 0.6rem;
      padding-top: 0.6rem;
      border-top: 1px solid #f3f4f6;
    }

    .wt-tree-session-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 0.75rem;
      padding: 0.35rem 0;
      border-bottom: 1px solid #f3f4f6;
    }

    .wt-tree-session-row:last-child {
      border-bottom: none;
    }

    .wt-tree-session-title {
      font-size: 0.82rem;
      color: #111827;
      font-weight: 700;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      max-width: 220px;
    }

    .wt-tree-session-sub {
      font-size: 0.76rem;
      color: #6b7280;
    }

    .wt-tree-session-badge {
      font-size: 0.75rem;
      font-weight: 700;
      flex: 0 0 auto;
    }
  `}</style>

  <div style={container}>
    <div style={headerCard}>
      <div
        style={{
          fontSize: '0.8rem',
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
          color: '#6b7280',
          marginBottom: '0.2rem',
        }}
      >
        Árbol del proyecto
      </div>

      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '1rem' }}>
        <div style={{ minWidth: 0 }}>
          <h1
            style={{
              fontSize: '1.5rem',
              fontWeight: 600,
              color: '#111827',
              margin: 0,
            }}
          >
            {projectName}
          </h1>
          <p style={{ fontSize: '0.9rem', color: '#4b5563', marginTop: '0.35rem', marginBottom: 0 }}>
            Vista tipo organigrama: tareas, subtareas y sesiones (desplegables) conectadas visualmente.
          </p>
        </div>

        <Link
          to={`/projects/${projectId}/charts`}
          style={{ ...miniBtn, textDecoration: 'none', display: 'inline-block', marginTop: '0.15rem' }}
        >
          ← Volver a gráficos
        </Link>
      </div>
    </div>

    <div style={treeCard}>
      {loading && (
        <div style={{ fontSize: '0.9rem', color: '#6b7280' }}>
          Cargando árbol…
        </div>
      )}

      {!loading && loadError && (
        <div style={{ fontSize: '0.9rem', color: '#b91c1c' }}>
          Error: {loadError}
        </div>
      )}

      {!loading && !loadError && rootTasks.length === 0 && (
        <div style={{ fontSize: '0.9rem', color: '#6b7280' }}>
          Este proyecto todavía no tiene tareas.
        </div>
      )}

      {!loading && !loadError && rootTasks.length > 0 && (
        <div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem', marginBottom: '0.75rem' }}>
            <div style={{ display: 'flex', gap: '0.45rem', flexWrap: 'wrap', alignItems: 'center' }}>
              {!isZoomMode ? (
                <button type="button" onClick={enterZoomMode} style={toolBtn} title="Activar lupa (zoom + scroll)">
                  🔍 Lupa
                </button>
              ) : (
                <>
                  <button type="button" onClick={exitZoomMode} style={toolBtn} title="Volver al modo ajustado (sin scroll)">
                    Ajustar
                  </button>

                  <button
                    type="button"
                    onClick={() => setZoomScale((s) => clamp(round2((Number(s) || 1) - 0.1), 0.2, 2.5))}
                    style={toolBtn}
                    title="Zoom -"
                  >
                    −
                  </button>

                  <button
                    type="button"
                    onClick={() => setZoomScale((s) => clamp(round2((Number(s) || 1) + 0.1), 0.2, 2.5))}
                    style={toolBtn}
                    title="Zoom +"
                  >
                    +
                  </button>

                  <button
                    type="button"
                    onClick={() => setZoomScale(1)}
                    style={toolBtn}
                    title="Reset zoom (100%)"
                  >
                    100%
                  </button>

                  <span style={{ fontSize: '0.78rem', color: '#6b7280' }}>
                    Zoom: {Math.round((zoomScale || 1) * 100)}%
                  </span>
                </>
              )}

              {focusTaskId && (
                <button
                  type="button"
                  onClick={clearFocus}
                  style={toolBtn}
                  title="Volver al árbol completo del proyecto"
                >
                  Árbol completo
                </button>
              )}
            </div>

            {false && !isZoomMode && (
              <div style={{ fontSize: '0.78rem', color: '#6b7280' }}>
                Ajuste: {Math.round((fitScale || 1) * 100)}%
              </div>
            )}
          </div>

          <div
            ref={treeViewportRef}
            style={viewportStyle}
          >
            <div
              className="wt-tree-stage"
              ref={treeStageRef}
              style={{
                transform: `scale(${actualScale})`,
                width: 'max-content',
                flex: '0 0 auto',
              }}
            >
              <div className="wt-tree">
                {focusTask ? (
                  <ul>
                    <li>
                      {renderFocusRootNode(focusTask)}
                      <ul>
                        {focusChildren.map((t) => renderTreeTask(t))}
                      </ul>
                    </li>
                  </ul>
                ) : (
                  <ul>
                    <li>
                      <div className="wt-tree-node">
                        <div className="wt-tree-node-bar" style={{ backgroundColor: projectColor }} />
                        <div className="wt-tree-node-inner">
                          <div className="wt-tree-node-top">
                            <div className="wt-tree-node-title">{projectName}</div>
                            <div className="wt-tree-node-status">Proyecto</div>
                          </div>
                          <div className="wt-tree-node-sub">Nodo raíz del proyecto</div>
                          <div className="wt-tree-node-actions">
                            <Link
                              to={`/projects/${projectId}`}
                              style={{ ...miniBtn, textDecoration: 'none', display: 'inline-block' }}
                            >
                              Abrir proyecto
                            </Link>
                          </div>
                        </div>
                      </div>

                      <ul>
                        {rootTasks.map((t) => renderTreeTask(t))}
                      </ul>
                    </li>
                  </ul>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  </div>
</div>


);
}
export default ProjectTreePage;
