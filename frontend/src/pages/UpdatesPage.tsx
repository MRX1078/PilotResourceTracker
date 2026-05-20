import { ReloadOutlined, SyncOutlined } from '@ant-design/icons';
import { Alert, Button, Card, Progress, Space, Table, Tag, Tooltip, Typography, message } from 'antd';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import { api } from '../api';
import { PilotLatestRun, QueryRunStatus } from '../types/api';
import { formatDate } from '../utils/date';

const statusColor: Record<QueryRunStatus, string> = {
  pending: 'default',
  running: 'processing',
  success: 'success',
  failed: 'error',
};

const statusLabel: Record<QueryRunStatus, string> = {
  pending: 'PENDING',
  running: 'RUNNING',
  success: 'SUCCESS',
  failed: 'FAILED',
};

interface RefreshProgress {
  total: number;
  done: number;
  currentPilotId: number | null;
  currentPilotName: string | null;
}

const formatDateTime = (value: string | null | undefined): string => {
  if (!value) return '-';
  const formatted = formatDate(value);
  // formatDate returns YYYY-MM-DD; append the time if present in the source string.
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return formatted;
  const hh = String(date.getHours()).padStart(2, '0');
  const mm = String(date.getMinutes()).padStart(2, '0');
  return `${formatted} ${hh}:${mm}`;
};

export const UpdatesPage = () => {
  const [rows, setRows] = useState<PilotLatestRun[]>([]);
  const [loading, setLoading] = useState(false);
  const [refreshProgress, setRefreshProgress] = useState<RefreshProgress | null>(null);

  const loadRows = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getLatestRunsByPilot();
      setRows(data);
    } catch (error) {
      message.error(`Не удалось загрузить состояние обновлений: ${(error as Error).message}`);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadRows();
  }, [loadRows]);

  const eligible = useMemo(() => rows.filter((row) => row.has_successful_run), [rows]);
  const skippedCount = rows.length - eligible.length;

  const handleRefreshAll = async () => {
    if (eligible.length === 0) {
      message.warning(
        'Нет пилотов, у которых был хотя бы один успешный запуск. Запустите их вручную из карточки пилота.'
      );
      return;
    }

    setRefreshProgress({
      total: eligible.length,
      done: 0,
      currentPilotId: null,
      currentPilotName: null,
    });

    let successCount = 0;
    let failedCount = 0;

    for (let index = 0; index < eligible.length; index += 1) {
      const target = eligible[index];
      setRefreshProgress({
        total: eligible.length,
        done: index,
        currentPilotId: target.pilot_id,
        currentPilotName: target.pilot_name,
      });

      try {
        await api.refreshPilot(target.pilot_id);
        successCount += 1;
        message.success(`Готово: ${target.pilot_name}`);
      } catch (error) {
        failedCount += 1;
        message.error(`Ошибка обновления ${target.pilot_name}: ${(error as Error).message}`);
      }

      // Reload after every pilot so the table reflects current state in real-time.
      await loadRows();
    }

    setRefreshProgress({
      total: eligible.length,
      done: eligible.length,
      currentPilotId: null,
      currentPilotName: null,
    });

    message.info(
      `Цикл обновления завершен. Успешно: ${successCount}, с ошибками: ${failedCount}.`
    );

    // Drop progress indicator after a short pause so the final state stays visible.
    setTimeout(() => setRefreshProgress(null), 1500);
  };

  const isRefreshing = refreshProgress !== null && refreshProgress.done < refreshProgress.total;

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Card className="page-card">
        <Space style={{ width: '100%', justifyContent: 'space-between' }} wrap>
          <Space direction="vertical" size={0}>
            <Typography.Title level={4} style={{ margin: 0 }}>
              Состояние SQL-обновлений по пилотам
            </Typography.Title>
            <Typography.Text type="secondary">
              По каждому активному SQL-пилоту показано только последнее состояние запуска.
            </Typography.Text>
          </Space>
          <Space>
            <Button icon={<ReloadOutlined />} onClick={() => void loadRows()} disabled={isRefreshing}>
              Перечитать
            </Button>
            <Tooltip
              title={
                eligible.length === 0
                  ? 'Нет пилотов с хотя бы одним успешным запуском'
                  : `Будет обновлено пилотов: ${eligible.length}`
              }
            >
              <Button
                type="primary"
                icon={<SyncOutlined spin={isRefreshing} />}
                disabled={eligible.length === 0}
                loading={isRefreshing}
                onClick={() => void handleRefreshAll()}
              >
                Обновить все ({eligible.length})
              </Button>
            </Tooltip>
          </Space>
        </Space>
      </Card>

      {skippedCount > 0 && (
        <Alert
          showIcon
          type="info"
          message={`Будут пропущены ${skippedCount} пилот(ов) без единого успешного запуска`}
          description="Запустите их вручную из карточки пилота — после первого успеха они станут участвовать в массовом обновлении."
        />
      )}

      {refreshProgress && (
        <Card className="page-card">
          <Space direction="vertical" size={8} style={{ width: '100%' }}>
            <Space style={{ width: '100%', justifyContent: 'space-between' }} wrap>
              <Typography.Text strong>
                Обновление: {refreshProgress.done}/{refreshProgress.total}
              </Typography.Text>
              {refreshProgress.currentPilotName && (
                <Typography.Text>
                  Сейчас: <Tag color="processing">{refreshProgress.currentPilotName}</Tag>
                </Typography.Text>
              )}
            </Space>
            <Progress
              percent={
                refreshProgress.total === 0
                  ? 0
                  : Math.round((refreshProgress.done / refreshProgress.total) * 100)
              }
              status={isRefreshing ? 'active' : 'success'}
            />
          </Space>
        </Card>
      )}

      <Card className="page-card">
        <Table
          rowKey="pilot_id"
          loading={loading}
          dataSource={rows}
          pagination={{ pageSize: 20 }}
          columns={[
            {
              title: 'Пилот',
              render: (_, row: PilotLatestRun) => (
                <Link to={`/pilots/${row.pilot_id}`}>{row.pilot_name}</Link>
              ),
            },
            {
              title: 'Статус последнего запуска',
              render: (_, row: PilotLatestRun) => {
                if (!row.last_run) return <Tag>NEVER RUN</Tag>;
                const status = row.last_run.status;
                return <Tag color={statusColor[status] ?? 'default'}>{statusLabel[status] ?? status}</Tag>;
              },
            },
            {
              title: 'Был успех?',
              render: (_, row: PilotLatestRun) =>
                row.has_successful_run ? <Tag color="success">да</Tag> : <Tag>нет</Tag>,
            },
            {
              title: 'Запуск',
              render: (_, row: PilotLatestRun) => formatDateTime(row.last_run?.started_at ?? null),
            },
            {
              title: 'Завершен',
              render: (_, row: PilotLatestRun) => formatDateTime(row.last_run?.finished_at ?? null),
            },
            {
              title: 'Строк',
              render: (_, row: PilotLatestRun) => row.last_run?.rows_returned ?? '-',
            },
            {
              title: 'Ошибка',
              render: (_, row: PilotLatestRun) => row.last_run?.error_message ?? '-',
            },
          ]}
        />
      </Card>
    </Space>
  );
};
