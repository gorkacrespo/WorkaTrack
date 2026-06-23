import { useParams } from 'react-router-dom';
import { useEffect, useMemo, useState } from 'react';

/**
 * Convierte 'YYYY-MM-DD' a Date (sin líos de zona horaria).
 */
function parseISODate(dateStr) {
  const [y, m, d] = dateStr.split('-').map((x) => Number(x));
  return new Date(y, m - 1, d);
}

/**
 * Diferencia de días entre dos fechas.
 */
function diffInDays(start, end) {
  const ms = end.getTime() - start.getTime();
  return ms / (1000 * 60 * 60 * 24);
}

/**
 * Devuelve una lista de meses entre minDate y maxDate (incluyendo ambos extremos).
 * Cada mes: { key: '2025-01', label: 'Enero', year, monthIndex }
 */
function buildMonthBuckets(minDate, maxDate) {
  const months = [
    'Enero',
    'Febrero',
    'Marzo',
    'Abril',
    'Mayo',
    'Junio',
    'Julio',
    'Agosto',
    'Septiembre',
    'Octubre',
    'Noviembre',
    'Diciembre',
  ];

  const result = [];
  const current = new Date(minDate.getFullYear(), minDate.getMonth(), 1);
  const limit = new Date(maxDate.getFullYear(), maxDate.getMonth(), 1);

  while (current <= limit) {
    const year = current.getFullYear();
    const monthIndex = current.getMonth(); // 0-11
    result.push({
      key: `${year}-${String(monthIndex + 1).padStart(2, '0')}`,
      label: `${months[monthIndex]}`,
      year,
      monthIndex,
    });
    current.setMonth(current.getMonth() + 1);
  }

  return result;
}

/**
 * Gantt "global": cabecera por MESES.
 * items: array de { id, label, start, end }
 * secondaryItems: para la vista de comparación (barras superpuestas opcionales).
 * onMonthClick: recibe el bucket del mes pulsado.
 * activeMonthKey: mes actualmente seleccionado (para resaltarlo).
 */
function SimpleGantt({ items, secondaryItems, onMonthClick, activeMonthKey }) {
  const parsedItems = useMemo(
    () =>
      items.map((it) => ({
        ...it,
        startDate: parseISODate(it.start),
        endDate: parseISODate(it.end),
      })),
    [items]
  );

  const parsedSecondary = useMemo(
    () =>
      (secondaryItems || []).map((it) => ({
        ...it,
        startDate: parseISODate(it.start),
        endDate: parseISODate(it.end),
      })),
    [secondaryItems]
  );

  const allDates = [
    ...parsedItems.map((it) => it.startDate),
    ...parsedItems.map((it) => it.endDate),
    ...parsedSecondary.map((it) => it.startDate),
    ...parsedSecondary.map((it) => it.endDate),
  ];

  if (allDates.length === 0) {
    return (
      <div
        style={{
          borderRadius: '0.75rem',
          border: '1px dashed #d1d5db',
          padding: '1.5rem',
          fontSize: '0.9rem',
          color: '#6b7280',
          textAlign: 'center',
          marginTop: '0.5rem',
        }}
      >
        No hay datos para generar el diagrama de Gantt.
      </div>
    );
  }

  const minDate = new Date(
    Math.min(...allDates.map((d) => d.getTime()))
  );
  const maxDate = new Date(
    Math.max(...allDates.map((d) => d.getTime()))
  );

  const totalDays = Math.max(diffInDays(minDate, maxDate), 1);
  const monthBuckets = buildMonthBuckets(minDate, maxDate);

  const findSecondaryFor = (id) =>
    parsedSecondary.find((s) => s.id === id) || null;

  return (
    <div style={{ overflowX: 'auto' }}>
      <div
        style={{
          minWidth: '700px',
          borderRadius: '0.75rem',
          backgroundColor: '#f9fafb',
          padding: '1rem 1.25rem',
        }}
      >
        {/* Cabecera de meses (clicables) */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: `160px repeat(${monthBuckets.length}, 1fr)`,
            columnGap: '0.25rem',
            fontSize: '0.8rem',
            color: '#4b5563',
            marginBottom: '0.5rem',
          }}
        >
          <div />{/* hueco para la columna de tareas */}
          {monthBuckets.map((m) => {
            const isActive = activeMonthKey === m.key;
            const clickable = !!onMonthClick;
            return (
              <button
                key={m.key}
                type="button"
                onClick={() => onMonthClick && onMonthClick(m)}
                style={{
                  border: 'none',
                  backgroundColor: isActive ? '#ffffff' : 'transparent',
                  borderRadius: '999px',
                  cursor: clickable ? 'pointer' : 'default',
                  textAlign: 'center',
                  fontWeight: 500,
                  padding: '0.1rem 0.4rem',
                  color: isActive ? '#111827' : '#111827',
                }}
              >
                {m.label}
              </button>
            );
          })}
        </div>

        {/* Filas de tareas */}
        <div>
          {parsedItems.map((item) => {
            const offsetDays = diffInDays(minDate, item.startDate);
            const durationDays = Math.max(
              diffInDays(item.startDate, item.endDate),
              1
            );

            const leftPercent = (offsetDays / totalDays) * 100;
            const widthPercent = (durationDays / totalDays) * 100;

            const secondary = findSecondaryFor(item.id);
            let secondaryLeftPercent = null;
            let secondaryWidthPercent = null;

            if (secondary) {
              const off2 = diffInDays(minDate, secondary.startDate);
              const dur2 = Math.max(
                diffInDays(secondary.startDate, secondary.endDate),
                1
              );
              secondaryLeftPercent = (off2 / totalDays) * 100;
              secondaryWidthPercent = (dur2 / totalDays) * 100;
            }

            return (
              <div
                key={item.id}
                style={{
                  display: 'grid',
                  gridTemplateColumns: `160px 1fr`,
                  columnGap: '0.25rem',
                  alignItems: 'center',
                  marginBottom: '0.35rem',
                }}
              >
                {/* Nombre de la tarea */}
                <div
                  style={{
                    fontSize: '0.85rem',
                    color: '#111827',
                    paddingRight: '0.5rem',
                  }}
                >
                  {item.label}
                </div>

                {/* Contenedor de la barra */}
                <div
                  style={{
                    position: 'relative',
                    height: '1rem',
                    borderRadius: '999px',
                    backgroundColor: '#e5e7eb',
                    overflow: 'hidden',
                  }}
                >
                  {/* Barra principal (previsto o real, según dataset) */}
                  <div
                    style={{
                      position: 'absolute',
                      left: `${leftPercent}%`,
                      width: `${widthPercent}%`,
                      top: '0.1rem',
                      bottom: '0.1rem',
                      borderRadius: '999px',
                      backgroundColor: '#22c55e', // verde
                    }}
                  />

                  {/* Barra secundaria para comparación (si existe) */}
                  {secondary && (
                    <div
                      style={{
                        position: 'absolute',
                        left: `${secondaryLeftPercent}%`,
                        width: `${secondaryWidthPercent}%`,
                        top: '0.25rem',
                        bottom: '0.25rem',
                        borderRadius: '999px',
                        backgroundColor: '#3b82f6', // azul
                        opacity: 0.9,
                      }}
                    />
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Leyenda para la comparación */}
        {secondaryItems && secondaryItems.length > 0 && (
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
                  backgroundColor: '#22c55e',
                }}
              />
              Previsto
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
        )}
      </div>
    </div>
  );
}

/**
 * Gantt mensual con cabecera por DÍAS del mes.
 * primaryItems / secondaryItems ya vienen recortados al mes.
 */
function MonthlyGantt({ year, monthIndex, primaryItems, secondaryItems }) {
  const parsedPrimary = useMemo(
    () =>
      primaryItems.map((it) => ({
        ...it,
        startDate: parseISODate(it.start),
        endDate: parseISODate(it.end),
      })),
    [primaryItems]
  );

  const parsedSecondary = useMemo(
    () =>
      (secondaryItems || []).map((it) => ({
        ...it,
        startDate: parseISODate(it.start),
        endDate: parseISODate(it.end),
      })),
    [secondaryItems]
  );

  const daysInMonth = new Date(year, monthIndex + 1, 0).getDate();

  const hasAny =
    parsedPrimary.length > 0 || parsedSecondary.length > 0;

  if (!hasAny) {
    return (
      <div
        style={{
          borderRadius: '0.75rem',
          border: '1px dashed #d1d5db',
          padding: '1.25rem',
          fontSize: '0.85rem',
          color: '#6b7280',
          textAlign: 'center',
        }}
      >
        En el mes seleccionado no hay tareas con fechas dentro del rango.
      </div>
    );
  }

  const findSecondaryFor = (id) =>
    parsedSecondary.find((s) => s.id === id) || null;

  return (
    <div style={{ overflowX: 'auto' }}>
      <div
        style={{
          minWidth: '700px',
          borderRadius: '0.75rem',
          backgroundColor: '#f9fafb',
          padding: '1rem 1.25rem',
        }}
      >
        {/* Cabecera con días del mes */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: `160px repeat(${daysInMonth}, 1fr)`,
            columnGap: '0.1rem',
            fontSize: '0.75rem',
            color: '#6b7280',
            marginBottom: '0.4rem',
          }}
        >
          <div />
          {Array.from({ length: daysInMonth }).map((_, i) => (
            <div
              key={i + 1}
              style={{
                textAlign: 'center',
              }}
            >
              {i + 1}
            </div>
          ))}
        </div>

        {/* Filas de tareas */}
        <div>
          {parsedPrimary.map((item) => {
            const startDay = item.startDate.getDate();
            const endDay = item.endDate.getDate();
            const offsetDays = Math.max(startDay - 1, 0);
            const durationDays = Math.max(endDay - startDay + 1, 1);

            const leftPercent = (offsetDays / daysInMonth) * 100;
            const widthPercent = (durationDays / daysInMonth) * 100;

            const secondary = findSecondaryFor(item.id);
            let secondaryLeftPercent = null;
            let secondaryWidthPercent = null;

            if (secondary) {
              const sDay = secondary.startDate.getDate();
              const eDay = secondary.endDate.getDate();
              const off2 = Math.max(sDay - 1, 0);
              const dur2 = Math.max(eDay - sDay + 1, 1);
              secondaryLeftPercent = (off2 / daysInMonth) * 100;
              secondaryWidthPercent = (dur2 / daysInMonth) * 100;
            }

            return (
              <div
                key={item.id}
                style={{
                  display: 'grid',
                  gridTemplateColumns: `160px 1fr`,
                  columnGap: '0.25rem',
                  alignItems: 'center',
                  marginBottom: '0.35rem',
                }}
              >
                <div
                  style={{
                    fontSize: '0.85rem',
                    color: '#111827',
                    paddingRight: '0.5rem',
                  }}
                >
                  {item.label}
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
                  {/* Barra principal */}
                  <div
                    style={{
                      position: 'absolute',
                      left: `${leftPercent}%`,
                      width: `${widthPercent}%`,
                      top: '0.1rem',
                      bottom: '0.1rem',
                      borderRadius: '999px',
                      backgroundColor: '#22c55e',
                    }}
                  />

                  {/* Barra secundaria para comparación */}
                  {secondary && (
                    <div
                      style={{
                        position: 'absolute',
                        left: `${secondaryLeftPercent}%`,
                        width: `${secondaryWidthPercent}%`,
                        top: '0.25rem',
                        bottom: '0.25rem',
                        borderRadius: '999px',
                        backgroundColor: '#3b82f6',
                        opacity: 0.9,
                      }}
                    />
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {secondaryItems && secondaryItems.length > 0 && (
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
                  backgroundColor: '#22c55e',
                }}
              />
              Previsto
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
        )}
      </div>
    </div>
  );
}

function ProjectGanttPage() {
  const { projectId } = useParams();
  const [projectInfo, setProjectInfo] = useState(null);

  // Recuperamos nombre, color y progreso guardados en localStorage
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

  // Vistas: previsto / real / comparación
  const [view, setView] = useState('planned'); // 'planned' | 'actual' | 'compare'

  /**
   * DATOS DE EJEMPLO:
   * Más adelante estos vendrán del backend (tareas + sesiones reales).
   */
  const plannedItems = useMemo(
    () => [
      {
        id: 1,
        label: 'Tarea 1',
        start: '2025-01-05',
        end: '2025-02-10',
      },
      {
        id: 2,
        label: 'Tarea 2',
        start: '2025-02-01',
        end: '2025-03-15',
      },
      {
        id: 3,
        label: 'Tarea 3',
        start: '2025-03-10',
        end: '2025-04-05',
      },
      {
        id: 4,
        label: 'Tarea 4',
        start: '2025-03-20',
        end: '2025-05-01',
      },
      {
        id: 5,
        label: 'Tarea 5',
        start: '2025-04-15',
        end: '2025-06-10',
      },
    ],
    []
  );

  // Simulación de fechas reales
  const actualItems = useMemo(
    () =>
      plannedItems.map((p) => {
        const startDate = parseISODate(p.start);
        const endDate = parseISODate(p.end);
        const delayedStart = new Date(startDate);
        delayedStart.setDate(delayedStart.getDate() + 3);
        const newEnd = new Date(endDate);
        newEnd.setDate(newEnd.getDate() + (p.id % 2 === 0 ? 5 : -2));

        const toISO = (d) =>
          [
            d.getFullYear(),
            String(d.getMonth() + 1).padStart(2, '0'),
            String(d.getDate()).padStart(2, '0'),
          ].join('-');

        return {
          id: p.id,
          label: p.label,
          start: toISO(delayedStart),
          end: toISO(newEnd),
        };
      }),
    [plannedItems]
  );

  // Qué dataset usamos en la vista principal (global)
  let ganttPrimary = plannedItems;
  let ganttSecondary = null;

  if (view === 'actual') {
    ganttPrimary = actualItems;
  } else if (view === 'compare') {
    ganttPrimary = plannedItems;
    ganttSecondary = actualItems;
  }

  // -------- Vista mensual detallada (controlada por clic en meses) --------

  // Para calcular los meses disponibles usamos tanto previsto como real
  const allForMonths = useMemo(
    () => [...plannedItems, ...actualItems],
    [plannedItems, actualItems]
  );

  const monthBuckets = useMemo(() => {
    if (!allForMonths.length) return [];

    const parsed = allForMonths.map((it) => ({
      ...it,
      startDate: parseISODate(it.start),
      endDate: parseISODate(it.end),
    }));

    const allDates = [
      ...parsed.map((it) => it.startDate),
      ...parsed.map((it) => it.endDate),
    ];

    if (!allDates.length) return [];

    const minDate = new Date(
      Math.min(...allDates.map((d) => d.getTime()))
    );
    const maxDate = new Date(
      Math.max(...allDates.map((d) => d.getTime()))
    );

    return buildMonthBuckets(minDate, maxDate);
  }, [allForMonths]);

  const [selectedMonthKey, setSelectedMonthKey] = useState(null);

  const selectedMonthMeta = useMemo(
    () =>
      monthBuckets.find((m) => m.key === selectedMonthKey) || null,
    [monthBuckets, selectedMonthKey]
  );

  // Función para recortar un array de items a un mes concreto
  const clampItemsToMonth = (items, monthMeta) => {
    if (!monthMeta || !items) return [];

    const monthStart = new Date(
      monthMeta.year,
      monthMeta.monthIndex,
      1
    );
    const monthEnd = new Date(
      monthMeta.year,
      monthMeta.monthIndex + 1,
      0
    );

    return items
      .map((it) => {
        const s = parseISODate(it.start);
        const e = parseISODate(it.end);

        if (e < monthStart || s > monthEnd) {
          return null;
        }

        const clampedStart =
          s < monthStart ? monthStart : s;
        const clampedEnd = e > monthEnd ? monthEnd : e;

        const toISO = (d) =>
          [
            d.getFullYear(),
            String(d.getMonth() + 1).padStart(2, '0'),
            String(d.getDate()).padStart(2, '0'),
          ].join('-');

        return {
          id: it.id,
          label: it.label,
          start: toISO(clampedStart),
          end: toISO(clampedEnd),
        };
      })
      .filter(Boolean);
  };

  // Primary/secondary para el zoom mensual según la vista
  const monthlyPrimaryItems = useMemo(
    () => clampItemsToMonth(ganttPrimary, selectedMonthMeta),
    [ganttPrimary, selectedMonthMeta]
  );

  const monthlySecondaryItems = useMemo(
    () => clampItemsToMonth(ganttSecondary, selectedMonthMeta),
    [ganttSecondary, selectedMonthMeta]
  );

  // Cuando se hace clic en un mes del Gantt global
  const handleMonthClick = (monthBucket) => {
    setSelectedMonthKey(monthBucket.key);
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
        {/* Cabecera con progreso global grande */}
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
            Diagrama de Gantt
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
            Visualiza cómo se distribuyen tus tareas a lo largo del tiempo.
            Puedes alternar entre la planificación prevista, las fechas
            reales y una vista comparativa. Si quieres acercarte a un mes,
            haz clic en su nombre en la vista global para abrir un zoom
            detallado.
          </p>

          {/* Barra de progreso a lo ancho del bloque de texto */}
          <div
            style={{
              marginTop: '0.1rem',
            }}
          >
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

        {/* Selector de vista: previsto / real / comparación */}
        <div
          style={{
            marginBottom: '1rem',
            display: 'inline-flex',
            padding: '0.2rem',
            borderRadius: '999px',
            backgroundColor: '#e5e7eb',
          }}
        >
          {[
            { key: 'planned', label: 'Previsto' },
            { key: 'actual', label: 'Real' },
            { key: 'compare', label: 'Comparación' },
          ].map((opt) => {
            const active = view === opt.key;
            return (
              <button
                key={opt.key}
                type="button"
                onClick={() => setView(opt.key)}
                style={{
                  border: 'none',
                  borderRadius: '999px',
                  padding: '0.3rem 0.9rem',
                  fontSize: '0.8rem',
                  cursor: 'pointer',
                  backgroundColor: active ? '#ffffff' : 'transparent',
                  color: active ? '#111827' : '#374151',
                }}
              >
                {opt.label}
              </button>
            );
          })}
        </div>

        {/* --- Vista global del proyecto (PRIMERO) --- */}
        <div>
          <h2
            style={{
              fontSize: '0.9rem',
              fontWeight: 600,
              color: '#111827',
              marginBottom: '0.3rem',
            }}
          >
            Vista global del proyecto
          </h2>
          <p
            style={{
              fontSize: '0.85rem',
              color: '#4b5563',
              marginBottom: '0.5rem',
            }}
          >
            Visión general del proyecto completo. Haz clic en el nombre de
            un mes para abrir un zoom detallado de ese tramo.
          </p>

          <div
            style={{
              backgroundColor: '#ffffff',
              borderRadius: '0.75rem',
              border: '1px solid #e5e7eb',
              padding: '1rem 1.25rem 1.25rem',
              minHeight: '260px',
            }}
          >
            <SimpleGantt
              items={ganttPrimary}
              secondaryItems={ganttSecondary}
              onMonthClick={handleMonthClick}
              activeMonthKey={selectedMonthKey}
            />
          </div>
        </div>

        {/* --- Vista mensual detallada (solo si se ha elegido un mes) --- */}
        {selectedMonthMeta && (
          <div
            style={{
              marginTop: '1.5rem',
            }}
          >
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '0.6rem',
                gap: '0.75rem',
              }}
            >
              <div>
                <h2
                  style={{
                    fontSize: '0.95rem',
                    fontWeight: 600,
                    color: '#111827',
                    margin: 0,
                    marginBottom: '0.1rem',
                  }}
                >
                  Vista mensual detallada – {selectedMonthMeta.label}
                </h2>
                <p
                  style={{
                    fontSize: '0.85rem',
                    color: '#4b5563',
                    margin: 0,
                  }}
                >
                  Zoom del mes seleccionado con vista por días. Si estás en
                  modo comparación, verás superpuestas las barras previstas
                  y reales dentro de este mes.
                </p>
              </div>
            </div>

            <div
              style={{
                backgroundColor: '#ffffff',
                borderRadius: '0.75rem',
                border: '1px solid #e5e7eb',
                padding: '1rem 1.25rem 1.25rem',
                minHeight: '260px',
              }}
            >
              <MonthlyGantt
                year={selectedMonthMeta.year}
                monthIndex={selectedMonthMeta.monthIndex}
                primaryItems={monthlyPrimaryItems}
                secondaryItems={monthlySecondaryItems}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default ProjectGanttPage;
