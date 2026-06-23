import { Routes, Route, Navigate } from 'react-router-dom';
import AuthPage from './pages/AuthPage';
import ProjectsPage from './pages/ProjectsPage';
import ProjectDetailPage from './pages/ProjectDetailPage';
import TaskDetailPage from './pages/TaskDetailPage';
import ProjectChartsPage from './pages/ProjectChartsPage';
import ProjectGanttPage from './pages/ProjectGanttPage';
import ProjectHeatmapPage from './pages/ProjectHeatmapPage';
import ProjectWeeklyChartPage from './pages/ProjectWeeklyChartPage'; // ⬅️ ESTE
import ProjectDeviationPage from './pages/ProjectDeviationPage';
import ProjectCategoriesPage from './pages/ProjectCategoriesPage';
import ProjectTreePage from './pages/ProjectTreePage';

function App() {
  return (
    <Routes>
      {/* Página inicial: Login / Registro */}
      <Route path="/" element={<AuthPage />} />

      {/* Lista de proyectos */}
      <Route path="/projects" element={<ProjectsPage />} />

      {/* Detalle de un proyecto */}
      <Route path="/projects/:projectId" element={<ProjectDetailPage />} />

      {/* Detalle de una tarea dentro de un proyecto */}
      <Route
        path="/projects/:projectId/tasks/:taskId"
        element={<TaskDetailPage />}
      />

      {/* Lista de tipos de gráfico del proyecto */}
      <Route
        path="/projects/:projectId/charts"
        element={<ProjectChartsPage />}
      />

      {/* Diagrama de Gantt */}
      <Route
        path="/projects/:projectId/gantt"
        element={<ProjectGanttPage />}
      />

      {/* Heatmap anual de sesiones */}
      <Route
        path="/projects/:projectId/heatmap"
        element={<ProjectHeatmapPage />}
      />

      {/* Evolución semanal de horas */}
      <Route
        path="/projects/:projectId/weekly"
        element={<ProjectWeeklyChartPage />}
      />

      {/* Desviación estimado vs real */}
      <Route
        path="/projects/:projectId/deviation"
        element={<ProjectDeviationPage />}
      />

      {/* Distribución por categorías */}
      <Route
        path="/projects/:projectId/categories"
        element={<ProjectCategoriesPage />}
      />

      {/* Árbol del proyecto */}
      <Route
        path="/projects/:projectId/tree"
        element={<ProjectTreePage />}
      />


      {/* Redirección si la ruta no existe */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
