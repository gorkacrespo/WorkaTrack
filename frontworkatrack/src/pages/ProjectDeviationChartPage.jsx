import { useParams } from 'react-router-dom';
import { useEffect, useState, useMemo } from 'react';

function ProjectDeviationChartPage() {
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

  // Datos de ejemplo: horas estimadas vs reales por tarea
  const tasks = useMemo(
    () => [
      { id: 1, name: 'Revisión bibliografía', estimated: 6, actual: 8 },
      { id: 2, name: 'Redacción introducción', estimated: 5, actual: 4 },
      { id: 3, name: 'Análisis datos', estimated: 8, actual: 10 },
      { id: 4, name: 'Resultados y discusión', estimated: 7, actual: 6 },
      { id: 5, name: 'Revisión final', estimated: 4, actual: 5 },
    ],
    []
  );

  const maxHours = Math.max(
    ...tasks.flatMap((t) => [t.estimated, t.actual]),
    1
  );

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
                Estimación vs horas reales por tarea
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
            Compara las horas estimadas frente a las horas realmente
            dedicadas a cada tarea (de momento con datos de ejemplo; luego
            lo conectaremos con tus tareas y sesiones reales).
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
          {/* Leyenda */}
          <div
            style={{
              display: 'flex',
              gap: '1rem',
              fontSize: '0.8rem',
              color: '#4b5563',
              marginBottom: '0.75rem',
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.4rem',
              }}
            >
              <span
                style={{
                  display: 'inline-block',
                  width: '12px',
                  height: '6px',
                  borderRadius: '999px',
                  backgroundColor: '#111827',
                }}
              />
              Estimado
            </div>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.4rem',
              }}
            >
              <span
                style={{
                  display: 'inline-block',
                  width: '12px',
                  height: '6px',
                  borderRadius: '999px',
                  backgroundColor: '#3b82f6',
                }}
              />
              Real
            </div>
          </div>

          {/* Filas por tarea */}
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '0.75rem',
            }}
          >
            {tasks.map((t) => {
              const estWidth = (t.estimated / maxHours) * 100;
              const actWidth = (t.actual / maxHours) * 100;

              return (
                <div key={t.id}>
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      fontSize: '0.85rem',
                      marginBottom: '0.2rem',
                    }}
                  >
                    <span>{t.name}</span>
                    <span
                      style={{
                        color: '#4b5563',
                      }}
                    >
                      {t.estimated} h est · {t.actual} h reales
                    </span>
                  </div>

                  <div
                    style={{
                      position: 'relative',
                      height: '1.1rem',
                      borderRadius: '0.5rem',
                      backgroundColor: '#e5e7eb',
                      overflow: 'hidden',
                    }}
                  >
                    {/* Estimado */}
                    <div
                      style={{
                        position: 'absolute',
                        left: 0,
                        top: '0.16rem',
                        bottom: '0.16rem',
                        width: `${estWidth}%`,
                        borderRadius: '999px',
                        backgroundColor: '#111827',
                      }}
                    />

                    {/* Real */}
                    <div
                      style={{
                        position: 'absolute',
                        left: 0,
                        top: '0.16rem',
                        bottom: '0.16rem',
                        width: `${actWidth}%`,
                        borderRadius: '999px',
                        backgroundColor: '#3b82f6',
                        opacity: 0.85,
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

export default ProjectDeviationChartPage;
