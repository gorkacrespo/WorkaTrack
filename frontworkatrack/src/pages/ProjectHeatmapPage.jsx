import { useParams } from 'react-router-dom';
import { useEffect, useMemo, useState } from 'react';

function ProjectHeatmapPage() {
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

  const baseYear = 2025;

  // Datos de ejemplo de horas por día (muy simples)
  const sessionsByDay = useMemo(() => {
    const data = {};
    const add = (month, day, hours) => {
      const key = `${baseYear}-${String(month).padStart(2, '0')}-${String(
        day
      ).padStart(2, '0')}`;
      data[key] = hours;
    };

    add(1, 3, 1);
    add(1, 5, 3);
    add(1, 10, 2);
    add(2, 1, 4);
    add(2, 12, 1.5);
    add(3, 4, 5);
    add(3, 18, 2);
    add(4, 7, 3.5);
    add(5, 21, 4);
    add(6, 2, 1);
    add(6, 15, 2.5);
    add(7, 9, 3);
    add(8, 30, 4.5);
    add(9, 5, 2);
    add(10, 11, 3);
    add(11, 22, 5);
    add(12, 3, 4);

    return data;
  }, []);

  // Generar todos los días del año en semanas de 7 días
  const weeks = useMemo(() => {
    const days = [];
    const start = new Date(baseYear, 0, 1);
    const end = new Date(baseYear, 11, 31);

    for (let d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {
      const dateKey = [
        d.getFullYear(),
        String(d.getMonth() + 1).padStart(2, '0'),
        String(d.getDate()).padStart(2, '0'),
      ].join('-');
      const hours = sessionsByDay[dateKey] || 0;
      days.push({
        date: new Date(d),
        key: dateKey,
        hours,
      });
    }

    const result = [];
    let currentWeek = [];
    days.forEach((day) => {
      currentWeek.push(day);
      if (currentWeek.length === 7) {
        result.push(currentWeek);
        currentWeek = [];
      }
    });
    if (currentWeek.length > 0) {
      while (currentWeek.length < 7) {
        currentWeek.push(null);
      }
      result.push(currentWeek);
    }

    return result;
  }, [sessionsByDay]);

  const colorForHours = (h) => {
    if (h <= 0) return '#e5e7eb';
    if (h < 2) return '#bfdbfe';
    if (h < 4) return '#60a5fa';
    return '#1d4ed8';
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        backgroundColor: '#f3f4f6',
        padding: '1.5rem 1.25rem 2rem',
      }}
    >
      <div style={{ maxWidth: '1100px', margin: '0 auto' }}>
        {/* Cabecera con progreso global (igual que Gantt) */}
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
            Heatmap anual de sesiones
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
            Representación tipo GitHub de tu constancia a lo largo del año.
            Cada cuadrado es un día; cuanto más oscuro, más horas
            dedicadas al proyecto (datos de ejemplo).
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

        {/* Heatmap */}
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
              fontSize: '0.85rem',
              color: '#4b5563',
              marginBottom: '0.75rem',
            }}
          >
            Año {baseYear} (mock). Más adelante conectaremos esta vista con tus
            sesiones reales para mostrar tu constancia de estudio/trabajo.
          </div>

          <div
            style={{
              display: 'flex',
              gap: '0.4rem',
              fontSize: '0.75rem',
              color: '#6b7280',
              marginBottom: '0.3rem',
            }}
          >
            <span>L</span>
            <span>M</span>
            <span>X</span>
            <span>J</span>
            <span>V</span>
            <span>S</span>
            <span>D</span>
          </div>

          <div
            style={{
              display: 'flex',
              gap: '0.15rem',
              overflowX: 'auto',
              paddingBottom: '0.25rem',
            }}
          >
            {weeks.map((week, i) => (
              <div
                key={i}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.15rem',
                }}
              >
                {week.map((day, idx) =>
                  day ? (
                    <div
                      key={day.key}
                      title={`${day.key} – ${
                        day.hours > 0 ? `${day.hours} h` : 'Sin sesiones'
                      }`}
                      style={{
                        width: '12px',
                        height: '12px',
                        borderRadius: '3px',
                        backgroundColor: colorForHours(day.hours),
                      }}
                    />
                  ) : (
                    <div
                      key={`empty-${idx}`}
                      style={{
                        width: '12px',
                        height: '12px',
                        borderRadius: '3px',
                        backgroundColor: 'transparent',
                      }}
                    />
                  )
                )}
              </div>
            ))}
          </div>

          {/* Leyenda */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              marginTop: '0.6rem',
              fontSize: '0.75rem',
              color: '#6b7280',
            }}
          >
            <span>Menos</span>
            <span
              style={{
                width: '12px',
                height: '12px',
                borderRadius: '3px',
                backgroundColor: '#e5e7eb',
              }}
            />
            <span
              style={{
                width: '12px',
                height: '12px',
                borderRadius: '3px',
                backgroundColor: '#bfdbfe',
              }}
            />
            <span
              style={{
                width: '12px',
                height: '12px',
                borderRadius: '3px',
                backgroundColor: '#60a5fa',
              }}
            />
            <span
              style={{
                width: '12px',
                height: '12px',
                borderRadius: '3px',
                backgroundColor: '#1d4ed8',
              }}
            />
            <span>Más</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ProjectHeatmapPage;
