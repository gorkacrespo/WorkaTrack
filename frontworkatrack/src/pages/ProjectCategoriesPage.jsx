import { useParams } from 'react-router-dom';
import { useEffect, useMemo, useState } from 'react';

function ProjectCategoriesPage() {
  const { projectId } = useParams();
  const [projectInfo, setProjectInfo] = useState(null);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(
        `workatrack-project-${projectId}`
      );
      if (raw) {
        setProjectInfo(JSON.parse(raw));
      }
    } catch (e) {
      // ignoramos errores
    }
  }, [projectId]);

  const projectName = projectInfo?.name || `Proyecto ${projectId}`;
  const projectProgress =
    typeof projectInfo?.progress === 'number'
      ? projectInfo.progress
      : 0;

  // Datos de ejemplo de categorías
  const categories = useMemo(
    () => [
      { id: 1, name: 'Lectura / teoría', hours: 18 },
      { id: 2, name: 'Práctica / código', hours: 25 },
      { id: 3, name: 'Documentación', hours: 10 },
      { id: 4, name: 'Reuniones / organización', hours: 7 },
    ],
    []
  );

  const totalHours = categories.reduce(
    (sum, c) => sum + c.hours,
    0
  );
  const maxHours = Math.max(...categories.map((c) => c.hours), 1);

  return (
    <div
      style={{
        minHeight: '100vh',
        backgroundColor: '#f3f4f6',
        padding: '1.5rem 1.25rem 2rem',
      }}
    >
      <div style={{ maxWidth: '1100px', margin: '0 auto' }}>
        {/* Cabecera con progreso global */}
        <div
          style={{
            marginBottom: '1.5rem',
          }}
        >
          <div
            style={{
              fontSize: '0.8rem',
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
              color: '#6b7280',
              marginBottom: '0.2rem',
            }}
          >
            Distribución por categorías
          </div>
          <h1
            style={{
              fontSize: '1.5rem',
              fontWeight: 600,
              color: '#111827',
              marginBottom: '0.3rem',
            }}
          >
            {projectName}
          </h1>
          <p
            style={{
              fontSize: '0.9rem',
              color: '#4b5563',
              marginBottom: '0.7rem',
            }}
          >
            Visualiza cómo se reparte tu tiempo real entre los distintos tipos
            de actividad del proyecto (datos de ejemplo). Más adelante
            usaremos las categorías de tus tareas reales.
          </p>

          {/* Barra de progreso igual que en el Gantt */}
          <div>
            <div
              style={{
                fontSize: '0.8rem',
                color: '#4b5563',
                marginBottom: '0.2rem',
              }}
            >
              Progreso global
            </div>
            <div
              style={{
                position: 'relative',
                height: '0.7rem',
                borderRadius: '999px',
                backgroundColor: '#e5e7eb',
                overflow: 'hidden',
              }}
            >
              <div
                style={{
                  position: 'absolute',
                  left: 0,
                  top: 0,
                  bottom: 0,
                  width: `${Math.max(
                    0,
                    Math.min(projectProgress, 100)
                  )}%`,
                  borderRadius: '999px',
                  backgroundColor: '#111827',
                }}
              />
            </div>
            <div
              style={{
                fontSize: '0.75rem',
                color: '#4b5563',
                marginTop: '0.15rem',
                textAlign: 'right',
              }}
            >
              {Math.max(0, Math.min(projectProgress, 100))}%
            </div>
          </div>
        </div>

        {/* Contenido principal */}
        <div
          style={{
            backgroundColor: '#ffffff',
            borderRadius: '0.75rem',
            border: '1px solid #e5e7eb',
            padding: '1.25rem 1.5rem',
          }}
        >
          <div
            style={{
              marginBottom: '1rem',
              fontSize: '0.85rem',
              color: '#374151',
            }}
          >
            Total horas (mock): <strong>{totalHours} h</strong>
          </div>

          {/* Barras horizontales por categoría */}
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '0.75rem',
            }}
          >
            {categories.map((c) => {
              const widthPercent = (c.hours / maxHours) * 100;
              const percentage =
                totalHours > 0 ? (c.hours / totalHours) * 100 : 0;

              return (
                <div key={c.id}>
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      marginBottom: '0.2rem',
                      fontSize: '0.85rem',
                      color: '#111827',
                    }}
                  >
                    <span>{c.name}</span>
                    <span
                      style={{
                        fontSize: '0.8rem',
                        color: '#4b5563',
                      }}
                    >
                      {c.hours} h · {percentage.toFixed(1)}%
                    </span>
                  </div>

                  <div
                    style={{
                      position: 'relative',
                      height: '0.9rem',
                      borderRadius: '999px',
                      backgroundColor: '#e5e7eb',
                      overflow: 'hidden',
                    }}
                  >
                    <div
                      style={{
                        position: 'absolute',
                        left: 0,
                        top: '0.12rem',
                        bottom: '0.12rem',
                        width: `${widthPercent}%`,
                        borderRadius: '999px',
                        backgroundColor: '#111827',
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>

          {/* Nota final */}
          <div
            style={{
              marginTop: '0.9rem',
              fontSize: '0.8rem',
              color: '#6b7280',
            }}
          >
            Esta vista es ideal para ver si estás equilibrando bien tu tiempo
            entre lectura, práctica, documentación, reuniones, etc.
          </div>
        </div>
      </div>
    </div>
  );
}

export default ProjectCategoriesPage;
