import { useParams, Link } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { apiFetch } from '../api/client';

function ProjectChartsPage() {
  const { projectId } = useParams();
  const [projectInfo, setProjectInfo] = useState(null);

  // Q&A
  const [qaQuery, setQaQuery] = useState('');
  const [qaMode, setQaMode] = useState('deep'); // fast | deep
  const [qaJobId, setQaJobId] = useState(null);
  const [qaStatus, setQaStatus] = useState(null);
  const [qaAnswer, setQaAnswer] = useState('');
  const [qaAnswerMode, setQaAnswerMode] = useState(null); // llm | fallback | no_data
  const [qaIsFallback, setQaIsFallback] = useState(false);
  const [qaRunning, setQaRunning] = useState(false);
  const [qaError, setQaError] = useState('');

  const [qaStartedAtMs, setQaStartedAtMs] = useState(null);
  const [qaElapsedSecs, setQaElapsedSecs] = useState(0);

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

  useEffect(() => {
    if (!qaRunning || qaStartedAtMs == null) return;

    const t = window.setInterval(() => {
      setQaElapsedSecs(Math.floor((Date.now() - qaStartedAtMs) / 1000));
    }, 500);

    return () => window.clearInterval(t);
  }, [qaRunning, qaStartedAtMs]);

  const projectName = projectInfo?.name || `Proyecto ${projectId}`;
  const projectProgress =
    typeof projectInfo?.progress === 'number' ? projectInfo.progress : 0;

  const openInNewTab = (path) => {
    const url = `${window.location.origin}${path}`;
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  const formatEta = (secs) => {
    const s = Number(secs);
    if (!Number.isFinite(s) || s < 0) return '—';
    const mm = Math.floor(s / 60);
    const ss = Math.floor(s % 60);
    if (mm <= 0) return `${ss}s`;
    return `${mm}m ${ss}s`;
  };

  const qaStageLabel = (st) => {
    const stage = (st?.stage || '').toLowerCase();
    const done = Number(st?.done) || 0;
    const total = Number(st?.total) || 0;

    if (stage === 'map') {
      const totalWeeks = Math.max(0, total - 1);
      const ws = st?.week_start || '';
      const we = st?.week_end || '';
      return `Resumiendo semana ${done}/${totalWeeks}${
        ws && we ? ` (${ws}..${we})` : ''
      }`;
    }
    if (stage === 'reduce') return 'Generando respuesta final…';
    if (stage === 'done') return 'Completado';
    if (stage === 'error') return 'Error';
    return 'Preparando…';
  };

  const qaPercent =
    qaStatus?.total > 0
      ? Math.max(
          0,
          Math.min(
            100,
            (Number(qaStatus?.done || 0) / Number(qaStatus?.total || 1)) * 100
          )
        )
      : 0;

  const handleAskQa = async () => {
    const q = (qaQuery || '').trim();
    if (!q) {
      setQaError('Escribe una pregunta.');
      return;
    }

    setQaError('');
    setQaAnswer('');
    setQaAnswerMode(null);
    setQaIsFallback(false);
    setQaStatus(null);
    setQaJobId(null);
    setQaRunning(true);
  
    setQaStartedAtMs(Date.now());
    setQaElapsedSecs(0);

    try {
      if (qaMode === 'deep') {
        const res = await apiFetch(`/projects/${projectId}/qa`, {
          method: 'POST',
          body: JSON.stringify({
            query: q,
            mode: 'deep',
            scope: 'all',
            async: true,
          }),
        });

        if (!res?.job_id) {
          throw new Error('No se recibió job_id');
        }

        setQaJobId(res.job_id);
      } else {
        const res = await apiFetch(`/projects/${projectId}/qa`, {
          method: 'POST',
          body: JSON.stringify({
            query: q,
            mode: 'fast',
            scope: 'all',
          }),
        });

        if (!res) {
          setQaError(res?.message || 'Error en Q&A (FAST).');
          setQaRunning(false);
          return;
        }

        setQaAnswerMode(res?.answer_mode || null);
        setQaIsFallback(Boolean(res?.is_fallback));

        const ans = String(res?.answer || '').trim();
        if (!ans) {
          // Si no hay evidencia, lo mostramos como aviso (no como error)
          if (res?.answer_mode === 'no_data') {
            setQaAnswer('');
            setQaRunning(false);
            return;
          }
          setQaError(res?.message || 'Q&A (FAST) no devolvió respuesta.');
          setQaRunning(false);
          return;
        }

        setQaAnswer(ans);
        setQaRunning(false);
      }
    } catch (e) {
      setQaError(e?.message || 'Error al consultar Q&A');
      setQaRunning(false);
    }
  };

  useEffect(() => {
    if (!qaJobId) return;

    let cancelled = false;
    let timer = null;

    const poll = async () => {
      try {
        const st = await apiFetch(`/qa/jobs/${qaJobId}`);
        if (cancelled) return;

        setQaStatus(st);

        if (st?.status === 'done') {
          setQaAnswerMode(st?.answer_mode || st?.result?.answer_mode || null);
          setQaIsFallback(Boolean(st?.is_fallback || st?.result?.is_fallback));
          setQaAnswer(st?.answer || '');
          setQaRunning(false);
          setQaJobId(null);
        } else if (st?.status === 'error') {
          setQaError(st?.error || 'Error en job');
          setQaRunning(false);
          setQaJobId(null);
        }
      } catch (e) {
        if (cancelled) return;
        setQaError(e?.message || 'Error consultando estado');
        setQaRunning(false);
        setQaJobId(null);
      }
    };

    poll();
    timer = window.setInterval(poll, 1500);

    return () => {
      cancelled = true;
      if (timer) window.clearInterval(timer);
    };
  }, [qaJobId, projectId]);

  return (
    <div
      style={{
        minHeight: '100vh',
        overflowY: 'auto',
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
            Gráficos del proyecto
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
            Elige qué tipo de gráfico quieres generar. Cada uno se abrirá en una
            pestaña nueva para que puedas comparar y navegar sin perder tu
            contexto.
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
                  width: `${Math.max(0, Math.min(projectProgress, 100))}%`,
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

        <div
          style={{
            marginBottom: '1.25rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '0.35rem',
            alignItems: 'flex-start',
          }}
        >
          <Link
            to="/projects"
            style={{
              fontSize: '0.8rem',
              color: '#4b5563',
              textDecoration: 'none',
            }}
          >
            ← Volver al listado de proyectos
          </Link>

          <Link
            to={`/projects/${projectId}`}
            style={{
              fontSize: '0.8rem',
              color: '#4b5563',
              textDecoration: 'none',
            }}
          >
            ← Volver al detalle del proyecto
          </Link>
        </div>

        {/* Q&A (analista) */}
        <div
          style={{
            border: '1px solid #e5e7eb',
            backgroundColor: '#ffffff',
            borderRadius: '0.75rem',
            padding: '1rem 1.1rem',
            marginBottom: '1rem',
          }}
        >
          <div
            style={{
              fontSize: '0.9rem',
              fontWeight: 600,
              color: '#111827',
              marginBottom: '0.35rem',
            }}
          >
            Q&amp;A (analista)
          </div>

          <div
            style={{
              fontSize: '0.85rem',
              color: '#4b5563',
              marginBottom: '0.7rem',
              lineHeight: 1.35,
            }}
          >
            Haz una pregunta y obtén una respuesta basada en notas del proyecto,
            tareas, sesiones e hitos, con referencias humanas incrustadas.
          </div>

          <div
            style={{
              display: 'flex',
              gap: '0.6rem',
              alignItems: 'center',
              flexWrap: 'wrap',
              marginBottom: '0.6rem',
            }}
          >
            <label style={{ fontSize: '0.8rem', color: '#4b5563' }}>Modo</label>
            <select
              value={qaMode}
              onChange={(e) => setQaMode(e.target.value)}
              style={{
                border: '1px solid #d1d5db',
                borderRadius: '0.5rem',
                padding: '0.35rem 0.5rem',
                fontSize: '0.85rem',
                backgroundColor: '#ffffff',
              }}
              disabled={qaRunning}
            >
              <option value="fast">Fast</option>
              <option value="deep">Deep (MAP/REDUCE)</option>
            </select>

            <button
              type="button"
              onClick={handleAskQa}
              disabled={qaRunning}
              style={{
                marginLeft: 'auto',
                borderRadius: '0.6rem',
                border: '1px solid #111827',
                backgroundColor: qaRunning ? '#9ca3af' : '#111827',
                color: '#ffffff',
                padding: '0.45rem 0.8rem',
                cursor: qaRunning ? 'not-allowed' : 'pointer',
                fontSize: '0.85rem',
              }}
            >
              {qaRunning ? 'Procesando…' : 'Preguntar'}
            </button>
          </div>

          <textarea
            value={qaQuery}
            onChange={(e) => setQaQuery(e.target.value)}
            placeholder="Ej: ¿Cómo evolucionó la relación con el cliente durante el proyecto?"
            style={{
              width: '100%',
              minHeight: '88px',
              borderRadius: '0.65rem',
              border: '1px solid #d1d5db',
              padding: '0.65rem 0.75rem',
              fontSize: '0.9rem',
              resize: 'vertical',
              outline: 'none',
              boxSizing: 'border-box',
              marginBottom: '0.65rem',
            }}
            disabled={qaRunning}
          />

          {(qaRunning || qaStatus) && (
            <div style={{ marginBottom: '0.65rem' }}>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  gap: '0.75rem',
                  marginBottom: '0.25rem',
                }}
              >
                <div style={{ fontSize: '0.8rem', color: '#4b5563' }}>
                  {qaStageLabel(qaStatus)}
                </div>
                <div style={{ fontSize: '0.8rem', color: '#4b5563' }}>
                  {qaMode === 'fast'
                    ? `Tiempo: ${formatEta(qaElapsedSecs)}`                  
                    : `ETA: ${formatEta(qaStatus?.eta_seconds)}`}
                </div>
              </div>

              <div
                style={{
                  position: 'relative',
                  height: '0.55rem',
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
                    width: `${qaPercent}%`,
                    borderRadius: '999px',
                    backgroundColor: '#111827',
                    transition: 'width 200ms linear',
                  }}
                />
              </div>

              <div
                style={{
                  fontSize: '0.75rem',
                  color: '#4b5563',
                  marginTop: '0.2rem',
                  textAlign: 'right',
                }}
              >
                {qaStatus?.total ? `${qaStatus?.done}/${qaStatus?.total}` : ''}
              </div>
            </div>
          )}

          {qaError && (
            <div
              style={{
                fontSize: '0.85rem',
                color: '#b91c1c',
                marginBottom: '0.65rem',
              }}
            >
              {qaError}
            </div>
          )}

          {(qaAnswer || qaAnswerMode === 'no_data') && (
            <div
              style={{
                borderTop: '1px solid #e5e7eb',
                paddingTop: '0.75rem',
              }}
            >
              <div
                style={{
                  fontSize: '0.8rem',
                  color: '#6b7280',
                  marginBottom: '0.25rem',
                }}
              >
                Respuesta
              </div>
              {(qaAnswerMode === 'fallback' || qaIsFallback) && (
                <div style={{ fontSize: '0.8rem', color: '#92400e', marginBottom: '0.35rem' }}>
                  Respuesta provisional
                </div>
              )}
              {qaAnswerMode === 'no_data' && (
                <div style={{ fontSize: '0.8rem', color: '#1f2937', marginBottom: '0.35rem' }}>
                  Sin evidencia suficiente
                </div>
              )}
              <div
                style={{
                  whiteSpace: 'pre-wrap',
                  fontSize: '0.92rem',
                  color: '#111827',
                  lineHeight: 1.45,
                }}
              >
                {qaAnswer || (qaAnswerMode === 'no_data' ? 'No hay evidencia suficiente en el proyecto para responder a esta pregunta.' : '')}
              </div>
            </div>
          )}
        </div>

        {/* Lista de tipos de gráfico */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
            gap: '1rem',
          }}
        >
          {/* Gantt */}
          <button
            type="button"
            onClick={() => openInNewTab(`/projects/${projectId}/gantt`)}
            style={{
              textAlign: 'left',
              borderRadius: '0.75rem',
              border: '1px solid #e5e7eb',
              backgroundColor: '#ffffff',
              padding: '1rem 1.1rem',
              cursor: 'pointer',
            }}
          >
            <div
              style={{
                fontSize: '0.9rem',
                fontWeight: 600,
                color: '#111827',
                marginBottom: '0.25rem',
              }}
            >
              Diagrama de Gantt
            </div>
            <p
              style={{
                fontSize: '0.85rem',
                color: '#4b5563',
                marginBottom: 0,
              }}
            >
              Visualiza la planificación prevista, las fechas reales y una
              comparación de ambas con zoom mensual.
            </p>
          </button>

          {/* Heatmap anual */}
          <button
            type="button"
            onClick={() => openInNewTab(`/projects/${projectId}/heatmap`)}
            style={{
              textAlign: 'left',
              borderRadius: '0.75rem',
              border: '1px solid #e5e7eb',
              backgroundColor: '#ffffff',
              padding: '1rem 1.1rem',
              cursor: 'pointer',
            }}
          >
            <div
              style={{
                fontSize: '0.9rem',
                fontWeight: 600,
                color: '#111827',
                marginBottom: '0.25rem',
              }}
            >
              Heatmap anual de sesiones
            </div>
            <p
              style={{
                fontSize: '0.85rem',
                color: '#4b5563',
                marginBottom: 0,
              }}
            >
              Muestra tu constancia a lo largo del año, estilo GitHub: cada día
              se colorea según las horas dedicadas al proyecto.
            </p>
          </button>

          {/* Evolución semanal */}
          <button
            type="button"
            onClick={() => openInNewTab(`/projects/${projectId}/weekly`)}
            style={{
              textAlign: 'left',
              borderRadius: '0.75rem',
              border: '1px solid #e5e7eb',
              backgroundColor: '#ffffff',
              padding: '1rem 1.1rem',
              cursor: 'pointer',
            }}
          >
            <div
              style={{
                fontSize: '0.9rem',
                fontWeight: 600,
                color: '#111827',
                marginBottom: '0.25rem',
              }}
            >
              Evolución semanal de horas
            </div>
            <p
              style={{
                fontSize: '0.85rem',
                color: '#4b5563',
                marginBottom: 0,
              }}
            >
              Ve cómo cambia tu dedicación semana a semana y detecta picos,
              valles y rachas de trabajo.
            </p>
          </button>

          {/* Desviación estimado vs real */}
          <button
            type="button"
            onClick={() => openInNewTab(`/projects/${projectId}/deviation`)}
            style={{
              textAlign: 'left',
              borderRadius: '0.75rem',
              border: '1px solid #e5e7eb',
              backgroundColor: '#ffffff',
              padding: '1rem 1.1rem',
              cursor: 'pointer',
            }}
          >
            <div
              style={{
                fontSize: '0.9rem',
                fontWeight: 600,
                color: '#111827',
                marginBottom: '0.25rem',
              }}
            >
              Desviación estimado vs real
            </div>
            <p
              style={{
                fontSize: '0.85rem',
                color: '#4b5563',
                marginBottom: 0,
              }}
            >
              Compara las horas estimadas para cada tarea con las horas reales
              invertidas y mide la precisión de tu planificación.
            </p>
          </button>

          {/* Distribución por categorías */}
          <button
            type="button"
            onClick={() => openInNewTab(`/projects/${projectId}/categories`)}
            style={{
              textAlign: 'left',
              borderRadius: '0.75rem',
              border: '1px solid #e5e7eb',
              backgroundColor: '#ffffff',
              padding: '1rem 1.1rem',
              cursor: 'pointer',
            }}
          >
            <div
              style={{
                fontSize: '0.9rem',
                fontWeight: 600,
                color: '#111827',
                marginBottom: '0.25rem',
              }}
            >
              Distribución por categorías
            </div>
            <p
              style={{
                fontSize: '0.85rem',
                color: '#4b5563',
                marginBottom: 0,
              }}
            >
              Descubre cómo se reparte tu tiempo real entre las distintas
              categorías del proyecto (TFG, MIR, trabajo, etc.).
            </p>
          </button>

          {/* Árbol del proyecto */}
          <button
            type="button"
            onClick={() => openInNewTab(`/projects/${projectId}/tree`)}
            style={{
              textAlign: 'left',
              borderRadius: '0.75rem',
              border: '1px solid #e5e7eb',
              backgroundColor: '#ffffff',
              padding: '1rem 1.1rem',
              cursor: 'pointer',
            }}
          >
            <div
              style={{
                fontSize: '0.9rem',
                fontWeight: 600,
                color: '#111827',
                marginBottom: '0.25rem',
              }}
            >
              Árbol del proyecto
            </div>
            <p
              style={{
                fontSize: '0.85rem',
                color: '#4b5563',
                marginBottom: 0,
              }}
            >
              Vista jerárquica desplegable del proyecto: tareas, subtareas y
              sesiones.
            </p>
          </button>
        </div>
      </div>
    </div>
  );
}

export default ProjectChartsPage;
