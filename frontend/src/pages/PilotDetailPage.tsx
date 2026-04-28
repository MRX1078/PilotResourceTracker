import {
  Alert,
  Button,
  Card,
  Col,
  DatePicker,
  Descriptions,
  Divider,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Row,
  Segmented,
  Select,
  Space,
  Spin,
  Statistic,
  Table,
  Tag,
  Typography,
  Upload,
  message,
} from 'antd';
import { FileTextOutlined, UploadOutlined } from '@ant-design/icons';
import dayjs, { Dayjs } from 'dayjs';
import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import { api } from '../api';
import { WeekPicker } from '../components/WeekPicker';
import { Assignment, Pilot, PilotWeeklyMetric } from '../types/api';
import { formatDate, toIsoDate, weekStartOf } from '../utils/date';
import { downloadTemplate, FILE_TEMPLATES } from '../utils/fileTemplates';
import { formatMoney, formatNumber } from '../utils/format';

type PeriodMode = 'week' | 'range';

interface AssignmentFormValues {
  employee_id?: number;
  cas?: string;
  full_name?: string;
  rc?: string;
  hours?: number;
  load_percent?: number;
  pshe?: number;
}

export const PilotDetailPage = () => {
  const params = useParams();
  const navigate = useNavigate();
  const [periodMode, setPeriodMode] = useState<PeriodMode>('week');
  const [week, setWeek] = useState(weekStartOf(dayjs()));
  const [range, setRange] = useState<[Dayjs, Dayjs]>([
    weekStartOf(dayjs().subtract(7, 'week')),
    weekStartOf(dayjs()),
  ]);
  const [pilot, setPilot] = useState<Pilot | null>(null);
  const [metrics, setMetrics] = useState<PilotWeeklyMetric[]>([]);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [employees, setEmployees] = useState<{ id: number; full_name: string; cas: string | null; rc: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshLoading, setRefreshLoading] = useState(false);
  const [csvUploading, setCsvUploading] = useState(false);
  const [createForm] = Form.useForm<AssignmentFormValues>();
  const [editForm] = Form.useForm<AssignmentFormValues>();
  const [editingAssignment, setEditingAssignment] = useState<Assignment | null>(null);

  const pilotId = Number(params.pilotId);
  const selectedWeek = useMemo(() => toIsoDate(weekStartOf(week)), [week]);
  const normalizedRange = useMemo<[Dayjs, Dayjs]>(() => {
    const start = weekStartOf(range[0]);
    const end = weekStartOf(range[1]);
    return start.isAfter(end) ? [end, start] : [start, end];
  }, [range]);
  const rangeStart = useMemo(() => toIsoDate(normalizedRange[0]), [normalizedRange]);
  const rangeEnd = useMemo(() => toIsoDate(normalizedRange[1]), [normalizedRange]);
  const assignmentWeek = periodMode === 'week' ? selectedWeek : rangeEnd;
  const currentScopeMetrics = useMemo(() => {
    if (periodMode === 'week') {
      return metrics.filter((item) => item.week_start_date === selectedWeek);
    }
    return metrics.filter((item) => item.week_start_date >= rangeStart && item.week_start_date <= rangeEnd);
  }, [metrics, periodMode, rangeStart, rangeEnd, selectedWeek]);
  const chartMetrics = useMemo(() => {
    if (periodMode === 'week') {
      return metrics;
    }
    return metrics.filter((item) => item.week_start_date >= rangeStart && item.week_start_date <= rangeEnd);
  }, [metrics, periodMode, rangeStart, rangeEnd]);
  const scopeLabel = useMemo(() => {
    if (periodMode === 'week') {
      return formatDate(selectedWeek);
    }
    return `${formatDate(rangeStart)} - ${formatDate(rangeEnd)}`;
  }, [periodMode, selectedWeek, rangeStart, rangeEnd]);

  const scopeTotals = useMemo(() => {
    return currentScopeMetrics.reduce(
      (acc, item) => {
        acc.totalHours += Number(item.total_hours);
        acc.totalPshe += Number(item.total_pshe);
        acc.totalCost += Number(item.total_cost);
        acc.totalProfitability += Number(item.profitability_estimate);
        return acc;
      },
      { totalHours: 0, totalPshe: 0, totalCost: 0, totalProfitability: 0 }
    );
  }, [currentScopeMetrics]);

  const yearEndForecast = useMemo(() => {
    const reference = dayjs(periodMode === 'week' ? selectedWeek : rangeEnd);
    const weeksPassed = Math.min(52, Math.max(1, reference.diff(reference.startOf('year'), 'week') + 1));
    const year = reference.year();

    const ytdCost = metrics
      .filter((item) => {
        const metricDate = dayjs(item.week_start_date);
        return metricDate.year() === year && !metricDate.isAfter(reference, 'day');
      })
      .reduce((sum, item) => sum + Number(item.total_cost), 0);

    const weeklyRunRate = weeksPassed > 0 ? ytdCost / weeksPassed : 0;
    const weeksRemaining = Math.max(0, 52 - weeksPassed);
    const forecastCost = ytdCost + weeklyRunRate * weeksRemaining;
    const annualRevenue = Number(pilot?.annual_revenue ?? 0);
    const forecastProfit = annualRevenue - forecastCost;

    return {
      year,
      ytdCost,
      weeklyRunRate,
      weeksPassed,
      forecastCost,
      annualRevenue,
      forecastProfit,
    };
  }, [metrics, pilot?.annual_revenue, periodMode, rangeEnd, selectedWeek]);

  const loadData = async () => {
    if (!pilotId) return;
    setLoading(true);
    try {
      const [pilotData, metricData, assignmentData, employeesData] = await Promise.all([
        api.getPilot(pilotId),
        api.getMetrics(pilotId),
        api.getAssignments(pilotId, assignmentWeek),
        api.getEmployees(),
      ]);
      setPilot(pilotData);
      setMetrics(metricData);
      setAssignments(assignmentData);
      setEmployees(employeesData);
    } catch (error) {
      message.error(`Не удалось загрузить карточку пилота: ${(error as Error).message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadData();
  }, [pilotId, assignmentWeek]);

  const handleRefresh = async () => {
    if (!pilotId) return;
    setRefreshLoading(true);
    try {
      const response = await api.refreshPilot(pilotId);
      message.success(`${response.pilot_name}: обновлено ${response.rows_processed} строк`);
      await loadData();
    } catch (error) {
      message.error(`Ошибка refresh: ${(error as Error).message}`);
    } finally {
      setRefreshLoading(false);
    }
  };

  const handleCreateAssignment = async (values: AssignmentFormValues) => {
    if (!pilotId) return;
    const hasExistingEmployee = Boolean(values.employee_id);
    const cas = values.cas?.trim();
    const fullName = values.full_name?.trim();
    const rc = values.rc?.trim();
    const hasCas = Boolean(cas);
    const hasNewEmployeeData = Boolean(fullName && rc);
    const hasPartialProfile = Boolean((fullName && !rc) || (!fullName && rc));

    if (hasPartialProfile) {
      message.error('Для нового сотрудника нужно заполнить и ФИО, и РЦ');
      return;
    }

    if (!hasExistingEmployee && !hasCas && !hasNewEmployeeData) {
      message.error('Выберите сотрудника из списка, укажите CAS существующего сотрудника или заполните ФИО+РЦ');
      return;
    }

    try {
      await api.createAssignment(pilotId, {
        employee_id: values.employee_id,
        cas: cas || undefined,
        full_name: fullName || undefined,
        rc: rc || undefined,
        week_start_date: assignmentWeek,
        hours: values.hours,
        load_percent: values.load_percent,
        pshe: values.pshe,
        source: 'manual',
      });
      message.success('Назначение добавлено');
      createForm.resetFields();
      await loadData();
    } catch (error) {
      message.error(`Не удалось добавить назначение: ${(error as Error).message}`);
    }
  };

  const handleImportCsv = async (file: File) => {
    if (!pilotId) return false;
    setCsvUploading(true);
    try {
      const response = await api.importAssignmentsCsv(pilotId, file);
      message.success(
        `CSV импорт завершен: ${response.imported_count} строк (создано ${response.created_count}, обновлено ${response.updated_count})`
      );
      await loadData();
    } catch (error: any) {
      const detail = error?.response?.data?.detail;
      if (detail && typeof detail === 'object' && Array.isArray(detail.errors)) {
        const firstErrors = detail.errors
          .slice(0, 3)
          .map((item: { row_number: number; error: string }) => `строка ${item.row_number}: ${item.error}`)
          .join(' | ');
        message.error(`Ошибка CSV: ${firstErrors}`);
      } else {
        message.error(`Не удалось импортировать CSV: ${error?.message ?? 'unknown error'}`);
      }
    } finally {
      setCsvUploading(false);
    }
    return false;
  };

  const handleOpenEditModal = (assignment: Assignment) => {
    setEditingAssignment(assignment);
    editForm.setFieldsValue({
      hours: Number(assignment.hours),
      load_percent: Number(assignment.load_percent),
      pshe: Number(assignment.pshe),
    });
  };

  const handleUpdateAssignment = async () => {
    if (!editingAssignment) return;
    try {
      const values = await editForm.validateFields();
      await api.updateAssignment(editingAssignment.id, {
        hours: values.hours,
        load_percent: values.load_percent,
        pshe: values.pshe,
      });
      message.success('Назначение обновлено');
      setEditingAssignment(null);
      await loadData();
    } catch (error) {
      message.error(`Не удалось обновить назначение: ${(error as Error).message}`);
    }
  };

  const handleDeleteAssignment = async (assignmentId: number) => {
    try {
      await api.deleteAssignment(assignmentId);
      message.success('Назначение удалено');
      await loadData();
    } catch (error) {
      message.error(`Не удалось удалить назначение: ${(error as Error).message}`);
    }
  };

  if (loading && !pilot) {
    return (
      <Card className="page-card">
        <Spin />
      </Card>
    );
  }

  if (!pilot) {
    return (
      <Card className="page-card">
        <Typography.Text>Пилот не найден.</Typography.Text>
      </Card>
    );
  }

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Card className="page-card">
        <Space direction="vertical" size={10} style={{ width: '100%' }}>
          <Space style={{ width: '100%', justifyContent: 'space-between' }} wrap>
            <Space direction="vertical" size={0}>
              <Typography.Title level={4} style={{ margin: 0 }}>
                {pilot.name}
              </Typography.Title>
              <Typography.Text type="secondary">{pilot.description || 'Описание не задано'}</Typography.Text>
            </Space>
            <Space>
              <Button onClick={() => navigate(`/pilots/${pilot.id}/edit`)}>Редактировать</Button>
              <Button onClick={() => navigate('/pilots')}>К списку</Button>
              {pilot.accounting_mode === 'sql' && (
                <Button type="primary" loading={refreshLoading} onClick={() => void handleRefresh()}>
                  Refresh SQL
                </Button>
              )}
            </Space>
          </Space>

          <Row gutter={[12, 12]}>
            <Col xs={24} md={8}>
              <Tag color={pilot.accounting_mode === 'sql' ? 'blue' : 'green'}>
                Режим: {pilot.accounting_mode.toUpperCase()}
              </Tag>
            </Col>
            <Col xs={24} md={8}>
              <Typography.Text>Доходность/год: {formatMoney(pilot.annual_revenue)}</Typography.Text>
            </Col>
            <Col xs={24} md={8}>
              <Typography.Text>Доп. ПШЕ: {formatNumber(pilot.additional_pshe_default)}</Typography.Text>
            </Col>
          </Row>

          <Space direction="vertical" size={8} style={{ width: '100%' }}>
            <Space wrap>
              <Typography.Text type="secondary">Период:</Typography.Text>
              <Segmented<PeriodMode>
                value={periodMode}
                options={[
                  { label: 'Неделя', value: 'week' },
                  { label: 'Интервал', value: 'range' },
                ]}
                onChange={(value) => {
                  const next = value as PeriodMode;
                  setPeriodMode(next);
                  if (next === 'week') {
                    setWeek(weekStartOf(normalizedRange[1]));
                  }
                }}
              />
            </Space>

            {periodMode === 'week' ? (
              <WeekPicker value={week} onChange={setWeek} />
            ) : (
              <Space wrap>
                <Typography.Text type="secondary">Интервал:</Typography.Text>
                <DatePicker.RangePicker
                  picker="week"
                  allowClear={false}
                  format="YYYY-[W]WW"
                  value={normalizedRange}
                  onChange={(next) => {
                    if (!next || !next[0] || !next[1]) {
                      return;
                    }
                    setRange([weekStartOf(next[0]), weekStartOf(next[1])]);
                  }}
                />
              </Space>
            )}

            <Tag color="geekblue">Текущий срез: {scopeLabel}</Tag>
          </Space>

          {pilot.accounting_mode === 'sql' && pilot.sql_query && (
            <Card size="small" title="SQL-запрос" style={{ marginTop: 8 }}>
              <Typography.Paragraph className="text-prewrap" style={{ marginBottom: 0 }}>
                {pilot.sql_query}
              </Typography.Paragraph>
            </Card>
          )}

          {pilot.accounting_mode === 'sql' && (
            <Card size="small" title="Подключение Trino" style={{ marginTop: 8 }}>
              <Descriptions
                size="small"
                column={{ xs: 1, sm: 2 }}
                items={[
                  { key: 'host', label: 'Host', children: pilot.trino_host || 'из .env' },
                  { key: 'port', label: 'Port', children: pilot.trino_port ?? 'из .env' },
                  { key: 'user', label: 'User', children: pilot.trino_user || 'из .env' },
                  { key: 'password', label: 'Password', children: pilot.trino_password ? '********' : 'из .env / не задан' },
                  { key: 'catalog', label: 'Catalog', children: pilot.trino_catalog || 'из .env' },
                  { key: 'schema', label: 'Schema', children: pilot.trino_schema || 'из .env' },
                  { key: 'scheme', label: 'HTTP scheme', children: pilot.trino_http_scheme || 'из .env' },
                ]}
              />
            </Card>
          )}
        </Space>
      </Card>

      {currentScopeMetrics.length === 0 && (
        <Alert
          showIcon
          type="info"
          message="Для выбранного периода пока нет метрик"
          description="Попробуйте выбрать другой период или обновить данные пилота."
        />
      )}

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card className="page-card">
            <Statistic
              title={periodMode === 'week' ? 'Hours (неделя)' : 'Hours (интервал)'}
              value={formatNumber(scopeTotals.totalHours)}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className="page-card">
            <Statistic
              title={periodMode === 'week' ? 'ПШЕ (неделя)' : 'ПШЕ (интервал)'}
              value={formatNumber(scopeTotals.totalPshe)}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className="page-card">
            <Statistic
              title={periodMode === 'week' ? 'Cost (неделя)' : 'Cost (интервал)'}
              value={formatMoney(scopeTotals.totalCost)}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className="page-card">
            <Statistic
              title={periodMode === 'week' ? 'Profitability (неделя)' : 'Profitability (интервал)'}
              value={formatMoney(scopeTotals.totalProfitability)}
              valueStyle={{ color: scopeTotals.totalProfitability >= 0 ? '#15803d' : '#b91c1c' }}
            />
          </Card>
        </Col>
      </Row>

      <Card className="page-card">
        <Space direction="vertical" size={8} style={{ width: '100%' }}>
          <Typography.Title level={5} style={{ margin: 0 }}>
            Прогноз до конца года
          </Typography.Title>
          <Typography.Text type="secondary">
            С учетом текущих трат по проекту к концу {yearEndForecast.year} года будет итог:
            {' '}
            <Typography.Text
              style={{ color: yearEndForecast.forecastProfit >= 0 ? '#15803d' : '#b91c1c', fontWeight: 700 }}
            >
              {formatMoney(yearEndForecast.forecastProfit)}
            </Typography.Text>
          </Typography.Text>
          <Row gutter={[12, 12]}>
            <Col xs={24} md={8}>
              <Statistic title="Факт трат (YTD)" value={formatMoney(yearEndForecast.ytdCost)} />
            </Col>
            <Col xs={24} md={8}>
              <Statistic
                title="Run-rate трат / неделя"
                value={formatMoney(yearEndForecast.weeklyRunRate)}
              />
            </Col>
            <Col xs={24} md={8}>
              <Statistic
                title="Прогноз трат до конца года"
                value={formatMoney(yearEndForecast.forecastCost)}
              />
            </Col>
          </Row>
        </Space>
      </Card>

      <Card className="page-card" title="Метрики по неделям">
        <div style={{ width: '100%', height: 320 }}>
          <ResponsiveContainer>
            <LineChart data={chartMetrics}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="week_start_date" tickFormatter={formatDate} />
              <YAxis yAxisId="left" tickFormatter={(value) => formatNumber(value, 0)} />
              <YAxis yAxisId="right" orientation="right" tickFormatter={(value) => formatNumber(value, 2)} />
              <Tooltip
                labelFormatter={(label) => `Неделя: ${formatDate(label)}`}
                formatter={(value: string | number, name) =>
                  name === 'total_cost' ? formatMoney(value) : formatNumber(value)
                }
              />
              <Line yAxisId="left" dataKey="total_cost" stroke="#0f766e" strokeWidth={3} />
              <Line yAxisId="right" dataKey="total_pshe" stroke="#ea580c" strokeWidth={3} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>

      {pilot.accounting_mode === 'manual' && (
        <Card className="page-card" title="Добавить назначение сотрудника">
          <Form<AssignmentFormValues> form={createForm} layout="vertical" onFinish={(values) => void handleCreateAssignment(values)}>
            <Typography.Text type="secondary">
              Можно выбрать существующего сотрудника, указать только CAS (если сотрудник уже в справочнике), либо создать нового по ФИО+РЦ.
            </Typography.Text>
            <Row gutter={[12, 12]} style={{ marginTop: 8 }}>
              <Col xs={24} lg={12}>
                <Form.Item name="employee_id" label="Существующий сотрудник">
                  <Select
                    allowClear
                    showSearch
                    placeholder="Выбрать из списка"
                    options={employees.map((employee) => ({
                      value: employee.id,
                      label: `${employee.full_name} (${employee.cas ?? '-'} / ${employee.rc})`,
                    }))}
                    filterOption={(input, option) =>
                      String(option?.label ?? '')
                        .toLowerCase()
                        .includes(input.toLowerCase())
                    }
                  />
                </Form.Item>
              </Col>
              <Col xs={24} lg={4}>
                <Form.Item name="cas" label="CAS">
                  <Input placeholder="cas123" />
                </Form.Item>
              </Col>
              <Col xs={24} lg={4}>
                <Form.Item name="full_name" label="ФИО">
                  <Input placeholder="Иванов Иван" />
                </Form.Item>
              </Col>
              <Col xs={24} lg={4}>
                <Form.Item name="rc" label="РЦ">
                  <Input placeholder="RC-1" />
                </Form.Item>
              </Col>
              <Col xs={24} md={8}>
                <Form.Item name="hours" label="Часы" rules={[{ required: true, message: 'Укажите часы' }]}>
                  <InputNumber min={0} step={0.5} placeholder="40" style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col xs={24} md={8}>
                <Form.Item name="load_percent" label="% загрузки (опц.)">
                  <InputNumber min={0} step={1} placeholder="100" style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col xs={24} md={8}>
                <Form.Item name="pshe" label="ПШЕ (опц.)">
                  <InputNumber min={0} step={0.1} placeholder="1" style={{ width: '100%' }} />
                </Form.Item>
              </Col>
            </Row>
            <Space>
              <Tag color="processing">Неделя: {assignmentWeek}</Tag>
              {periodMode === 'range' && (
                <Tag color="gold">Используется конечная неделя выбранного интервала</Tag>
              )}
              <Button type="primary" htmlType="submit">
                Добавить назначение
              </Button>
            </Space>
          </Form>

          <Divider />

          <Space direction="vertical" size={6} style={{ width: '100%' }}>
            <Typography.Text strong>Импорт назначений из CSV</Typography.Text>
            <Typography.Text type="secondary">
              Поддерживаемые колонки: `week_start_date`, `employee_id` или `cas/cas_id`, `hours`/`pshe`/`load_percent`, `source` (опц.). Если справочник сотрудников уже загружен, достаточно `cas_id + трудозатраты` — ФИО и РЦ подтянутся автоматически.
            </Typography.Text>
            <Upload
              accept=".csv,text/csv"
              maxCount={1}
              showUploadList={false}
              beforeUpload={(file) => {
                void handleImportCsv(file);
                return false;
              }}
            >
              <Button icon={<UploadOutlined />} loading={csvUploading}>
                Импортировать CSV
              </Button>
            </Upload>
            <Button icon={<FileTextOutlined />} onClick={() => downloadTemplate(FILE_TEMPLATES.assignmentsCsv)}>
              Скачать шаблон CSV
            </Button>
          </Space>
        </Card>
      )}

      <Card
        className="page-card"
        title={
          periodMode === 'week'
            ? `Сотрудники пилота за неделю ${formatDate(assignmentWeek)}`
            : `Сотрудники пилота за неделю окончания интервала: ${formatDate(assignmentWeek)}`
        }
      >
        {assignments.some((item) => Number(item.load_percent) > 100) && (
          <Alert
            style={{ marginBottom: 12 }}
            showIcon
            type="warning"
            message="В этой неделе есть назначения с load_percent больше 100%"
          />
        )}
        <Table
          rowKey="id"
          dataSource={assignments}
          pagination={{ pageSize: 8 }}
          columns={[
            {
              title: 'Сотрудник',
              render: (_, row) => <Link to={`/employees/${row.employee.id}`}>{row.employee.full_name}</Link>,
            },
            {
              title: 'CAS',
              render: (_, row) => row.employee.cas ?? '-',
            },
            {
              title: 'РЦ',
              render: (_, row) => row.employee.rc,
            },
            {
              title: 'Часы',
              dataIndex: 'hours',
              render: (value: string) => formatNumber(value),
            },
            {
              title: 'ПШЕ',
              dataIndex: 'pshe',
              render: (value: string) => formatNumber(value),
            },
            {
              title: '% загрузки',
              dataIndex: 'load_percent',
              render: (value: string) => `${formatNumber(value)}%`,
            },
            {
              title: 'Источник',
              dataIndex: 'source',
              render: (value: string) =>
                value === 'sql' ? <Tag color="blue">SQL</Tag> : <Tag color="green">Manual</Tag>,
            },
            {
              title: 'Другие пилоты',
              dataIndex: 'other_pilots',
              render: (value: Assignment['other_pilots']) =>
                value.length === 0 ? '-' : value.map((item) => <Tag key={`${item.pilot_id}`}>{item.pilot_name}</Tag>),
            },
            {
              title: 'Действия',
              render: (_, row) => (
                <Space>
                  <Button size="small" onClick={() => handleOpenEditModal(row)} disabled={row.source !== 'manual'}>
                    Изменить
                  </Button>
                  <Popconfirm
                    title="Удалить назначение?"
                    okText="Да"
                    cancelText="Нет"
                    onConfirm={() => void handleDeleteAssignment(row.id)}
                  >
                    <Button size="small" danger disabled={row.source !== 'manual'}>
                      Удалить
                    </Button>
                  </Popconfirm>
                </Space>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        title={editingAssignment ? `Редактировать назначение: ${editingAssignment.employee.full_name}` : 'Редактировать'}
        open={Boolean(editingAssignment)}
        onCancel={() => setEditingAssignment(null)}
        onOk={() => void handleUpdateAssignment()}
        okText="Сохранить"
      >
        <Form form={editForm} layout="vertical">
          <Form.Item name="hours" label="Часы" rules={[{ required: true, message: 'Укажите часы' }]}>
            <InputNumber min={0} step={0.5} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="load_percent" label="Процент загрузки">
            <InputNumber min={0} step={1} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="pshe" label="ПШЕ">
            <InputNumber min={0} step={0.1} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  );
};
