import { ArrowLeftOutlined, CheckCircleOutlined, SaveOutlined } from '@ant-design/icons';
import { Alert, Button, Card, Form, Input, InputNumber, Select, Space, Typography, message } from 'antd';
import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';

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
      const result = await api.validateSql({ sql_query: sql });
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
                Рекомендуемый минимальный формат: `cas`, `date` (или `week_start_date`), `hours` (+ `load_percent` опционально). Если CAS уже есть в справочнике сотрудников, ФИО и РЦ подтянутся автоматически. Если CAS неизвестен — сотрудник будет создан с заглушками «Неизвестный сотрудник» и «Неизвестный РЦ», которые потом можно отредактировать вручную.
              </Typography.Text>

              <Alert
                style={{ marginBottom: 12 }}
                type="info"
                showIcon
                message="Подключение к Trino задается один раз"
                description={
                  <>
                    Параметры подключения (host, user, пароль и т.д.) теперь хранятся глобально и редактируются на странице{' '}
                    <Link to="/backups">«Бэкап»</Link>. Они применяются ко всем SQL-пилотам.
                  </>
                }
              />

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
