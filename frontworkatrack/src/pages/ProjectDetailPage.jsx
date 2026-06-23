import { useState, useEffect } from 'react';
import { useParams, Link, useLocation } from 'react-router-dom';
import { apiFetch } from '../api/client';
import ProjectYearCalendar from '../components/ProjectYearCalendar';
import ProjectSummaryBox from '../components/ProjectSummaryBox';

/**

Detalle de un proyecto:

Carga tareas reales del backend (GET /me/tasks).

Considera que las tareas de este proyecto son las que tienen categoria === nombre del proyecto.

Permite:

· Crear tareas (POST /tasks)

· Editar tarea (PUT /tasks/:id) -> NO tocamos horas_estimadas

· Finalizar tarea (PUT /tasks/:id, estado="finalizada")

Hitos: de momento son locales (solo UI), se pintan en el calendario.
*/

function getTodayLocalISO() {
const today = new Date();
const y = today.getFullYear();
const m = String(today.getMonth() + 1).padStart(2, '0');
const d = String(today.getDate()).padStart(2, '0');
return String(y) + '-' + m + '-' + d;
}

function formatMinutes(totalMinutes) {
if (!totalMinutes || totalMinutes <= 0) return '0min';

const h = Math.floor(totalMinutes / 60);
const m = totalMinutes % 60;

if (h > 0 && m > 0) return String(h) + 'h ' + String(m) + 'min';
if (h > 0) return String(h) + 'h';
return String(m) + 'min';
}

function getRandomTaskColor() {
  const colors = [
    '#ef4444', // rojo
    '#f97316', // naranja
    '#eab308', // amarillo
    '#22c55e', // verde
    '#06b6d4', // cyan
    '#3b82f6', // azul
    '#6366f1', // indigo
    '#a855f7', // violeta
    '#ec4899', // rosa
  ];

  return colors[Math.floor(Math.random() * colors.length)];
}


function ProjectDetailPage() {
const { projectId } = useParams();
const location = useLocation();

const projectNameFromState = location.state?.projectName;
const projectColorFromState = location.state?.projectColor;

const [resolvedProjectName, setResolvedProjectName] = useState(projectNameFromState || '');
const [resolvedProjectColor, setResolvedProjectColor] = useState(projectColorFromState || '');
const [viewMode, setViewMode] = useState('default'); // 'default' | 'columns'


const projectName = resolvedProjectName || ('Proyecto #' + String(projectId));
const projectColor = resolvedProjectColor || '#2563eb';

// ===== Estado de tareas (backend) =====
const [tasks, setTasks] = useState([]); // solo tareas de este proyecto
const [expandedTasks, setExpandedTasks] = useState({});
const childrenMap = {};
tasks.forEach((t) => {
  const key = t.parent_task_id ? String(t.parent_task_id) : 'root';
  if (!childrenMap[key]) childrenMap[key] = [];
  childrenMap[key].push(t);
});

const rootTasks = childrenMap.root || [];

const getChildren = (taskId) => childrenMap[String(taskId)] || [];
const hasChildren = (taskId) => getChildren(taskId).length > 0;

// ===== Color por rama (root task) =====
const tasksById = {};
tasks.forEach((t) => {
  tasksById[String(t.id)] = t;
});

function getRootTask(task) {
  let cur = task;
  let guard = 0;

  while (cur && cur.parent_task_id && guard < 50) {
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


const toggleExpanded = (taskId) => {
  setExpandedTasks((prev) => ({
    ...prev,
    [taskId]: !prev[taskId],
  }));
};

const [loading, setLoading] = useState(false);
const [loadError, setLoadError] = useState('');

// ===== Resumen del proyecto (backend) =====
const [projectStats, setProjectStats] = useState(null);

// ===== Hitos (LOCAL por ahora) =====
const [milestones, setMilestones] = useState([]);

// ===== Modal crear tarea =====
const [createOpen, setCreateOpen] = useState(false);
const [newTitle, setNewTitle] = useState('');
const [newDescription, setNewDescription] = useState('');
const [newStartDate, setNewStartDate] = useState('');
const [newEndDate, setNewEndDate] = useState('');
const [newEstimatedHours, setNewEstimatedHours] = useState('');
const [newEstimatedMinutes, setNewEstimatedMinutes] = useState('');
const [createError, setCreateError] = useState('');

// ===== Modal editar tarea =====
const [editModal, setEditModal] = useState(null); // { taskId, titulo, descripcion, fecha_plan_inicio, fecha_plan_fin, estado }
const [editError, setEditError] = useState('');

// ===== Modal crear hito (LOCAL) =====
const [milestoneModalOpen, setMilestoneModalOpen] = useState(false);
const [milestoneName, setMilestoneName] = useState('');
const [milestoneDate, setMilestoneDate] = useState('');
const [milestoneDesc, setMilestoneDesc] = useState('');
const [milestoneError, setMilestoneError] = useState('');

// ===== Modal eliminar tarea =====
const [deleteModal, setDeleteModal] = useState(null); // { id, titulo }
const [deletePassword, setDeletePassword] = useState('');
const [deleteError, setDeleteError] = useState('');

// ===== Estilos de modales =====
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
...inputStyle,
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

// =====================================================
// CARGAR HITOS DESDE BACKEND (GET /projects/:id/milestones)
// =====================================================
async function loadMilestones() {
  try {
    const data = await apiFetch(`/projects/${projectId}/milestones`);

    if (!Array.isArray(data)) {
      throw new Error('Respuesta inesperada de hitos');
    }

    // Adaptamos al formato que ya usa tu UI
    const normalized = data.map((m) => ({
      id: m.id,
      name: m.titulo,
      date: m.fecha,
      description: m.descripcion,
      color: resolvedProjectColor || '#2563eb',
    }));

    setMilestones(normalized);
  } catch (err) {
    console.error('Error cargando hitos:', err);
    setMilestones([]);
  }
}



// =====================================================
// CARGAR TAREAS DESDE BACKEND (GET /me/tasks)
// =====================================================
async function loadTasks() {
setLoading(true);
setLoadError('');

try {
  const data = await apiFetch('/me/tasks/with-time');

  if (!Array.isArray(data)) {
    throw new Error('Respuesta inesperada de /me/tasks/with-time');
  }

  // Tareas de este proyecto: categoria === nombre del proyecto
  const projectTasks = data.filter((t) => {
  // Preferente: relación real por project_id
  if (t.project_id !== undefined && t.project_id !== null) {
    return Number(t.project_id) === Number(projectId);
  }

  // Fallback temporal: tareas antiguas sin project_id
  return t.categoria === projectName;
});

setTasks(projectTasks);

} catch (err) {
  console.error('Error cargando tareas:', err);
  setLoadError(err.message || 'Error cargando tareas');
  setTasks([]);
} finally {
  setLoading(false);
}


}

useEffect(() => {
  if (projectNameFromState && projectColorFromState) return;

  async function loadProjectMeta() {
    try {
      const project = await apiFetch('/projects/' + String(projectId));
      setResolvedProjectName(project.name);
      setResolvedProjectColor(project.color || '#2563eb');
    } catch (err) {
      console.error('Error cargando proyecto:', err);
    }
  }

  loadProjectMeta();
}, [projectId]);

useEffect(() => {
  loadMilestones();
  // eslint-disable-next-line react-hooks/exhaustive-deps
}, [projectId]);

useEffect(() => {
loadTasks();
// eslint-disable-next-line react-hooks/exhaustive-deps
}, [projectName]);

useEffect(() => {
  loadProjectStats();
}, [projectId, tasks]);

async function loadProjectStats() {
  try {
    const data = await apiFetch(`/projects/${projectId}/stats`);
    setProjectStats(data);
  } catch (err) {
    console.error('Error cargando estadísticas del proyecto:', err);
    setProjectStats(null);
  }
}


// =====================================================
// CREAR TAREA (POST /tasks)
// =====================================================
const openCreateModal = () => {
setCreateOpen(true);
setNewTitle('');
setNewDescription('');
setNewStartDate('');
setNewEndDate('');
setNewEstimatedHours('');
setCreateError('');
};

const closeCreateModal = () => {
setCreateOpen(false);
setNewTitle('');
setNewDescription('');
setNewStartDate('');
setNewEndDate('');
setNewEstimatedHours('');
setCreateError('');
};

const handleCreateTask = async () => {
const trimmed = newTitle.trim();
if (!trimmed) {
setCreateError('El título de la tarea es obligatorio.');
return;
}

if (newStartDate && newEndDate && newEndDate < newStartDate) {
  setCreateError('La fecha de fin no puede ser anterior a la de inicio.');
  return;
}

let minutosEstimados = null;
const horas = Number(newEstimatedHours) || 0;
const minutos = Number(newEstimatedMinutes) || 0;

if (horas < 0 || minutos < 0 || minutos > 59) {
  setCreateError('Tiempo estimado inválido.');
  return;
}

if (horas === 0 && minutos === 0) {
  minutosEstimados = null;
} else {
  minutosEstimados = horas * 60 + minutos;
}
const payload = {
  titulo: trimmed,
  descripcion: newDescription.trim() || null,
  categoria: projectName,
  project_id: Number(projectId),
  estado: 'pendiente',
  fecha_plan_inicio: newStartDate || null,
  fecha_plan_fin: newEndDate || null,
  minutos_estimados: minutosEstimados,
};

try {
  await apiFetch('/tasks', {
    method: 'POST',
    body: JSON.stringify(payload),
  });

  await loadTasks();
  closeCreateModal();
} catch (err) {
  console.error('Error creando tarea:', err);
  setCreateError(err.message || 'Error creando la tarea');
}


};

// =====================================================
// EDITAR TAREA (PUT /tasks/:id) -> NO tocamos horas_estimadas
// =====================================================
const openEditTaskModal = (task) => {
setEditModal({
taskId: task.id,
titulo: task.titulo || '',
descripcion: task.descripcion || '',
fecha_plan_inicio: task.fecha_plan_inicio || '',
fecha_plan_fin: task.fecha_plan_fin || '',
estado: task.estado || 'pendiente',
color: task.color || '#000000',
});
setEditError('');
};

const closeEditTaskModal = () => {
setEditModal(null);
setEditError('');
};

const confirmEditTask = async () => {
if (!editModal) return;

const trimmed = editModal.titulo.trim();
if (!trimmed) {
  setEditError('El título de la tarea no puede estar vacío.');
  return;
}

if (
  editModal.fecha_plan_inicio &&
  editModal.fecha_plan_fin &&
  editModal.fecha_plan_fin < editModal.fecha_plan_inicio
) {
  setEditError('La fecha de fin no puede ser anterior a la de inicio.');
  return;
}

const payload = {
  titulo: trimmed,
  descripcion: editModal.descripcion.trim() || null,
  estado: editModal.estado,
  fecha_plan_inicio: editModal.fecha_plan_inicio || null,
  fecha_plan_fin: editModal.fecha_plan_fin || null,
  color: editModal.color,
  // horas_estimadas: NO se toca aquí a propósito
};

try {
  await apiFetch('/tasks/' + String(editModal.taskId), {
    method: 'PUT',
    body: JSON.stringify(payload),
  });

  await loadTasks();
  closeEditTaskModal();
} catch (err) {
  console.error('Error editando tarea:', err);
  setEditError(err.message || 'Error editando la tarea');
}


};

const finalizeTask = async (taskId) => {
try {
await apiFetch(`/tasks/${taskId}/status`, {
method: 'PUT',
body: JSON.stringify({ estado: 'finalizada' }),
});
await loadTasks();
} catch (err) {
console.error('Error finalizando tarea:', err);
alert(err.message || 'Error finalizando la tarea');
}
};

const confirmDeleteTask = async () => {
if (!deleteModal) return;

if (!deletePassword.trim()) {
  setDeleteError('Introduce la contraseña del proyecto.');
  return;
}

try {
  await apiFetch('/tasks/' + String(deleteModal.id), { method: 'DELETE', body: JSON.stringify({ password: deletePassword.trim(), }),  });
  await loadTasks();
  setDeleteModal(null);
  setDeletePassword('');
  setDeleteError('');
} catch (err) {
  setDeleteError(err.message || 'Error eliminando la tarea');
}


};

// =====================================================
// CREAR HITO (LOCAL) - solo UI
// =====================================================
const openMilestoneModal = () => {
setMilestoneModalOpen(true);
setMilestoneName('');
setMilestoneDate('');
setMilestoneDesc('');
setMilestoneError('');
};

const closeMilestoneModal = () => {
setMilestoneModalOpen(false);
setMilestoneName('');
setMilestoneDate('');
setMilestoneDesc('');
setMilestoneError('');
};

const confirmCreateMilestone = async () => {
  const name = milestoneName.trim();
  if (!name) {
    setMilestoneError('El hito necesita un nombre.');
    return;
  }
  if (!milestoneDate) {
    setMilestoneError('Selecciona una fecha para el hito.');
    return;
  }

  try {
    await apiFetch(`/projects/${projectId}/milestones`, {
      method: 'POST',
      body: JSON.stringify({
        titulo: name,
        fecha: milestoneDate,
        descripcion: milestoneDesc.trim() || null,
        color: projectColor,
      }),
    });

    await loadMilestones();
    closeMilestoneModal();
  } catch (err) {
    console.error('Error creando hito:', err);
    setMilestoneError(err?.message ||'Error creando el hito');
  }
};

function buildCalendarEvents({
  projectId,
  projectName,
  projectColor,
  tasks,
  milestones,
}) {
  const events = [];

  // 1. Tareas
  tasks.forEach((t) => {
   const taskColor = getBranchColor(t);

    if (t.fecha_plan_inicio) {
      events.push({
        id: `task-${t.id}-start`,
        name: `Inicio tarea: ${t.titulo}`,
        createdAt: t.fecha_plan_inicio,
        shape: 'circle',
        color: taskColor,
        type: 'task-start',
      });
    }

    if (t.fecha_plan_fin) {
      events.push({
        id: `task-${t.id}-end`,
        name: `Fin tarea: ${t.titulo}`,
        createdAt: t.fecha_plan_fin,
        shape: 'triangle',
        color: taskColor,
        type: 'task-end',
      });
    }
  });

  // 2. Hitos
  milestones.forEach((m) => {
    events.push({
      id: `milestone-${m.id}`,
      name: `Hito: ${m.name}`,
      createdAt: m.date,
      shape: 'square',
      color: m.color || projectColor,
      type: 'milestone',
    });
  });

  return events;
}


// =====================================================
// DATOS PARA EL CALENDARIO
// =====================================================
const calendarItems = buildCalendarEvents({
  projectId,
  projectName,
  projectColor,
  tasks,
  milestones,
});

// =====================================================
// RENDER
// =====================================================
return (
  <>
    <div
      className="projects-layout"
      style={
        viewMode === 'columns'
          ? { gridTemplateColumns: '1fr' }
          : undefined
      }
    >
      {/* Columna izquierda: listado de tareas */}
      <div className="projects-list-panel" style={viewMode === 'columns' ? { width: '100%', maxWidth: 'none' } : undefined}>
        <div className="projects-header">
          <div>
            <h2>Proyecto: {projectName}</h2>
            <p className="projects-subtitle">
              Aquí verás las tareas asociadas a este proyecto y podrás abrir sus sesiones de trabajo.
            </p>
          </div>

          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            {/* Toggle vista */}
            <button
              type="button"
              className="create-project-btn"
              onClick={() => setViewMode((v) => (v === 'default' ? 'columns' : 'default'))}
              title={
                viewMode === 'default'
                  ? 'Cambiar a vista por columnas'
                  : 'Cambiar a vista calendario'
              }
              style={{
                padding: '0.35rem 0.6rem',
                fontSize: '0.85rem',
              }}
            >
              {viewMode === 'default' ? '▦' : '📅'}
            </button>

            {/* Botones existentes */}
            <button type="button" className="create-project-btn" onClick={openCreateModal}>
              + Crear tarea
            </button>

            <button type="button" className="create-project-btn" onClick={openMilestoneModal}>
              + Crear hito
            </button>
          </div>
        </div>

        {loading && (
          <div className="project-card">
            <p style={{ margin: 0, fontSize: '0.9rem', color: '#6b7280' }}>
              Cargando tareas…
            </p>
          </div>
        )}

        {loadError && !loading && (
          <div className="project-card">
            <p style={{ margin: 0, fontSize: '0.9rem', color: '#b91c1c' }}>
              Error al cargar tareas: {loadError}
            </p>
          </div>
        )}

        {!loading && !loadError && rootTasks.length === 0 && (
          <div className="project-card">
            <p style={{ margin: 0, fontSize: '0.9rem', color: '#6b7280' }}>
              Todavía no hay tareas registradas para este proyecto. Crea la primera con el botón &quot;Crear tarea&quot;.
            </p>
          </div>
        )}

        {/* ===== Vista default (lista) ===== */}
        {viewMode === 'default' && (
          <div className="projects-list">
            {rootTasks.map((task) => {
              const spentMinutes = typeof task.minutos_reales === 'number' ? task.minutos_reales : 0;
              const estimatedMinutes = typeof task.minutos_estimados === 'number' ? task.minutos_estimados : 0;

              const progressPercent =
                estimatedMinutes > 0 ? Math.min(100, (spentMinutes / estimatedMinutes) * 100) : 0;

              const isFinalized = String(task.estado || '').toLowerCase() === 'finalizada';

              const renderTaskNode = (task, level = 0) => {
                const spentMinutes = typeof task.minutos_reales === 'number' ? task.minutos_reales : 0;
                const estimatedMinutes = typeof task.minutos_estimados === 'number' ? task.minutos_estimados : 0;

                const progressPercent =
                  estimatedMinutes > 0 ? Math.min(100, (spentMinutes / estimatedMinutes) * 100) : 0;

                const isFinalized = String(task.estado || '').toLowerCase() === 'finalizada';

                const taskHasChildren = hasChildren(task.id);
                const isExpanded = !!expandedTasks[task.id];
                const indentPx = level * 18;

                const branchColor = getBranchColor(task);

                return (
                  <div key={task.id} style={{ marginLeft: String(indentPx) + 'px' }}>
                    <div
                      className="project-card"
                      style={{
                        borderLeft:
                          '4px solid ' + branchColor,
                        position: 'relative',
                      }}
                    >
                      <button
                        type="button"
                        className="create-project-btn"
                        style={{
                          position: 'absolute',
                          top: '0.75rem',
                          right: '0.75rem',
                        }}
                        onClick={() => setDeleteModal({ id: task.id, titulo: task.titulo })}
                      >
                        Eliminar
                      </button>

                      <div className="project-card-header">
                        <div className="project-title-row" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          {taskHasChildren && (
                            <button
                              type="button"
                              onClick={() => toggleExpanded(task.id)}
                              title={isExpanded ? 'Ocultar subtareas' : 'Mostrar subtareas'}
                              style={{
                                width: '1.6rem',
                                height: '1.6rem',
                                borderRadius: '999px',
                                border: '1px solid #d1d5db',
                                background: '#fff',
                                cursor: 'pointer',
                                display: 'inline-flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                fontSize: '0.85rem',
                                lineHeight: 1,
                              }}
                            >
                              {isExpanded ? '▾' : '▸'}
                            </button>
                          )}

                          <h3 style={{ margin: 0 }}>{task.titulo}</h3>

                          <span
                            className="project-color-dot"
                            style={{
                              marginLeft: 'auto',
                              backgroundColor: branchColor,
                            }}
                          />
                        </div>

                        <span className="project-created">Estado: {task.estado || 'pendiente'}</span>
                      </div>
              
                      <div className="project-progress-bar">
                        <div
                          className="project-progress-bar-fill"
                          style={{
                            width: String(progressPercent) + '%',
                            backgroundColor: branchColor,
                          }}
                        />
                      </div>
              
                      <p className="project-progress-label">
                        {formatMinutes(spentMinutes)} / {estimatedMinutes ? formatMinutes(estimatedMinutes) : '—'}
                      </p>
              
                      {task.descripcion && (
                        <p
                          style={{
                            marginTop: 0,
                            marginBottom: '0.25rem',
                            fontSize: '0.9rem',
                            color: '#4b5563',
                          }}
                        >
                          {task.descripcion}
                        </p>
                      )}
              
                      <div
                        style={{
                          fontSize: '0.8rem',
                          color: '#6b7280',
                          marginBottom: '0.5rem',
                        }}
                      >
                        {task.fecha_plan_inicio && (
                          <>
                            Inicio previsto: {task.fecha_plan_inicio}
                            {' · '}
                          </>
                        )}
                        {task.fecha_plan_fin && <>Fin previsto: {task.fecha_plan_fin}</>}
                        {estimatedMinutes > 0 ? (
                          <>
                            {' · '}
                            Estimación: {formatMinutes(estimatedMinutes)}
                          </>
                        ) : null}
                      </div>
              
                      <div className="project-card-footer">
                        <div className="project-footer-left">
                          <Link
                            to={'/projects/' + String(projectId) + '/tasks/' + String(task.id)}
                            state={{
                              taskName: task.titulo,
                              taskColor: branchColor,
                              milestones,
                              projectName,
                              projectColor,
                            }}
                            className="project-link"
                          >
                            Ver sesiones
                          </Link>
                          <span
                            style={{
                              fontSize: '0.8rem',
                              color:
                                task.estado === 'finalizada'
                                  ? '#16a34a'
                                  : task.estado === 'en_pausa'
                                  ? '#f59e0b'
                                  : task.estado === 'pendiente'
                                  ? '#6b7280'
                                  : '#2563eb',
                              marginLeft: '0.5rem',
                            }}
                          >
                            {task.estado === 'finalizada'
                              ? 'Finalizada'
                              : task.estado === 'en_pausa'
                              ? 'En pausa'
                              : task.estado === 'pendiente'
                              ? 'Pendiente'
                              : 'En progreso'}
                          </span>
                        </div>
              
                        <div className="project-footer-right" style={{ gap: '0.4rem' }}>
                          <button
                            type="button"
                            className="project-color-picker-label"
                            onClick={() => openEditTaskModal(task)}
                          >
                            Editar tarea
                          </button>
              
                          <button
                            type="button"
                            className="delete-project-btn"
                            disabled={isFinalized}
                            onClick={() => finalizeTask(task.id)}
                          >
                            Finalizar tarea
                          </button>
                        </div>
                      </div>
                    </div>
              
                    {taskHasChildren && isExpanded && (
                      <div style={{ marginTop: '0.5rem' }}>
                        {getChildren(task.id).map((child) => renderTaskNode(child, level + 1))}
                      </div>
                    )}
                  </div>
                );
              };
  

              return renderTaskNode(task, 0);
            })}
          </div>
        )}              

        {/* ===== Vista columns (columnas) ===== */}
        {viewMode === 'columns' && (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(4, minmax(0, 1fr))',
              gap: '1rem',
              marginTop: '0.5rem',
            }}
          >
            {[
              { key: 'en_progreso', label: 'En progreso' },
              { key: 'en_pausa', label: 'En pausa' },
              { key: 'pendiente', label: 'Pendientes' },
              { key: 'finalizada', label: 'Finalizadas' },
            ].map((col) => {
             const colTasks = rootTasks.filter((t) => t.estado === col.key);

             const renderColumnTaskNode = (task, level = 0) => {
               const spentMinutes = typeof task.minutos_reales === 'number' ? task.minutos_reales : 0;
               const estimatedMinutes = typeof task.minutos_estimados === 'number' ? task.minutos_estimados : 0;

               const progressPercent =
                 estimatedMinutes > 0 ? Math.min(100, (spentMinutes / estimatedMinutes) * 100) : 0;

               const isFinalized = String(task.estado || '').toLowerCase() === 'finalizada';

               const taskHasChildren = hasChildren(task.id);
               const isExpanded = !!expandedTasks[task.id];
               const indentPx = level * 18;
               const branchColor = getBranchColor(task);

               return (
                 <div key={task.id} style={{ marginLeft: String(indentPx) + 'px' }}>
                   <div
                     className="project-card"
                     style={{
                       borderLeft:
                         '4px solid ' + branchColor,
                       position: 'relative',
                       marginBottom: '0.75rem',
                     }}
                   >
                     <button
                       type="button"
                       className="create-project-btn"
                       style={{
                         position: 'absolute',
                         top: '0.75rem',
                         right: '0.75rem',
                       }}
                       onClick={() => setDeleteModal({ id: task.id, titulo: task.titulo })}
                     >
                       Eliminar
                     </button>

                     <div className="project-card-header">
                       <div
                         className="project-title-row"
                         style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
                       >
                         {taskHasChildren && (
                           <button
                             type="button"
                             onClick={() => toggleExpanded(task.id)}
                             title={isExpanded ? 'Ocultar subtareas' : 'Mostrar subtareas'}
                             style={{
                               width: '1.6rem',
                               height: '1.6rem',
                               borderRadius: '999px',
                               border: '1px solid #d1d5db',
                               background: '#fff',
                               cursor: 'pointer',
                               display: 'inline-flex',
                               alignItems: 'center',
                               justifyContent: 'center',
                               fontSize: '0.85rem',
                               lineHeight: 1,
                             }}
                           >
                             {isExpanded ? '▾' : '▸'}
                           </button>
                         )}

                         <h3 style={{ margin: 0 }}>{task.titulo}</h3>

                         <span
                           className="project-color-dot"
                           style={{
                             marginLeft: 'auto',
                             backgroundColor: branchColor,
                           }}
                         />
                       </div>
                       <span className="project-created">Estado: {task.estado || 'pendiente'}</span>
                     </div>

                     <div className="project-progress-bar">
                       <div
                         className="project-progress-bar-fill"
                         style={{
                           width: String(progressPercent) + '%',
                           backgroundColor: branchColor,
                         }}
                       />
                     </div>

                     <p className="project-progress-label">
                       {formatMinutes(spentMinutes)} / {estimatedMinutes ? formatMinutes(estimatedMinutes) : '—'}
                     </p>

                     {task.descripcion && (
                       <p
                         style={{
                           marginTop: 0,
                           marginBottom: '0.25rem',
                           fontSize: '0.9rem',
                           color: '#4b5563',
                         }}
                       >
                         {task.descripcion}
                       </p>
                     )}

                     <div
                       style={{
                         fontSize: '0.8rem',
                         color: '#6b7280',
                         marginBottom: '0.5rem',
                       }}
                     >
                       {task.fecha_plan_inicio && (
                         <>
                           Inicio previsto: {task.fecha_plan_inicio}
                           {' · '}
                         </>
                       )}
                       {task.fecha_plan_fin && <>Fin previsto: {task.fecha_plan_fin}</>}
                       {estimatedMinutes > 0 ? (
                         <>
                           {' · '}
                           Estimación: {formatMinutes(estimatedMinutes)}
                         </>
                       ) : null}
                     </div>

                     <div className="project-card-footer">
                       <div className="project-footer-left">
                         <Link
                           to={'/projects/' + String(projectId) + '/tasks/' + String(task.id)}
                           state={{
                             taskName: task.titulo,
                             taskColor: branchColor,
                             milestones,
                             projectName,
                             projectColor,
                           }}
                           className="project-link"
                         >
                           Ver sesiones
                         </Link>
                         <span
                           style={{
                             fontSize: '0.8rem',
                             color:
                               task.estado === 'finalizada'
                                 ? '#16a34a'
                                 : task.estado === 'en_pausa'
                                 ? '#f59e0b'
                                 : task.estado === 'pendiente'
                                 ? '#6b7280'
                                 : '#2563eb',
                             marginLeft: '0.5rem',
                           }}
                         >
                           {task.estado === 'finalizada'
                             ? 'Finalizada'
                             : task.estado === 'en_pausa'
                             ? 'En pausa'
                             : task.estado === 'pendiente'
                             ? 'Pendiente'
                             : 'En progreso'}
                         </span>
                       </div>
                        <div className="project-footer-right" style={{ gap: '0.4rem' }}>
                         <button
                           type="button"
                           className="project-color-picker-label"
                           onClick={() => openEditTaskModal(task)}
                         >
                           Editar tarea
                         </button>

                         <button
                           type="button"
                           className="delete-project-btn"
                           disabled={isFinalized}
                           onClick={() => finalizeTask(task.id)}
                         >
                           Finalizar tarea
                         </button>
                       </div>
                     </div>
                   </div>

                   {taskHasChildren && isExpanded && (
                     <div style={{ marginTop: '0.5rem' }}>
                       {getChildren(task.id).map((child) => renderColumnTaskNode(child, level + 1))}
                     </div>
                   )}
                 </div>
               );
             };

              return (
                 <div
                  key={col.key}
                  style={{
                    backgroundColor: '#f9fafb',
                    borderRadius: '0.75rem',
                    padding: '0.75rem',
                    border: '1px solid #e5e7eb',
                    minHeight: '8rem',
                  }}
                >
                  <h4
                    style={{
                      marginTop: 0,
                      marginBottom: '0.75rem',
                      fontSize: '0.9rem',
                      color: '#374151',
                      textAlign: 'center',
                    }}
                  >
                    {col.label}
                  </h4>

                  {colTasks.map((task) => {
                    return renderColumnTaskNode(task, 0);
                  })}

                  {colTasks.length === 0 && (
                    <p
                      style={{
                        fontSize: '0.8rem',
                        color: '#9ca3af',
                        textAlign: 'center',
                        margin: 0,
                      }}
                    >
                      Sin tareas
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        )}

        <p style={{ marginTop: '1rem' }}>
          <Link to="/projects">← Volver a todos los proyectos</Link>
        </p>
      </div>

      {/* Columna derecha: calendario del proyecto (SOLO en vista default) */}
      {viewMode === 'default' && (
        <div className="projects-calendar-panel">
          <h3>Calendario del proyecto</h3>
          <p
            style={{
              fontSize: '0.8rem',
              color: '#6b7280',
              marginTop: 0,
              marginBottom: '0.5rem',
            }}
          >
            Círculos → tareas de este proyecto.&nbsp;
            Cuadrados → hitos principales.
          </p>
          <ProjectYearCalendar projects={calendarItems} />
          <ProjectSummaryBox stats={projectStats} />
        </div>
      )}
    </div>

    {/* MODAL CREAR TAREA */}
    {createOpen && (
      <div style={overlayStyle}>
        <div style={modalStyle}>
          <h3>Crear nueva tarea en {projectName}</h3>

          <label style={{ fontSize: '0.85rem' }}>Título de la tarea</label>
          <input
            type="text"
            style={inputStyle}
            placeholder="Ej: Revisar bibliografía"
            value={newTitle}
            onChange={(e) => {
              setNewTitle(e.target.value);
              setCreateError('');
            }}
          />

          <label style={{ fontSize: '0.85rem' }}>Descripción (opcional)</label>
          <textarea
            style={textAreaStyle}
            rows={2}
            placeholder="Breve descripción de la tarea..."
            value={newDescription}
            onChange={(e) => setNewDescription(e.target.value)}
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
                value={newStartDate}
                onChange={(e) => setNewStartDate(e.target.value)}
              />
            </div>
            <div>
              <label style={{ fontSize: '0.85rem' }}>Fin previsto</label>
              <input
                type="date"
                style={inputStyle}
                value={newEndDate}
                onChange={(e) => setNewEndDate(e.target.value)}
              />
            </div>
          </div>

          <label style={{ fontSize: '0.85rem' }}>Tiempo estimado (opcional)</label>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: '0.75rem',
            }}
          >
            <input
              type="number"
              min="0"
              step="0.5"
              style={inputStyle}
              placeholder="Ej: 4"
              value={newEstimatedHours}
              onChange={(e) => {
                setNewEstimatedHours(e.target.value);
                setCreateError('');
              }}
            />

            <input
              type="number"
              min="0"
              max="59"
              step="1"
              style={inputStyle}
              placeholder="Minutos"
              value={newEstimatedMinutes}
              onChange={(e) => {
                setNewEstimatedMinutes(e.target.value);
                setCreateError('');
              }}
            />
          </div>

          {createError && <div style={errorText}>{createError}</div>}

          <div style={modalActions}>
            <button type="button" style={secondaryBtn} onClick={closeCreateModal}>
              Cancelar
            </button>
            <button type="button" style={primaryBtn} onClick={handleCreateTask}>
              Crear tarea
            </button>
          </div>
        </div>
      </div>
    )}

    {/* MODAL EDITAR TAREA */}
    {editModal && (
      <div style={overlayStyle}>
        <div style={modalStyle}>
          <h3>Editar tarea</h3>

          <label style={{ fontSize: '0.85rem' }}>Título</label>
          <input
            type="text"
            style={inputStyle}
            value={editModal.titulo}
            onChange={(e) => {
              setEditModal((prev) => (prev ? { ...prev, titulo: e.target.value } : prev));
              setEditError('');
            }}
          />

          <label style={{ fontSize: '0.85rem' }}>Descripción (opcional)</label>
          <textarea
            style={textAreaStyle}
            rows={2}
            value={editModal.descripcion}
            onChange={(e) =>
              setEditModal((prev) => (prev ? { ...prev, descripcion: e.target.value } : prev))
            }
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
                value={editModal.fecha_plan_inicio || ''}
                onChange={(e) => {
                  setEditModal((prev) => (prev ? { ...prev, fecha_plan_inicio: e.target.value } : prev));
                  setEditError('');
                }}
              />
            </div>
            <div>
              <label style={{ fontSize: '0.85rem' }}>Fin previsto</label>
              <input
                type="date"
                style={inputStyle}
                value={editModal.fecha_plan_fin || ''}
                onChange={(e) => {
                  setEditModal((prev) => (prev ? { ...prev, fecha_plan_fin: e.target.value } : prev));
                  setEditError('');
                }}
              />
            </div>
          </div>

          <label style={{ fontSize: '0.85rem' }}>Estado</label>
          <select
            style={inputStyle}
            value={editModal.estado}
            onChange={(e) => setEditModal((prev) => (prev ? { ...prev, estado: e.target.value } : prev))}
          >
            <option value="pendiente">Pendiente</option>
            <option value="en_progreso">En progreso</option>
            <option value="en_pausa">En pausa</option>
            <option value="finalizada">Finalizada</option>
          </select>

          <label style={{ fontSize: '0.85rem', marginTop: '0.75rem' }}>
            Color de la tarea
          </label>

          <input
            type="color"
            value={editModal.color || '#000000'}
            onChange={(e) =>
              setEditModal((prev) =>
                prev ? { ...prev, color: e.target.value } : prev
              )
            }
            style={{
              width: '3rem',
              height: '2rem',
              padding: 0,
              border: 'none',
              background: 'none',
              cursor: 'pointer',
              marginBottom: '0.75rem',
            }}
          />

          <p style={{ margin: 0, fontSize: '0.8rem', color: '#6b7280' }}>
            Nota: aquí no se editan las horas estimadas (se mantienen como las planificaste).
          </p>

          {editError && <div style={errorText}>{editError}</div>}

          <div style={modalActions}>
            <button type="button" style={secondaryBtn} onClick={closeEditTaskModal}>
              Cancelar
            </button>
            <button type="button" style={primaryBtn} onClick={confirmEditTask}>
              Guardar cambios
            </button>
          </div>
        </div>
      </div>
    )}

    {/* MODAL ELIMINAR TAREA */}
    {deleteModal && (
      <div style={overlayStyle}>
        <div style={modalStyle}>
          <h3>Eliminar tarea</h3>

          <p style={{ fontSize: '0.9rem', color: '#374151' }}>
            Vas a eliminar la tarea <strong>{deleteModal.titulo}</strong>.
            Esta acción no se puede deshacer.
          </p>

          <label style={{ fontSize: '0.85rem' }}>Contraseña del proyecto</label>
          <input
            type="password"
            style={inputStyle}
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
                setDeleteModal(null);
                setDeletePassword('');
                setDeleteError('');
              }}
            >
              Cancelar
            </button>

            <button type="button" style={dangerBtn} onClick={confirmDeleteTask}>
              Eliminar definitivamente
            </button>
          </div>
        </div>
      </div>
    )}

    {/* MODAL CREAR HITO (LOCAL) */}
    {milestoneModalOpen && (
      <div style={overlayStyle}>
        <div style={modalStyle}>
          <h3>Crear hito en {projectName}</h3>

          <label style={{ fontSize: '0.85rem' }}>Nombre del hito</label>
          <input
            type="text"
            style={inputStyle}
            placeholder="Ej: Entrega MVP"
            value={milestoneName}
            onChange={(e) => {
              setMilestoneName(e.target.value);
              setMilestoneError('');
            }}
          />

          <label style={{ fontSize: '0.85rem' }}>Fecha del hito</label>
          <input
            type="date"
            style={inputStyle}
            value={milestoneDate}
            onChange={(e) => {
              setMilestoneDate(e.target.value);
              setMilestoneError('');
            }}
          />

          <label style={{ fontSize: '0.85rem' }}>Descripción (opcional)</label>
          <textarea
            style={textAreaStyle}
            rows={2}
            value={milestoneDesc}
            onChange={(e) => setMilestoneDesc(e.target.value)}
          />

          {milestoneError && <div style={errorText}>{milestoneError}</div>}

          <div style={modalActions}>
            <button type="button" style={secondaryBtn} onClick={closeMilestoneModal}>
              Cancelar
            </button>
            <button type="button" style={primaryBtn} onClick={confirmCreateMilestone}>
              Crear hito
            </button>
          </div>
        </div>
      </div>
    )}
  </>
);
};

export default ProjectDetailPage;
