import { useParams } from 'react-router-dom';
import { useEffect, useMemo, useState } from 'react';

function ProjectDeviationPage() {
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
      { id: 1, name: 'Revisión bibliografía', estimated: 6, actual: 10 },
      { id: 2, name: 'Redacción introducción', estimated: 8, actual: 7 },
      { id: 3, name: 'Diseño de modelo de datos', estimated: 5, actual: 9 },
      { id: 4, name: 'Implementación API', estimated: 12, actual: 14 },
      { id: 5, name: 'Pruebas y documentación', estimated: 10, actual: 8 },
    ],
    []
  );

  const tasksWithDeviation = useMemo(
    () =>
      tasks
        .map((t) => ({
          ...t,
          deviation: t.actual - t.estimated,
        }))
        .sort((a, b) => Math.abs(b.deviation) - Math.abs(a.deviation)),
    [tasks]
  );

  const maxHours = Math.max(
    ...tasksWithDeviation.map((t) => Math.max(t.estimated, t.actual)),
    1
  );

  const totalEstimated = tasks.reduce(
    (sum, t) => sum + t.estimated,
    0
  );
  const totalActual = tasks.reduce((sum, t) => sum + t.actual, 0);
  const totalDeviation = totalActual - totalEstimated;

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
            Desviación estimado vs real
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
            Compara el tiempo estimado y el tiempo real que has dedicado a
            cada tarea. Esto te ayudará a medir lo realistas que son tus
            planificaciones (datos de ejemplo).
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
          {/* Resumen general */}
          <div
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: '1.5rem',
              marginBottom: '1rem',
              fontSize: '0.85rem',
              color: '#374151',
            }}
          >
            <div>
              <div style={{ fontWeight: 500 }}>Total estimado</div>
              <div>{totalEstimated} h</div>
            </div>
            <div>
              <div style={{ fontWeight: 500 }}>Total real</div>
              <div>{totalActual} h</div>
            </div>
            <div>
              <div style={{ fontWeight: 500 }}>Desviación global</div>
              <div
                style={{
                  color:
                    totalDeviation > 0
                      ? '#b91c1c'
                      : totalDeviation < 0
                      ? '#15803d'
                      : '#374151',
                }}
              >
                {totalDeviation > 0 ? '+' : ''}
                {totalDeviation} h
              </div>
            </div>
          </div>

          {/* Barras por tarea */}
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '0.75rem',
            }}
          >
            {tasksWithDeviation.map((t) => {
              const estWidth = (t.estimated / maxHours) * 100;
              const actWidth = (t.actual / maxHours) * 100;
              const deviationColor =
                t.deviation > 0
                  ? '#b91c1c'
                  : t.deviation < 0
                  ? '#15803d'
                  : '#4b5563';

              return (
                <div key={t.id}>
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      marginBottom: '0.2rem',
                      fontSize: '0.85rem',
                      color: '#111827',
                    }}
                  >
                    <span>{t.name}</span>
                    <span
                      style={{
                        color: deviationColor,
                        fontSize: '0.8rem',
                      }}
                    >
                      {t.deviation > 0 ? '+' : ''}
                      {t.deviation} h
                    </span>
                  </div>

                  <div
                    style={{
                      position: 'relative',
                      height: '1rem',
                      borderRadius: '999px',
                      backgroundColor: '#e5e7eb',
                      overflow: 'hidden',
                    }}
                  >
                    {/* estimado (gris) */}
                    <div
                      style={{
                        position: 'absolute',
                        left: 0,
                        top: '0.2rem',
                        bottom: '0.2rem',
                        width: `${estWidth}%`,
                        borderRadius: '999px',
                        backgroundColor: '#d1d5db',
                      }}
                    />

                    {/* real (azul) */}
                    <div
                      style={{
                        position: 'absolute',
                        left: 0,
                        top: '0.08rem',
                        bottom: '0.08rem',
                        width: `${actWidth}%`,
                        borderRadius: '999px',
                        backgroundColor: '#1d4ed8',
                        opacity: 0.95,
                      }}
                    />
                  </div>

                  <div
                    style={{
                      marginTop: '0.15rem',
                      fontSize: '0.78rem',
                      color: '#4b5563',
                      display: 'flex',
                      justifyContent: 'space-between',
                    }}
                  >
                    <span>Estimado: {t.estimated} h</span>
                    <span>Real: {t.actual} h</span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Leyenda */}
          <div
            style={{
              display: 'flex',
              gap: '1rem',
              marginTop: '0.9rem',
              fontSize: '0.8rem',
              color: '#4b5563',
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
                  backgroundColor: '#d1d5db',
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
                  backgroundColor: '#1d4ed8',
                }}
              />
              Real
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ProjectDeviationPage;
