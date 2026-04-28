import { DownloadOutlined, FileTextOutlined, UploadOutlined } from '@ant-design/icons';
import { Alert, Button, Card, Descriptions, Space, Switch, Typography, Upload, message } from 'antd';
import { useState } from 'react';

import { api } from '../api';
import { BackupImportResponse } from '../types/api';
import { downloadTemplate, FILE_TEMPLATES } from '../utils/fileTemplates';

export const BackupsPage = () => {
  const [exportLoading, setExportLoading] = useState(false);
  const [importLoading, setImportLoading] = useState(false);
  const [runRefreshAfterImport, setRunRefreshAfterImport] = useState(true);
  const [lastImportResult, setLastImportResult] = useState<BackupImportResponse | null>(null);

  const handleExportBackup = async () => {
    setExportLoading(true);
    try {
      const { blob, filename } = await api.exportBackup();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      message.success('Файл бэкапа скачан');
    } catch (error) {
      message.error(`Не удалось скачать бэкап: ${(error as Error).message}`);
    } finally {
      setExportLoading(false);
    }
  };

  const handleImportBackup = async (file: File) => {
    setImportLoading(true);
    try {
      const result = await api.importBackup(file, runRefreshAfterImport);
      setLastImportResult(result);
      message.success('Бэкап успешно импортирован');
    } catch (error) {
      message.error(`Не удалось импортировать бэкап: ${(error as Error).message}`);
    } finally {
      setImportLoading(false);
    }
    return false;
  };

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Card className="page-card">
        <Space direction="vertical" size={8} style={{ width: '100%' }}>
          <Typography.Title level={4} style={{ margin: 0 }}>
            Резервные копии и перенос между коллегами
          </Typography.Title>
          <Typography.Text type="secondary">
            Скачайте JSON-бэкап со всеми пилотами, SQL-запросами, сотрудниками, назначениями, метриками и историей refresh.
          </Typography.Text>
          <Alert
            showIcon
            type="info"
            message="Рекомендуемый поток"
            description="Коллега экспортирует бэкап, передает файл, вы импортируете его и при необходимости сразу запускаете синхронизацию SQL-пилотов."
          />
        </Space>
      </Card>

      <Card className="page-card" title="Экспорт бэкапа">
        <Space direction="vertical" size={10}>
          <Typography.Text>
            Экспорт создает один JSON-файл, который можно передать в полу-оффлайн режиме.
          </Typography.Text>
          <Button type="primary" icon={<DownloadOutlined />} loading={exportLoading} onClick={() => void handleExportBackup()}>
            Скачать бэкап
          </Button>
        </Space>
      </Card>

      <Card className="page-card" title="Шаблоны для быстрого старта">
        <Space direction="vertical" size={12} style={{ width: '100%' }}>
          <Typography.Text>
            Скачайте готовые шаблоны для импорта сотрудников, назначений и пример SQL-запроса для пилотов в SQL-режиме.
          </Typography.Text>
          <Space wrap>
            <Button
              icon={<FileTextOutlined />}
              onClick={() => downloadTemplate(FILE_TEMPLATES.employeesCsv)}
            >
              Шаблон сотрудников CSV
            </Button>
            <Button
              icon={<FileTextOutlined />}
              onClick={() => downloadTemplate(FILE_TEMPLATES.assignmentsCsv)}
            >
              Шаблон назначений CSV
            </Button>
            <Button
              icon={<FileTextOutlined />}
              onClick={() => downloadTemplate(FILE_TEMPLATES.trinoSql)}
            >
              Шаблон SQL для Trino
            </Button>
          </Space>
          <Alert
            showIcon
            type="info"
            message="Подсказка"
            description="Сначала импортируйте справочник сотрудников по cas_id/cas, затем назначайте их в ручные пилоты по CAS."
          />
        </Space>
      </Card>

      <Card className="page-card" title="Импорт бэкапа">
        <Space direction="vertical" size={12} style={{ width: '100%' }}>
          <Typography.Text>
            Импорт заменяет текущие данные базы на содержимое файла бэкапа.
          </Typography.Text>

          <Space>
            <Typography.Text>После импорта запустить refresh-all SQL:</Typography.Text>
            <Switch checked={runRefreshAfterImport} onChange={setRunRefreshAfterImport} />
          </Space>

          <Upload
            accept=".json,application/json"
            maxCount={1}
            showUploadList={false}
            beforeUpload={(file) => {
              void handleImportBackup(file);
              return false;
            }}
          >
            <Button icon={<UploadOutlined />} loading={importLoading}>
              Загрузить бэкап
            </Button>
          </Upload>

          <Typography.Text type="secondary">
            Важно: импорт перезапишет текущую базу. Перед импортом можно сделать свежий экспорт как точку возврата.
          </Typography.Text>
        </Space>
      </Card>

      {lastImportResult && (
        <Card className="page-card" title="Результат последнего импорта">
          <Descriptions column={1} size="small" bordered>
            <Descriptions.Item label="Статус">{lastImportResult.message}</Descriptions.Item>
            <Descriptions.Item label="Импортировано пилотов">{lastImportResult.imported.pilots}</Descriptions.Item>
            <Descriptions.Item label="Импортировано сотрудников">{lastImportResult.imported.employees}</Descriptions.Item>
            <Descriptions.Item label="Импортировано назначений">{lastImportResult.imported.assignments}</Descriptions.Item>
            <Descriptions.Item label="Импортировано метрик">{lastImportResult.imported.metrics}</Descriptions.Item>
            <Descriptions.Item label="Импортировано запусков SQL">{lastImportResult.imported.trino_query_runs}</Descriptions.Item>
            <Descriptions.Item label="WORK_HOURS_PER_WEEK из файла">
              {lastImportResult.settings_from_backup.work_hours_per_week}
            </Descriptions.Item>
            <Descriptions.Item label="COST_PER_MINUTE из файла">
              {lastImportResult.settings_from_backup.cost_per_minute}
            </Descriptions.Item>
          </Descriptions>

          {lastImportResult.refresh_all_result && (
            <Alert
              style={{ marginTop: 12 }}
              type={lastImportResult.refresh_all_result.failed_count > 0 ? 'warning' : 'success'}
              showIcon
              message={`Refresh-all: успешно ${lastImportResult.refresh_all_result.success_count}, ошибок ${lastImportResult.refresh_all_result.failed_count}`}
            />
          )}

          {lastImportResult.warnings.length > 0 && (
            <Alert
              style={{ marginTop: 12 }}
              type="warning"
              showIcon
              message="Предупреждения"
              description={lastImportResult.warnings.join(' | ')}
            />
          )}
        </Card>
      )}
    </Space>
  );
};
