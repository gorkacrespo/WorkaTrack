import { useParams } from 'react-router-dom';
import { useEffect, useState, useMemo } from 'react';

function ProjectWeeklyChartPage() {
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

  // Datos de ejemplo: horas por semana
  const weeklyData = useMemo(
    () => [
      { week: 'Semana 1', hours: 6 },
      { week: 'Semana 2', hours: 10 },
      { week: 'Semana 3', hours: 4 },
      { week: 'Semana 4', hours: 12 },
      { week: 'Semana 5', hours: 9 },
      { week: 'Semana 6', hours: 7 },
    ],
    []
  );

  const maxHours = Math.max(...weeklyData.map((w) => w.hours), 1);

  return (
    <div
      style={{
        minHeight: '100vh',
        backgroundColor: '#f3f4f6',
        padding: '1.5rem 1.25rem 2rem',
      }}
    >
      <div style={{ maxWidth: '1100px', margin: '0 auto' }}>
        {/* Cabecera con progreso global (mismo estilo que Gantt) */}
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
            Evolución semanal de horas
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
            Muestra cuántas horas has dedicado a este proyecto cada semana
            (datos de ejemplo; más adelante lo conectaremos con tus sesiones
            reales).
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

        {/* Tarjeta del gráfico */}
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
              height: '260px',
              display: 'flex',
              alignItems: 'flex-end',
              gap: '0.8rem',
            }}
          >
            {weeklyData.map((w) => {
              const heightPercent = (w.hours / maxHours) * 100;

              return (
                <div
                  key={w.week}
                  style={{
                    flex: 1,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'flex-end',
                    fontSize: '0.8rem',
                  }}
                >
                  <div
                    style={{
                      height: `${heightPercent}%`,
                      minHeight: '4px',
                      width: '16px',
                      borderRadius: '999px',
                      backgroundColor: '#111827',
                      marginBottom: '0.35rem',
                    }}
                  />
                  <div
                    style={{
                      color: '#111827',
                      marginBottom: '0.1rem',
                    }}
                  >
                    {w.hours} h
                  </div>
                  <div
                    style={{
                      color: '#6b7280',
                      textAlign: 'center',
                      lineHeight: 1.2,
                    }}
                  >
                    {w.week}
                  </div>
                </div>
              );
            })}
          </div>

          <div
            style={{
              marginTop: '0.8rem',
              fontSize: '0.8rem',
              color: '#6b7280',
            }}
          >
            Esta gráfica te permitirá ver de un vistazo qué semanas han sido
            más productivas y dónde ha habido bajones de trabajo.
          </div>
        </div>
      </div>
    </div>
  );
}

export default ProjectWeeklyChartPage;
