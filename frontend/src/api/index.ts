import { apiClient } from './client';
import {
  Assignment,
  BackupImportResponse,
  AssignmentCsvImportResponse,
  AssignmentPayload,
  DashboardSummary,
  CrossAssignmentItem,
  EmployeeDetail,
  EmployeeCsvImportResponse,
  EmployeeListItem,
  EmployeePilotLoad,
  Pilot,
  PilotListItem,
  PilotPayload,
  PilotWeeklyMetric,
  RefreshAllResponse,
  RefreshPilotResponse,
  ResourceByRcItem,
  ResourceLoadItem,
  SqlValidationResponse,
  TrinoConnectionConfig,
  TrinoRun,
  WeeklyCostPoint,
} from '../types/api';

export const api = {
  getPilots: async () => (await apiClient.get<PilotListItem[]>('/pilots')).data,
  getPilot: async (pilotId: number) => (await apiClient.get<Pilot>(`/pilots/${pilotId}`)).data,
  createPilot: async (payload: PilotPayload) => (await apiClient.post<Pilot>('/pilots', payload)).data,
  updatePilot: async (pilotId: number, payload: Partial<PilotPayload>) =>
    (await apiClient.put<Pilot>(`/pilots/${pilotId}`, payload)).data,
  deletePilot: async (pilotId: number) => apiClient.delete(`/pilots/${pilotId}`),
  refreshPilot: async (pilotId: number) =>
    (await apiClient.post<RefreshPilotResponse>(`/pilots/${pilotId}/refresh`)).data,
  refreshAllPilots: async () =>
    (await apiClient.post<RefreshAllResponse>('/pilots/refresh-all')).data,
  validateSql: async (payload: { sql_query: string } & Partial<TrinoConnectionConfig>) =>
    (await apiClient.post<SqlValidationResponse>('/pilots/validate-sql', payload)).data,

  getAssignments: async (pilotId: number, weekStartDate?: string) => {
    const params = weekStartDate ? { week_start_date: weekStartDate } : undefined;
    return (await apiClient.get<Assignment[]>(`/pilots/${pilotId}/assignments`, { params })).data;
  },
  createAssignment: async (pilotId: number, payload: AssignmentPayload) =>
    (await apiClient.post<Assignment>(`/pilots/${pilotId}/assignments`, payload)).data,
  importAssignmentsCsv: async (pilotId: number, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return (
      await apiClient.post<AssignmentCsvImportResponse>(`/pilots/${pilotId}/assignments/import-csv`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
    ).data;
  },
  updateAssignment: async (assignmentId: number, payload: Partial<AssignmentPayload>) =>
    (await apiClient.put<Assignment>(`/assignments/${assignmentId}`, payload)).data,
  deleteAssignment: async (assignmentId: number) => apiClient.delete(`/assignments/${assignmentId}`),

  getMetrics: async (pilotId: number, startWeek?: string, endWeek?: string) => {
    const params: Record<string, string> = {};
    if (startWeek) params.start_week = startWeek;
    if (endWeek) params.end_week = endWeek;
    return (await apiClient.get<PilotWeeklyMetric[]>(`/pilots/${pilotId}/metrics`, { params })).data;
  },

  getDashboardSummary: async (params: { weekStartDate?: string; startWeek?: string; endWeek?: string }) =>
    (
      await apiClient.get<DashboardSummary>('/dashboard/summary', {
        params: {
          week_start_date: params.weekStartDate,
          start_week: params.startWeek,
          end_week: params.endWeek,
        },
      })
    ).data,
  getCrossAssignments: async (params: { weekStartDate?: string; startWeek?: string; endWeek?: string }) =>
    (
      await apiClient.get<CrossAssignmentItem[]>('/dashboard/cross-assignments', {
        params: {
          week_start_date: params.weekStartDate,
          start_week: params.startWeek,
          end_week: params.endWeek,
        },
      })
    ).data,
  getWeeklyCosts: async (params: { weeks?: number; startWeek?: string; endWeek?: string }) =>
    (
      await apiClient.get<WeeklyCostPoint[]>('/dashboard/weekly-costs', {
        params: {
          weeks: params.weeks,
          start_week: params.startWeek,
          end_week: params.endWeek,
        },
      })
    ).data,
  getResourceLoad: async (params: { weekStartDate?: string; startWeek?: string; endWeek?: string }) =>
    (
      await apiClient.get<ResourceLoadItem[]>('/dashboard/resource-load', {
        params: {
          week_start_date: params.weekStartDate,
          start_week: params.startWeek,
          end_week: params.endWeek,
        },
      })
    ).data,
  getResourceByRc: async (params: { weekStartDate?: string; startWeek?: string; endWeek?: string }) =>
    (
      await apiClient.get<ResourceByRcItem[]>('/dashboard/resource-by-rc', {
        params: {
          week_start_date: params.weekStartDate,
          start_week: params.startWeek,
          end_week: params.endWeek,
        },
      })
    ).data,

  getEmployees: async (search?: string) =>
    (await apiClient.get<EmployeeListItem[]>('/employees', { params: { search } })).data,
  importEmployeesCsv: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return (
      await apiClient.post<EmployeeCsvImportResponse>('/employees/import-csv', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
    ).data;
  },
  getEmployee: async (employeeId: number, weekStartDate?: string) =>
    (
      await apiClient.get<EmployeeDetail>(`/employees/${employeeId}`, {
        params: weekStartDate ? { week_start_date: weekStartDate } : undefined,
      })
    ).data,
  getEmployeePilots: async (employeeId: number, weekStartDate?: string) =>
    (
      await apiClient.get<EmployeePilotLoad[]>(`/employees/${employeeId}/pilots`, {
        params: weekStartDate ? { week_start_date: weekStartDate } : undefined,
      })
    ).data,

  getTrinoRuns: async (limit = 100) =>
    (await apiClient.get<TrinoRun[]>('/trino-runs', { params: { limit } })).data,

  exportBackup: async () => {
    const response = await apiClient.get<Blob>('/system/backup/export', {
      responseType: 'blob',
    });
    const disposition = response.headers['content-disposition'] as string | undefined;
    const filenameMatch = disposition?.match(/filename=\"?([^\";]+)\"?/i);
    const filename = filenameMatch?.[1] ?? 'pilot_tracker_backup.json';
    return { blob: response.data, filename };
  },
  importBackup: async (file: File, runRefreshAllSql: boolean) => {
    const formData = new FormData();
    formData.append('file', file);
    return (
      await apiClient.post<BackupImportResponse>(
        '/system/backup/import',
        formData,
        {
          params: { run_refresh_all_sql: runRefreshAllSql },
          headers: { 'Content-Type': 'multipart/form-data' },
        }
      )
    ).data;
  },
};
