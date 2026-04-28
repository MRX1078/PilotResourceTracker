import { FileTextOutlined, PlusOutlined, UploadOutlined } from '@ant-design/icons';
import {
  Alert,
  Button,
  Card,
  Col,
  DatePicker,
  Form,
  Input,
  InputNumber,
  Modal,
  Row,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  Upload,
  message,
} from 'antd';
import dayjs, { Dayjs } from 'dayjs';
import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import { api } from '../api';
import { AssignmentPayload, EmployeeListItem, PilotListItem } from '../types/api';
import { toIsoDate, weekStartOf } from '../utils/date';
import { downloadTemplate, FILE_TEMPLATES } from '../utils/fileTemplates';

interface AssignFormValues {
  pilot_id: number;
  week_start_date: Dayjs;
  hours?: number;
  load_percent?: number;
  pshe?: number;
  cas?: string;
  full_name?: string;
  rc?: string;
}

export const EmployeesPage = () => {
  const [employees, setEmployees] = useState<EmployeeListItem[]>([]);
  const [pilots, setPilots] = useState<PilotListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchInput, setSearchInput] = useState('');
  const [searchQuery, setSearchQuery] = useState<string | undefined>(undefined);

  const [isAssignModalOpen, setIsAssignModalOpen] = useState(false);
  const [selectedEmployee, setSelectedEmployee] = useState<EmployeeListItem | null>(null);
  const [submittingAssignment, setSubmittingAssignment] = useState(false);
  const [importingEmployeesCsv, setImportingEmployeesCsv] = useState(false);
  const [assignForm] = Form.useForm<AssignFormValues>();

  const manualPilots = useMemo(
    () => pilots.filter((pilot) => pilot.is_active && pilot.accounting_mode === 'manual'),
    [pilots]
  );

  const loadEmployees = async (query?: string) => {
    setLoading(true);
    try {
      const data = await api.getEmployees(query);
      setEmployees(data);
    } catch (error) {
      message.error(`Не удалось загрузить сотрудников: ${(error as Error).message}`);
    } finally {
      setLoading(false);
    }
  };

  const loadPilots = async () => {
    try {
      const data = await api.getPilots();
      setPilots(data);
    } catch (error) {
      message.error(`Не удалось загрузить пилоты: ${(error as Error).message}`);
    }
  };

  useEffect(() => {
    void loadEmployees(searchQuery);
  }, [searchQuery]);

  useEffect(() => {
    void loadPilots();
  }, []);

  const openAssignModal = (employee: EmployeeListItem | null) => {
    setSelectedEmployee(employee);
    setIsAssignModalOpen(true);
    assignForm.resetFields();
    assignForm.setFieldsValue({
      week_start_date: weekStartOf(dayjs()),
    });
  };

  const closeAssignModal = () => {
    setIsAssignModalOpen(false);
    setSelectedEmployee(null);
    assignForm.resetFields();
  };

  const handleImportEmployeesCsv = async (file: File) => {
    setImportingEmployeesCsv(true);
    try {
      const response = await api.importEmployeesCsv(file);
      message.success(
        `Импорт сотрудников завершен: ${response.imported_count} строк (создано ${response.created_count}, обновлено ${response.updated_count})`
      );
      if (response.errors.length > 0) {
        const preview = response.errors
          .slice(0, 3)
          .map((item) => `строка ${item.row_number}: ${item.error}`)
          .join(' | ');
        message.warning(`Часть строк пропущена: ${preview}`);
      }
      await loadEmployees(searchQuery);
    } catch (error: any) {
      const detail = error?.response?.data?.detail;
      if (detail && typeof detail === 'object' && Array.isArray(detail.errors)) {
        const preview = detail.errors
          .slice(0, 3)
          .map((item: { row_number: number; error: string }) => `строка ${item.row_number}: ${item.error}`)
          .join(' | ');
        message.error(`Импорт сотрудников не выполнен: ${preview}`);
      } else {
        message.error(`Не удалось импортировать сотрудников: ${(error as Error).message}`);
      }
    } finally {
      setImportingEmployeesCsv(false);
    }
    return false;
  };

  const handleAssignSubmit = async () => {
    if (manualPilots.length === 0) {
      message.error('Нет доступных ручных пилотов для назначения');
      return;
    }

    const values = await assignForm.validateFields();

    const payload: AssignmentPayload = {
      week_start_date: toIsoDate(weekStartOf(values.week_start_date)),
      source: 'manual',
      hours: values.hours,
      load_percent: values.load_percent,
      pshe: values.pshe,
    };

    if (selectedEmployee) {
      payload.employee_id = selectedEmployee.id;
    } else {
      const cas = values.cas?.trim();
      const fullName = values.full_name?.trim();
      const rc = values.rc?.trim();
      const hasCas = Boolean(cas);
      const hasFullProfile = Boolean(fullName && rc);
      const hasPartialProfile = Boolean((fullName && !rc) || (!fullName && rc));

      if (!hasCas && !hasFullProfile) {
        message.error('Укажите CAS существующего сотрудника или заполните ФИО+РЦ для создания нового');
        return;
      }

      if (hasPartialProfile) {
        message.error('Для нового сотрудника нужно заполнить и ФИО, и РЦ');
        return;
      }

      payload.cas = cas || undefined;
      payload.full_name = fullName || undefined;
      payload.rc = rc || undefined;
    }

    setSubmittingAssignment(true);
    try {
      await api.createAssignment(values.pilot_id, payload);
      message.success('Назначение создано');
      closeAssignModal();
      await loadEmployees(searchQuery);
    } catch (error) {
      message.error(`Не удалось создать назначение: ${(error as Error).message}`);
    } finally {
      setSubmittingAssignment(false);
    }
  };

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Card className="page-card">
        <Space direction="vertical" size={8} style={{ width: '100%' }}>
          <Typography.Title level={4} style={{ margin: 0 }}>
            Сотрудники
          </Typography.Title>
          <Typography.Text type="secondary">
            Импортируйте справочник сотрудников 1 раз по CAS, затем распределяйте их по ручным пилотам.
          </Typography.Text>
          <Space wrap>
            <Input.Search
              placeholder="Поиск по ФИО или CAS"
              allowClear
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
              onSearch={(value) => setSearchQuery(value.trim() || undefined)}
              style={{ width: 320 }}
            />
            <Button icon={<PlusOutlined />} type="primary" onClick={() => openAssignModal(null)}>
              Новый сотрудник + назначение
            </Button>
            <Upload
              accept=".csv,text/csv"
              maxCount={1}
              showUploadList={false}
              beforeUpload={(file) => {
                void handleImportEmployeesCsv(file);
                return false;
              }}
            >
              <Button icon={<UploadOutlined />} loading={importingEmployeesCsv}>
                Импорт сотрудников CSV
              </Button>
            </Upload>
            <Button icon={<FileTextOutlined />} onClick={() => downloadTemplate(FILE_TEMPLATES.employeesCsv)}>
              Шаблон CSV
            </Button>
            <Button onClick={() => void loadEmployees(searchQuery)}>Обновить</Button>
          </Space>
        </Space>
      </Card>

      <Card className="page-card">
        <Alert
          showIcon
          style={{ marginBottom: 12 }}
          message="Поток работы"
          description="1) Импортируйте справочник сотрудников (колонки: cas_id/cas, full_name, rc). 2) Назначайте сотрудников в ручные пилоты из таблицы или по CAS в модальном окне."
          type="info"
        />

        <Table
          rowKey="id"
          loading={loading}
          dataSource={employees}
          pagination={{ pageSize: 12 }}
          columns={[
            {
              title: 'CAS',
              dataIndex: 'cas',
              render: (value: string | null) => value ?? '-',
            },
            {
              title: 'ФИО',
              dataIndex: 'full_name',
            },
            {
              title: 'РЦ',
              dataIndex: 'rc',
            },
            {
              title: 'Действия',
              render: (_, row) => (
                <Space>
                  <Button size="small">
                    <Link to={`/employees/${row.id}`}>Карточка</Link>
                  </Button>
                  <Button size="small" type="primary" onClick={() => openAssignModal(row)}>
                    Назначить в пилот
                  </Button>
                </Space>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        title={selectedEmployee ? `Назначить: ${selectedEmployee.full_name}` : 'Новый сотрудник + назначение'}
        open={isAssignModalOpen}
        onCancel={closeAssignModal}
        onOk={() => void handleAssignSubmit()}
        okText="Сохранить"
        confirmLoading={submittingAssignment}
      >
        <Form<AssignFormValues>
          form={assignForm}
          layout="vertical"
          initialValues={{ week_start_date: weekStartOf(dayjs()) }}
        >
          {selectedEmployee ? (
            <Card size="small" style={{ marginBottom: 12 }}>
              <Space direction="vertical" size={2}>
                <Typography.Text strong>{selectedEmployee.full_name}</Typography.Text>
                <Typography.Text type="secondary">
                  CAS: {selectedEmployee.cas ?? '-'} | РЦ: {selectedEmployee.rc}
                </Typography.Text>
              </Space>
            </Card>
          ) : (
            <Row gutter={12}>
              <Col span={8}>
                <Form.Item name="cas" label="CAS">
                  <Input placeholder="cas123" />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="full_name" label="ФИО">
                  <Input placeholder="Иванов Иван" />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="rc" label="РЦ">
                  <Input placeholder="RC-1" />
                </Form.Item>
              </Col>
            </Row>
          )}

          <Form.Item name="pilot_id" label="Пилот" rules={[{ required: true, message: 'Выберите пилот' }]}>
            <Select
              placeholder="Выберите ручной пилот"
              options={manualPilots.map((pilot) => ({ value: pilot.id, label: pilot.name }))}
              notFoundContent="Нет ручных пилотов"
            />
          </Form.Item>

          <Form.Item name="week_start_date" label="Неделя" rules={[{ required: true, message: 'Выберите неделю' }]}>
            <DatePicker picker="week" format="YYYY-[W]WW" style={{ width: '100%' }} allowClear={false} />
          </Form.Item>

          <Row gutter={12}>
            <Col span={8}>
              <Form.Item name="hours" label="Часы" rules={[{ required: true, message: 'Укажите часы' }]}>
                <InputNumber min={0} step={0.5} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="load_percent" label="% загрузки (опц.)">
                <InputNumber min={0} step={1} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="pshe" label="ПШЕ (опц.)">
                <InputNumber min={0} step={0.1} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Tag color="processing">Назначение создается с источником MANUAL</Tag>
        </Form>
      </Modal>
    </Space>
  );
};
