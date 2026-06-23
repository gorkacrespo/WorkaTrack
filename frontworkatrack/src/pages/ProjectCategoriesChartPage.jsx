import { useParams } from 'react-router-dom';
import { useEffect, useState, useMemo } from 'react';

function ProjectCategoriesChartPage() {
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

  // Datos de ejemplo: horas por categoría
  const categories = useMemo(
    () => [
      { id: 'estudio', label: 'Estudio / lectura', hours: 24 },
      { id: 'redaccion', label: 'Redacción / escritura', hours: 18 },
      { id: 'analisis', label: 'Análisis de datos', hours: 12 },
      { id: 'reuniones', label: 'Reuniones / coordinación', hours: 6 },
      { id: 'otros', label: 'Otros', hours: 4 },
    ],
    []
  );

  const totalHours = categories.reduce((acc, c) => acc + c.hours, 0);
  const maxHours = Math.max(...categories.map((c) => c.hours), 1);

  return (
    <div
      style={{
        minHeight: '100vh',
        backgroundColor: '#f3f4f6',
        padding: '1.5rem 1.25rem 2rem',
      }}
    >
      <div style={{ maxWidth: '900px', margin: '0 auto' }}>
        {/* Cabecera con progreso */}
        <div
          style={{
            marginBottom: '1.5rem',
          }}
        >
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'baseline',
              gap: '1rem',
              marginBottom: '0.5rem',
            }}
          >
            <div>
              <div
                style={{
                  fontSize: '0.8rem',
                  textTransform: 'uppercase',
                  letterSpacing: '0.08em',
                  color: '#6b7280',
                  marginBottom: '0.2rem',
                }}
              >
                Distribución del tiempo por categorías
              </div>
              <h1
                style={{
                  fontSize: '1.5rem',
                  fontWeight: 600,
                  color: '#111827',
                }}
              >
                {projectName}
              </h1>
            </div>

            {/* Progreso global */}
            <div
              style={{
                minWidth: '220px',
              }}
            >
              <div
                style={{
                  fontSize: '0.8rem',
                  color: '#4b5563',
                  marginBottom: '0.2rem',
                  textAlign: 'right',
                }}
              >
                Progreso global
              </div>
              <div
                style={{
                  position: 'relative',
                  height: '0.6rem',
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

          <p
            style={{
              fontSize: '0.9rem',
              color: '#4b5563',
              marginTop: '0.3rem',
            }}
          >
            Este gráfico muestra cómo se reparten las horas dedicadas al
            proyecto entre distintos tipos de actividad (datos de ejemplo,
            luego vendrán de tus sesiones reales).
          </p>
        </div>

        {/* Tarjeta del gráfico */}
        <div
          style={{
            backgroundColor: '#ffffff',
            borderRadius: '0.75rem',
            border: '1px solid #e5e7eb',
            padding: '1rem 1.25rem 1.25rem',
          }}
        >
          <div
            style={{
              marginBottom: '0.75rem',
              fontSize: '0.85rem',
              color: '#4b5563',
            }}
          >
            Total horas (ejemplo): <strong>{totalHours} h</strong>
          </div>

          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '0.6rem',
            }}
          >
            {categories.map((cat) => {
              const widthPercent = (cat.hours / maxHours) * 100;

              return (
                <div key={cat.id}>
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      fontSize: '0.85rem',
                      marginBottom: '0.15rem',
                    }}
                  >
                    <span>{cat.label}</span>
                    <span
                      style={{
                        color: '#4b5563',
                      }}
                    >
                      {cat.hours} h
                    </span>
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
        </div>
      </div>
    </div>
  );
}

export default ProjectCategoriesChartPage;
