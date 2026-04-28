export type AccountingMode = 'manual' | 'sql';
export type AssignmentSource = 'manual' | 'sql';
export type QueryRunStatus = 'pending' | 'running' | 'success' | 'failed';

export interface TrinoConnectionConfig {
  trino_host: string | null;
  trino_port: number | null;
  trino_user: string | null;
  trino_password: string | null;
  trino_catalog: string | null;
  trino_schema: string | null;
  trino_http_scheme: 'http' | 'https' | null;
}

export interface PilotMetricSnapshot {
  week_start_date: string;
  total_cost: string;
  total_pshe: string;
}

export interface Pilot extends TrinoConnectionConfig {
  id: number;
  name: string;
  description: string | null;
  annual_revenue: string;
  accounting_mode: AccountingMode;
  sql_query: string | null;
  additional_pshe_default: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface PilotListItem extends Pilot {
  latest_metric: PilotMetricSnapshot | null;
  employees_count: number;
  last_refresh_status: QueryRunStatus | null;
  last_refresh_started_at: string | null;
}

export interface PilotPayload extends Partial<TrinoConnectionConfig> {
  name: string;
  description?: string | null;
  annual_revenue: number;
  accounting_mode: AccountingMode;
  sql_query?: string | null;
  additional_pshe_default: number;
  is_active?: boolean;
}

export interface PilotWeeklyMetric {
  id: number;
  pilot_id: number;
  week_start_date: string;
  total_hours: string;
  total_pshe: string;
  additional_pshe: string;
  total_cost: string;
  annual_revenue: string;
  weekly_revenue_estimate: string;
  profitability_estimate: string;
  created_at: string;
  updated_at: string;
}

export interface AssignmentEmployee {
  id: number;
  cas: string | null;
  full_name: string;
  rc: string;
}

export interface OtherPilotInfo {
  pilot_id: number;
  pilot_name: string;
}

export interface Assignment {
  id: number;
  pilot_id: number;
  employee_id: number;
  week_start_date: string;
  load_percent: string;
  pshe: string;
  hours: string;
  source: AssignmentSource;
  created_at: string;
  updated_at: string;
  employee: AssignmentEmployee;
  other_pilots: OtherPilotInfo[];
}

export interface AssignmentPayload {
  employee_id?: number;
  week_start_date: string;
  load_percent?: number;
  pshe?: number;
  hours?: number;
  source?: AssignmentSource;
  cas?: string;
  full_name?: string;
  rc?: string;
}

export interface AssignmentCsvImportError {
  row_number: number;
  error: string;
}

export interface AssignmentCsvImportResponse {
  total_rows: number;
  imported_count: number;
  created_count: number;
  updated_count: number;
  weeks_affected: string[];
  errors: AssignmentCsvImportError[];
}

export interface DashboardTopPilot {
  pilot_id: number;
  pilot_name: string;
  total_cost: string;
  total_pshe: string;
}

export interface DashboardPilotAllocation {
  pilot_id: number;
  pilot_name: string;
  total_hours: string;
  total_pshe: string;
  total_cost: string;
  employees_count: number;
  cost_share_percent: string;
}

export interface DashboardProfitabilityItem {
  pilot_id: number;
  pilot_name: string;
  revenue_estimate: string;
  total_cost: string;
  profitability_estimate: string;
  margin_percent: string;
}

export interface DashboardSummary {
  period_start_date: string;
  period_end_date: string;
  weeks_count: number;
  active_pilots_count: number;
  total_cost: string;
  total_pshe: string;
  active_employees_count: number;
  resource_allocation: DashboardPilotAllocation[];
  worst_profitability_pilots: DashboardProfitabilityItem[];
}

export interface CrossAssignmentItem {
  employee_id: number;
  cas: string | null;
  full_name: string;
  rc: string;
  pilot_count: number;
  pilots: string[];
  total_load_percent: string;
  overloaded: boolean;
}

export interface WeeklyCostPoint {
  week_start_date: string;
  total_cost: string;
  total_pshe: string;
}

export interface ResourceLoadItem {
  employee_id: number;
  full_name: string;
  cas: string | null;
  total_load_percent: string;
  total_hours: string;
  overloaded: boolean;
}

export interface ResourceByRcItem {
  rc: string;
  employees_count: number;
  pilots_count: number;
  total_hours: string;
  total_pshe: string;
  load_share_percent: string;
}

export interface BackupCounts {
  pilots: number;
  employees: number;
  assignments: number;
  metrics: number;
  trino_query_runs: number;
}

export interface BackupSettings {
  work_hours_per_week: number;
  cost_per_minute: number;
}

export interface BackupImportResponse {
  message: string;
  imported_at: string;
  imported: BackupCounts;
  settings_from_backup: BackupSettings;
  refresh_all_result: RefreshAllResponse | null;
  warnings: string[];
}

export interface EmployeePilotLoad {
  pilot_id: number;
  pilot_name: string;
  week_start_date: string;
  load_percent: string;
  hours: string;
  pshe: string;
}

export interface EmployeeListItem {
  id: number;
  cas: string | null;
  full_name: string;
  rc: string;
}

export interface EmployeeCsvImportError {
  row_number: number;
  error: string;
}

export interface EmployeeCsvImportResponse {
  total_rows: number;
  imported_count: number;
  created_count: number;
  updated_count: number;
  errors: EmployeeCsvImportError[];
}

export interface EmployeeWeeklyLoad {
  week_start_date: string;
  total_load_percent: string;
  total_hours: string;
}

export interface EmployeeDetail {
  id: number;
  cas: string | null;
  full_name: string;
  rc: string;
  created_at: string;
  updated_at: string;
  pilots: EmployeePilotLoad[];
  weekly_loads: EmployeeWeeklyLoad[];
  selected_week_total_load_percent: string;
  is_overloaded: boolean;
}

export interface TrinoRun {
  id: number;
  pilot_id: number;
  pilot_name: string;
  started_at: string;
  finished_at: string | null;
  status: QueryRunStatus;
  error_message: string | null;
  rows_returned: number;
}

export interface RefreshPilotResponse {
  pilot_id: number;
  pilot_name: string;
  rows_processed: number;
  message: string;
}

export interface RefreshAllError {
  pilot_id: number;
  pilot_name: string;
  error: string;
}

export interface RefreshAllResponse {
  success_count: number;
  failed_count: number;
  errors: RefreshAllError[];
}

export interface SqlValidationResponse {
  is_valid: boolean;
  columns: string[];
  message: string;
}
