import { Alert, Card, Col, DatePicker, Progress, Row, Segmented, Space, Spin, Statistic, Table, Tag, Typography, message } from 'antd';
import dayjs, { Dayjs } from 'dayjs';
import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import { api } from '../api';
import { WeekPicker } from '../components/WeekPicker';
import {
  CrossAssignmentItem,
  DashboardPilotAllocation,
  DashboardProfitabilityItem,
  DashboardSummary,
  ResourceByRcItem,
  ResourceLoadItem,
  WeeklyCostPoint,
} from '../types/api';
import { formatDate, toIsoDate, weekStartOf } from '../utils/date';
import { formatMoney, formatNumber } from '../utils/format';

type DashboardPeriodMode = 'week' | 'range';

export const DashboardPage = () => {
  const navigate = useNavigate();
  const [periodMode, setPeriodMode] = useState<DashboardPeriodMode>('week');
  const [week, setWeek] = useState(weekStartOf(dayjs()));
  const [range, setRange] = useState<[Dayjs, Dayjs]>([
    weekStartOf(dayjs().subtract(11, 'week')),
    weekStartOf(dayjs()),
  ]);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [crossAssignments, setCrossAssignments] = useState<CrossAssignmentItem[]>([]);
  const [weeklyCosts, setWeeklyCosts] = useState<WeeklyCostPoint[]>([]);
  const [resourceLoad, setResourceLoad] = useState<ResourceLoadItem[]>([]);
  const [resourceByRc, setResourceByRc] = useState<ResourceByRcItem[]>([]);
  const [loading, setLoading] = useState(true);

  const weekStart = useMemo(() => toIsoDate(weekStartOf(week)), [week]);
  const normalizedRange = useMemo<[Dayjs, Dayjs]>(() => {
    const start = weekStartOf(range[0]);
    const end = weekStartOf(range[1]);
    return start.isAfter(end) ? [end, start] : [start, end];
  }, [range]);
  const rangeStart = useMemo(() => toIsoDate(normalizedRange[0]), [normalizedRange]);
  const rangeEnd = useMemo(() => toIsoDate(normalizedRange[1]), [normalizedRange]);
  const periodLabel = useMemo(() => {
    if (periodMode === 'week') {
      return formatDate(weekStart);
    }
    return `${formatDate(rangeStart)} - ${formatDate(rangeEnd)}`;
  }, [periodMode, rangeEnd, rangeStart, weekStart]);
  const topEmployeesChartData = useMemo(() => resourceLoad.slice(0, 8), [resourceLoad]);
  const topPilotAllocationChartData = useMemo(() => summary?.resource_allocation.slice(0, 8) ?? [], [summary]);

  const handlePilotDrilldown = (pilotId?: number) => {
    if (!pilotId) return;
    navigate(`/pilots/${pilotId}`);
  };

  const handleEmployeeDrilldown = (employeeId?: number) => {
    if (!employeeId) return;
    navigate(`/employees/${employeeId}`);
  };

  const handlePilotChartClick = (_: unknown, index: number) => {
    const item = topPilotAllocationChartData[index];
    if (item) {
      handlePilotDrilldown(item.pilot_id);
    }
  };

  const handleEmployeeChartClick = (_: unknown, index: number) => {
    const item = topEmployeesChartData[index];
    if (item) {
      handleEmployeeDrilldown(item.employee_id);
    }
  };

  const handleWeeklyChartClick = (state: { activeLabel?: string } | undefined) => {
    if (!state?.activeLabel) return;
    if (periodMode !== 'week') return;
    const parsed = dayjs(state.activeLabel);
    if (parsed.isValid()) {
      setWeek(parsed);
    }
  };

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const periodParams =
          periodMode === 'week'
            ? { weekStartDate: weekStart }
            : { startWeek: rangeStart, endWeek: rangeEnd };

        const [summaryResponse, crossResponse, weeklyResponse, loadResponse, rcResponse] = await Promise.all([
          api.getDashboardSummary(periodParams),
          api.getCrossAssignments(periodParams),
          api.getWeeklyCosts(
            periodMode === 'week'
              ? { weeks: 16 }
              : { startWeek: rangeStart, endWeek: rangeEnd }
          ),
          api.getResourceLoad(periodParams),
          api.getResourceByRc(periodParams),
        ]);
        setSummary(summaryResponse);
        setCrossAssignments(crossResponse);
        setWeeklyCosts(weeklyResponse);
        setResourceLoad(loadResponse);
        setResourceByRc(rcResponse);
      } catch (error) {
        message.error(`Не удалось загрузить dashboard: ${(error as Error).message}`);
      } finally {
        setLoading(false);
      }
    };

    void load();
  }, [periodMode, rangeEnd, rangeStart, weekStart]);

  if (loading && !summary) {
    return (
      <Card className="page-card">
        <Spin />
      </Card>
    );
  }

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Card className="page-card dashboard-hero-card">
        <Space direction="vertical" size={12} style={{ width: '100%' }}>
          <Space wrap style={{ width: '100%', justifyContent: 'space-between' }}>
            <Space direction="vertical" size={2}>
              <Typography.Title level={4} style={{ margin: 0 }}>
                Dashboard пилотов
              </Typography.Title>
              <Typography.Text type="secondary">Ключевые метрики по ресурсам и экономике за выбранный период.</Typography.Text>
            </Space>
            <Space wrap>
              <Tag color="geekblue" style={{ fontSize: 13, padding: '4px 8px' }}>
                Период: {periodLabel}
              </Tag>
              <Tag color="cyan" style={{ fontSize: 13, padding: '4px 8px' }}>
                Недель: {summary?.weeks_count ?? 1}
              </Tag>
            </Space>
          </Space>
          <Space direction="vertical" size={8} style={{ width: '100%' }}>
            <Space wrap>
              <Typography.Text type="secondary">Режим:</Typography.Text>
              <Segmented<DashboardPeriodMode>
                value={periodMode}
                options={[
                  { label: 'Неделя', value: 'week' },
                  { label: 'Диапазон', value: 'range' },
                ]}
                onChange={(value) => {
                  const next = value as DashboardPeriodMode;
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
                    if (!next || !next[0] || !next[1]) return;
                    setRange([weekStartOf(next[0]), weekStartOf(next[1])]);
                  }}
                />
              </Space>
            )}
          </Space>
        </Space>
      </Card>

      {summary && (
        <>
          <Row gutter={[16, 16]}>
            <Col xs={24} sm={12} lg={6}>
              <Card className="page-card">
                <Statistic title="Активные пилоты" value={summary.active_pilots_count} />
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card className="page-card">
                <Statistic title="Стоимость ресурсов" value={formatMoney(summary.total_cost)} />
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card className="page-card">
                <Statistic title="Суммарная ПШЕ" value={formatNumber(summary.total_pshe)} />
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card className="page-card">
                <Statistic title="Сотрудники в пилотах" value={summary.active_employees_count} />
              </Card>
            </Col>
          </Row>

          <Row gutter={[16, 16]}>
            <Col xs={24} xl={16}>
              <Card className="page-card" title="Динамика стоимости и ПШЕ по неделям">
                <div style={{ width: '100%', height: 320 }}>
                  <ResponsiveContainer>
                    <LineChart data={weeklyCosts} onClick={(state) => handleWeeklyChartClick(state as { activeLabel?: string })}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="week_start_date" tickFormatter={formatDate} />
                      <YAxis yAxisId="left" tickFormatter={(v) => formatNumber(v, 0)} />
                      <YAxis yAxisId="right" orientation="right" tickFormatter={(v) => formatNumber(v, 2)} />
                      <Tooltip
                        formatter={(value: string | number, name) =>
                          name === 'total_cost' ? formatMoney(value) : formatNumber(value)
                        }
                        labelFormatter={(label) => `Неделя: ${formatDate(label)}`}
                      />
                      <Line yAxisId="left" type="monotone" dataKey="total_cost" stroke="#0f766e" strokeWidth={3} />
                      <Line yAxisId="right" type="monotone" dataKey="total_pshe" stroke="#ea580c" strokeWidth={3} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
                <Typography.Text type="secondary" className="chart-hint">
                  {periodMode === 'week'
                    ? 'Подсказка: клик по точке на графике переключит выбранную неделю.'
                    : 'График показывает динамику внутри выбранного диапазона.'}
                </Typography.Text>
              </Card>
            </Col>
            <Col xs={24} xl={8}>
              <Card className="page-card" title="Топ сотрудников по загрузке">
                <div style={{ width: '100%', height: 320 }}>
                  <ResponsiveContainer>
                    <BarChart data={topEmployeesChartData} layout="vertical" margin={{ left: 10, right: 10 }}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis type="number" />
                      <YAxis type="category" dataKey="full_name" width={140} />
                      <Tooltip formatter={(value: string | number) => `${formatNumber(value)}%`} />
                      <Bar
                        dataKey="total_load_percent"
                        fill="#ef4444"
                        radius={[0, 8, 8, 0]}
                        cursor="pointer"
                        onClick={handleEmployeeChartClick}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <Typography.Text type="secondary" className="chart-hint">
                  Клик по сотруднику откроет его карточку.
                </Typography.Text>
              </Card>
            </Col>
          </Row>

          <Row gutter={[16, 16]}>
            <Col xs={24} lg={14}>
              <Card className="page-card resource-allocation-card" title="Куда уходит ресурс: доля по пилотам">
                <Space direction="vertical" size={14} style={{ width: '100%' }}>
                  <div style={{ width: '100%', height: 280 }}>
                    <ResponsiveContainer>
                      <BarChart data={topPilotAllocationChartData} layout="vertical" margin={{ left: 8, right: 16 }}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis type="number" tickFormatter={(value) => `${formatNumber(value)}%`} />
                        <YAxis type="category" dataKey="pilot_name" width={160} />
                        <Tooltip formatter={(value: string | number) => `${formatNumber(value)}%`} />
                        <Bar
                          dataKey="cost_share_percent"
                          fill="#14b8a6"
                          radius={[0, 8, 8, 0]}
                          cursor="pointer"
                          onClick={handlePilotChartClick}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                  <Typography.Text type="secondary" className="chart-hint">
                    Клик по пилоту в графике откроет карточку пилота.
                  </Typography.Text>

                  <Table<DashboardPilotAllocation>
                    pagination={false}
                    rowKey="pilot_id"
                    dataSource={summary.resource_allocation}
                    columns={[
                      {
                        title: 'Пилот',
                        dataIndex: 'pilot_name',
                        render: (_: string, row: DashboardPilotAllocation) => (
                          <Typography.Link onClick={() => handlePilotDrilldown(row.pilot_id)}>
                            {row.pilot_name}
                          </Typography.Link>
                        ),
                      },
                      {
                        title: 'Доля ресурса',
                        dataIndex: 'cost_share_percent',
                        render: (value: string) => (
                          <Progress
                            percent={Math.min(Number(value), 100)}
                            size="small"
                            format={(percent) => `${formatNumber(percent ?? 0)}%`}
                          />
                        ),
                      },
                      {
                        title: 'Детали',
                        render: (_: string, row: DashboardPilotAllocation) => (
                          <Space direction="vertical" size={0}>
                            <Typography.Text type="secondary">Стоимость: {formatMoney(row.total_cost)}</Typography.Text>
                            <Typography.Text type="secondary">Часы: {formatNumber(row.total_hours)}</Typography.Text>
                            <Typography.Text type="secondary">Сотрудники: {row.employees_count}</Typography.Text>
                          </Space>
                        ),
                      },
                    ]}
                  />
                </Space>
              </Card>
            </Col>
            <Col xs={24} lg={10}>
              <Card className="page-card" title="Пилоты с самой низкой прибыльностью">
                <Table<DashboardProfitabilityItem>
                  pagination={false}
                  rowKey="pilot_id"
                  dataSource={summary.worst_profitability_pilots}
                  columns={[
                    {
                      title: 'Пилот',
                      dataIndex: 'pilot_name',
                      render: (_: string, row: DashboardProfitabilityItem) => (
                        <Typography.Link onClick={() => handlePilotDrilldown(row.pilot_id)}>
                          {row.pilot_name}
                        </Typography.Link>
                      ),
                    },
                    {
                      title: 'Прибыль/убыток',
                      dataIndex: 'profitability_estimate',
                      render: (value: string) => (
                        <span style={{ color: Number(value) >= 0 ? '#15803d' : '#b91c1c' }}>{formatMoney(value)}</span>
                      ),
                    },
                    {
                      title: 'Маржа',
                      dataIndex: 'margin_percent',
                      render: (value: string) => `${formatNumber(value)}%`,
                    },
                  ]}
                />
              </Card>
            </Col>
          </Row>

          <Card className="page-card" title="Распределение ресурса по РЦ (за выбранный период)">
            <Row gutter={[16, 16]}>
              <Col xs={24} xl={12}>
                <div style={{ width: '100%', height: 300 }}>
                  <ResponsiveContainer>
                    <BarChart data={resourceByRc}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="rc" />
                      <YAxis tickFormatter={(value) => `${formatNumber(value)}%`} />
                      <Tooltip formatter={(value: string | number) => `${formatNumber(value)}%`} />
                      <Bar dataKey="load_share_percent" fill="#0ea5e9" radius={[8, 8, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </Col>
              <Col xs={24} xl={12}>
                <Table
                  rowKey="rc"
                  pagination={false}
                  dataSource={resourceByRc}
                  columns={[
                    { title: 'РЦ', dataIndex: 'rc' },
                    { title: 'Сотрудники', dataIndex: 'employees_count' },
                    { title: 'Пилоты', dataIndex: 'pilots_count' },
                    {
                      title: 'Часы',
                      dataIndex: 'total_hours',
                      render: (value: string) => formatNumber(value),
                    },
                    {
                      title: 'Доля',
                      dataIndex: 'load_share_percent',
                      render: (value: string) => `${formatNumber(value)}%`,
                    },
                  ]}
                />
              </Col>
            </Row>
          </Card>

          <Card className="page-card" title="Сотрудники, участвующие в нескольких пилотах">
            {crossAssignments.some((item) => item.overloaded) && (
              <Alert
                style={{ marginBottom: 12 }}
                type="warning"
                showIcon
                message="Есть перегруженные сотрудники с общей загрузкой больше 100%"
              />
            )}
            <Table
              rowKey="employee_id"
              dataSource={crossAssignments}
              pagination={{ pageSize: 8 }}
              columns={[
                { title: 'CAS', dataIndex: 'cas', render: (value: string | null) => value ?? '-' },
                {
                  title: 'ФИО',
                  dataIndex: 'full_name',
                  render: (_: string, row: CrossAssignmentItem) => (
                    <Typography.Link onClick={() => handleEmployeeDrilldown(row.employee_id)}>
                      {row.full_name}
                    </Typography.Link>
                  ),
                },
                { title: 'РЦ', dataIndex: 'rc' },
                { title: 'Кол-во пилотов', dataIndex: 'pilot_count' },
                { title: 'Пилоты', dataIndex: 'pilots', render: (value: string[]) => value.join(', ') },
                {
                  title: periodMode === 'week' ? 'Суммарная загрузка' : 'Средняя загрузка/нед',
                  dataIndex: 'total_load_percent',
                  render: (value: string) => `${formatNumber(value)}%`,
                },
                {
                  title: 'Статус',
                  dataIndex: 'overloaded',
                  render: (value: boolean) =>
                    value ? <span className="warning-text">Перегружен</span> : 'Нормально',
                },
              ]}
            />
          </Card>
        </>
      )}
    </Space>
  );
};
