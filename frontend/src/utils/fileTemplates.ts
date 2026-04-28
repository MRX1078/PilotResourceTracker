export interface DownloadableTemplate {
  filename: string;
  mimeType: string;
  content: string;
  withBom?: boolean;
}

const EMPLOYEES_CSV_TEMPLATE_CONTENT = [
  'cas_id,full_name,rc',
  'cas001,Иванов Иван,RC-Alpha',
  'cas002,Петров Петр,RC-Beta',
  'cas003,Сидорова Анна,RC-Gamma',
].join('\n');

const ASSIGNMENTS_CSV_TEMPLATE_CONTENT = [
  'week_start_date,cas_id,hours,load_percent,pshe,source',
  '2026-04-20,cas001,40,100,1,manual',
  '2026-04-20,cas002,24,60,0.6,manual',
  '2026-04-20,cas003,16,40,0.4,manual',
].join('\n');

const TRINO_SQL_TEMPLATE_CONTENT = `SELECT
    CAST(event_date AS DATE) AS date,
    cas,
    SUM(hours_spent) AS hours,
    SUM(hours_spent) / 40.0 * 100 AS load_percent
FROM some_schema.some_table
WHERE pilot_name = 'Pilot A'
GROUP BY 1, 2;`;

export const FILE_TEMPLATES = {
  employeesCsv: {
    filename: 'employees_template.csv',
    mimeType: 'text/csv;charset=utf-8',
    content: EMPLOYEES_CSV_TEMPLATE_CONTENT,
    withBom: true,
  } satisfies DownloadableTemplate,
  assignmentsCsv: {
    filename: 'pilot_assignments_template.csv',
    mimeType: 'text/csv;charset=utf-8',
    content: ASSIGNMENTS_CSV_TEMPLATE_CONTENT,
    withBom: true,
  } satisfies DownloadableTemplate,
  trinoSql: {
    filename: 'trino_pilot_template.sql',
    mimeType: 'text/sql;charset=utf-8',
    content: TRINO_SQL_TEMPLATE_CONTENT,
  } satisfies DownloadableTemplate,
};

export const downloadTemplate = (template: DownloadableTemplate) => {
  const content = template.withBom ? `\uFEFF${template.content}` : template.content;
  const blob = new Blob([content], { type: template.mimeType });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = template.filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};
