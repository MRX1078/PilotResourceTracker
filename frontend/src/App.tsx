import { Navigate, Route, Routes } from 'react-router-dom';

import { AppLayout } from './components/AppLayout';
import { BackupsPage } from './pages/BackupsPage';
import { DashboardPage } from './pages/DashboardPage';
import { EmployeeDetailPage } from './pages/EmployeeDetailPage';
import { EmployeesPage } from './pages/EmployeesPage';
import { PilotDetailPage } from './pages/PilotDetailPage';
import { PilotFormPage } from './pages/PilotFormPage';
import { PilotsListPage } from './pages/PilotsListPage';
import { UpdatesPage } from './pages/UpdatesPage';

export const App = () => {
  return (
    <Routes>
      <Route path="/" element={<AppLayout />}>
        <Route index element={<DashboardPage />} />
        <Route path="pilots" element={<PilotsListPage />} />
        <Route path="pilots/new" element={<PilotFormPage mode="create" />} />
        <Route path="pilots/:pilotId" element={<PilotDetailPage />} />
        <Route path="pilots/:pilotId/edit" element={<PilotFormPage mode="edit" />} />
        <Route path="employees" element={<EmployeesPage />} />
        <Route path="employees/:employeeId" element={<EmployeeDetailPage />} />
        <Route path="backups" element={<BackupsPage />} />
        <Route path="updates" element={<UpdatesPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};
