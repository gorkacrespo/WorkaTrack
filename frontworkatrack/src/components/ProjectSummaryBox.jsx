import { useState } from 'react';

function formatMinutes(totalMinutes) {
  if (!totalMinutes || totalMinutes <= 0) return '—';

  const h = Math.floor(totalMinutes / 60);
  const m = totalMinutes % 60;

  if (h > 0 && m > 0) return `${h}h ${m}min`;
  if (h > 0) return `${h}h`;
  return `${m}min`;
}

function ProjectSummaryBox({ stats }) {
  const [isMinimized, setIsMinimized] = useState(false);

  return (
    <div
      className="calendar-summary-box"
      style={
        isMinimized
          ? {
              display: 'inline-flex',
              alignItems: 'center',
              height: 'auto',
              minHeight: 'unset',
              padding: '0.75rem 1rem',
            }
          : undefined
      }
    >
      <h4
        style={{
          marginTop: 0,
          marginBottom: isMinimized ? 0 : undefined,
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
        }}
      >
        <span>Resumen proyecto</span>
        <button
          onClick={() => setIsMinimized((v) => !v)}
          style={{
            background: 'none',
            border: '1px solid #d1d5db',
            borderRadius: '0.375rem',
            cursor: 'pointer',
            fontSize: '0.85rem',
            padding: '0.15rem 0.35rem',
            color: '#374151',
          }}
          title={isMinimized ? 'Mostrar resumen' : 'Ocultar resumen'}
        >
          {isMinimized ? '▸' : '▾'}
        </button>
      </h4>

      {!isMinimized && (
        <>
          {!stats && (
            <p style={{ fontSize: '0.85rem', color: '#6b7280' }}>
              Cargando resumen…
            </p>
          )}

          {stats && (
            <>
              <p style={{ fontSize: '0.85rem', marginBottom: '0.25rem' }}>
                Tiempo estimado:{' '}
                {stats.minutos_estimados > 0
                  ? formatMinutes(stats.minutos_estimados)
                  : '—'}
              </p>

              <p style={{ fontSize: '0.85rem', marginBottom: '0.25rem' }}>
                Tiempo real:{' '}
                {stats.minutos_reales > 0
                  ? formatMinutes(stats.minutos_reales)
                  : '—'}
              </p>

              <p style={{ fontSize: '0.85rem', marginBottom: 0 }}>
                Progreso:{' '}
                {stats.minutos_estimados > 0
                  ? `${stats.progreso}%`
                  : '—'}
              </p>
            </>
          )}
        </>
      )}
    </div>
  );
}

export default ProjectSummaryBox;
