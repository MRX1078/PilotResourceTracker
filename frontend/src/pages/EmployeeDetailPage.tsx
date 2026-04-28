import { Alert, Card, DatePicker, Segmented, Space, Spin, Table, Tag, Typography, message } from 'antd';
import dayjs, { Dayjs } from 'dayjs';
import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import { api } from '../api';
import { WeekPicker } from '../components/WeekPicker';
import { EmployeeDetail } from '../types/api';
import { formatDate, toIsoDate, weekStartOf } from '../utils/date';
import { formatNumber } from '../utils/format';

type EmployeePeriodMode = 'week' | 'range';

export const EmployeeDetailPage = () => {
  const params = useParams();
  const [periodMode, setPeriodMode] = useState<EmployeePeriodMode>('week');
  const [week, setWeek] = useState(weekStartOf(dayjs()));
  const [range, setRange] = useState<[Dayjs, Dayjs]>([
    weekStartOf(dayjs().subtract(7, 'week')),
    weekStartOf(dayjs()),
  ]);
  const [employee, setEmployee] = useState<EmployeeDetail | null>(null);
  const [loading, setLoading] = useState(true);

  const employeeId = Number(params.employeeId);
  const weekStart = useMemo(() => toIsoDate(weekStartOf(week)), [week]);
  const normalizedRange = useMemo<[Dayjs, Dayjs]>(() => {
    const start = weekStartOf(range[0]);
    const end = weekStartOf(range[1]);
    return start.isAfter(end) ? [end, start] : [start, end];
  }, [range]);
  const rangeStart = useMemo(() => toIsoDate(normalizedRange[0]), [normalizedRange]);
  const rangeEnd = useMemo(() => toIsoDate(normalizedRange[1]), [normalizedRange]);
  const requestWeek = periodMode === 'week' ? weekStart : rangeEnd;

  useEffect(() => {
    if (!employeeId) return;

    const load = async () => {
      setLoading(true);
      try {
        const data = await api.getEmployee(employeeId, requestWeek);
        setEmployee(data);
      } catch (error) {
        message.error(`Не удалось загрузить карточку сотрудника: ${(error as Error).message}`);
      } finally {
        setLoading(false);
      }
    };

    void load();
  }, [employeeId, requestWeek]);

  const filteredWeeklyLoads = useMemo(() => {
    if (!employee) return [];
    if (periodMode === 'week') {
      return employee.weekly_loads.filter((item) => item.week_start_date === weekStart);
    }
    return employee.weekly_loads.filter(
      (item) => item.week_start_date >= rangeStart && item.week_start_date <= rangeEnd
    );
  }, [employee, periodMode, rangeEnd, rangeStart, weekStart]);

  const periodAverageLoadPercent = useMemo(() => {
    if (filteredWeeklyLoads.length === 0) return 0;
    const total = filteredWeeklyLoads.reduce((sum, item) => sum + Number(item.total_load_percent), 0);
    return total / filteredWeeklyLoads.length;
  }, [filteredWeeklyLoads]);

  const periodTotalHours = useMemo(
    () => filteredWeeklyLoads.reduce((sum, item) => sum + Number(item.total_hours), 0),
    [filteredWeeklyLoads]
  );

  const periodOverloaded = useMemo(() => {
    if (periodMode === 'week') {
      return employee?.is_overloaded ?? false;
    }
    return filteredWeeklyLoads.some((item) => Number(item.total_load_percent) > 100);
  }, [employee?.is_overloaded, filteredWeeklyLoads, periodMode]);

  const chartData = useMemo(() => {
    if (!employee) return [];
    if (periodMode === 'week') return employee.weekly_loads;
    return filteredWeeklyLoads;
  }, [employee, filteredWeeklyLoads, periodMode]);

  if (loading && !employee) {
    return (
      <Card className="page-card">
        <Spin />
      </Card>
    );
  }

  if (!employee) {
    return (
      <Card className="page-card">
        <Typography.Text>Сотрудник не найден.</Typography.Text>
      </Card>
    );
  }

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Card className="page-card">
        <Space direction="vertical" size={8} style={{ width: '100%' }}>
          <Typography.Title level={4} style={{ margin: 0 }}>
            {employee.full_name}
          </Typography.Title>
          <Space>
            <Tag color="processing">CAS: {employee.cas ?? '-'}</Tag>
            <Tag>РЦ: {employee.rc}</Tag>
            <Tag color={periodOverloaded ? 'error' : 'success'}>
              {periodMode === 'week'
                ? `Загрузка: ${formatNumber(employee.selected_week_total_load_percent)}%`
                : `Средняя загрузка/нед: ${formatNumber(periodAverageLoadPercent)}%`}
            </Tag>
            {periodMode === 'range' && <Tag color="blue">Часы за период: {formatNumber(periodTotalHours)}</Tag>}
          </Space>
          <Space direction="vertical" size={8} style={{ width: '100%' }}>
            <Space wrap>
              <Typography.Text type="secondary">Период:</Typography.Text>
              <Segmented<EmployeePeriodMode>
                value={periodMode}
                options={[
                  { label: 'Неделя', value: 'week' },
                  { label: 'Интервал', value: 'range' },
                ]}
                onChange={(value) => {
                  const next = value as EmployeePeriodMode;
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

      {periodOverloaded && (
        <Alert
          type="warning"
          showIcon
          message="Сотрудник перегружен"
          description={
            periodMode === 'week'
              ? 'Суммарная загрузка по пилотам за выбранную неделю больше 100%.'
              : 'В выбранном интервале есть недели, где суммарная загрузка по пилотам больше 100%.'
          }
        />
      )}

      <Card
        className="page-card"
        title={
          periodMode === 'week'
            ? `Пилоты сотрудника за неделю ${formatDate(weekStart)}`
            : `Пилоты сотрудника за неделю окончания интервала: ${formatDate(rangeEnd)}`
        }
      >
        <Table
          rowKey={(item) => `${item.pilot_id}-${item.week_start_date}`}
          dataSource={employee.pilots}
          pagination={false}
          columns={[
            {
              title: 'Пилот',
              render: (_, row) => <Link to={`/pilots/${row.pilot_id}`}>{row.pilot_name}</Link>,
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
              title: 'Неделя',
              dataIndex: 'week_start_date',
              render: (value: string) => formatDate(value),
            },
          ]}
        />
      </Card>

      <Card
        className="page-card"
        title={periodMode === 'week' ? 'Суммарная загрузка по неделям' : 'Суммарная загрузка в выбранном интервале'}
      >
        <div style={{ width: '100%', height: 320 }}>
          <ResponsiveContainer>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="week_start_date" tickFormatter={formatDate} />
              <YAxis tickFormatter={(value) => `${formatNumber(value)}%`} />
              <Tooltip
                labelFormatter={(label) => `Неделя: ${formatDate(label)}`}
                formatter={(value: string | number) => `${formatNumber(value)}%`}
              />
              <Line type="monotone" dataKey="total_load_percent" stroke="#dc2626" strokeWidth={3} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>
    </Space>
  );
};
