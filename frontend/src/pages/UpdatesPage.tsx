import { Button, Card, Space, Table, Tag, Typography, message } from 'antd';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { api } from '../api';
import { TrinoRun } from '../types/api';
import { formatDate } from '../utils/date';

const statusColor: Record<string, string> = {
  pending: 'default',
  running: 'processing',
  success: 'success',
  failed: 'error',
};

export const UpdatesPage = () => {
  const [runs, setRuns] = useState<TrinoRun[]>([]);
  const [loading, setLoading] = useState(false);

  const loadRuns = async () => {
    setLoading(true);
    try {
      const data = await api.getTrinoRuns(200);
      setRuns(data);
    } catch (error) {
      message.error(`Не удалось загрузить историю обновлений: ${(error as Error).message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadRuns();
  }, []);

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Card className="page-card">
        <Space style={{ width: '100%', justifyContent: 'space-between' }} wrap>
          <Space direction="vertical" size={0}>
            <Typography.Title level={4} style={{ margin: 0 }}>
              История запусков SQL-запросов
            </Typography.Title>
            <Typography.Text type="secondary">
              По каждому запуску показывается статус, ошибка и количество обработанных строк.
            </Typography.Text>
          </Space>
          <Button onClick={() => void loadRuns()}>Обновить</Button>
        </Space>
      </Card>

      <Card className="page-card">
        <Table
          rowKey="id"
          loading={loading}
          dataSource={runs}
          pagination={{ pageSize: 12 }}
          columns={[
            {
              title: 'Пилот',
              render: (_, row) => <Link to={`/pilots/${row.pilot_id}`}>{row.pilot_name}</Link>,
            },
            {
              title: 'Запуск',
              dataIndex: 'started_at',
              render: (value: string) => formatDate(value),
            },
            {
              title: 'Статус',
              dataIndex: 'status',
              render: (value: string) => <Tag color={statusColor[value] ?? 'default'}>{value.toUpperCase()}</Tag>,
            },
            {
              title: 'Строк',
              dataIndex: 'rows_returned',
            },
            {
              title: 'Ошибка',
              dataIndex: 'error_message',
              render: (value: string | null) => value ?? '-',
            },
            {
              title: 'Завершен',
              dataIndex: 'finished_at',
              render: (value: string | null) => (value ? formatDate(value) : '-'),
            },
          ]}
        />
      </Card>
    </Space>
  );
};
