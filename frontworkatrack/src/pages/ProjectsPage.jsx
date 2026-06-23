import { createPortal } from 'react-dom';
import { useState, useMemo, useEffect } from 'react';
import { Link } from 'react-router-dom';
import ProjectYearCalendar from '../components/ProjectYearCalendar';
import { apiFetch } from '../api/client';

/**
 * Paleta de colores para nuevos proyectos.
 */
const colorPalette = [
  '#1f2937',
  '#2563eb',
  '#f97316',
  '#16a34a',
  '#7c3aed',
  '#db2777',
];

function buildProjectSearch(project) {
  const params = new URLSearchParams();

  if (project?.name) params.set('name', project.name);
  if (project?.color) params.set('color', project.color);
  if (typeof project?.progress === 'number') {
    params.set('progress', String(project.progress));
  }

  const s = params.toString();
  return s ? `?${s}` : '';
}

/* =========================
   STATS (FUERA, CORRECTO)
========================= */
async function loadProjectStats(projectId) {
  try {
    return await apiFetch(`/projects/${projectId}/stats`);
  } catch (err) {
    console.error(`Error cargando stats del proyecto ${projectId}`, err);
    return null;
  }
}

function formatMinutes(mins) {
  if (!mins || mins <= 0) return '0h';
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return m > 0 ? `${h}h ${m}min` : `${h}h`;
}

// ===== Estilos de modales (copiados de ProjectDetailPage) =====
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


function ProjectsPage() {
  const [projects, setProjects] = useState([]);

  /* =========================
     LOAD PROJECTS (ARREGLADO)
  ========================= */
  async function loadProjects() {
    try {
      const data = await apiFetch('/projects');
      if (!Array.isArray(data)) return;

      const normalized = await Promise.all(
        data.map(async (p) => {
          const stats = await loadProjectStats(p.id);
          console.log('STATS proyecto', p.id, stats);     

      const minutosEstimados =
        typeof p.minutos_estimados === 'number'
          ? Number(p.minutos_estimados)
          : null;


      const minutosReales =
        typeof stats?.minutos_reales === 'number'
          ? stats.minutos_reales
          : undefined;

      const progress =
        minutosEstimados && minutosEstimados > 0
          ? Math.min(100, (minutosReales / minutosEstimados) * 100)
          : 0;


          return {
            id: p.id,
            name: p.name,
            description: p.description,
            priority: p.priority,
            category: p.category,
            fecha_inicio: p.fecha_inicio || null,
            fecha_fin_prevista: p.fecha_fin_prevista || null,
            progress,
            minutos_estimados: minutosEstimados,
            minutos_reales: minutosReales,
            color: p.color || '#2563eb',
            milestones: (p.milestones || []).map((m) => ({
              id: m.id,
              name: m.titulo,
              date: m.fecha,
              color: p.color,
            })),
          };
        })
      );

      setProjects(normalized);
    } catch (err) {
      console.error('Error cargando proyectos:', err);
    }
  }

  useEffect(() => {
    loadProjects();
  }, []);

  /* =========================
     MODAL CREAR PROYECTO
  ========================= */
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [createName, setCreateName] = useState('');
  const [createDescription, setCreateDescription] = useState('');
  const [createPriority, setCreatePriority] = useState('media');
  const [createCategory, setCreateCategory] = useState('');
  const [createError, setCreateError] = useState('');
  const [createPassword, setCreatePassword] = useState('');
  const [createStartDate, setCreateStartDate] = useState('');
  const [createEndDate, setCreateEndDate] = useState('');
  const [createEstimatedHours, setCreateEstimatedHours] = useState('');
  const [createEstimatedMinutes, setCreateEstimatedMinutes] = useState('');


  const openCreateModal = () => {
    setCreateModalOpen(true);
    setCreateName('');
    setCreateDescription('');
    setCreatePriority('media');
    setCreateCategory('');
    setCreatePassword('');
    setCreateStartDate('');
    setCreateEndDate('');
    setCreateEstimatedHours('');
    setCreateEstimatedMinutes('');
    setCreateError('');
  };

  const confirmCreateProject = async () => {
    const trimmed = createName.trim();
    if (!trimmed) {
      setCreateError('El nombre del proyecto no puede estar vacío.');
      return;
    }

    if (!createPassword.trim()) {
      setCreateError('La contraseña del proyecto es obligatoria.');
      return;
    }

    if (createStartDate && createEndDate && createEndDate < createStartDate) {
      setCreateError('La fecha de fin no puede ser anterior a la de inicio.');
      return;
    }

    const h = Number(createEstimatedHours) || 0;
    const m = Number(createEstimatedMinutes) || 0;

    if (h < 0 || m < 0 || m > 59) {
      setCreateError('Estimación de tiempo inválida.');
      return;
    }

    const minutosEstimadosProyecto =
      h === 0 && m === 0 ? null : h * 60 + m;


    const randomColor =
      colorPalette[Math.floor(Math.random() * colorPalette.length)];

    try {
      await apiFetch('/projects', {
        method: 'POST',
        body: JSON.stringify({
          name: trimmed,
          description: createDescription.trim(),
          priority: createPriority,
          category: createCategory.trim(),
          color: randomColor,
          password: createPassword.trim(),
          minutos_estimados: minutosEstimadosProyecto,
          fecha_inicio: createStartDate || null,
          fecha_fin_prevista: createEndDate || null,
        }),
      });

      await loadProjects();
      setCreateModalOpen(false);
    } catch {
      setCreateError('Error creando el proyecto.');
    }
  };

  /* =========================
     EDITAR / BORRAR
  ========================= */
  const [editModal, setEditModal] = useState(null);
  const [editError, setEditError] = useState('');
  const [deleteModal, setDeleteModal] = useState(null);
  const [deletePassword, setDeletePassword] = useState('');
  const [deleteError, setDeleteError] = useState('');

  const openEditModal = (project) => {
    setEditModal({
      id: project.id,
      name: project.name || '',
      description: project.description || '',
      priority: project.priority || 'media',
      category: project.category || '',
      color: project.color || '#2563eb',
    });
    setEditError(''); 
  };

  const openDeleteModal = (project) => {
    setDeleteModal({
      projectId: project.id,
      projectName: project.name,
    });
    setDeletePassword('');
    setDeleteError('');
  };


  const confirmEditProject = async () => {
    if (!editModal.name.trim()) {
      setEditError('El nombre del proyecto no puede estar vacío.');
      return;
    }

    if (
      editModal.fecha_inicio &&
      editModal.fecha_fin_prevista &&
      editModal.fecha_fin_prevista < editModal.fecha_inicio
    ) {
      setEditError('La fecha de fin no puede ser anterior a la de inicio.');
      return;
    }

    try {
      await apiFetch(`/projects/${editModal.id}`, {
        method: 'PUT',
        body: JSON.stringify({
          name: editModal.name,
          description: editModal.description,
          priority: editModal.priority,
          category: editModal.category,
          color: editModal.color,
        }),
      });

      await loadProjects();
      setEditModal(null);
    } catch (err) {
      console.error('Error actualizando el proyecto:', err);
      alert('Error actualizando el proyecto:',err);
    }
  };

  const confirmDeleteProject = async () => {
    if (!deletePassword.trim()) {
      setDeleteError('Introduce tu contraseña.');
      return;
    }

    try {
      await apiFetch(`/projects/${deleteModal.projectId}`, {
        method: 'DELETE',
        body: JSON.stringify({
          password: deletePassword.trim(), 
        }),
      });
      await loadProjects();
      setDeleteModal(null);
      setDeletePassword('');
      setDeleteError('');
    } catch (err) {
      setDeleteError(err.message || 'Contraseña incorrecta o error eliminando el proyecto');
    }
  };

  /* =========================
     CALENDARIO
  ========================= */
  const calendarItems = useMemo(() => {
    const items = [];
    projects.forEach((project) => {
    if (project.fecha_inicio) {
      items.push({
        id: `project-${project.id}-start`,
        name: `Inicio: ${project.name}`,
        createdAt: project.fecha_inicio,
        shape: 'circle',
        progress: project.progress,
        color: project.color,
        type: 'project-start',
      });
    }
    if (project.fecha_fin_prevista) {
      items.push({
        id: `project-${project.id}-end`,
        name: `Fin: ${project.name}`,
        createdAt: project.fecha_fin_prevista,
        shape: 'triangle',
        progress: project.progress,
        color: project.color,
        type: 'project-end',
      });
    }


      project.milestones.forEach((m) => {
        items.push({
          id: `p-${project.id}-m-${m.id}`,
          name: `Hito: ${m.name}`,
          createdAt: m.date,
          progress: 0,
          shape: 'square',
          color: project.color,
          type: 'milestone',
        });
      });
    });
    return items;
  }, [projects]);

  /* =========================
     RENDER
  ========================= */
  console.log('ProjectsPage render');
  return (
    <>
      <div className="projects-layout">
        <div className="projects-list-panel">
          <div className="projects-header">
            <div>
              <h2>Mis proyectos</h2>
              <p className="projects-subtitle">
                Aquí verás tu lista de proyectos y un calendario global.
              </p>
            </div>

            <button className="create-project-btn" onClick={openCreateModal}>
              + Crear proyecto
            </button>
          </div>

          <div className="projects-list">
            {projects.map((project) => (
              <div key={project.id} className="project-card">
                <div className="project-card-header">
                  <div className="project-title-row">
                    <h3>{project.name}</h3>
                    <span
                      className="project-color-dot"
                      style={{ backgroundColor: project.color }}
                    />
                  </div>
                </div>

                <div className="project-progress">
                  <div className="project-progress-bar">
                    <div
                      className="project-progress-bar-fill"
                      style={{ width: typeof project.minutos_estimados === 'number' && project.minutos_estimados > 0 ? `${project.progress}%` : '0%', }}
                    />
                  </div>
                  <span>
                    Progreso:{' '}
                    {typeof project.minutos_estimados === 'number' && project.minutos_estimados > 0
                      ? `${Math.round(project.progress)}%`
                      : '—'}
                  </span>
 

                  {project.minutos_estimados != null && (
                    <div
                      style={{
                        fontSize: '0.8rem',
                        color: '#6b7280',
                        marginTop: '0.15rem',
                      }}
                     >
                      {formatMinutes(project.minutos_reales)} reales /{' '}
                      {formatMinutes(project.minutos_estimados)} estimadas (tareas)
                    </div>
                  )}

                </div>

                <div className="project-card-footer">
                  <div>
                    <Link
                      to={{
                        pathname: `/projects/${project.id}`,
                        search: buildProjectSearch(project),
                      }}
                      state={{
                        projectName: project.name,
                        projectColor: project.color,
                      }}
                      className="project-link"
                    >
                      Ver detalle
                    </Link>

                    <Link
                      to={{
                        pathname: `/projects/${project.id}/charts`,
                        search: buildProjectSearch(project),
                      }}
                      className="project-link"
                      style={{ marginLeft: '0.75rem' }}
                    >
                      Generar gráficos
                    </Link>
                  </div>

                  <div>
                    <button onClick={() => openEditModal(project)}>
                      Editar
                    </button>
                    <button onClick={() => openDeleteModal(project)}>
                      Eliminar
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
        <div className="projects-calendar-panel">
          <h3>Calendario de proyectos</h3>
          <ProjectYearCalendar projects={calendarItems} />
        </div>
      </div>

      {/* MODAL CREAR PROYECTO */}
      {createModalOpen && (
        <div style={overlayStyle}>
          <div style={modalStyle}>
            <h3>Crear nuevo proyecto</h3>

            <label style={{ fontSize: '0.85rem' }}>Nombre del proyecto</label>
            <input
              type="text"
              style={inputStyle}
              value={createName}
              onChange={(e) => {
                setCreateName(e.target.value);
                setCreateError('');
              }}
            />

            <label style={{ fontSize: '0.85rem' }}>Descripción</label>
            <textarea
              style={textAreaStyle}
              rows={2}
              value={createDescription}
              onChange={(e) => setCreateDescription(e.target.value)}
            />

            <label style={{ fontSize: '0.85rem' }}>Prioridad</label>
            <select
              style={inputStyle}
              value={createPriority}
              onChange={(e) => setCreatePriority(e.target.value)}
            >
              <option value="alta">Alta</option>
              <option value="media">Media</option>
              <option value="baja">Baja</option>
            </select>

            <label style={{ fontSize: '0.85rem' }}>Categoría</label>
            <input
              type="text"
              style={inputStyle}
              value={createCategory}
              onChange={(e) => setCreateCategory(e.target.value)}
            />

            <label style={{ fontSize: '0.85rem' }}>Fechas del proyecto</label>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
                gap: '0.75rem',
              }}
            >
              <input
                type="date"
                style={inputStyle}
                value={createStartDate}
                onChange={(e) => {
                  setCreateStartDate(e.target.value);
                  setCreateError('');
                }}
                placeholder="Inicio"
              />
              <input
                type="date"
                style={inputStyle}
                value={createEndDate}
                onChange={(e) => {
                  setCreateEndDate(e.target.value);
                  setCreateError('');
               }}
                placeholder="Fin previsto"
              />
            </div>

            <label style={{ fontSize: '0.85rem' }}>Estimación total del proyecto</label>
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
                style={inputStyle}
                placeholder="Horas"
                value={createEstimatedHours}
                onChange={(e) => {
                  setCreateEstimatedHours(e.target.value);
                  setCreateError('');
                }}
              />
              <input
                type="number"
                min="0"
                max="59"
                style={inputStyle}
                placeholder="Minutos"
                value={createEstimatedMinutes}
                onChange={(e) => {
                  setCreateEstimatedMinutes(e.target.value);
                  setCreateError('');
                }}
              />
            </div>


            <label style={{ fontSize: '0.85rem' }}>Contraseña del proyecto</label>
            <input
              type="password"
              style={inputStyle}
              value={createPassword}
              onChange={(e) => {
                setCreatePassword(e.target.value);
                setCreateError('');
              }}
            />

            {createError && <div style={errorText}>{createError}</div>}

            <div style={modalActions}>
              <button
                type="button"
                style={secondaryBtn}
                onClick={() => setCreateModalOpen(false)}
              >
                Cancelar
              </button>
              <button type="button" style={primaryBtn} onClick={confirmCreateProject}>
                Crear proyecto
              </button>
            </div>
          </div>
        </div>
      )} 

      {/* MODAL EDITAR PROYECTO */}
      {editModal && (
        <div style={overlayStyle}>
          <div style={modalStyle}>
            <h3>Editar proyecto</h3>

            <label style={{ fontSize: '0.85rem' }}>Nombre del proyecto</label>
            <input
              type="text"
              style={inputStyle}
              value={editModal.name}
              onChange={(e) => {
                setEditModal((prev) => ({ ...prev, name: e.target.value }));
                setEditError('');
              }}
            />

            <label style={{ fontSize: '0.85rem' }}>Descripción</label>
            <textarea
              style={textAreaStyle}
              rows={2}
              value={editModal.description || ''}
              onChange={(e) =>
                setEditModal((prev) => ({ ...prev, description: e.target.value }))
              }
            />

            <label style={{ fontSize: '0.85rem' }}>Prioridad</label>
            <select
              style={inputStyle}
              value={editModal.priority}
              onChange={(e) =>
                setEditModal((prev) => ({ ...prev, priority: e.target.value }))
              }
            >
              <option value="alta">Alta</option>
              <option value="media">Media</option>
              <option value="baja">Baja</option>
            </select>

            <label style={{ fontSize: '0.85rem' }}>Categoría</label>
            <input
              type="text"
              style={inputStyle}
              value={editModal.category || ''}
              onChange={(e) =>
                setEditModal((prev) => ({ ...prev, category: e.target.value }))
              }
            />

            <label style={{ fontSize: '0.85rem', marginTop: '0.75rem' }}>
              Color del proyecto
            </label>

            <input
              type="color"
              value={editModal.color || '#2563eb'}
              onChange={(e) =>
                setEditModal((prev) => ({
                  ...prev,
                  color: e.target.value,
                }))
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
          {editError && <div style={errorText}>{editError}</div>}

          <div style={modalActions}>
            <button
              type="button"
              style={secondaryBtn}
              onClick={() => setEditModal(null)}
            >
              Cancelar
            </button>

            <button
              type="button"
              style={primaryBtn}
              onClick={confirmEditProject}
            >
              Guardar cambios
            </button>
          </div>
         </div>
        </div>
     )}
              
      {/* MODAL ELIMINAR PROYECTO */}
      {deleteModal && (
        <div style={overlayStyle}>
          <div style={modalStyle}>
            <h3>Eliminar proyecto</h3>

            <p style={{ fontSize: '0.9rem', color: '#374151' }}>
              Vas a eliminar el proyecto{' '}
              <strong>{deleteModal.projectName}</strong>.
              Esta acción no se puede deshacer.
            </p>

            <label style={{ fontSize: '0.85rem' }}>
              Contraseña del proyecto
            </label>
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

              <button
                type="button"
                style={dangerBtn}
                onClick={confirmDeleteProject}
              >
                Eliminar definitivamente
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export default ProjectsPage;
