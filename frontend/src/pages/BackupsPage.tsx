import { DownloadOutlined, FileTextOutlined, SaveOutlined, UploadOutlined } from '@ant-design/icons';
import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Form,
  Input,
  InputNumber,
  Row,
  Select,
  Space,
  Spin,
  Switch,
  Typography,
  Upload,
  message,
} from 'antd';
import { useEffect, useState } from 'react';

import { api } from '../api';
import { BackupImportResponse, TrinoConnectionSettings } from '../types/api';
import { downloadTemplate, FILE_TEMPLATES } from '../utils/fileTemplates';

interface TrinoSettingsFormValues {
  trino_host?: string | null;
  trino_port?: number | null;
  trino_user?: string | null;
  trino_password?: string | null;
  trino_catalog?: string | null;
  trino_schema?: string | null;
  trino_http_scheme?: 'http' | 'https' | null;
}

const normalizeNullableText = (value?: string | null): string | null => {
  if (typeof value !== 'string') return null;
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
};

export const BackupsPage = () => {
  const [exportLoading, setExportLoading] = useState(false);
  const [importLoading, setImportLoading] = useState(false);
  const [runRefreshAfterImport, setRunRefreshAfterImport] = useState(true);
  const [lastImportResult, setLastImportResult] = useState<BackupImportResponse | null>(null);

  const [trinoForm] = Form.useForm<TrinoSettingsFormValues>();
  const [trinoLoading, setTrinoLoading] = useState(true);
  const [trinoSaving, setTrinoSaving] = useState(false);

  const applyTrinoSettings = (settingsValue: TrinoConnectionSettings | null) => {
    trinoForm.setFieldsValue({
      trino_host: settingsValue?.trino_host ?? '',
      trino_port: settingsValue?.trino_port ?? undefined,
      trino_user: settingsValue?.trino_user ?? '',
      trino_password: settingsValue?.trino_password ?? '',
      trino_catalog: settingsValue?.trino_catalog ?? '',
      trino_schema: settingsValue?.trino_schema ?? '',
      trino_http_scheme: settingsValue?.trino_http_scheme ?? undefined,
    });
  };

  useEffect(() => {
    const loadSettings = async () => {
      setTrinoLoading(true);
      try {
        const result = await api.getTrinoSettings();
        applyTrinoSettings(result);
      } catch (error) {
        message.error(`Не удалось загрузить параметры Trino: ${(error as Error).message}`);
      } finally {
        setTrinoLoading(false);
      }
    };

    void loadSettings();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSaveTrinoSettings = async (values: TrinoSettingsFormValues) => {
    setTrinoSaving(true);
    try {
      const payload: TrinoConnectionSettings = {
        trino_host: normalizeNullableText(values.trino_host),
        trino_port: typeof values.trino_port === 'number' ? values.trino_port : null,
        trino_user: normalizeNullableText(values.trino_user),
        trino_password: normalizeNullableText(values.trino_password),
        trino_catalog: normalizeNullableText(values.trino_catalog),
        trino_schema: normalizeNullableText(values.trino_schema),
        trino_http_scheme: (values.trino_http_scheme ?? null) as 'http' | 'https' | null,
      };
      const saved = await api.updateTrinoSettings(payload);
      applyTrinoSettings(saved);
      message.success('Параметры подключения к Trino сохранены');
    } catch (error) {
      message.error(`Не удалось сохранить параметры Trino: ${(error as Error).message}`);
    } finally {
      setTrinoSaving(false);
    }
  };

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
      if (result.trino_settings_from_backup) {
        applyTrinoSettings(result.trino_settings_from_backup);
      }
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
            Резервные копии и параметры подключения
          </Typography.Title>
          <Typography.Text type="secondary">
            Здесь задается единое подключение к Trino для всех SQL-пилотов, а также скачивается/загружается JSON-бэкап.
          </Typography.Text>
          <Alert
            showIcon
            type="info"
            message="Рекомендуемый поток"
            description="Заполните параметры подключения к Trino один раз — они применятся ко всем SQL-пилотам. Затем экспортируйте/импортируйте бэкап, чтобы перенести данные между коллегами."
          />
        </Space>
      </Card>

      <Card className="page-card" title="Подключение к Trino (общее для всех SQL-пилотов)">
        <Spin spinning={trinoLoading}>
          <Form<TrinoSettingsFormValues>
            form={trinoForm}
            layout="vertical"
            onFinish={(values) => void handleSaveTrinoSettings(values)}
          >
            <Typography.Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
              Эти параметры заменяют поля Trino, которые раньше задавались для каждого пилота отдельно. Если поле пустое — используется значение из переменной окружения `.env`.
            </Typography.Text>

            <Row gutter={[12, 0]}>
              <Col xs={24} md={12}>
                <Form.Item name="trino_host" label="TRINO_HOST">
                  <Input placeholder="trino.company.local" />
                </Form.Item>
              </Col>
              <Col xs={24} md={6}>
                <Form.Item name="trino_port" label="TRINO_PORT">
                  <InputNumber min={1} max={65535} style={{ width: '100%' }} placeholder="8080" />
                </Form.Item>
              </Col>
              <Col xs={24} md={6}>
                <Form.Item name="trino_http_scheme" label="TRINO_HTTP_SCHEME">
                  <Select
                    allowClear
                    options={[
                      { value: 'http', label: 'http' },
                      { value: 'https', label: 'https' },
                    ]}
                    placeholder="http"
                  />
                </Form.Item>
              </Col>
              <Col xs={24} md={12}>
                <Form.Item name="trino_user" label="TRINO_USER">
                  <Input placeholder="service_user" />
                </Form.Item>
              </Col>
              <Col xs={24} md={12}>
                <Form.Item name="trino_password" label="TRINO_PASSWORD">
                  <Input.Password placeholder="Пароль (если нужен)" />
                </Form.Item>
              </Col>
              <Col xs={24} md={12}>
                <Form.Item name="trino_catalog" label="TRINO_CATALOG">
                  <Input placeholder="hive" />
                </Form.Item>
              </Col>
              <Col xs={24} md={12}>
                <Form.Item name="trino_schema" label="TRINO_SCHEMA">
                  <Input placeholder="default" />
                </Form.Item>
              </Col>
            </Row>

            <Button
              type="primary"
              htmlType="submit"
              loading={trinoSaving}
              icon={<SaveOutlined />}
            >
              Сохранить параметры Trino
            </Button>
          </Form>
        </Spin>
      </Card>

      <Card className="page-card" title="Экспорт бэкапа">
        <Space direction="vertical" size={10}>
          <Typography.Text>
            Экспорт создает один JSON-файл, который можно передать в полу-оффлайн режиме. Параметры подключения к Trino также попадают в этот файл.
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
            {lastImportResult.trino_settings_from_backup && (
              <Descriptions.Item label="Подключение Trino из файла">
                {lastImportResult.trino_settings_from_backup.trino_host || '—'}
                {lastImportResult.trino_settings_from_backup.trino_port
                  ? `:${lastImportResult.trino_settings_from_backup.trino_port}`
                  : ''}
                {lastImportResult.trino_settings_from_backup.trino_user
                  ? ` (${lastImportResult.trino_settings_from_backup.trino_user})`
                  : ''}
              </Descriptions.Item>
            )}
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
