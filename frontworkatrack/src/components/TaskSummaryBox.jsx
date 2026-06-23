import { useEffect, useState } from 'react';
import { apiFetch } from '../api/client';

function formatMinutes(totalMinutes) {
  if (!totalMinutes || totalMinutes <= 0) return '—';

  const h = Math.floor(totalMinutes / 60);
  const m = totalMinutes % 60;

  if (h > 0 && m > 0) return `${h}h ${m}min`;
  if (h > 0) return `${h}h`;
  return `${m}min`;
}

function TaskSummaryBox({ taskId }) {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [isMinimized, setIsMinimized] = useState(false);

  useEffect(() => {
    if (!taskId) return;

    async function loadStats() {
      setLoading(true);
      setError('');

      try {
        const data = await apiFetch(`/tasks/${taskId}/stats`);
        setStats(data);
      } catch (err) {
        setError(err.message || 'Error cargando estadísticas de la tarea');
        setStats(null);
      } finally {
        setLoading(false);
      }
    }

    loadStats();
  }, [taskId]);

  return (
    <div
      className="calendar-summary-box"
      style={
        isMinimized
          ? {
              height: 'auto',
              minHeight: 'unset',
            }
          : undefined
      }
    >
      <h4
        style={{
          marginTop: 0,
          marginBottom: isMinimized ? 0 : undefined,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <span>Resumen de la tarea</span>
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
          {loading && (
            <p style={{ fontSize: '0.85rem' }}>
              Cargando…
            </p>
          )}

          {!loading && stats && (
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

          {!loading && error && (
            <p style={{ fontSize: '0.8rem', color: '#b91c1c' }}>
              {error}
            </p>
          )}
        </>
      )}
    </div>
  );
}

export default TaskSummaryBox;
