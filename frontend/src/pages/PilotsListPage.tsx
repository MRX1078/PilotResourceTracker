import { ReloadOutlined, PlusOutlined } from '@ant-design/icons';
import { Button, Card, Input, Popconfirm, Space, Table, Tag, Typography, message } from 'antd';
import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { api } from '../api';
import { PilotListItem, RefreshAllResponse } from '../types/api';
import { formatDate } from '../utils/date';
import { formatMoney, formatNumber } from '../utils/format';

export const PilotsListPage = () => {
  const navigate = useNavigate();
  const [pilots, setPilots] = useState<PilotListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');

  const loadPilots = async () => {
    setLoading(true);
    try {
      const data = await api.getPilots();
      setPilots(data);
    } catch (error) {
      message.error(`Не удалось загрузить пилоты: ${(error as Error).message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadPilots();
  }, []);

  const filteredPilots = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return pilots;
    return pilots.filter((pilot) =>
      [pilot.name, pilot.description ?? '', pilot.accounting_mode].join(' ').toLowerCase().includes(term)
    );
  }, [pilots, search]);

  const handleRefreshOne = async (pilotId: number) => {
    try {
      const response = await api.refreshPilot(pilotId);
      message.success(`${response.pilot_name}: обновлено строк ${response.rows_processed}`);
      await loadPilots();
    } catch (error) {
      message.error(`Ошибка обновления пилота: ${(error as Error).message}`);
    }
  };

  const handleRefreshAll = async () => {
    try {
      const response: RefreshAllResponse = await api.refreshAllPilots();
      const errorsText = response.errors
        .map((item) => `${item.pilot_name} (#${item.pilot_id}): ${item.error}`)
        .join('\n');

      if (response.failed_count > 0) {
        message.warning(
          `refresh-all завершен. Успешно: ${response.success_count}, ошибок: ${response.failed_count}. ${errorsText}`
        );
      } else {
        message.success(`refresh-all завершен успешно. Обновлено пилотов: ${response.success_count}`);
      }

      await loadPilots();
    } catch (error) {
      message.error(`Ошибка refresh-all: ${(error as Error).message}`);
    }
  };

  const handleDeletePilot = async (pilotId: number) => {
    try {
      await api.deletePilot(pilotId);
      message.success('Пилот деактивирован');
      await loadPilots();
    } catch (error) {
      message.error(`Не удалось удалить пилот: ${(error as Error).message}`);
    }
  };

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Card className="page-card">
        <Space direction="vertical" size={12} style={{ width: '100%' }}>
          <Typography.Title level={4} style={{ margin: 0 }}>
            Список пилотов
          </Typography.Title>
          <Space wrap>
            <Input.Search
              placeholder="Поиск по названию, описанию, режиму"
              allowClear
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              style={{ width: 360 }}
            />
            <Button icon={<ReloadOutlined />} onClick={() => void loadPilots()}>
              Обновить таблицу
            </Button>
            <Button icon={<ReloadOutlined />} type="default" onClick={() => void handleRefreshAll()}>
              Refresh all SQL
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/pilots/new')}>
              Новый пилот
            </Button>
          </Space>
        </Space>
      </Card>

      <Card className="page-card">
        <Table
          rowKey="id"
          loading={loading}
          dataSource={filteredPilots}
          pagination={{ pageSize: 10 }}
          columns={[
            {
              title: 'Название',
              dataIndex: 'name',
              sorter: (a, b) => a.name.localeCompare(b.name),
            },
            {
              title: 'Режим учета',
              dataIndex: 'accounting_mode',
              render: (value: string) =>
                value === 'sql' ? <Tag color="blue">SQL</Tag> : <Tag color="green">Manual</Tag>,
            },
            {
              title: 'Доходность/год',
              dataIndex: 'annual_revenue',
              render: (value: string) => formatMoney(value),
              sorter: (a, b) => Number(a.annual_revenue) - Number(b.annual_revenue),
            },
            {
              title: 'Стоимость последней недели',
              dataIndex: 'latest_metric',
              render: (value: PilotListItem['latest_metric']) =>
                value ? formatMoney(value.total_cost) : 'Нет данных',
            },
            {
              title: 'ПШЕ последней недели',
              dataIndex: 'latest_metric',
              render: (value: PilotListItem['latest_metric']) =>
                value ? formatNumber(value.total_pshe) : 'Нет данных',
            },
            {
              title: 'Сотрудников',
              dataIndex: 'employees_count',
            },
            {
              title: 'Последний refresh',
              dataIndex: 'last_refresh_status',
              render: (_, row) => {
                if (!row.last_refresh_status) return 'Не запускался';
                const label = `${row.last_refresh_status.toUpperCase()} ${
                  row.last_refresh_started_at ? `(${formatDate(row.last_refresh_started_at)})` : ''
                }`;
                return (
                  <Tag color={row.last_refresh_status === 'success' ? 'success' : row.last_refresh_status === 'failed' ? 'error' : 'default'}>
                    {label}
                  </Tag>
                );
              },
            },
            {
              title: 'Действия',
              key: 'actions',
              render: (_, row) => (
                <Space wrap>
                  <Button size="small" onClick={() => navigate(`/pilots/${row.id}`)}>
                    Открыть
                  </Button>
                  <Button size="small" onClick={() => navigate(`/pilots/${row.id}/edit`)}>
                    Редактировать
                  </Button>
                  <Button
                    size="small"
                    icon={<ReloadOutlined />}
                    onClick={() => void handleRefreshOne(row.id)}
                    disabled={row.accounting_mode !== 'sql'}
                  >
                    Обновить
                  </Button>
                  <Popconfirm
                    title="Деактивировать пилот?"
                    onConfirm={() => void handleDeletePilot(row.id)}
                    okText="Да"
                    cancelText="Нет"
                  >
                    <Button danger size="small">
                      Удалить
                    </Button>
                  </Popconfirm>
                </Space>
              ),
            },
          ]}
        />
      </Card>
    </Space>
  );
};
