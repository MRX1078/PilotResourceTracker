import { ArrowLeftOutlined, CheckCircleOutlined, SaveOutlined } from '@ant-design/icons';
import { Button, Card, Divider, Form, Input, InputNumber, Select, Space, Typography, message } from 'antd';
import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import { api } from '../api';
import { AccountingMode, PilotPayload } from '../types/api';

interface PilotFormPageProps {
  mode: 'create' | 'edit';
}

interface PilotFormValues {
  name: string;
  description?: string;
  annual_revenue: number;
  accounting_mode: AccountingMode;
  sql_query?: string;
  trino_host?: string;
  trino_port?: number;
  trino_user?: string;
  trino_password?: string;
  trino_catalog?: string;
  trino_schema?: string;
  trino_http_scheme?: 'http' | 'https';
  additional_pshe_default: number;
}

export const PilotFormPage = ({ mode }: PilotFormPageProps) => {
  const [form] = Form.useForm<PilotFormValues>();
  const [loading, setLoading] = useState(false);
  const [validateLoading, setValidateLoading] = useState(false);
  const [currentMode, setCurrentMode] = useState<AccountingMode>('manual');
  const navigate = useNavigate();
  const params = useParams();

  const pilotId = Number(params.pilotId);
  const normalizeNullableText = (value?: string) => {
    if (typeof value !== 'string') return null;
    const normalized = value.trim();
    return normalized.length > 0 ? normalized : null;
  };

  useEffect(() => {
    if (mode !== 'edit' || !pilotId) return;

    const loadPilot = async () => {
      setLoading(true);
      try {
        const pilot = await api.getPilot(pilotId);
        setCurrentMode(pilot.accounting_mode);
        form.setFieldsValue({
          name: pilot.name,
          description: pilot.description ?? '',
          annual_revenue: Number(pilot.annual_revenue),
          accounting_mode: pilot.accounting_mode,
          sql_query: pilot.sql_query ?? '',
          trino_host: pilot.trino_host ?? '',
          trino_port: pilot.trino_port ?? undefined,
          trino_user: pilot.trino_user ?? '',
          trino_password: pilot.trino_password ?? '',
          trino_catalog: pilot.trino_catalog ?? '',
          trino_schema: pilot.trino_schema ?? '',
          trino_http_scheme: pilot.trino_http_scheme ?? 'http',
          additional_pshe_default: Number(pilot.additional_pshe_default),
        });
      } catch (error) {
        message.error(`Не удалось загрузить пилот: ${(error as Error).message}`);
      } finally {
        setLoading(false);
      }
    };

    void loadPilot();
  }, [mode, pilotId, form]);

  const handleSubmit = async (values: PilotFormValues) => {
    setLoading(true);
    const sqlMode = values.accounting_mode === 'sql';
    const payload: PilotPayload = {
      name: values.name,
      description: values.description?.trim() || null,
      annual_revenue: Number(values.annual_revenue ?? 0),
      accounting_mode: values.accounting_mode,
      sql_query: sqlMode ? values.sql_query?.trim() || null : null,
      trino_host: sqlMode ? normalizeNullableText(values.trino_host) : null,
      trino_port: sqlMode ? values.trino_port ?? null : null,
      trino_user: sqlMode ? normalizeNullableText(values.trino_user) : null,
      trino_password: sqlMode ? normalizeNullableText(values.trino_password) : null,
      trino_catalog: sqlMode ? normalizeNullableText(values.trino_catalog) : null,
      trino_schema: sqlMode ? normalizeNullableText(values.trino_schema) : null,
      trino_http_scheme: sqlMode ? values.trino_http_scheme ?? null : null,
      additional_pshe_default: Number(values.additional_pshe_default ?? 0),
      is_active: true,
    };

    try {
      if (mode === 'create') {
        const created = await api.createPilot(payload);
        message.success('Пилот создан');
        navigate(`/pilots/${created.id}`);
      } else {
        const updated = await api.updatePilot(pilotId, payload);
        message.success('Пилот обновлен');
        navigate(`/pilots/${updated.id}`);
      }
    } catch (error) {
      message.error(`Ошибка сохранения: ${(error as Error).message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleValidateSql = async () => {
    const sql = form.getFieldValue('sql_query');
    if (!sql || !sql.trim()) {
      message.warning('Введите SQL-запрос для проверки');
      return;
    }

    setValidateLoading(true);
    try {
      const result = await api.validateSql({
        sql_query: sql,
        trino_host: normalizeNullableText(form.getFieldValue('trino_host')),
        trino_port: form.getFieldValue('trino_port') ?? null,
        trino_user: normalizeNullableText(form.getFieldValue('trino_user')),
        trino_password: normalizeNullableText(form.getFieldValue('trino_password')),
        trino_catalog: normalizeNullableText(form.getFieldValue('trino_catalog')),
        trino_schema: normalizeNullableText(form.getFieldValue('trino_schema')),
        trino_http_scheme: form.getFieldValue('trino_http_scheme') ?? null,
      });
      if (result.is_valid) {
        message.success(`SQL корректный. Колонки: ${result.columns.join(', ')}`);
      } else {
        message.error(result.message);
      }
    } catch (error) {
      message.error(`Проверка SQL не удалась: ${(error as Error).message}`);
    } finally {
      setValidateLoading(false);
    }
  };

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Card className="page-card">
        <Space style={{ width: '100%', justifyContent: 'space-between' }} wrap>
          <Space direction="vertical" size={0}>
            <Typography.Title level={4} style={{ margin: 0 }}>
              {mode === 'create' ? 'Новый пилот' : 'Редактирование пилота'}
            </Typography.Title>
            <Typography.Text type="secondary">
              Настройка режима учета, доходности и дополнительных ПШЕ
            </Typography.Text>
          </Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/pilots')}>
            К списку пилотов
          </Button>
        </Space>
      </Card>

      <Card className="page-card" loading={loading}>
        <Form<PilotFormValues>
          form={form}
          layout="vertical"
          onFinish={(values) => void handleSubmit(values)}
          initialValues={{
            annual_revenue: 0,
            accounting_mode: 'manual',
            trino_port: 8080,
            trino_http_scheme: 'http',
            additional_pshe_default: 0,
          }}
          onValuesChange={(changed) => {
            if (changed.accounting_mode) {
              setCurrentMode(changed.accounting_mode);
            }
          }}
        >
          <Form.Item name="name" label="Название пилота" rules={[{ required: true, message: 'Введите название' }]}>
            <Input placeholder="Например, Pilot Atlas" />
          </Form.Item>

          <Form.Item name="description" label="Описание">
            <Input.TextArea rows={4} placeholder="Короткое описание целей пилота" />
          </Form.Item>

          <Form.Item
            name="annual_revenue"
            label="Доходность в год, руб"
            rules={[{ required: true, message: 'Укажите доходность' }]}
          >
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item
            name="additional_pshe_default"
            label="Дополнительная нагрузка в ПШЕ"
            tooltip="Будет автоматически добавлена в недельные метрики"
          >
            <InputNumber min={0} step={0.1} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item
            name="accounting_mode"
            label="Режим учета ресурсов"
            rules={[{ required: true, message: 'Выберите режим учета' }]}
          >
            <Select
              options={[
                { value: 'manual', label: 'Manual' },
                { value: 'sql', label: 'SQL' },
              ]}
            />
          </Form.Item>

          {currentMode === 'sql' && (
            <>
              <Form.Item
                name="sql_query"
                label="SQL-запрос к Trino"
                rules={[{ required: true, message: 'Введите SQL-запрос' }]}
              >
                <Input.TextArea
                  rows={12}
                  placeholder="SELECT cas, date, hours FROM ..."
                />
              </Form.Item>
              <Typography.Text type="secondary" style={{ display: 'block', marginTop: -6, marginBottom: 10 }}>
                Рекомендуемый минимальный формат: `cas`, `date` (или `week_start_date`), `hours` (+ `load_percent` опционально). Если CAS уже есть в справочнике сотрудников, ФИО и РЦ подтянутся автоматически.
              </Typography.Text>

              <Divider style={{ marginTop: 8, marginBottom: 16 }}>Подключение к Trino</Divider>
              <Typography.Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
                Если поля не заполнены, backend возьмет параметры из `.env`. Можно задать отдельные креды на этот пилот.
              </Typography.Text>

              <Space direction="vertical" size={12} style={{ width: '100%' }}>
                <Space style={{ width: '100%' }} wrap>
                  <Form.Item name="trino_host" label="TRINO_HOST" style={{ minWidth: 280, flex: 1 }}>
                    <Input placeholder="trino.company.local" />
                  </Form.Item>
                  <Form.Item name="trino_port" label="TRINO_PORT" style={{ width: 180 }}>
                    <InputNumber min={1} max={65535} style={{ width: '100%' }} />
                  </Form.Item>
                  <Form.Item name="trino_http_scheme" label="TRINO_HTTP_SCHEME" style={{ width: 220 }}>
                    <Select
                      allowClear
                      options={[
                        { value: 'http', label: 'http' },
                        { value: 'https', label: 'https' },
                      ]}
                    />
                  </Form.Item>
                </Space>

                <Space style={{ width: '100%' }} wrap>
                  <Form.Item name="trino_user" label="TRINO_USER" style={{ minWidth: 280, flex: 1 }}>
                    <Input placeholder="service_user" />
                  </Form.Item>
                  <Form.Item name="trino_password" label="TRINO_PASSWORD" style={{ minWidth: 280, flex: 1 }}>
                    <Input.Password placeholder="Пароль (если нужен)" />
                  </Form.Item>
                </Space>

                <Space style={{ width: '100%' }} wrap>
                  <Form.Item name="trino_catalog" label="TRINO_CATALOG" style={{ minWidth: 280, flex: 1 }}>
                    <Input placeholder="hive" />
                  </Form.Item>
                  <Form.Item name="trino_schema" label="TRINO_SCHEMA" style={{ minWidth: 280, flex: 1 }}>
                    <Input placeholder="default" />
                  </Form.Item>
                </Space>
              </Space>

              <Button icon={<CheckCircleOutlined />} loading={validateLoading} onClick={() => void handleValidateSql()}>
                Проверить запрос
              </Button>
            </>
          )}

          <Space style={{ marginTop: 20 }}>
            <Button type="primary" htmlType="submit" loading={loading} icon={<SaveOutlined />}>
              Сохранить
            </Button>
            <Button onClick={() => navigate('/pilots')}>Отмена</Button>
          </Space>
        </Form>
      </Card>
    </Space>
  );
};
