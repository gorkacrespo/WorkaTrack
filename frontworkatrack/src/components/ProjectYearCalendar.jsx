import { useMemo, useState } from 'react';

/**
 * Calendario anual minimalista para proyectos / tareas / hitos.
 *
 * shapes:
 * - circle  → inicios
 * - triangle → finales
 * - square  → hitos
 */

function getYearFromDateString(dateStr) {
  if (!dateStr) return null;
  const [datePart] = dateStr.split('T');
  const [year] = datePart.split('-');
  const yearNum = Number(year);
  return Number.isNaN(yearNum) ? null : yearNum;
}

function ProjectYearCalendar({ projects }) {
  const availableYears = useMemo(() => {
    const years = new Set();
    projects.forEach((p) => {
      const y = getYearFromDateString(p.createdAt);
      if (y) years.add(y);
    });
    if (years.size === 0) years.add(new Date().getFullYear());
    return Array.from(years).sort((a, b) => b - a);
  }, [projects]);

  const [selectedYear, setSelectedYear] = useState(availableYears[0]);

  const monthNames = [
    'Enero','Febrero','Marzo','Abril','Mayo','Junio',
    'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre',
  ];

  const getDaysInMonth = (year, monthIndex) =>
    Array.from(
      { length: new Date(year, monthIndex + 1, 0).getDate() },
      (_, i) => i + 1
    );

  const projectsByDate = useMemo(() => {
    const map = {};
    projects.forEach((p) => {
      if (!p.createdAt) return;
      const [datePart] = p.createdAt.split('T');
      if (getYearFromDateString(datePart) !== selectedYear) return;
      if (!map[datePart]) map[datePart] = [];
      map[datePart].push(p);
    });
    return map;
  }, [projects, selectedYear]);

  return (
    <div className="year-calendar">
      <div className="year-calendar-header">
        <span>Año:</span>
        <select
          value={selectedYear}
          onChange={(e) => setSelectedYear(Number(e.target.value))}
        >
          {availableYears.map((y) => (
            <option key={y} value={y}>{y}</option>
          ))}
        </select>
      </div>

      <div className="year-calendar-grid">
        {monthNames.map((name, monthIndex) => (
          <div key={name} className="year-calendar-month">
            <div className="year-calendar-month-name">{name}</div>

            <div className="year-calendar-days-grid">
              {getDaysInMonth(selectedYear, monthIndex).map((day) => {
                const key = `${selectedYear}-${String(monthIndex + 1).padStart(2,'0')}-${String(day).padStart(2,'0')}`;
                const dayItems = projectsByDate[key] || [];

                const hasMultipleEvents = dayItems.length > 1;

                const referenceItem =
                  !hasMultipleEvents
                    ? (
                        dayItems.find((p) => p.type === 'milestone') ||
                        dayItems.find((p) => p.type?.endsWith('-end')) ||
                        dayItems[0]
                      )
                    : null;

                const color = referenceItem?.color || '#111827';
                const type = referenceItem?.type || 'default';

                const tooltip = dayItems.length === 1 ? dayItems[0].name : dayItems.map((p) => `• ${p.name}`).join('\n');

                let shapeStyle = null;

                //multiples eventos en un dia
                if (hasMultipleEvents) {
                  // ⭐ estrella
                  shapeStyle = {
                    backgroundColor: '#111827',
                    clipPath:
                      'polygon(50% 0%, 61% 35%, 98% 35%, 68% 57%, 79% 91%, 50% 70%, 21% 91%, 32% 57%, 2% 35%, 39% 35%)',
                   };
                 } 
                // ⬛ HITO
                else if (type === 'milestone') {
                  shapeStyle = {
                    backgroundColor: color,
                    borderRadius: '0.25rem',
                  };
                }
                // 🔺 FIN
                else if (type.endsWith('-end')) {
                  shapeStyle = {
                    backgroundColor: color,
                    clipPath: 'polygon(50% 0%, 0% 100%, 100% 100%)',
                  };
                }
                // ⚪ INICIO
                else {
                  shapeStyle = {
                    backgroundColor: color,
                    borderRadius: '999px',
                  };
                }

                return (
                  <div
                    key={day}
                    className="year-calendar-day"
                    title={tooltip}
                  >
                    <span
                      className="year-calendar-day-number"
                      style={
                        (hasMultipleEvents || referenceItem)
                          ? {
                              ...shapeStyle,
                              color: '#fff',
                              width: '20px',
                              height: '20px',
                              display: 'inline-flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              fontSize: '0.7rem',
                            }
                          : undefined
                      }
                    >
                      {day}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default ProjectYearCalendar;
