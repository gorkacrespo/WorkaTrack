import { useEffect, useMemo, useState } from 'react';
import { useParams, Link, useLocation } from 'react-router-dom';
import { apiFetch } from '../api/client';
import TaskSummaryBox from '../components/TaskSummaryBox';
import ProjectYearCalendar from '../components/ProjectYearCalendar';

/**
 * TaskDetailPage (conectado a backend)
 *
 * Backend actual:
 *  - GET  /api/me/sessions          -> lista sesiones del usuario
 *  - POST /api/sessions             -> crea sesión {tarea_id, fecha, minutos, tipo, notas, started_at, ended_at}
 *  - PUT  /api/sessions/:id         -> actualiza sesión
 *  - DELETE /api/sessions/:id       -> elimina sesión
 *
 * NOTA:
 * started_at / ended_at ya existen en backend.
 * Mantenemos compat con metadata en `notas` (JSON) para objectives/notes/predictedHours.
 */

function safeJsonParse(str) {
  try {
    return JSON.parse(str);
  } catch {
    return null;
  }
}

function encodeNotas({
  objectives = '',
  notes = '',
  startedAt = null,
  endedAt = null,
  predictedHours = null,
} = {}) {
  return JSON.stringify({
    v: 2,
    objectives,
    notes,
    startedAt,
    endedAt,
    predictedHours,
  });
}

function decodeNotas(notasRaw) {
  if (!notasRaw) {
    return {
      objectives: '',
      notes: '',
      startedAt: null,
      endedAt: null,
      predictedHours: null,
    };
  }

  const parsed = safeJsonParse(notasRaw);

  // compat: si antes guardaste texto plano
  if (!parsed || typeof parsed !== 'object') {
    return {
      objectives: notasRaw,
      notes: '',
      startedAt: null,
      endedAt: null,
      predictedHours: null,
    };
  }

  return {
    objectives: parsed.objectives || '',
    notes: parsed.notes || '',
    startedAt: parsed.startedAt || null,
    endedAt: parsed.endedAt || null,
    predictedHours:
      typeof parsed.predictedHours === 'number' ? parsed.predictedHours : null,
  };
}

function diffHours(startISO, endISO) {
  const start = new Date(startISO);
  const end = new Date(endISO);
  const ms = end - start;
  const hours = ms / (1000 * 60 * 60);
  return Math.max(0, Math.round(hours * 100) / 100);
}

function formatDateTime(isoString) {
  if (!isoString) return '—';
  const d = new Date(isoString);
  if (Number.isNaN(d.getTime())) return isoString;
  const date = d.toISOString().slice(0, 10);
  const time = d.toTimeString().slice(0, 5);
  return `${date} · ${time}`;
}

function TaskDetailPage() {
  const { projectId, taskId } = useParams();
  const location = useLocation();

  const taskNameFromState = location.state?.taskName;
  const taskColorFromState = location.state?.taskColor;
  const [projectMilestones, setProjectMilestones] = useState([]);

  // Para volver con estado al proyecto:
  const projectNameFromState = location.state?.projectName;
  const projectColorFromState = location.state?.projectColor;

  // ===== Resolver nombres/colores cuando NO hay location.state (Ctrl+Click / nueva pestaña) =====
  const [resolvedTaskName, setResolvedTaskName] = useState(taskNameFromState || '');
  const [resolvedTaskColor, setResolvedTaskColor] = useState(taskColorFromState || '');
  const [resolvedProjectName, setResolvedProjectName] = useState(projectNameFromState || '');
  const [resolvedProjectColor, setResolvedProjectColor] = useState(projectColorFromState || '');

  const taskName = resolvedTaskName || `Tarea #${taskId}`;
  const taskColor = resolvedTaskColor || '#2563eb';

  const projectName = resolvedProjectName || `Proyecto #${projectId}`;
  const projectColor = resolvedProjectColor || '#2563eb';

  useEffect(() => {
    const needsTaskName = !taskNameFromState;
    const needsProjectInfo = !projectNameFromState || !projectColorFromState;

    if (!needsTaskName && !needsProjectInfo) return;

    let cancelled = false;

    (async () => {
      try {
        if (needsTaskName) {
          const tasks = await apiFetch('/me/tasks/with-time');
          if (!cancelled && Array.isArray(tasks)) {
            const t = tasks.find((x) => Number(x.id) === Number(taskId));
            if (t) {
              setResolvedTaskName(t.titulo || '');
              // Si no tenemos projectName por state, al menos usamos la categoria de la tarea
              if (!projectNameFromState && t.categoria) {
                setResolvedProjectName(String(t.categoria));
              }
            }
          }
        }

        if (needsProjectInfo) {
          const projects = await apiFetch('/projects');
          if (!cancelled && Array.isArray(projects)) {
            const p = projects.find((x) => Number(x.id) === Number(projectId));
            if (p) {
              // backend típico: { id, nombre, color }
              setResolvedProjectName(p.nombre || p.name || resolvedProjectName || '');
              setResolvedProjectColor(p.color || resolvedProjectColor || '');
            }
          }
        }
      } catch (err) {
        // No bloqueamos la UI: si falla, se quedarán los fallbacks
        console.warn('No se pudo resolver task/project desde backend:', err);
      }
    })();

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, taskId, taskNameFromState, projectNameFromState, projectColorFromState]);

  // ===== Backend sessions =====
  const [sessions, setSessions] = useState([]);
  const [loadingSessions, setLoadingSessions] = useState(false);
  const [sessionsError, setSessionsError] = useState('');

  // ===== Modal INICIAR sesión =====
  const [startModalOpen, setStartModalOpen] = useState(false);
  const [plannedDate, setPlannedDate] = useState('');
  const [predictedHours, setPredictedHours] = useState('');
  const [sessionTitle, setSessionTitle] = useState('');
  const [sessionObjectivesText, setSessionObjectivesText] = useState('');
  const [startError, setStartError] = useState('');

  // ===== Modal CREAR SUBTAREA =====
  const [createChildTaskModalOpen, setCreateChildTaskModalOpen] = useState(false);
  const [childTaskTitle, setChildTaskTitle] = useState('');
  const [childTaskDescription, setChildTaskDescription] = useState('');
  const [childStartDate, setChildStartDate] = useState('');
  const [childEndDate, setChildEndDate] = useState('');
  const [childEstimatedHours, setChildEstimatedHours] = useState('');
  const [childEstimatedMinutes, setChildEstimatedMinutes] = useState('0');
  const [childTaskError, setChildTaskError] = useState('');

  // ===== Modal FINALIZAR sesión =====
  const [finishModal, setFinishModal] = useState(null); // { sessionId }
  const [finishNotes, setFinishNotes] = useState('');
  const [finishError, setFinishError] = useState('');

  // ===== Modal ELIMINAR sesión =====
  const [deleteSessionModal, setDeleteSessionModal] = useState(null); // { sessionId }
  const [deletePassword, setDeletePassword] = useState('');
  const [deleteError, setDeleteError] = useState('');

  // ===== Modal EDITAR sesión =====
  const [editSessionModal, setEditSessionModal] = useState(null); // { sessionId }
  const [editPlannedDate, setEditPlannedDate] = useState('');
  const [editPredictedHours, setEditPredictedHours] = useState('');
  const [editSessionTitle, setEditSessionTitle] = useState('');
  const [editObjectives, setEditObjectives] = useState('');
  const [editNotes, setEditNotes] = useState('');
  const [editError, setEditError] = useState('');

  // ===== Modal VER DETALLE =====
  const [viewSessionModal, setViewSessionModal] = useState(null);

  // ===== Estilos (como el resto de la app) =====
  const overlayStyle = {
    position: 'fixed',
    inset: 0,
    backgroundColor: 'rgba(15,23,42,0.35)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 50,
  };

  const modalStyle = {
    backgroundColor: '#ffffff',
    borderRadius: '0.75rem',
    padding: '1.5rem',
    minWidth: '360px',
    maxWidth: '700px',
    boxShadow: '0 10px 30px rgba(15,23,42,0.25)',
  };

  const modalActions = {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '0.5rem',
    marginTop: '1rem',
  };

  const inputStyle = {
    width: '100%',
    padding: '0.45rem 0.6rem',
    borderRadius: '0.5rem',
    border: '1px solid #d1d5db',
    fontSize: '0.9rem',
    marginBottom: '0.5rem',
  };

  const textAreaStyle = {
    width: '100%',
    padding: '0.45rem 0.6rem',
    borderRadius: '0.5rem',
    border: '1px solid #d1d5db',
    fontSize: '0.9rem',
    marginBottom: '0.5rem',
    resize: 'vertical',
  };

  const primaryBtn = {
    padding: '0.4rem 0.9rem',
    borderRadius: '999px',
    border: 'none',
    backgroundColor: '#111827',
    color: '#fff',
    fontSize: '0.85rem',
    cursor: 'pointer',
  };

  const secondaryBtn = {
    padding: '0.4rem 0.9rem',
    borderRadius: '999px',
    border: '1px solid #d1d5db',
    backgroundColor: '#fff',
    color: '#374151',
    fontSize: '0.85rem',
    cursor: 'pointer',
  };

  const dangerBtn = {
    ...primaryBtn,
    backgroundColor: '#b91c1c',
  };

  const errorText = {
    fontSize: '0.8rem',
    color: '#b91c1c',
    marginTop: '0.25rem',
  };

  // =============================
  //   CARGAR HITOS DEL PROYECTO (BACKEND)
  // =============================
  async function loadProjectMilestones() {
    try {
      const data = await apiFetch(`/projects/${projectId}/milestones`);

      if (!Array.isArray(data)) {
        throw new Error('Respuesta inesperada de hitos');
      }

      const normalized = data.map((m) => ({
        id: m.id,
        name: m.titulo,
        date: m.fecha,
        color: resolvedProjectColor || '#2563eb',
      }));

      setProjectMilestones(normalized);
    } catch (err) {
      console.error('Error cargando hitos del proyecto:', err);
      setProjectMilestones([]);
    }
  }

  // =============================
  //   CARGAR SESIONES (BACKEND)
  // =============================
  async function loadSessions() {
    setLoadingSessions(true);
    setSessionsError('');
    try {
      const data = await apiFetch('/me/sessions'); // devuelve array
      if (!Array.isArray(data)) {
        throw new Error('Respuesta inesperada de /api/me/sessions');
      }

      const tid = Number(taskId);
      const filtered = data
        .filter((s) => Number(s.tarea_id) === tid)
        .map((s) => {
          const meta = decodeNotas(s.notas);

          const predicted =
            meta.predictedHours != null
              ? Number(meta.predictedHours)
              : s.minutos != null
                ? Number(s.minutos) / 60
                : null;

          const startedAt = s.started_at || meta.startedAt || null;
          const endedAt = s.ended_at || meta.endedAt || null;

          const durationHours =
            endedAt && s.minutos != null ? Number(s.minutos) / 60 : 0;

          return {
            id: s.id,
            plannedDate: s.fecha || null,
            predictedHours: predicted,
            title: s.tipo || null,
            objectives: meta.objectives || '',
            notes: meta.notes || '',
            start: startedAt,
            end: endedAt,
            realMinutes: endedAt && s.minutos != null ? Number(s.minutos) : 0,
            durationHours,
          };
        });

      setSessions(filtered);
    } catch (err) {
      console.error('Error cargando sesiones:', err);
      setSessionsError(err.message || 'Error cargando sesiones');
      setSessions([]);
    } finally {
      setLoadingSessions(false);
    }
  }

  useEffect(() => {
    loadSessions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [taskId]);

  useEffect(() => {
    loadProjectMilestones();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  // =============================
  //   INICIAR SESIÓN (BACKEND)
  // =============================
  const openStartSessionModal = () => {
    setStartModalOpen(true);
    setPlannedDate('');
    setPredictedHours('');
    setSessionTitle('');
    setSessionObjectivesText('');
    setStartError('');
  };

  const confirmStartSession = async () => {
    if (!plannedDate) {
      setStartError('Selecciona una fecha para la sesión.');
      return;
    }

    let predicted = null;
    if (predictedHours) {
      const num = Number(predictedHours);
      if (!num || num <= 0) {
        setStartError('Las horas previstas deben ser un número mayor de 0.');
        return;
      }
      predicted = num;
    }

    const nowISO = new Date().toISOString();

    const payload = {
      tarea_id: Number(taskId),
      fecha: plannedDate,
      minutos: 0,
      tipo: sessionTitle.trim() || null,
      notas: encodeNotas({
        objectives: sessionObjectivesText.trim(),
        notes: '',
        startedAt: nowISO,
        endedAt: null,
        predictedHours: predicted,
      }),
      started_at: nowISO,
      ended_at: null,
    };

    try {
      await apiFetch('/sessions', {
        method: 'POST',
        body: JSON.stringify(payload),
      });

      await loadSessions();
      setStartModalOpen(false);
    } catch (err) {
      console.error('Error iniciando sesión:', err);
      setStartError(err.message || 'Error iniciando la sesión');
    }
  };

  // =============================
  //   CREAR SUBTAREA (BACKEND)
  // =============================
  const openCreateChildTaskModal = () => {
    setCreateChildTaskModalOpen(true);
    setChildTaskTitle('');
    setChildTaskDescription('');
    setChildStartDate('');
    setChildEndDate('');
    setChildEstimatedHours('');
    setChildEstimatedMinutes('0');
    setChildTaskError('');
  };

  const confirmCreateChildTask = async () => {
    if (!childTaskTitle.trim()) {
      setChildTaskError('El título es obligatorio.');
      return;
    }

    if (childStartDate && childEndDate && childEndDate < childStartDate) {
      setChildTaskError('La fecha de fin no puede ser anterior a la de inicio.');
      return;
    }

    let minutos_estimados = null;

    const hoursStr = childEstimatedHours.trim();
    const minutesStr = childEstimatedMinutes.trim();

    if (hoursStr || minutesStr) {
      const h = hoursStr ? Number(hoursStr) : 0;
      const m = minutesStr ? Number(minutesStr) : 0;

      if (!Number.isFinite(h) || h < 0 || !Number.isInteger(h)) {
        setChildTaskError('Las horas estimadas deben ser un entero ≥ 0.');
        return;
      }

      if (!Number.isFinite(m) || m < 0 || m > 59 || !Number.isInteger(m)) {
        setChildTaskError('Los minutos estimados deben ser un entero entre 0 y 59.');
        return;
      }

      const total = (h * 60) + m;
      minutos_estimados = total > 0 ? total : null;
    }

    const payload = {
      titulo: childTaskTitle.trim(),
      descripcion: childTaskDescription.trim() || null,
      project_id: Number(projectId),
      parent_task_id: Number(taskId),
      estado: 'pendiente',
      fecha_plan_inicio: childStartDate || null,
      fecha_plan_fin: childEndDate || null,
      minutos_estimados,
    };

    try {
      await apiFetch('/tasks', {
        method: 'POST',
        body: JSON.stringify(payload),
      });

      setCreateChildTaskModalOpen(false);
    } catch (err) {
      console.error('Error creando subtarea:', err);
      setChildTaskError(err.message || 'Error creando la subtarea');
    }
  };

  // =============================
  //   FINALIZAR SESIÓN (BACKEND)
  // =============================
  const openFinishSessionModal = (sessionId) => {
    setFinishModal({ sessionId });
    setFinishNotes('');
    setFinishError('');
  };

  const confirmFinishSession = async () => {
    if (!finishModal) return;

    const nowISO = new Date().toISOString();

    const target = sessions.find((s) => s.id === finishModal.sessionId);
    if (!target || !target.start) {
      setFinishError('No se puede finalizar: falta hora de inicio.');
      return;
    }

    const duration = diffHours(target.start, nowISO);
    const minutesReal = Math.max(0, Math.round(duration * 60));

    const mergedNotas = encodeNotas({
      objectives: target.objectives || '',
      notes: finishNotes.trim(),
      startedAt: target.start,
      endedAt: nowISO,
      predictedHours:
        typeof target.predictedHours === 'number' ? target.predictedHours : null,
    });

    try {
      await apiFetch(`/sessions/${finishModal.sessionId}`, {
        method: 'PUT',
        body: JSON.stringify({
          tarea_id: Number(taskId),
          fecha: target.plannedDate,
          minutos: minutesReal,
          tipo: target.title || null,
          notas: mergedNotas,
          started_at: target.start,
          ended_at: nowISO,
        }),
      });

      await loadSessions();
      setFinishModal(null);
    } catch (err) {
      console.error('Error finalizando sesión:', err);
      setFinishError(err.message || 'Error finalizando la sesión');
    }
  };

  // =============================
  //   ELIMINAR SESIÓN (BACKEND)
  // =============================
  const openDeleteSessionModal = (sessionId) => {
    setDeleteSessionModal({ sessionId });
    setDeletePassword('');
    setDeleteError('');
  };

  const confirmDeleteSession = async () => {
    if (!deleteSessionModal) return;

    if (!deletePassword.trim()) {
      setDeleteError('Debes introducir tu contraseña para borrar la sesión.');
      return;
    }

    try {
      await apiFetch(`/sessions/${deleteSessionModal.sessionId}`, {
        method: 'DELETE',
        body: JSON.stringify({ password: deletePassword }),
      });

      await loadSessions();
      setDeleteSessionModal(null);
      setDeletePassword('');
      setDeleteError('');
    } catch (err) {
      console.error('Error eliminando sesión:', err);
      setDeleteError(err.message || 'Error eliminando la sesión');
    }
  };

  // =============================
  //   EDITAR SESIÓN (BACKEND)
  // =============================
  const openEditSessionModal = (session) => {
    const baseDate =
      session.plannedDate || (session.start ? session.start.slice(0, 10) : '');

    setEditSessionModal({ sessionId: session.id });
    setEditPlannedDate(baseDate);
    setEditPredictedHours(
      session.predictedHours != null ? String(session.predictedHours) : ''
    );
    setEditSessionTitle(session.title || '');
    setEditObjectives(session.objectives || '');
    setEditNotes(session.notes || '');
    setEditError('');
  };

  const confirmEditSession = async () => {
    if (!editSessionModal) return;

    if (!editPlannedDate) {
      setEditError('Selecciona una fecha en el calendario para la sesión.');
      return;
    }

    let predicted = null;
    if (editPredictedHours) {
      const num = Number(editPredictedHours);
      if (!num || num <= 0) {
        setEditError('Las horas previstas deben ser un número mayor de 0.');
        return;
      }
      predicted = num;
    }

    const target = sessions.find((s) => s.id === editSessionModal.sessionId);
    if (!target) {
      setEditError('Sesión no encontrada.');
      return;
    }

    const minutesToStore = target.end
      ? Math.max(0, Math.round((target.durationHours || 0) * 60))
      : 0;

    const notasMerged = encodeNotas({
      objectives: editObjectives.trim(),
      notes: editNotes.trim(),
      startedAt: target.start || null,
      endedAt: target.end || null,
      predictedHours: predicted,
    });

    try {
      await apiFetch(`/sessions/${editSessionModal.sessionId}`, {
        method: 'PUT',
        body: JSON.stringify({
          tarea_id: Number(taskId),
          fecha: editPlannedDate,
          minutos: minutesToStore,
          tipo: editSessionTitle.trim() || null,
          notas: notasMerged,
          started_at: target.start || null,
          ended_at: target.end || null,
        }),
      });

      await loadSessions();
      setEditSessionModal(null);
    } catch (err) {
      console.error('Error editando sesión:', err);
      setEditError(err.message || 'Error editando la sesión');
    }
  };

  // =============================
  //   CALENDARIO
  // =============================
  const calendarItems = useMemo(() => {
    const items = [
      ...sessions.map((s) => ({
        id: s.id,
        name: s.title ? `${taskName}: ${s.title}` : taskName,
        createdAt: s.plannedDate || (s.start ? s.start.slice(0, 10) : null),
        progress: 0,
        color: taskColor,
        type: 'default',
      })),

      ...projectMilestones.map((m) => ({
        id: `milestone-${m.id}`,
        name: `Hito: ${m.name}`,
        createdAt: m.date,
        progress: 0,
        color: m.color || '#111827',
        type: 'milestone',
      })),
    ];

    return items.filter((x) => x.createdAt);
  }, [sessions, projectMilestones, taskName, taskColor]);

  return (
    <>
      <div className="projects-layout">
        <div className="projects-list-panel">
          <div className="projects-header">
            <div>
              <h2>Sesiones de la tarea: {taskName}</h2>
              <p className="projects-subtitle">
                Aquí verás el listado de sesiones, objetivos y notas de esta tarea.
              </p>
            </div>

            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button
                type="button"
                className="create-project-btn"
                onClick={openStartSessionModal}
              >
                + Comenzar sesión
              </button>

              <button
                type="button"
                className="create-project-btn"
                onClick={openCreateChildTaskModal}
              >
                + Subtarea
              </button>
            </div>
          </div>

          {loadingSessions && (
            <div className="project-card">
              <p style={{ margin: 0, fontSize: '0.9rem', color: '#6b7280' }}>
                Cargando sesiones…
              </p>
            </div>
          )}

          {sessionsError && !loadingSessions && (
            <div className="project-card">
              <p style={{ margin: 0, fontSize: '0.9rem', color: '#b91c1c' }}>
                Error al cargar sesiones: {sessionsError}
              </p>
            </div>
          )}

          <div className="projects-list">
            {!loadingSessions && !sessionsError && sessions.length === 0 && (
              <div className="project-card">
                <p style={{ color: '#6b7280', fontSize: '0.9rem', margin: 0 }}>
                  Todavía no hay sesiones registradas para esta tarea. Inicia la primera con el botón
                  &quot;Comenzar sesión&quot;.
                </p>
              </div>
            )}

            {sessions.map((s) => {
              const isActive = !s.end;
              const displayDate =
                s.plannedDate || (s.start ? s.start.slice(0, 10) : '—');

              let durationLabel = 'Duración aún no registrada';

              if (s.end && typeof s.durationHours === 'number') {
                const totalMinutes = Math.round(s.durationHours * 60);

                if (totalMinutes < 60) {
                  durationLabel = `Real: ${totalMinutes}min`;
                } else {
                  const h = Math.floor(totalMinutes / 60);
                  const m = totalMinutes % 60;
                  durationLabel = m > 0 ? `Real: ${h}h ${m}min` : `Real: ${h}h`;
                }
              } else if (!s.end && s.predictedHours) {
                durationLabel = `Previsto: ${s.predictedHours}h`;
              }

              return (
                <div
                  key={s.id}
                  className="project-card"
                  style={{ borderLeft: `4px solid ${taskColor}` }}
                >
                  <div className="project-card-header">
                    <h3>
                      Sesión del {displayDate}
                      {s.title ? `: ${s.title}` : ''}
                    </h3>
                    <span className="project-created">{durationLabel}</span>
                  </div>

                  {s.objectives && (
                    <p
                      style={{
                        marginTop: 0,
                        marginBottom: '0.25rem',
                        fontSize: '0.85rem',
                        color: '#4b5563',
                      }}
                    >
                      <strong>Objetivos: </strong>
                      {s.objectives}
                    </p>
                  )}

                  {s.notes && (
                    <p
                      style={{
                        marginTop: 0,
                        marginBottom: '0.25rem',
                        fontSize: '0.85rem',
                        color: '#4b5563',
                      }}
                    >
                      <strong>Notas: </strong>
                      {s.notes}
                    </p>
                  )}

                  <div className="project-card-footer">
                    <div className="project-footer-left">
                      <span
                        style={{
                          fontSize: '0.8rem',
                          color: isActive ? '#f97316' : '#16a34a',
                        }}
                      >
                        {isActive ? 'Sesión en curso' : 'Sesión finalizada'}
                      </span>
                    </div>

                    <div className="project-footer-right" style={{ gap: '0.4rem' }}>
                      <button
                        type="button"
                        className="project-link"
                        onClick={() => setViewSessionModal(s)}
                      >
                        Ver detalle
                      </button>

                      <button
                        type="button"
                        className="project-color-picker-label"
                        onClick={() => openEditSessionModal(s)}
                      >
                        Editar sesión
                      </button>

                      <button
                        type="button"
                        className="delete-project-btn"
                        onClick={() => openDeleteSessionModal(s.id)}
                      >
                        Eliminar sesión
                      </button>

                      {isActive && (
                        <button
                          type="button"
                          className="project-color-picker-label"
                          onClick={() => openFinishSessionModal(s.id)}
                        >
                          Finalizar sesión
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          <p style={{ marginTop: '1rem' }}>
            <Link
              to={`/projects/${projectId}`}
              state={{
                projectName,
                projectColor,
              }}
            >
              ← Volver al proyecto
            </Link>
          </p>
        </div>

        <div className="projects-calendar-panel">
          <h3>Calendario de la tarea</h3>
          <p
            style={{
              fontSize: '0.8rem',
              color: '#6b7280',
              marginTop: 0,
              marginBottom: '0.5rem',
            }}
          >
            Círculos → sesiones de esta tarea. Cuadrados → hitos del proyecto.
          </p>
          <ProjectYearCalendar projects={calendarItems} />
          <TaskSummaryBox taskId={taskId} />
        </div>
      </div>

      {/* MODAL CREAR SUBTAREA */}
      {createChildTaskModalOpen && (
        <div style={overlayStyle}>
          <div style={modalStyle}>
            <h3>Crear subtarea de {taskName}</h3>

            <label style={{ fontSize: '0.85rem' }}>Título</label>
            <input
              type="text"
              style={inputStyle}
              placeholder="Ej: Diseñar el esquema del árbol"
              value={childTaskTitle}
              onChange={(e) => {
                setChildTaskTitle(e.target.value);
                setChildTaskError('');
              }}
            />

            <label style={{ fontSize: '0.85rem' }}>Descripción (opcional)</label>
            <textarea
              style={textAreaStyle}
              placeholder="Descripción breve..."
              value={childTaskDescription}
              onChange={(e) => {
                setChildTaskDescription(e.target.value);
                setChildTaskError('');
              }}
              rows={3}
            />

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
                gap: '0.75rem',
              }}
            >
              <div>
                <label style={{ fontSize: '0.85rem' }}>Inicio previsto</label>
                <input
                  type="date"
                  style={inputStyle}
                  value={childStartDate}
                  onChange={(e) => {
                    setChildStartDate(e.target.value);
                    setChildTaskError('');
                  }}
                />
              </div>

              <div>
                <label style={{ fontSize: '0.85rem' }}>Fin previsto</label>
                <input
                  type="date"
                  style={inputStyle}
                  value={childEndDate}
                  onChange={(e) => {
                    setChildEndDate(e.target.value);
                    setChildTaskError('');
                  }}
                />
              </div>
            </div>

            <label style={{ fontSize: '0.85rem' }}>Tiempo estimado (opcional)</label>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <input
                type="number"
                min="0"
                step="1"
                style={inputStyle}
                placeholder="Horas"
                value={childEstimatedHours}
                onChange={(e) => {
                  setChildEstimatedHours(e.target.value);
                  setChildTaskError('');
                }}
              />
              <input
                type="number"
                min="0"
                max="59"
                step="1"
                style={inputStyle}
                placeholder="Minutos"
                value={childEstimatedMinutes}
                onChange={(e) => {
                  setChildEstimatedMinutes(e.target.value);
                  setChildTaskError('');
                }}
              />
            </div>

            {childTaskError && <div style={errorText}>{childTaskError}</div>}

            <div style={modalActions}>
              <button
                type="button"
                style={secondaryBtn}
                onClick={() => {
                  setCreateChildTaskModalOpen(false);
                  setChildTaskError('');
                }}
              >
                Cancelar
              </button>
              <button
                type="button"
                style={primaryBtn}
                onClick={confirmCreateChildTask}
              >
                Crear subtarea
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL INICIAR SESIÓN */}
      {startModalOpen && (
        <div style={overlayStyle}>
          <div style={modalStyle}>
            <h3>Iniciar sesión para {taskName}</h3>

            <label style={{ fontSize: '0.85rem' }}>Fecha de la sesión</label>
            <input
              type="date"
              style={inputStyle}
              value={plannedDate}
              onChange={(e) => {
                setPlannedDate(e.target.value);
                setStartError('');
              }}
            />

            <label style={{ fontSize: '0.85rem' }}>
              Nombre de la sesión (opcional)
            </label>
            <input
              type="text"
              style={inputStyle}
              placeholder="Ej: Inicializar el proyecto"
              value={sessionTitle}
              onChange={(e) => setSessionTitle(e.target.value)}
            />

            <label style={{ fontSize: '0.85rem' }}>
              Horas previstas (opcional)
            </label>
            <input
              type="number"
              min="0"
              step="0.25"
              style={inputStyle}
              placeholder="Ej: 1.5"
              value={predictedHours}
              onChange={(e) => {
                setPredictedHours(e.target.value);
                setStartError('');
              }}
            />

            <label style={{ fontSize: '0.85rem' }}>
              Objetivos de la sesión
            </label>
            <textarea
              style={textAreaStyle}
              placeholder="Ej: terminar el esquema del tema 12, revisar bibliografía..."
              value={sessionObjectivesText}
              onChange={(e) => setSessionObjectivesText(e.target.value)}
              rows={3}
            />

            {startError && <div style={errorText}>{startError}</div>}

            <div style={modalActions}>
              <button
                type="button"
                style={secondaryBtn}
                onClick={() => setStartModalOpen(false)}
              >
                Cancelar
              </button>
              <button
                type="button"
                style={primaryBtn}
                onClick={confirmStartSession}
              >
                Iniciar sesión ahora
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL FINALIZAR SESIÓN */}
      {finishModal && (
        <div style={overlayStyle}>
          <div style={modalStyle}>
            <h3>Finalizar sesión</h3>
            <p style={{ fontSize: '0.9rem', marginBottom: '0.5rem' }}>
              Escribe cómo ha ido la sesión, sensaciones, incidencias… La duración se calculará automáticamente.
            </p>

            <label style={{ fontSize: '0.85rem' }}>
              Notas / sensaciones de la sesión
            </label>
            <textarea
              style={textAreaStyle}
              placeholder="Ej: he avanzado más de lo esperado, me he atascado en..."
              value={finishNotes}
              onChange={(e) => {
                setFinishNotes(e.target.value);
                setFinishError('');
              }}
              rows={3}
            />

            {finishError && <div style={errorText}>{finishError}</div>}

            <div style={modalActions}>
              <button
                type="button"
                style={secondaryBtn}
                onClick={() => setFinishModal(null)}
              >
                Cancelar
              </button>
              <button
                type="button"
                style={primaryBtn}
                onClick={confirmFinishSession}
              >
                Guardar y finalizar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL ELIMINAR SESIÓN */}
      {deleteSessionModal && (
        <div style={overlayStyle}>
          <div style={modalStyle}>
            <h3>Eliminar sesión</h3>
            <p style={{ fontSize: '0.9rem', marginBottom: '0.5rem' }}>
              Vas a eliminar esta sesión de trabajo. Más adelante validaremos la contraseña con el backend.
            </p>

            <label style={{ fontSize: '0.85rem' }}>Contraseña</label>
            <input
              type="password"
              style={inputStyle}
              placeholder="Contraseña"
              value={deletePassword}
              onChange={(e) => {
                setDeletePassword(e.target.value);
                setDeleteError('');
              }}
            />

            {deleteError && <div style={errorText}>{deleteError}</div>}

            <div style={modalActions}>
              <button
                type="button"
                style={secondaryBtn}
                onClick={() => {
                  setDeleteSessionModal(null);
                  setDeletePassword('');
                  setDeleteError('');
                }}
              >
                Cancelar
              </button>
              <button
                type="button"
                style={dangerBtn}
                onClick={confirmDeleteSession}
              >
                Eliminar sesión
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL EDITAR SESIÓN */}
      {editSessionModal && (
        <div style={overlayStyle}>
          <div style={modalStyle}>
            <h3>Editar sesión de {taskName}</h3>

            <label style={{ fontSize: '0.85rem' }}>Fecha en calendario</label>
            <input
              type="date"
              style={inputStyle}
              value={editPlannedDate}
              onChange={(e) => {
                setEditPlannedDate(e.target.value);
                setEditError('');
              }}
            />

            <label style={{ fontSize: '0.85rem' }}>
              Nombre de la sesión (opcional)
            </label>
            <input
              type="text"
              style={inputStyle}
              value={editSessionTitle}
              onChange={(e) => setEditSessionTitle(e.target.value)}
            />

            <label style={{ fontSize: '0.85rem' }}>
              Horas previstas (opcional)
            </label>
            <input
              type="number"
              min="0"
              step="0.25"
              style={inputStyle}
              value={editPredictedHours}
              onChange={(e) => {
                setEditPredictedHours(e.target.value);
                setEditError('');
              }}
            />

            <label style={{ fontSize: '0.85rem' }}>
              Objetivos de la sesión
            </label>
            <textarea
              style={textAreaStyle}
              value={editObjectives}
              onChange={(e) => setEditObjectives(e.target.value)}
              rows={3}
            />

            <label style={{ fontSize: '0.85rem' }}>
              Notas / sensaciones
            </label>
            <textarea
              style={textAreaStyle}
              value={editNotes}
              onChange={(e) => setEditNotes(e.target.value)}
              rows={3}
            />

            {editError && <div style={errorText}>{editError}</div>}

            <div style={modalActions}>
              <button
                type="button"
                style={secondaryBtn}
                onClick={() => setEditSessionModal(null)}
              >
                Cancelar
              </button>
              <button
                type="button"
                style={primaryBtn}
                onClick={confirmEditSession}
              >
                Guardar cambios
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL VER DETALLE */}
      {viewSessionModal && (
        <div style={overlayStyle}>
          <div style={modalStyle}>
            <h3>
              Sesión de {taskName}
              {viewSessionModal.title ? `: ${viewSessionModal.title}` : ''}
            </h3>

            <p
              style={{
                fontSize: '0.9rem',
                marginBottom: '0.75rem',
                color: '#4b5563',
              }}
            >
              <strong>Fecha en calendario:</strong>{' '}
              {viewSessionModal.plannedDate ||
                (viewSessionModal.start
                  ? viewSessionModal.start.slice(0, 10)
                  : '—')}
              <br />
              <strong>Inicio real:</strong>{' '}
              {formatDateTime(viewSessionModal.start)}
              <br />
              <strong>Fin real:</strong>{' '}
              {viewSessionModal.end
                ? formatDateTime(viewSessionModal.end)
                : 'Todavía en curso'}
              <br />
              <strong>Duración real:</strong>{' '}
              {viewSessionModal.end &&
              typeof viewSessionModal.durationHours === 'number'
                ? `${viewSessionModal.durationHours.toFixed(2)}h`
                : 'Todavía en curso'}
            </p>

            {viewSessionModal.objectives && (
              <div style={{ marginBottom: '0.75rem' }}>
                <h4
                  style={{
                    margin: 0,
                    marginBottom: '0.25rem',
                    fontSize: '0.9rem',
                  }}
                >
                  Objetivos de la sesión
                </h4>
                <p
                  style={{
                    margin: 0,
                    fontSize: '0.9rem',
                    color: '#111827',
                  }}
                >
                  {viewSessionModal.objectives}
                </p>
              </div>
            )}

            {viewSessionModal.notes && (
              <div style={{ marginBottom: '0.75rem' }}>
                <h4
                  style={{
                    margin: 0,
                    marginBottom: '0.25rem',
                    fontSize: '0.9rem',
                  }}
                >
                  Notas y sensaciones
                </h4>
                <p
                  style={{
                    margin: 0,
                    fontSize: '0.9rem',
                    color: '#111827',
                  }}
                >
                  {viewSessionModal.notes}
                </p>
              </div>
            )}

            <div style={modalActions}>
              <button
                type="button"
                style={secondaryBtn}
                onClick={() => setViewSessionModal(null)}
              >
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export default TaskDetailPage;
