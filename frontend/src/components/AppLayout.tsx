import { AppstoreOutlined, DashboardOutlined, DatabaseOutlined, HistoryOutlined, TeamOutlined } from '@ant-design/icons';
import { Layout, Menu, Space, Typography } from 'antd';
import { useMemo } from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';

const { Header, Sider, Content } = Layout;

const menuItems = [
  {
    key: '/',
    icon: <DashboardOutlined />,
    label: <Link to="/">Dashboard</Link>,
  },
  {
    key: '/pilots',
    icon: <AppstoreOutlined />,
    label: <Link to="/pilots">Пилоты</Link>,
  },
  {
    key: '/updates',
    icon: <HistoryOutlined />,
    label: <Link to="/updates">Обновления SQL</Link>,
  },
  {
    key: '/employees',
    icon: <TeamOutlined />,
    label: <Link to="/employees">Сотрудники</Link>,
  },
  {
    key: '/backups',
    icon: <DatabaseOutlined />,
    label: <Link to="/backups">Бэкапы</Link>,
  },
];

export const AppLayout = () => {
  const location = useLocation();

  const selectedKey = useMemo(() => {
    if (location.pathname.startsWith('/pilots')) return '/pilots';
    if (location.pathname.startsWith('/updates')) return '/updates';
    if (location.pathname.startsWith('/employees')) return '/employees';
    if (location.pathname.startsWith('/backups')) return '/backups';
    return '/';
  }, [location.pathname]);

  return (
    <Layout className="app-root-layout">
      <Sider width={250} className="app-sider" breakpoint="lg" collapsedWidth={0}>
        <div className="app-sider-inner">
          <div className="app-logo-block">
            <div className="app-logo-mark">PM</div>
            <div>
              <div className="app-logo-title">Pilot Metrics Hub</div>
              <Typography.Text className="app-logo-subtitle">Ресурсы и экономика</Typography.Text>
            </div>
          </div>
          <Menu className="app-nav-menu" theme="dark" mode="inline" selectedKeys={[selectedKey]} items={menuItems} />
          <div className="app-sider-footer">
            <Typography.Text className="app-sider-footer-text">MVP Internal Service</Typography.Text>
          </div>
        </div>
      </Sider>
      <Layout>
        <Header className="app-header">
          <Space direction="vertical" size={0}>
            <Typography.Title level={3} className="app-header-title">
              Учет ресурсов и доходности пилотов
            </Typography.Title>
            <Typography.Text className="app-header-subtitle">
              Планируйте загрузку, контролируйте затраты и отслеживайте экономику пилотов в одном месте.
            </Typography.Text>
          </Space>
        </Header>
        <Content className="app-content">
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
};
